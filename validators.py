# /admin: custom_validators = {'circuits.circuit': ['local.validators.MyValidator']}

from extras.validators import CustomValidator
from circuits.models import Circuit

class MyCircuitValidator(CustomValidator):

    def validate(self, circuit: Circuit, manual = False):
        if not circuit.cid.startswith("my"):
            failed_message = f"Circuit ID '{circuit.cid}' must start with 'my'."
            if manual:
                return failed_message
            else:
                self.fail(failed_message, field='cid')
