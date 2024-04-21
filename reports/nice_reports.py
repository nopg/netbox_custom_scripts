from circuits.models import Circuit
from dcim.models import Device
from extras.reports import Report

# from local.validators import MyCircuitValidator


class CircuitCableReport(Report):
    name = "Circuit Cable Report"
    description = "Retrieve Circuits that do not have a cable terminated on either side."
    scheduling_enabled = False

    def test_circuit_cables(self):
        circuits = Circuit.objects.all()
        circuits_with = []
        circuits_without = []

        for circuit in circuits:
            self.log_success(circuit)
            terms = circuit.terminations.all()
            if not terms:
                circuits_without.append(circuit)
                continue
            count = 0
            for term in terms:
                if term.cable:
                    count += 1
            if count == 0:
                circuits_without.append(circuit)
                continue
            else:
                circuits_with.append(circuit)

        self.log(f"With: {len(circuits_with)}")
        for circuit in circuits_with:
            self.log_info(circuit, "Has Cable Attached")

        self.log(f"Without: {len(circuits_without)}")
        for circuit in circuits_without:
            self.log_warning(circuit, "No Cable Attached")

        self.log(f"Total: {len(circuits_with) + len(circuits_without)}")


class ReviewReport(Report):
    name = "Circuits Needing Review"
    description = "Display Circuits needing extra review."
    scheduling_enabled = False

    def test_review_circuits(self):
        for circuit in Circuit.objects.all():
            review = circuit.cf.get("review")
            if review:
                self.log_info(circuit, "Needs Review")


class DeviceSNReport(Report):
    name = "Devices Missing Serial Number"
    description = "Display Devices with blank Serial Number"
    scheduling_enabled = False

    def test_device_missing_sn(self):
        for device in Device.objects.all():
            if not device.serial:
                if (
                    not "PDU" in device.name.upper()
                    and not "panel" in device.name.lower()
                    and not "cable mgmt" in device.name.lower()
                ):
                    self.log_info(device, "Missing Serial Number")


name = "Circuit Validation Report"
