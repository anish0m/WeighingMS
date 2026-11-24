"""Bolt 014 over HTTP: ``/station/api/sessions/<id>/write-back[/result]``.

B-24187 is weighed 5 of 5 through the real flow (Dummy Scale and Scanner);
the consumption is posted to the live Dummy OrgaTEX as the browser would,
then reported back. Stories 002 and 003 (FR-17, NFR-7).
"""

from decimal import Decimal

from django.test import Client, override_settings

from tests.helpers import post_json, put_json, set_mode
from tests.weighing.flow import BLUE, TEAL
from tests.weighing.test_confirmation_api import FlowApiTestCase
from weighing.models import WeighingRecord

EXPECTED_COMPONENTS = [
    {"code": "DYE-1180", "actualQty": "1241.5", "unit": "g"},
    {"code": "DYE-2204", "actualQty": "385.4", "unit": "g"},
    {"code": "DYE-4471", "actualQty": "94.2", "unit": "g"},
    {"code": "AUX-0101", "actualQty": "24.048", "unit": "kg"},
    {"code": "AUX-0107", "actualQty": "9.612", "unit": "kg"},
]


class WriteBackApiTestCase(FlowApiTestCase):
    def setUp(self):
        super().setUp()
        self.enterContext(override_settings(ORGATEX_BASE_URL=self.api))
        self.url = f"/station/api/sessions/{self.session.pk}/write-back"

    def weigh(self, count=5):
        self.post(BLUE, "activate")
        for sequence in range(1, count + 1):
            self.verify(sequence)
            self.set_weight(sequence, TEAL[sequence][3])
            self.assertEqual(self.post(sequence, "confirm").status_code, 201)

    def start(self, client=None):
        return post_json(client or self.client, self.url, {})

    def report(self, posted, reason="", client=None):
        return post_json(
            client or self.client,
            self.url + "/result",
            {"posted": posted, "reason": reason},
        )

    def post_to_orgatex(self, started):
        return post_json(
            self.client,
            f"/api/batches/{started['batchId']}/consumption",
            started["body"],
        )

    def consumptions(self):
        return self.client.get("/api/batches/B-24187/consumption").json()[
            "consumptions"
        ]


class WriteBackFlowTests(WriteBackApiTestCase):
    def setUp(self):
        super().setUp()
        self.weigh()

    def test_completion_leaves_a_pending_write_back_before_the_first_start(self):
        """Bolt 015 (ADR-013): the 5th confirm opens the write-back, 0 attempts."""
        response = Client().get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["writeBack"],
            {
                "status": "pending",
                "idempotencyKey": f"WMS-B-24187-S{self.session.pk}",
                "attempts": 0,
                "confirmedAt": None,
                "reason": None,
                "operatorId": "OP-01",
            },
        )

    def test_start_returns_key_and_body_with_every_actual(self):
        """Story 002 AC 1."""
        response = self.start()

        self.assertEqual(response.status_code, 200)
        data = response.json()
        key = f"WMS-B-24187-S{self.session.pk}"
        self.assertEqual(data["batchId"], "B-24187")
        self.assertEqual(
            data["body"], {"idempotencyKey": key, "components": EXPECTED_COMPONENTS}
        )
        self.assertEqual(
            data["writeBack"],
            {
                "status": "pending",
                "idempotencyKey": key,
                "attempts": 1,
                "confirmedAt": None,
                "reason": None,
                "operatorId": "OP-01",
            },
        )

    def test_one_post_creates_one_consumption_and_is_confirmed(self):
        """Story 002 AC 1 + AC 3."""
        started = self.start().json()
        accepted = self.post_to_orgatex(started).json()["acceptedAt"]

        result = self.report(True).json()["writeBack"]

        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(result["confirmedAt"], accepted)
        stored = self.consumptions()
        self.assertEqual(len(stored), 1)
        self.assertEqual(
            [
                (c["code"], Decimal(c["actualQty"]), c["unit"])
                for c in stored[0]["components"]
            ],
            [
                (c["code"], Decimal(c["actualQty"]), c["unit"])
                for c in EXPECTED_COMPONENTS
            ],
        )
        self.assertEqual(Client().get(self.url).json()["writeBack"], result)

    def test_triggering_again_keeps_one_consumption(self):
        """Story 002 AC 2."""
        first = self.start().json()
        self.post_to_orgatex(first)
        self.report(True)

        again = self.start().json()
        response = self.post_to_orgatex(again)

        self.assertEqual(again["body"], first["body"])
        self.assertEqual(again["writeBack"]["status"], "confirmed")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.consumptions()), 1)

    def test_unavailable_orgatex_is_not_written_and_records_stay(self):
        """Story 003 AC 1."""
        started = self.start().json()
        set_mode(self.client, "orgatex", "unavailable")
        self.assertEqual(self.post_to_orgatex(started).status_code, 503)

        result = self.report(False, "OrgaTEX unavailable").json()["writeBack"]

        self.assertEqual(result["status"], "not_written")
        self.assertEqual(result["reason"], "OrgaTEX unavailable")
        self.assertIsNone(result["confirmedAt"])
        self.assertEqual(
            [str(r.actual_weight) for r in WeighingRecord.objects.order_by("pk")],
            ["1241.5000", "385.4000", "94.2000", "24.0480", "9.6120"],
        )

    def test_retry_with_the_same_key_confirms(self):
        """Story 003 AC 2."""
        set_mode(self.client, "orgatex", "unavailable")
        first = self.start().json()
        self.post_to_orgatex(first)
        self.report(False, "OrgaTEX unavailable")
        set_mode(self.client, "orgatex", "ok")

        retry = self.start().json()
        self.post_to_orgatex(retry)
        result = self.report(True).json()["writeBack"]

        self.assertEqual(
            retry["body"]["idempotencyKey"], first["body"]["idempotencyKey"]
        )
        self.assertEqual(result["status"], "confirmed")
        self.assertIsNotNone(result["confirmedAt"])
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(len(self.consumptions()), 1)

    def test_ambiguous_failure_creates_no_duplicate(self):
        """Story 003 AC 3: stored, but the browser saw a timeout."""
        started = self.start().json()
        self.post_to_orgatex(started)

        result = self.report(False, "OrgaTEX unavailable").json()["writeBack"]
        self.start()
        self.post_to_orgatex(started)

        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(len(self.consumptions()), 1)

    def test_posted_report_without_a_stored_consumption_is_not_written(self):
        """NFR-7: the browser cannot mark a batch CONFIRMED."""
        self.start()

        result = self.report(True).json()["writeBack"]

        self.assertEqual(result["status"], "not_written")
        self.assertEqual(result["reason"], "OrgaTEX did not store the consumption")


class WriteBackRefusalTests(WriteBackApiTestCase):
    def test_start_at_4_of_5_is_refused(self):
        self.weigh(4)

        response = self.start()

        self.assert_error(response, 409, "BATCH_NOT_COMPLETE")
        self.assertEqual(Client().get(self.url).json(), {"writeBack": None})

    def test_report_before_start_is_refused(self):
        self.assert_error(self.report(True), 409, "WRITE_BACK_NOT_STARTED")

    def test_without_operator_both_posts_are_refused(self):
        self.weigh()
        anonymous = Client()

        self.assert_error(self.start(anonymous), 403, "OPERATOR_REQUIRED")
        self.assert_error(self.report(True, client=anonymous), 403, "OPERATOR_REQUIRED")

    def test_unknown_session_is_404(self):
        url = "/station/api/sessions/9999/write-back"

        self.assert_error(self.client.get(url), 404, "SESSION_NOT_FOUND")
        self.assert_error(post_json(self.client, url, {}), 404, "SESSION_NOT_FOUND")
        self.assert_error(
            post_json(self.client, url + "/result", {"posted": True}),
            404,
            "SESSION_NOT_FOUND",
        )

    def test_report_body_is_validated(self):
        for body in ({}, {"posted": "yes"}, {"posted": True, "reason": 5}, "[]"):
            with self.subTest(body=body):
                response = post_json(self.client, self.url + "/result", body)
                self.assert_error(response, 400, "VALIDATION_ERROR")

    def test_start_without_csrf_token_is_rejected(self):
        self.weigh()
        csrf_client = Client(enforce_csrf_checks=True)
        put_json(csrf_client, "/station/api/operator", {"operatorId": "OP-01"})

        self.assertEqual(self.start(csrf_client).status_code, 403)

    def test_other_methods_are_not_allowed(self):
        self.assertEqual(self.client.delete(self.url).status_code, 405)
        self.assertEqual(self.client.get(self.url + "/result").status_code, 405)
