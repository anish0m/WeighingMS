"""Stories 002-select-batch and 003-load-read-only-recipe: the station API.

``POST /station/api/selections`` and ``GET /station/api/selections/<id>``
(ADR-002), against the seeded Dummy OrgaTEX over real HTTP.
"""

import json
import time
from unittest.mock import patch

from django.test import Client, LiveServerTestCase, override_settings

from batches.models import BatchSelection
from dummy_orgatex.services import seed_training_scenario
from tests.batches import factories
from tests.helpers import post_json, set_mode

SELECTIONS = "/station/api/selections"


class LiveApiTestCase(LiveServerTestCase):
    def setUp(self):
        seed_training_scenario()
        self.enterContext(
            override_settings(ORGATEX_BASE_URL=f"{self.live_server_url}/api")
        )

    def select(self, batch_id="B-24187", method="touch"):
        return post_json(
            self.client, SELECTIONS, {"batchId": batch_id, "method": method}
        )

    def assert_error(self, response, status, code, message=None):
        self.assertEqual(response.status_code, status)
        error = response.json()["error"]
        self.assertEqual(error["code"], code)
        if message is not None:
            self.assertEqual(error["message"], message)
        self.assertEqual(BatchSelection.objects.count(), 0)


class SelectApiTests(LiveApiTestCase):
    def test_touch_b24187_returns_201_with_header(self):
        response = self.select()

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["method"], "touch")
        self.assertEqual(
            body["batch"],
            {
                "batchId": "B-24187",
                "orderId": "SO-9931",
                "machine": "JET-04",
                "fabricLot": "100% CTN knit · 480 kg",
                "shade": "Teal 4C",
                "componentCount": 5,
                "status": "QUEUED",
            },
        )

    def test_scan_b24187_returns_201(self):
        response = self.select(method="scan")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["method"], "scan")

    def test_recipe_components_in_sequence_with_all_fields(self):
        recipe = self.select().json()["recipe"]

        self.assertEqual(recipe["recipeName"], "Teal 4C")
        self.assertEqual([c["sequence"] for c in recipe["components"]], [1, 2, 3, 4, 5])
        self.assertEqual(
            recipe["components"][2],
            {
                "sequence": 3,
                "code": "DYE-4471",
                "name": "Remazol Yellow RGB",
                "colour": "#d9a520",
                "targetQty": "94.0000",
                "unit": "g",
                "tolerance": "0.5000",
                "displayMax": "125.0000",
                "lot": "2026-0387",
                "container": "C-12",
                "tare": "214.0000",
                "state": "pending",
            },
        )

    def test_quantities_are_strings_never_json_numbers(self):
        raw = self.select().content.decode()

        components = json.loads(raw, parse_float=self.fail)["recipe"]["components"]
        for component in components:
            for key in ("targetQty", "tolerance", "displayMax", "tare"):
                self.assertIsInstance(component[key], str)

    def test_recipe_is_available_within_3_seconds(self):
        started = time.perf_counter()
        response = self.select()
        elapsed = time.perf_counter() - started

        self.assertEqual(response.status_code, 201)
        self.assertLess(elapsed, 3.0)

    def test_batch_id_is_trimmed(self):
        response = self.select(batch_id="  B-24187 ")

        self.assertEqual(response.json()["batch"]["batchId"], "B-24187")


class RefusalApiTests(LiveApiTestCase):
    def test_unknown_batch_is_404_batch_not_found(self):
        self.assert_error(
            self.select("B-99999", "scan"), 404, "BATCH_NOT_FOUND", "Batch not found"
        )

    def test_batch_without_recipe_is_409_with_reason(self):
        self.assert_error(
            self.select("B-24188"),
            409,
            "RECIPE_NOT_AVAILABLE",
            "Recipe not available in training data",
        )

    def test_orgatex_unavailable_is_503(self):
        set_mode(self.client, "orgatex", "unavailable")

        self.assert_error(
            self.select(), 503, "ORGATEX_UNAVAILABLE", "OrgaTEX unavailable"
        )

    @patch("batches.services.adapter")
    def test_batch_not_released_is_409(self, adapter):
        adapter.fetch_batch.return_value = factories.batch(status="WEIGHED")

        self.assert_error(self.select(), 409, "NOT_RELEASED", "Batch not released")


class ValidationTests(LiveApiTestCase):
    def post_raw(self, data):
        return self.client.post(SELECTIONS, data, content_type="application/json")

    def test_invalid_requests_are_400(self):
        cases = {
            "not json": "{batchId",
            "array": "[]",
            "missing batchId": json.dumps({"method": "touch"}),
            "blank batchId": json.dumps({"batchId": "  ", "method": "touch"}),
            "number batchId": json.dumps({"batchId": 24187, "method": "touch"}),
            "too long": json.dumps({"batchId": "B" * 33, "method": "touch"}),
            "missing method": json.dumps({"batchId": "B-24187"}),
            "unknown method": json.dumps({"batchId": "B-24187", "method": "wave"}),
        }
        for name, data in cases.items():
            with self.subTest(case=name):
                self.assert_error(self.post_raw(data), 400, "INVALID_REQUEST")


class SelectionDetailTests(LiveApiTestCase):
    def test_get_returns_the_stored_snapshot(self):
        created = self.select().json()

        response = self.client.get(f"{SELECTIONS}/{created['selectionId']}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), created)

    def test_stored_snapshot_survives_orgatex_going_down(self):
        created = self.select().json()
        set_mode(self.client, "orgatex", "unavailable")

        response = self.client.get(f"{SELECTIONS}/{created['selectionId']}")

        self.assertEqual(response.json()["recipe"], created["recipe"])

    def test_unknown_selection_is_404(self):
        response = self.client.get(f"{SELECTIONS}/999")

        self.assert_error(response, 404, "SELECTION_NOT_FOUND")


class NoEditPathTests(LiveApiTestCase):
    """C-01, story 003 AC 2: no endpoint changes a recipe."""

    def test_selection_cannot_be_changed_or_deleted(self):
        selection_id = self.select().json()["selectionId"]
        url = f"{SELECTIONS}/{selection_id}"
        body = json.dumps({"recipe": {"recipeName": "Changed"}})

        for method in ("put", "patch", "post", "delete"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    url, body, content_type="application/json"
                )
                self.assertEqual(response.status_code, 405)

        self.assertEqual(BatchSelection.objects.get().recipe_name, "Teal 4C")

    def test_collection_accepts_only_post(self):
        for method in ("get", "put", "patch", "delete"):
            with self.subTest(method=method):
                self.assertEqual(
                    getattr(self.client, method)(SELECTIONS).status_code, 405
                )


class CsrfTests(LiveApiTestCase):
    def test_post_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)

        response = post_json(
            client, SELECTIONS, {"batchId": "B-24187", "method": "touch"}
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(BatchSelection.objects.count(), 0)
