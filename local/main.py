from extras.scripts import Script
from local.utils import build_circuit, build_pp_cable, build_cable, build_terminations, load_data_from_csv, prepare_netbox_data

def main_circuit_single(self: Script, netbox_row: dict[str, any]):
    """
    Entry Point for Single Circuit Import
    """    
    circuit = build_circuit(self, netbox_row)
    ct_side_a, ct_side_z = build_terminations(self, netbox_row, circuit)

    build_pp_cable(self, netbox_row, circuit)

    if netbox_row["interface"]:
        build_cable(self, side_a=netbox_row["interface"], side_b=netbox_row["pp_front_port"])
    else:
        self.log_warning(f"Skipping cable creation to device interface due to missing interface on device '{circuit.cid}")

def main_circuits_bulk(self: Script, circuits_csv: list[dict[str, any]], overwrite: bool) -> None:
    """
    Entry Point for Bulk Circuits Import

    Just loops through Single Circuit Import
    """
    # # Bulk Circuits are allowed to skip cable creation
    allow_cable_skip = True

    # Prepare CSV for Netbox
    csv_data = load_data_from_csv(circuits_csv)
    netbox_data = prepare_netbox_data(csv_data, overwrite=overwrite, allow_cable_skip=allow_cable_skip)

    # Loop through circuits
    for netbox_row in netbox_data:
        if netbox_row["skip"]:
            self.log_warning(f"Skipping circuit \'{netbox_row['cid']}\' due to: {netbox_row['skip']}")
        else:
            main_circuit_single(self, netbox_row)


# Check/should already have circuit data for blank circuit
# Check/should be easy to add terminations to site/PN
# Check if enough info to build cable (s?!)
# If allow_cable_skip -- log and continue building
# Elso, log failure and end this row (single will end, bulk will move to next circuit)