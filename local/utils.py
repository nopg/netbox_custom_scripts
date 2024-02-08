import codecs, csv, sys
from circuits.choices import CircuitStatusChoices
from circuits.models import Circuit, CircuitType, Provider, ProviderNetwork, CircuitTermination
from dcim.models import Cable, Device, Interface, Site
from extras.scripts import Script

from django.core.exceptions import ValidationError
from utilities.exceptions import AbortScript

from local.validators import MyCircuitValidator


# Type Hinting
from django.core.files.uploadedfile import InMemoryUploadedFile
from typing import TextIO
FILE = InMemoryUploadedFile | TextIO

UPDATED_ATTRIBUTES = "install_date"

HEADER_MAPPING = {
    "Circuit ID": "cid",
    "Provider": "provider",
    "Circuit Type": "type",
    "Side A": "side_a",
    "Device": "device",
    "Interface": "interface",
    "Side Z": "side_z",
    "Description": "description",
    "Date Installed": "install_date", # UPDATE TO date_installed
    "Commit Rate (Kbps)": "cir",
    "Comments": "comments",
    "Contacts": "contacts",
    "Tags": "tags",
}

REQUIRED_VARS = {
    "cid", "provider", "type"
}

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

def validate_row(row: dict) -> bool | str:
    missing = []
    error = False

    for var in REQUIRED_VARS:
        if row.get(var) is None:
            missing.append(var)
    if missing:
        columns = "\, ".join(missing)
        error = f"{row['cid']} is missing required values(s): {columns}, skipping."

    return error

def load_data_from_csv(csv_file) -> list[dict]:
    circuits_csv = csv.DictReader(codecs.iterdecode(csv_file, "utf-8"))
    csv_data = []

    # Update Dictionary Keys / Headers
    for row in circuits_csv:
        csv_row = {}

        # Update_vars()?
        for k,v in row.items():
            if k in HEADER_MAPPING:
                csv_row[HEADER_MAPPING[k]] = v
       
        csv_data.append(csv_row)

    return csv_data

def prepare_netbox_row(row: dict):
    provider = get_provider_by_name(name=row["provider"])
    circuit_type = get_circuit_type_by_name(name=row["type"])
    site = get_site_by_name(name=row["side_a"])
    provider_network = get_provider_network_by_name(name=row["side_z"])
    device = get_device_by_name(name=row["device"], site=site)
    interface = get_interface_by_name(name=row["interface"], device=device)

    netbox_row = {
        "cid": row["cid"],
        "provider": provider,
        "type": circuit_type,
        "side_a": site,             # SIDE A ALWAYS SITE ?!
        "device": device,
        "interface": interface,
        "side_z": provider_network, # SIDE Z ALWAYS PROVIDER NETWORK ?!
        "description": row["description"],
        "install_date": row["install_date"],
        "cir": row["cir"],
        "comments": row["comments"],
        "contacts": row["contacts"],
        "tags": row["tags"],
    }

    netbox_row["skip"] = validate_row(netbox_row)

    return netbox_row

def prepare_netbox_data(csv_data: list[dict]) -> dict:
    circuit_data = []
    for row in csv_data:
        circuit_data.append(prepare_netbox_row(row=row))
    return circuit_data

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

    return termination_a

def save_cable(cable: Cable) -> None:
    cable.full_clean()
    cable.save()

def build_cable(self: Script, side_a: Interface, side_b) -> None:
    cable = Cable(a_terminations=[side_a], b_terminations=[side_b])
    save_cable(cable)

def main_circuit_entry(self: Script, netbox_row: dict[str, any], overwrite: bool):    
    circuit = build_circuit(self, netbox_row, overwrite)
    ct_side_a = build_terminations(self, netbox_row, circuit)

    if netbox_row["interface"]:
        build_cable(self, side_a=netbox_row["interface"], side_b=ct_side_a)
    else:
        self.log_warning(f"Skipping cable creation to device interface due to missing interface on device '{circuit.cid}")

def main_circuits_loop(self: Script, netbox_data: list[dict[str, any]], overwrite: bool = False) -> None:
    for netbox_row in netbox_data:
        if netbox_row["skip"]:
            self.log_warning(f"Skipping circuit \'{netbox_row['cid']}\' due to: {netbox_row['skip']}")
        else:
            main_circuit_entry(self, netbox_row, overwrite)
