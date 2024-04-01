import inspect
from dataclasses import dataclass, fields

import local.utils as utils
from circuits.choices import CircuitStatusChoices
from circuits.models import (
    Circuit,
    CircuitTermination,
    CircuitType,
    Provider,
    ProviderNetwork,
)
from dcim.choices import CableTypeChoices, PortTypeChoices
from dcim.models import Cable, Device, FrontPort, Interface, RearPort, Site
from django.core.files.uploadedfile import InMemoryUploadedFile
from extras.scripts import Script
from utilities.exceptions import AbortScript


@dataclass
class NiceCircuit:
    """Parent/Main dataclass representing a circuit in netbox with cabling details"""

    logger: Script
    # Circuit
    cid: str
    description: str
    bun: str
    provider: Provider
    circuit_type: CircuitType
    side_a_site: Site
    side_z_providernetwork: ProviderNetwork
    # Cables (Side A)
    pp: Device
    pp_port: RearPort
    pp_new_port: str
    pp_port_description: str
    pp_info: str
    xconnect_id: str
    device: Device
    interface: Interface
    direct_to_device: bool
    create_pp_port: bool
    # Other
    port_speed: int
    upstream_speed: int
    cir: int
    install_date: str
    review: bool
    comments: str
    # Misc
    allow_skip: bool
    overwrite: bool
    from_csv: bool

    # For now - always defaulted to LC
    # pp_port_type: RearPort = PortTypeChoices.TYPE_LC
    # z_pp_port_type: RearPort = PortTypeChoices.TYPE_LC

    def __post_init__(self, **kwargs) -> None:
        self.pp_port_type = PortTypeChoices.TYPE_LC
        """Validate/Set initial data properly"""
        if self.from_csv:
            NiceCircuit._prepare_circuit_from_csv(self)
        self._validate_data()
        self._set_custom_fields()

    def _set_custom_fields(self) -> None:
        """Set the custom fields in netbox format on this object"""
        self.custom_fields = {
            "bun": self.bun,
            # "bun_folder_range": utils.get_bun_link(self.bun),
            "bun_link": utils.get_bun_link(self.bun) if self.bun else "",
            "review": self.review,
        }

    def _prepare_circuit_from_csv(self) -> None:
        """
        Used to prepare the required data as netbox objects, if it was initially loaded from a CSV
        """

        # Fix bools
        for field in [
            "direct_to_device",
            "allow_skip",
            "review",
            "overwrite",
            "create_pp_port",
        ]:
            value = getattr(self, field)
            setattr(self, field, utils.fix_bools(value))

        self.bun = self.bun if utils.is_four_digit_numeric(self.bun) else ""
        self.cir = self.cir or 0
        self.port_speed = self.port_speed or 0
        self.upstream_speed = self.upstream_speed or 0
        self.provider = utils.get_provider_by_name(self.provider)
        self.circuit_type = utils.get_circuit_type_by_name(name=self.circuit_type)
        self.side_a_site = utils.get_site_by_name(self.side_a_site)
        self.side_z_providernetwork = utils.get_provider_network_by_name(self.side_z_providernetwork)
        self.device = utils.get_device_by_name(name=self.device, site=self.side_a_site)
        self.interface = utils.get_interface_by_name(name=self.interface, device=self.device)
        self.pp = utils.get_device_by_name(name=self.pp, site=self.side_a_site)
        self.pp_port = utils.get_rearport_by_name(name=self.pp_port, device=self.pp)
        self.pp_new_port = utils.validate_pp_new_port(
            port_num=self.pp_new_port, logger=self.logger, skip=self.allow_skip
        )
        self.install_date = utils.validate_date(self.install_date)

    def create_new_pp_port(self, pp: Device, port_num: int, description: str) -> None:
        """
        Create a new Patch Panel Port (Rear & Front)

        Args:
            pp: netbox Device
            port_num: Integer for the new port number
            descriptin: description
        """
        error = False

        rps = RearPort.objects.filter(device=pp)
        for rp in rps:
            if f"Rear{port_num}" in rp.name:
                error = f"Patch Panel RearPort {pp}/{port_num} already exists! Skipping."

        fps = FrontPort.objects.filter(device=pp)
        for fp in fps:
            if f"Front{port_num}" in fp.name:
                error = f"Patch Panel FrontPort {pp}/{port_num} already exists! Skipping."
        if error:
            utils.handle_errors(self.logger.log_failure, error, self.allow_skip)

        # refactor all this into self?
        pp_rearport = utils.create_rearport(
            name=f"Rear{port_num}", type=self.pp_port_type, pp=pp, description=description
        )
        if not pp_rearport:
            return

        utils.save_rearport(self.logger, pp_rearport)

        pp_frontport = utils.create_frontport(
            name=f"Front{port_num}", type=self.pp_port_type, pp=pp, rear_port=pp_rearport, description=description
        )
        if not pp_frontport:
            return

        utils.save_frontport(self.logger, pp_frontport)
        utils.create_extra_pp_ports(
            port_num=port_num, type=self.pp_port_type, pp=pp, logger=self.logger, allow_skip=self.allow_skip
        )

        return pp_rearport

    def _init_patch_panel_properties(self) -> None:
        """
        Initialize any Patch Panel Properties
        Including if there shouldn't be a Patch Panel
        """
        error = False
        if self.pp_new_port and not self.create_pp_port:
            error = f"Cannot create new Patch Panel Port #: {self.pp_new_port} unless \"Create Patch Panel Interface\" is selected."
        elif self.pp_port and self.create_pp_port:
            error = f"Cannot choose an existing Patch Panel Port ({self.pp_port}) AND enable 'Create Patch Panel Port' simultaneously."
        if error:
            utils.handle_errors(self.logger.log_failure, error, self.allow_skip)
            return False

        # Create Patch Panel Port?
        if self.pp_new_port and self.create_pp_port:
            self.pp_port = self.create_new_pp_port(self.pp, self.pp_new_port, self.pp_port_description)

        valid = self._validate_x_cables(
            self.pp,
            self.pp_port,
            self.pp_port_description,
            self.device,
            self.interface,
            self.direct_to_device,
        )
        return valid

    def _validate_data(self) -> None:
        """Validate things"""
        # Validate we have enough information for a circuit
        if not all([self.cid, self.provider, self.circuit_type]):
            error = (
                f"Missing/Not Found Mandatory Value for either: Circuit ID ({self.cid}), "
                f"Provider ({self.provider}), or Circuit Type ({self.circuit_type})"
            )
            raise AbortScript(error)

    def _build_site_termination(self, side: str, site: Site) -> CircuitTermination:
        """
        Builds the site Termination object and returns it (not yet created/saved to the DB)

        Args:
            side: A or Z
            site: netbox Site object

        Returns:
            A netbox CircuitTermination
        """
        xconnect_id = self.xconnect_id if side == "A" else self.z_xconnect_id
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
                xconnect_id=xconnect_id,
            )
        else:
            termination.port_speed = self.port_speed
            termination.upstream_speed = self.upstream_speed
            termination.xconnect_id = self.xconnect_id

        return termination

    def create_site_termination(self, side: str, site: Site) -> CircuitTermination:
        """
        Saves the site Termination to the netbox DB, and returns it

        Args:
            side: A or Z
            site: netbox Site object

        Returns:
            A netbox CircuitTermination
        """
        if isinstance(site, Site):
            termination_x = self._build_site_termination(side, site)

            if not isinstance(termination_x, CircuitTermination):
                error = termination_x
                utils.handle_errors(self.logger.log_warning, error, self.allow_skip)
                return None

            utils.save_terminations(logger=self.logger, termination=termination_x)
        else:
            error = f"CID '{self.cid}': Missing Site for Termination {side}"
            utils.handle_errors(self.logger.log_warning, error, self.allow_skip)
            return None

        return termination_x

    def _build_provider_network_termination(self, side: str, provider_network: ProviderNetwork) -> CircuitTermination:
        """
        Builds the ProviderNetwork Termination object and returns it (not yet created/saved to the DB)

        Args:
            side: A or Z
            provider_network: netbox ProviderNetwork object

        Returns:
            A netbox CircuitTermination
        """
        termination: CircuitTermination = None
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
        """
        Saves the Provider Network Termination to the netbox DB, and returns it

        Args:
            side: A or Z
            provider_network: netbox ProviderNetwork object

        Returns:
            A netbox CircuitTermination
        """
        if isinstance(provider_network, ProviderNetwork):
            termination_x = self._build_provider_network_termination(side, provider_network)

            if not isinstance(termination_x, CircuitTermination):
                error = termination_x
                utils.handle_errors(self.logger.log_failure, error, self.allow_skip)
                return None
            utils.save_terminations(logger=self.logger, termination=termination_x)
        else:
            error = f"CID '{self.cid}': Missing Provider Network for Termination {side.upper()}"
            utils.handle_errors(self.logger.log_failure, error, self.allow_skip)
            return None

        return termination_x

    def _build_circuit(self) -> Circuit:
        """
        Builds the Circuit object and returns it (not yet created/saved to the db)
        """
        return Circuit(
            cid=self.cid,
            provider=self.provider,
            type=self.circuit_type,
            status=CircuitStatusChoices.STATUS_ACTIVE,
            description=self.description,
            commit_rate=self.cir,
            install_date=self.install_date,
            custom_field_data=self.custom_fields,
        )

    def _update_circuit(self, circuit: Circuit) -> Circuit:
        """Update existing Circuit attributes"""
        circuit.type = self.circuit_type
        circuit.status = CircuitStatusChoices.STATUS_ACTIVE
        circuit.description = self.description
        circuit.commit_rate = self.cir
        circuit.install_date = self.install_date
        circuit.custom_field_data = self.custom_fields
        return circuit

    def get_frontport(self, rear_port) -> FrontPort:
        """
        Get FrontPort associated with RearPort

        Args:
            rear_port: The RearPort

        Returns:
            A netbox FrontPort object
        """
        if not isinstance(rear_port, RearPort):
            return None
        if self.pp_port.positions > 1:
            raise AbortScript(f"RearPorts with multiple positions not yet implemented: Device/RearPort: {rear_port.device.name} / {rear_port}")

        return rear_port.frontports.first()

    def _validate_x_cables(
        self,
        pp: Device,
        pp_port: RearPort,
        pp_port_description: str,
        device: Device,
        interface: Interface,
        direct_to_device: bool,
    ) -> None:
        """
        Validate we have what is necessary to create the cables

        Args:
            pp: patch panel
            pp_port: The patch panel RearPort
            pp_port_description: Description for the Front/RearPorts
            device: Typically a switch or router)
            interface: The switch/router Interface
            direct_to_device: bool on whether cable goes through a patch panel or not
        """

        valid = True
        error = False
        if device is None or interface is None:
            error = f"\tCID '{self.cid}': Error: Missing Device ({device}) and/or Interface ({interface})."
        elif direct_to_device and (pp or pp_port):
            error = (
                f"\tCID '{self.cid}': Error: Cable Direct to Device chosen, but Patch Panel ({pp}) was also selected."
            )
        elif not direct_to_device and (pp is None or pp_port is None):
            error = f"\tCID '{self.cid}': Error: Patch Panel or port {pp}/{pp_port} missing, and 'Cable Direct to Device' is not checked."
        # Update Description
        elif isinstance(pp, Device):
            if not pp_port.description and pp_port_description:
                pp_port.description = pp_port_description
                self.get_frontport(pp_port).description = pp_port_description

        if error:
            utils.handle_errors(self.logger.log_failure, error, self.allow_skip)
            valid = False

        return valid

    def _build_device_or_pp_cable(
        self, device_or_pp: Device, interface_or_pp_port: Interface, a_side: FrontPort | CircuitTermination,
    ) -> Cable:
        """
        Builds a Cable from a Device and returns it (not yet created/saved to the db)

        Args:
            device: The device
            interface: The device's Interface
            a_side: The OTHER side of this cable, either a FrontPort or Circuit Termination

        Returns:
            A netbox Cable object
        """
        if not device_or_pp or not interface_or_pp_port:
            error = f"CID '{self.cid}': Unable to create cable to the device for circuit: {self.cid}"
            utils.handle_errors(self.logger.log_failure, error, self.allow_skip)
            return

        if isinstance(a_side, CircuitTermination):
            label = f"({a_side}) <-> ({device_or_pp} / {interface_or_pp_port})"
        elif isinstance(a_side, FrontPort):
            label = f"({self.cid}: {device_or_pp} / {interface_or_pp_port}) <-> ({a_side.device.name} / {(a_side)})"
        else:
            raise AbortScript(f"Unsupported a_side: {a_side}.")

        return Cable(
            a_terminations=[a_side], b_terminations=[interface_or_pp_port], type=CableTypeChoices.TYPE_SMF_OS2, label=label
        )

    def create_standard_cables(
        self,
        pp: Device,
        pp_port: RearPort,
        device: Device,
        interface: Interface,
        termination: CircuitTermination,
        direct_to_device: bool,
    ) -> None:
        """
        Creates ands saves 'standard' cables for most circuit use cases
        """
        if direct_to_device:
            pp_cable = None
            device_side_a = termination
        else:
            pp_cable = self._build_device_or_pp_cable(pp, pp_port, a_side=termination)
            device_side_a = self.get_frontport(pp_port)

        device_cable = self._build_device_or_pp_cable(device, interface, a_side=device_side_a)

        return utils.save_cables(logger=self.logger, allow_skip=self.allow_skip, cables=[pp_cable, device_cable])

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
            error = f"CID '{self.cid}': Error, existing Circuit found!"
            circuit = None
            utils.handle_errors(self.logger.log_failure, error, self.allow_skip)
            return None

        if circuit:
            utils.save_circuit(circuit, self.logger, allow_skip=self.allow_skip)

        return circuit


class NiceBulkCircuits:
    """Entry point for loading a CSV of bulk circuits to create NiceCircuit obects"""

    @classmethod
    def from_csv(cls, logger: Script, overwrite: bool = False, filename="", circuit_num: int = 0):
        """
        Load up circuits from a CSV

        circuit_num: Pull only one circuit out of the CSV (used extensively for tests)
        """
        csv_data = utils.load_data_from_csv(filename=filename)
        circuits = []

        if circuit_num:
            try:
                csv_data = [csv_data[circuit_num - 1]]  # 1 for header, 1 for zero indexing
            except IndexError:
                raise AbortScript(f"Circuit {circuit_num} not found!, Only {len(csv_data)} rows found.")
    
        for row in csv_data:
            # Set initial values
            row["logger"] = logger
            row["from_csv"] = True
            if overwrite:
                row["overwrite"] = overwrite
            elif row["overwrite"]:
                row["overwrite"] = utils.fix_bools(row["overwrite"])

            if row.get("nice_script_type") == "Standard Circuit":
                del row["nice_script_type"]
                try:
                    circuits.append(NiceStandardCircuit.from_csv(**row))
                except TypeError as e:
                    error = "Malformed/Unsupported CSV Columns:\n"
                    error += f"{row}"
                    error += f"\n{e}\n"
                    raise AbortScript(error)

            elif row.get("nice_script_type") == "P2P Circuit":
                del row["nice_script_type"]
                try:
                    circuits.append(NiceP2PCircuit.from_csv(**row))
                except TypeError as e:
                    error = "Malformed/Unsupported CSV Columns:\n"
                    error += f"{row}"
                    error += f"\n{e}\n"
                    raise AbortScript(error)

            elif row.get("nice_script_type") == "MeetMe Circuit":
                del row["nice_script_type"]
                try:
                    circuits.append(NiceMeetMeCircuit.from_csv(**row))
                except TypeError as e:
                    error = "Malformed/Unsupported CSV Columns:\n"
                    error += f"{row}"
                    error += f"\n{e}\n"
                    raise AbortScript(error)
            else:
                raise AbortScript(f"Invalid Script Type: {row.get('nice_script_type')}")
        return circuits


@dataclass
class NiceStandardCircuit(NiceCircuit):
    """
    The Standard NICE Circuit (device <-> patch panel (optional) <-> site <-> provider_network)
    """

    @classmethod
    def from_csv(cls, **kwargs):
        # return cls(**{k: v for k, v in kwargs.items() if k in inspect.signature(cls).parameters})
        field_names = {f.name for f in fields(cls)}
        parameters = inspect.signature(cls).parameters
        return cls(**{k: v for k, v in kwargs.items() if k in field_names and k in parameters})

    def __post_init__(self, **kwargs):
        super().__post_init__()

    def create(self):
        """
        Standard Circuit Creation
        """
        self.logger.log_info(f"Beginning Standard: {self.cid} / {self.description} creation..")
        result = self.create_standard()
        self.logger.log_info(f"Finished {self.cid}.")

        return result

    def create_standard(self, p2p: bool = False) -> None:
        """
        Logic to Create a Standard Circuit
        """
        self.circuit = super().create_circuit()
        if not self.circuit:
            return

        self.termination_a = super().create_site_termination(side="A", site=self.side_a_site)
        if not self.termination_a:
            return

        self.termination_z = super().create_provider_network_termination(
            side="Z", provider_network=self.side_z_providernetwork
        )
        if not self.termination_z:
            return

        success = super()._init_patch_panel_properties()
        if not success:
            return
        success = super().create_standard_cables(
            self.pp, self.pp_port, self.device, self.interface, self.termination_a, self.direct_to_device
        )

        return success


@dataclass
class NiceP2PCircuit(NiceCircuit):
    """
    P2P NICE Circuit (device <-> patch panel (optional) <-> site <-> site <-> patch panel (optional) <-> device)
    """

    # Cables (Side Z)
    side_z_site: Site
    z_pp: Device
    z_pp_port: RearPort
    z_pp_port_description: str
    z_pp_new_port: bool
    z_pp_info: str
    z_xconnect_id: str
    z_device: Device
    z_interface: Interface
    z_direct_to_device: bool
    z_create_pp_port: bool

    @classmethod
    def from_csv(cls, **kwargs):
        return cls(**{k: v for k, v in kwargs.items() if k in inspect.signature(cls).parameters})

    def __post_init__(self):
        super().__post_init__()
        if self.from_csv:
            self._prepare_circuit_from_csv()
        self._validate_p2p_data()

    def _validate_p2p_data(self):
        # Validate sites are unique
        if self.side_a_site == self.side_z_site:
            error = f"Cannot terminate {self.side_a_site} to {self.side_z_site}"
            raise AbortScript(error)

    def _prepare_circuit_from_csv(self) -> None:
        """
        Used to prepare the required data as netbox objects, if it was initially loaded from a CSV
        """

        # Fix bools
        for field in [
            "z_direct_to_device",
            "z_create_pp_port",
        ]:
            value = getattr(self, field)
            setattr(self, field, utils.fix_bools(value))

        # P2P
        self.side_z_site = utils.get_site_by_name(self.side_z_site)  # P2P
        self.z_device = utils.get_device_by_name(name=self.z_device, site=self.side_z_site)
        self.z_interface = utils.get_interface_by_name(name=self.z_interface, device=self.z_device)
        self.z_pp = utils.get_device_by_name(name=self.z_pp, site=self.side_z_site)
        self.z_pp_port = utils.get_rearport_by_name(name=self.z_pp_port, device=self.z_pp)
        self.z_pp_new_port = utils.validate_pp_new_port(
            port_num=self.z_pp_new_port, logger=self.logger, skip=self.allow_skip
        )

    def _init_patch_panel_properties(self) -> None:
        """
        Initialize any Patch Panel Properties
        Including if there shouldn't be a Patch Panel
        """
        valid = super()._init_patch_panel_properties()
        if not valid:
            return
        error = False
        if self.z_pp_new_port and not self.z_create_pp_port:
            error = f"Cannot create new Patch Panel Port #: {self.pp_new_port} unless \"Create Patch Panel Interface\" is selected."
        elif self.z_pp_port and self.z_create_pp_port:
            error = f"Cannot choose an existing Patch Panel Port ({self.z_pp_port} AND enable 'Create Patch Panel Port' simultaneously."
        if error:
            utils.handle_errors(self.logger.log_failure, error, self.allow_skip)

        # Create Patch Panel Port?
        if self.z_pp_new_port and self.z_create_pp_port:
            self.z_pp_port = self.create_new_pp_port(self.z_pp, self.z_pp_new_port, self.z_pp_port_description)

        valid = super()._validate_x_cables(
            self.z_pp,
            self.z_pp_port,
            self.z_pp_port_description,
            self.z_device,
            self.z_interface,
            self.z_direct_to_device,
        )

        return valid

    def create(self):
        self.logger.log_info(f"Beginning P2P: {self.cid} / {self.description} creation..")
        result = self.create_p2p()
        self.logger.log_info(f"Finished {self.cid}.")

        return result

    def create_p2p(self) -> None:
        """
        Logic to Create a Point-to-Point Circuit
        """
        self.circuit = super().create_circuit()
        if not self.circuit:
            return

        self.termination_a = super().create_site_termination(side="A", site=self.side_a_site)
        if not self.termination_a:
            return

        self.termination_z = super().create_site_termination(side="Z", site=self.side_z_site)
        if not self.termination_z:
            return

        success = self._init_patch_panel_properties()
        if not success:
            return
        success = super().create_standard_cables(
            self.pp, self.pp_port, self.device, self.interface, self.termination_a, self.direct_to_device
        )
        if not success:
            return
        success = super().create_standard_cables(
            self.z_pp, self.z_pp_port, self.z_device, self.z_interface, self.termination_z, self.z_direct_to_device
        )

        return success


@dataclass
class NiceMeetMeCircuit(NiceCircuit):
    """
    Meet Me NICE Circuit (device <-> patch panel <-> patch panel <-> site <-> provider_network)
    """

    # Cables (Extra PP (closest to circuit))
    mm_pp: Device
    mm_pp_port: RearPort
    mm_pp_port_description: str
    mm_pp_new_port: bool
    mm_pp_info: str
    mm_xconnect_id: str
    mm_create_pp_port: bool

    @classmethod
    def from_csv(cls, **kwargs):
        return cls(**{k: v for k, v in kwargs.items() if k in inspect.signature(cls).parameters})

    def __post_init__(self):
        super().__post_init__()
        if self.from_csv:
            self._prepare_circuit_from_csv()
        self._validate_meet_me_data()

    def _validate_meet_me_data(self):
        return True

    def _prepare_circuit_from_csv(self) -> None:
        """
        Used to prepare the required data as netbox objects, if it was initially loaded from a CSV
        """
        # Fix bools
        for field in [
            "mm_create_pp_port",
        ]:
            value = getattr(self, field)
            setattr(self, field, utils.fix_bools(value))

        # Meet Me
        self.mm_pp = utils.get_device_by_name(name=self.mm_pp, site=self.side_a_site)
        self.mm_pp_port = utils.get_rearport_by_name(name=self.mm_pp_port, device=self.mm_pp)
        self.mm_pp_new_port = utils.validate_pp_new_port(
            port_num=self.mm_pp_new_port, logger=self.logger, skip=self.allow_skip
        )

    def create(self):
        self.logger.log_info(f"Beginning Meet Me: {self.cid} / {self.description} creation..")
        result = self.create_meet_me()
        self.logger.log_info(f"Finished {self.cid}.")

        return result

    def create_meet_me(self) -> None:
        self.circuit = super().create_circuit()
        if not self.circuit:
            return

        self.termination_a = super().create_site_termination(side="A", site=self.side_a_site)
        if not self.termination_a:
            return

        self.termination_z = super().create_provider_network_termination(
            side="Z", provider_network=self.side_z_providernetwork
        )
        if not self.termination_z:
            return

        success = super()._init_patch_panel_properties()
        if not success:
            return

        # Circuit Side A Cable
        pp_cable = super()._build_device_or_pp_cable(
            self.mm_pp, self.mm_pp_port, a_side=self.termination_a
        )

        # Meet Me Cable
        mm_frontport = self.get_frontport(self.mm_pp_port)
        mm_to_pp_cable = super()._build_device_or_pp_cable(self.pp, self.pp_port, a_side=mm_frontport)

        # Device Cable
        pp_frontport = self.get_frontport(self.pp_port)
        device_cable = self._build_device_or_pp_cable(self.device, self.interface, a_side=pp_frontport)

        success = utils.save_cables(
            logger=self.logger, allow_skip=self.allow_skip, cables=[device_cable, mm_to_pp_cable, pp_cable]
        )

        return success
