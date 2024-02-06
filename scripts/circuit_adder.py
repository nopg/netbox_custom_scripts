from circuits.choices import CircuitStatusChoices
from circuits.models import ProviderNetwork
from dcim.models import Cable, Device, Interface, Site
from extras.scripts import BooleanVar, ChoiceVar, FileVar, IntegerVar, ObjectVar, Script, StringVar

from local.utils import load_data_from_csv, prepare_netbox_data, main_circuit_entry, main_circuits_loop


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
                ("side_a", "side_z", "device", "interface")
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
        output = main_circuit_entry(circuit_data=data, overwrite=data["overwrite"], self=self)
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
        csv_data = load_data_from_csv(data["bulk_circuits"])
        netbox_data = prepare_netbox_data(csv_data)
        # return pretty_repr(circuit_data)

        main_circuits_loop(netbox_data=netbox_data, overwrite=data['overwrite'], self=self)
        # log final job status as failed/completed better (abortscript)

script_order = (SingleCircuit, BulkCircuits)
name = "NICE InContact Circuit Manager"
