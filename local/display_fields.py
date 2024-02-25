from circuits.models import CircuitType, Provider, ProviderNetwork
from dcim.models import Device, Interface, RearPort, Site
from extras.scripts import BooleanVar, FileVar,IntegerVar, ObjectVar, StringVar, TextVar

YYYY_MM_DD = r"^\d{4}-([0]\d|1[0-2])-([0-2]\d|3[01])$"

# Standard / All Circuits
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
    required=True,
)
side_a_site = ObjectVar(
    model=Site,
    label="NICE Side A",
    required=True,
)
side_z_site = ObjectVar(
    model=Site,
    label="NICE Side Z",
    required=False,
)
side_z_providernetwork = ObjectVar(
    model=ProviderNetwork,
    label="Carrier Side Z",
    required=True,
)

# Cables Side A
pp = ObjectVar(model=Device, label="Patch Panel", required=False, query_params={"site_id": "$side_a_site"})
pp_port = ObjectVar(model=RearPort, label="Patch Panel Port", required=False, query_params={"device_id": "$pp"})
pp_new_port = IntegerVar(
    label="CREATE Patch Panel Port #:",
    description="Will be 'Front# and Back#, Enable creation via check box below.",
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
create_pp_port = BooleanVar(
    label="Create Patch Panel Interface?",
    description="Enter Patch Panel # in field above",
    default=False,
)

# Other
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
    label="Commit rate (Kbps)",
    min_value=0,
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
comments = TextVar(
    label="Comments",
    required=False,
)

# P2P Circuit / Cables Side Z
z_pp = ObjectVar(model=Device, label="Patch Panel Side Z", required=False, query_params={"site_id": "$side_z_site"})
z_pp_port = ObjectVar(
    model=RearPort, label="Patch Panel Port Side Z", required=False, query_params={"device_id": "$z_pp"}
)
z_pp_new_port = IntegerVar(
    label="CREATE Patch Panel Z Port #:",
    description="Will be 'Front# and Back#, Enable creation via check box below.",
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
z_create_pp_port = BooleanVar(
    label="Create Patch Panel (Z Side) Interface?",
    description="Enter Patch Panel # in field above",
    default=False,
)

# Bulk Circuits
bulk_circuits = FileVar(
    label="Import CSV",
    description="Bulk Import Circuits",
    required=True,
)
circuit_num = IntegerVar(label="Circuit/Line Number", required=False)
overwrite = BooleanVar(
    description="Overwrite existing circuits? (same Ciruit ID & Provider == Same Circuit)", default=False
)


## CSV Headers mapped to display fields (Also used as NiceCircuit attributes)
HEADER_MAPPING = {
    # Circuit
    "Circuit ID": "cid",
    "Description": "description",
    "Provider": "provider",    
    "Circuit Type": "circuit_type",
    "Side A Site": "side_a_site",
    "Side Z Site": "side_z_site",
    "Side Z Provider Network": "side_z_providernetwork",
    # Cables (Side A)
    "Patch Panel": "pp",
    "PP Port": "pp_port",
    "PP New Port": "pp_new_port",
    "PP Port Description": "pp_port_description",
    "PP Info": "pp_info",
    "Cross Connect": "xconnect_id",
    "Device": "device",
    "Interface": "interface",
    "Cable Direct To Device": "direct_to_device",
    "Create PP Port": "create_pp_port",
    # Other
    "Port Speed": "port_speed",
    "Upload Speed": "upstream_speed",
    "Commit Rate (Kbps)": "cir",
    "Install Date": "install_date",
    "Review": "review",
    "Comments": "comments",
    # Cables (Side Z)
    "Patch Panel Z": "z_pp",
    "PP Port Z": "z_pp_port",
    "PP Z New Port": "z_pp_new_port",
    "PP Z Port Description": "z_pp_port_description",
    "PP Z Info": "z_pp_info",
    "Z Cross Connect": "z_xconnect_id",
    "Device Z": "z_device",
    "Interface Z": "z_interface",
    "Cable Z Direct To Device": "z_direct_to_device",
    "Create PP Z Port": "z_create_pp_port",
    # Misc
    "Allow Skip": "allow_skip",
    "Overwrite": "overwrite",
    "NICE Script Type": "nice_script_type",
}
