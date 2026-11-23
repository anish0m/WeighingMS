"""Bolt 014: write-back key, body and status, decided by reading OrgaTEX.

Stories 002-post-consumption-idempotently and 003-write-back-failure-and-retry
against the live Dummy OrgaTEX (training contract, not the real interface).
"""

from datetime import datetime
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from orgatex import write_back
from orgatex.models import WriteBack, WriteBackStatus
from tests.helpers import post_json, set_mode
from tests.orgatex.test_adapter import LiveOrgatexTestCase

LOGGER = "orgatex.write_back"
LINES = [
    write_back.Line("DYE-1180", Decimal("1241.5"), "g"),
    write_back.Line("DYE-2204", Decimal("385.4"), "g"),
    write_back.Line("DYE-4471", Decimal("94.2"), "g"),
    write_back.Line("AUX-0101", Decimal("24.048"), "kg"),
    write_back.Line("AUX-0107", Decimal("9.612"), "kg"),
]


class KeyAndBodyTests(SimpleTestCase):
    def test_key_is_derived_from_batch_and_session(self):
        self.assertEqual(write_back.idempotency_key("B-24187", 7), "WMS-B-24187-S7")

    def test_body_has_every_component_as_decimal_strings(self):
        body = write_back.consumption_body("WMS-B-24187-S7", LINES)

        self.assertEqual(body["idempotencyKey"], "WMS-B-24187-S7")
        self.assertEqual(
            body["components"],
            [
                {"code": "DYE-1180", "actualQty": "1241.5", "unit": "g"},
                {"code": "DYE-2204", "actualQty": "385.4", "unit": "g"},
                {"code": "DYE-4471", "actualQty": "94.2", "unit": "g"},
                {"code": "AUX-0101", "actualQty": "24.048", "unit": "kg"},
                {"code": "AUX-0107", "actualQty": "9.612", "unit": "kg"},
            ],
        )

    def test_quantities_never_use_an_exponent(self):
        line = write_back.Line("AUX-0101", Decimal("1E+1"), "kg")

        body = write_back.consumption_body("k", [line])

        self.assertEqual(body["components"][0]["actualQty"], "10")


class StartTests(TestCase):
    def start(self, operator_id="OP-01"):
        with self.assertLogs(LOGGER, "INFO"):
            return write_back.start("B-24187", 7, operator_id)

    def test_first_start_is_pending_with_one_attempt(self):
        record = self.start()

        self.assertEqual(record.status, WriteBackStatus.PENDING)
        self.assertEqual(record.idempotency_key, "WMS-B-24187-S7")
        self.assertEqual(record.attempts, 1)
        self.assertEqual(record.operator_id, "OP-01")
        self.assertIsNone(record.confirmed_at)

    def test_retry_reuses_the_row_and_the_key(self):
        first = self.start()
        second = self.start("OP-02")

        self.assertEqual(second.pk, first.pk)
        self.assertEqual(second.idempotency_key, first.idempotency_key)
        self.assertEqual(second.attempts, 2)
        self.assertEqual(second.operator_id, "OP-02")
        self.assertEqual(WriteBack.objects.count(), 1)

    def test_retry_after_not_written_is_pending_again(self):
        record = self.start()
        WriteBack.objects.filter(pk=record.pk).update(
            status=WriteBackStatus.NOT_WRITTEN, last_error="OrgaTEX unavailable"
        )

        record = self.start()

        self.assertEqual(record.status, WriteBackStatus.PENDING)
        self.assertEqual(record.last_error, "")

    def test_start_never_downgrades_a_confirmed_write_back(self):
        record = self.start()
        accepted = timezone.now()
        WriteBack.objects.filter(pk=record.pk).update(
            status=WriteBackStatus.CONFIRMED, confirmed_at=accepted
        )

        record = self.start()

        self.assertEqual(record.status, WriteBackStatus.CONFIRMED)
        self.assertEqual(record.confirmed_at, accepted)

    def test_confirmed_at_is_only_allowed_on_a_confirmed_row(self):
        record = self.start()

        with self.assertRaises(IntegrityError), transaction.atomic():
            WriteBack.objects.filter(pk=record.pk).update(confirmed_at=timezone.now())


class VerifyTests(LiveOrgatexTestCase):
    def setUp(self):
        super().setUp()
        with self.assertLogs(LOGGER, "INFO"):
            self.record = write_back.start("B-24187", 7, "OP-01")
        self.body = write_back.consumption_body(self.record.idempotency_key, LINES)

    def post_to_dummy(self):
        return post_json(self.client, "/api/batches/B-24187/consumption", self.body)

    def consumptions(self):
        return self.client.get("/api/batches/B-24187/consumption").json()[
            "consumptions"
        ]

    def verify(self, posted, reason="", level="INFO"):
        with self.assertLogs(LOGGER, level) as logs:
            record = write_back.verify(self.record, posted, reason)
        self.logs = logs.output
        return record

    def test_accepted_post_is_confirmed_with_orgatex_time(self):
        """Story 002 AC 1 + AC 3."""
        accepted = self.post_to_dummy().json()["acceptedAt"]

        record = self.verify(posted=True)

        self.assertEqual(record.status, WriteBackStatus.CONFIRMED)
        self.assertEqual(record.confirmed_at, datetime.fromisoformat(accepted))
        self.assertEqual(record.last_error, "")
        self.assertEqual(len(self.consumptions()), 1)
        self.assertIn("WriteBackConfirmed", self.logs[0])

    def test_repeat_trigger_keeps_one_consumption(self):
        """Story 002 AC 2: same key, the Dummy answers duplicate."""
        self.assertEqual(self.post_to_dummy().status_code, 201)
        self.verify(posted=True)
        with self.assertLogs(LOGGER, "INFO"):
            again = write_back.start("B-24187", 7, "OP-01")

        response = self.post_to_dummy()

        self.assertEqual(again.idempotency_key, self.record.idempotency_key)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["duplicate"])
        self.assertEqual(len(self.consumptions()), 1)

    def test_unavailable_orgatex_is_not_written_with_the_reason(self):
        """Story 003 AC 1: never CONFIRMED."""
        set_mode(self.client, "orgatex", "unavailable")

        with self.assertLogs("orgatex.adapter", "WARNING"):
            record = self.verify(False, "OrgaTEX unavailable", "WARNING")

        self.assertEqual(record.status, WriteBackStatus.NOT_WRITTEN)
        self.assertEqual(record.last_error, "OrgaTEX unavailable")
        self.assertIsNone(record.confirmed_at)
        self.assertTrue(any("WriteBackNotWritten" in line for line in self.logs))

    def test_retry_when_orgatex_is_back_confirms(self):
        """Story 003 AC 2: same key, CONFIRMED with time, two attempts."""
        set_mode(self.client, "orgatex", "unavailable")
        with self.assertLogs("orgatex.adapter", "WARNING"):
            self.verify(False, "OrgaTEX unavailable", "WARNING")
        set_mode(self.client, "orgatex", "ok")
        with self.assertLogs(LOGGER, "INFO"):
            self.record = write_back.start("B-24187", 7, "OP-01")
        self.post_to_dummy()

        record = self.verify(posted=True)

        self.assertEqual(record.status, WriteBackStatus.CONFIRMED)
        self.assertEqual(record.idempotency_key, "WMS-B-24187-S7")
        self.assertEqual(record.attempts, 2)
        self.assertIsNotNone(record.confirmed_at)

    def test_timeout_after_the_dummy_stored_the_post_is_confirmed(self):
        """Story 003 AC 3: the browser reports a failure, OrgaTEX holds it."""
        self.post_to_dummy()

        record = self.verify(False, "OrgaTEX unavailable")
        self.post_to_dummy()

        self.assertEqual(record.status, WriteBackStatus.CONFIRMED)
        self.assertEqual(len(self.consumptions()), 1)

    def test_a_posted_report_that_orgatex_does_not_hold_is_not_written(self):
        """NFR-7: a browser claim alone never gives CONFIRMED."""
        record = self.verify(posted=True, level="WARNING")

        self.assertEqual(record.status, WriteBackStatus.NOT_WRITTEN)
        self.assertEqual(record.last_error, write_back.NOT_STORED)

    def test_another_keys_consumption_does_not_confirm(self):
        self.body["idempotencyKey"] = "WMS-B-24187-S6"
        self.post_to_dummy()

        record = self.verify(posted=True, level="WARNING")

        self.assertEqual(record.status, WriteBackStatus.NOT_WRITTEN)

    def test_unreachable_orgatex_is_not_written(self):
        with (
            override_settings(ORGATEX_BASE_URL="http://127.0.0.1:9/api"),
            self.assertLogs("orgatex.adapter", "WARNING"),
        ):
            record = self.verify(posted=True, level="WARNING")

        self.assertEqual(record.status, WriteBackStatus.NOT_WRITTEN)
        self.assertEqual(record.last_error, write_back.UNAVAILABLE)
        self.assertTrue(any("WriteBackCheckFailed" in line for line in self.logs))

    def test_browser_reason_is_trimmed(self):
        record = self.verify(False, "  OrgaTEX\n  refused " + "x" * 300, "WARNING")

        self.assertTrue(record.last_error.startswith("OrgaTEX refused x"))
        self.assertEqual(len(record.last_error), write_back.MAX_REASON)

    def test_a_confirmed_write_back_is_never_downgraded(self):
        self.post_to_dummy()
        confirmed = self.verify(posted=True)
        set_mode(self.client, "orgatex", "unavailable")

        record = write_back.verify(confirmed, False, "OrgaTEX unavailable")

        self.assertEqual(record.status, WriteBackStatus.CONFIRMED)
        self.assertEqual(record.confirmed_at, confirmed.confirmed_at)
