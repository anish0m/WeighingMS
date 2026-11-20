"""Story 001 AC 1 / AC 3: a weighing session needs an identified operator."""

from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from tests.weighing import factories
from weighing import services
from weighing.models import (
    Operator,
    SessionNotDeletable,
    SessionState,
    WeighingSession,
)
from weighing.services import RefusalReason, WeighingRefused

LOGGER = "weighing.services"


class StartSessionTests(TestCase):
    def setUp(self):
        self.selection = factories.selection()

    def test_session_cannot_start_without_an_operator(self):
        with self.assertRaises(WeighingRefused) as caught:
            services.start_session(self.selection.pk, None)

        self.assertEqual(caught.exception.reason, RefusalReason.OPERATOR_REQUIRED)
        self.assertEqual(WeighingSession.objects.count(), 0)

    def test_session_starts_for_the_identified_operator(self):
        session, created = services.start_session(self.selection.pk, "OP-01")

        self.assertTrue(created)
        self.assertEqual(session.operator.operator_id, "OP-01")
        self.assertEqual(session.selection, self.selection)
        self.assertEqual(session.batch_id, "B-24187")
        self.assertEqual(session.state, SessionState.IN_PROGRESS)
        self.assertIsNotNone(session.started_at)
        self.assertIsNone(session.completed_at)

    def test_start_is_logged(self):
        with self.assertLogs(LOGGER, "INFO") as logs:
            services.start_session(self.selection.pk, "OP-01")

        self.assertIn("WeighingSessionStarted", logs.output[-1])
        self.assertIn("B-24187", logs.output[-1])
        self.assertIn("OP-01", logs.output[-1])

    def test_unknown_selection_is_refused(self):
        with self.assertRaises(WeighingRefused) as caught:
            services.start_session(999999, "OP-01")

        self.assertEqual(caught.exception.reason, RefusalReason.SELECTION_NOT_FOUND)
        self.assertEqual(WeighingSession.objects.count(), 0)

    def test_operator_is_checked_before_the_selection(self):
        with self.assertRaises(WeighingRefused) as caught:
            services.start_session(999999, None)

        self.assertEqual(caught.exception.reason, RefusalReason.OPERATOR_REQUIRED)


class OpenSessionPerBatchTests(TestCase):
    """Decision 4: a batch has at most one open session; it is returned."""

    def setUp(self):
        self.selection = factories.selection()
        self.first, _ = services.start_session(self.selection.pk, "OP-01")

    def test_starting_again_returns_the_open_session(self):
        session, created = services.start_session(self.selection.pk, "OP-01")

        self.assertFalse(created)
        self.assertEqual(session, self.first)
        self.assertEqual(WeighingSession.objects.count(), 1)

    def test_a_newer_selection_of_the_batch_returns_the_open_session(self):
        newer = factories.selection()

        session, created = services.start_session(newer.pk, "OP-01")

        self.assertFalse(created)
        self.assertEqual(session.selection, self.selection)

    def test_returned_session_keeps_its_operator(self):
        Operator.objects.create(operator_id="OP-02", name="A. Test", shift="B")

        session, _ = services.start_session(self.selection.pk, "OP-02")

        self.assertEqual(session.operator.operator_id, "OP-01")

    def test_another_batch_gets_its_own_session(self):
        other = factories.selection("B-24188")

        _, created = services.start_session(other.pk, "OP-01")

        self.assertTrue(created)
        self.assertEqual(WeighingSession.objects.count(), 2)

    def test_database_rejects_a_second_open_session(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            WeighingSession.objects.create(
                selection=self.selection,
                batch_id="B-24187",
                operator=self.first.operator,
            )

    def test_completed_session_does_not_block_a_new_one(self):
        WeighingSession.objects.filter(pk=self.first.pk).update(
            state=SessionState.COMPLETE
        )

        _, created = services.start_session(self.selection.pk, "OP-01")

        self.assertTrue(created)


class SessionIntegrityTests(TestCase):
    """NFR-12 groundwork: sessions and the rows they point at stay."""

    def setUp(self):
        self.selection = factories.selection()
        self.session, _ = services.start_session(self.selection.pk, "OP-01")

    def test_session_cannot_be_deleted(self):
        with self.assertRaises(SessionNotDeletable):
            self.session.delete()

        self.assertEqual(WeighingSession.objects.count(), 1)

    def test_operator_of_a_session_cannot_be_deleted(self):
        with self.assertRaises(ProtectedError):
            Operator.objects.filter(operator_id="OP-01").delete()
