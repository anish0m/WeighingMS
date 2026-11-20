"""Story 006-dummy-scanner-and-printer: Dummy Scanner."""

from django.test import TestCase

from dummy_orgatex.services import seed_training_scenario
from dummy_scanner.models import DummyScan
from tests.helpers import post_json

SCAN = "/api/training/scanner/scans"
LATEST = "/api/scanner/scans/latest"


class ScannerApiTests(TestCase):
    def setUp(self):
        seed_training_scenario()

    def test_no_scan_yet_returns_null(self):
        response = self.client.get(LATEST)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["scan"])

    def test_batch_scan_becomes_the_latest_scan(self):
        response = post_json(self.client, SCAN, {"kind": "batch", "code": "B-24187"})

        self.assertEqual(response.status_code, 201)
        scan = self.client.get(LATEST).json()["scan"]
        self.assertEqual(scan["kind"], "batch")
        self.assertEqual(scan["code"], "B-24187")
        self.assertEqual(scan["scanId"], response.json()["scanId"])

    def test_dyestuff_scan_replaces_the_previous_latest(self):
        post_json(self.client, SCAN, {"kind": "batch", "code": "B-24187"})

        post_json(self.client, SCAN, {"kind": "dyestuff", "code": "DYE-4471"})

        scan = self.client.get(LATEST).json()["scan"]
        self.assertEqual((scan["kind"], scan["code"]), ("dyestuff", "DYE-4471"))

    def test_status_is_ready(self):
        response = self.client.get("/api/scanner/status")

        self.assertEqual(response.json(), {"status": "ready"})

    def test_invalid_scans_return_400_and_store_nothing(self):
        cases = {
            "unknown kind": {"kind": "pallet", "code": "X"},
            "missing code": {"kind": "batch"},
            "blank code": {"kind": "batch", "code": "  "},
            "code too long": {"kind": "batch", "code": "B" * 65},
            "not an object": [],
        }
        for name, body in cases.items():
            with self.subTest(case=name):
                response = post_json(self.client, SCAN, body)

                self.assertEqual(response.status_code, 400)
                self.assertEqual(DummyScan.objects.count(), 0)

    def test_reseed_clears_scans(self):
        post_json(self.client, SCAN, {"kind": "batch", "code": "B-24187"})

        seed_training_scenario()

        self.assertIsNone(self.client.get(LATEST).json()["scan"])
