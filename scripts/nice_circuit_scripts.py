from circuits.choices import CircuitStatusChoices
from circuits.models import CircuitType, Provider, ProviderNetwork
from dcim.choices import CableTypeChoices
from dcim.models import Cable, Device, FrontPort, Interface, RearPort, Site
from extras.scripts import BooleanVar, ChoiceVar, FileVar, IntegerVar, ObjectVar, Script, StringVar, TextVar
from utilities.exceptions import AbortScript

from local.utils import validate_user, pp_port_update
from local.nice import NiceBulkCircuits, NiceStandardCircuit, NiceP2PCircuit

YYYY_MM_DD = r"^\d{4}-([0]\d|1[0-2])-([0-2]\d|3[01])$"


class StandardCircuit(Script):
    """
    Netbox Custom Script -- StandardCircuit

    This class provides the GUI Interface & Main Entry Point for a Standard Single Circuit Import
    """

    class Meta:
        name = "Standard Circuit"
        description = "Provision one Standard Circuit."
        commit_default = False
        scheduling_enabled = False

        # Organize the GUI Options
        fieldsets = (
            (
                "Enter Circuit Information",
                ("cid", "description", "provider", "circuit_type", "side_a_site", "side_z_providernetwork"),
            ),
            (
                "Cables",
                ("pp", "pp_port", "pp_new_port", "pp_info", "xconnect_id","device", "interface", "direct_to_device", "create_pp_port"),
            ),
            (
                "Other",
                (
                    "port_speed",
                    "upstream_speed",
                    "cir",
                    "install_date",
                    "review",
                    "comments",
                ),
            ),
            # ("Advanced Options", ("overwrite",)),
        )

    # Display Fields
    cid = StringVar(
        label="Circuit ID",
        required=True,
    )
    description = StringVar(
        label="Circuit Description",
        required=False,
    )
    provider = ObjectVar(
        model=Provider,
        label="Circuit Provider",
        required=True,
    )
    circuit_type = ObjectVar(
        model=CircuitType,
        description="Circuit Type",
        required=True,
    )
    side_a_site = ObjectVar(
        model=Site,
        label="NICE Side A",
        required=True,
    )
    side_z_providernetwork = ObjectVar(
        model=ProviderNetwork,
        label="NICE Side Z",
        required=True,
    )
    pp = ObjectVar(model=Device, label="Patch Panel", required=False, query_params={"site_id": "$side_a_site"})
    pp_port = ObjectVar(model=RearPort, label="Patch Panel Port", required=False, query_params={"device_id": "$pp"})
    pp_new_port = IntegerVar(
        label="CREATE Patch Panel Port #:",
        required=False,
    )
    pp_info = StringVar(
        label="Extra Patch Panel Info",
        required=False,
    )
    xconnect_id = StringVar(
        label="Cross Connect ID/Info",
        required=False,
    )
    device = ObjectVar(model=Device, label="Device", required=False, query_params={"site_id": "$side_a_site"})
    interface = ObjectVar(
        model=Interface,
        label="Interface",
        required=False,
        query_params={"device_id": "$device"},
    )
    create_pp_port = BooleanVar(
        label="Create Patch Panel Interface?",
        description="Will be 'Front# and Rear#",
        default=False,
    )
    direct_to_device = BooleanVar(
        label="Cable Direct To Device?",
        description="Check this box ONLY if the Circuit does not flow through a Patch Panel",
        default=False,
    )

    port_speed = IntegerVar(
        label="Port Speed (Kbps)",
        min_value=0,
        required=False,
    )
    upstream_speed = IntegerVar(
        label="Upload Speed (Kbps)",
        min_value=0,
        required=False,
    )
    cir = IntegerVar(
        label="Commit rate",
        min_value=0,
        required=False,
    )
    comments = TextVar(
        label="Comments",
        required=False,
    )
    install_date = StringVar(
        label="Install Date (YYYY-MM-DD)",
        description="Don't know? Use 2021-02-01",
        regex=YYYY_MM_DD,
        default="2021-02-01",
        required=True,
    )
    review = BooleanVar(description="Extra Review Needed?", default=False)
    overwrite = BooleanVar(
        description="Overwrite existing circuits? (same Ciruit ID & Provider == Same Circuit)", default=False
    )

    # Add StandardCircuit
    def run(self, data, commit):
        circuit = NiceStandardCircuit(logger=self, **data)
        circuit.create()


class P2PCircuit(Script):
    """
    Netbox Custom Script -- SingleCircuit

    This class provides the GUI Interface & Main Entry Point for a Single Circuit Import
    """

    class Meta:
        name = "Point to Point Circuit"
        description = "Provision one new Point-to-Point circuit."
        commit_default = False
        scheduling_enabled = False

        # Organize the GUI Options
        fieldsets = (
            (
                "Enter Circuit Information",
                ("cid", "description", "provider", "circuit_type"),
            ),
            (
                "Side A (NICE Side)",
                ("side_a_site",),
            ),
            (
                "Side Z (Carrier Side)",
                ("side_z_site",),
            ),
            ("Cables Side A", ("pp", "pp_port", "pp_new_port", "pp_info", "xconnect_id","device", "interface", "direct_to_device", "create_pp_port")),
            ("Cables Side Z", ("z_pp", "z_pp_port", "z_pp_new_port", "z_pp_info", "xconnect_id","z_device", "z_interface", "z_direct_to_device", "z_create_z_pp_port")),
            (
                "Other",
                (
                    "port_speed",
                    "upstream_speed",
                    "cir",
                    "install_date",
                    "review",
                    "comments",
                ),
            ),
            # ("Advanced Options", ("overwrite",)),
        )

    # Display Fields
    provider = ObjectVar(
        model=Provider,
        label="Circuit Provider",
        required=True,
    )

    circuit_type = ObjectVar(
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
    port_speed = IntegerVar(
        label="Port Speed (Kbps)",
        min_value=0,
        required=False,
    )
    upstream_speed = IntegerVar(
        label="Upload Speed (Kbps)",
        min_value=0,
        required=False,
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
    side_z_site = ObjectVar(
        model=Site,
        label="Site",
        required=False,
    )
    pp = ObjectVar(model=Device, label="Patch Panel", required=False, query_params={"site_id": "$side_a_site"})
    pp_port = ObjectVar(model=RearPort, label="Patch Panel Port", required=False, query_params={"device_id": "$pp"})
    pp_new_port = IntegerVar(
        label="CREATE Patch Panel Port #:",
        description="Will be 'Front# and Back#",
        required=False,
    )
    pp_info = StringVar(
        label="Extra Patch Panel Info",
        required=False,
    )
    xconnect_id = StringVar(
        label="Cross Connect ID/Info",
        required=False,
    )
    device = ObjectVar(model=Device, label="Device", required=False, query_params={"site_id": "$side_a_site"})
    interface = ObjectVar(
        model=Interface,
        label="Interface",
        required=False,
        query_params={"device_id": "$device"},
    )
    direct_to_device = BooleanVar(
        label="Cable Direct To Device?",
        description="Check this box ONLY if the Circuit does not flow through a Patch Panel",
        default=False,
    )

    z_pp = ObjectVar(model=Device, label="Patch Panel Side Z", required=False, query_params={"site_id": "$side_z_site"})
    z_pp_port = ObjectVar(
        model=RearPort, label="Patch Panel Port Side Z", required=False, query_params={"device_id": "$z_pp"}
    )
    z_pp_new_port = IntegerVar(
        label="CREATE Patch Panel Z Port #:",
        description="Will be 'Front# and Back#",
        required=False,
    )
    z_pp_info = StringVar(
        label="Extra Patch Panel Info",
        required=False,
    )
    z_xconnect_id = StringVar(
        label="Cross Connect ID/Info",
        required=False,
    )
    z_device = ObjectVar(model=Device, label="Device Side Z", required=False, query_params={"site_id": "$side_z_site"})
    z_interface = ObjectVar(
        model=Interface,
        label="Interface Side Z",
        required=False,
        query_params={"device_id": "$device_z"},
    )
    z_direct_to_device = BooleanVar(
        label="Cable Direct To Device?",
        description="Check this box ONLY if the Circuit does not flow through a Patch Panel",
        default=False,
    )

    comments = TextVar(
        label="Comments",
        required=False,
    )
    install_date = StringVar(
        label="Install Date (YYYY-MM-DD)",
        description="Don't know? Use 2021-02-01",
        required=True,
    )
    overwrite = BooleanVar(
        description="Overwrite existing circuits? (same Ciruit ID & Provider == Same Circuit)",
        default=False,
    )
    create_pp_port = BooleanVar(
        label="Create Patch Panel Interface?",
        description="Will be 'Front# and Back#",
        default=False,
    )
    create_z_pp_port = BooleanVar(
        label="Create Patch Panel (Z Side) Interface?",
        description="Will be 'Front# and Back#",
        default=False,
    )

    # Add P2PCircuit
    def run(self, data, commit):
        circuit = NiceP2PCircuit(logger=self, **data)
        circuit.create()


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
            ("Advanced Options", ("overwrite", "circuit_num")),
        )

    # Display fields
    bulk_circuits = FileVar(
        label="Import CSV",
        description="Bulk Import Circuits",
        required=True,
    )

    overwrite = BooleanVar(
        description="Overwrite existing circuits? (same Ciruit ID & Provider == Same Circuit)", default=False
    )

    circuit_num = IntegerVar(label="Circuit/Line Number", required=False)

    # Run BulkCircuits
    def run(self, data, commit):
        # Check if this user is allowed to run Bulk Circuit updates
        allowed = validate_user(user=self.request.user)
        if not allowed:
            raise AbortScript(f"User '{self.request.user}' does not have permission to run this script.")

        circuits = NiceBulkCircuits.from_csv(
            logger=self, overwrite=data["overwrite"], filename=data["bulk_circuits"], circuit_num=data["circuit_num"]
        )
        for circuit in circuits:
            circuit.create()


class UpdatePatchPanelPorts(Script):
    """
    Netbox Custom Script -- UpdatePatchPanelPorts

    This class provides the GUI Interface & Main Entry Point for Updating Patch Panel Port Names
    """

    class Meta:
        name = "Update Patch Panel Port Names"
        description = "Swap/Standardize on Patch Panel Port Names, for existing Patch Panels"
        commit_default = False
        scheduling_enabled = False

        # Organize the GUI Options
        fieldsets = (
            ("Patch Panel", ("site", "pp", "pp_frontport", "pp_rearport")),
            ("Front Ports", ("old_frontport_name", "new_frontport_name")),
            ("Rear Ports", ("old_rearport_name", "new_rearport_name")),
            ("Other", ("revert_if_failed",)),
        )

    site = ObjectVar(
        model=Site,
        description="Only used to help filter available patch panels",
        required=False,
    )
    pp = ObjectVar(model=Device, label="Patch Panel", required=True, query_params={"site_id": "$site"})
    pp_frontport = ObjectVar(
        model=FrontPort,
        label="Existing/Example FrontPort Names",
        description="Only used to help confirm existing port names",
        required=False,
        query_params={"device_id": "$pp"},
    )
    pp_rearport = ObjectVar(
        model=RearPort,
        label="Existing/Example FrontPort Names",
        description="Only used to help confirm existing port names",
        required=False,
        query_params={"device_id": "$pp"},
    )

    old_frontport_name = StringVar(
        label="Old FrontPort Name",
        required=True,
    )
    new_frontport_name = StringVar(
        label="New FrontPort Name",
        required=True,
    )
    old_rearport_name = StringVar(
        label="Old RearPort Name",
        required=True,
    )
    new_rearport_name = StringVar(
        label="New RearPort Name",
        required=True,
    )
    revert_if_failed = BooleanVar(label="Revert changes if any renames fail?", default=True, required=False)

    def run(self, data, commit):
        del data["pp_frontport"]
        del data["pp_rearport"]
        del data["site"]

        pp_port_update(logger=self, **data)


script_order = (StandardCircuit, P2PCircuit, BulkCircuits, UpdatePatchPanelPorts)
name = "NICE InContact Single Circuit Manager"
