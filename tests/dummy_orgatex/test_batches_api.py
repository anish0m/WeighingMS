"""Story 002-dummy-orgatex-batch-endpoints."""

from datetime import datetime

from django.test import TestCase

from dummy_orgatex.services import seed_training_scenario

BATCH_KEYS = {
    "batchId",
    "orderId",
    "machine",
    "fabricLot",
    "shade",
    "componentCount",
    "status",
}


class BatchListApiTests(TestCase):
    def setUp(self):
        seed_training_scenario()

    def test_queue_returns_the_four_seeded_batches_in_order(self):
        response = self.client.get("/api/batches")

        self.assertEqual(response.status_code, 200)
        batches = response.json()["batches"]
        self.assertEqual(
            [b["batchId"] for b in batches],
            ["B-24187", "B-24188", "B-24190", "B-24191"],
        )
        for batch in batches:
            self.assertEqual(set(batch), BATCH_KEYS)

    def test_queue_includes_received_time(self):
        body = self.client.get("/api/batches").json()

        received = datetime.fromisoformat(body["receivedAt"])
        self.assertIsNotNone(received.tzinfo)

    def test_queue_row_carries_prototype_values(self):
        first = self.client.get("/api/batches").json()["batches"][0]

        self.assertEqual(
            first,
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

    def test_queue_rejects_post(self):
        response = self.client.post("/api/batches")

        self.assertEqual(response.status_code, 405)


class BatchDetailApiTests(TestCase):
    def setUp(self):
        seed_training_scenario()

    def test_known_batch_returns_its_details(self):
        response = self.client.get("/api/batches/B-24187")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["batchId"], "B-24187")
        self.assertEqual(body["machine"], "JET-04")
        self.assertEqual(set(body), BATCH_KEYS)

    def test_unknown_batch_returns_404_in_standard_error_format(self):
        response = self.client.get("/api/batches/B-99999")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "BATCH_NOT_FOUND")
        self.assertIn("message", response.json()["error"])
