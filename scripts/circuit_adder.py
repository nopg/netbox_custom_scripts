from circuits.choices import CircuitStatusChoices
from circuits.models import CircuitType, Provider, ProviderNetwork
from dcim.models import Cable, Device, Interface, RearPort, Site
from extras.scripts import BooleanVar, ChoiceVar, FileVar, IntegerVar, ObjectVar, Script, StringVar
from utilities.exceptions import AbortScript

from local.utils import load_data_from_csv, prepare_netbox_data, validate_user
from local.main import main_circuits_bulk, main_circuit_single


class SingleCircuit(Script):
    """
    Netbox Custom Script -- SingleCircuit

    This class provides the GUI Interface & Main Entry Point for a Single Circuit Import
    """
    class Meta:
        name = "Single Circuit"
        description = "Provision one new circuit."
        commit_default = False
        scheduling_enabled = False

        # Organize the GUI Options
        fieldsets = (
            (
                "Enter Circuit Information",
                ("provider", "type", "cid", "description", "status"),
            ),
            (
                "Side A (Choose only 1)",
                ("side_a_site", "side_a_providernetwork"),
            ),
            (
                "Side Z (Choose only 1)",
                ("side_z_site", "side_z_providernetwork"),
            ),
            ("Cables", ("pp", "pp_port", "device", "interface")),
            (
                "Other",
               ("cir", "install_date", "termination_date", "comment", "pp_or_device"),
            ),
            ("P2P Circuits", ("pp_z", "pp_port_z", "device_z", "interface_z")),
            ("Advanced Options", ("overwrite",)),
        )

    # Display Fields
    provider = ObjectVar(
        model=Provider,
        label="Circuit Provider",
        required=True,
    )

    type = ObjectVar(
        model=CircuitType,
        description="Circuit Type",
        required=True,
    )
    cid = StringVar(
        label="Circuit ID",
        required=True,
    )
    description = StringVar(
        label="Circuit Description",
        required=False,
    )
    status = ChoiceVar(
        CircuitStatusChoices,
        default=CircuitStatusChoices.STATUS_ACTIVE,
        label="Circuit Status",
        required=True,
    )
    cir = IntegerVar(
        label="Commit rate",
        min_value=0,
        required=False,
    )
    side_a_site = ObjectVar(
        model=Site,
        label="Site",
        required=False,
    )
    side_a_providernetwork = ObjectVar(
        model=ProviderNetwork,
        label="Provider",
        required=False,
    )
    side_z_site = ObjectVar(
        model=Site,
        label="Site",
        required=False,
    )
    side_z_providernetwork = ObjectVar(
        model=ProviderNetwork,
        label="Provider",
        required=False,
    )
    pp = ObjectVar(model=Device, label="Patch Panel", required=False)
    pp_port = ObjectVar(model=RearPort, label="Patch Panel Port", required=False, query_params={"device_id": "$pp"})

    device = ObjectVar(model=Device, label="Device", required=False)#, query_params={"site_id": "$side_a"})
    interface = ObjectVar(
        model=Interface,
        label="Interface",
        required=False,
        query_params={"device_id": "$device"},
    )

    pp_z = ObjectVar(model=Device, label="Patch Panel Side Z", required=False)
    pp_port_z = ObjectVar(model=RearPort, label="Patch Panel Port Side Z", required=False, query_params={"device_id": "$pp_z"})
    device_z = ObjectVar(model=Device, label="Device Side Z", required=False)#, query_params={"site_id": "$side_a"})
    interface_z = ObjectVar(
        model=Interface,
        label="Interface Side Z",
        required=False,
        query_params={"device_id": "$device_z"},
    )

    comment = StringVar(
        label="Comment",
        required=False,
    )
    install_date = StringVar(
        label="Install Date (YYYY-MM-DD)",
        description="Don't know? Use 2021-02-01",
        required=True,
    )
    termination_date = StringVar(
        label="Termination Date (YYYY-MM-DD)",
        required=True,
    )

    overwrite = BooleanVar(description="Overwrite existing circuits? (same Ciruit ID & Provider == Same Circuit)", default=True)
    pp_or_device = BooleanVar(
        label="Cable Direct To Device?",
        description="Check this box ONLY if the Circuit does not flow through a Patch Panel",
        default=False
    )

    # Run SingleCircuit
    def run(self, data, commit):
        # Validate Form Data
        if data["side_a_site"] and data["side_a_providernetwork"]:
            raise AbortScript(f"Circuit {data['cid']} cannot have Side A Site AND Side A Provider Network Simultaneously")
        if data["side_z_site"] and data["side_z_providernetwork"]:
            raise AbortScript(f"Circuit {data['cid']} cannot have Side Z Site AND Side Z Provider Network Simultaneously")
        
        # set rear/front port (create function)
        rear_port = data.get("pp_port")
        # check date is real (create function)

        if rear_port:
            data["pp_front_port"] = rear_port.frontports.all()[0]

        # Single Circuits are NOT allowed to skip cable creation
        data["allow_cable_skip"] = False

        # Run Script
        output = main_circuit_single(netbox_row=data, self=self)
        if output:
            return output
        # log final job status as failed/completed better (abortscript)


class BulkCircuits(Script):
    """
    Netbox Custom Script -- BulkCircuits

    This class provides the GUI Interface & Main Entry Point for Bulk Circuit Imports
    """
    class Meta:
        name = "Bulk Circuits"
        description = "Provision circuits in bulk via CSV import"
        commit_default = False
        scheduling_enabled = False

        # Organize the GUI Options
        fieldsets = (
            ("Import CSV", ("bulk_circuits",)),
            ("Advanced Options", ("overwrite",)),
        )

    # Display fields
    bulk_circuits = FileVar(
        label="Import CSV",
        description="Bulk Import Circuits",
        required=True,
    )

    overwrite = BooleanVar(
        description="Overwrite existing circuits? (same Ciruit ID & Provider == Same Circuit)", default=True
    )

    # Run BulkCircuits
    def run(self, data, commit):
        # Check if this user is allowed to run Bulk Circuit updates
        allowed = validate_user(user=self.request.user)
        if not allowed:
            raise AbortScript(f"User '{self.request.user}' does not have permission to run this script.")

        # # Bulk Circuits are allowed to skip cable creation
        # allow_cable_skip = True

        # # Prepare CSV for Netbox
        # csv_data = load_data_from_csv(data["bulk_circuits"])
        # netbox_data = prepare_netbox_data(csv_data, overwrite=data['overwrite'], allow_cable_skip=allow_cable_skip)

        # # Run Script
        # main_circuits_bulk(netbox_data=netbox_data, self=self)
    


        # Run Script
        main_circuits_bulk(circuits_csv=data["bulk_circuits"], overwrite=data["overwrite"], self=self)
        
        # log final job status as failed/completed better (abortscript)


script_order = (SingleCircuit, BulkCircuits)
name = "NICE InContact Single Circuit Manager"
