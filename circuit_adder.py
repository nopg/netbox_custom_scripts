import codecs, csv
from circuits.choices import CircuitStatusChoices
from circuits.models import Circuit, CircuitType, Provider
from extras.scripts import BooleanVar, ChoiceVar, FileVar, IntegerVar, Script, StringVar

from django.core.exceptions import ValidationError
from utilities.exceptions import AbortScript

from local.validators import MyCircuitValidator


## Util functions


def get_provider_by_name(name: str):
    provider = Provider.objects.get(name=name)
    return provider

def get_circuit_type_by_name(name: str):
    _type = CircuitType.objects.get(name=name)
    return _type

def load_circuits_from_csv(circuitsfile, self):
    circuits_csv = csv.reader(codecs.iterdecode(circuitsfile, "utf-8"))
    circuits = []
    for (
        cid,
        provider,
        type,
        side_a,
        side_z,
        description,
        date_installed,
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
            "side_z": side_z,
            "description": description,
            "date_installed": date_installed,
            "cir": cir,
            "comments": comments,
            "contacts": contacts,
            "tags": tags,
        }
        circuits.append(circuit)
    return circuits

def load_circuit_from_gui(data: dict):
    provider = get_provider_by_name(name=data["provider"])
    circuit_type = get_circuit_type_by_name(name=data["circuit_type"])

    circuit = {
        "cid": data["cid"],
        "provider": provider,
        "type": circuit_type,
        "side_a": data["side_a"],
        "side_z": data["side_z"],
        "description": data["description"],
        "date_installed": data["date_installed"],
        "cir": data["cir"],
        "comments": data["comments"],
        "contacts": data["contacts"],
        "tags": data["tags"],
    }
    return circuit

def prepare_circuit(circuit: dict, overwrite, self):
    if circuit["provider"] == "" or circuit["type"] == "":
        return None

    provider = Provider.objects.get(name=circuit["provider"])
    _type = CircuitType.objects.get(name=circuit["type"])

    circ = Circuit.objects.filter(
        cid=circuit["cid"], provider__name=circuit["provider"]
    )

    prepared_circuit = Circuit(
        cid=circuit["cid"],
        provider=provider,
        commit_rate=circuit["cir"],
        type=_type,
        status=CircuitStatusChoices.STATUS_ACTIVE,
        description=circuit["description"],
        # custom_field_data={
        #     "salesforce_url": "https://ifconfig.co"
        # },
    )

    if circ.count() == 0:  # Normal creation
        return prepared_circuit
    if circ.count() > 1:  # Should never hit
        raise AbortScript(
            f"Error, multiple duplicates for Circuit ID: {circuit['cid']}, please resolve manually."
        )
    else:  # We are attempting to update an existing circuit:
        circ = circ[0]
        if not overwrite:
            self.log_failure(
                f"Error, existing Circuit: {circ.cid} found and overwrites are disabled, skipping."
            )
            return None

        self.log_warning(
            f"Overwrites enabled, updating existing circuit: {circ.cid} ! See change log for original values."
        )
        if circ.pk and hasattr(circ, "snapshot"):
            # self.log_info(f"Creating snapshot: {circ.cid}")
            circ.snapshot()

        # Finish proper updates
        circ.description = circuit["description"]
        return circ


def add_circuit(circuit, overwrite, self, test=False):
    if test:
        output = ""
        for k, v in circuit.items():
            output += f"{v=} - "
        print(f"{output}\n")
        return output

    new_circuit = prepare_circuit(circuit, overwrite, self)

    if new_circuit:
        try:
            b = MyCircuitValidator()
            failed = b.validate(circuit=new_circuit, manual=True)
            if failed:
                self.log_failure(f"Failed validation: {failed}")
                return None
            new_circuit.full_clean()
            new_circuit.save()
            self.log_success(f"Created circuit: {new_circuit.cid}")
        except ValidationError as e:
            lmessages = [msg for msg in e.messages]
            messages = "\n".join(lmessages)
            self.log_failure(f"{new_circuit.cid} - Failed validation: {messages}")


def add_circuits(circuits, overwrite, self):
    output = ""
    for circuit in circuits:
        _output = add_circuit(circuit, overwrite, self)
        if _output:
            output += _output
    if output:
        return output


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
                ("provider", "circuit_type", "cid", "cir", "side_a", "side_z", "description", "status"),
            ),
            (
                "Other",
                ("date_installed", "comment", "contacts", "tags"),
            ),
            ("Advanced Options", ("create_sites", "create_provider", "overwrite"))
        )

    create_sites = BooleanVar(
        description="Auto create non-existing Sites?", default=False
    )
    create_provider = BooleanVar(
        description="Auto create non-existing Providers?", default=False
    )
    overwrite = BooleanVar(
        description="Overwrite existing circuits? (same ID & Provider)", default=True
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
    side_a = StringVar(
        description="Side A (update to...?)",
        required=False,
    )
    side_z = StringVar(
        description="Side Z (update to...?)",
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
    date_installed = StringVar(
        description="Date installed (update to  date field...?)",
        required=False,
    )
    cir = IntegerVar(
        description="Commit rate(rename, update to int",
        required=False,
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
        #circuit = prepare_circuit(circuit=data, overwrite=data["overwrite"], self=self)
        output = add_circuit(circuit=data, overwrite=data["overwrite"], self=self)
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
            ("Advanced Options", ("create_sites", "create_provider", "overwrite")),
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
    overwrite = BooleanVar(
        description="Overwrite existing circuits? (same ID & Provider)", default=True
    )

    # Run
    def run(self, data, commit):
        circuits = load_circuits_from_csv(data["bulk_circuits"], self)
        output = add_circuits(circuits, data['overwrite'], self)
        if output:
            return output
        # log final job status as failed/completed better (abortscript)


script_order = (SingleCircuit, BulkCircuits)
name = "NICE InContact Circuit Manager"
