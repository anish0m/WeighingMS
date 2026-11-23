"""Stories 003 (tare / re-tare / quit), 008 (progression) and 010 (resume).

``weighing.progression`` against the live Dummy Scale (training contract).
Component state is derived from attempts and records (ADR-010); scale calls
happen before the write transaction (ADR-011).
"""

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from tests.weighing import factories
from tests.weighing.flow import (
    BLUE,
    SODIUM,
    UNREACHABLE,
    YELLOW,
    LiveFlowTestCase,
)
from weighing import confirmation, progression
from weighing.models import (
    AttemptEnd,
    AttemptImmutable,
    ComponentAttempt,
    WeighingRecord,
    WeighingResult,
)
from weighing.services import RefusalReason, WeighingRefused

LOGGER = "weighing.progression"


class RefusalAssertions:
    def assert_refused(self, reason, action, *args):
        with self.assertRaises(WeighingRefused) as refused:
            action(*args)
        self.assertEqual(refused.exception.reason, reason)


class ActivationTests(RefusalAssertions, LiveFlowTestCase):
    def activate(self, sequence, operator_id="OP-01"):
        return progression.activate(self.session.pk, sequence, operator_id)

    def test_before_activation_everything_is_pending(self):
        state = progression.progress(self.session.pk)

        self.assertEqual([c.state for c in state.components], ["pending"] * 5)
        self.assertIsNone(state.active_attempt)
        self.assertEqual(state.next_pending, BLUE)
        self.assertEqual(state.text, "0 of 5 components weighed")

    def test_first_activation_is_blue_rspl_tared_automatically(self):
        self.set_weight(BLUE, "214.0")

        state = self.activate(BLUE)

        attempt = state.active_attempt
        self.assertEqual(
            (attempt.component_sequence, attempt.scale_id), (1, "scale-3kg")
        )
        self.assertTrue(attempt.is_tared)
        self.assertEqual(self.scale_weight("scale-3kg"), "0.0000")

    def test_yellow_rgb_starts_tared_and_an_empty_container_reads_zero(self):
        """Story 003 AC 1: container C-12 (214 g) on the scale → 0.0 g net."""
        self.set_weight(YELLOW, "214.0")

        attempt = self.activate(YELLOW).active_attempt

        self.assertTrue(attempt.is_tared)
        self.assertEqual(self.scale_weight("scale-3kg"), "0.0000")

    def test_touching_a_pending_component_switches_to_it(self):
        """Story 008 AC 4: active with its own scale and units."""
        first = self.activate(YELLOW).active_attempt

        with self.assertLogs(LOGGER, "INFO") as logs:
            state = self.activate(SODIUM)

        first.refresh_from_db()
        self.assertEqual(first.end_reason, AttemptEnd.SWITCHED)
        self.assertEqual(state.active_attempt.scale_id, "scale-32kg")
        self.assertEqual(
            [(c.sequence, c.state, c.unit) for c in state.components][2:4],
            [(3, "pending", "g"), (4, "active", "kg")],
        )
        self.assertTrue(any("AttemptSwitched" in line for line in logs.output))
        self.assertFalse(WeighingRecord.objects.exists())

    def test_touching_the_active_component_changes_nothing(self):
        first = self.activate(YELLOW).active_attempt

        again = self.activate(YELLOW).active_attempt

        self.assertEqual(again.pk, first.pk)
        self.assertEqual(ComponentAttempt.objects.count(), 1)

    def test_touching_a_done_component_does_nothing(self):
        """Story 008 AC 3."""
        self.activate(BLUE)
        self.verify(BLUE)
        self.set_weight(BLUE, "1241.5")
        confirmation.confirm(self.session.pk, BLUE, "OP-01")
        before = list(ComponentAttempt.objects.values_list("pk", "ended_at"))

        with self.assertLogs(LOGGER, "INFO"):
            self.assert_refused(RefusalReason.COMPONENT_DONE, self.activate, BLUE)

        self.assertEqual(
            list(ComponentAttempt.objects.values_list("pk", "ended_at")), before
        )
        active = progression.progress(self.session.pk).active_attempt
        self.assertEqual(active.component_sequence, 2)

    def test_activation_needs_an_operator(self):
        with self.assertLogs("weighing.services", "INFO"):
            self.assert_refused(
                RefusalReason.OPERATOR_REQUIRED, self.activate, BLUE, None
            )
        self.assertFalse(ComponentAttempt.objects.exists())

    def test_unknown_component_is_refused(self):
        with self.assertLogs("weighing.identity", "INFO"):
            self.assert_refused(RefusalReason.COMPONENT_NOT_FOUND, self.activate, 9)

    def test_a_closed_session_is_refused(self):
        self.session.state = "complete"
        self.session.save()

        with self.assertLogs(LOGGER, "INFO"):
            self.assert_refused(RefusalReason.SESSION_NOT_OPEN, self.activate, BLUE)

    def test_a_failed_automatic_tare_leaves_the_component_active_but_untared(self):
        self.scale_mode("scale-3kg", "disconnected")

        with self.assertLogs(LOGGER, "WARNING") as logs:
            state = self.activate(YELLOW)

        self.assertEqual(state.active_attempt.component_sequence, YELLOW)
        self.assertFalse(state.active_attempt.is_tared)
        self.assertTrue(any("TareFailed" in line for line in logs.output))

    def test_the_attempt_keeps_its_scale_when_the_threshold_changes(self):
        attempt = self.activate(YELLOW).active_attempt

        with override_settings(WEIGHING_SCALE_THRESHOLD_KG=Decimal("0.05")):
            again = self.activate(YELLOW).active_attempt

        self.assertEqual((again.pk, again.scale_id), (attempt.pk, "scale-3kg"))


class TareAndQuitTests(RefusalAssertions, LiveFlowTestCase):
    def setUp(self):
        super().setUp()
        self.attempt = progression.activate(
            self.session.pk, YELLOW, "OP-01"
        ).active_attempt

    def test_retare_resets_net_to_zero_and_restarts_the_attempt(self):
        """Story 003 AC 2."""
        self.set_weight(YELLOW, "40.0")

        with self.assertLogs(LOGGER, "INFO") as logs:
            state = progression.tare(self.session.pk, YELLOW, "OP-01")

        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.end_reason, AttemptEnd.RETARED)
        self.assertNotEqual(state.active_attempt.pk, self.attempt.pk)
        self.assertTrue(state.active_attempt.is_tared)
        self.assertEqual(self.scale_weight("scale-3kg"), "0.0000")
        self.assertTrue(any("AttemptRetared" in line for line in logs.output))

    def test_taring_an_untared_attempt_keeps_the_attempt(self):
        progression.quit_attempt(self.session.pk, YELLOW, "OP-01")
        untared = progression.progress(self.session.pk).active_attempt

        state = progression.tare(self.session.pk, YELLOW, "OP-01")

        self.assertEqual(state.active_attempt.pk, untared.pk)
        self.assertTrue(state.active_attempt.is_tared)

    def test_quit_records_nothing_and_restarts_the_component(self):
        """Story 003 AC 3 and model Decision 2 (restart untared)."""
        self.set_weight(YELLOW, "40.0")

        with self.assertLogs(LOGGER, "INFO") as logs:
            state = progression.quit_attempt(self.session.pk, YELLOW, "OP-01")

        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.end_reason, AttemptEnd.QUIT)
        self.assertEqual(state.active_attempt.component_sequence, YELLOW)
        self.assertFalse(state.active_attempt.is_tared)
        self.assertFalse(WeighingRecord.objects.exists())
        self.assertEqual(self.scale_weight("scale-3kg"), "40.0000")
        self.assertTrue(any("AttemptQuit" in line for line in logs.output))

    def test_tare_on_a_disconnected_scale_changes_nothing(self):
        self.scale_mode("scale-3kg", "disconnected")

        with self.assertLogs(LOGGER, "INFO"):
            self.assert_refused(
                RefusalReason.SCALE_DISCONNECTED,
                progression.tare,
                self.session.pk,
                YELLOW,
                "OP-01",
            )

        self.assertEqual(ComponentAttempt.objects.count(), 1)
        self.assertIsNone(ComponentAttempt.objects.get().ended_at)

    def test_tare_on_an_unreachable_scale_is_unavailable(self):
        with (
            override_settings(SCALE_BASE_URL=UNREACHABLE),
            self.assertLogs(LOGGER, "INFO"),
            self.assertLogs("devices", "WARNING"),
        ):
            self.assert_refused(
                RefusalReason.SCALE_UNAVAILABLE,
                progression.tare,
                self.session.pk,
                YELLOW,
                "OP-01",
            )

    def test_tare_and_quit_need_the_active_component(self):
        for action in (progression.tare, progression.quit_attempt):
            with self.subTest(action=action.__name__), self.assertLogs(LOGGER):
                self.assert_refused(
                    RefusalReason.COMPONENT_NOT_ACTIVE,
                    action,
                    self.session.pk,
                    SODIUM,
                    "OP-01",
                )

    def test_tare_and_quit_need_an_operator(self):
        for action in (progression.tare, progression.quit_attempt):
            with (
                self.subTest(action=action.__name__),
                self.assertLogs("weighing.services"),
            ):
                self.assert_refused(
                    RefusalReason.OPERATOR_REQUIRED,
                    action,
                    self.session.pk,
                    YELLOW,
                    None,
                )


class NoActiveComponentTests(RefusalAssertions, LiveFlowTestCase):
    def test_tare_without_an_active_component(self):
        with self.assertLogs(LOGGER, "INFO"):
            self.assert_refused(
                RefusalReason.NO_ACTIVE_COMPONENT,
                progression.tare,
                self.session.pk,
                YELLOW,
                "OP-01",
            )


class ResumeTests(LiveFlowTestCase):
    def confirm(self, sequence, weight):
        self.verify(sequence)
        self.set_weight(sequence, weight)
        confirmation.confirm(self.session.pk, sequence, "OP-01")

    def test_reload_reopens_at_the_in_progress_component(self):
        """Story 010 AC 1: 2 of 5 confirmed → Yellow RGB active, both kept."""
        progression.activate(self.session.pk, BLUE, "OP-01")
        self.confirm(BLUE, "1241.5")
        self.confirm(2, "385.4")

        state = progression.current_session()

        self.assertEqual(state.session.pk, self.session.pk)
        self.assertEqual(state.active_attempt.component_sequence, YELLOW)
        self.assertEqual(state.text, "2 of 5 components weighed")
        self.assertEqual(
            [str(c.record.actual_weight) for c in state.components[:2]],
            ["1241.5000", "385.4000"],
        )

    def test_the_most_recently_active_open_session_is_resumed(self):
        other = factories.session(factories.teal_selection(batch_id="B-24188"))
        progression.activate(self.session.pk, BLUE, "OP-01")
        progression.activate(other.pk, BLUE, "OP-01")

        self.assertEqual(progression.current_session().session.pk, other.pk)

        progression.activate(self.session.pk, YELLOW, "OP-01")
        self.assertEqual(progression.current_session().session.pk, self.session.pk)


class StoredStateTests(TestCase):
    """Story 010 AC 2: the state is rebuilt from database rows only."""

    def test_progress_is_derived_from_attempts_and_records(self):
        session = factories.session()
        done = ComponentAttempt.objects.create(
            session=session, component_sequence=1, scale_id="scale-3kg"
        )
        done.ended_at = done.started_at
        done.end_reason = AttemptEnd.CONFIRMED
        done.save()
        component = session.selection.components.get(sequence=1)
        WeighingRecord.objects.create(
            session=session,
            attempt=done,
            batch_id=session.batch_id,
            component_sequence=1,
            component_code=component.code,
            component_name=component.name,
            actual_weight=component.target_qty,
            unit="g",
            lot=component.lot,
            container=component.container,
            tare=component.tare,
            scale_id="scale-3kg",
            target=component.target_qty,
            tolerance_min=component.target_qty,
            tolerance_max=component.target_qty,
            result=WeighingResult.WITHIN,
            operator=session.operator,
        )
        ComponentAttempt.objects.create(
            session=session, component_sequence=4, scale_id="scale-32kg"
        )

        state = progression.progress(session.pk)

        self.assertEqual(
            [c.state for c in state.components],
            ["done", "pending", "pending", "active", "pending"],
        )
        self.assertEqual(state.text, "1 of 5 components weighed")
        self.assertEqual(state.next_pending, 4)

    def test_no_open_session_resumes_nothing(self):
        session = factories.session()
        session.state = "complete"
        session.save()

        self.assertIsNone(progression.current_session())

    def test_a_new_session_starts_at_the_first_component(self):
        session = factories.session()

        state = progression.progress(session.pk)

        self.assertEqual(state.next_pending, 1)
        self.assertEqual(state.total, 5)


class AttemptAppendOnlyTests(TestCase):
    """ADR-010: attempts are append-only, one open attempt per session."""

    def setUp(self):
        self.attempt = ComponentAttempt.objects.create(
            session=factories.session(), component_sequence=3, scale_id="scale-3kg"
        )

    def test_fixed_fields_cannot_change(self):
        self.attempt.scale_id = "scale-32kg"

        with self.assertRaises(AttemptImmutable):
            self.attempt.save()

    def test_tared_and_ended_are_set_once(self):
        self.attempt.tared_at = self.attempt.started_at
        self.attempt.save()
        self.attempt.ended_at = self.attempt.started_at
        self.attempt.end_reason = AttemptEnd.QUIT
        self.attempt.save()

        self.attempt.end_reason = AttemptEnd.CONFIRMED
        with self.assertRaises(AttemptImmutable):
            self.attempt.save()

    def test_an_attempt_cannot_be_deleted(self):
        with self.assertRaises(AttemptImmutable):
            self.attempt.delete()

    def test_only_one_open_attempt_per_session(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ComponentAttempt.objects.create(
                session=self.attempt.session,
                component_sequence=4,
                scale_id="scale-32kg",
            )
