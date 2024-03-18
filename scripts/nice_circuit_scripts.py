from dcim.models import Device, FrontPort, RearPort, Site
from extras.scripts import BooleanVar, ObjectVar, Script, StringVar
from local.nice_circuits import NiceBulkCircuits, NiceP2PCircuit, NiceStandardCircuit
from local.utils import pp_port_update, validate_user
from utilities.exceptions import AbortScript


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

        # Organize the GUI Layout
        fieldsets = (
            (
                "Enter Circuit Information",
                ("cid", "description", "bun", "provider", "circuit_type", "side_a_site", "side_z_providernetwork"),
            ),
            (
                "Cables",
                (
                    "pp",
                    "pp_port",
                    "pp_new_port",
                    "pp_info",
                    "xconnect_id",
                    "device",
                    "interface",
                    "direct_to_device",
                    "create_pp_port",
                ),
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

    from local.display_fields import (
        bun,
        cid,
        cir,
        circuit_type,
        comments,
        create_pp_port,
        description,
        device,
        direct_to_device,
        install_date,
        interface,
        port_speed,
        pp,
        pp_info,
        pp_new_port,
        pp_port,
        provider,
        review,
        side_a_site,
        side_z_providernetwork,
        upstream_speed,
        xconnect_id,
    )

    # Add StandardCircuit
    def run(self, data, commit):
        circuit = NiceStandardCircuit(logger=self, **data)
        circuit.create()


class P2PCircuit(Script):
    """
    Netbox Custom Script -- P2PCircuit

    This class provides the GUI Interface & Main Entry Point for a Single Point-to-Point Circuit Import
    """

    class Meta:
        name = "Point to Point Circuit"
        description = "Provision one new Point-to-Point circuit."
        commit_default = False
        scheduling_enabled = False

        # Organize the GUI Layout
        fieldsets = (
            (
                "Enter Circuit Information",
                ("cid", "description", "bun", "provider", "circuit_type", "side_a_site", "side_z_site"),
            ),
            (
                "Cables Side A",
                (
                    "pp",
                    "pp_port",
                    "pp_new_port",
                    "pp_info",
                    "xconnect_id",
                    "device",
                    "interface",
                    "direct_to_device",
                    "create_pp_port",
                ),
            ),
            (
                "Cables Side Z",
                (
                    "z_pp",
                    "z_pp_port",
                    "z_pp_new_port",
                    "z_pp_info",
                    "z_xconnect_id",
                    "z_device",
                    "z_interface",
                    "z_direct_to_device",
                    "z_create_pp_port",
                ),
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

    from local.display_fields import (
        bun,
        cid,
        cir,
        circuit_type,
        comments,
        create_pp_port,
        description,
        device,
        direct_to_device,
        install_date,
        interface,
        port_speed,
        pp,
        pp_info,
        pp_new_port,
        pp_port,
        provider,
        review,
        side_a_site,
        side_z_site,
        upstream_speed,
        xconnect_id,
        z_create_pp_port,
        z_device,
        z_direct_to_device,
        z_interface,
        z_pp,
        z_pp_info,
        z_pp_new_port,
        z_pp_port,
        z_xconnect_id,
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

        # Organize the GUI Layout
        fieldsets = (
            ("Import CSV", ("bulk_circuits",)),
            ("Advanced Options", ("circuit_num", "overwrite")),
        )

    from local.display_fields import bulk_circuits, circuit_num, overwrite

    # Run BulkCircuits
    def run(self, data, commit):
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

    This class provides the GUI Interface & Main Entry Point for the Update Patch Panel Port Names Tool
    """

    class Meta:
        name = "Update Patch Panel Port Names"
        description = "Swap/Standardize on Patch Panel Port Names, for existing Patch Panels"
        commit_default = False
        scheduling_enabled = False

        # Organize the GUI Layout
        fieldsets = (
            ("Patch Panel", ("site", "pp", "pp_frontport", "pp_rearport")),
            ("Front Ports", ("old_frontport_name", "new_frontport_name")),
            ("Rear Ports", ("old_rearport_name", "new_rearport_name")),
            ("Other", ("revert_if_failed",)),
        )

    # Unique, so not imported from local.display_fields
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

    # Update Patch Panel Port Names
    def run(self, data, commit):
        # Remove unnecessary keys
        del data["pp_frontport"]
        del data["pp_rearport"]
        del data["site"]

        pp_port_update(logger=self, **data)


script_order = (StandardCircuit, P2PCircuit, BulkCircuits, UpdatePatchPanelPorts)
name = "NICE InContact Single Circuit Manager"
