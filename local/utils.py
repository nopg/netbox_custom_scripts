import codecs
import csv
import re

import dateutil.parser as date_parser
from circuits.choices import CircuitStatusChoices
from circuits.models import (
    Circuit,
    CircuitTermination,
    CircuitType,
    Provider,
    ProviderNetwork,
)
from dateutil.parser import ParserError
from dcim.choices import CableTypeChoices, PortTypeChoices
from dcim.models import Cable, Device, FrontPort, Interface, RearPort, Site
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from extras.scripts import Script
from local.display_fields import HEADER_MAPPING
from local.validators import MyCircuitValidator
from utilities.choices import ColorChoices
from utilities.exceptions import AbortScript

BULK_SCRIPT_ALLOWED_USERS = ["netbox", "danny.berman", "joe.deweese", "loran.fuchs", "taylor", "gustavo"]


def generate_range(input_string):
    # Convert the input string to an integer
    num = int(input_string)

    # Calculate the start and end values for the range
    start = num - (num % 50) + 1
    end = start + 49

    # Ensure that the start and end values are within the valid range of 4-digit numbers
    start = max(start, 1)
    end = min(end, 9999)

    # Pad the start and end strings with zeros to ensure they have the same length
    start_str = str(start).zfill(4)
    end_str = str(end).zfill(4)

    return start_str, end_str


def is_four_digit_numeric(string):
    # Define a regular expression pattern to match exactly 4 digits
    pattern = r'^\d{4}$'
    # Use the match function to check if the string matches the pattern
    return bool(re.match(pattern, string))


def get_bun_link(bun: str) -> str:
    # Convert the input string to an integer
    num = int(bun)

    # Calculate the start and end values for the range
    start = num - (num % 50) + 1
    end = start + 49

    # Ensure that the start and end values are within the valid range of 4-digit numbers
    start = max(start, 1)
    end = min(end, 9999)

    # Pad the start and end strings with zeros to ensure they have the same length
    start_str = str(start).zfill(4)
    end_str = str(end).zfill(4)

    from local.display_fields import customs

    bun_link = f"{customs['bun_root_path']}\\{start_str} - {end_str}\\"
    return bun_link


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
            raise AbortScript(f"Date: {date_str} is outside constraints: Minimum year: 1980, Maximum year: 2036")
    except (ParserError, ValueError, TypeError):
        raise AbortScript(error)
    return date.date().isoformat()


def validate_user(user) -> bool:
    """
    Validate if the user is allowed to perform bulk operations.
    """
    return user.username in BULK_SCRIPT_ALLOWED_USERS


def validate_pp_new_port(port_num: str, logger, skip):
    if not port_num:
        return ""

    if not port_num.isnumeric():
        handle_errors(logger.log_failure, error=f"Invalid value for new Patch Panel Port: {port_num}", skip=skip)

    if int(port_num) > 48:
        handle_errors(logger.log_failure, error=f"New Patch Panel Port must be below 48: {port_num}", skip=skip)

    return int(port_num)


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

    circuits_csv = csv.DictReader(codecs.iterdecode(csv_file, "utf-8-sig"))

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


def create_rearport(name: str, type: PortTypeChoices, pp: Device, description: str = "") -> RearPort:
    # if not pp:
    #     handle_errors(logger, )
    return RearPort(
        name=name,
        type=type,
        device=pp,
        description=description,
    )


def create_frontport(
    name: str, type: PortTypeChoices, pp: Device, rear_port: RearPort, description: str = ""
) -> FrontPort:
    return FrontPort(
        name=name,
        type=type,
        device=pp,
        rear_port=rear_port,
        description=description,
    )


def create_extra_pp_ports(
    port_num: int, type: PortTypeChoices, pp: Device, logger: Script, allow_skip: bool = False
) -> None:
    rps = pp.rearports.all()

    for i in range(1, port_num):
        rear_port_name = f"Rear{i}"
        front_port_name = f"Front{i}"
        if not any(rp.name == rear_port_name for rp in rps):
            try:
                new_rp = create_rearport(name=rear_port_name, type=type, pp=pp)
                new_rp.full_clean()
                new_rp.save()
                logger.log_success(f"Saved: {new_rp}")

                new_fp = create_frontport(name=front_port_name, type=type, pp=pp, rear_port=new_rp)
                new_fp.full_clean()
                new_fp.save()
                logger.log_success(f"Saved: {new_fp}")
            except ValidationError as e:
                error = f"Error creating Patch Panel Port, please standardize port names before continuing.\n{e}"
                handle_errors(logger=logger.log_failure, error=error, skip=allow_skip)


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
                error = f"\tUnknown error saving Cable {cable}: {e}"
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


def save_rearport(logger: Script, rear_port: RearPort):
    """
    Save RearPort
    """
    if isinstance(rear_port, RearPort):
        rear_port.full_clean()
        rear_port.save()
        logger.log_success(f"\tCreated RearPort {rear_port.name}")


def save_frontport(logger: Script, front_port: RearPort):
    """
    Save FrontPort
    """
    if isinstance(front_port, FrontPort):
        front_port.full_clean()
        front_port.save()
        logger.log_success(f"\tCreated FrontPort {front_port.name}")
