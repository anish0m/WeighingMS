"""Story 006-dummy-scanner-and-printer: Dummy Printer."""

from django.test import TestCase

from dummy_orgatex.services import seed_training_scenario
from dummy_printer.models import DummyTicket
from tests.helpers import post_json

CONTENT = "FCI DYEING — WEIGHING TICKET\nBATCH   B-24187\nALL WITHIN TOLERANCE"


class PrinterApiTests(TestCase):
    def setUp(self):
        seed_training_scenario()

    def test_print_stores_ticket_and_returns_id(self):
        response = post_json(
            self.client, "/api/tickets", {"content": CONTENT, "batchId": "B-24187"}
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertIsInstance(body["ticketId"], int)
        self.assertEqual(body["content"], CONTENT)
        self.assertEqual(body["batchId"], "B-24187")
        self.assertIn("printedAt", body)
        self.assertEqual(DummyTicket.objects.count(), 1)

    def test_stored_ticket_is_returned_unchanged_by_id(self):
        ticket_id = post_json(self.client, "/api/tickets", {"content": CONTENT}).json()[
            "ticketId"
        ]

        response = self.client.get(f"/api/tickets/{ticket_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["content"], CONTENT)
        self.assertIsNone(response.json()["batchId"])

    def test_unknown_ticket_returns_404(self):
        response = self.client.get("/api/tickets/999")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "TICKET_NOT_FOUND")

    def test_status_is_ready(self):
        response = self.client.get("/api/printer/status")

        self.assertEqual(response.json(), {"status": "ready"})

    def test_invalid_tickets_return_400_and_store_nothing(self):
        cases = {
            "missing content": {},
            "blank content": {"content": "   "},
            "non-string content": {"content": 42},
            "batch id too long": {"content": CONTENT, "batchId": "B" * 33},
            "invalid json": "{nope",
        }
        for name, body in cases.items():
            with self.subTest(case=name):
                response = post_json(self.client, "/api/tickets", body)

                self.assertEqual(response.status_code, 400)
                self.assertEqual(DummyTicket.objects.count(), 0)
