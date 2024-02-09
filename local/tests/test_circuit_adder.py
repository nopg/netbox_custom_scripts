#
# export NETBOX_CONFIGURATION=netbox.configuration_testing
# python manage.py test scripts.testing_circuits -v 3 --keepdb

from dcim.choices import InterfaceTypeChoices
from dcim.models import Device, DeviceType, DeviceRole, Interface, Manufacturer, Site
from circuits.models import Circuit, CircuitType, CircuitTermination, Provider, ProviderNetwork
from utilities.testing.base import TestCase

# from extras.choices import LogLevelChoices
from extras.scripts import Script
from scripts.circuit_adder import BulkCircuits, SingleCircuit
import os
from local.utils import *


class CircuitAdderTestCase(TestCase):
    """
    check dupe

    :form_data: Data to be used when creating a new object.
    """
    form_data = {}
    
    # Set up Test Database
    @classmethod
    def setUpTestData(cls):
        script_dir = os.path.dirname(__file__)
        csv_test_filename = "csv_bulk_circuits_test.csv"
        filename = os.path.join(script_dir, csv_test_filename)
        iofile = open(filename, mode="rb")
        cls.csv_data = load_data_from_csv(iofile)
        iofile.close()

        cls.new_circuit_duplicate_1 = {
            "cid": "Circuit 1",
            "provider": "Provider 1",
            "type": "Circuit-Type 1",
            "description": "My description 1",
            "install_date": "",
            "comments": "",
            "contacts": "",
            "tags": "",
            "side_a": "",
            "side_z": "",
            "device": "",
            "interface": "",
            "cir": 1000,
        }

        cls.new_circuit_add_1 = {
            "cid": "Circuit Test Add",
            "provider": "Provider 1",
            "type": "Circuit-Type 1",
            "description": "My description 1",
            "install_date": "",
            "comments": "",
            "contacts": "",
            "tags": "",
            "side_a": "Site 1",
            "side_z": "Provider-Network 1",
            "device": "Device 1",
            "interface": "Interface 1",
            "cir": 1000,
        }

        cls.new_circuit_add_2 = {
            "cid": "Circuit Test Add 2",
            "provider": "Provider 2",
            "type": "Circuit-Type 2",
            "description": "My description 2",
            "install_date": "",
            "comments": "",
            "contacts": "",
            "tags": "",
            "side_a": "",
            "side_z": "",
            "device": "",
            "interface": "",
            "cir": 1000,
        }

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
        )
        DeviceType.objects.bulk_create(device_types)
        DeviceRole.objects.create(name='Device-Role 1', slug='device-role-1')

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
        )
        Device.objects.bulk_create(devices)

        interfaces = (
            Interface(name="Interface 1", device=devices[0], type=InterfaceTypeChoices.TYPE_1GE_FIXED),
            Interface(name="Interface 2", device=devices[1], type=InterfaceTypeChoices.TYPE_1GE_FIXED),
            Interface(name="Interface 3", device=devices[2], type=InterfaceTypeChoices.TYPE_1GE_FIXED),
        )
        Interface.objects.bulk_create(interfaces)
    
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
        # Load File
        script_dir = os.path.dirname(__file__)
        csv_test_filename = "csv_bulk_circuits_test.csv"
        filename = os.path.join(script_dir, csv_test_filename)
        with open(filename, mode="rb") as iofile:
            csv_data = load_data_from_csv(iofile)

        self.assertIsInstance(csv_data, list)
        self.assertIsInstance(csv_data[0], dict)

    def test_validate_row(self):
        row = {
            "cid": "Circuit Test",
            "provider": "Provider 1",
            "type": "Circuit-Type 1",
            "side_a": "Site 1",
            "device": "Device 1",
            "interface": "Interface 1",
            "side_z": "Provider-Network 1",
            "description": "Description 1",
            "install_date": "",
            "cir": "10485760",
            "comments": "",
            "contacts": "",
            "tags": "",
        }
        skip = validate_row(row)
        self.assertFalse(skip)

    def test_validate_row_fail_1(self):
        row = {
            # Missing cid
            "provider": "Provider 1",
            "type": "Circuit-Type 1",
            "side_a": "Site 1",
            "device": "Device 1",
            "interface": "Interface 1",
            "side_z": "Provider-Network 1",
            "description": "Description 1",
            "install_date": "",
            "cir": "10485760",
            "comments": "",
            "contacts": "",
            "tags": "",
        }
        skip = validate_row(row)
        self.assertTrue(skip)

    def test_validate_row_fail_2(self):
        row = {
            "provider": "Provider 1",
            # Missing Circuit Type
            "side_a": "Site 1",
            "device": "Device 1",
            "interface": "Interface 1",
            "side_z": "Provider-Network 1",
            "description": "Description 1",
            "install_date": "",
            "cir": "10485760",
            "comments": "",
            "contacts": "",
            "tags": "",
        }
        skip = validate_row(row)
        self.assertTrue(skip)

    def test_prepare_netbox_row(self):
        row = {
            "cid": "Circuit Test",
            "provider": "Provider 1",
            "type": "Circuit-Type 1",
            "side_a": "Site 1",
            "device": "Device 1",
            "interface": "Interface 1",
            "side_z": "Provider-Network 1",
            "description": "Description 1",
            "install_date": "",
            "cir": "10485760",
            "comments": "",
            "contacts": "",
            "tags": "",
        }

        circuit_data = prepare_netbox_row(row)
        self.assertFalse(circuit_data["skip"])  # Valid Circuit

    def test_prepare_netbox_row_fail_1(self):
        row = {
            "cid": "Circuit Test",
            "provider": "Provider Missing",
            "type": "Circuit-Type 1",
            "side_a": "Site 1",
            "device": "Device 1",
            "interface": "Interface 1",
            "side_z": "Provider-Network 1",
            "description": "Description 1",
            "install_date": "",
            "cir": "10485760",
            "comments": "",
            "contacts": "",
            "tags": "",
        }

        circuit_data = prepare_netbox_row(row)
        self.assertTrue(circuit_data["skip"])   # Invalid Circuit

    def test_prepare_netbox_data(self):
        netbox_data = prepare_netbox_data(self.csv_data)

        self.assertFalse(netbox_data[0]["skip"])
        self.assertTrue(netbox_data[1]["skip"])     # Missing Provider
        self.assertTrue(netbox_data[2]["skip"])     # Missing Circuit Type
        self.assertFalse(netbox_data[3]["skip"])

    def test_create_circuit_from_data(self):
        netbox_data = prepare_netbox_data(self.csv_data)[0] # Only need 1 circuit
        new_circuit = create_circuit_from_data(netbox_data)
        self.assertIsInstance(new_circuit, Circuit)

    def test_save_circuit(self):
        netbox_data = prepare_netbox_data(self.csv_data)[0]
        new_circuit = create_circuit_from_data(netbox_data)

        with self.assertLogs(
            "netbox.scripts.scripts.circuit_adder.SingleCircuit", level="INFO"
        ) as logs:  # LogLevelChoices.LOG_SUCCESS
            output = save_circuit(new_circuit, self=SingleCircuit())

        self.assertIn("Saved circuit:", logs.output[0])

    def test_save_circuit_duplicate(self):
        netbox_data = prepare_netbox_row(self.new_circuit_duplicate_1)
        new_circuit = create_circuit_from_data(netbox_data)

        with self.assertLogs(
            "netbox.scripts.scripts.circuit_adder.SingleCircuit", level="ERROR"
        ) as logs:  # LogLevelChoices.LOG_??
            output = save_circuit(new_circuit, self=SingleCircuit())

        self.assertIn("already exists.", logs.output[0])

    def test_check_circuit_duplicate_1(self):
        netbox_data = prepare_netbox_row(self.new_circuit_duplicate_1)
        duplicate = check_circuit_duplicate(netbox_data)
        self.assertTrue(duplicate) # No duplicate

    def test_check_circuit_duplicate_2(self):
        netbox_data = prepare_netbox_row(self.new_circuit_add_1)
        duplicate = check_circuit_duplicate(netbox_data)
        self.assertFalse(duplicate) # No duplicate

    def test_update_existing_circuit(self):
        existing_circuit = Circuit.objects.first()
        netbox_row = prepare_netbox_row(self.new_circuit_duplicate_1)
        netbox_row["install_date"] = "updated"
        circuit = update_existing_circuit(existing_circuit, netbox_row)

        self.assertIsInstance(circuit, Circuit)
        self.assertEquals(circuit.install_date, "updated")

    def test_build_circuit_new(self):
        netbox_row = prepare_netbox_row(self.new_circuit_add_1)
        overwrite = False
        circuit = build_circuit(SingleCircuit(), netbox_row, overwrite)
        self.assertIsInstance(circuit, Circuit)

    def test_build_circuit_duplicate_overwrite(self):
        netbox_row = prepare_netbox_row(self.new_circuit_duplicate_1)
        overwrite = True

        with self.assertLogs(
            "netbox.scripts.scripts.circuit_adder.SingleCircuit", level="WARNING"
        ) as logs:  # LogLevelChoices.LOG_??
            circuit = build_circuit(SingleCircuit(), netbox_row, overwrite)

        self.assertIn("Overwrites enabled, updating existing circuit", logs.output[0])

    def test_build_circuit_duplicate_no_overwrite(self):
        netbox_row = prepare_netbox_row(self.new_circuit_duplicate_1)
        overwrite = False

        with self.assertLogs(
            "netbox.scripts.scripts.circuit_adder.SingleCircuit", level="ERROR"
        ) as logs:  # LogLevelChoices.LOG_??
            circuit = build_circuit(SingleCircuit(), netbox_row, overwrite)

        self.assertIn("overwrites are disabled, skipping.", logs.output[0])

    def test_build_terminations(self):
        netbox_row = prepare_netbox_row(self.new_circuit_add_1)
        circuit = build_circuit(SingleCircuit(), netbox_row)

        termination_a = build_terminations(SingleCircuit(), netbox_row, circuit)

        self.assertIsInstance(termination_a, CircuitTermination)

    def test_build_terminations_missing_interface(self):
        new_circuit_add_missing_interface_1 = {
            "cid": "Circuit Test Add Missing Interface",
            "provider": "Provider 2",
            "type": "Circuit-Type 2",
            "description": "My description 2",
            "install_date": "",
            "comments": "",
            "contacts": "",
            "tags": "",
            "side_a": "Site 1",
            "side_z": "",
            "device": "Device 1",
            "interface": "",
            "cir": 1000,
        }
        netbox_row = prepare_netbox_row(new_circuit_add_missing_interface_1)
        circuit = build_circuit(SingleCircuit(), netbox_row)

        with self.assertLogs(
            "netbox.scripts.scripts.circuit_adder.SingleCircuit", level="WARNING"
        ) as logs:  # LogLevelChoices.LOG_??
            termination_a = build_terminations(SingleCircuit(), netbox_row, circuit)

        self.assertIn("due to missing Device Interface", logs.output[0])

    def test_build_terminations_missing_site(self):
        new_circuit_add_missing_site = {
            "cid": "Circuit Test Add Missing Site",
            "provider": "Provider 2",
            "type": "Circuit-Type 2",
            "description": "My description 2",
            "install_date": "",
            "comments": "",
            "contacts": "",
            "tags": "",
            "side_a": "Site Missing",
            "side_z": "",
            "device": "Device 1",
            "interface": "",
            "cir": 1000,
        }
        netbox_row = prepare_netbox_row(new_circuit_add_missing_site)
        circuit = build_circuit(SingleCircuit(), netbox_row)

        with self.assertLogs(
            "netbox.scripts.scripts.circuit_adder.SingleCircuit", level="WARNING"
        ) as logs:  # LogLevelChoices.LOG_??
            termination_a = build_terminations(SingleCircuit(), netbox_row, circuit)

        self.assertIn("due to missing Site", logs.output[0])

    def test_build_terminations_missing_provider_network(self):
        new_circuit_add_missing_provider_network = {
            "cid": "Circuit Test Add Missing Provider Network",
            "provider": "Provider 2",
            "type": "Circuit-Type 2",
            "description": "My description 2",
            "install_date": "",
            "comments": "",
            "contacts": "",
            "tags": "",
            "side_a": "Site 1",
            "side_z": "Provider Network Missing",
            "device": "Device 1",
            "interface": "Interface 1",
            "cir": 1000,
        }
        netbox_row = prepare_netbox_row(new_circuit_add_missing_provider_network)
        circuit = build_circuit(SingleCircuit(), netbox_row)

        with self.assertLogs(
            "netbox.scripts.scripts.circuit_adder.SingleCircuit", level="WARNING"
        ) as logs:  # LogLevelChoices.LOG_??
            termination_a = build_terminations(SingleCircuit(), netbox_row, circuit)

        self.assertIn("due to missing Provider Network", logs.output[0])
