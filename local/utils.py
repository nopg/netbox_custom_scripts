import csv
import codecs
import dateutil.parser as date_parser
from dateutil.parser import ParserError

from django.core.exceptions import ValidationError
from extras.scripts import Script

from circuits.choices import CircuitStatusChoices
from circuits.models import Circuit, CircuitType, Provider, ProviderNetwork, CircuitTermination
from dcim.choices import CableTypeChoices
from dcim.models import Cable, Device, Interface, RearPort, Site
from utilities.choices import ColorChoices
from utilities.exceptions import AbortScript

from local.validators import MyCircuitValidator
import re

from django.core.files.uploadedfile import InMemoryUploadedFile

BULK_SCRIPT_ALLOWED_USERS = ["netbox", "danny.berman", "joe.deweese", "loran.fuchs"]

HEADER_MAPPING = {
    "Circuit ID": "cid",
    "NICE Script Type": "nice_script_type",
    "Provider": "provider",
    "Circuit Type": "circuit_type",
    "Side A Site": "side_a_site",
    "Side A Provider Network": "side_a_providernetwork",
    "Patch Panel": "pp",
    "PP Port": "pp_port",
    "Device": "device",
    "Interface": "interface",
    "Side Z Site": "side_z_site",
    "Side Z Provider Network": "side_z_providernetwork",
    "Description": "description",
    "Install Date": "install_date",
    "Commit Rate (Kbps)": "cir",
    "Comments": "comments",
    "Patch Panel Z": "z_pp",
    "PP Port Z": "z_pp_port",
    "Device Z": "z_device",
    "Interface Z": "z_interface",
    "Cable Direct To Device": "direct_to_device",
    "Cross Connect": "xconnect_id",
    "Z Cross Connect": "z_xconnect_id",
    "Cable Type": "cable_type",
    "Allow Skip": "allow_skip",
    "Review": "review",
    "Overwrite": "overwrite",
    "Create PP Port": "create_pp_port",
    "Create PP Z Port": "create_z_pp_port",
    "Cable Z Direct To Device": "z_direct_to_device",
}


def handle_errors(logger: Script, error: str, skip: bool = False):
    """
    Handle errors based on the skip parameter.
    """
    if skip:
        logger(error)
    else:
        raise AbortScript(error)


def fix_bools(value) -> None:
    if isinstance(value, bool):
        return value
    return value.lower() == "true"


def validate_date(date_str: str) -> str:
    """
    Validate the date string format and return the ISO formatted date.
    """
    error = f"Invalid date ({date_str}), should be YYYY-MM-DD"
    try:
        date = date_parser.parse(date_str)
        if not 1980 <= date.year <= 2036:
            raise AbortScript(f"Date: {date_str} is outside constraints: Minimum year: 1980, Maximum year: 2026")
    except (ParserError, ValueError, TypeError):
        raise AbortScript(error)
    return date.date().isoformat()


def validate_user(user) -> bool:
    """
    Validate if the user is allowed to perform bulk operations.
    """
    return user.username in BULK_SCRIPT_ALLOWED_USERS


def get_provider_by_name(name: str) -> Provider | None:
    """
    Retrieve a provider by name.
    """
    return Provider.objects.filter(name=name).first()


def get_provider_network_by_name(name: str) -> ProviderNetwork | None:
    """
    Retrieve a provider network by name.
    """
    return ProviderNetwork.objects.filter(name=name).first()


def get_circuit_type_by_name(name: str) -> CircuitType | None:
    """
    Retrieve a circuit type by name.
    """
    return CircuitType.objects.filter(name=name).first()


def get_site_by_name(name: str) -> Site | None:
    """
    Retrieve a site by name.
    """
    return Site.objects.filter(name=name).first()


def get_device_by_name(name: str, site: Site = None) -> Device | None:
    """
    Retrieve a device by name.
    """
    if site:
        return Device.objects.filter(name=name, site=site).first()
    return Device.objects.filter(name=name).first()


def get_interface_by_name(name: str, device: Device = None) -> Interface | None:
    """
    Retrieve an interface by name.
    """
    if device:
        return Interface.objects.filter(name=name, device=device).first()
    return Interface.objects.filter(name=name).first()


def get_rearport_by_name(name: str, device: Device = None) -> RearPort | None:
    """
    Retrieve a rear port by name.
    """
    if device:
        return RearPort.objects.filter(name=name, device=device).first()
    return RearPort.objects.filter(name=name).first()


def get_side_by_name(side_site, side_providernetwork) -> Site | ProviderNetwork:
    """
    Retrieve a site or provider network by name.
    """
    side = get_site_by_name(side_site)
    if not side:
        side = get_provider_network_by_name(side_providernetwork)
    return side


def load_data_from_csv(filename) -> list[dict]:
    """
    Load data from a CSV file and map header names to new names.
    """
    if not isinstance(filename, InMemoryUploadedFile):
        try:
            csv_file = open(filename, "rb")
        except FileNotFoundError:
            raise AbortScript(f"File '{filename}' not found!")
    else:
        csv_file = filename

    circuits_csv = csv.DictReader(codecs.iterdecode(csv_file, "utf-8"))

    csv_data = []
    for row in circuits_csv:
        csv_row = {}
        for old_header, value in row.items():
            if old_header in HEADER_MAPPING:
                csv_row[HEADER_MAPPING[old_header]] = value
                for old_header, new_header in HEADER_MAPPING.items():
                    if not csv_row.get(new_header):
                        csv_row[new_header] = ""
        if csv_row:
            csv_data.append(csv_row)

    return csv_data


def _pp_port_update(logger, port, old, new, revert_if_failed) -> None:
    
    old_name = port.name
    if old not in old_name:
        error = f"{old} was not found in the port name, typo?"
        handle_errors(logger.log_warning, error, revert_if_failed)

    port.name = port.name.replace(old, new)
    if port.name == old_name:
        error = f"Name did not change from {old_name}. New: {new}"
        handle_errors(logger.log_failure, error, not revert_if_failed)
    try:
        port.full_clean()
        port.save()
        logger.log_success(f"Renamed {old_name} to: {port.name}")
    except (AttributeError, TypeError, ValidationError) as e:
        raise AbortScript(e)

def pp_port_update(
    logger: Script,
    pp: Device,
    old_frontport_name: str,
    new_frontport_name: str,
    old_rearport_name: str,
    new_rearport_name: str,
    revert_if_failed: bool = True,
) -> None:
    frontports = pp.frontports.all()
    rearports = pp.rearports.all()

    # Remove the last number after the string
    old = re.sub(r'\d+$', '', old_frontport_name)
    new = re.sub(r'\d+$', '', new_frontport_name)

    #     new_name = re.sub(r'\b' + re.escape(old_word) + r'\b', new_word, name_without_digits)

    for frontport in frontports:
        _pp_port_update(logger, frontport, old, new, revert_if_failed)

    old = re.sub(r'\d+$', '', old_rearport_name)
    new = re.sub(r'\d+$', '', new_rearport_name)
    for rearport in rearports:
        _pp_port_update(logger, rearport, old, new, revert_if_failed)

    return pp


def save_cables(logger: Script, cables: list, allow_skip: bool = False):
    """
    Save cables and handle any errors.
    """
    for cable in cables:
        if cable:
            try:
                cable.full_clean()
                cable.save()
                logger.log_success(f"\tSaved Cable: '{cable}'")
            except ValidationError as e:
                error = ""
                for msg in e.messages:
                    if "Duplicate" in msg:
                        error += f"\tDuplicate Cable found, unable to create Cable: {cable}\n"
                    else:
                        error += f"\tValidation Error saving Cable: {e.messages}\n"
                handle_errors(logger.log_failure, error, allow_skip)
            except AttributeError as e:
                error = f"\tUnknown error saving Cable: {e}"
                handle_errors(logger.log_failure, error, allow_skip)
            except Exception as e:
                error = f"\tUnknown error saving Cable: {e}"
                error += f"\tType: {type(e)}"
                handle_errors(logger.log_failure, error, allow_skip)


def validate_circuit(circuit: Circuit) -> bool:
    """
    Validate a circuit.
    """
    b = MyCircuitValidator()
    failed = b.validate(circuit=circuit, manual=True)
    return failed


def save_circuit(circuit: Circuit, logger: Script, allow_skip: bool = False):
    """
    Save a circuit and handle any errors.
    """
    error = validate_circuit(circuit)
    if error:
        error += f"Failed custom validation: {error}"
        handle_errors(logger.log_failure, error, allow_skip)
    else:
        try:
            circuit.full_clean()
            circuit.save()
            logger.log_success(f"\tSaved Circuit: '{circuit.cid}'")
        except ValidationError as e:
            lmessages = [msg for msg in e.messages]
            messages = "\n".join(lmessages)
            error = f"\tUnable to save circuit: {circuit.cid} - Failed Netbox validation: {messages}"
            handle_errors(logger.log_failure, error, allow_skip)

    return None


def check_circuit_duplicate(cid: str, provider: Provider) -> bool:
    """
    Check for duplicate circuits.
    """
    circ = Circuit.objects.filter(cid=cid, provider=provider)
    if circ.count() == 0:  # Normal creation, no duplicate
        return False
    else:
        return True  # Duplicate found


def save_terminations(logger: Script, termination: list):
    """
    Save terminations.
    """
    if isinstance(termination, CircuitTermination):
        termination.full_clean()
        termination.save()
        name = termination.site if termination.site else termination.provider_network
        logger.log_success(f"\tSaved Termination {termination.term_side}: {name}")
