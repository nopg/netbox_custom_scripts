# /admin: custom_validators = {'circuits.circuit': ['local.validators.MyValidator']}

from circuits.models import Circuit
from extras.validators import CustomValidator


class MyCircuitValidator(CustomValidator):

    def validate(self, circuit: Circuit, manual=False):
        failed = False
        if not circuit.cid.startswith("my"):
            failed = f"Circuit ID '{circuit.cid}' must start with 'my'."
            # JUST SUCCEED FOR NOW
            return False  # no error
            if manual:
                return failed
            else:
                self.fail(failed, field='cid')
