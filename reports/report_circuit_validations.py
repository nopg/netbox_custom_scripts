from circuits.models import Circuit
from extras.reports import Report

from local.validators import MyCircuitValidator

# A modified John Anderson's NetBox Day 2020 Presentation by adding a check for all sites, not just LAX
# All credit goes to @lampwins

class CircuitIDReport(Report):
    #description = "Verify each device conforms to naming convention Example: (site_name)-RTR-1 or (site_name)-SW-2"
    description = "Circuit Validation Report"
    
    def test_circuit_naming(self):
       validator = MyCircuitValidator()
       for circuit in Circuit.objects.all():
           # Change the naming standard based on the re.match
           failed = validator.validate(circuit = circuit, manual = True)
           if not failed:
               self.log_success(circuit, f"{circuit.cid} is valid!")
           else:
               self.log_failure(circuit, f"{circuit.cid} does not conform to standard!")

name = "Circuit Validation Report"