"""Story 007-handle-overshoot: blocked, recovered, never recalculated.

The STEP 24 training rule (OQ-4, ADR-012) against the live Dummy Scale
(training contract): an overweight component remains unconfirmed; the
recovery is to remove material back into the band, or Quit (F4) to discard
and re-weigh, which the server stores as an overshoot discard.
"""

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from batches.models import SnapshotComponent
from tests.weighing.flow import TEAL, YELLOW, LiveFlowTestCase
from weighing import confirmation, progression
from weighing.models import (
    AttemptEnd,
    AttemptImmutable,
    ComponentAttempt,
    WeighingRecord,
    WeighingResult,
)
from weighing.services import RefusalReason, WeighingRefused

OVER = "96.4"


class OvershootFlowTestCase(LiveFlowTestCase):
    def setUp(self):
        super().setUp()
        self.attempt = progression.activate(
            self.session.pk, YELLOW, "OP-01"
        ).active_attempt
        self.verify(YELLOW)

    def confirm(self):
        return confirmation.confirm(self.session.pk, YELLOW, "OP-01")

    def quit(self):
        return progression.quit_attempt(self.session.pk, YELLOW, "OP-01")

    def targets(self):
        return list(
            SnapshotComponent.objects.order_by("pk").values_list(
                "pk", "target_qty", "tolerance", "unit"
            )
        )


class BlockedTests(OvershootFlowTestCase):
    def test_confirm_at_96_4_g_is_refused_with_the_surplus(self):
        """Story 007 AC 1 on the server: confirm blocked, nothing stored."""
        self.set_weight(YELLOW, OVER)

        with (
            self.assertLogs("weighing.confirmation", "INFO"),
            self.assertRaises(WeighingRefused) as refused,
        ):
            self.confirm()

        self.assertEqual(refused.exception.reason, RefusalReason.OUT_OF_TOLERANCE)
        self.assertEqual(
            refused.exception.detail,
            {
                "net": "96.4",
                "unit": "g",
                "zone": "over",
                "surplus": "2.4",
                "surplusPercent": "2.6",
                "surplusText": "2.4 g",
            },
        )
        self.assertFalse(WeighingRecord.objects.exists())

    def test_no_target_changes_after_an_overshoot(self):
        """Story 007 AC 2: no recalculation, whatever the operator does."""
        before = self.targets()
        self.set_weight(YELLOW, OVER)
        with (
            self.assertLogs("weighing.confirmation", "INFO"),
            self.assertRaises(WeighingRefused),
        ):
            self.confirm()
        self.quit()
        progression.tare(self.session.pk, YELLOW, "OP-01")
        self.set_weight(YELLOW, "94.2")
        self.confirm()

        self.assertEqual(self.targets(), before)
        record = WeighingRecord.objects.get()
        self.assertEqual(
            (record.target, record.tolerance_min, record.tolerance_max),
            (Decimal("94.0000"), Decimal("93.5000"), Decimal("94.5000")),
        )

    def test_no_override_or_recalculation_endpoint_exists(self):
        base = f"/station/api/sessions/{self.session.pk}/components/{YELLOW}"
        for action in ("override", "recalculate", "compensate", "targets"):
            with self.subTest(action=action):
                self.assertEqual(self.client.post(f"{base}/{action}").status_code, 404)
        self.assertEqual(
            {value for value, _ in WeighingResult.choices}, {WeighingResult.WITHIN}
        )


class RecoveryTests(OvershootFlowTestCase):
    def test_removing_material_back_into_the_band_allows_confirm(self):
        """Recovery (a): 96.4 g, then 94.0 g → recorded at 94.0 g, within."""
        self.set_weight(YELLOW, OVER)
        with (
            self.assertLogs("weighing.confirmation", "INFO"),
            self.assertRaises(WeighingRefused),
        ):
            self.confirm()

        self.set_weight(YELLOW, "94.0")
        record, state = self.confirm()

        self.assertEqual(record.actual_weight, Decimal("94.0"))
        self.assertEqual(record.result, WeighingResult.WITHIN)
        self.assertEqual(record.attempt_id, self.attempt.pk)
        self.assertEqual(state.weighed, 1)

    def test_quit_over_tolerance_is_an_overshoot_discard(self):
        """Recovery (b): Quit F4 = discard and re-weigh, stored with its surplus."""
        self.set_weight(YELLOW, OVER)

        with self.assertLogs("weighing.progression", "INFO") as logs:
            state = self.quit()

        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.end_reason, AttemptEnd.OVERSHOOT_DISCARDED)
        self.assertEqual(
            (self.attempt.end_net, self.attempt.end_surplus, self.attempt.end_unit),
            (Decimal("96.4"), Decimal("2.4"), "g"),
        )
        self.assertFalse(WeighingRecord.objects.exists())
        self.assertEqual(state.active_attempt.component_sequence, YELLOW)
        self.assertFalse(state.active_attempt.is_tared)
        self.assertEqual(state.ended.attempt_id, self.attempt.pk)
        self.assertEqual(state.ended.reason, AttemptEnd.OVERSHOOT_DISCARDED)
        self.assertEqual(
            state.ended.message,
            "Overshoot discarded (96.4 g). Empty the container and press Re-tare (F2).",
        )
        discarded = [line for line in logs.output if "OvershootDiscarded" in line]
        self.assertEqual(len(discarded), 1)
        self.assertIn("surplus=2.4", discarded[0])
        self.assertIn("percent=2.6", discarded[0])
        self.assertIn("operator=OP-01", discarded[0])
        self.assertFalse(any("AttemptQuit" in line for line in logs.output))

    def test_after_a_discard_retare_and_reweigh_confirms(self):
        self.set_weight(YELLOW, OVER)
        self.quit()

        progression.tare(self.session.pk, YELLOW, "OP-01")
        self.set_weight(YELLOW, TEAL[YELLOW][3])
        record, _ = self.confirm()

        self.assertEqual(record.actual_weight, Decimal("94.2"))
        self.assertEqual(
            list(
                ComponentAttempt.objects.order_by("pk").values_list(
                    "end_reason", flat=True
                )
            ),
            # discarded, re-weighed and confirmed, then Sodium Sulphate (open)
            [AttemptEnd.OVERSHOOT_DISCARDED, AttemptEnd.CONFIRMED, ""],
        )

    def test_quit_within_tolerance_is_a_plain_quit(self):
        self.set_weight(YELLOW, "94.0")

        state = self.quit()

        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.end_reason, AttemptEnd.QUIT)
        self.assertIsNone(self.attempt.end_net)
        self.assertIsNone(self.attempt.end_surplus)
        self.assertEqual(self.attempt.end_unit, "")
        self.assertIsNone(state.ended.discard)
        self.assertEqual(
            state.ended.message,
            "Attempt abandoned. Empty the container and press Re-tare (F2).",
        )

    def test_quit_on_a_disconnected_scale_is_never_blocked(self):
        """Model Decision 3: no reading → no measured overshoot → plain quit."""
        self.set_weight(YELLOW, OVER)
        self.scale_mode("scale-3kg", "disconnected")

        state = self.quit()

        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.end_reason, AttemptEnd.QUIT)
        self.assertIsNone(self.attempt.end_net)
        self.assertEqual(state.active_attempt.component_sequence, YELLOW)


class DiscardStorageTests(OvershootFlowTestCase):
    def test_the_discard_snapshot_is_written_once(self):
        self.set_weight(YELLOW, OVER)
        self.quit()
        self.attempt.refresh_from_db()

        self.attempt.end_net = Decimal("95.0")
        with self.assertRaises(AttemptImmutable):
            self.attempt.save()
        with self.assertRaises(AttemptImmutable):
            self.attempt.delete()

    def test_the_database_ties_the_snapshot_to_the_discard_reason(self):
        ended = {"session": self.session, "scale_id": "scale-3kg"}
        now = timezone.now()
        bad = (
            {"end_reason": AttemptEnd.QUIT, "end_net": Decimal("96.4")},
            {
                "end_reason": AttemptEnd.OVERSHOOT_DISCARDED,
                "end_net": Decimal("96.4"),
                "end_surplus": Decimal("2.4"),
            },
            {"end_reason": AttemptEnd.OVERSHOOT_DISCARDED},
        )
        for fields in bad:
            with (
                self.subTest(fields=fields),
                self.assertRaises(IntegrityError),
                transaction.atomic(),
            ):
                ComponentAttempt.objects.create(
                    component_sequence=YELLOW, ended_at=now, **ended, **fields
                )
