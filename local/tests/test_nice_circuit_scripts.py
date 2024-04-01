#
# export NETBOX_CONFIGURATION=netbox.configuration_testing
# python manage.py test scripts.testing_circuits -v 3 --keepdb

from django.contrib.contenttypes.models import ContentType

from dcim.choices import InterfaceTypeChoices, PortTypeChoices
from dcim.models import (
    Device,
    DeviceType,
    DeviceRole,
    FrontPortTemplate,
    Interface,
    Manufacturer,
    RearPortTemplate,
    Site,
)
from extras.choices import CustomFieldTypeChoices
from extras.models import CustomField
from circuits.models import Circuit, CircuitType, CircuitTermination, Provider, ProviderNetwork
from utilities.testing.base import TestCase

# from extras.choices import LogLevelChoices
from extras.scripts import Script
from scripts.nice_circuit_scripts import BulkCircuits, StandardCircuit
import os
from local.utils import *
from local.nice_circuits import NiceBulkCircuits, NiceCircuit, NiceStandardCircuit


class CircuitAdderTestCase(TestCase):
    """
    check dupe

    :form_data: Data to be used when creating a new object.
    """

    form_data = {}

    # Set up Test Database
    @classmethod
    def setUpTestData(cls):
        # script_dir = os.path.dirname(__file__)
        # csv_test_filename = "csv_bulk_circuits_test.csv"
        # filename = os.path.join(script_dir, csv_test_filename)
        # iofile = open(filename, mode="rb")
        # cls.csv_data = load_data_from_csv(iofile)
        # iofile.close()
        ...

    def setUp(self):
        super().setUp()

        providers = (
            Provider(name="Provider 1", slug="provider-1"),
            Provider(name="Provider 2", slug="provider-2"),
            Provider(name="Provider 3", slug="provider-3"),
        )
        Provider.objects.bulk_create(providers)

        provider_networks = (
            ProviderNetwork(name="Provider-Network 1", provider=providers[0]),  # , slug="provider-1"),
            ProviderNetwork(name="Provider-Network 2", provider=providers[1]),  # , slug="provider-2"),
            ProviderNetwork(name="Provider-Network 2", provider=providers[2]),  # , slug="provider-2"),
        )
        ProviderNetwork.objects.bulk_create(provider_networks)

        circuittypes = (
            CircuitType(name="Circuit-Type 1", slug="circuit-type-1"),
            CircuitType(name="Circuit-Type 2", slug="circuit-type-2"),
            CircuitType(name="Circuit-Type 3", slug="circuit-type-3"),
        )
        CircuitType.objects.bulk_create(circuittypes)

        circuits = (
            Circuit(cid="Circuit 1", provider=providers[0], type=circuittypes[0]),
            Circuit(cid="Circuit 2", provider=providers[1], type=circuittypes[1]),
            Circuit(cid="Circuit 3", provider=providers[2], type=circuittypes[2]),
        )
        Circuit.objects.bulk_create(circuits)

        sites = (
            Site(name="Site 1", slug="site-1"),
            Site(name="Site 2", slug="site-2"),
            Site(name="Site 3", slug="site-3"),
        )
        Site.objects.bulk_create(sites)

        manufacturer = Manufacturer.objects.create(name='Manufacturer 1', slug='manufacturer-1')
        device_types = (
            DeviceType(manufacturer=manufacturer, model='Device-Type 1', slug='device-type-1'),
            DeviceType(manufacturer=manufacturer, model='Device-Type 2', slug='device-type-2'),
            DeviceType(manufacturer=manufacturer, model='Device-Type 3', slug='device-type-3'),
            DeviceType(manufacturer=manufacturer, model='Patch-Panel-Type 1', slug='patch-panel-1'),
        )
        DeviceType.objects.bulk_create(device_types)
        DeviceRole.objects.create(name='Device-Role 1', slug='device-role-1')

        rearport_templates = (
            RearPortTemplate(device_type=device_types[3], name="Rear 1", type=PortTypeChoices.TYPE_LC, positions=1),
            RearPortTemplate(device_type=device_types[3], name="Rear 2", type=PortTypeChoices.TYPE_LC, positions=1),
            RearPortTemplate(device_type=device_types[3], name="Rear 3", type=PortTypeChoices.TYPE_LC, positions=1),
            RearPortTemplate(device_type=device_types[3], name="Rear 4", type=PortTypeChoices.TYPE_LC, positions=1),
        )
        RearPortTemplate.objects.bulk_create(rearport_templates)

        frontport_templates = (
            FrontPortTemplate(
                device_type=device_types[3],
                name="Front 1",
                type=PortTypeChoices.TYPE_LC,
                rear_port=rearport_templates[0],
            ),
            FrontPortTemplate(
                device_type=device_types[3],
                name="Front 2",
                type=PortTypeChoices.TYPE_LC,
                rear_port=rearport_templates[1],
            ),
            FrontPortTemplate(
                device_type=device_types[3],
                name="Front 3",
                type=PortTypeChoices.TYPE_LC,
                rear_port=rearport_templates[2],
            ),
            FrontPortTemplate(
                device_type=device_types[3],
                name="Front 4",
                type=PortTypeChoices.TYPE_LC,
                rear_port=rearport_templates[3],
            ),
        )
        FrontPortTemplate.objects.bulk_create(frontport_templates)

        devices = (
            Device(
                name="Device 1",
                site=sites[0],
                device_type=device_types[0],
                role=DeviceRole.objects.first(),
            ),
            Device(
                name="Device 2",
                site=sites[1],
                device_type=device_types[1],
                role=DeviceRole.objects.first(),
            ),
            Device(
                name="Device 3",
                site=sites[2],
                device_type=device_types[2],
                role=DeviceRole.objects.first(),
            ),
            Device(
                name="Patch Panel 11",
                site=sites[0],
                device_type=DeviceType.objects.get(model="Patch-Panel-Type 1"),
                role=DeviceRole.objects.first(),
            ),
            Device(
                name="Patch Panel 12",
                site=sites[1],
                device_type=DeviceType.objects.get(model="Patch-Panel-Type 1"),
                role=DeviceRole.objects.first(),
            ),
            Device(
                name="Patch Panel 13",
                site=sites[2],
                device_type=DeviceType.objects.get(model="Patch-Panel-Type 1"),
                role=DeviceRole.objects.first(),
            ),
        )
        Device.objects.bulk_create(devices)

        interfaces = (
            Interface(name="Interface 1", device=devices[0], type=InterfaceTypeChoices.TYPE_1GE_FIXED),
            Interface(name="Interface 1", device=devices[1], type=InterfaceTypeChoices.TYPE_1GE_FIXED),
            Interface(name="Interface 1", device=devices[2], type=InterfaceTypeChoices.TYPE_1GE_FIXED),
            Interface(name="Interface 2", device=devices[0], type=InterfaceTypeChoices.TYPE_1GE_FIXED),
            Interface(name="Interface 2", device=devices[1], type=InterfaceTypeChoices.TYPE_1GE_FIXED),
            Interface(name="Interface 2", device=devices[2], type=InterfaceTypeChoices.TYPE_1GE_FIXED),
            Interface(name="Interface 3", device=devices[0], type=InterfaceTypeChoices.TYPE_1GE_FIXED),
            Interface(name="Interface 3", device=devices[1], type=InterfaceTypeChoices.TYPE_1GE_FIXED),
            Interface(name="Interface 3", device=devices[2], type=InterfaceTypeChoices.TYPE_1GE_FIXED),
        )
        Interface.objects.bulk_create(interfaces)

        # Custom Fields
        cf_review = CustomField(name="review", type=CustomFieldTypeChoices.TYPE_BOOLEAN)
        cf_review.full_clean()
        cf_review.save()
        cf_review.content_types.set([ContentType.objects.get_for_model(Circuit)])

        cf_bun = CustomField(name="bun", type=CustomFieldTypeChoices.TYPE_TEXT)
        cf_bun.full_clean()
        cf_bun.save()
        cf_bun.content_types.set([ContentType.objects.get_for_model(Circuit)])

        cf_bun_link = CustomField(name="bun_link", type=CustomFieldTypeChoices.TYPE_TEXT)
        cf_bun_link.full_clean()
        cf_bun_link.save()
        cf_bun_link.content_types.set([ContentType.objects.get_for_model(Circuit)])

    # Tests
    def test_get_provider_by_name(self):
        provider = get_provider_by_name("Provider 1")
        self.assertIsInstance(provider, Provider)

    def test_get_provider_by_name_missing(self):
        provider = get_provider_by_name("Provider Missing")
        self.assertIsNone(provider)

    def test_get_provider_network_by_name(self):
        provider_network = get_provider_network_by_name("Provider-Network 1")
        self.assertIsInstance(provider_network, ProviderNetwork)

    def test_get_provider_network_by_name_missing(self):
        provider_network = get_provider_network_by_name("Provider Network Missing")
        self.assertIsNone(provider_network)

    def test_get_circuit_type_by_name(self):
        circuit_type = get_circuit_type_by_name("Circuit-Type 1")
        self.assertIsInstance(circuit_type, CircuitType)

    def test_get_circuit_type_by_name_missing(self):
        circuit_type = get_circuit_type_by_name("Circuit-Type Missing")
        self.assertIsNone(circuit_type)

    def test_get_site_by_name(self):
        site = get_site_by_name("Site 1")
        self.assertIsInstance(site, Site)

    def test_get_site_by_name_missing(self):
        site = get_site_by_name("Site Missing")
        self.assertIsNone(site)

    def test_get_device_by_name(self):
        device = get_device_by_name(name="Device 1", site=Site.objects.first())
        self.assertIsInstance(device, Device)

    def test_get_device_by_name_missing(self):
        device = get_device_by_name(name="Device Missing", site=Site.objects.first())
        self.assertIsNone(device)

    def test_get_interface_by_name(self):
        interface = get_interface_by_name(name="Interface 1", device=Device.objects.first())
        self.assertIsInstance(interface, Interface)

    def test_get_interface_by_name_missing(self):
        interface = get_interface_by_name(name="Interface Missing", device=Device.objects.first())
        self.assertIsNone(interface)

    def test_load_data_from_csv(self):
        csv_test_filename = "local/tests/test_bulk_circuits.csv"
        circuits = NiceBulkCircuits.from_csv(
            logger=StandardCircuit(), overwrite=False, filename=csv_test_filename, circuit_num=1
        )
        self.assertIsInstance(circuits[0], NiceStandardCircuit)

    ## FAILURES
    def test_load_data_from_csv_fail_notfound(self):
        csv_test_filename_notfound = "local/tests/test_bulk_circuits_notfound.csv"
        with self.assertRaisesMessage(AbortScript, "not found!"):
            circuits = NiceBulkCircuits.from_csv(
                logger=StandardCircuit(), overwrite=False, filename=csv_test_filename_notfound
            )

    def test_load_data_from_csv_fail_missing_circuittype(self):
        csv_test_filename_fail = "local/tests/test_bulk_circuits_fail.csv"
        with self.assertRaisesMessage(AbortScript, "Missing/Not Found Mandatory Value"):
            circuits = NiceBulkCircuits.from_csv(
                logger=StandardCircuit(), filename=csv_test_filename_fail, circuit_num=1
            )

    def test_load_data_from_csv_fail_missing_provider(self):
        csv_test_filename_fail = "local/tests/test_bulk_circuits_fail.csv"
        with self.assertRaisesMessage(AbortScript, "Missing/Not Found Mandatory Value"):
            circuits = NiceBulkCircuits.from_csv(
                logger=StandardCircuit(), filename=csv_test_filename_fail, circuit_num=2
            )

    def test_load_data_from_csv_fail_missing_cid(self):
        csv_test_filename_fail = "local/tests/test_bulk_circuits_fail.csv"
        with self.assertRaisesMessage(AbortScript, "Missing/Not Found Mandatory Value"):
            circuits = NiceBulkCircuits.from_csv(
                logger=StandardCircuit(), filename=csv_test_filename_fail, circuit_num=3
            )

    def test_bulk_circuit_2_overwrite_fail(self):
        csv_test_filename_fail = "local/tests/test_bulk_circuits_fail.csv"
        with self.assertLogs("netbox.scripts.scripts.nice_circuit_scripts.StandardCircuit", level="ERROR") as logs:
            circuits = NiceBulkCircuits.from_csv(
                logger=StandardCircuit(), filename=csv_test_filename_fail, circuit_num=4
            )
            _ = circuits[0].create()

        self.assertIn("existing Circuit found!", logs.output[0])

    def test_bulk_circuit_3_missing_device(self):
        csv_test_filename_fail = "local/tests/test_bulk_circuits_fail.csv"
        with self.assertRaisesMessage(AbortScript, "Missing Device"):
            circuits = NiceBulkCircuits.from_csv(
                logger=StandardCircuit(), filename=csv_test_filename_fail, circuit_num=5
            )
            circuits[0].create()

    def test_bulk_circuit_4_missing_pp(self):
        csv_test_filename_fail = "local/tests/test_bulk_circuits_fail.csv"

        with self.assertLogs("netbox.scripts.scripts.nice_circuit_scripts.StandardCircuit", level="ERROR") as logs:
            circuits = NiceBulkCircuits.from_csv(
                logger=StandardCircuit(), filename=csv_test_filename_fail, circuit_num=6
            )
            _ = circuits[0].create()

        self.assertIn("Patch Panel or port", logs.output[0])
        self.assertIn("missing", logs.output[0])

    def test_p2p_missing_z_site(self):
        csv_test_filename_fail = "local/tests/test_bulk_circuits_fail.csv"
        with self.assertLogs("netbox.scripts.scripts.nice_circuit_scripts.StandardCircuit", level="WARNING") as logs:
            circuits = NiceBulkCircuits.from_csv(
                logger=StandardCircuit(), filename=csv_test_filename_fail, circuit_num=7
            )
            _ = circuits[0].create()

        self.assertIn("Missing Site for Termination Z", logs.output[0])

    def test_bulk_circuit_5_extra_pp(self):
        device = Device(
            site=Site.objects.first(),
            device_type=DeviceType.objects.get(model="Patch-Panel-Type 1"),
            role=DeviceRole.objects.first(),
            name="Patch Panel 1",
        )
        device.save()

        csv_test_filename_fail = "local/tests/test_bulk_circuits_fail.csv"
        with self.assertLogs("netbox.scripts.scripts.nice_circuit_scripts.StandardCircuit", level="ERROR") as logs:
            circuits = NiceBulkCircuits.from_csv(
                logger=StandardCircuit(), filename=csv_test_filename_fail, circuit_num=8
            )
            _ = circuits[0].create()

        self.assertIn("Cable Direct to Device chosen, but Patch Panel", logs.output[0])

    def test_new_pp_port_fail_1(self):
        device = Device(
            site=Site.objects.first(),
            device_type=DeviceType.objects.get(model="Patch-Panel-Type 1"),
            role=DeviceRole.objects.first(),
            name="Patch Panel 1",
        )
        device.save()

        csv_test_filename_fail = "local/tests/test_bulk_circuits_fail.csv"
        with self.assertLogs("netbox.scripts.scripts.nice_circuit_scripts.StandardCircuit", level="ERROR") as logs:
            circuits = NiceBulkCircuits.from_csv(
                logger=StandardCircuit(), filename=csv_test_filename_fail, circuit_num=9
            )
            _ = circuits[0].create()

        self.assertIn("unless \"Create Patch Panel Interface\" is selected", logs.output[0])

    def test_new_pp_port_fail_2(self):
        device = Device(
            site=Site.objects.first(),
            device_type=DeviceType.objects.get(model="Patch-Panel-Type 1"),
            role=DeviceRole.objects.first(),
            name="Patch Panel 1",
        )
        device.save()

        csv_test_filename_fail = "local/tests/test_bulk_circuits_fail.csv"
        with self.assertLogs("netbox.scripts.scripts.nice_circuit_scripts.StandardCircuit", level="ERROR") as logs:
            circuits = NiceBulkCircuits.from_csv(
                logger=StandardCircuit(), filename=csv_test_filename_fail, circuit_num=10
            )
            _ = circuits[0].create()

        self.assertIn("Cannot choose an existing Patch Panel Port", logs.output[0])
        self.assertIn("AND enable 'Create Patch Panel Port' simultaneously", logs.output[0])

    def test_new_pp_port_fail_3(self):
        device = Device(
            site=Site.objects.first(),
            device_type=DeviceType.objects.get(model="Patch-Panel-Type 1"),
            role=DeviceRole.objects.first(),
            name="Patch Panel 1",
        )
        device.save()

        csv_test_filename_fail = "local/tests/test_bulk_circuits_fail.csv"
        with self.assertLogs("netbox.scripts.scripts.nice_circuit_scripts.StandardCircuit", level="ERROR") as logs:
            circuits = NiceBulkCircuits.from_csv(
                logger=StandardCircuit(), filename=csv_test_filename_fail, circuit_num=11
            )
            _ = circuits[0].create()

        self.assertIn("New Patch Panel Port must be below 48", logs.output[0])

    ## SUCCESSES
    def test_bulk_circuit_1_direct_to_device(self):
        csv_test_filename = "local/tests/test_bulk_circuits.csv"
        circuits = NiceBulkCircuits.from_csv(
            logger=StandardCircuit(), overwrite=False, filename=csv_test_filename, circuit_num=1
        )
        with self.assertLogs("netbox.scripts.scripts.nice_circuit_scripts.StandardCircuit", level="INFO") as logs:
            _ = circuits[0].create()

        # Correct Logs
        self.assertTrue(any("Saved Circuit:" in log for log in logs.output))
        term_count = sum(log.count("Saved Termination") for log in logs.output)
        cable_count = sum(log.count("Saved Cable:") for log in logs.output)
        self.assertEqual(term_count, 2)
        self.assertEqual(cable_count, 1)
        # No warnings
        self.assertFalse(any("WARNING" in log for log in logs.output))

    def test_bulk_circuit_1_the_standard(self):
        # Build PP / Etc
        device = Device(
            site=Site.objects.first(),
            device_type=DeviceType.objects.get(model="Patch-Panel-Type 1"),
            role=DeviceRole.objects.first(),
            name="Patch Panel 1",
        )
        device.save()

        csv_test_filename = "local/tests/test_bulk_circuits.csv"
        circuits = NiceBulkCircuits.from_csv(
            logger=StandardCircuit(), overwrite=False, filename=csv_test_filename, circuit_num=3
        )

        with self.assertLogs(
            "netbox.scripts.scripts.nice_circuit_scripts.StandardCircuit", level="INFO"
        ) as logs:  # LogLevelChoices.LOG_SUCCESS
            _ = circuits[0].create()

        # Correct Logs
        self.assertTrue(any("Saved Circuit:" in log for log in logs.output))
        term_count = sum(log.count("Saved Termination") for log in logs.output)
        cable_count = sum(log.count("Saved Cable:") for log in logs.output)
        self.assertEqual(term_count, 2)
        self.assertEqual(cable_count, 2)
        # No warnings
        self.assertFalse(any("WARNING" in log for log in logs.output))
        # No errors
        self.assertFalse(any("ERROR" in log for log in logs.output))

    def test_p2p_direct_to_device(self):
        csv_test_filename = "local/tests/test_bulk_circuits.csv"
        circuits = NiceBulkCircuits.from_csv(
            logger=StandardCircuit(), overwrite=False, filename=csv_test_filename, circuit_num=5
        )
        with self.assertLogs(
            "netbox.scripts.scripts.nice_circuit_scripts.StandardCircuit", level="INFO"
        ) as logs:  # LogLevelChoices.LOG_SUCCESS
            _ = circuits[0].create()

        # Correct Logs
        self.assertTrue(any("Saved Circuit:" in log for log in logs.output))
        term_count = sum(log.count("Saved Termination") for log in logs.output)
        term_a_count = sum(log.count("Termination Z") for log in logs.output)
        term_z_count = sum(log.count("Termination Z") for log in logs.output)
        cable_count = sum(log.count("Saved Cable:") for log in logs.output)
        self.assertEqual(term_count, 2)
        self.assertEqual(term_a_count, 2)
        self.assertEqual(term_z_count, 2)
        self.assertEqual(cable_count, 2)
        # No warnings
        self.assertFalse(any("WARNING" in log for log in logs.output))

    def test_p2p_the_standard(self):
        # Build PP / Etc
        device1 = Device(
            site=Site.objects.first(),
            device_type=DeviceType.objects.get(model="Patch-Panel-Type 1"),
            role=DeviceRole.objects.first(),
            name="Patch Panel 1",
        )
        device1.save()

        device2 = Device(
            site=Site.objects.get(name="Site 2"),
            device_type=DeviceType.objects.get(model="Patch-Panel-Type 1"),
            role=DeviceRole.objects.first(),
            name="Patch Panel 2",
        )
        device2.save()

        csv_test_filename = "local/tests/test_bulk_circuits.csv"
        circuits = NiceBulkCircuits.from_csv(
            logger=StandardCircuit(), overwrite=False, filename=csv_test_filename, circuit_num=6
        )

        with self.assertLogs(
            "netbox.scripts.scripts.nice_circuit_scripts.StandardCircuit", level="INFO"
        ) as logs:  # LogLevelChoices.LOG_SUCCESS
            _ = circuits[0].create()

        # Correct Logs
        self.assertTrue(any("Saved Circuit:" in log for log in logs.output))
        term_count = sum(log.count("Saved Termination") for log in logs.output)
        term_a_count = sum(log.count("Termination A") for log in logs.output)
        term_z_count = sum(log.count("Termination Z") for log in logs.output)
        cable_count = sum(log.count("Saved Cable:") for log in logs.output)
        self.assertEqual(term_count, 2)
        self.assertEqual(term_a_count, 2)
        self.assertEqual(term_z_count, 2)
        self.assertEqual(cable_count, 4)
        # No warnings
        self.assertFalse(any("WARNING" in log for log in logs.output))
        # No errors
        self.assertFalse(any("ERROR" in log for log in logs.output))

    def test_the_standard_new_pp_port(self):
        # Build PP / Etc
        device = Device(
            site=Site.objects.first(),
            device_type=DeviceType.objects.get(model="Patch-Panel-Type 1"),
            role=DeviceRole.objects.first(),
            name="Patch Panel 1",
        )
        device.save()

        csv_test_filename = "local/tests/test_bulk_circuits.csv"
        circuits = NiceBulkCircuits.from_csv(
            logger=StandardCircuit(), overwrite=False, filename=csv_test_filename, circuit_num=7
        )

        with self.assertLogs(
            "netbox.scripts.scripts.nice_circuit_scripts.StandardCircuit", level="INFO"
        ) as logs:  # LogLevelChoices.LOG_SUCCESS
            _ = circuits[0].create()

        # Correct Logs
        self.assertTrue(any("Saved Circuit:" in log for log in logs.output))
        term_count = sum(log.count("Saved Termination") for log in logs.output)
        self.assertEqual(sum(log.count("Created RearPort Rear7") for log in logs.output), 1)
        self.assertEqual(sum(log.count("Created FrontPort Front7") for log in logs.output), 1)
        extra_rp_count = sum(log.count("Saved: Rear") for log in logs.output)
        extra_fp_count = sum(log.count("Saved: Front") for log in logs.output)
        cable_count = sum(log.count("Saved Cable:") for log in logs.output)
        self.assertEqual(term_count, 2)
        self.assertEqual(cable_count, 2)
        self.assertEqual(extra_rp_count, 6)
        self.assertEqual(extra_fp_count, 6)
        # No warnings
        self.assertFalse(any("WARNING" in log for log in logs.output))
        # No errors
        self.assertFalse(any("ERROR" in log for log in logs.output))

    ## WARNINGS
    def test_bulk_circuit_2_overwrite_circuit(self):
        csv_test_filename = "local/tests/test_bulk_circuits.csv"
        circuits = NiceBulkCircuits.from_csv(
            logger=StandardCircuit(), overwrite=True, filename=csv_test_filename, circuit_num=2
        )
        with self.assertLogs(
            "netbox.scripts.scripts.nice_circuit_scripts.StandardCircuit", level="INFO"
        ) as logs:  # LogLevelChoices.LOG_SUCCESS
            _ = circuits[0].create()

        # Correct Logs
        self.assertTrue(any("updating existing circuit!" in log for log in logs.output))
        self.assertTrue(any("Saved Circuit:" in log for log in logs.output))
        term_count = sum(log.count("Saved Termination") for log in logs.output)
        cable_count = sum(log.count("Saved Cable:") for log in logs.output)
        self.assertEqual(term_count, 2)
        self.assertEqual(cable_count, 1)
        # No warnings
        self.assertFalse(any("ERROR" in log for log in logs.output))
        # New Date (actually overwritten)
        c = Circuit.objects.get(cid="Circuit 1")
        import dateutil.parser as dp

        date = dp.parse("1999-09-09").date()
        self.assertEqual(c.install_date, date)
