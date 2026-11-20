"""Story 001-identify-operator and ADR-004: seeded identities and their rules."""

from django.test import TestCase

from weighing import services
from weighing.models import Operator, Supervisor
from weighing.services import OperatorRef, RefusalReason, WeighingRefused

LOGGER = "weighing.services"
R_KARIM = OperatorRef("OP-01", "R. Karim", "A", "R. Karim · Shift A")


class SeedTests(TestCase):
    def test_r_karim_shift_a_is_seeded(self):
        operator = Operator.objects.get(operator_id="OP-01")

        self.assertEqual((operator.name, operator.shift), ("R. Karim", "A"))
        self.assertTrue(operator.active)

    def test_training_supervisor_is_seeded_with_a_hashed_pin(self):
        supervisor = Supervisor.objects.get(supervisor_id="SUP-01")

        self.assertEqual(supervisor.name, "Training Supervisor")
        self.assertTrue(supervisor.pin_hash.startswith("pbkdf2_sha256$"))
        self.assertNotIn("2468", supervisor.pin_hash)

    def test_operators_and_supervisors_are_separate(self):
        self.assertFalse(Operator.objects.filter(operator_id="SUP-01").exists())
        self.assertFalse(Supervisor.objects.filter(supervisor_id="OP-01").exists())


class OperatorListTests(TestCase):
    def test_list_holds_the_seeded_operator(self):
        self.assertEqual(services.list_operators(), [R_KARIM])

    def test_inactive_operators_are_not_listed(self):
        Operator.objects.create(operator_id="OP-02", name="Former", shift="B")
        Operator.objects.filter(operator_id="OP-02").update(active=False)

        self.assertEqual(services.list_operators(), [R_KARIM])

    def test_list_is_ordered_by_name(self):
        Operator.objects.create(operator_id="OP-02", name="A. Test", shift="B")

        names = [o.name for o in services.list_operators()]

        self.assertEqual(names, ["A. Test", "R. Karim"])


class ChooseOperatorTests(TestCase):
    def test_header_text_is_name_and_shift(self):
        self.assertEqual(services.find_operator("OP-01").display, "R. Karim · Shift A")

    def test_unknown_operator_cannot_be_chosen(self):
        with self.assertRaises(WeighingRefused) as caught:
            services.find_operator("OP-99")

        self.assertEqual(caught.exception.reason, RefusalReason.OPERATOR_NOT_FOUND)

    def test_inactive_operator_cannot_be_chosen(self):
        Operator.objects.filter(operator_id="OP-01").update(active=False)

        with self.assertRaises(WeighingRefused):
            services.find_operator("OP-01")

    def test_supervisor_id_is_not_an_operator(self):
        with self.assertRaises(WeighingRefused):
            services.find_operator("SUP-01")


class RequireOperatorTests(TestCase):
    """Story AC 3: a weighing action without an operator is refused."""

    def test_identified_operator_passes(self):
        self.assertEqual(services.require_operator("OP-01", "test"), R_KARIM)

    def test_no_operator_is_refused(self):
        for operator_id in (None, ""):
            with (
                self.subTest(operator_id=operator_id),
                self.assertRaises(WeighingRefused) as caught,
            ):
                services.require_operator(operator_id, "test")
            self.assertEqual(caught.exception.reason, RefusalReason.OPERATOR_REQUIRED)
            self.assertEqual(caught.exception.message, "Choose an operator first")

    def test_operator_no_longer_active_counts_as_none(self):
        Operator.objects.filter(operator_id="OP-01").update(active=False)

        with self.assertRaises(WeighingRefused):
            services.require_operator("OP-01", "test")

    def test_refusal_is_logged_with_action(self):
        with (
            self.assertLogs(LOGGER, "INFO") as logs,
            self.assertRaises(WeighingRefused),
        ):
            services.require_operator(None, "start_session")

        self.assertIn("WeighingActionRefused", logs.output[0])
        self.assertIn("start_session", logs.output[0])
        self.assertIn("OPERATOR_REQUIRED", logs.output[0])


class SupervisorVerificationTests(TestCase):
    """OQ-3 / NFR-4: supervisor ID + PIN; no shared credentials between roles."""

    def test_correct_id_and_pin_verify(self):
        supervisor = services.verify_supervisor("SUP-01", "2468")

        self.assertEqual(supervisor.supervisor_id, "SUP-01")

    def test_every_mismatch_gives_the_same_refusal(self):
        cases = {
            "wrong pin": ("SUP-01", "1111"),
            "empty pin": ("SUP-01", ""),
            "unknown id": ("SUP-99", "2468"),
            "operator id": ("OP-01", "2468"),
        }
        for name, (supervisor_id, pin) in cases.items():
            with (
                self.subTest(case=name),
                self.assertLogs(LOGGER, "WARNING"),
                self.assertRaises(WeighingRefused) as caught,
            ):
                services.verify_supervisor(supervisor_id, pin)
            self.assertEqual(
                caught.exception.reason, RefusalReason.SUPERVISOR_NOT_VERIFIED
            )
            self.assertEqual(caught.exception.message, "Supervisor ID or PIN incorrect")

    def test_inactive_supervisor_is_refused(self):
        Supervisor.objects.filter(supervisor_id="SUP-01").update(active=False)

        with self.assertLogs(LOGGER, "WARNING"), self.assertRaises(WeighingRefused):
            services.verify_supervisor("SUP-01", "2468")

    def test_failed_verification_never_logs_the_pin(self):
        with (
            self.assertLogs(LOGGER, "WARNING") as logs,
            self.assertRaises(WeighingRefused),
        ):
            services.verify_supervisor("SUP-01", "9753")

        self.assertIn("SupervisorVerificationFailed", logs.output[0])
        self.assertNotIn("9753", "".join(logs.output))

    def test_set_pin_stores_only_a_hash(self):
        supervisor = Supervisor(supervisor_id="SUP-02", name="Second")
        supervisor.set_pin("1357")

        self.assertNotIn("1357", supervisor.pin_hash)
        self.assertTrue(supervisor.check_pin("1357"))
        self.assertFalse(supervisor.check_pin("1358"))
