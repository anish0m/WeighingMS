"""Story 001-identify-operator: the station identity and session API.

``/station/api/operators``, ``/operator`` and ``/sessions`` (ADR-002). The
current operator lives in the server-side session (ADR-005); the test client
keeps the session cookie between requests like the station browser does.
"""

import json

from django.test import Client, TestCase

from tests.helpers import post_json, put_json
from tests.weighing import factories
from weighing.models import WeighingSession

OPERATORS = "/station/api/operators"
OPERATOR = "/station/api/operator"
SESSIONS = "/station/api/sessions"
R_KARIM = {
    "operatorId": "OP-01",
    "name": "R. Karim",
    "shift": "A",
    "display": "R. Karim · Shift A",
}


class ApiTestCase(TestCase):
    def choose(self, operator_id="OP-01"):
        return put_json(self.client, OPERATOR, {"operatorId": operator_id})

    def start(self, selection_id):
        return post_json(self.client, SESSIONS, {"selectionId": selection_id})

    def assert_error(self, response, status, code, message=None):
        self.assertEqual(response.status_code, status)
        error = response.json()["error"]
        self.assertEqual(error["code"], code)
        if message is not None:
            self.assertEqual(error["message"], message)


class OperatorApiTests(ApiTestCase):
    def test_operator_list_holds_r_karim(self):
        response = self.client.get(OPERATORS)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"operators": [R_KARIM]})

    def test_station_starts_without_an_operator(self):
        self.assertEqual(self.client.get(OPERATOR).json(), {"operator": None})

    def test_choosing_r_karim_gives_the_header_text(self):
        response = self.choose()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"operator": R_KARIM})
        header = "Operator " + self.client.get(OPERATOR).json()["operator"]["display"]
        self.assertEqual(header, "Operator R. Karim · Shift A")

    def test_operator_stays_chosen_across_requests(self):
        self.choose()

        for _ in range(3):
            self.assertEqual(self.client.get(OPERATOR).json()["operator"], R_KARIM)

    def test_operator_is_per_browser_session(self):
        self.choose()

        self.assertIsNone(Client().get(OPERATOR).json()["operator"])

    def test_unknown_operator_is_404_and_keeps_the_earlier_choice(self):
        self.choose()

        self.assert_error(
            self.choose("OP-99"), 404, "OPERATOR_NOT_FOUND", "Operator not found"
        )
        self.assertEqual(self.client.get(OPERATOR).json()["operator"], R_KARIM)

    def test_clearing_the_operator(self):
        self.choose()

        response = self.client.delete(OPERATOR)

        self.assertEqual(response.status_code, 204)
        self.assertIsNone(self.client.get(OPERATOR).json()["operator"])

    def test_invalid_choices_are_400(self):
        cases = {
            "not json": "{operatorId",
            "array": "[]",
            "missing": json.dumps({}),
            "blank": json.dumps({"operatorId": "  "}),
            "number": json.dumps({"operatorId": 1}),
            "too long": json.dumps({"operatorId": "O" * 17}),
        }
        for name, data in cases.items():
            with self.subTest(case=name):
                response = self.client.put(
                    OPERATOR, data, content_type="application/json"
                )
                self.assert_error(response, 400, "INVALID_REQUEST")


class SessionApiTests(ApiTestCase):
    def setUp(self):
        self.selection = factories.selection()

    def test_weighing_without_an_operator_is_refused(self):
        self.assert_error(
            self.start(self.selection.pk),
            403,
            "OPERATOR_REQUIRED",
            "Choose an operator first",
        )
        self.assertEqual(WeighingSession.objects.count(), 0)

    def test_weighing_after_clearing_the_operator_is_refused(self):
        self.choose()
        self.client.delete(OPERATOR)

        self.assert_error(self.start(self.selection.pk), 403, "OPERATOR_REQUIRED")

    def test_session_starts_with_the_chosen_operator(self):
        self.choose()

        response = self.start(self.selection.pk)

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["selectionId"], self.selection.pk)
        self.assertEqual(body["batchId"], "B-24187")
        self.assertEqual(body["state"], "in_progress")
        self.assertEqual(body["operator"], R_KARIM)
        self.assertIsNone(body["completedAt"])

    def test_operator_in_the_body_is_ignored(self):
        response = post_json(
            self.client,
            SESSIONS,
            {"selectionId": self.selection.pk, "operatorId": "OP-01"},
        )

        self.assert_error(response, 403, "OPERATOR_REQUIRED")

    def test_starting_again_returns_the_open_session_with_200(self):
        self.choose()
        first = self.start(self.selection.pk).json()

        response = self.start(self.selection.pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), first)

    def test_unknown_selection_is_404(self):
        self.choose()

        self.assert_error(
            self.start(999999),
            404,
            "SELECTION_NOT_FOUND",
            "Batch selection not found",
        )

    def test_invalid_selection_ids_are_400(self):
        self.choose()
        for value in (None, "1", 0, -1, 1.5, True):
            with self.subTest(selectionId=value):
                self.assert_error(self.start(value), 400, "INVALID_REQUEST")
        self.assertEqual(WeighingSession.objects.count(), 0)

    def test_get_returns_the_session(self):
        self.choose()
        created = self.start(self.selection.pk).json()

        response = self.client.get(f"{SESSIONS}/{created['sessionId']}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), created)

    def test_unknown_session_is_404(self):
        self.assert_error(
            self.client.get(f"{SESSIONS}/999999"), 404, "SESSION_NOT_FOUND"
        )


class MethodTests(ApiTestCase):
    def test_other_methods_are_405(self):
        cases = {
            OPERATORS: ("post", "put", "patch", "delete"),
            OPERATOR: ("post", "patch"),
            SESSIONS: ("get", "put", "patch", "delete"),
            f"{SESSIONS}/1": ("post", "put", "patch", "delete"),
        }
        for url, methods in cases.items():
            for method in methods:
                with self.subTest(url=url, method=method):
                    response = getattr(self.client, method)(url)
                    self.assertEqual(response.status_code, 405)


class CsrfTests(ApiTestCase):
    def setUp(self):
        self.csrf_client = Client(enforce_csrf_checks=True)

    def test_choosing_without_csrf_token_is_rejected(self):
        response = put_json(self.csrf_client, OPERATOR, {"operatorId": "OP-01"})

        self.assertEqual(response.status_code, 403)
        self.assertIsNone(self.csrf_client.get(OPERATOR).json()["operator"])

    def test_starting_without_csrf_token_is_rejected(self):
        selection = factories.selection()

        response = post_json(self.csrf_client, SESSIONS, {"selectionId": selection.pk})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(WeighingSession.objects.count(), 0)
