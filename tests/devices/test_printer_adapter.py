"""Bolt 016: the server reads a printed ticket back from the Dummy Printer.

Training contract only; the server never prints (printer-client.js does).
"""

from datetime import datetime
from unittest.mock import patch

from django.test import LiveServerTestCase, SimpleTestCase, override_settings

from devices import printer
from devices.printer import PrintedTicket, PrinterUnavailable, TicketNotFound
from dummy_orgatex.services import seed_training_scenario
from tests.helpers import post_json, set_mode

LOGGER = "devices"


class LivePrinterTestCase(LiveServerTestCase):
    def setUp(self):
        seed_training_scenario()
        self.enterContext(
            override_settings(PRINTER_BASE_URL=f"{self.live_server_url}/api")
        )

    def print_ticket(self, content="TICKET\n", batch_id="B-24187"):
        response = post_json(
            self.client, "/api/tickets", {"content": content, "batchId": batch_id}
        )
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()


class FetchTicketTests(LivePrinterTestCase):
    def test_stored_ticket_is_read_back_typed(self):
        stored = self.print_ticket("FCI DYEING\n")

        ticket = printer.fetch_ticket(stored["ticketId"])

        self.assertIsInstance(ticket, PrintedTicket)
        self.assertEqual(ticket.ticket_id, stored["ticketId"])
        self.assertEqual(ticket.content, "FCI DYEING\n")
        self.assertEqual(ticket.batch_id, "B-24187")
        self.assertEqual(ticket.printed_at, datetime.fromisoformat(stored["printedAt"]))

    def test_ticket_without_batch_has_none(self):
        stored = post_json(self.client, "/api/tickets", {"content": "X"}).json()

        self.assertIsNone(printer.fetch_ticket(stored["ticketId"]).batch_id)

    def test_unknown_ticket_raises_not_found(self):
        with self.assertLogs(LOGGER, "WARNING"), self.assertRaises(TicketNotFound):
            printer.fetch_ticket(999)

    def test_stored_ticket_stays_readable_while_printer_is_in_error(self):
        stored = self.print_ticket()
        set_mode(self.client, "printer", "error")

        self.assertEqual(printer.fetch_ticket(stored["ticketId"]).content, "TICKET\n")

    def test_unreachable_printer_is_unavailable(self):
        with (
            override_settings(PRINTER_BASE_URL="http://127.0.0.1:9/api"),
            self.assertLogs(LOGGER, "WARNING") as logs,
            self.assertRaises(PrinterUnavailable),
        ):
            printer.fetch_ticket(1)

        self.assertIn("http://127.0.0.1:9/api/tickets/1", logs.output[0])


class _FakeResponse:
    def __init__(self, body):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


class MalformedTicketTests(SimpleTestCase):
    def assert_unavailable(self, body):
        with (
            patch("devices.http.urlopen", return_value=_FakeResponse(body)),
            self.assertLogs(LOGGER, "WARNING"),
            self.assertRaises(PrinterUnavailable),
        ):
            printer.fetch_ticket(1)

    def test_missing_content_is_rejected(self):
        self.assert_unavailable(
            b'{"ticketId": 1, "batchId": null, "printedAt": "2026-11-24T03:00:00"}'
        )

    def test_wrong_batch_type_is_rejected(self):
        self.assert_unavailable(
            b'{"ticketId": 1, "content": "x", "batchId": 5, '
            b'"printedAt": "2026-11-24T03:00:00"}'
        )
