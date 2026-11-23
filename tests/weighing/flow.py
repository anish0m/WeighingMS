"""Live weighing flow for bolt 010 tests: Dummy Scale + Dummy Scanner over HTTP.

Each test gets the training seed (scales, scanner), operator OP-01 and an open
B-24187 session. ``LiveServerTestCase`` flushes the database between tests, so
the operator is re-created here.
"""

from django.test import LiveServerTestCase, override_settings

from dummy_orgatex.services import seed_training_scenario
from tests.helpers import post_json, set_mode
from tests.weighing import factories
from weighing import identity
from weighing.models import Operator

# sequence: (scale_id, unit, code, a weight within tolerance)
TEAL = {
    1: ("scale-3kg", "g", "DYE-1180", "1241.5"),
    2: ("scale-3kg", "g", "DYE-2204", "385.4"),
    3: ("scale-3kg", "g", "DYE-4471", "94.2"),
    4: ("scale-32kg", "kg", "AUX-0101", "24.048"),
    5: ("scale-32kg", "kg", "AUX-0107", "9.612"),
}
BLUE, RED, YELLOW, SODIUM, SODA = 1, 2, 3, 4, 5
UNREACHABLE = "http://127.0.0.1:9/api"


class LiveFlowTestCase(LiveServerTestCase):
    def setUp(self):
        seed_training_scenario()
        Operator.objects.get_or_create(
            operator_id="OP-01", defaults={"name": "R. Karim", "shift": "A"}
        )
        self.api = f"{self.live_server_url}/api"
        self.enterContext(
            override_settings(SCANNER_BASE_URL=self.api, SCALE_BASE_URL=self.api)
        )
        self.session = factories.session()

    # Dummy training controls -------------------------------------------------

    def set_weight(self, sequence, weight):
        scale_id, unit, _, _ = TEAL[sequence]
        response = post_json(
            self.client,
            f"/api/training/scales/{scale_id}/simulate",
            {"action": "set", "weight": weight, "unit": unit},
        )
        self.assertEqual(response.status_code, 200, response.content)

    def scale_weight(self, scale_id):
        return self.client.get(f"/api/scales/{scale_id}/weight").json()["netWeight"]

    def scale_mode(self, scale_id, mode):
        set_mode(self.client, scale_id, mode)

    def verify(self, sequence, code=None, session=None):
        """Scan the component's code and record the identity check (bolt 008)."""
        session = session or self.session
        code = code or TEAL[sequence][2]
        scan_id = post_json(
            self.client,
            "/api/training/scanner/scans",
            {"kind": "dyestuff", "code": code},
        ).json()["scanId"]
        identity.verify_identity(session.pk, sequence, scan_id, "OP-01")
