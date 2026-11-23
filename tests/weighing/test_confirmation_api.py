"""Stories 003, 006, 008 and 010 over HTTP (bolt 010 endpoints, ADR-002).

``/station/api/current-session``, ``…/sessions/<id>/progress`` and the
``…/components/<seq>/activate|tare|quit|confirm`` POSTs, against the live
Dummy Scale and Scanner (training contracts).
"""

from django.test import Client, TestCase

from tests.helpers import post_json, put_json
from tests.weighing import factories
from tests.weighing.flow import BLUE, TEAL, YELLOW, LiveFlowTestCase
from weighing.models import ComponentAttempt, WeighingRecord

R_KARIM = {
    "operatorId": "OP-01",
    "name": "R. Karim",
    "shift": "A",
    "display": "R. Karim · Shift A",
}
ACTIONS = ("activate", "tare", "quit", "confirm")


def action_url(session_id, sequence, action):
    return f"/station/api/sessions/{session_id}/components/{sequence}/{action}"


class ErrorAssertions:
    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.content)
        self.assertEqual(response.json()["error"]["code"], code)


class FlowApiTestCase(ErrorAssertions, LiveFlowTestCase):
    def setUp(self):
        super().setUp()
        put_json(self.client, "/station/api/operator", {"operatorId": "OP-01"})

    def post(self, sequence, action, body=None, client=None):
        return post_json(
            client or self.client,
            action_url(self.session.pk, sequence, action),
            body or {},
        )

    def ready(self, sequence, weight=None):
        self.assertEqual(self.post(sequence, "activate").status_code, 200)
        self.verify(sequence)
        self.set_weight(sequence, weight or TEAL[sequence][3])


class ProgressApiTests(FlowApiTestCase):
    def test_progress_before_activation(self):
        response = self.client.get(f"/station/api/sessions/{self.session.pk}/progress")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(
            {k: body[k] for k in body if k != "components"},
            {
                "sessionId": self.session.pk,
                "batchId": "B-24187",
                "state": "in_progress",
                "weighed": 0,
                "total": 5,
                "progressText": "0 of 5 components weighed",
                "active": None,
                "nextPending": 1,
            },
        )
        self.assertEqual(
            body["components"][3],
            {
                "sequence": 4,
                "state": "pending",
                "actualWeight": None,
                "unit": "kg",
                "actualText": None,
                "recordId": None,
            },
        )

    def test_activate_returns_the_active_tared_component(self):
        body = self.post(YELLOW, "activate").json()

        active = body["active"]
        self.assertEqual(
            {k: active[k] for k in ("sequence", "scaleId", "tared")},
            {"sequence": 3, "scaleId": "scale-3kg", "tared": True},
        )
        self.assertEqual(body["nextPending"], YELLOW)
        self.assertEqual(body["components"][2]["state"], "active")

    def test_quit_returns_an_untared_restart(self):
        self.post(YELLOW, "activate")

        body = self.post(YELLOW, "quit").json()

        self.assertEqual(body["active"]["sequence"], YELLOW)
        self.assertFalse(body["active"]["tared"])

    def test_tare_returns_a_tared_attempt(self):
        self.post(YELLOW, "activate")
        self.post(YELLOW, "quit")

        body = self.post(YELLOW, "tare").json()

        self.assertTrue(body["active"]["tared"])

    def test_tare_on_a_disconnected_scale_is_503(self):
        self.post(YELLOW, "activate")
        self.scale_mode("scale-3kg", "disconnected")

        with self.assertLogs("weighing.progression", "INFO"):
            response = self.post(YELLOW, "tare")

        self.assert_error(response, 503, "SCALE_DISCONNECTED")


class ConfirmApiTests(FlowApiTestCase):
    def test_confirm_is_201_with_the_record_and_the_progress(self):
        """Story 006 AC 1 over HTTP."""
        self.ready(YELLOW, "94.2")

        response = self.post(YELLOW, "confirm")

        self.assertEqual(response.status_code, 201)
        record = response.json()["record"]
        self.assertEqual(
            {k: record[k] for k in record if k not in ("recordId", "recordedAt")},
            {
                "sessionId": self.session.pk,
                "batchId": "B-24187",
                "sequence": 3,
                "componentCode": "DYE-4471",
                "componentName": "Remazol Yellow RGB",
                "actualWeight": "94.2",
                "unit": "g",
                "actualText": "94.2 g",
                "lot": "2026-0387",
                "container": "C-12",
                "tare": "214.0000",
                "tareText": "214 g",
                "scaleId": "scale-3kg",
                "target": "94.0000",
                "toleranceMin": "93.5000",
                "toleranceMax": "94.5000",
                "result": "within",
                "operator": R_KARIM,
            },
        )
        self.assertTrue(record["recordedAt"].endswith("+00:00"))
        progress = response.json()["progress"]
        self.assertEqual(progress["progressText"], "1 of 5 components weighed")
        self.assertEqual(
            progress["components"][2],
            {
                "sequence": 3,
                "state": "done",
                "actualWeight": "94.2",
                "unit": "g",
                "actualText": "94.2 g",
                "recordId": record["recordId"],
            },
        )

    def test_a_weight_in_the_body_is_ignored(self):
        """The server reads the scale itself (ADR-008, FR-13b)."""
        self.ready(YELLOW, "94.2")

        response = self.post(YELLOW, "confirm", {"actualWeight": "94.0"})

        self.assertEqual(response.json()["record"]["actualWeight"], "94.2")

    def test_out_of_tolerance_is_409_with_the_measured_weight(self):
        self.ready(YELLOW, "94.6")

        with self.assertLogs("weighing.confirmation", "INFO"):
            response = self.post(YELLOW, "confirm")

        self.assert_error(response, 409, "OUT_OF_TOLERANCE")
        self.assertEqual(
            response.json()["error"],
            {
                "code": "OUT_OF_TOLERANCE",
                "message": "Weight is not within tolerance",
                "detail": {
                    "net": "94.6",
                    "unit": "g",
                    "zone": "over",
                    "surplus": "0.6",
                    "surplusPercent": "0.6",
                    "surplusText": "0.6 g",
                },
            },
        )
        self.assertFalse(WeighingRecord.objects.exists())

    def test_precondition_refusals(self):
        self.post(YELLOW, "activate")
        self.set_weight(YELLOW, "94.0")
        with self.assertLogs("weighing.confirmation", "INFO"):
            self.assert_error(
                self.post(YELLOW, "confirm"), 409, "IDENTITY_NOT_VERIFIED"
            )
            self.post(YELLOW, "quit")
            self.assert_error(self.post(YELLOW, "confirm"), 409, "TARE_REQUIRED")
            self.assert_error(self.post(BLUE, "confirm"), 409, "COMPONENT_NOT_ACTIVE")
        self.assertFalse(WeighingRecord.objects.exists())

    def test_disconnected_scale_is_503(self):
        self.ready(YELLOW)
        self.scale_mode("scale-3kg", "disconnected")

        with self.assertLogs("weighing.confirmation", "INFO"):
            response = self.post(YELLOW, "confirm")

        self.assert_error(response, 503, "SCALE_DISCONNECTED")

    def test_double_confirm_is_409_component_done(self):
        self.ready(YELLOW)
        self.assertEqual(self.post(YELLOW, "confirm").status_code, 201)

        with self.assertLogs("weighing.confirmation", "INFO"):
            response = self.post(YELLOW, "confirm")

        self.assert_error(response, 409, "COMPONENT_DONE")
        self.assertEqual(WeighingRecord.objects.count(), 1)

    def test_touching_a_done_component_is_409_and_changes_nothing(self):
        self.ready(YELLOW)
        self.post(YELLOW, "confirm")
        attempts = ComponentAttempt.objects.count()

        with self.assertLogs("weighing.progression", "INFO"):
            response = self.post(YELLOW, "activate")

        self.assert_error(response, 409, "COMPONENT_DONE")
        self.assertEqual(ComponentAttempt.objects.count(), attempts)

    def test_confirm_without_csrf_token_is_rejected(self):
        self.ready(YELLOW)
        csrf_client = Client(enforce_csrf_checks=True)
        put_json(csrf_client, "/station/api/operator", {"operatorId": "OP-01"})

        response = self.post(YELLOW, "confirm", client=csrf_client)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(WeighingRecord.objects.exists())


class ResumeApiTests(FlowApiTestCase):
    def test_reload_resumes_with_both_confirmations(self):
        """Story 010 AC 1 over HTTP: the page reload reads current-session."""
        self.post(BLUE, "activate")
        for sequence in (1, 2):
            self.verify(sequence)
            self.set_weight(sequence, TEAL[sequence][3])
            self.assertEqual(self.post(sequence, "confirm").status_code, 201)

        session = Client().get("/station/api/current-session").json()["session"]

        self.assertEqual(session["sessionId"], self.session.pk)
        self.assertEqual(session["progressText"], "2 of 5 components weighed")
        self.assertEqual(session["active"]["sequence"], YELLOW)
        self.assertEqual(
            [c["actualText"] for c in session["components"]],
            ["1241.5 g", "385.4 g", None, None, None],
        )


class EndpointRulesTests(ErrorAssertions, TestCase):
    """Requests refused before any scale call."""

    def setUp(self):
        self.session = factories.session()

    def test_no_current_session(self):
        self.session.state = "complete"
        self.session.save()

        response = self.client.get("/station/api/current-session")

        self.assertEqual(response.json(), {"session": None})

    def test_actions_need_an_operator(self):
        for action in ACTIONS:
            with self.subTest(action=action), self.assertLogs("weighing.services"):
                response = post_json(
                    self.client, action_url(self.session.pk, YELLOW, action), {}
                )
                self.assert_error(response, 403, "OPERATOR_REQUIRED")
        self.assertFalse(ComponentAttempt.objects.exists())

    def test_unknown_session_and_component_are_404(self):
        put_json(self.client, "/station/api/operator", {"operatorId": "OP-01"})
        self.assert_error(
            self.client.get("/station/api/sessions/999/progress"),
            404,
            "SESSION_NOT_FOUND",
        )
        for action in ACTIONS:
            with self.subTest(action=action):
                self.assert_error(
                    post_json(self.client, action_url(999, YELLOW, action), {}),
                    404,
                    "SESSION_NOT_FOUND",
                )
                with self.assertLogs("weighing.identity", "INFO"):
                    response = post_json(
                        self.client, action_url(self.session.pk, 9, action), {}
                    )
                self.assert_error(response, 404, "COMPONENT_NOT_FOUND")

    def test_other_methods_are_405(self):
        for action in ACTIONS:
            for method in ("get", "put", "patch", "delete"):
                with self.subTest(action=action, method=method):
                    response = getattr(self.client, method)(
                        action_url(self.session.pk, YELLOW, action)
                    )
                    self.assertEqual(response.status_code, 405)
        for url in (
            "/station/api/current-session",
            f"/station/api/sessions/{self.session.pk}/progress",
        ):
            for method in ("post", "put", "patch", "delete"):
                with self.subTest(url=url, method=method):
                    self.assertEqual(getattr(self.client, method)(url).status_code, 405)
