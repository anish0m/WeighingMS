"""Story 005-dummy-scale-api: training simulate controls (DB-6)."""

from decimal import Decimal

from django.test import TestCase

from dummy_orgatex.services import seed_training_scenario
from tests.helpers import post_json

URL = "/api/training/scales/{}/simulate"
YELLOW = {"target": "94.0", "tolerance": "0.5", "unit": "g"}


class SimulateTests(TestCase):
    def setUp(self):
        seed_training_scenario()

    def _simulate(self, body, scale_id="scale-3kg"):
        return post_json(self.client, URL.format(scale_id), body)

    def _weight(self, scale_id="scale-3kg"):
        body = self.client.get(f"/api/scales/{scale_id}/weight").json()
        return Decimal(body["netWeight"]), body["unit"]

    def test_dispense_lands_at_target_plus_0_4_tolerance(self):
        response = self._simulate({"action": "dispense", **YELLOW})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._weight(), (Decimal("94.2"), "g"))

    def test_overshoot_lands_at_target_plus_4_8_tolerance(self):
        self._simulate({"action": "overshoot", **YELLOW})

        self.assertEqual(self._weight(), (Decimal("96.4"), "g"))

    def test_reset_returns_weight_to_zero(self):
        self._simulate({"action": "overshoot", **YELLOW})

        self._simulate({"action": "reset"})

        self.assertEqual(self._weight(), (Decimal("0.0"), "g"))

    def test_set_exact_weight_for_tolerance_boundaries(self):
        for weight in ("93.4", "93.5", "94.0", "94.5", "94.6"):
            with self.subTest(weight=weight):
                self._simulate({"action": "set", "weight": weight, "unit": "g"})

                self.assertEqual(self._weight(), (Decimal(weight), "g"))

    def test_dispense_on_floor_scale_in_kg(self):
        # Sodium Sulphate 24.000 kg +/- 0.120 kg -> 24.048 kg
        self._simulate(
            {"action": "dispense", "target": "24.000", "tolerance": "0.120",
             "unit": "kg"},
            scale_id="scale-32kg",
        )  # fmt: skip

        self.assertEqual(self._weight("scale-32kg"), (Decimal("24.048"), "kg"))

    def test_response_is_the_new_reading(self):
        response = self._simulate({"action": "dispense", **YELLOW})

        body = response.json()
        self.assertEqual(body["netWeight"], "94.2000")
        self.assertEqual(body["unit"], "g")

    def test_invalid_requests_return_400_and_leave_weight_unchanged(self):
        cases = {
            "unknown action": {"action": "explode"},
            "missing action": {},
            "unit mismatch": {"action": "dispense", **YELLOW, "unit": "kg"},
            "float target": {"action": "dispense", **YELLOW, "target": 94.0},
            "non-decimal tolerance": {"action": "dispense", **YELLOW,
                                      "tolerance": "half"},
            "negative weight": {"action": "set", "weight": "-1", "unit": "g"},
            "over capacity": {"action": "set", "weight": "3000.1", "unit": "g"},
            "not an object": [],
            "invalid json": "{nope",
        }  # fmt: skip
        for name, body in cases.items():
            with self.subTest(case=name):
                response = self._simulate(body)

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")
                self.assertEqual(self._weight(), (Decimal(0), "g"))

    def test_unknown_scale_returns_404(self):
        response = self._simulate({"action": "reset"}, scale_id="scale-99kg")

        self.assertEqual(response.status_code, 404)
