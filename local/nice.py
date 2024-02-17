from dataclasses import dataclass

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

    side_a_providernetwork: ProviderNetwork = None
    side_z_site: Site = None
    pp_z: Device = None
    pp_z_port: RearPort = None
    device_z: Device = None
    interface_z: Interface = None

@dataclass
class NiceBulkCircuits(NiceCircuit):

    @classmethod
    def from_csv(self, logger: Script, filename):
        circuits = []
        try:
            with open(filename, "rb") as f:
                csv_data = utils.load_data_from_csv(csv_file=f)
        except FileNotFoundError:
            raise AbortScript(f"File '{filename}' not found!")
        circuits = []
        
        for row in csv_data:
            row["logger"] = logger
            if row.get("nice_script_type") == "Standard Circuit":
                del row["nice_script_type"]
                try:
                    circuits.append(NiceStandardCircuit(**row))
                except TypeError as e:
                    error = "Malformed/Unsupported CSV Columns:\n"
                    error += f"{row}"
                    error += f"\n{e}\n"
                    print(error)
                    print(dir(e))
                    #print(f"{csv_data=}")
            # self.logger.log_failure(error)
            # self.logger.log_failure(f"{csv_data=}")
        return circuits
    
        # allow_cable_skip: row.get("allow_cable_skip"),
        # overwrite: row.get("overwrite"),
        # cable_direct_to_device: row.get("cable_direct_to_device"),
        # cid: row["cid"],
        # provider: row["provider"],
        # type: row["type"],
        # description: row["description"],
        # install_date: row["install_date"],
        # termination_date: row["termination_date"],
        # cir: row["cir"] if row["cir"] else None,
        # comments: row["comments"],
        # side_a: side_a,
        # device: device,
        # interface: interface,
        # pp: pp,
        # pp_port: pp_port,
        # pp_frontport: pp_frontport,

@dataclass
class NiceStandardCircuit(NiceCircuit):
    # logger: Script
    # cid: str
    # provider: Provider
    # circuit_type: CircuitType
    # side_a_site: Site
    # side_z_providernetwork: ProviderNetwork
    # description: str
    # install_date: str
    # termination_date: str
    # cir: int
    # comments: str
    # device: Device
    # interface: Interface
    # xconnect_id: str = ""
    # port_speed: int = 0
    # upstream_speed: int = 0
    # pp_info: str = ""
    pp: Device = None
    pp_port: RearPort = None
    pp_new_port: str = ""  # IMPLEMENT
    create_pp_port: bool = False  # IMPLEMENT

    cable_direct_to_device: bool = False
    allow_cable_skip: bool = False
    overwrite: bool = False

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
        )

    def _update_circuit(self, circuit: Circuit) -> Circuit:
        circuit.type = self.circuit_type
        circuit.status = (CircuitStatusChoices.STATUS_ACTIVE,)
        circuit.description = (self.description,)
        circuit.commit_rate = (self.cir,)
        circuit.install_date = (self.install_date,)
        circuit.termination_date = self.termination_date
        return circuit

    def _validate_cables(self) -> None:
        """
        Validate we have what is necessary to create the cables
        """
        error = False

        if self.cable_direct_to_device and (self.pp or self.pp_port):
            error = f"Error: Cable Direct to Device chosen, but Patch Panel also Selected."
        elif not self.cable_direct_to_device and (not self.pp or not self.pp_port):
            error = f"Error: Patch Panel missing, and 'Cable Direct to Device' is not checked."
            error += f"\n{self.pp=}\t{self.pp_port=}\t{self.cable_direct_to_device=}"

        if error:
            if self.allow_cable_skip:
                self.logger.log_warning(error)
            else:
                raise AbortScript(error)

    def _build_termination_a(self) -> CircuitTermination:
        return CircuitTermination(
            term_side="A",
            site=self.side_a_site,
            circuit=self.circuit,
            port_speed=self.port_speed,
            upstream_speed=self.upstream_speed,
            xconnect_id=self.xconnect_id,
        )

    def _build_termination_z(self) -> CircuitTermination:
        return CircuitTermination(
            term_side="Z",
            provider_network=self.side_z_providernetwork,
            circuit=self.circuit,
            port_speed=self.port_speed,
            upstream_speed=self.upstream_speed,
            xconnect_id=self.xconnect_id,
        )

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
            error = f"Unable to create cable to the device for circuit: {self.cid}"
            if self.allow_cable_skip:
                self.logger.log_warning(error)
                return None
            else:
                raise AbortScript(error)

        if self.cable_direct_to_device:
            side_a = self.termination_a # Site
        else:
            side_a = self.pp_frontport 

        label = f"{self.cid}: {self.interface} <-> {side_a}"
        return Cable(a_terminations=[side_a], b_terminations=[self.interface], type=CableTypeChoices.TYPE_SMF_OS2, label=label)

    def _build_pp_cable(self):
        if not self.pp or not self.pp_port or not self.pp_frontport:
            error = f"Unable to create cable to Patch Panel for circuit: {self.cid}"
            if self.allow_cable_skip:
                self.logger.log_warning(error)
                return None
            else:
                raise AbortScript(error)

        if self.cable_direct_to_device:
            return None

        label = f"{self.cid}: {self.pp_port} <-> {self.termination_a}"
        return Cable(a_terminations=[self.termination_a], b_terminations=[self.pp_port], type=CableTypeChoices.TYPE_SMF_OS2, label=label)
        pp_cable = utils.build_cable(self.logger, side_a=self.termination_a, side_b=self.pp_port, label=label)
        self.logger.log_info(f"Built Cable to Patch Panel for {self.cid}")
        return pp_cable

    def create_circuit(self) -> Circuit:
        """
        Create & Save Netbox Circuit
        """
        duplicate = utils.check_circuit_duplicate(self.cid, self.provider)
        if not duplicate:  # No duplicate
            self.circuit = self._build_circuit()
        elif duplicate and self.overwrite:
            self.logger.log_warning(
                f"Overwrites enabled, updating existing circuit: {self.cid} ! See change log for original values."
            )
            # Updating existing circuit, create snapshot (change log)
            self.circuit = Circuit.objects.get(cid=self.cid, provider__name=self.provider)
            if self.circuit.pk and hasattr(self.circuit, "snapshot"):
                self.circuit.snapshot()

            self.circuit = self._update_circuit(self.circuit)
        else:  # don't overwrite
            self.logger.log_failure(f"Error, existing Circuit: {self.cid} found and overwrites are disabled, skipping.")
            self.circuit = None

        if self.circuit:
            utils.save_circuit(self.circuit, self.logger, allow_cable_skip=self.allow_cable_skip)

    def create_terminations(self):
        self.termination_a = self._build_termination_a()
        self.termination_z = self._build_termination_z()
        utils.save_terminations([self.termination_a, self.termination_z])

    def create_cables(self):
        self.pp_cable = self._build_pp_cable()
        self.device_cable = self._build_device_cable()

        utils.save_cables(
            self.logger, allow_cable_skip=self.allow_cable_skip, cables=[self.pp_cable, self.device_cable]
        )

    def create(self):
        self.create_circuit()
        self.create_terminations()
        self.create_cables()

    def __post_init__(self):
        # utils.validate_date(self.install_date)
        # utils.validate_date(self.termination_date)
        self._validate_cables()
        self.side_a = self.side_a_site
        self.side_z = self.side_z_providernetwork
        if not self.cir:
            self.cir = 0
        if not self.port_speed:
            self.port_speed = 0
        if not self.upstream_speed:
            self.upstream_speed = 0





# @dataclass
# class NiceP2PCircuit:
#     def __post__init(self):
#         allow_cable_skip: row.get("allow_cable_skip"),
#         overwrite: row.get("overwrite"),
#         cable_direct_to_device: row.get("cable_direct_to_device"),
#         cid: row["cid"],
#         provider: row["provider"],
#         type: row["type"],
#         description: row["description"],
#         install_date: row["install_date"],
#         termination_date: row["termination_date"],
#         cir: row["cir"] if row["cir"] else None,
#         comments: row["comments"],
#         side_a: side_a,
#         devic: device,
#         interface: interface,
#         pp: pp,
#         pp_port: pp_port,
#         pp_frontport: pp_frontport,
#         side_z: side_z,
#         device_z: device_z,
#         interface_z: interface_z,
#         pp_z: pp_z,
#         pp_port_z: pp_z_port,
#         pp_z_frontport: pp_z_frontport,
