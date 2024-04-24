from circuits.models import Circuit, CircuitType, ProviderNetwork
from dcim.models import Interface, RearPort, Site
from extras.scripts import Script
from extras.validators import CustomValidator


class PositionValidator(CustomValidator):
    """
    Raise Error if Device is assigned to rack, with u_height above 0, but not assigned a Rack Position
    """

    def get_device_height(self, device):
        device_type = device.device_type
        height = device_type.u_height
        return height

    def validate(self, device):
        if not device.rack:
            return
        height = self.get_device_height(device)
        if not height:
            return
        # In rack and height > 0, must have rack position
        if not device.position:
            self.fail(f"Device with height {height} must be assigned a Rack Position.")


class CircuitValidator(CustomValidator):
    """
    Report to validate whether the Circuit conforms to the 'standard'
    Including Standard, P2P, Meet Me, and 'Direct to Device'
    """

    def check_term_site(self, site):
        if not isinstance(site, Site):
            return False, f"Unknown Site: ({site})"

        return True, ""

    def check_term_provider_network(self, provider_network):
        if not isinstance(provider_network, ProviderNetwork):
            return False, f"Unknown Provider Network: ({self.term_z})"

        return True, ""

    def check_standard_cables(self, b_side):
        meet_me = False

        for term in b_side:
            front_port = term.frontports.first()
            device_cable = front_port.cable

            if not device_cable:
                return (
                    False,
                    f"Patch Panel Cable found, but missing Cable on the corresponding FrontPort of RearPort:{term}",
                )

            if front_port.opposite_cable_end == "A":
                self.logger.log_warning(
                    f"Circuit: {self.circuit} -- Warning: Cable ({device_cable}) has cable ends swapped."
                )
                cable_side = "a_terminations"
            else:
                cable_side = "b_terminations"

            interface = getattr(device_cable, cable_side)
            if not interface:
                return False, f"Patch Panel Cable found, but missing Device Cable: {device_cable}"
            if isinstance(interface[0], RearPort):
                # Meet Me Extra Cable
                mm_port = interface[0].frontports.first()
                device_cable = mm_port.cable

                cable_side = f"{mm_port.opposite_cable_end.lower()}_terminations"
                interface = getattr(device_cable, cable_side)
                meet_me = True

            if not isinstance(interface[0], Interface):
                return False, f"Unsupported Extra Cable, {interface=} / {device_cable.color}, manually review."

        message = "" if not meet_me else "Meet Me Circuit"
        return True, message

    def cable_check(self, cable):
        a_side = cable.a_terminations
        b_side = cable.b_terminations

        if not a_side or not b_side:
            return False, f"Unknown Cable: {cable}"

        if self.term_a.opposite_cable_end == "A":
            self.logger.log_warning(
                f"Circuit: {self.circuit} -- Warning: Cable ({self.term_a.cable}) has cable ends swapped."
            )
            cable_side = "a_terminations"
        else:
            cable_side = "b_terminations"

        b_side = getattr(cable, cable_side)

        if isinstance(b_side[0], RearPort):
            valid, message = self.check_standard_cables(b_side)
        elif isinstance(b_side[0], Interface):
            return True, f"Direct to Device"
        else:
            return False, f"Invalid Cable Termination Type: {cable} -- {type(b_side[0])}"

        return valid, message

    def standard_check(self):
        """Validate Standard (and Meet Me) Cables"""
        valid, message = self.check_term_site(self.term_a.site)
        if not valid:
            return False, message

        valid, message = self.check_term_provider_network(self.term_z.provider_network)
        if not valid:
            return False, f"Standard -- {message}"

        cable = self.term_a.cable
        if not cable:
            return False, f"Standard -- No Cable found for Termination A."

        valid, message = self.cable_check(cable)

        message = f"Standard -- {message}" if message else "Standard"

        return valid, message

    def p2p_check(self):
        """Validate P2P Cables"""
        for site in (self.term_a.site, self.term_z.site):
            valid, message = self.check_term_site(site)
            if not valid:
                return False, f"P2P -- {message}"

        if self.circuit.type != CircuitType.objects.get(name="P2P (Point to Point)"):
            self.logger.log_warning(
                f"Circuit: {self.circuit} -- Warning: P2P Circuit but Circuit Type is set to: {self.circuit.type}"
            )

        for term in (self.term_a, self.term_z):
            cable = term.cable
            if not cable:
                return False, f"P2P -- No Cable found for Termination {term.term_side}:"
            valid, message = self.cable_check(cable)
            if not valid:
                return valid, f"P2P -- {message}"

        message = f"P2P -- {message}" if message else "P2P"

        return valid, message

    def validate(self, circuit: Circuit, logger: Script = None) -> tuple[bool, str]:
        """Validate Circuit to meet the 'standard'"""
        self.logger = logger
        self.circuit = circuit
        self.term_a = circuit.termination_a
        self.term_z = circuit.termination_z

        if not self.term_a:
            return False, "Invalid -- No Termination A"
        if not self.term_z:
            return False, "Invalid -- No Termination Z"

        if self.term_a.site is not None and self.term_z.site is not None:
            valid, message = self.p2p_check()
        elif self.term_a.site and self.term_z.provider_network:
            valid, message = self.standard_check()
        else:
            return (
                False,
                f"Missing or Invalid Circuit Terminations: {self.circuit} - Termination A: {self.term_a}, - Termination Z: {self.term_z}",
            )

        if valid:
            message = f"Valid -- {message}"
        else:
            message = f"Invalid -- {message}"

        return valid, message
