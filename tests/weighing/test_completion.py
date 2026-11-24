"""Story 009-complete-batch (bolt 015, ADR-013): completion and its summary.

Domain rules are tested pure; completion runs through the real confirmation
against the live Dummy Scale and Scanner (training contracts).
"""

from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone

from orgatex import write_back
from orgatex.models import WriteBack, WriteBackStatus
from tests.weighing.flow import BLUE, SODA, LiveFlowTestCase
from weighing import completion, confirmation, progression
from weighing.models import ComponentAttempt, SessionState, WeighingRecord
from weighing.services import RefusalReason, WeighingRefused

LOGGER = "weighing.completion"
# The prototype's actuals (story 009 AC 2).
PROTOTYPE = {1: "1241.5", 2: "385.4", 3: "94.2", 4: "23.980", 5: "9.621"}


def record(weight, unit, result="within"):
    return SimpleNamespace(actual_weight=Decimal(weight), unit=unit, result=result)


class TotalDispensedTests(SimpleTestCase):
    def test_prototype_actuals_total_35_322_kg(self):
        """Story 009 AC 2."""
        records = [
            record("1241.5", "g"),
            record("385.4", "g"),
            record("94.2", "g"),
            record("23.980", "kg"),
            record("9.621", "kg"),
        ]

        total = completion.total_dispensed_kg(records)

        self.assertEqual(total, Decimal("35.322"))
        self.assertIsInstance(total, Decimal)
        self.assertEqual(f"{total:f}", "35.322")

    def test_grams_and_kilograms_are_summed_in_kg(self):
        total = completion.total_dispensed_kg([record("500.0", "g"), record("1", "kg")])

        self.assertEqual(f"{total:f}", "1.500")

    def test_total_rounds_half_up_to_one_gram(self):
        self.assertEqual(
            completion.total_dispensed_kg([record("0.5", "g")]), Decimal("0.001")
        )
        self.assertEqual(
            completion.total_dispensed_kg([record("0.4", "g")]), Decimal("0.000")
        )

    def test_no_records_total_zero(self):
        self.assertEqual(f"{completion.total_dispensed_kg([]):f}", "0.000")


class ElapsedTextTests(SimpleTestCase):
    def test_prototype_format(self):
        cases = {
            401: "6 min 41 s",
            59: "0 min 59 s",
            0: "0 min 0 s",
            3600: "60 min 0 s",
        }
        for seconds, text in cases.items():
            with self.subTest(seconds=seconds):
                self.assertEqual(completion.elapsed_text(seconds), text)


class SummaryTextTests(SimpleTestCase):
    def summary(self, all_within):
        now = timezone.now()
        return completion.BatchSummary(
            session=None,
            weighed=5,
            total=5,
            all_within=all_within,
            total_dispensed_kg=Decimal("35.322"),
            elapsed_seconds=401,
            operator=None,
            started_at=now - timedelta(seconds=401),
            completed_at=now,
        )

    def test_texts(self):
        summary = self.summary(True)

        self.assertEqual(summary.components_text, "5 of 5")
        self.assertEqual(summary.all_within_text, "YES")
        self.assertEqual(summary.total_text, "35.322 kg")
        self.assertEqual(summary.elapsed_text, "6 min 41 s")

    def test_not_all_within_is_no(self):
        self.assertEqual(self.summary(False).all_within_text, "NO")


class CompletionFlowTestCase(LiveFlowTestCase):
    def confirm(self, sequence, weight=None):
        self.verify(sequence)
        self.set_weight(sequence, weight or PROTOTYPE[sequence])
        return confirmation.confirm(self.session.pk, sequence, "OP-01")

    def weigh(self, count=5):
        progression.activate(self.session.pk, BLUE, "OP-01")
        for sequence in range(1, count + 1):
            result = self.confirm(sequence)
        return result

    def reload(self):
        self.session.refresh_from_db()
        return self.session


class CompletionTests(CompletionFlowTestCase):
    def test_fifth_confirmation_completes_the_batch(self):
        """Story 009 AC 1: complete when the last confirmation is saved."""
        with self.assertLogs(LOGGER, "INFO") as logs:
            record, state = self.weigh()

        session = self.reload()
        self.assertEqual(session.state, SessionState.COMPLETE)
        self.assertEqual(session.completed_at, record.recorded_at)
        self.assertEqual(state.session.state, SessionState.COMPLETE)
        self.assertEqual(state.text, "5 of 5 components weighed")
        self.assertIsNone(state.active_attempt)
        self.assertFalse(
            ComponentAttempt.objects.filter(ended_at__isnull=True).exists()
        )
        self.assertIn("BatchCompleted", logs.output[0])
        self.assertIn("totalDispensedKg=35.322", logs.output[0])
        self.assertIn("WriteBackTriggered", logs.output[1])

    def test_summary_of_the_prototype_actuals(self):
        """Story 009 AC 1 + AC 2."""
        self.weigh()

        summary = completion.summary(self.session.pk)

        self.assertEqual(summary.components_text, "5 of 5")
        self.assertTrue(summary.all_within)
        self.assertEqual(summary.total_dispensed_kg, Decimal("35.322"))
        self.assertEqual(summary.operator.display, "R. Karim · Shift A")
        session = self.reload()
        self.assertEqual(
            summary.elapsed_seconds,
            int((session.completed_at - session.started_at).total_seconds()),
        )

    def test_completion_triggers_the_write_back(self):
        """Story 009 AC 4: a pending write-back, nothing posted yet."""
        self.weigh()

        write_back = WriteBack.objects.get(session_id=self.session.pk)
        self.assertEqual(write_back.status, WriteBackStatus.PENDING)
        self.assertEqual(write_back.attempts, 0)
        self.assertEqual(write_back.batch_id, "B-24187")
        self.assertEqual(write_back.idempotency_key, f"WMS-B-24187-S{self.session.pk}")
        self.assertEqual(write_back.operator_id, "OP-01")

    def test_four_of_five_is_not_complete(self):
        """Story 009 AC 3."""
        self.weigh(4)

        session = self.reload()
        self.assertEqual(session.state, SessionState.IN_PROGRESS)
        self.assertIsNone(session.completed_at)
        self.assertFalse(WriteBack.objects.exists())
        with self.assertRaises(WeighingRefused) as refused:
            completion.summary(self.session.pk)
        self.assertEqual(refused.exception.reason, RefusalReason.BATCH_NOT_COMPLETE)

    def test_completion_request_at_four_of_five_is_refused(self):
        """Story 009 AC 3, service level."""
        self.weigh(4)

        with self.assertRaises(WeighingRefused) as refused:
            completion.complete(self.reload(), timezone.now(), "OP-01")

        self.assertEqual(refused.exception.reason, RefusalReason.BATCH_NOT_COMPLETE)
        self.assertEqual(self.reload().state, SessionState.IN_PROGRESS)

    def test_a_complete_session_is_not_completed_again(self):
        self.weigh()

        with self.assertRaises(WeighingRefused) as refused:
            completion.complete(self.reload(), timezone.now(), "OP-01")

        self.assertEqual(refused.exception.reason, RefusalReason.SESSION_NOT_OPEN)

    def test_a_complete_session_refuses_weighing_actions(self):
        self.weigh()

        for action in (
            progression.activate,
            progression.tare,
            progression.quit_attempt,
            confirmation.confirm,
        ):
            with self.subTest(action=action.__name__):
                with self.assertRaises(WeighingRefused) as refused:
                    action(self.session.pk, SODA, "OP-01")
                self.assertEqual(
                    refused.exception.reason, RefusalReason.SESSION_NOT_OPEN
                )
        self.assertEqual(WeighingRecord.objects.count(), 5)

    def test_a_failed_completion_rolls_back_the_fifth_record(self):
        """ADR-013 risk: one transaction for record, completion and write-back."""
        self.weigh(4)
        self.verify(SODA)
        self.set_weight(SODA, PROTOTYPE[SODA])

        with (
            patch("orgatex.write_back.open_write_back", side_effect=RuntimeError("db")),
            self.assertRaises(RuntimeError),
        ):
            confirmation.confirm(self.session.pk, SODA, "OP-01")

        self.assertEqual(WeighingRecord.objects.count(), 4)
        self.assertEqual(self.reload().state, SessionState.IN_PROGRESS)
        self.assertFalse(WriteBack.objects.exists())
        # The operator confirms again and the batch completes.
        with self.assertLogs(LOGGER, "INFO"):
            confirmation.confirm(self.session.pk, SODA, "OP-01")
        self.assertEqual(self.reload().state, SessionState.COMPLETE)

    def test_open_write_back_is_idempotent(self):
        self.weigh()

        again = write_back.open_write_back("B-24187", self.session.pk, "OP-02")

        self.assertEqual(again.attempts, 0)
        self.assertEqual(again.operator_id, "OP-01")
        self.assertEqual(WriteBack.objects.count(), 1)
