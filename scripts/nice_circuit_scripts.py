from circuits.models import Circuit
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
                    "pp_port_description",
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
        pp_port_description,
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
        _ = circuit.create()


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
                    "pp_port_description",
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
                    "z_pp_port_description",
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
        pp_port_description,
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
        z_pp_port_description,
        z_xconnect_id,
    )

    # Add P2PCircuit
    def run(self, data, commit):
        circuit = NiceP2PCircuit(logger=self, **data)
        _ = circuit.create()


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
        results = {}
        for circuit in circuits:
            result = circuit.create()
            results[circuit.cid] = {"result": result, "description": circuit.description}

        # Output
        output_success = "| Circuit ID | Description |\n"
        output_success += "|------------|-------------|\n"
        success_count = 0
        for cid, result in results.items():
            if result["result"]:
                success_count += 1
                output_success += f"| {cid} | {result['description']}|\n"

        output_fail = "| Circuit ID | Description |\n"
        output_fail += "|------------|-------------|\n"
        fail_count = 0
        for cid, result in results.items():
            if not result["result"]:
                fail_count += 1
                output_fail += f"| {cid} | {result['description']}|\n"

        if success_count:
            self.log_info("---")
            self.log_success("**Successes:**")
            self.log_success(output_success)
        if fail_count:
            self.log_info("---")
            self.log_failure("**Failures:**")
            self.log_failure(output_fail)


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
        label="Existing/Example RearPort Names",
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


class CircuitCableReport(Script):
    class Meta:
        name = "Circuit Cable Report"
        commit_default = False
        scheduling_enabled = False
        description = "Retrieve Circuits that do not have a cable terminated on either side."

    def get_site_name(self, circuit):
        site_name = "Unknown"
        for term in circuit.terminations.all():
            if isinstance(term.site, Site):
                site_name = term.site.name
                break
        return site_name

    def circuit_cables(self, data):
        # Get the Circuits
        site = data.get("site")
        show_all = data.get("show_all", False)

        if site:
            circuits_a = Circuit.objects.filter(termination_a__site__name=site.name)
            circuits_z = Circuit.objects.filter(termination_z__site__name=site.name)
            circuits = circuits_a | circuits_z
        else:
            circuits = Circuit.objects.all()

        circuits_with = []
        circuits_without = []

        # Build the lists
        for circuit in circuits:
            terms = circuit.terminations.all()
            cable_count = sum(1 for term in terms if term.cable)
            if cable_count > 0:
                circuits_with.append(circuit)
            else:
                circuits_without.append(circuit)

        # Log Output
        output = "| Circuit ID | Description | Site | Cable(s) Exist |\n"
        output += "|------------|-------------|------|----------|\n"

        if show_all:
            for circuit in circuits_with:
                site_name = self.get_site_name(circuit)
                output += f"| {circuit.cid} | {circuit.description} | {site_name} | True\n"

        for circuit in circuits_without:
            site_name = self.get_site_name(circuit)
            output += f"| {circuit.cid} | {circuit.description} | {site_name} | False\n"

        output += "<br/>"
        output += "<br/>"
        if show_all:
            output += f"With Cables: {len(circuits_with)}<br/>"
        output += f"Without Cables: {len(circuits_without)}<br/>"
        output += f"Total Circuits: {len(circuits)}\n"
        self.log_info(output)

    site = ObjectVar(
        model=Site,
        description="Limit Report to only this Site",
        required=False,
    )
    show_all = BooleanVar(
        label="Show All Circuits (WITH and without cables)",
        description="Unchecked will only show circuits missing/without cables.",
        default=False,
    )

    def run(self, data, commit):
        commit = False
        self.circuit_cables(data)


script_order = (StandardCircuit, P2PCircuit, BulkCircuits, UpdatePatchPanelPorts, CircuitCableReport)
name = "NICE InContact Single Circuit Manager"
