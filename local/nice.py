import csv
from dataclasses import dataclass

from django.core.files.uploadedfile import InMemoryUploadedFile

from circuits.choices import CircuitStatusChoices
from circuits.models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork
from dcim.choices import CableTypeChoices
from dcim.models import Cable, Device, FrontPort, Interface, RearPort, Site
from extras.scripts import Script
from utilities.exceptions import AbortScript

import local.utils as utils


@dataclass
class NiceCircuit:
    logger: Script
    cid: str
    provider: Provider
    circuit_type: CircuitType
    side_a_site: Site
    side_z_providernetwork: ProviderNetwork
    description: str
    install_date: str
    termination_date: str
    cir: int
    comments: str
    device: Device
    interface: Interface
    cable_type: str = ""
    xconnect_id: str = ""
    port_speed: int = 0
    upstream_speed: int = 0
    pp_info: str = ""

    pp: Device = None
    pp_port: RearPort = None
    pp_new_port: str = ""  # IMPLEMENT
    create_pp_port: bool = False  # IMPLEMENT

    cable_direct_to_device: bool = False
    allow_cable_skip: bool = False
    overwrite: bool = False
    review: bool = False

    from_csv: bool = False
    side_a_providernetwork: ProviderNetwork = None
    side_z_site: Site = None
    z_pp: Device = None
    z_pp_port: RearPort = None
    z_device: Device = None
    z_interface: Interface = None
    overwrite: bool = False

    def __post_init__(self):
        if self.from_csv:
            self._prepare_circuit_from_csv()
        self._validate_data()
        if not self.cir:
            self.cir = 0
        if not self.port_speed:
            self.port_speed = 0
        if not self.upstream_speed:
            self.upstream_speed = 0
        self._set_custom_fields()

    def _set_custom_fields(self):
        self.custom_fields = {
            "review": self.review,
        }

    def _fix_bools(self, value) -> None:
        if isinstance(value, bool):
            return value
        return value.lower() == "true"

    def _prepare_circuit_from_csv(self) -> None:
        """
        Used to prepare netbox objects, if loaded from a CSV originally
        """
        for field in ["cable_direct_to_device", "allow_cable_skip", "review", "overwrite"]:
            value = getattr(self, field)
            setattr(self, field, self._fix_bools(value))

        self.provider = utils.get_provider_by_name(self.provider)
        self.circuit_type = utils.get_circuit_type_by_name(name=self.circuit_type)
        self.side_a_site = utils.get_site_by_name(self.side_a_site)
        # self.side_a_providernetwork = utils.get_provider_network_by_name(self.side_a_providernetwork) -- never needed?
        self.side_z_site = utils.get_site_by_name(self.side_z_site)  # P2P
        self.side_z_providernetwork = utils.get_provider_network_by_name(self.side_z_providernetwork)
        self.device = utils.get_device_by_name(name=self.device, site=self.side_a_site)
        self.interface = utils.get_interface_by_name(name=self.interface, device=self.device)
        self.pp = utils.get_device_by_name(name=self.pp, site=self.side_a_site)
        self.pp_port = utils.get_rearport_by_name(name=self.pp_port, device=self.pp)
        self.install_date = utils.validate_date(self.install_date)
        self.termination_date = utils.validate_date(self.termination_date)

        # P2P
        self.z_device = utils.get_device_by_name(name=self.z_device, site=self.side_z_site)
        self.z_interface = utils.get_interface_by_name(name=self.z_interface, device=self.z_device)
        self.z_pp = utils.get_device_by_name(name=self.z_pp, site=self.side_z_site)
        self.z_pp_port = utils.get_rearport_by_name(name=self.z_pp_port, device=self.z_pp)

    def _validate_data(self) -> None:
        error = False
        if not all([self.cid, self.provider, self.circuit_type]):
            error = (
                f"Missing/Not Found Mandatory Value for either: Circuit ID ({self.cid}), "
                f"Provider ({self.provider}), or Circuit Type ({self.circuit_type})"
            )

        if error:
            raise AbortScript(error)

    def _build_site_termination(self, side: str, site: Site) -> CircuitTermination:
        termination = None
        existing = self.circuit.terminations.all()
        if len(existing) > 0:
            for term in existing:
                if term.term_side == side.upper():
                    if term.site != site:
                        return f"CID {self.cid}: Cannot change existing termination{side.upper()} to new Site"
                    else:
                        if self.overwrite:
                            termination = term
        if not termination:
            termination = CircuitTermination(
                term_side=side.upper(),
                site=site,
                circuit=self.circuit,
                port_speed=self.port_speed,
                upstream_speed=self.upstream_speed,
                xconnect_id=self.xconnect_id,
            )
        else:
            termination.port_speed = self.port_speed
            termination.upstream_speed = self.upstream_speed
            termination.xconnect_id = self.xconnect_id

        return termination

    def create_site_termination(self, side: str, site: Site):
        if isinstance(site, Site):
            termination_x = self._build_site_termination(side, site)

            if not isinstance(termination_x, CircuitTermination):
                error = termination_x
                utils.handle_errors(self.logger.log_warning, error, self.allow_cable_skip)
                return None

            utils.save_terminations(logger=self.logger, termination=termination_x)
        else:
            error = f"CID '{self.cid}': Missing Site for Termination {side}"
            utils.handle_errors(self.logger.log_warning, error, self.allow_cable_skip)
            return None

        return termination_x

    def _build_provider_network_termination(self, side: str, provider_network: ProviderNetwork) -> CircuitTermination:
        termination = None
        existing = self.circuit.terminations.all()
        if len(existing) > 0:
            for term in existing:
                if term.term_side == side.upper():
                    if term.provider_network != provider_network:
                        return f"CID {self.cid}: Cannot change existing termination {side.upper()} to new Provider"
                    else:
                        if self.overwrite:
                            termination = term
        if not termination:
            termination = CircuitTermination(
                term_side=side.upper(),
                provider_network=provider_network,
                circuit=self.circuit,
                port_speed=self.port_speed,
                upstream_speed=self.upstream_speed,
                xconnect_id=self.xconnect_id,
            )
        else:
            termination.port_speed = self.port_speed
            termination.upstream_speed = self.upstream_speed
            termination.xconnect_id = self.xconnect_id

        return termination

    def create_provider_network_termination(self, side: str, provider_network: ProviderNetwork) -> CircuitTermination:
        if isinstance(provider_network, ProviderNetwork):
            termination_x = self._build_provider_network_termination(side, provider_network)

            if not isinstance(termination_x, CircuitTermination):
                error = termination_x
                utils.handle_errors(self.logger.log_failure, error, self.allow_cable_skip)
                return None
            utils.save_terminations(logger=self.logger, termination=termination_x)
        else:
            error = f"CID '{self.cid}': Missing Provider Network for Termination {side.upper()}"
            utils.handle_errors(self.logger.log_failure, error, self.allow_cable_skip)
            return None

        return termination_x

    def _build_circuit(self) -> Circuit:
        return Circuit(
            cid=self.cid,
            provider=self.provider,
            type=self.circuit_type,
            status=CircuitStatusChoices.STATUS_ACTIVE,
            description=self.description,
            commit_rate=self.cir,
            install_date=self.install_date,
            termination_date=self.termination_date,
            custom_field_data=self.custom_fields,
        )

    def _update_circuit(self, circuit: Circuit) -> Circuit:
        circuit.type = self.circuit_type
        circuit.status = CircuitStatusChoices.STATUS_ACTIVE
        circuit.description = self.description
        circuit.commit_rate = self.cir
        circuit.install_date = self.install_date
        circuit.termination_date = self.termination_date
        circuit.custom_field_data = self.custom_fields
        return circuit

    def get_frontport(self, rear_port) -> FrontPort:
        """
        Get FrontPort associated with RearPort
        """
        if not isinstance(rear_port, RearPort):
            return None
        if self.pp_port.positions > 1:
            raise AbortScript(f"RearPorts with multiple positions not yet implemented: RearPort: {rear_port}")

        return rear_port.frontports.first()

    def _validate_x_cables(self, pp: Device, pp_port: RearPort, device: Device, interface: Interface) -> None:
        """
        Validate we have what is necessary to create the cables
        """
        valid = True
        error = False
        if device is None or interface is None:
            error = f"\tCID '{self.cid}': Error: Missing Device and/or Interface."
        elif self.cable_direct_to_device and (pp or pp_port):
            error = f"\tCID '{self.cid}': Error: Cable Direct to Device chosen, but Patch Panel also Selected."
        elif not self.cable_direct_to_device and (pp is None or pp_port is None):
            error = f"\tCID '{self.cid}': Error: Patch Panel (or port) missing, and 'Cable Direct to Device' is not checked."

        if error:
            utils.handle_errors(self.logger.log_failure, error, self.allow_cable_skip)
            valid = False
        
        return valid

    def _build_device_x_cable(
        self, device: Device, interface: Interface, a_side: FrontPort | CircuitTermination, a_side_label: str
    ) -> Cable:
        if not device or not interface:
            error = f"CID '{self.cid}': Unable to create cable to the device for circuit: {self.cid}"
            utils.handle_errors(self.logger.log_failure, error, self.allow_cable_skip)
            return

        label = f"{self.cid}: {self.device}/{self.interface} <-> {a_side_label}"

        return Cable(
            a_terminations=[a_side], b_terminations=[self.interface], type=CableTypeChoices.TYPE_SMF_OS2, label=label
        )

    def _build_pp_x_cable(self, pp: Device, pp_port: RearPort, a_side: CircuitTermination | Interface):
        """
        Build Patch Panel Cable
        """
        if self.cable_direct_to_device:
            return None

        if not pp or not pp_port:
            error = f"CID '{self.cid}': Unable to create cable to Patch Panel for circuit: {self.cid}"
            utils.handle_errors(self.logger.log_failure, error, self.allow_cable_skip)

        label = f"{self.cid}: {pp}/{pp_port} <-> {a_side}"

        return Cable(
            a_terminations=[a_side],
            b_terminations=[self.pp_port],
            type=CableTypeChoices.TYPE_SMF_OS2,
            label=label,
        )

    def create_standard_cables(self, pp: Device, pp_port: RearPort, device: Device, interface: Interface):
        valid = self._validate_x_cables(pp, pp_port, device, interface)
        if not valid:
            return

        pp_cable = self._build_pp_x_cable(pp, pp_port, a_side=self.termination_a)  # CREATE A VAR?!

        if self.cable_direct_to_device:
            device_side_a = self.termination_a
            label = f"{self.termination_a}"
        else:
            device_side_a = self.get_frontport(pp_port)
            label = f"{self.pp}/{self.get_frontport(pp_port)}"

        device_cable = self._build_device_x_cable(device, interface, a_side=device_side_a, a_side_label=label)

        utils.save_cables(
            logger=self.logger, allow_cable_skip=self.allow_cable_skip, cables=[pp_cable, device_cable]
        )

    def create_circuit(self) -> Circuit:
        """
        Create & Save Netbox Circuit
        """
        duplicate = utils.check_circuit_duplicate(self.cid, self.provider)
        if not duplicate:
            circuit = self._build_circuit()
        elif duplicate and self.overwrite:
            self.logger.log_warning(
                f"CID '{self.cid}': Overwrites enabled, updating existing circuit! See change log for original values."
            )
            # Updating existing circuit, create snapshot (change log)
            circuit = Circuit.objects.get(cid=self.cid, provider__name=self.provider)
            if circuit.pk and hasattr(circuit, "snapshot"):
                circuit.snapshot()

            circuit = self._update_circuit(circuit)
        else:
            error = f"CID '{self.cid}': Error, existing Circuit found and overwrites are disabled"
            circuit = None
            utils.handle_errors(self.logger.log_failure, error, self.allow_cable_skip)
            return None

        if circuit:
            utils.save_circuit(circuit, self.logger, allow_cable_skip=self.allow_cable_skip)

        return circuit

    def create_standard(self) -> None:
        self.circuit = self.create_circuit()
        if not self.circuit:
            return

        self.termination_a = self.create_site_termination(side="A", site=self.side_a_site)
        if not self.termination_a:
            return

        self.termination_z = self.create_provider_network_termination(
            side="Z", provider_network=self.side_z_providernetwork
        )
        if not self.termination_z:
            return

        self.create_standard_cables(self.pp, self.pp_port, self.device, self.interface)
        self.logger.log_info(f"Finished {self.cid}.")

    def create_p2p(self) -> None:
        self.circuit = self.create_circuit()
        if not self.circuit:
            return

        self.termination_a = self.create_site_termination(side="A", site=self.side_a_site)
        if not self.termination_a:
            return

        self.termination_z = self.create_provider_network_termination(
            side="Z", provider_network=self.side_z_providernetwork
        )
        if not self.termination_z:
            return

        self.create_standard_cables(self.pp, self.pp_port, self.device, self.interface)
        self.logger.log_info(f"Finished {self.cid}.")

@dataclass
class NiceBulkCircuits(NiceCircuit):

    @classmethod
    def from_csv(cls, logger: Script, overwrite: bool = False, filename="", circuit_num: int = 0):
        """
        Load up circuits from a CSV

        circuit_num: Pull only one circuit out of the CSV (used extensively for tests)
        """
        csv_data = utils.load_data_from_csv(filename=filename)
        circuits = []

        if circuit_num:
            csv_data = [csv_data[circuit_num - 1]]
        for row in csv_data:
            # Set initial values
            row["logger"] = logger
            row["from_csv"] = True
            if not row["overwrite"]:
                if overwrite:
                    row["overwrite"] = "True"

            if row.get("nice_script_type") == "Standard Circuit":
                del row["nice_script_type"]
                try:
                    circuits.append(NiceStandardCircuit(**row))
                except TypeError as e:
                    error = "Malformed/Unsupported CSV Columns:\n"
                    error += f"{row}"
                    error += f"\n{e}\n"
                    raise AbortScript(error)
            elif row.get("nice_script_type") == "P2P Circuit":
                del row["nice_script_type"]
                try:
                    circuits.append(NiceP2PCircuit(**row))
                except TypeError as e:
                    error = "Malformed/Unsupported CSV Columns:\n"
                    error += f"{row}"
                    error += f"\n{e}\n"
                    raise AbortScript(error)
        return circuits


@dataclass
class NiceStandardCircuit(NiceCircuit):
    """
    The Standard NICE Circuit (device <-> patch panel (optional) <-> site <-> provider_network)
    """

    def __post_init__(self):
        super().__post_init__()

    def create(self):
        """
        Standard Circuit Creation
        """
        self.logger.log_info(f"Beginning P2P {self.cid} creation..")
        super().create_standard()


@dataclass
class NiceP2PCircuit(NiceCircuit):
    """
    P2P NICE Circuit (device <-> patch panel (optional) <-> site <-> site <-> patch panel (optional) <-> device)
    """

    def __post_init__(self):
        super().__post_init__()

    def create(self):
        self.logger.log_info(f"Beginning P2P {self.cid} creation..")
        super().create_standard()


