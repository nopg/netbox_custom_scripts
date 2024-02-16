from circuits.choices import CircuitStatusChoices
from circuits.models import CircuitType, Provider, ProviderNetwork
from dcim.choices import CableTypeChoices
from dcim.models import Cable, Device, Interface, RearPort, Site
from extras.scripts import BooleanVar, ChoiceVar, FileVar, IntegerVar, ObjectVar, Script, StringVar, TextVar
from utilities.exceptions import AbortScript

from local.utils import load_data_from_csv, prepare_netbox_data, validate_user, get_side_by_name, prepare_pp_ports, validate_date
from local.main import main_circuits_bulk, main_circuit_single, main_standard_circuit


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
                ("cid", "description", "provider", "type", "side_a_site", "side_z_providernetwork"),
            ),
            ("Cables", ("pp", "pp_port", "pp_new_port", "device", "interface", "cable_direct_to_device", "create_pp_port")),
            (
                "Other",
               ("port_speed", "upload_speed", "cir", "install_date", "termination_date", "cross_connect", "pp_info","comments"),
            ),
            ("Advanced Options", ("overwrite",)),
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
    type = ObjectVar(
        model=CircuitType,
        description="Circuit Type",
        required=True,
    )
    side_a_site = ObjectVar(
        model=Site,
        label="Side A (NICE)",
        required=True,
    )
    side_z_providernetwork = ObjectVar(
        model=ProviderNetwork,
        label="Side Z (Carrier)",
        required=True,
    )
    pp = ObjectVar(model=Device, label="Patch Panel", required=False, query_params={"site_id": "$side_a_site"})
    pp_port = ObjectVar(model=RearPort, label="Patch Panel Port", required=False, query_params={"device_id": "$pp"})
    pp_new_port = IntegerVar(
        label="CREATE Patch Panel Port #:",
        required=False,
    )

    device = ObjectVar(model=Device, label="Device", required=False, query_params={"site_id": "$side_a_site"})
    interface = ObjectVar(
        model=Interface,
        label="Interface",
        required=False,
        query_params={"device_id": "$device"},
    )
    cable_direct_to_device = BooleanVar(
        label="Cable Direct To Device?",
        description="Check this box ONLY if the Circuit does not flow through a Patch Panel",
        default=False
    )
    create_pp_port = BooleanVar(
        label = "Create Patch Panel Interface?",
        default=False,
    )
    port_speed = IntegerVar(
        label="Port Speed (Kbps)",
        min_value=0,
        required=False,
    )
    upload_speed = IntegerVar(
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
        required=True,
    )
    termination_date = StringVar(
        label="Termination Date (YYYY-MM-DD)",
        regex=YYYY_MM_DD,
        required=True,
    )
    cross_connect = StringVar(
        label="Cross Connect ID/Info",
        required=False,
    )
    pp_info = StringVar(
        label="Extra Patch Panel Info",
        required=False,
    )
    overwrite = BooleanVar(description="Overwrite existing circuits? (same Ciruit ID & Provider == Same Circuit)", default=False)

    # Run SingleCircuit
    def run(self, data, commit):
        output = main_standard_circuit(data=data, logger=self)
        if output:
            return output
        # log final job status as failed/completed better (abortscript)


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
                ("provider", "type", "cid", "description", "status"),
            ),
            (
                "Side A (NICE Side)",
                ("side_a_site", "side_a_providernetwork"),
            ),
            (
                "Side Z (Carrier Side)",
                ("side_z_site", "side_z_providernetwork"),
            ),
            ("Cables", ("pp", "pp_port", "device", "interface", "cable_type")),
            (
                "Other",
               ("cir", "install_date", "termination_date", "comment", "cable_direct_to_device", "cross_connect"),
            ),
            ("P2P Circuits", ("pp_z", "pp_z_port", "device_z", "interface_z", "cable_z_type")),
            ("Advanced Options", ("overwrite","create_pp_port", "create_pp_z_port")),
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
    pp = ObjectVar(model=Device, label="Patch Panel", required=False, query_params={"site_id": "$side_a_site"})
    pp_port = ObjectVar(model=RearPort, label="Patch Panel Port", required=False, query_params={"device_id": "$pp"})

    device = ObjectVar(model=Device, label="Device", required=False, query_params={"site_id": "$side_a_site"})
    interface = ObjectVar(
        model=Interface,
        label="Interface",
        required=False,
        query_params={"device_id": "$device"},
    )
    cable_type = ChoiceVar(
        CableTypeChoices,
        default=CableTypeChoices.TYPE_SMF,
        label="Cable Type",
        required=False,     
    )

    pp_z = ObjectVar(model=Device, label="Patch Panel Side Z", required=False)
    pp_z_port = ObjectVar(model=RearPort, label="Patch Panel Port Side Z", required=False, query_params={"device_id": "$pp_z"})
    device_z = ObjectVar(model=Device, label="Device Side Z", required=False, query_params={"site_id": "$side_z_site"})
    interface_z = ObjectVar(
        model=Interface,
        label="Interface Side Z",
        required=False,
        query_params={"device_id": "$device_z"},
    )
    cable_z_type = ChoiceVar(
        CableTypeChoices,
        default=CableTypeChoices.TYPE_SMF,
        label="Cable Type Side Z",
        required=False,     
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
    cross_connect = StringVar(
        label="Cross Connect ID/Info",
        required=False,
    )
    overwrite = BooleanVar(description="Overwrite existing circuits? (same Ciruit ID & Provider == Same Circuit)", default=False)
    cable_direct_to_device = BooleanVar(
        label="Cable Direct To Device?",
        description="Check this box ONLY if the Circuit does not flow through a Patch Panel",
        default=False
    )
    create_pp_port = BooleanVar(
        label = "Create Patch Panel Interface?",
        default=False,
    )
    create_pp_z_port = BooleanVar(
        label = "Create Patch Panel (Z Side) Interface?",
        default=False,
    )

    # Run SingleCircuit
    def run(self, data, commit):
        # Validate Form Data
        if data["side_a_site"] and data["side_a_providernetwork"]:
            raise AbortScript(f"Circuit {data['cid']} cannot have Side A Site AND Side A Provider Network Simultaneously")
        if data["side_z_site"] and data["side_z_providernetwork"]:
            raise AbortScript(f"Circuit {data['cid']} cannot have Side Z Site AND Side Z Provider Network Simultaneously")
        
        # FIX BELOW / Create FUNCITON?
        side_a = get_side_by_name(data["side_a_site"], data["side_a_providernetwork"])
        side_z = get_side_by_name(data["side_z_site"], data["side_z_providernetwork"])
        if type(side_a) == Site:
            site = side_a
        elif type(side_a) == ProviderNetwork:
            if not skip:
                skip = ""
            skip += "\nSide Z to Device/Patch Panel without Side A Device/Patch Panel is currently unsupported."
            site = None
        else:
            site = None
        data["side_a"] = side_a
        data["side_z"] = side_z
        
        data["pp_frontport"] = prepare_pp_ports(data["pp_port"])
        data["pp_z_frontport"] = prepare_pp_ports(data["pp_z_port"])

        # set rear/front port (create function)
        rear_port = data.get("pp_port")
        # check date is real (create function)

        if rear_port:
            data["pp_front_port"] = rear_port.frontports.all()[0]

        # Single Circuits are NOT allowed to skip cable creation
        data["allow_cable_skip"] = False

        # Run Script
        output = main_circuit_single(netbox_row=data, logger=self)
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
        description="Overwrite existing circuits? (same Ciruit ID & Provider == Same Circuit)", default=False
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
        main_circuits_bulk(circuits_csv=data["bulk_circuits"], overwrite=data["overwrite"], logger=self)
        
        # log final job status as failed/completed better (abortscript)


script_order = (StandardCircuit, P2PCircuit, BulkCircuits)
name = "NICE InContact Single Circuit Manager"


# class SingleCircuit(Script):
#     """
#     Netbox Custom Script -- SingleCircuit

#     This class provides the GUI Interface & Main Entry Point for a Single Circuit Import
#     """
#     class Meta:
#         name = "Single Circuit"
#         description = "Provision one new circuit."
#         commit_default = False
#         scheduling_enabled = False

#         # Organize the GUI Options
#         fieldsets = (
#             (
#                 "Enter Circuit Information",
#                 ("provider", "type", "cid", "description", "status"),
#             ),
#             (
#                 "Side A (NICE Side)",
#                 ("side_a_site", "side_a_providernetwork"),
#             ),
#             (
#                 "Side Z (Carrier Side)",
#                 ("side_z_site", "side_z_providernetwork"),
#             ),
#             ("Cables", ("pp", "pp_port", "device", "interface", "cable_type")),
#             (
#                 "Other",
#                ("cir", "install_date", "termination_date", "comment", "cable_direct_to_device", "cross_connect"),
#             ),
#             ("P2P Circuits", ("pp_z", "pp_z_port", "device_z", "interface_z", "cable_z_type")),
#             ("Advanced Options", ("overwrite","create_pp_port", "create_pp_z_port")),
#         )

#     # Display Fields
#     provider = ObjectVar(
#         model=Provider,
#         label="Circuit Provider",
#         required=True,
#     )

#     type = ObjectVar(
#         model=CircuitType,
#         description="Circuit Type",
#         required=True,
#     )
#     cid = StringVar(
#         label="Circuit ID",
#         required=True,
#     )
#     description = StringVar(
#         label="Circuit Description",
#         required=False,
#     )
#     status = ChoiceVar(
#         CircuitStatusChoices,
#         default=CircuitStatusChoices.STATUS_ACTIVE,
#         label="Circuit Status",
#         required=True,
#     )
#     cir = IntegerVar(
#         label="Commit rate",
#         min_value=0,
#         required=False,
#     )
#     side_a_site = ObjectVar(
#         model=Site,
#         label="Site",
#         required=False,
#     )
#     side_a_providernetwork = ObjectVar(
#         model=ProviderNetwork,
#         label="Provider",
#         required=False,
#     )
#     side_z_site = ObjectVar(
#         model=Site,
#         label="Site",
#         required=False,
#     )
#     side_z_providernetwork = ObjectVar(
#         model=ProviderNetwork,
#         label="Provider",
#         required=False,
#     )
#     pp = ObjectVar(model=Device, label="Patch Panel", required=False, query_params={"site_id": "$side_a_site"})
#     pp_port = ObjectVar(model=RearPort, label="Patch Panel Port", required=False, query_params={"device_id": "$pp"})

#     device = ObjectVar(model=Device, label="Device", required=False, query_params={"site_id": "$side_a_site"})
#     interface = ObjectVar(
#         model=Interface,
#         label="Interface",
#         required=False,
#         query_params={"device_id": "$device"},
#     )
#     cable_type = ChoiceVar(
#         CableTypeChoices,
#         default=CableTypeChoices.TYPE_SMF,
#         label="Cable Type",
#         required=False,     
#     )

#     pp_z = ObjectVar(model=Device, label="Patch Panel Side Z", required=False)
#     pp_z_port = ObjectVar(model=RearPort, label="Patch Panel Port Side Z", required=False, query_params={"device_id": "$pp_z"})
#     device_z = ObjectVar(model=Device, label="Device Side Z", required=False, query_params={"site_id": "$side_z_site"})
#     interface_z = ObjectVar(
#         model=Interface,
#         label="Interface Side Z",
#         required=False,
#         query_params={"device_id": "$device_z"},
#     )
#     cable_z_type = ChoiceVar(
#         CableTypeChoices,
#         default=CableTypeChoices.TYPE_SMF,
#         label="Cable Type Side Z",
#         required=False,     
#     )

#     comment = StringVar(
#         label="Comment",
#         required=False,
#     )
#     install_date = StringVar(
#         label="Install Date (YYYY-MM-DD)",
#         description="Don't know? Use 2021-02-01",
#         required=True,
#     )
#     termination_date = StringVar(
#         label="Termination Date (YYYY-MM-DD)",
#         required=True,
#     )
#     cross_connect = StringVar(
#         label="Cross Connect ID/Info",
#         required=False,
#     )
#     overwrite = BooleanVar(description="Overwrite existing circuits? (same Ciruit ID & Provider == Same Circuit)", default=False)
#     cable_direct_to_device = BooleanVar(
#         label="Cable Direct To Device?",
#         description="Check this box ONLY if the Circuit does not flow through a Patch Panel",
#         default=False
#     )
#     create_pp_port = BooleanVar(
#         label = "Create Patch Panel Interface?",
#         default=False,
#     )
#     create_pp_z_port = BooleanVar(
#         label = "Create Patch Panel (Z Side) Interface?",
#         default=False,
#     )

#     # Run SingleCircuit
#     def run(self, data, commit):
#         # Validate Form Data
#         if data["side_a_site"] and data["side_a_providernetwork"]:
#             raise AbortScript(f"Circuit {data['cid']} cannot have Side A Site AND Side A Provider Network Simultaneously")
#         if data["side_z_site"] and data["side_z_providernetwork"]:
#             raise AbortScript(f"Circuit {data['cid']} cannot have Side Z Site AND Side Z Provider Network Simultaneously")
        
#         # FIX BELOW / Create FUNCITON?
#         side_a = get_side_by_name(data["side_a_site"], data["side_a_providernetwork"])
#         side_z = get_side_by_name(data["side_z_site"], data["side_z_providernetwork"])
#         if type(side_a) == Site:
#             site = side_a
#         elif type(side_a) == ProviderNetwork:
#             if not skip:
#                 skip = ""
#             skip += "\nSide Z to Device/Patch Panel without Side A Device/Patch Panel is currently unsupported."
#             site = None
#         else:
#             site = None
#         data["side_a"] = side_a
#         data["side_z"] = side_z
        
#         data["pp_frontport"] = prepare_pp_ports(data["pp_port"])
#         data["pp_z_frontport"] = prepare_pp_ports(data["pp_z_port"])

#         # set rear/front port (create function)
#         rear_port = data.get("pp_port")
#         # check date is real (create function)

#         if rear_port:
#             data["pp_front_port"] = rear_port.frontports.all()[0]

#         # Single Circuits are NOT allowed to skip cable creation
#         data["allow_cable_skip"] = False

#         # Run Script
#         output = main_circuit_single(netbox_row=data, logger=self)
#         if output:
#             return output
#         # log final job status as failed/completed better (abortscript)