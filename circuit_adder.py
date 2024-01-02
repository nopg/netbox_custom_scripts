import codecs, csv
from circuits.choices import CircuitStatusChoices
from circuits.models import Circuit, CircuitType, Provider, ProviderNetwork
from dcim.models import Device, Interface, Site
from extras.scripts import BooleanVar, ChoiceVar, FileVar, IntegerVar, ObjectVar, Script, StringVar

from django.core.exceptions import ValidationError
from utilities.exceptions import AbortScript

from local.validators import MyCircuitValidator

from rich.pretty import pretty_repr

## Util functions


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
        if site:
            device = Device.objects.get(name=name, site=site)
        else:
            device = Device.objects.get(name=name)
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

def load_circuits_from_csv(circuitsfile, self):
    # column_names = {
    # 'date': ['date', 'valutadate'],
    # 'amount': ['amount', 'amount_withdrawal']
    # }
    circuits_csv = csv.reader(codecs.iterdecode(circuitsfile, "utf-8"))
    circuits = []
    for (
        cid,
        provider,
        type,
        side_a,
        device,
        interface,
        side_z,
        description,
        install_date,
        cir,
        comments,
        contacts,
        tags,
    ) in circuits_csv:
        if cid == "Circuit ID":
            continue
        circuit = {
            "cid": cid,
            "provider": provider,
            "type": type,
            "side_a": side_a,
            "device": device,
            "interface": interface,
            "side_z": side_z,
            "description": description,
            "install_date": install_date,
            "cir": cir,
            "comments": comments,
            "contacts": contacts,
            "tags": tags,
        }
        circuits.append(circuit)
    return circuits

def prepare_csv_row(row: dict):
    skip = False

    provider = get_provider_by_name(name=row["provider"])
    circuit_type = get_circuit_type_by_name(name=row["type"])
    site = get_site_by_name(name=row["side_a"])
    provider_network = get_provider_network_by_name(name=row["side_z"])
    device = get_device_by_name(name=row["device"], site=site)
    interface = get_interface_by_name(name=row["interface"], device=device)

    if not provider or not circuit_type:
        skip = f"Circuit \'{row['cid']}\' is missing a Provider or Circuit Type"

    circuit_row_data = {
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
        "skip": skip,
    }
    return circuit_row_data

def prepare_csv_data(csv_data: dict):
    circuit_data = []
    for row in csv_data:
        circuit_data.append(prepare_csv_row(row=row))
    return circuit_data



def create_circuit(circuit_data: dict[str,any]) -> Circuit:
    new_circuit = Circuit(
        cid=circuit_data["cid"],
        provider=circuit_data["provider"],
        commit_rate=circuit_data["cir"],
        type=circuit_data["type"],
        status=CircuitStatusChoices.STATUS_ACTIVE,
        description=circuit_data["description"],
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

    
def circuit_duplicate(circuit_data: dict[str,any]) -> bool:
    # Check for duplicate
    circ = Circuit.objects.filter(
        cid=circuit_data["cid"], provider__name=circuit_data["provider"]
    )
    if circ.count() == 0:  # Normal creation, no duplicate
        return False
    elif circ.count() > 1:
        raise AbortScript(
            f"Error, multiple duplicates for Circuit ID: {circuit_data['cid']}, please resolve manually."
        )
    else:
        return True # Duplicate found
    
def update_existing_circuit(existing_circuit: Circuit, new_circuit: dict[str, any]) -> None:
    for attribute in ("description", "type", "install_date", "cir", "comments"):
        if not new_circuit[attribute] and attribute in ("install_date"):
                setattr(existing_circuit, attribute, None)
        else:
            setattr(existing_circuit, attribute, new_circuit[attribute])
    return existing_circuit

def build_circuit(self: Script, circuit_data: dict[str,any], overwrite: bool) -> None:
    duplicate = circuit_duplicate(circuit_data)
    if not duplicate: # No duplicate
        new_circuit = create_circuit(circuit_data)
    elif duplicate and overwrite:
        self.log_warning(
            f"Overwrites enabled, updating existing circuit: {circuit_data['cid']} ! See change log for original values."
        )
        existing_circuit = Circuit.objects.get(
            cid=circuit_data["cid"], provider__name=circuit_data["provider"]
        )
        if existing_circuit.pk and hasattr(existing_circuit, "snapshot"):
            # self.log_info(f"Creating snapshot: {circ.cid}")
            existing_circuit.snapshot()
        new_circuit = update_existing_circuit(existing_circuit, new_circuit=circuit_data)    
    else: # don't overwrite
        self.log_failure(
            f"Error, existing Circuit: {circuit_data['cid']} found and overwrites are disabled, skipping."
        )
        return None

    save_circuit(new_circuit, self)

def build_terminations(self, circuit) -> None:
    # RENAME CIRCUIT HERE AND CIRCUITS TO DATA OR OTHER
    if circuit["device"] and not circuit["interface"]:
        self.log_failure(f"Skipping Side A Termination on '{circuit['cid']}' due to missing Device Interface")

def main_circuit_entry(self: Script, circuit: dict[str, any], overwrite: bool):

#     ### prepare data
#     ### add circuit
#     # add terminations
#     # add cable
#     # save
    
    build_circuit(self, circuit, overwrite)
    build_terminations(self, circuit)
    #add_cable(self, circuit)

def main_circuits_loop(self: Script, circuits_data: list[dict[str, any]], overwrite: bool = False) -> None:
    for circuit_data in circuits_data:
        if not circuit_data["skip"]:
            main_circuit_entry(self, circuit_data, overwrite)
        else:
            self.log_warning(f"Skipping circuit \'{circuit_data['cid']}\' due to: {circuit_data['skip']}")


## Custom Scripts

class SingleCircuit(Script):
    class Meta:
        name = "Single Circuit"
        description = "Provision one new circuit."
        commit_default = False
        scheduling_enabled = False  ## NEW SINCE 3.2.0

        # field_order = ['site_name', 'switch_count', 'switch_model']
        fieldsets = (
            (
                "Enter Circuit Information",
                ("provider", "circuit_type", "cid", "cir", "description", "status"),
            ),
            (
                "Termination",
                ("side_a", "side_z", "device_name", "interface")
            ),
            (
                "Other",
                ("install_date", "comment", "contacts", "tags"),
            ),
            ("Advanced Options", ("create_sites", "create_provider", "create_device", "create_rack", "create_pp", "overwrite"))
        )

    create_sites = BooleanVar(
        description="Auto create non-existing Sites?", default=False
    )
    create_provider = BooleanVar(
        description="Auto create non-existing Providers?", default=False
    )
    create_device = BooleanVar(
        description="Auto create non-existing Devices?", default=False
    )
    create_rack = BooleanVar(
        description="Auto create non-existing Racks?", default=False
    )
    create_pp = BooleanVar(
        description="Auto create non-existing Patch Panels?", default=False
    )
    overwrite = BooleanVar(
        description="Overwrite existing circuits? (same ID & Provider)", default=False
    )
    provider = StringVar(
        description="Circuit Provider",
        required=False,
    )
    circuit_type = StringVar(
        description="Circuit Type",
        required=False,
    )
    cid = StringVar(
        description="Circuit ID",
        required=False,
    )
    description = StringVar(
        description="Circuit Description",
        required=False,
    )
    status = ChoiceVar(
        CircuitStatusChoices,
        default=CircuitStatusChoices.STATUS_ACTIVE,
        description="Circuit Status",
        required=False,
    )
    install_date = StringVar(
        description="Date installed (update to  date field...?)",
        required=False,
    )
    cir = IntegerVar(
        description="Commit rate(rename, update to int",
        required=False,
    )
    side_a = ObjectVar(
        model = Site,
        description="Side A",
        required=False,
    )
    side_z = ObjectVar(
        model = ProviderNetwork,
        description="Side Z",
        required=False,
    )
    device = ObjectVar(
        model = Device,
        description = "Device",
        required = False,
        query_params={
            "site_id": "$side_a"
        }

    )
    interface = ObjectVar(
        model = Interface,
        description = "Interface",
        required = False,
        query_params={
            "device_id": "$device"
        },
    )
    comment = StringVar(
        description="Comment",
        required=False,
    )
    contacts = StringVar(
        description="Contacts (update to contact object)",
        required=False,
    )
    tags = StringVar(
        description="Tags (update to tags object?)",
        required=False,
    )

    def run(self, data, commit):
        data["type"] = data["circuit_type"]
        output = add_circuit_data(circuit_data=data, overwrite=data["overwrite"], self=self)
        if output:
            return output


class BulkCircuits(Script):
    class Meta:
        name = "Bulk Circuits"
        description = "Provision circuits in bulk via CSV import"
        commit_default = False
        scheduling_enabled = False

        fieldsets = (
            ("Import CSV", ("bulk_circuits",)),
            ("Advanced Options", ("create_sites", "create_provider", "create_device", "create_rack", "create_pp", "overwrite")),
        )

    # Display fields
    bulk_circuits = FileVar(
        description="Bulk Import Circuits", required=False, label="Import CSV"
    )
    create_sites = BooleanVar(
        description="Auto create non-existing Sites?", default=False
    )
    create_provider = BooleanVar(
        description="Auto create non-existing Providers?", default=False
    )
    create_device = BooleanVar(
        description="Auto create non-existing Devices?", default=False
    )
    create_rack = BooleanVar(
        description="Auto create non-existing Racks?", default=False
    )
    create_pp = BooleanVar(
        description="Auto create non-existing Patch Panels?", default=False
    )
    overwrite = BooleanVar(
        description="Overwrite existing circuits? (same ID & Provider)", default=False
    )

    # Run
    def run(self, data, commit):
        csv_data = load_circuits_from_csv(data["bulk_circuits"], self)
        circuit_data = prepare_csv_data(csv_data)
        # return pretty_repr(circuit_data)

        main_circuits_loop(circuits_data=circuit_data, overwrite=data['overwrite'], self=self)
        # log final job status as failed/completed better (abortscript)

script_order = (SingleCircuit, BulkCircuits)
name = "NICE InContact Circuit Manager"
