"""Story 007-dummy-failure-toggles: every Dummy can fail and recover."""

from django.test import TestCase

from dummy_orgatex.models import DummyConsumption
from dummy_orgatex.services import seed_training_scenario
from dummy_printer.models import DummyTicket
from dummy_scanner.models import DummyScan
from tests.helpers import post_json, set_mode

ORGATEX_ENDPOINTS = (
    "/api/batches",
    "/api/batches/B-24187",
    "/api/batches/B-24187/recipe",
    "/api/batches/B-24187/consumption",
)
CONSUMPTION = {
    "idempotencyKey": "K-mode",
    "components": [{"code": "DYE-4471", "actualQty": "94.2", "unit": "g"}],
}


class ModeListTests(TestCase):
    def setUp(self):
        seed_training_scenario()

    def test_all_dummies_start_ok(self):
        response = self.client.get("/api/training/modes")

        self.assertEqual(
            response.json()["modes"],
            {
                "orgatex": "ok",
                "scale-32kg": "ok",
                "scale-3kg": "ok",
                "scanner": "ok",
                "printer": "ok",
            },
        )

    def test_invalid_target_or_mode_returns_400(self):
        cases = (
            ("oven", "ok", "INVALID_TARGET"),
            ("orgatex", "broken", "INVALID_MODE"),
            ("scale-3kg", "unavailable", "INVALID_MODE"),
            ("printer", "unavailable", "INVALID_MODE"),
        )
        for target, mode, code in cases:
            with self.subTest(target=target, mode=mode):
                response = set_mode(self.client, target, mode)

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], code)

    def test_mode_change_requires_put(self):
        response = self.client.post("/api/training/modes/orgatex")

        self.assertEqual(response.status_code, 405)

    def test_reseed_resets_every_mode_to_ok(self):
        set_mode(self.client, "orgatex", "unavailable")
        set_mode(self.client, "scale-3kg", "disconnected")
        set_mode(self.client, "scanner", "unavailable")
        set_mode(self.client, "printer", "error")

        seed_training_scenario()

        modes = self.client.get("/api/training/modes").json()["modes"]
        self.assertEqual(set(modes.values()), {"ok"})


class OrgatexUnavailableTests(TestCase):
    def setUp(self):
        seed_training_scenario()

    def test_unavailable_returns_503_on_every_orgatex_endpoint(self):
        set_mode(self.client, "orgatex", "unavailable")

        for url in ORGATEX_ENDPOINTS:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 503)
                self.assertEqual(
                    response.json()["error"]["code"], "ORGATEX_UNAVAILABLE"
                )

    def test_unavailable_consumption_post_stores_nothing(self):
        set_mode(self.client, "orgatex", "unavailable")

        response = post_json(
            self.client, "/api/batches/B-24187/consumption", CONSUMPTION
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(DummyConsumption.objects.count(), 0)

    def test_back_to_ok_resumes_normal_responses(self):
        set_mode(self.client, "orgatex", "unavailable")

        set_mode(self.client, "orgatex", "ok")

        for url in ORGATEX_ENDPOINTS:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)


class ScaleDisconnectedTests(TestCase):
    def setUp(self):
        seed_training_scenario()

    def test_disconnected_scale_reports_status_and_no_weight(self):
        set_mode(self.client, "scale-3kg", "disconnected")

        status = self.client.get("/api/scales/scale-3kg/status")
        weight = self.client.get("/api/scales/scale-3kg/weight")

        self.assertEqual(status.json()["status"], "disconnected")
        self.assertEqual(weight.status_code, 503)
        self.assertEqual(weight.json()["error"]["code"], "SCALE_DISCONNECTED")
        self.assertNotIn("netWeight", weight.json())

    def test_disconnected_scale_refuses_tare_and_simulate(self):
        set_mode(self.client, "scale-3kg", "disconnected")

        tare = self.client.post("/api/scales/scale-3kg/tare")
        simulate = post_json(
            self.client,
            "/api/training/scales/scale-3kg/simulate",
            {"action": "set", "weight": "94.0", "unit": "g"},
        )

        self.assertEqual(tare.status_code, 503)
        self.assertEqual(simulate.status_code, 503)

    def test_other_scale_is_unaffected(self):
        set_mode(self.client, "scale-3kg", "disconnected")

        response = self.client.get("/api/scales/scale-32kg/weight")

        self.assertEqual(response.status_code, 200)

    def test_back_to_ok_resumes_readings(self):
        set_mode(self.client, "scale-3kg", "disconnected")

        set_mode(self.client, "scale-3kg", "ok")

        self.assertEqual(
            self.client.get("/api/scales/scale-3kg/weight").status_code, 200
        )
        status = self.client.get("/api/scales/scale-3kg/status").json()["status"]
        self.assertEqual(status, "ready")


class ScannerUnavailableTests(TestCase):
    def setUp(self):
        seed_training_scenario()

    def test_unavailable_scan_returns_error_and_stores_nothing(self):
        set_mode(self.client, "scanner", "unavailable")

        response = post_json(
            self.client,
            "/api/training/scanner/scans",
            {"kind": "batch", "code": "B-24187"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "SCANNER_UNAVAILABLE")
        self.assertEqual(DummyScan.objects.count(), 0)
        self.assertEqual(self.client.get("/api/scanner/scans/latest").status_code, 503)
        status = self.client.get("/api/scanner/status").json()["status"]
        self.assertEqual(status, "unavailable")

    def test_back_to_ok_resumes_scanning(self):
        set_mode(self.client, "scanner", "unavailable")

        set_mode(self.client, "scanner", "ok")

        response = post_json(
            self.client,
            "/api/training/scanner/scans",
            {"kind": "batch", "code": "B-24187"},
        )
        self.assertEqual(response.status_code, 201)


class PrinterErrorTests(TestCase):
    def setUp(self):
        seed_training_scenario()

    def test_error_print_returns_error_and_stores_nothing(self):
        set_mode(self.client, "printer", "error")

        response = post_json(self.client, "/api/tickets", {"content": "TICKET"})

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "PRINTER_ERROR")
        self.assertEqual(DummyTicket.objects.count(), 0)
        status = self.client.get("/api/printer/status").json()["status"]
        self.assertEqual(status, "error")

    def test_back_to_ok_resumes_printing(self):
        set_mode(self.client, "printer", "error")

        set_mode(self.client, "printer", "ok")

        response = post_json(self.client, "/api/tickets", {"content": "TICKET"})
        self.assertEqual(response.status_code, 201)
