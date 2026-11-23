"""Story 004-verify-dyestuff-identity and story 005 AC 2: identity checks, readiness.

``verify_identity`` re-reads the scan through the scanner adapter (ADR-006), so
those tests run against the live Dummy Scanner (training contract). The
readiness rule is tested with stored checks.
"""

from django.test import LiveServerTestCase, TestCase, override_settings

from dummy_orgatex.services import seed_training_scenario
from tests.helpers import post_json, set_mode
from tests.weighing import factories
from weighing import identity
from weighing.identity import IdentityStatus
from weighing.models import (
    IdentityCheck,
    IdentityCheckImmutable,
    IdentityResult,
    Operator,
)
from weighing.services import RefusalReason, WeighingRefused

YELLOW = factories.YELLOW_RGB
SODIUM = factories.SODIUM_SULPHATE
LOGGER = "weighing.identity"


def record(session, sequence, result, scan_id, code="DYE-4471"):
    return IdentityCheck.objects.create(
        session=session,
        component_sequence=sequence,
        expected_code="DYE-4471",
        scan_id=scan_id,
        scanned_code=code,
        result=result,
        operator=session.operator,
    )


class LiveScannerTestCase(LiveServerTestCase):
    def setUp(self):
        seed_training_scenario()
        Operator.objects.get_or_create(
            operator_id="OP-01", defaults={"name": "R. Karim", "shift": "A"}
        )
        self.enterContext(
            override_settings(SCANNER_BASE_URL=f"{self.live_server_url}/api")
        )
        self.session = factories.session()

    def scan(self, code, kind="dyestuff"):
        response = post_json(
            self.client, "/api/training/scanner/scans", {"kind": kind, "code": code}
        )
        return response.json()["scanId"]

    def verify(self, scan_id, sequence=YELLOW, operator_id="OP-01"):
        return identity.verify_identity(self.session.pk, sequence, scan_id, operator_id)

    def assert_refused(self, reason, scan_id, sequence=YELLOW, operator_id="OP-01"):
        with self.assertRaises(WeighingRefused) as refused:
            self.verify(scan_id, sequence, operator_id)
        self.assertEqual(refused.exception.reason, reason)
        self.assertEqual(IdentityCheck.objects.count(), 0)


class VerifyTests(LiveScannerTestCase):
    def test_matching_scan_verifies_yellow_rgb(self):
        """Story 004 AC 1."""
        with self.assertLogs(LOGGER, "INFO") as logs:
            check, created = self.verify(self.scan("DYE-4471"))

        self.assertTrue(created)
        self.assertEqual(check.result, IdentityResult.VERIFIED)
        self.assertEqual(
            (check.expected_code, check.scanned_code), ("DYE-4471", "DYE-4471")
        )
        self.assertEqual(check.operator.operator_id, "OP-01")
        self.assertEqual(
            identity.identity_status(self.session, YELLOW)[0], IdentityStatus.VERIFIED
        )
        self.assertIn("DyestuffVerified", logs.output[0])

    def test_different_code_is_wrong_dyestuff_and_blocks(self):
        """Story 004 AC 2."""
        with self.assertLogs(LOGGER, "WARNING") as logs:
            check, created = self.verify(self.scan("DYE-2204"))

        self.assertTrue(created)
        self.assertEqual(check.result, IdentityResult.WRONG_DYESTUFF)
        self.assertEqual(identity.RESULT_MESSAGE[check.result], "Wrong dyestuff")
        self.assertIn("WrongDyestuffScanned", logs.output[0])
        self.assertIn("expected=DYE-4471 scanned=DYE-2204", logs.output[0])
        with self.assertRaises(WeighingRefused) as refused:
            identity.check_material_ready(self.session, YELLOW)
        self.assertEqual(refused.exception.reason, RefusalReason.WRONG_DYESTUFF)

    def test_code_is_compared_exactly(self):
        check, _ = self.verify(self.scan("dye-4471"))

        self.assertEqual(check.result, IdentityResult.WRONG_DYESTUFF)

    def test_surrounding_spaces_are_ignored(self):
        check, _ = self.verify(self.scan(" DYE-4471 "))

        self.assertEqual(check.result, IdentityResult.VERIFIED)

    def test_auxiliaries_are_verified_too(self):
        """Model Decision 5: every component needs an identity scan."""
        check, _ = self.verify(self.scan("AUX-0101"), sequence=SODIUM)

        self.assertEqual(check.result, IdentityResult.VERIFIED)

    def test_a_dyestuff_code_of_another_component_is_wrong(self):
        check, _ = self.verify(self.scan("DYE-4471"), sequence=SODIUM)

        self.assertEqual(check.result, IdentityResult.WRONG_DYESTUFF)

    def test_wrong_scan_after_a_verified_one_blocks_again(self):
        """Model Decision 3: the latest check counts."""
        self.verify(self.scan("DYE-4471"))
        with self.assertLogs(LOGGER, "WARNING"):
            self.verify(self.scan("DYE-9999"))

        status, latest = identity.identity_status(self.session, YELLOW)

        self.assertEqual(status, IdentityStatus.WRONG_DYESTUFF)
        self.assertEqual(latest.scanned_code, "DYE-9999")
        self.assertEqual(IdentityCheck.objects.count(), 2)

    def test_right_scan_after_a_wrong_one_unblocks(self):
        with self.assertLogs(LOGGER, "WARNING"):
            self.verify(self.scan("DYE-9999"))
        self.verify(self.scan("DYE-4471"))

        self.assertIsNone(identity.check_material_ready(self.session, YELLOW))

    def test_the_same_scan_is_recorded_once(self):
        scan_id = self.scan("DYE-4471")
        first, _ = self.verify(scan_id)

        again, created = self.verify(scan_id)

        self.assertFalse(created)
        self.assertEqual(again.pk, first.pk)
        self.assertEqual(IdentityCheck.objects.count(), 1)

    def test_a_scan_stays_with_the_component_it_was_first_checked_for(self):
        scan_id = self.scan("DYE-4471")
        self.verify(scan_id)

        again, created = self.verify(scan_id, sequence=SODIUM)

        self.assertFalse(created)
        self.assertEqual(again.component_sequence, YELLOW)
        self.assertEqual(
            identity.identity_status(self.session, SODIUM)[0],
            IdentityStatus.UNVERIFIED,
        )


class VerifyRefusalTests(LiveScannerTestCase):
    def test_batch_scan_is_not_a_dyestuff_scan(self):
        with self.assertLogs(LOGGER, "INFO"):
            self.assert_refused(
                RefusalReason.NOT_A_DYESTUFF_SCAN, self.scan("B-24187", kind="batch")
            )

    def test_a_scan_that_is_no_longer_the_latest_is_refused(self):
        older = self.scan("DYE-4471")
        self.scan("DYE-2204")

        with self.assertLogs(LOGGER, "INFO"):
            self.assert_refused(RefusalReason.SCAN_NOT_CURRENT, older)

    def test_an_unknown_scan_id_is_refused(self):
        self.scan("DYE-4471")

        with self.assertLogs(LOGGER, "INFO"):
            self.assert_refused(RefusalReason.SCAN_NOT_CURRENT, 999)

    def test_no_scan_at_all_is_refused(self):
        with self.assertLogs(LOGGER, "INFO"):
            self.assert_refused(RefusalReason.SCAN_NOT_CURRENT, 1)

    def test_unavailable_scanner_stores_nothing(self):
        scan_id = self.scan("DYE-4471")
        set_mode(self.client, "scanner", "unavailable")

        with self.assertLogs(LOGGER, "INFO"), self.assertLogs("devices", "WARNING"):
            self.assert_refused(RefusalReason.SCANNER_UNAVAILABLE, scan_id)

        self.assertEqual(
            identity.identity_status(self.session, YELLOW)[0],
            IdentityStatus.UNVERIFIED,
        )

    def test_no_operator_is_refused_before_reading_the_scanner(self):
        set_mode(self.client, "scanner", "unavailable")

        with self.assertLogs("weighing.services", "INFO"):
            self.assert_refused(RefusalReason.OPERATOR_REQUIRED, 1, operator_id=None)

    def test_unknown_component_is_refused(self):
        with self.assertLogs(LOGGER, "INFO"):
            self.assert_refused(
                RefusalReason.COMPONENT_NOT_FOUND, self.scan("DYE-4471"), sequence=9
            )

    def test_unknown_session_is_refused(self):
        with self.assertRaises(WeighingRefused) as refused:
            identity.verify_identity(999, YELLOW, self.scan("DYE-4471"), "OP-01")

        self.assertEqual(refused.exception.reason, RefusalReason.SESSION_NOT_FOUND)


class ReadinessTests(TestCase):
    """``check_material_ready``: the material gate bolt 010's confirm calls."""

    def ready_or_reason(self, session, sequence=YELLOW):
        try:
            identity.check_material_ready(session, sequence)
        except WeighingRefused as refused:
            return refused.reason
        return None

    def test_not_verified_is_refused(self):
        """Story 004 AC 3."""
        with self.assertLogs(LOGGER, "INFO"):
            reason = self.ready_or_reason(factories.session())

        self.assertEqual(reason, RefusalReason.IDENTITY_NOT_VERIFIED)

    def test_wrong_dyestuff_is_refused(self):
        session = factories.session()
        record(session, YELLOW, IdentityResult.WRONG_DYESTUFF, 1, code="DYE-2204")

        with self.assertLogs(LOGGER, "INFO"):
            reason = self.ready_or_reason(session)

        self.assertEqual(reason, RefusalReason.WRONG_DYESTUFF)

    def test_verified_component_with_lot_and_container_is_ready(self):
        session = factories.session()
        record(session, YELLOW, IdentityResult.VERIFIED, 1)

        self.assertIsNone(self.ready_or_reason(session))

    def test_missing_lot_is_refused_even_when_verified(self):
        """Story 005 AC 2."""
        session = factories.session(factories.teal_selection({YELLOW: {"lot": ""}}))
        record(session, YELLOW, IdentityResult.VERIFIED, 1)

        with self.assertLogs(LOGGER, "INFO"):
            reason = self.ready_or_reason(session)

        self.assertEqual(reason, RefusalReason.LOT_MISSING)
        self.assertEqual(reason.value, "Lot missing for this component")

    def test_missing_container_is_refused(self):
        """Model Decision 4 (FR-6b)."""
        session = factories.session(
            factories.teal_selection({YELLOW: {"container": " "}})
        )
        record(session, YELLOW, IdentityResult.VERIFIED, 1)

        with self.assertLogs(LOGGER, "INFO"):
            reason = self.ready_or_reason(session)

        self.assertEqual(reason, RefusalReason.CONTAINER_MISSING)

    def test_lot_is_checked_before_identity(self):
        session = factories.session(factories.teal_selection({YELLOW: {"lot": ""}}))

        with self.assertLogs(LOGGER, "INFO"):
            reason = self.ready_or_reason(session)

        self.assertEqual(reason, RefusalReason.LOT_MISSING)

    def test_verification_is_per_component(self):
        session = factories.session()
        record(session, YELLOW, IdentityResult.VERIFIED, 1)

        with self.assertLogs(LOGGER, "INFO"):
            reason = self.ready_or_reason(session, SODIUM)

        self.assertEqual(reason, RefusalReason.IDENTITY_NOT_VERIFIED)

    def test_verification_is_per_session(self):
        first = factories.session()
        record(first, YELLOW, IdentityResult.VERIFIED, 1)
        first.state = "complete"
        first.save()
        second = factories.session()

        with self.assertLogs(LOGGER, "INFO"):
            reason = self.ready_or_reason(second)

        self.assertEqual(reason, RefusalReason.IDENTITY_NOT_VERIFIED)


class AppendOnlyTests(TestCase):
    def test_a_check_cannot_be_changed(self):
        check = record(factories.session(), YELLOW, IdentityResult.WRONG_DYESTUFF, 1)
        check.result = IdentityResult.VERIFIED

        with self.assertRaises(IdentityCheckImmutable):
            check.save()

    def test_a_check_cannot_be_deleted(self):
        check = record(factories.session(), YELLOW, IdentityResult.VERIFIED, 1)

        with self.assertRaises(IdentityCheckImmutable):
            check.delete()
        self.assertTrue(IdentityCheck.objects.filter(pk=check.pk).exists())
