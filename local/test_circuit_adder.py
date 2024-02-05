#
# export NETBOX_CONFIGURATION=netbox.configuration_testing
# python manage.py test scripts.testing_circuits -v 3 --keepdb

from circuits.models import Circuit, CircuitType, Provider
from utilities.testing.base import TestCase
#from extras.choices import LogLevelChoices
from extras.scripts import Script
from scripts.circuit_adder import BulkCircuits

from .utils import save_circuit, prepare_netbox_row, circuit_duplicate, create_circuit


class CircuitAdderTestCase(TestCase):
    """
    check dupe

    :form_data: Data to be used when creating a new object.
    """

    form_data = {}

    def setUp(self):
        super().setUp()

        providers = (
            Provider(name='Provider 1', slug='provider-1'),
            Provider(name='Provider 2', slug='provider-2'),
        )
        Provider.objects.bulk_create(providers)

        circuittypes = (
            CircuitType(name='Circuit Type 1', slug='circuit-type-1'),
            CircuitType(name='Circuit Type 2', slug='circuit-type-2'),
        )
        CircuitType.objects.bulk_create(circuittypes)

        circuits = (
            Circuit(cid='Circuit 1', provider=providers[0], type=circuittypes[0]),
            Circuit(cid='Circuit 2', provider=providers[0], type=circuittypes[0]),
            Circuit(cid='Circuit 3', provider=providers[0], type=circuittypes[0]),
        )

        Circuit.objects.bulk_create(circuits)

    def test_duplicate_1(self):
        x = 5
        self.assertEquals(x, 5)

    def test_save_circuit(self):
        circuit = {
            "cid": 'myCircuit 10',
            "provider": "Provider 1",
            "type": "Circuit Type 1",
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
        circuit = prepare_netbox_row(circuit)
        circuit = create_circuit(circuit)

        with self.assertLogs(
            "netbox.scripts.scripts.circuit_adder.BulkCircuits", level="INFO"
        ) as logs:  # LogLevelChoices.LOG_SUCCESS
            output = save_circuit(circuit, self=BulkCircuits())

        # ['INFO:netbox.scripts.scripts.circuit_adder.BulkCircuits:Created circuit: Circuit 10']
        self.assertIn("Saved circuit:", logs.output[0])

    # def test_add_circuit_duplicate_overwrite(self):
    #     circuit = {
    #         "cid": 'Circuit 1',
    #         "provider": "Provider 1",
    #         "type": "Circuit Type 1",
    #         "description": "My description 1",
    #         "cir": 1000,
    #     }

    #     with self.assertLogs(
    #         "netbox.scripts.scripts.circuit_adder.SingleCircuit", level="WARNING"
    #     ) as logs:  # LogLevelChoices.LOG_WARNING
    #         output = add_circuit_data(circuit, overwrite=True, self=SingleCircuit())

    #     # ['WARNING:netbox.scripts.scripts.circuit_adder.BulkCircuits:Overwrites enabled, updating existing circuit: Circuit 1 ! See change log for original values.']
    #     self.assertIn("Overwrites enabled, updating existing circuit:", logs.output[0])

    def test_duplicate_circuit(self):
        circuit = {
            "cid": 'Circuit 1',
            "provider": "Provider 1",
            "type": "Circuit Type 1",
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
        self.assertTrue(circuit_duplicate(circuit))
