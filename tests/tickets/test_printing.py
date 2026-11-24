"""Stories 001 and 002 (bolt 016): print, reprint and printer failure.

B-24187 is completed with the prototype's actuals through the real flow; the
ticket is printed on the live Dummy Printer the way printer-client.js does it,
and the server reads it back before marking the job printed.
"""

from django.test import override_settings

from tests.helpers import post_json, set_mode
from tests.weighing.test_completion import CompletionFlowTestCase
from tickets import printing
from tickets.models import PrintJob, PrintStatus
from weighing.models import SessionState, WeighingRecord
from weighing.services import RefusalReason, WeighingRefused

LOGGER = "tickets.printing"


class PrintingTestCase(CompletionFlowTestCase):
    complete = True

    def setUp(self):
        super().setUp()
        self.enterContext(override_settings(PRINTER_BASE_URL=self.api))
        if self.complete:
            self.weigh()

    def start(self):
        with self.assertLogs(LOGGER, "INFO"):
            return printing.start_print(self.session.pk, "OP-01")

    def send_to_printer(self, job):
        """What printer-client.js does: POST /api/tickets."""
        return post_json(
            self.client,
            "/api/tickets",
            {"content": job.content, "batchId": job.batch_id},
        )

    def report(self, job, printed, ticket_id=None, reason="", level="INFO"):
        with self.assertLogs(LOGGER, level) as logs:
            result = printing.report_print(
                self.session.pk, job.pk, "OP-01", printed, ticket_id, reason
            )
        self.logs = logs.output
        return result

    def print_once(self):
        job = self.start()
        ticket = self.send_to_printer(job).json()
        return self.report(job, True, ticket["ticketId"]), ticket

    def stored_ticket(self, ticket_id):
        return self.client.get(f"/api/tickets/{ticket_id}").json()


class PrintTests(PrintingTestCase):
    def test_print_sends_the_ticket_and_is_printed(self):
        """Story 001 AC 1 + AC 2."""
        job, ticket = self.print_once()

        self.assertEqual(job.status, PrintStatus.PRINTED)
        self.assertFalse(job.is_reprint)
        self.assertEqual(job.printer_ticket_id, ticket["ticketId"])
        self.assertIsNotNone(job.printed_at)
        stored = self.stored_ticket(ticket["ticketId"])
        self.assertEqual(stored["content"], job.content)
        self.assertEqual(stored["batchId"], "B-24187")
        for text in (
            "FCI DYEING — WEIGHING TICKET",
            "BATCH   B-24187",
            "ORDER   SO-9931",
            "MACHINE JET-04",
            "SHADE   Teal 4C",
            "DATE    ",
            "OPER.   R. Karim",
            "Remazol Yellow RGB",
            "ALL WITHIN TOLERANCE",
            "*B-24187*",
        ):
            self.assertIn(text, stored["content"])
        self.assertIn("TicketPrinted", self.logs[0])

    def test_preview_shows_the_printed_content(self):
        """Story 001 AC 2: before printing the preview is what gets printed."""
        before = printing.preview(self.session.pk)
        job, _ = self.print_once()

        self.assertEqual(before.content, job.content)
        self.assertFalse(before.reprint)
        self.assertFalse(before.printed)
        after = printing.preview(self.session.pk)
        self.assertTrue(after.printed)
        self.assertEqual([j.pk for j in after.jobs], [job.pk])

    def test_ticket_lines_come_from_the_stored_records(self):
        """Story 001 AC 3: 23.980 kg is the record, not the 24.000 kg target."""
        job = self.start()

        for record in WeighingRecord.objects.filter(session=self.session):
            self.assertIn(record.component_name, job.content)
        self.assertIn("Sodium Sulphate           24.000  23.980 kg", job.content)
        self.assertIn("Soda Ash                   9.600   9.621 kg", job.content)

    def test_second_print_is_a_reprint(self):
        """Story 002 AC 1."""
        first, _ = self.print_once()

        second, _ = self.print_once()

        self.assertFalse(first.is_reprint)
        self.assertTrue(second.is_reprint)
        self.assertTrue(second.content.startswith(" " * 14 + "*** REPRINT ***\n"))
        self.assertEqual(second.content.split("\n", 1)[1], first.content)
        self.assertTrue(printing.preview(self.session.pk).reprint)


class PrinterFailureTests(PrintingTestCase):
    def test_printer_error_is_failed_and_nothing_printed(self):
        """Story 002 AC 2."""
        set_mode(self.client, "printer", "error")
        job = self.start()
        response = self.send_to_printer(job)
        self.assertEqual(response.status_code, 503)

        result = self.report(
            job, False, None, "Printer error: ticket not printed", "WARNING"
        )

        self.assertEqual(result.status, PrintStatus.FAILED)
        self.assertEqual(result.reason, "Printer error: ticket not printed")
        self.assertIsNone(result.printer_ticket_id)
        self.assertFalse(printing.preview(self.session.pk).printed)
        self.assertIn("TicketNotPrinted", self.logs[0])

    def test_restored_printer_prints_and_a_failed_attempt_is_no_reprint(self):
        """Story 002 AC 3."""
        set_mode(self.client, "printer", "error")
        failed = self.start()
        self.send_to_printer(failed)
        self.report(failed, False, None, "Printer error", "WARNING")
        set_mode(self.client, "printer", "ok")

        job, _ = self.print_once()

        self.assertEqual(job.status, PrintStatus.PRINTED)
        self.assertFalse(job.is_reprint)
        self.assertEqual(
            list(PrintJob.objects.values_list("status", flat=True)),
            ["failed", "printed"],
        )

    def test_batch_and_records_are_unchanged_by_any_print_outcome(self):
        """Story 002 AC 4."""
        self.reload()
        before = (
            self.session.state,
            self.session.completed_at,
            list(WeighingRecord.objects.order_by("pk").values()),
        )
        set_mode(self.client, "printer", "error")
        failed = self.start()
        self.report(failed, False, None, "Printer error", "WARNING")
        set_mode(self.client, "printer", "ok")
        self.print_once()
        self.print_once()

        session = self.reload()
        after = (
            session.state,
            session.completed_at,
            list(WeighingRecord.objects.order_by("pk").values()),
        )
        self.assertEqual(after, before)
        self.assertEqual(session.state, SessionState.COMPLETE)

    def test_a_printed_report_without_a_stored_ticket_is_failed(self):
        """The browser cannot mark a ticket printed (bolt 016 Decision 1)."""
        job = self.start()

        with self.assertLogs("devices", "WARNING"):
            result = self.report(job, True, 999, level="WARNING")

        self.assertEqual(result.status, PrintStatus.FAILED)
        self.assertEqual(result.reason, printing.NOT_STORED)

    def test_another_tickets_id_does_not_confirm(self):
        job = self.start()
        other = post_json(
            self.client, "/api/tickets", {"content": "OTHER", "batchId": "B-24187"}
        ).json()

        result = self.report(job, True, other["ticketId"], level="WARNING")

        self.assertEqual(result.status, PrintStatus.FAILED)

    def test_one_printer_ticket_confirms_one_job_only(self):
        first, ticket = self.print_once()
        second = self.start()
        # A copy of the reprint's text is not sent; the old ticket is reused.
        result = self.report(second, True, ticket["ticketId"], level="WARNING")

        self.assertEqual(first.status, PrintStatus.PRINTED)
        self.assertEqual(result.status, PrintStatus.FAILED)

    def test_unreadable_printer_is_failed(self):
        job = self.start()
        ticket = self.send_to_printer(job).json()

        with (
            override_settings(PRINTER_BASE_URL="http://127.0.0.1:9/api"),
            self.assertLogs("devices", "WARNING"),
        ):
            result = self.report(job, True, ticket["ticketId"], level="WARNING")

        self.assertEqual(result.status, PrintStatus.FAILED)
        self.assertEqual(result.reason, printing.PRINTER_UNAVAILABLE)

    def test_a_finished_job_is_final(self):
        job, ticket = self.print_once()

        again = printing.report_print(
            self.session.pk, job.pk, "OP-01", False, None, "late error"
        )

        self.assertEqual(again.status, PrintStatus.PRINTED)
        self.assertEqual(again.printer_ticket_id, ticket["ticketId"])

    def test_reason_is_trimmed(self):
        job = self.start()

        result = self.report(job, False, None, "  jam \n" + "x" * 300, "WARNING")

        self.assertTrue(result.reason.startswith("jam x"))
        self.assertEqual(len(result.reason), printing.MAX_REASON)


class RefusalTests(PrintingTestCase):
    complete = False

    def assert_refused(self, reason, call, *args):
        with self.assertRaises(WeighingRefused) as refused:
            call(*args)
        self.assertEqual(refused.exception.reason, reason)

    def test_no_ticket_before_the_batch_is_complete(self):
        self.weigh(4)

        for call in (printing.preview, printing.start_print):
            with self.subTest(call=call.__name__):
                args = (
                    (self.session.pk,)
                    if call is printing.preview
                    else (
                        self.session.pk,
                        "OP-01",
                    )
                )
                self.assert_refused(RefusalReason.BATCH_NOT_COMPLETE, call, *args)
        self.assertFalse(PrintJob.objects.exists())

    def test_print_needs_an_operator(self):
        self.weigh()

        with self.assertLogs("weighing.services"):
            self.assert_refused(
                RefusalReason.OPERATOR_REQUIRED,
                printing.start_print,
                self.session.pk,
                None,
            )

    def test_a_job_of_another_session_is_not_found(self):
        self.weigh()
        job = self.start()

        self.assert_refused(
            RefusalReason.SESSION_NOT_FOUND,
            printing.report_print,
            9999,
            job.pk,
            "OP-01",
            False,
            None,
            "",
        )
        with self.assertLogs("weighing.progression"):
            self.assert_refused(
                RefusalReason.PRINT_JOB_NOT_FOUND,
                printing.report_print,
                self.session.pk,
                job.pk + 1,
                "OP-01",
                False,
                None,
                "",
            )
