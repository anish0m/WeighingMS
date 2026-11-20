"""Story 003-scanner-input: scans reach WeighingMS once; failures change nothing.

The scanner adapter reads the seeded Dummy Scanner over real HTTP.
"""

from django.test import LiveServerTestCase, override_settings

from devices import scanner
from devices.scanner import Scan, ScannerUnavailable
from dummy_orgatex.services import seed_training_scenario
from tests.helpers import post_json, set_mode

LOGGER = "devices"


class LiveScannerTestCase(LiveServerTestCase):
    def setUp(self):
        seed_training_scenario()
        self.enterContext(
            override_settings(SCANNER_BASE_URL=f"{self.live_server_url}/api")
        )

    def scan(self, kind, code):
        return post_json(
            self.client, "/api/training/scanner/scans", {"kind": kind, "code": code}
        )


class ReceiveScanTests(LiveScannerTestCase):
    def test_no_scan_yet_returns_none(self):
        self.assertIsNone(scanner.read_latest_scan())

    def test_batch_scan_is_received(self):
        self.scan("batch", "B-24187")

        scan = scanner.read_latest_scan()

        self.assertIsInstance(scan, Scan)
        self.assertEqual((scan.kind, scan.code), ("batch", "B-24187"))

    def test_each_scan_is_received_once(self):
        self.scan("batch", "B-24187")
        first = scanner.read_new_scan(None)

        again = scanner.read_new_scan(first.scan_id)

        self.assertEqual(first.code, "B-24187")
        self.assertIsNone(again)

    def test_a_later_scan_is_received_as_new(self):
        self.scan("batch", "B-24187")
        first = scanner.read_new_scan(None)
        self.scan("dyestuff", "DYE-4471")

        later = scanner.read_new_scan(first.scan_id)

        self.assertEqual((later.kind, later.code), ("dyestuff", "DYE-4471"))


class UnavailableTests(LiveScannerTestCase):
    def test_unavailable_scanner_reports_an_error(self):
        set_mode(self.client, "scanner", "unavailable")

        with (
            self.assertLogs(LOGGER, "WARNING") as logs,
            self.assertRaises(ScannerUnavailable),
        ):
            scanner.read_latest_scan()

        self.assertIn("503", logs.output[0])
        self.assertIn("SCANNER_UNAVAILABLE", logs.output[0])

    def test_scan_attempt_while_unavailable_changes_nothing(self):
        set_mode(self.client, "scanner", "unavailable")
        self.assertEqual(self.scan("batch", "B-24187").status_code, 503)

        set_mode(self.client, "scanner", "ok")

        self.assertIsNone(scanner.read_latest_scan())

    def test_reads_resume_when_scanner_is_back(self):
        set_mode(self.client, "scanner", "unavailable")
        with self.assertLogs(LOGGER, "WARNING"), self.assertRaises(ScannerUnavailable):
            scanner.read_latest_scan()

        set_mode(self.client, "scanner", "ok")
        self.scan("batch", "B-24187")

        self.assertEqual(scanner.read_latest_scan().code, "B-24187")

    def test_unreachable_scanner_is_unavailable(self):
        with (
            override_settings(SCANNER_BASE_URL="http://127.0.0.1:9/api"),
            self.assertLogs(LOGGER, "WARNING"),
            self.assertRaises(ScannerUnavailable),
        ):
            scanner.read_latest_scan()
