from circuits.models import Circuit, ProviderNetwork
from dcim.models import Cable, Site
from extras.scripts import Script
from utilities.exceptions import AbortScript

from local.utils import build_circuit, build_cable, build_terminations, load_data_from_csv, prepare_netbox_data, prepare_pp_ports,save_cables, validate_date


def build_device_cable(logger, side_a, row):
    if row["device"] and row["interface"] and side_a:
        device_cable = build_cable(logger, side_a=side_a, side_b=row["interface"])
        logger.log_info(f"Built Cable to Device for {row['cid']}.")
        return device_cable
    else:
        if row["allow_cable_skip"]:
            logger.log_warning(f"Unable to create cable to the device for circuit: {row['cid']}")            
        else:
            raise AbortScript(f"Error, not allowed to skip cable creation, and unable to create cable to device for circuit: {row['cid']}")

def build_pp_device_cable(logger, side_a, row):
    if row["device"] and row["interface"] and side_a:
        device_cable = build_cable(logger, side_a=side_a, side_b=row["interface"])
        logger.log_info(f"Built Cable to Device for {row['cid']}.")
        return device_cable
    else:
        if row["allow_cable_skip"]:
            logger.log_warning(f"Unable to create cable to the device for circuit: {row['cid']}")            
        else:
            raise AbortScript(f"Error, not allowed to skip cable creation, and unable to create cable to device for circuit: {row['cid']}")

def build_pp_cable(logger: Script, netbox_row: dict, circuit: Circuit) -> Cable | None:
    if netbox_row["pp"] and netbox_row["pp_port"] and netbox_row["pp_frontport"]:
        pp_cable = build_cable(logger, side_a=circuit.termination_a, side_b=netbox_row["pp_port"])
        logger.log_info(f"Built Cable to Patch Panel for {circuit.cid}")
        return pp_cable
    else:
        if netbox_row["allow_cable_skip"]:
            logger.log_warning(f"Unable to create cable to Patch Panel for circuit: {circuit.cid}")
        else:
            raise AbortScript(f"Error, not allowed to skip cable creation, and unable to create cable to Patch Panel on circuit: {circuit.cid}")


def main_standard_circuit(data: dict[str,any], logger: Script) -> None:
    """
    Entry Point for Standard Single Circuit
    """
    validate_date(data["install_date"])
    validate_date(data["termination_date"])

    # Single Circuits are NOT allowed to skip cable creation
    data["allow_cable_skip"] = False
    
    # FIX BELOW / Create FUNCITON?
    data["side_a"] = data["side_a_site"]
    data["side_z"] = data["side_z_providernetwork"]
    data["pp_frontport"] = prepare_pp_ports(data["pp_port"])

    # # set rear/front port (create function)
    # rear_port = data.get("pp_port")
    # # check date is real (create function)

    # if rear_port:
    #     data["pp_front_port"] = rear_port.frontports.all()[0]

    # Begin:
    circuit = build_circuit(logger, data)
    ct_a, ct_z = build_terminations(logger, data, circuit)
    
    if data["cable_direct_to_device"] and (data["pp"] or data["pp_port"]):
        raise AbortScript(f"Error: Cable Direct to Device chosen, but Patch Panel also Selected.")
    elif not data["cable_direct_to_device"] and (not data["pp"] or not data["pp_port"]):
        raise AbortScript(f"Error: Patch Panel missing, and 'Cable Direct to Device' is not checked.")
    elif data["cable_direct_to_device"]:
        pp_cable = None
        device_cable = build_device_cable(logger, side_a=ct_a, row=data)
    else:
        pp_cable = build_pp_cable(logger, data, circuit)
        device_cable = build_pp_device_cable(logger, data["pp_frontport"], data)
    
    save_cables(logger, pp_cable, device_cable)

def main_circuit_single(logger: Script, netbox_row: dict[str, any]):
    """
    Entry Point for Single Circuit Import
    """    
    
    # Create (don't save) circuit
    circuit = build_circuit(logger, netbox_row)

    # Create (don't save) terminations (to site or PN)
    ct_a, ct_z = build_terminations(logger, netbox_row, circuit)

    # Check PP & Interface
    # Check Device & Interface
    # Build Cable to PP (prolly, or device)
    # Build Cable from PP to Device

    if isinstance(netbox_row["side_a"], ProviderNetwork):
        raise AbortScript(f"Side A to Provider Networks currently not implemented: {netbox_row['circuit'].cid}")
    
    if isinstance(netbox_row["side_a"], Site):
        if netbox_row["cable_direct_to_device"]:
            pp_cable = None
            device_cable = build_device_cable(logger, side_a=circuit.termination_a, row=netbox_row)
        else:
            pp_cable = build_pp_cable(logger, netbox_row, circuit)
            device_cable = build_pp_device_cable(logger, netbox_row["pp_frontport"], netbox_row)

    if isinstance(netbox_row["side_z"], Site):
        raise AbortScript(f"Side Z to a Site is currently not implemented: {netbox_row['circuit'].cid}")
    
    if isinstance(netbox_row["side_z"], ProviderNetwork):
        # Nothing else to do?
        pass

    save_cables(logger, pp_cable, device_cable)

    # if netbox_row["interface"]:
    #     build_cable(self, side_a=netbox_row["interface"], side_b=netbox_row["pp_front_port"])
    # else:
    #     logger.log_warning(f"Skipping cable creation to device interface due to missing interface on device '{circuit.cid}")

def main_circuits_bulk(logger: Script, circuits_csv: list[dict[str, any]], overwrite: bool) -> None:
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
            logger.log_warning(f"Skipping circuit \'{netbox_row['cid']}\' due to: {netbox_row['skip']}")
        else:
            main_circuit_single(logger, netbox_row)


# Check/should already have circuit data for blank circuit
# Check/should be easy to add terminations to site/PN
# Check if enough info to build cable (s?!)
# If allow_cable_skip -- log and continue building
# Elso, log failure and end this row (single will end, bulk will move to next circuit)