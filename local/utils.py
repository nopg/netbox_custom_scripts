import codecs, csv, datetime

from circuits.choices import CircuitStatusChoices
from circuits.models import Circuit, CircuitType, Provider, ProviderNetwork, CircuitTermination
from dcim.choices import CableTypeChoices
from dcim.models import Cable, Device, Interface, RearPort, Site
from extras.scripts import Script

from django.core.exceptions import ValidationError
from utilities.choices import ColorChoices
from utilities.exceptions import AbortScript

from local.validators import MyCircuitValidator

# Type Hinting
from django.core.files.uploadedfile import InMemoryUploadedFile
from typing import TextIO
FILE = InMemoryUploadedFile | TextIO

BULK_SCRIPT_ALLOWED_USERS = ["netbox", "danny.berman", "joe.deweese", "loran.fuchs"]
UPDATED_ATTRIBUTES = "install_date"

HEADER_MAPPING = {
    "Circuit ID": "cid",
    "Provider": "provider",
    "Circuit Type": "type",
    "Side A Site": "side_a_site",
    "Side A Provider Network": "side_a_providernetwork",
    "Patch Panel": "pp",
    "PP Port": "pp_port",
    "Device": "device",
    "Interface": "interface",
    "Side Z Site": "side_z_site",
    "Side Z Provider Network": "side_z_providernetwork",
    "Description": "description",
    "Install Date": "install_date",
    "Termination Date": "termination_date",
    "Commit Rate (Kbps)": "cir",
    "Comments": "comments",
    "Patch Panel Z": "pp_z",
    "PP Port Z": "pp_z_port",
    "Device Z": "device_z",
    "Interface Z": "interface_z",
    "Cable Direct To Device": "cable_direct_to_device",
    "Cross Connect": "cross_connect",
    "Cable Type": "cable_type",
}

REQUIRED_VARS = {
    "cid", "provider", "type"
}

CABLE_COLORS = {
    CableTypeChoices.TYPE_SMF: ColorChoices.COLOR_YELLOW,
    CableTypeChoices.TYPE_SMF_OS1: ColorChoices.COLOR_YELLOW,
    CableTypeChoices.TYPE_SMF_OS2: ColorChoices.COLOR_YELLOW,
    CableTypeChoices.TYPE_MMF: ColorChoices.COLOR_AQUA,
    CableTypeChoices.TYPE_MMF_OM1: ColorChoices.COLOR_AQUA,
    CableTypeChoices.TYPE_MMF_OM2: ColorChoices.COLOR_AQUA,
    CableTypeChoices.TYPE_MMF_OM3: ColorChoices.COLOR_AQUA,
    CableTypeChoices.TYPE_MMF_OM4: ColorChoices.COLOR_AQUA,
    CableTypeChoices.TYPE_MMF_OM5: ColorChoices.COLOR_AQUA,
    CableTypeChoices.TYPE_CAT5: ColorChoices.COLOR_WHITE,
    CableTypeChoices.TYPE_CAT5E: ColorChoices.COLOR_WHITE,
    CableTypeChoices.TYPE_CAT6: ColorChoices.COLOR_WHITE,
    CableTypeChoices.TYPE_CAT6A: ColorChoices.COLOR_WHITE,
}

def validate_date(date_str: str) -> None:
    try:
        date = datetime.date.fromisoformat(date_str)
        if date.year >= 2026 or date.year <= 1980:
            raise AbortScript(f"Date: {date_str} is outside constraints: Minimum year: 1980, Maximum year: 2026")
    except ValueError:
        raise AbortScript(f"Invalid date{date_str}), should be YYYY-MM-DD")
    
def validate_user(user):
    if user.username not in BULK_SCRIPT_ALLOWED_USERS:
        return False
    else:
        return True

def get_provider_by_name(name: str):
    try:
        provider = Provider.objects.get(name=name)
    except Provider.DoesNotExist:
        return None

    return provider

def get_provider_network_by_name(name: str):
    try:
        provider_network = ProviderNetwork.objects.get(name=name)
    except ProviderNetwork.DoesNotExist:
        return None

    return provider_network

def get_circuit_type_by_name(name: str):
    try:
        _type = CircuitType.objects.get(name=name)
    except CircuitType.DoesNotExist:
        return None
    
    return _type

def get_site_by_name(name: str):
    try:
        site = Site.objects.get(name=name)
    except Site.DoesNotExist:
        return None
    
    return site

def get_device_by_name(name: str, site: Site = None):
    try:
        if not site:
            device = Device.objects.get(name=name)
        else:
            device = Device.objects.get(name=name, site=site)
    except Device.DoesNotExist:
        return None
    
    return device

def get_interface_by_name(name: str, device: Device = None):
    try:
        if device:
            interface = Interface.objects.get(name=name, device=device)
        else:
            interface = Interface.objects.get(name=name)
    except Interface.DoesNotExist:
        return None
    
    return interface

def get_side_by_name(side_site, side_providernetwork) -> Site | ProviderNetwork:
    side = get_site_by_name(side_site)
    if not side:
        side = get_provider_network_by_name(side_providernetwork)
    return side

def load_data_from_csv(csv_file) -> list[dict]:
    circuits_csv = csv.DictReader(codecs.iterdecode(csv_file, "utf-8"))
    csv_data = []

    # Update Dictionary Keys / Headers
    for row in circuits_csv:
        csv_row = {}
        for old_header, value in row.items():
            if old_header in HEADER_MAPPING:
                csv_row[HEADER_MAPPING[old_header]] = value
        # Add any missing fields we may check later
        for header in HEADER_MAPPING:
            if header not in csv_row:
                csv_row[header] = ""

        csv_data.append(csv_row)

    return csv_data

def validate_row(row: dict) -> bool | str:
    """
    Validate we have the required variables
    """
    missing = []
    error = False

    for var in REQUIRED_VARS:
        if row.get(var) is None:
            missing.append(var)
    if missing:
        columns = ", ".join(missing)
        error = f"'{row.get('cid')}' is missing required values(s): {columns}\n"
    
    if row["side_a_site"] and row["side_a_providernetwork"]:
        error += f"Circuit {row['cid']} cannot have Side A Site AND Side A Provider Network Simultaneously\n"
    if row["side_z_site"] and row["side_z_providernetwork"]:
        error += f"Circuit {row['cid']} cannot have Side Z Site AND Side Z Provider Network Simultaneously\n"

    return error

def prepare_pp_ports(pp_rearport):
    """
    Get FrontPort associated with RearPort
    """
    if not isinstance(pp_rearport, RearPort):
        return None
    if pp_rearport.positions > 1:
        raise AbortScript(f"RearPorts with multiple positions not yet implemented: RearPort: {pp_rearport}")
    pp_frontport = pp_rearport.frontports.first()

    return pp_frontport


def prepare_netbox_row(row: dict):
    """
    Help convert CSV data into Netbox Models where necessary
    """

    row["provider"] = get_provider_by_name(name=row["provider"])
    row["type"] = get_circuit_type_by_name(name=row["type"])
    skip = validate_row(row)

    # # Single Circuits are NOT allowed to skip cable creation
    # if not row.get("allow_cable_skip"):
    #     row["allow_cable_skip"] = False
    # if not row.get("overwrite"):
    #     row["overwrite"] = False

    side_a = get_side_by_name(row["side_a_site"] , row["side_a_providernetwork"])
    side_z = get_side_by_name(row["side_z_site"] , row["side_z_providernetwork"])
    if type(side_a) == Site:
        site = side_a
    elif type(side_a) == ProviderNetwork:
        if not skip:
            skip = ""
        skip += "\nSide Z to Device/Patch Panel without Side A Device/Patch Panel is currently unsupported."
        site = None
    else:
        site = None

    device = get_device_by_name(name=row["device"], site=site)
    interface = get_interface_by_name(name=row["interface"], device=device)
    pp = get_device_by_name(name=row["pp"], site=site)

    ### PP PORT FRONT/REAR
    pp_port = get_interface_by_name(name=row["pp_port"], device=pp)
    pp_frontport = prepare_pp_ports(pp_port)
    ### PP PORT TYPE

    # Check circuit_type == P2P
    # TBD for P2P Circuits
    device_z = None
    interface_z = None
    pp_z = get_device_by_name(name=row["pp_z"], site=site)
    pp_z_port = get_interface_by_name(name=row["pp_z_port"], device=pp_z)
    pp_z_frontport = prepare_pp_ports(pp_z_port)

    netbox_row = {
        "allow_cable_skip": row.get("allow_cable_skip"),
        "overwrite": row.get("overwrite"),
        "cable_direct_to_device": row.get("cable_direct_to_device"),
        "cid": row["cid"],
        "provider": row["provider"],
        "type": row["type"],
        "description": row["description"],
        "install_date": row["install_date"],
        "termination_date": row["termination_date"],
        "cir": row["cir"] if row["cir"] else None,
        "comments": row["comments"],
        "side_a": side_a,
        "device": device,
        "interface": interface,
        "pp": pp,
        "pp_port": pp_port,
        "pp_frontport": pp_frontport,
        "side_z": side_z,
        "device_z": device_z,
        "interface_z": interface_z,
        "pp_z": pp_z,
        "pp_port_z": pp_z_port,
        "pp_z_frontport": pp_z_frontport,
    }

    netbox_row["skip"] = skip#validate_row(netbox_row)
    for k,v in netbox_row.items():
        if k not in ("description", "comments", "install_date", "termination_date"):
            if v == "":
                netbox_row[k] = None
    return netbox_row

def prepare_netbox_data(csv_data: list[dict], overwrite: bool, allow_cable_skip: bool) -> dict:
    circuit_data = []
    for row in csv_data:
        row["overwrite"] = overwrite
        row["allow_cable_skip"] = allow_cable_skip
        row = prepare_netbox_row(row=row)
        circuit_data.append(row)
    return circuit_data

def save_cables(logger, *objects, allow_cable_skip: bool = False):
    for obj in objects:
        if obj:
            try:
                obj.full_clean()
                obj.save()
                logger.log_success(f"Saved: '{obj}'")
            except ValidationError as e:
                error = ""
                for msg in e.messages:
                    if "Duplicate" in msg:
                        error += f"Duplicate Cable found, unable to create Cable: {obj}\n"
                    else:
                        error += f"Validation Error saving {type(obj)}: {e.messages}\n"
                
                if not allow_cable_skip:
                    raise AbortScript(error)
                else:
                    logger.log_failure(error)
            except Exception as e:
                logger.log_failure(f"Unknown error saving {type(obj)}: {e}")
                logger.log_failure(f"Type: {type(e)}")






def create_circuit_from_data(netbox_row: dict[str,any]) -> Circuit:
    new_circuit = Circuit(
        cid=netbox_row["cid"],
        provider=netbox_row["provider"],
        commit_rate=netbox_row["cir"],
        type=netbox_row["type"],
        status=CircuitStatusChoices.STATUS_ACTIVE,
        description=netbox_row["description"],
        # custom_field_data={
        #     "salesforce_url": "https://ifconfig.co"
        # },
    )
    return new_circuit

def validate_circuit(circuit: Circuit) -> bool:
    b = MyCircuitValidator()
    failed = b.validate(circuit=circuit, manual=True)
    return failed

def save_circuit(circuit: Circuit, self: Script):
    error = validate_circuit(circuit)
    if error:
        self.log_failure(f"Failed custom validation: {error}")
    else:
        try:
            circuit.full_clean()
            circuit.save()
            self.log_success(f"Saved circuit: '{circuit.cid}'")
        except ValidationError as e:
            lmessages = [msg for msg in e.messages]
            messages = "\n".join(lmessages)
            self.log_failure(f"{circuit.cid} - Failed Netbox validation: {messages}")

    return circuit

def check_circuit_duplicate(netbox_row: dict[str,any]) -> bool:
    # Check for duplicate
    circ = Circuit.objects.filter(
        cid=netbox_row["cid"], provider__name=netbox_row["provider"]
    )
    if circ.count() == 0:  # Normal creation, no duplicate
        return False
    elif circ.count() > 1:
        raise AbortScript(
            f"Error, multiple duplicates for Circuit ID: {netbox_row['cid']}, please resolve manually."
        )
    else:
        return True # Duplicate found
    
def update_existing_circuit(existing_circuit: Circuit, new_circuit: dict[str, any]) -> Circuit | None:
    for attribute in ("description", "type", "install_date", "cir", "comments"):
        if not new_circuit[attribute] and attribute in (UPDATED_ATTRIBUTES):
            setattr(existing_circuit, attribute, None)
        else:
            setattr(existing_circuit, attribute, new_circuit[attribute])
    return existing_circuit

def build_circuit(self: Script, netbox_row: dict[str,any], overwrite: bool = False) -> None:
    duplicate = check_circuit_duplicate(netbox_row)
    if not duplicate: # No duplicate
        new_circuit = create_circuit_from_data(netbox_row)

    elif duplicate and overwrite:
        self.log_warning(
            f"Overwrites enabled, updating existing circuit: {netbox_row['cid']} ! See change log for original values."
        )
        existing_circuit = Circuit.objects.get(
            cid=netbox_row["cid"], provider__name=netbox_row["provider"]
        )
        if existing_circuit.pk and hasattr(existing_circuit, "snapshot"):
            # self.log_info(f"Creating snapshot: {circ.cid}")
            existing_circuit.snapshot()

        new_circuit = update_existing_circuit(existing_circuit, new_circuit=netbox_row)    
    else: # don't overwrite
        self.log_failure(
            f"Error, existing Circuit: {netbox_row['cid']} found and overwrites are disabled, skipping."
        )
        return None

    # Don't save yet
    circuit = save_circuit(new_circuit, self)
    return circuit

def save_terminations(terminations: list):
    for termination in terminations:
        termination.full_clean()
        termination.save()


def build_terminations(self: Script, netbox_row: dict[str,any], circuit: Circuit) -> CircuitTermination | None:
    termination_a, termination_z = None, None

    if not netbox_row["side_a"]:
        self.log_warning(f"Skipping Side A Termination on '{netbox_row['cid']}' due to missing Site")
        # return None
    elif netbox_row["device"] and not netbox_row["interface"]:
        self.log_warning(f"Skipping Side A Termination on '{netbox_row['cid']}' due to missing Device Interface")
        # return None
    else:
        termination_a = CircuitTermination(term_side="A", site=netbox_row["side_a"], circuit=circuit)

    if not netbox_row["side_z"]:
        self.log_warning(f"Skipping Side Z Termination on '{netbox_row['cid']}' due to missing Provider Network")
        # return None
    else:
        termination_z = CircuitTermination(term_side="Z", provider_network=netbox_row["side_z"], circuit=circuit)
    if termination_a:
        if termination_z:
            save_terminations([termination_a, termination_z])
        else:
            save_terminations([termination_a])
    elif termination_z:
        save_terminations([termination_z])

    return termination_a, termination_z

def build_cable(self: Script, side_a: Interface, side_b) -> None:
    cable = Cable(a_terminations=[side_a], b_terminations=[side_b], type=CableTypeChoices.TYPE_SMF_OS2)
    #save_cable(cable)
    return cable
