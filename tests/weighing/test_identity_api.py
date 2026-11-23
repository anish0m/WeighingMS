"""Stories 004 and 005 over HTTP: component headers and the dyestuff-scan endpoint.

``GET /station/api/sessions/<id>/components`` and
``POST /station/api/sessions/<id>/components/<seq>/identity`` (ADR-002, ADR-006).
The POST tests run against the live Dummy Scanner (training contract).
"""

from django.test import Client, LiveServerTestCase, TestCase, override_settings

from dummy_orgatex.services import seed_training_scenario
from tests.helpers import post_json, put_json, set_mode
from tests.weighing import factories
from weighing.models import IdentityCheck, IdentityResult, Operator

YELLOW = factories.YELLOW_RGB
R_KARIM = {
    "operatorId": "OP-01",
    "name": "R. Karim",
    "shift": "A",
    "display": "R. Karim · Shift A",
}


def components_url(session_id):
    return f"/station/api/sessions/{session_id}/components"


def identity_url(session_id, sequence=YELLOW):
    return f"/station/api/sessions/{session_id}/components/{sequence}/identity"


class ErrorAssertions:
    def assert_error(self, response, status, code, message=None):
        self.assertEqual(response.status_code, status)
        error = response.json()["error"]
        self.assertEqual(error["code"], code)
        if message is not None:
            self.assertEqual(error["message"], message)


class ComponentsApiTests(ErrorAssertions, TestCase):
    def setUp(self):
        self.session = factories.session()

    def components(self):
        response = self.client.get(components_url(self.session.pk))
        self.assertEqual(response.status_code, 200)
        return {c["sequence"]: c for c in response.json()["components"]}

    def test_lists_the_five_components_in_sequence(self):
        body = self.client.get(components_url(self.session.pk)).json()

        self.assertEqual(body["sessionId"], self.session.pk)
        self.assertEqual(body["batchId"], "B-24187")
        self.assertEqual([c["sequence"] for c in body["components"]], [1, 2, 3, 4, 5])

    def test_yellow_rgb_component(self):
        """Story 005 AC 1; story 004 AC 3 (not verified → not ready)."""
        self.assertEqual(
            self.components()[YELLOW],
            {
                "sequence": 3,
                "code": "DYE-4471",
                "name": "Remazol Yellow RGB",
                "lot": "2026-0387",
                "container": "C-12",
                "tare": "214.0000",
                "unit": "g",
                "tareText": "214 g",
                "header": "Remazol Yellow RGB · DYE-4471 · LOT 2026-0387"
                " · CONTAINER C-12 · TARE 214 g",
                "identity": {
                    "status": "unverified",
                    "scannedCode": None,
                    "checkedAt": None,
                },
                "materialReady": False,
                "materialRefusal": {
                    "code": "IDENTITY_NOT_VERIFIED",
                    "message": "Scan the dyestuff first",
                },
                # Weighing rules, bolt 009 (tested in test_rules_api).
                "target": "94.0000",
                "targetText": "94.0 g",
                "scale": {
                    "scaleId": "scale-3kg",
                    "label": "3 kg precision",
                    "unit": "g",
                    "mode": "automatic",
                },
                "tolerance": {
                    "tolerance": "0.5000",
                    "low": "93.5000",
                    "high": "94.5000",
                    "nearFrom": "84.6000",
                    "caption": "TOLERANCE ±0.5 g (93.5 – 94.5)",
                },
            },
        )

    def test_sodium_sulphate_shows_d03_and_1850_kg(self):
        """Story 005 AC 3."""
        sodium = self.components()[factories.SODIUM_SULPHATE]

        self.assertEqual(sodium["container"], "D-03")
        self.assertEqual((sodium["tare"], sodium["tareText"]), ("1.8500", "1.850 kg"))

    def test_verified_component_is_ready(self):
        IdentityCheck.objects.create(
            session=self.session,
            component_sequence=YELLOW,
            expected_code="DYE-4471",
            scan_id=1,
            scanned_code="DYE-4471",
            result=IdentityResult.VERIFIED,
            operator=self.session.operator,
        )

        yellow = self.components()[YELLOW]

        self.assertEqual(yellow["identity"]["status"], "verified")
        self.assertEqual(yellow["identity"]["scannedCode"], "DYE-4471")
        self.assertTrue(yellow["materialReady"])
        self.assertIsNone(yellow["materialRefusal"])

    def test_wrong_dyestuff_is_shown(self):
        """Story 004 AC 2: "Wrong dyestuff", confirmation stays blocked."""
        IdentityCheck.objects.create(
            session=self.session,
            component_sequence=YELLOW,
            expected_code="DYE-4471",
            scan_id=1,
            scanned_code="DYE-2204",
            result=IdentityResult.WRONG_DYESTUFF,
            operator=self.session.operator,
        )

        yellow = self.components()[YELLOW]

        self.assertEqual(yellow["identity"]["status"], "wrong_dyestuff")
        self.assertFalse(yellow["materialReady"])
        self.assertEqual(
            yellow["materialRefusal"],
            {"code": "WRONG_DYESTUFF", "message": "Wrong dyestuff"},
        )

    def test_missing_lot_is_reported(self):
        """Story 005 AC 2."""
        self.session.state = "complete"
        self.session.save()
        session = factories.session(factories.teal_selection({YELLOW: {"lot": ""}}))

        yellow = {
            c["sequence"]: c
            for c in self.client.get(components_url(session.pk)).json()["components"]
        }[YELLOW]

        self.assertIn("LOT — ·", yellow["header"])
        self.assertEqual(yellow["materialRefusal"]["code"], "LOT_MISSING")

    def test_no_operator_is_needed_to_read(self):
        self.assertEqual(
            self.client.get(components_url(self.session.pk)).status_code, 200
        )

    def test_unknown_session_is_404(self):
        self.assert_error(
            self.client.get(components_url(999)),
            404,
            "SESSION_NOT_FOUND",
            "Weighing session not found",
        )


class IdentityApiValidationTests(ErrorAssertions, TestCase):
    """Requests refused before the scanner is read."""

    def setUp(self):
        self.session = factories.session()
        put_json(self.client, "/station/api/operator", {"operatorId": "OP-01"})

    def test_invalid_scan_ids_are_400(self):
        for body in (
            {},
            {"scanId": "7"},
            {"scanId": 0},
            {"scanId": -1},
            {"scanId": True},
            {"scanId": 1.5},
            "[]",
            "not json",
        ):
            with self.subTest(body=body):
                response = post_json(self.client, identity_url(self.session.pk), body)
                self.assert_error(response, 400, "INVALID_REQUEST")
        self.assertEqual(IdentityCheck.objects.count(), 0)

    def test_no_operator_is_403(self):
        """FR-19a / ADR-005: nothing is checked or stored without an operator."""
        self.client.delete("/station/api/operator")

        with self.assertLogs("weighing.services", "INFO"):
            response = post_json(
                self.client, identity_url(self.session.pk), {"scanId": 1}
            )

        self.assert_error(
            response, 403, "OPERATOR_REQUIRED", "Choose an operator first"
        )
        self.assertEqual(IdentityCheck.objects.count(), 0)

    def test_unknown_session_is_404(self):
        response = post_json(self.client, identity_url(999), {"scanId": 1})

        self.assert_error(response, 404, "SESSION_NOT_FOUND")

    def test_unknown_component_is_404(self):
        with self.assertLogs("weighing.identity", "INFO"):
            response = post_json(
                self.client, identity_url(self.session.pk, 9), {"scanId": 1}
            )

        self.assert_error(response, 404, "COMPONENT_NOT_FOUND", "Component not found")

    def test_other_methods_are_405(self):
        for method in ("get", "put", "patch", "delete"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(identity_url(self.session.pk))
                self.assertEqual(response.status_code, 405)
        for method in ("post", "put", "patch", "delete"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(components_url(self.session.pk))
                self.assertEqual(response.status_code, 405)

    def test_posting_without_csrf_token_is_rejected(self):
        csrf_client = Client(enforce_csrf_checks=True)
        put_json(csrf_client, "/station/api/operator", {"operatorId": "OP-01"})

        response = post_json(csrf_client, identity_url(self.session.pk), {"scanId": 1})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(IdentityCheck.objects.count(), 0)


class IdentityApiLiveTests(ErrorAssertions, LiveServerTestCase):
    def setUp(self):
        seed_training_scenario()
        Operator.objects.get_or_create(
            operator_id="OP-01", defaults={"name": "R. Karim", "shift": "A"}
        )
        self.enterContext(
            override_settings(SCANNER_BASE_URL=f"{self.live_server_url}/api")
        )
        self.session = factories.session()
        put_json(self.client, "/station/api/operator", {"operatorId": "OP-01"})

    def scan(self, code, kind="dyestuff"):
        response = post_json(
            self.client, "/api/training/scanner/scans", {"kind": kind, "code": code}
        )
        return response.json()["scanId"]

    def post(self, scan_id, body=None):
        return post_json(
            self.client, identity_url(self.session.pk), body or {"scanId": scan_id}
        )

    def test_matching_scan_is_201_verified(self):
        """Story 004 AC 1."""
        scan_id = self.scan("DYE-4471")

        response = self.post(scan_id)

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(
            {k: body[k] for k in body if k not in ("checkId", "checkedAt")},
            {
                "sessionId": self.session.pk,
                "sequence": YELLOW,
                "scanId": scan_id,
                "expectedCode": "DYE-4471",
                "scannedCode": "DYE-4471",
                "result": "verified",
                "message": "Dyestuff verified",
                "operator": R_KARIM,
            },
        )

    def test_other_code_is_201_wrong_dyestuff(self):
        """Story 004 AC 2."""
        response = self.post(self.scan("DYE-2204"))

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["result"], "wrong_dyestuff")
        self.assertEqual(response.json()["message"], "Wrong dyestuff")
        yellow = self.client.get(components_url(self.session.pk)).json()["components"][
            YELLOW - 1
        ]
        self.assertFalse(yellow["materialReady"])

    def test_code_in_the_body_is_ignored(self):
        """ADR-006: only the scanner's code counts."""
        response = self.post(
            None, {"scanId": self.scan("DYE-2204"), "code": "DYE-4471"}
        )

        self.assertEqual(response.json()["scannedCode"], "DYE-2204")
        self.assertEqual(response.json()["result"], "wrong_dyestuff")

    def test_resending_a_scan_is_200_with_the_first_check(self):
        scan_id = self.scan("DYE-4471")
        first = self.post(scan_id).json()

        again = self.post(scan_id)

        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json()["checkId"], first["checkId"])
        self.assertEqual(IdentityCheck.objects.count(), 1)

    def test_batch_scan_is_409(self):
        response = self.post(self.scan("B-24187", kind="batch"))

        self.assert_error(response, 409, "NOT_A_DYESTUFF_SCAN", "Scan a dyestuff code")

    def test_stale_scan_is_409(self):
        older = self.scan("DYE-4471")
        self.scan("DYE-2204")

        self.assert_error(self.post(older), 409, "SCAN_NOT_CURRENT", "Scan again")
        self.assertEqual(IdentityCheck.objects.count(), 0)

    def test_unavailable_scanner_is_503(self):
        scan_id = self.scan("DYE-4471")
        set_mode(self.client, "scanner", "unavailable")

        response = self.post(scan_id)

        self.assert_error(response, 503, "SCANNER_UNAVAILABLE", "Scanner unavailable")
        self.assertEqual(IdentityCheck.objects.count(), 0)
