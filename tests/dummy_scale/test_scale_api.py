"""Story 005-dummy-scale-api: list, status, weight and tare."""

from datetime import datetime
from decimal import Decimal

from django.test import TestCase

from dummy_orgatex.services import seed_training_scenario
from tests.helpers import post_json

SIMULATE = "/api/training/scales/{}/simulate"


class ScaleApiTests(TestCase):
    def setUp(self):
        seed_training_scenario()

    def test_list_returns_precision_and_floor_scale(self):
        response = self.client.get("/api/scales")

        self.assertEqual(response.status_code, 200)
        scales = {s["scaleId"]: s for s in response.json()["scales"]}
        self.assertEqual(set(scales), {"scale-3kg", "scale-32kg"})
        self.assertEqual(scales["scale-3kg"]["name"], "3 kg precision")
        self.assertEqual(scales["scale-3kg"]["unit"], "g")
        self.assertEqual(scales["scale-32kg"]["name"], "32 kg floor")
        self.assertEqual(scales["scale-32kg"]["unit"], "kg")
        self.assertEqual(Decimal(scales["scale-32kg"]["capacity"]), Decimal(32))

    def test_status_returns_ready(self):
        response = self.client.get("/api/scales/scale-3kg/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"scaleId": "scale-3kg", "status": "ready"})

    def test_weight_returns_decimal_string_unit_and_status(self):
        response = self.client.get("/api/scales/scale-32kg/weight")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["scaleId"], "scale-32kg")
        self.assertIsInstance(body["netWeight"], str)
        self.assertEqual(Decimal(body["netWeight"]), Decimal(0))
        self.assertEqual(body["unit"], "kg")
        self.assertEqual(body["status"], "ready")
        self.assertIsNotNone(datetime.fromisoformat(body["readAt"]).tzinfo)

    def test_tare_sets_net_weight_to_zero(self):
        post_json(
            self.client,
            SIMULATE.format("scale-3kg"),
            {"action": "set", "weight": "94.2", "unit": "g"},
        )

        response = self.client.post("/api/scales/scale-3kg/tare")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.json()["netWeight"]), Decimal(0))
        weight = self.client.get("/api/scales/scale-3kg/weight").json()["netWeight"]
        self.assertEqual(Decimal(weight), Decimal(0))

    def test_tare_requires_post(self):
        response = self.client.get("/api/scales/scale-3kg/tare")

        self.assertEqual(response.status_code, 405)

    def test_unknown_scale_returns_404_everywhere(self):
        for url in (
            "/api/scales/scale-99kg/status",
            "/api/scales/scale-99kg/weight",
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json()["error"]["code"], "SCALE_NOT_FOUND")
        response = self.client.post("/api/scales/scale-99kg/tare")
        self.assertEqual(response.status_code, 404)
