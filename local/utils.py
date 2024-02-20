import codecs, csv, datetime
import dateutil.parser as date_parser
from dateutil.parser import ParserError

from circuits.choices import CircuitStatusChoices
from circuits.models import Circuit, CircuitType, Provider, ProviderNetwork, CircuitTermination
from dcim.choices import CableTypeChoices
from dcim.models import Cable, Device, Interface, RearPort, Site
from extras.scripts import Script

from django.core.exceptions import ValidationError
from utilities.choices import ColorChoices
from utilities.exceptions import AbortScript

#from local.nice import NiceCircuit
from local.validators import MyCircuitValidator

# Type Hinting
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
    "Termination Date": "termination_date",
    "Commit Rate (Kbps)": "cir",
    "Comments": "comments",
    "Patch Panel Z": "pp_z",
    "PP Port Z": "pp_z_port",
    "Device Z": "device_z",
    "Interface Z": "interface_z",
    "Cable Direct To Device": "cable_direct_to_device",
    "Cross Connect": "xconnect_id",
    "Cable Type": "cable_type",
    "Allow Cable Skip": "allow_cable_skip",
    "Review": "review",
    "Overwrite": "overwrite",
}

# CABLE_COLORS = {
#     CableTypeChoices.TYPE_SMF: ColorChoices.COLOR_YELLOW,
#     CableTypeChoices.TYPE_SMF_OS1: ColorChoices.COLOR_YELLOW,
#     CableTypeChoices.TYPE_SMF_OS2: ColorChoices.COLOR_YELLOW,
#     CableTypeChoices.TYPE_MMF: ColorChoices.COLOR_AQUA,
#     CableTypeChoices.TYPE_MMF_OM1: ColorChoices.COLOR_AQUA,
#     CableTypeChoices.TYPE_MMF_OM2: ColorChoices.COLOR_AQUA,
#     CableTypeChoices.TYPE_MMF_OM3: ColorChoices.COLOR_AQUA,
#     CableTypeChoices.TYPE_MMF_OM4: ColorChoices.COLOR_AQUA,
#     CableTypeChoices.TYPE_MMF_OM5: ColorChoices.COLOR_AQUA,
#     CableTypeChoices.TYPE_CAT5: ColorChoices.COLOR_WHITE,
#     CableTypeChoices.TYPE_CAT5E: ColorChoices.COLOR_WHITE,
#     CableTypeChoices.TYPE_CAT6: ColorChoices.COLOR_WHITE,
#     CableTypeChoices.TYPE_CAT6A: ColorChoices.COLOR_WHITE,
# }

def handle_errors(logger: Script, error: str, skip: bool = False):   
    if skip:
        logger(error)
    else:
        raise AbortScript(error)

def validate_date(date_str: str) -> None:
    error = f"Invalid date ({date_str}), should be YYYY-MM-DD"
    try:
        date = date_parser.parse(date_str)
        if date.year >= 2026 or date.year <= 1980:
            raise AbortScript(f"Date: {date_str} is outside constraints: Minimum year: 1980, Maximum year: 2026")
    except ParserError:
        raise AbortScript(error)
    except ValueError:
        raise AbortScript(error)
    except TypeError:
        raise AbortScript(error)
    return date.date().isoformat()
    
def validate_user(user):
    if user.username not in BULK_SCRIPT_ALLOWED_USERS:
        return False
    else:
        return True

def get_provider_by_name(name: str):
    try:
        provider = Provider.objects.get(name=name)
    except Provider.DoesNotExist:
        return None

    return provider

def get_provider_network_by_name(name: str):
    try:
        provider_network = ProviderNetwork.objects.get(name=name)
    except ProviderNetwork.DoesNotExist:
        return None

    return provider_network

def get_circuit_type_by_name(name: str):
    try:
        _type = CircuitType.objects.get(name=name)
    except CircuitType.DoesNotExist:
        return None
    
    return _type

def get_site_by_name(name: str):
    try:
        site = Site.objects.get(name=name)
    except Site.DoesNotExist:
        return None
    
    return site

def get_device_by_name(name: str, site: Site = None):
    try:
        if not site:
            device = Device.objects.get(name=name)
        else:
            device = Device.objects.get(name=name, site=site)
    except Device.DoesNotExist:
        return None
    
    return device

def get_interface_by_name(name: str, device: Device = None):
    try:
        if device:
            interface = Interface.objects.get(name=name, device=device)
        else:
            interface = Interface.objects.get(name=name)
    except Interface.DoesNotExist:
        return None
    except Interface.MultipleObjectsReturned:
        return None
    
    return interface

def get_rearport_by_name(name: str, device: Device = None):
    try:
        if device:
            rearport = RearPort.objects.get(name=name, device=device)
        else:
            rearport = RearPort.objects.get(name=name)
    except RearPort.DoesNotExist:
        return None
    except RearPort.MultipleObjectsReturned:
        return None
    
    return rearport

def get_side_by_name(side_site, side_providernetwork) -> Site | ProviderNetwork:
    side = get_site_by_name(side_site)
    if not side:
        side = get_provider_network_by_name(side_providernetwork)
    return side

def load_data_from_csv(filename) -> list[dict]:
    # Check if from Netbox or via Tests
    if not isinstance(filename, InMemoryUploadedFile):
        try:
            csv_file = open(filename, "rb")
        except FileNotFoundError:
            raise AbortScript(f"File '{filename}' not found!")
    else:
        csv_file = filename

    circuits_csv = csv.DictReader(codecs.iterdecode(csv_file, "utf-8"))

    csv_data = []
    # Update Dictionary Keys / Headers
    for row in circuits_csv:
        csv_row = {}
        for old_header, value in row.items():
            if old_header in HEADER_MAPPING:
                csv_row[HEADER_MAPPING[old_header]] = value

                # Add any missing fields we may check later
                for old_header, new_header in HEADER_MAPPING.items():
                    if not csv_row.get(new_header):
                        csv_row[new_header] = ""
        if csv_row:
            csv_data.append(csv_row)

    return csv_data

def save_cables(logger: Script, cables: list, allow_cable_skip: bool = False):
    error = False
    for cable in cables:
        if cable:
            try:
                cable.full_clean()
                cable.save()
                logger.log_success(f"Saved Cable: '{cable}'")
            except ValidationError as e:
                error = ""
                for msg in e.messages:
                    if "Duplicate" in msg:
                        error += f"\tDuplicate Cable found, unable to create Cable: {cable}\n"
                    else:
                        error += f"\tValidation Error saving Cable: {e.messages}\n"
                
                if not allow_cable_skip:
                    raise AbortScript(error)
                else:
                    logger.log_failure(error)
            except AttributeError as e:
                error = f"\tUnknown error saving Cable: {e}"
                logger.log_failure(f"{type(logger)}")
                logger.log_failure(f"{logger.full_name}")
                logger.log_failure(f"{dir(logger)}")
                logger.log_info(f"WHAT IS THIS: {e}")
                return error
            except Exception as e:
                logger.log_failure(f"\tUnknown errore saving Cable: {e}")
                logger.log_failure(f"\tType: {type(e)}")
                return e
        if error:
            return error
            #handle_errors(logger.log_failure, error, allow_cable_skip)
    

def validate_circuit(circuit: Circuit) -> bool:
    b = MyCircuitValidator()
    failed = b.validate(circuit=circuit, manual=True)
    return failed

def save_circuit(circuit: Circuit, logger: Script, allow_cable_skip: bool = False):
    error = validate_circuit(circuit)
    if error:
        logger.log_failure(f"Failed custom validation: {error}")
    else:
        try:
            circuit.full_clean()
            circuit.save()
            logger.log_success(f"\tSaved Circuit: '{circuit.cid}'")
        except ValidationError as e:
            lmessages = [msg for msg in e.messages]
            messages = "\n".join(lmessages)
            error = f"\tUnable to save circuit: {circuit.cid} - Failed Netbox validation: {messages}"
            raise AbortScript(error)

    return None

def check_circuit_duplicate(cid: str, provider: Provider) -> bool:
    # Check for duplicate
    circ = Circuit.objects.filter(
        cid=cid, provider=provider
    )
    if circ.count() == 0:  # Normal creation, no duplicate
        return False
    elif circ.count() > 1:
        raise AbortScript(
            f"Error, multiple duplicates for Circuit ID: {cid}, please resolve manually."
        )
    else:
        return True # Duplicate found

def save_terminations(logger: Script, termination: list):
    if isinstance(termination, CircuitTermination):
        termination.full_clean()
        termination.save()
        logger.log_success(f"\tSaved Termination: {termination}")
