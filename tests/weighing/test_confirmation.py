"""Stories 006-confirm-weighing, 008-progress-components and 003 AC 4.

``weighing.confirmation.confirm`` against the live Dummy Scale and Scanner
(training contracts). The server re-reads the scale and evaluates it
(ADR-008 / ADR-009); every refusal stores nothing.
"""

from decimal import Decimal

from django.db.models import ProtectedError
from django.test import override_settings

from tests.weighing import factories
from tests.weighing.flow import (
    BLUE,
    SODIUM,
    TEAL,
    UNREACHABLE,
    YELLOW,
    LiveFlowTestCase,
)
from weighing import confirmation, progression
from weighing.models import (
    AttemptEnd,
    ComponentAttempt,
    Operator,
    WeighingRecord,
    WeighingRecordImmutable,
    WeighingResult,
)
from weighing.services import RefusalReason, WeighingRefused

LOGGER = "weighing.confirmation"


class ConfirmTestCase(LiveFlowTestCase):
    def activate(self, sequence):
        return progression.activate(self.session.pk, sequence, "OP-01")

    def confirm(self, sequence, operator_id="OP-01"):
        return confirmation.confirm(self.session.pk, sequence, operator_id)

    def ready(self, sequence, weight=None):
        """Active, tared, verified, with ``weight`` on the scale."""
        self.activate(sequence)
        self.verify(sequence)
        self.set_weight(sequence, weight or TEAL[sequence][3])

    def assert_refused(self, reason, sequence=YELLOW, operator_id="OP-01"):
        attempts = list(
            ComponentAttempt.objects.values_list("pk", "ended_at", "tared_at")
        )
        with self.assertRaises(WeighingRefused) as refused:
            self.confirm(sequence, operator_id)
        self.assertEqual(refused.exception.reason, reason)
        self.assertFalse(WeighingRecord.objects.exists())
        self.assertEqual(
            list(ComponentAttempt.objects.values_list("pk", "ended_at", "tared_at")),
            attempts,
        )
        return refused.exception


class ConfirmRecordTests(ConfirmTestCase):
    def test_the_record_has_every_traceability_field(self):
        """Story 006 AC 1 (FR-13c) and story 003 AC 4 (tare stored)."""
        self.ready(YELLOW, "94.2")

        with self.assertLogs(LOGGER, "INFO") as logs:
            record, _ = self.confirm(YELLOW)

        stored = WeighingRecord.objects.get()
        self.assertEqual(stored.pk, record.pk)
        self.assertEqual(
            {
                "batch": stored.batch_id,
                "sequence": stored.component_sequence,
                "code": stored.component_code,
                "name": stored.component_name,
                "actual": stored.actual_weight,
                "unit": stored.unit,
                "lot": stored.lot,
                "container": stored.container,
                "tare": stored.tare,
                "scale": stored.scale_id,
                "target": stored.target,
                "min": stored.tolerance_min,
                "max": stored.tolerance_max,
                "result": stored.result,
                "operator": stored.operator.operator_id,
            },
            {
                "batch": "B-24187",
                "sequence": 3,
                "code": "DYE-4471",
                "name": "Remazol Yellow RGB",
                "actual": Decimal("94.2"),
                "unit": "g",
                "lot": "2026-0387",
                "container": "C-12",
                "tare": Decimal(214),
                "scale": "scale-3kg",
                "target": Decimal("94.0"),
                "min": Decimal("93.5"),
                "max": Decimal("94.5"),
                "result": WeighingResult.WITHIN,
                "operator": "OP-01",
            },
        )
        self.assertEqual(str(stored.recorded_at.tzinfo), "UTC")
        self.assertTrue(any("WeighingConfirmed" in line for line in logs.output))

    def test_the_attempt_ends_confirmed_with_its_record(self):
        self.ready(YELLOW)

        record, _ = self.confirm(YELLOW)

        self.assertEqual(record.attempt.end_reason, AttemptEnd.CONFIRMED)
        self.assertEqual(record.attempt.component_sequence, YELLOW)

    def test_the_recorded_weight_is_the_evaluated_value(self):
        """ADR-009: 94.24 g on the scale is shown, judged and recorded as 94.2 g."""
        self.ready(YELLOW, "94.24")

        record, _ = self.confirm(YELLOW)

        self.assertEqual(record.actual_weight, Decimal("94.2"))

    def test_the_tolerance_band_ends_are_accepted(self):
        """Story 005 AC 1 at confirm: 93.5 and 94.5 g are within."""
        for weight in ("93.5", "94.5"):
            with self.subTest(weight=weight):
                session = factories.session(
                    factories.teal_selection(batch_id=f"B-{weight}")
                )
                progression.activate(session.pk, YELLOW, "OP-01")
                self.verify(YELLOW, session=session)
                self.set_weight(YELLOW, weight)

                record, _ = confirmation.confirm(session.pk, YELLOW, "OP-01")

                self.assertEqual(record.actual_weight, Decimal(weight))

    def test_the_record_names_the_operator_who_confirmed(self):
        """Model Decision 6: the station's current operator at confirm."""
        Operator.objects.create(operator_id="OP-02", name="S. Akter", shift="B")
        self.ready(YELLOW)

        record, _ = self.confirm(YELLOW, operator_id="OP-02")

        self.assertEqual(record.operator.operator_id, "OP-02")
        self.assertEqual(self.session.operator.operator_id, "OP-01")

    def test_the_record_uses_the_attempts_scale(self):
        self.ready(YELLOW)

        with override_settings(WEIGHING_SCALE_THRESHOLD_KG=Decimal("0.05")):
            record, _ = self.confirm(YELLOW)

        self.assertEqual(record.scale_id, "scale-3kg")

    def test_a_failed_tare_of_the_next_component_keeps_the_record(self):
        """ADR-011: the next tare runs after the commit and never undoes it."""
        self.ready(5)
        self.scale_mode("scale-3kg", "disconnected")

        with self.assertLogs("weighing.progression", "WARNING"):
            record, state = self.confirm(5)

        self.assertTrue(WeighingRecord.objects.filter(pk=record.pk).exists())
        self.assertEqual(state.active_attempt.component_sequence, BLUE)
        self.assertFalse(state.active_attempt.is_tared)


class ConfirmRefusalTests(ConfirmTestCase):
    """Story 006 AC 2: any precondition not met → refused, nothing saved."""

    def test_93_4_and_94_6_are_refused_out_of_tolerance(self):
        """Story 005 AC 1 / FR-13b: the server refuses 93.4 g and 94.6 g at confirm."""
        self.ready(YELLOW, "93.4")
        with self.assertLogs(LOGGER, "INFO") as logs:
            refused = self.assert_refused(RefusalReason.OUT_OF_TOLERANCE)
        self.assertEqual(refused.detail, {"net": "93.4", "unit": "g", "zone": "near"})
        self.assertIn("ConfirmationRefused", logs.output[-1])

        self.set_weight(YELLOW, "94.6")
        with self.assertLogs(LOGGER, "INFO"):
            refused = self.assert_refused(RefusalReason.OUT_OF_TOLERANCE)
        self.assertEqual(refused.detail["zone"], "over")

    def test_untared_is_refused(self):
        self.ready(YELLOW)
        progression.quit_attempt(self.session.pk, YELLOW, "OP-01")

        with self.assertLogs(LOGGER, "INFO"):
            self.assert_refused(RefusalReason.TARE_REQUIRED)

    def test_unverified_is_refused(self):
        self.activate(YELLOW)
        self.set_weight(YELLOW, "94.0")

        with self.assertLogs(LOGGER, "INFO"):
            self.assert_refused(RefusalReason.IDENTITY_NOT_VERIFIED)

    def test_wrong_dyestuff_is_refused(self):
        self.activate(YELLOW)
        with self.assertLogs("weighing.identity", "WARNING"):
            self.verify(YELLOW, code="DYE-2204")
        self.set_weight(YELLOW, "94.0")

        with self.assertLogs(LOGGER, "INFO"):
            self.assert_refused(RefusalReason.WRONG_DYESTUFF)

    def test_missing_lot_is_refused(self):
        """Story 005 (bolt 008) AC 2, end to end."""
        self.session.state = "complete"
        self.session.save()
        self.session = factories.session(
            factories.teal_selection({YELLOW: {"lot": ""}})
        )
        self.ready(YELLOW)

        with self.assertLogs(LOGGER, "INFO"):
            self.assert_refused(RefusalReason.LOT_MISSING)

    def test_disconnected_scale_is_refused(self):
        """FR-20a: the server's own re-read fails."""
        self.ready(YELLOW)
        self.scale_mode("scale-3kg", "disconnected")

        with self.assertLogs(LOGGER, "INFO"):
            self.assert_refused(RefusalReason.SCALE_DISCONNECTED)

    def test_unreachable_scale_is_refused(self):
        self.ready(YELLOW)

        with (
            override_settings(SCALE_BASE_URL=UNREACHABLE),
            self.assertLogs(LOGGER, "INFO"),
            self.assertLogs("devices", "WARNING"),
        ):
            self.assert_refused(RefusalReason.SCALE_UNAVAILABLE)

    def test_no_operator_is_refused_first(self):
        self.ready(YELLOW)

        with self.assertLogs("weighing.services", "INFO"):
            self.assert_refused(RefusalReason.OPERATOR_REQUIRED, operator_id=None)

    def test_another_component_active_is_refused(self):
        self.ready(YELLOW)

        with self.assertLogs(LOGGER, "INFO"):
            self.assert_refused(RefusalReason.COMPONENT_NOT_ACTIVE, sequence=SODIUM)

    def test_no_active_component_is_refused(self):
        with self.assertLogs(LOGGER, "INFO"):
            self.assert_refused(RefusalReason.NO_ACTIVE_COMPONENT)

    def test_a_closed_session_is_refused(self):
        self.ready(YELLOW)
        self.session.state = "complete"
        self.session.save()

        with self.assertLogs(LOGGER, "INFO"):
            self.assert_refused(RefusalReason.SESSION_NOT_OPEN)

    def test_confirming_twice_records_once(self):
        self.ready(YELLOW)
        self.confirm(YELLOW)

        with self.assertRaises(WeighingRefused) as refused, self.assertLogs(LOGGER):
            self.confirm(YELLOW)

        self.assertEqual(refused.exception.reason, RefusalReason.COMPONENT_DONE)
        self.assertEqual(WeighingRecord.objects.count(), 1)


class RecordImmutabilityTests(ConfirmTestCase):
    """Story 006 AC 3 (NFR-12)."""

    def test_a_record_cannot_be_changed_or_deleted(self):
        self.ready(YELLOW)
        record, _ = self.confirm(YELLOW)

        record.actual_weight = Decimal("94.0")
        with self.assertRaises(WeighingRecordImmutable):
            record.save()
        with self.assertRaises(WeighingRecordImmutable):
            record.delete()
        self.assertEqual(WeighingRecord.objects.get().actual_weight, Decimal("94.2"))

    def test_the_attempt_of_a_record_cannot_be_removed(self):
        self.ready(YELLOW)
        record, _ = self.confirm(YELLOW)

        with self.assertRaises(ProtectedError):
            ComponentAttempt.objects.filter(pk=record.attempt_id).delete()


class ProgressionOrderTests(ConfirmTestCase):
    def test_the_five_components_in_recipe_order(self):
        """Story 008 AC 1 and AC 2 (workbook STEP 23)."""
        self.activate(BLUE)
        seen = []
        for sequence in range(1, 6):
            self.verify(sequence)
            self.set_weight(sequence, TEAL[sequence][3])
            active = progression.progress(self.session.pk).active_attempt
            seen.append((active.component_sequence, active.scale_id))

            record, state = self.confirm(sequence)

            self.assertEqual(state.text, f"{sequence} of 5 components weighed")
            self.assertEqual(record.unit, TEAL[sequence][1])

        self.assertEqual(
            seen,
            [
                (1, "scale-3kg"),
                (2, "scale-3kg"),
                (3, "scale-3kg"),
                (4, "scale-32kg"),
                (5, "scale-32kg"),
            ],
        )
        self.assertEqual(
            list(WeighingRecord.objects.values_list("component_name", flat=True)),
            [
                "Remazol Brill. Blue RSPL",
                "Remazol Red RB",
                "Remazol Yellow RGB",
                "Sodium Sulphate",
                "Soda Ash",
            ],
        )
        final = progression.progress(self.session.pk)
        self.assertIsNone(final.active_attempt)
        self.assertIsNone(final.next_pending)
        self.assertTrue(
            all(
                r.attempt.end_reason == AttemptEnd.CONFIRMED
                for r in WeighingRecord.objects.all()
            )
        )

    def test_after_yellow_rgb_the_floor_scale_and_kg_take_over(self):
        """Story 008 AC 2."""
        self.activate(BLUE)
        for sequence in (BLUE, 2):
            self.verify(sequence)
            self.set_weight(sequence, TEAL[sequence][3])
            self.confirm(sequence)
        self.verify(YELLOW)
        self.set_weight(YELLOW, "94.2")

        _, state = self.confirm(YELLOW)

        active = state.active_attempt
        self.assertEqual(
            (active.component_sequence, active.scale_id), (SODIUM, "scale-32kg")
        )
        self.assertEqual(state.components[3].unit, "kg")
        self.assertTrue(active.is_tared)

    def test_after_a_touched_component_the_first_pending_one_comes_next(self):
        self.ready(YELLOW)

        _, state = self.confirm(YELLOW)

        self.assertEqual(state.active_attempt.component_sequence, BLUE)
        self.assertEqual(state.text, "1 of 5 components weighed")
