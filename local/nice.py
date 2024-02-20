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

    from_csv: bool = False
    side_a_providernetwork: ProviderNetwork = None
    side_z_site: Site = None
    pp_z: Device = None
    pp_z_port: RearPort = None
    device_z: Device = None
    interface_z: Interface = None
    overwrite: bool = False


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
        return circuits


@dataclass
class NiceStandardCircuit(NiceCircuit):
    pp: Device = None
    pp_port: RearPort = None
    pp_new_port: str = ""  # IMPLEMENT
    create_pp_port: bool = False  # IMPLEMENT

    cable_direct_to_device: bool = False
    allow_cable_skip: bool = False
    overwrite: bool = False
    review: bool = False

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
        self.side_z_providernetwork = utils.get_provider_network_by_name(self.side_z_providernetwork)
        self.device = utils.get_device_by_name(name=self.device, site=self.side_a_site)
        self.interface = utils.get_interface_by_name(name=self.interface, device=self.device)
        self.pp = utils.get_device_by_name(name=self.pp, site=self.side_a_site)
        self.pp_port = utils.get_rearport_by_name(name=self.pp_port, device=self.pp)

        self.install_date = utils.validate_date(self.install_date)
        self.termination_date = utils.validate_date(self.termination_date)

    def _validate_data(self) -> None:
        error = False
        if not all([self.cid, self.provider, self.circuit_type]):
            error = (
                f"Missing/Not Found Mandatory Value for either: Circuit ID ({self.cid}), "
                f"Provider ({self.provider}), or Circuit Type ({self.circuit_type})"
            )

        if error:
            raise AbortScript(error)

    def _set_custom_fields(self):
        self.custom_fields = {
            "review": self.review,
        }

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

    def _validate_cables(self) -> None:
        """
        Validate we have what is necessary to create the cables
        """
        error = False
        if self.device is None or self.interface is None:
            error = f"\tCID '{self.cid}': Error: Missing Device and/or Interface."
        elif self.cable_direct_to_device and (self.pp or self.pp_port):
            error = f"\tCID '{self.cid}': Error: Cable Direct to Device chosen, but Patch Panel also Selected."
        elif not self.cable_direct_to_device and (self.pp is None or self.pp_port is None):
            error = f"\tCID '{self.cid}': Error: Patch Panel (or port) missing, and 'Cable Direct to Device' is not checked."

        if error:
            return error

    def _build_termination_a(self) -> CircuitTermination:
        termination = None
        existing = self.circuit.terminations.all()
        if len(existing) > 0:
            for term in existing:
                if term.term_side == "A":
                    if term.site != self.side_a_site:
                        return f"CID {self.cid}: Cannot change existing termination A to new Site, skipping."
                    else:
                        if self.overwrite:
                            termination = term
        if not termination:
            termination = CircuitTermination(
                term_side="A",
                site=self.side_a_site,
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

    def _build_termination_z(self) -> CircuitTermination:
        termination = None
        existing = self.circuit.terminations.all()
        if len(existing) > 0:
            for term in existing:
                if term.term_side == "Z":
                    if term.provider_network != self.side_z_providernetwork:
                        return f"CID {self.cid}: Cannot change existing termination Z to new Provider, skipping."
                    else:
                        if self.overwrite:
                            termination = term
        if not termination:
            termination = CircuitTermination(
                term_side="Z",
                provider_network=self.side_z_providernetwork,
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

    @property
    def pp_frontport(self) -> FrontPort:
        """
        Get FrontPort associated with RearPort
        """
        if not isinstance(self.pp_port, RearPort):
            return None
        if self.pp_port.positions > 1:
            raise AbortScript(f"RearPorts with multiple positions not yet implemented: RearPort: {self.pp_port}")

        return self.pp_port.frontports.first()

    def _build_device_cable(self) -> Cable:
        if not self.device or not self.interface:
            error = f"CID '{self.cid}': Unable to create cable to the device for circuit: {self.cid}"
            utils.handle_errors(self.logger.log_failure, error, self.allow_cable_skip)
            return

        if self.cable_direct_to_device:
            side_a = self.termination_a  # Site
            label = f"{self.cid}: {self.device}/{self.interface} <-> {self.termination_a}"
        else:
            side_a = self.pp_frontport
            label = f"{self.cid}: {self.device}/{self.interface} <-> {self.pp}/{self.pp_frontport}"

        return Cable(
            a_terminations=[side_a], b_terminations=[self.interface], type=CableTypeChoices.TYPE_SMF_OS2, label=label
        )

    def _build_pp_cable(self):
        """
        Build Patch Panel Cable
        """
        if self.cable_direct_to_device:
            return None

        if not all([self.pp, self.pp_port, self.pp_frontport]):
            error = f"CID '{self.cid}': Unable to create cable to Patch Panel for circuit: {self.cid}"
            if self.allow_cable_skip:
                self.logger.log_warning(error)
                return None
            else:
                raise AbortScript(error)

        label = f"{self.cid}: {self.pp}/{self.pp_port} <-> {self.termination_a}"

        return Cable(
            a_terminations=[self.termination_a],
            b_terminations=[self.pp_port],
            type=CableTypeChoices.TYPE_SMF_OS2,
            label=label,
        )

    def create_circuit(self) -> Circuit:
        """
        Create & Save Netbox Circuit
        """
        duplicate = utils.check_circuit_duplicate(self.cid, self.provider)
        if not duplicate:  # No duplicate
            self.circuit = self._build_circuit()
        elif duplicate and self.overwrite:
            self.logger.log_warning(
                f"CID '{self.cid}': Overwrites enabled, updating existing circuit! See change log for original values."
            )
            # Updating existing circuit, create snapshot (change log)
            self.circuit = Circuit.objects.get(cid=self.cid, provider__name=self.provider)
            if self.circuit.pk and hasattr(self.circuit, "snapshot"):
                self.circuit.snapshot()

            self.circuit = self._update_circuit(self.circuit)
        else:  # don't overwrite
            error = f"CID '{self.cid}': Error, existing Circuit found and overwrites are disabled"
            self.circuit = None
            utils.handle_errors(self.logger.log_failure, error, self.allow_cable_skip)

        if self.circuit:
            try:
                utils.save_circuit(self.circuit, self.logger, allow_cable_skip=self.allow_cable_skip)
            except AbortScript as e:
                if self.allow_cable_skip:
                    return e
                else:
                    raise AbortScript(e)

    def create_termination_a(self):
        if isinstance(self.side_a_site, Site):
            self.termination_a = self._build_termination_a()

            if not isinstance(self.termination_a, CircuitTermination):
                return self.termination_a  # Error
            utils.save_terminations(logger=self.logger, termination=self.termination_a)
        else:
            error = f"CID '{self.cid}': Missing Site for Termination A"
            self.termination_a = None
            utils.handle_errors(self.logger.log_warning, error, self.allow_cable_skip)
            return error

    def create_termination_z(self):
        if isinstance(self.side_z_providernetwork, ProviderNetwork):
            self.termination_z = self._build_termination_z()

            if not isinstance(self.termination_z, CircuitTermination):
                return self.termination_z  # Error
            utils.save_terminations(logger=self.logger, termination=self.termination_z)
        else:
            self.termination_z = None
            error = f"CID '{self.cid}': Missing Provider Network for Termination Z"
            return error

    def create_cables(self):
        error = self._validate_cables()
        if error:
            utils.handle_errors(self.logger.log_failure, error, self.allow_cable_skip)
            return

        self.pp_cable = self._build_pp_cable()
        self.device_cable = self._build_device_cable()

        error = utils.save_cables(
            logger=self.logger, allow_cable_skip=self.allow_cable_skip, cables=[self.pp_cable, self.device_cable]
        )
        if error:
            utils.handle_errors(self.logger.log_failure, error, self.allow_cable_skip)
            return error

    def create(self):
        self.logger.log_info(f"Beginning {self.cid} creation..")

        error = self.create_circuit()
        if error:
            utils.handle_errors(self.logger.log_failure, error, self.allow_cable_skip)
            return

        error = self.create_termination_a()
        if error:
            utils.handle_errors(self.logger.log_warning, error, self.allow_cable_skip)
            return

        error = self.create_termination_z()
        if error:
            utils.handle_errors(self.logger.log_warning, error, self.allow_cable_skip)
            return

        error = self.create_cables()
        if error:
            print(error)
            self.logger.log_info(error)
            utils.handle_errors(self.logger.log_warning, error, self.allow_cable_skip)

        self.logger.log_info(f"Finished {self.cid}.")

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
        self.install_date = utils.validate_date(self.install_date)
        self.termination_date = utils.validate_date(self.termination_date)
        self._set_custom_fields()


@dataclass
class NiceP2PCircuit:
    def __post_init__(self):
        ...
