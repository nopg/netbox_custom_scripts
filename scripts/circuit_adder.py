from circuits.choices import CircuitStatusChoices
from circuits.models import CircuitType, Provider, ProviderNetwork
from dcim.models import Cable, Device, Interface, RearPort, Site
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
                ("provider", "type", "cid", "cir", "description", "status"),
            ),
            (
                "Termination",
                ("side_a", "side_z", "pp", "pp_port", "device", "interface")
            ),
            (
                "Other",
                ("install_date", "comment", "contacts", "tags"),
            ),
            ("Advanced Options", ("create_pp", "overwrite"))
        )

    create_pp = BooleanVar(
        description="Auto create non-existing Patch Panels?", default=False
    )
    overwrite = BooleanVar(
        description="Overwrite existing circuits? (same ID & Provider)", default=False
    )
    provider = ObjectVar(
        model = Provider,
        label = "Circuit Provider",
        required = True,
    )
    
    type = ObjectVar(
        model = CircuitType,
        description="Circuit Type",
        required=False,
    )
    cid = StringVar(
        label="Circuit ID",
        required=False,
    )
    description = StringVar(
        label="Circuit Description",
        required=False,
    )
    status = ChoiceVar(
        CircuitStatusChoices,
        default=CircuitStatusChoices.STATUS_ACTIVE,
        label="Circuit Status",
        required=False,
    )
    install_date = StringVar(
        label="Date installed (update to  date field...?)",
        required=False,
    )
    cir = IntegerVar(
        label="Commit rate(rename, update to int",
        required=False,
    )
    side_a = ObjectVar(
        model = Site,
        label="Side A",
        required=False,
    )
    side_z = ObjectVar(
        model = ProviderNetwork,
        label="Side Z",
        required=False,
    )
    pp = ObjectVar(
        model = Device,
        label = "Patch Panel",
        required = False
    )
    pp_port = ObjectVar(
        model = RearPort,
        label = "Patch Panel Port",
        required = False,
        query_params={
            "device_id": "$pp"
        }
    )

    device = ObjectVar(
        model = Device,
        label = "Device",
        required = False,
        query_params={
            "site_id": "$side_a"
        }

    )
    interface = ObjectVar(
        model = Interface,
        label = "Interface",
        required = False,
        query_params={
            "device_id": "$device"
        },
    )
    comment = StringVar(
        label="Comment",
        required=False,
    )
    contacts = StringVar(
        label="Contacts (update to contact object)",
        required=False,
    )
    tags = StringVar(
        label="Tags (update to tags object?)",
        required=False,
    )

    def run(self, data, commit):
        rear_port = data.get("pp_port")
        if rear_port:
            data["pp_front_port"] = rear_port.frontports.all()[0]
        output = main_circuit_entry(netbox_row=data, overwrite=data["overwrite"], self=self)
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
            ("Advanced Options", ("create_pp", "overwrite")),
        )

    # Display fields
    bulk_circuits = FileVar(
        description="Bulk Import Circuits", required=False, label="Import CSV"
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
