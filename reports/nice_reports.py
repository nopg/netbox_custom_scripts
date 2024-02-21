from circuits.models import Circuit
from extras.reports import Report

from local.validators import MyCircuitValidator


class CircuitIDReport(Report):
    name = "Circuit CID Validation"
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

class ReviewReport(Report):
    name = "Circuits that Need Review"
    description = "Display Circuits needing extra review."
    scheduling_enabled = False

    def test_review_circuits(self):
        for circuit in Circuit.objects.all():
            review = circuit.cf.get("review")
            if review:
                self.log_info(circuit, "Needs Review")


name = "Circuit Validation Report"