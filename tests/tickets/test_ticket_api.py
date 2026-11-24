"""Bolt 016 over HTTP: ``/station/api/sessions/<id>/ticket[/prints[/<job>/result]]``."""

from django.test import Client, override_settings

from tests.helpers import post_json, put_json, set_mode
from tests.weighing.test_completion import CompletionFlowTestCase
from tests.weighing.test_confirmation_api import ErrorAssertions

JOB_KEYS = {
    "jobId",
    "status",
    "reprint",
    "ticketId",
    "printedAt",
    "reason",
    "operatorId",
    "createdAt",
}


class TicketApiTestCase(ErrorAssertions, CompletionFlowTestCase):
    def setUp(self):
        super().setUp()
        self.enterContext(override_settings(PRINTER_BASE_URL=self.api))
        put_json(self.client, "/station/api/operator", {"operatorId": "OP-01"})
        self.url = f"/station/api/sessions/{self.session.pk}/ticket"

    def start(self, client=None):
        return post_json(client or self.client, self.url + "/prints", {})

    def report(self, job_id, body, client=None):
        return post_json(
            client or self.client, f"{self.url}/prints/{job_id}/result", body
        )

    def print_via_api(self):
        """The browser's flow: start → printer → report."""
        started = self.start().json()
        ticket = post_json(
            self.client,
            "/api/tickets",
            {"content": started["content"], "batchId": started["batchId"]},
        )
        body = (
            {"printed": True, "ticketId": ticket.json()["ticketId"]}
            if ticket.status_code == 201
            else {"printed": False, "reason": ticket.json()["error"]["message"]}
        )
        return started, self.report(started["job"]["jobId"], body)


class TicketApiTests(TicketApiTestCase):
    def setUp(self):
        super().setUp()
        self.weigh()

    def test_preview_before_any_print(self):
        response = Client().get(self.url)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["batchId"], "B-24187")
        self.assertFalse(body["reprint"])
        self.assertFalse(body["printed"])
        self.assertEqual(body["jobs"], [])
        self.assertIn("FCI DYEING — WEIGHING TICKET", body["content"])

    def test_start_returns_the_pending_job_and_the_content(self):
        response = self.start()

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["batchId"], "B-24187")
        self.assertEqual(set(body["job"]), JOB_KEYS)
        self.assertEqual(body["job"]["status"], "pending")
        self.assertFalse(body["job"]["reprint"])
        self.assertEqual(body["job"]["operatorId"], "OP-01")
        self.assertEqual(body["content"], Client().get(self.url).json()["content"])

    def test_print_then_reprint(self):
        """Story 001 AC 1-2 and story 002 AC 1 over HTTP."""
        started, response = self.print_via_api()

        self.assertEqual(response.status_code, 200)
        job = response.json()["job"]
        self.assertEqual(job["status"], "printed")
        self.assertIsNotNone(job["ticketId"])
        stored = self.client.get(f"/api/tickets/{job['ticketId']}").json()
        self.assertEqual(stored["content"], started["content"])

        preview = Client().get(self.url).json()
        self.assertTrue(preview["printed"])
        self.assertTrue(preview["reprint"])
        self.assertTrue(preview["content"].lstrip().startswith("*** REPRINT ***"))

        _, again = self.print_via_api()
        self.assertTrue(again.json()["job"]["reprint"])

    def test_printer_error_then_restored(self):
        """Story 002 AC 2 + AC 3 over HTTP."""
        set_mode(self.client, "printer", "error")

        _, failed = self.print_via_api()
        set_mode(self.client, "printer", "ok")
        _, printed = self.print_via_api()

        self.assertEqual(failed.json()["job"]["status"], "failed")
        self.assertEqual(
            failed.json()["job"]["reason"], "Printer error: ticket not printed"
        )
        self.assertIsNone(failed.json()["job"]["ticketId"])
        self.assertEqual(printed.json()["job"]["status"], "printed")
        self.assertFalse(printed.json()["job"]["reprint"])
        jobs = Client().get(self.url).json()["jobs"]
        self.assertEqual([j["status"] for j in jobs], ["failed", "printed"])

    def test_without_operator_print_and_report_are_refused(self):
        job_id = self.start().json()["job"]["jobId"]
        anonymous = Client()

        self.assert_error(self.start(anonymous), 403, "OPERATOR_REQUIRED")
        self.assert_error(
            self.report(job_id, {"printed": False}, anonymous), 403, "OPERATOR_REQUIRED"
        )

    def test_report_body_is_validated(self):
        job_id = self.start().json()["job"]["jobId"]
        for body in (
            {},
            {"printed": "yes"},
            {"printed": True, "ticketId": "7"},
            {"printed": True, "ticketId": 0},
            {"printed": True, "ticketId": True},
            {"printed": False, "reason": 5},
            "[]",
        ):
            with self.subTest(body=body):
                self.assert_error(self.report(job_id, body), 400, "VALIDATION_ERROR")

    def test_unknown_job_is_404(self):
        self.assert_error(
            self.report(9999, {"printed": False}), 404, "PRINT_JOB_NOT_FOUND"
        )

    def test_start_without_csrf_token_is_rejected(self):
        csrf_client = Client(enforce_csrf_checks=True)
        put_json(csrf_client, "/station/api/operator", {"operatorId": "OP-01"})

        self.assertEqual(self.start(csrf_client).status_code, 403)

    def test_methods(self):
        self.assertEqual(self.client.post(self.url).status_code, 405)
        self.assertEqual(self.client.get(self.url + "/prints").status_code, 405)


class TicketBeforeCompletionTests(TicketApiTestCase):
    def test_no_ticket_at_four_of_five(self):
        self.weigh(4)

        self.assert_error(Client().get(self.url), 409, "BATCH_NOT_COMPLETE")
        self.assert_error(self.start(), 409, "BATCH_NOT_COMPLETE")

    def test_unknown_session_is_404(self):
        url = "/station/api/sessions/9999/ticket"

        self.assert_error(Client().get(url), 404, "SESSION_NOT_FOUND")
        self.assert_error(
            post_json(self.client, url + "/prints", {}), 404, "SESSION_NOT_FOUND"
        )
