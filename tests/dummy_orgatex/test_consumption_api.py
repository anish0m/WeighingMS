"""Story 004-dummy-orgatex-consumption-endpoint."""

import json
from datetime import datetime
from decimal import Decimal

from django.test import TestCase

from dummy_orgatex.models import DummyConsumption, DummyConsumptionLine
from dummy_orgatex.services import seed_training_scenario

URL = "/api/batches/B-24187/consumption"


def _payload(key="K-1", components=None):
    return {
        "idempotencyKey": key,
        "components": components
        if components is not None
        else [
            {"code": "DYE-1180", "actualQty": "1241.5", "unit": "g"},
            {"code": "DYE-4471", "actualQty": "94.2", "unit": "g"},
            {"code": "AUX-0101", "actualQty": "24.010", "unit": "kg"},
        ],
    }


class ConsumptionApiTests(TestCase):
    def setUp(self):
        seed_training_scenario()

    def _post(self, body, url=URL):
        data = body if isinstance(body, str) else json.dumps(body)
        return self.client.post(url, data, content_type="application/json")

    def test_valid_post_is_stored_and_returns_acceptance_time(self):
        response = self._post(_payload())

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["batchId"], "B-24187")
        self.assertEqual(body["idempotencyKey"], "K-1")
        self.assertFalse(body["duplicate"])
        self.assertIsNotNone(datetime.fromisoformat(body["acceptedAt"]).tzinfo)
        self.assertEqual(DummyConsumption.objects.count(), 1)
        line = DummyConsumptionLine.objects.get(code="DYE-4471")
        self.assertEqual(line.actual_qty, Decimal("94.2"))

    def test_repeated_key_returns_success_without_second_record(self):
        first = self._post(_payload()).json()

        response = self._post(_payload())

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["duplicate"])
        self.assertEqual(body["acceptedAt"], first["acceptedAt"])
        self.assertEqual(DummyConsumption.objects.count(), 1)
        self.assertEqual(DummyConsumptionLine.objects.count(), 3)

    def test_different_keys_are_stored_separately(self):
        self._post(_payload("K-1"))
        self._post(_payload("K-2"))

        self.assertEqual(DummyConsumption.objects.count(), 2)

    def test_malformed_payloads_return_validation_error_and_store_nothing(self):
        cases = {
            "invalid json": "{not json",
            "not an object": [],
            "missing key": {"components": _payload()["components"]},
            "blank key": _payload(key="  "),
            "missing components": {"idempotencyKey": "K-x"},
            "empty components": _payload(components=[]),
            "float quantity": _payload(
                components=[{"code": "DYE-4471", "actualQty": 94.2, "unit": "g"}]
            ),
            "non-decimal quantity": _payload(
                components=[{"code": "DYE-4471", "actualQty": "abc", "unit": "g"}]
            ),
            "negative quantity": _payload(
                components=[{"code": "DYE-4471", "actualQty": "-1", "unit": "g"}]
            ),
            "unknown component": _payload(
                components=[{"code": "DYE-0000", "actualQty": "1", "unit": "g"}]
            ),
            "wrong unit": _payload(
                components=[{"code": "DYE-4471", "actualQty": "94.2", "unit": "kg"}]
            ),
            "duplicate component": _payload(
                components=[
                    {"code": "DYE-4471", "actualQty": "94.2", "unit": "g"},
                    {"code": "DYE-4471", "actualQty": "94.1", "unit": "g"},
                ]
            ),
        }
        for name, body in cases.items():
            with self.subTest(case=name):
                response = self._post(body)

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")
                self.assertEqual(DummyConsumption.objects.count(), 0)
                self.assertEqual(DummyConsumptionLine.objects.count(), 0)

    def test_unknown_batch_returns_404(self):
        response = self._post(_payload(), url="/api/batches/B-99999/consumption")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "BATCH_NOT_FOUND")
        self.assertEqual(DummyConsumption.objects.count(), 0)

    def test_batch_without_recipe_returns_recipe_not_available(self):
        response = self._post(_payload(), url="/api/batches/B-24188/consumption")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "RECIPE_NOT_AVAILABLE")
        self.assertEqual(DummyConsumption.objects.count(), 0)

    def test_key_reused_on_another_batch_returns_conflict(self):
        self._post(_payload("K-shared"))

        response = self._post(
            _payload("K-shared"), url="/api/batches/B-24188/consumption"
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "IDEMPOTENCY_KEY_CONFLICT")
        self.assertEqual(DummyConsumption.objects.count(), 1)

    def test_read_back_lists_stored_consumptions_with_string_quantities(self):
        self._post(_payload())

        response = self.client.get(URL)

        self.assertEqual(response.status_code, 200)
        consumptions = response.json()["consumptions"]
        self.assertEqual(len(consumptions), 1)
        self.assertEqual(consumptions[0]["idempotencyKey"], "K-1")
        quantities = [c["actualQty"] for c in consumptions[0]["components"]]
        self.assertTrue(all(isinstance(q, str) for q in quantities))
        self.assertEqual(Decimal(quantities[1]), Decimal("94.2"))

    def test_read_back_of_unknown_batch_returns_404(self):
        response = self.client.get("/api/batches/B-99999/consumption")

        self.assertEqual(response.status_code, 404)

    def test_endpoint_accepts_post_without_csrf_token(self):
        client = self.client_class(enforce_csrf_checks=True)

        response = client.post(
            URL, json.dumps(_payload()), content_type="application/json"
        )

        self.assertEqual(response.status_code, 201)
