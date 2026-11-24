"""Stories 009 and 011 over HTTP (bolt 015, ADR-013, ADR-014).

The confirm response's ``completion``, ``GET sessions/<id>/summary`` and
``GET batch-history/<batch_id>``, after B-24187 is weighed with the
prototype's actuals through the live Dummy Scale and Scanner.
"""

from django.test import Client

from tests.helpers import post_json
from tests.weighing import factories
from tests.weighing.flow import BLUE, YELLOW
from tests.weighing.test_completion import PROTOTYPE
from tests.weighing.test_confirmation_api import R_KARIM, FlowApiTestCase

HISTORY_KEYS = {
    "recordId",
    "sessionId",
    "batchId",
    "sequence",
    "componentCode",
    "componentName",
    "actualWeight",
    "unit",
    "actualText",
    "lot",
    "container",
    "tare",
    "tareText",
    "scaleId",
    "target",
    "toleranceMin",
    "toleranceMax",
    "result",
    "operator",
    "recordedAt",
}


class CompletionApiTestCase(FlowApiTestCase):
    def weigh(self, count=5, session=None):
        session = session or self.session
        self.assertEqual(self.post_for(session, BLUE, "activate").status_code, 200)
        responses = []
        for sequence in range(1, count + 1):
            self.verify(sequence, session=session)
            self.set_weight(sequence, PROTOTYPE[sequence])
            response = self.post_for(session, sequence, "confirm")
            self.assertEqual(response.status_code, 201, response.content)
            responses.append(response.json())
        return responses

    def post_for(self, session, sequence, action):
        return post_json(
            self.client,
            f"/station/api/sessions/{session.pk}/components/{sequence}/{action}",
            {},
        )

    def summary_url(self, session=None):
        return f"/station/api/sessions/{(session or self.session).pk}/summary"


class ConfirmCompletionTests(CompletionApiTestCase):
    def test_only_the_last_confirm_carries_the_completion(self):
        responses = self.weigh()

        for body in responses[:4]:
            self.assertNotIn("completion", body)
            self.assertEqual(body["progress"]["state"], "in_progress")
        last = responses[4]
        self.assertEqual(last["progress"]["state"], "complete")
        self.assertEqual(last["progress"]["progressText"], "5 of 5 components weighed")
        self.assertIsNone(last["progress"]["active"])
        self.assertEqual(last["completion"]["summary"]["totalDispensedKg"], "35.322")
        self.assertEqual(last["completion"]["writeBack"]["status"], "pending")


class SummaryApiTests(CompletionApiTestCase):
    def test_summary_of_the_completed_batch(self):
        """Story 009 AC 1 + AC 2 (View 3 values)."""
        last = self.weigh()[4]

        response = Client().get(self.summary_url())

        self.assertEqual(response.status_code, 200)
        body = response.json()
        summary = body["summary"]
        self.assertEqual(summary["sessionId"], self.session.pk)
        self.assertEqual(summary["batchId"], "B-24187")
        self.assertEqual(summary["weighed"], 5)
        self.assertEqual(summary["total"], 5)
        self.assertEqual(summary["componentsText"], "5 of 5")
        self.assertIs(summary["allWithin"], True)
        self.assertEqual(summary["allWithinText"], "YES")
        self.assertEqual(summary["totalDispensedKg"], "35.322")
        self.assertEqual(summary["totalDispensedText"], "35.322 kg")
        self.assertIsInstance(summary["elapsedSeconds"], int)
        self.assertRegex(summary["elapsedText"], r"^\d+ min \d+ s$")
        self.assertEqual(summary["operator"], R_KARIM)
        self.assertEqual(summary["completedAt"], last["record"]["recordedAt"])
        self.assertEqual(body, last["completion"])

    def test_summary_carries_the_pending_write_back(self):
        """Story 009 AC 4 over HTTP."""
        self.weigh()

        write_back = Client().get(self.summary_url()).json()["writeBack"]

        self.assertEqual(write_back["status"], "pending")
        self.assertEqual(write_back["attempts"], 0)
        self.assertEqual(
            write_back["idempotencyKey"], f"WMS-B-24187-S{self.session.pk}"
        )

    def test_summary_at_four_of_five_is_refused(self):
        """Story 009 AC 3."""
        self.weigh(4)

        self.assert_error(Client().get(self.summary_url()), 409, "BATCH_NOT_COMPLETE")

    def test_unknown_session_is_404(self):
        response = Client().get("/station/api/sessions/9999/summary")

        self.assert_error(response, 404, "SESSION_NOT_FOUND")

    def test_summary_is_read_only(self):
        self.assertEqual(self.client.post(self.summary_url()).status_code, 405)


class BatchHistoryApiTests(CompletionApiTestCase):
    url = "/station/api/batch-history/B-24187"

    def test_every_component_with_all_traceability_fields(self):
        """Story 011 AC 1."""
        self.weigh()

        response = Client().get(self.url)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["batchId"], "B-24187")
        records = body["records"]
        self.assertEqual([r["sequence"] for r in records], [1, 2, 3, 4, 5])
        for row in records:
            self.assertEqual(set(row), HISTORY_KEYS)
        yellow = records[YELLOW - 1]
        self.assertEqual(
            {k: yellow[k] for k in ("componentCode", "target", "actualWeight", "unit")},
            {
                "componentCode": "DYE-4471",
                "target": "94.0000",
                "actualWeight": "94.2",
                "unit": "g",
            },
        )
        self.assertEqual(
            {k: yellow[k] for k in ("scaleId", "lot", "container", "tare")},
            {
                "scaleId": "scale-3kg",
                "lot": "2026-0387",
                "container": "C-12",
                "tare": "214.0000",
            },
        )
        self.assertEqual(records[3]["scaleId"], "scale-32kg")
        self.assertEqual(records[3]["actualWeight"], "23.980")

    def test_every_record_carries_the_operator_id(self):
        """Story 011 AC 2."""
        self.weigh()

        records = Client().get(self.url).json()["records"]

        self.assertEqual({r["operator"]["operatorId"] for r in records}, {"OP-01"})
        self.assertTrue(all(r["recordedAt"] for r in records))

    def test_records_of_all_sessions_in_sequence_order(self):
        """ADR-014: a batch weighed again shows both runs."""
        self.weigh()
        second = factories.session(factories.teal_selection())
        self.weigh(2, session=second)

        records = Client().get(self.url).json()["records"]

        self.assertEqual([r["sequence"] for r in records], [1, 1, 2, 2, 3, 4, 5])
        self.assertEqual(
            [r["sessionId"] for r in records[:2]], [self.session.pk, second.pk]
        )

    def test_unknown_batch_has_an_empty_history(self):
        response = Client().get("/station/api/batch-history/B-99999")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"batchId": "B-99999", "records": []})

    def test_history_is_read_only(self):
        self.assertEqual(self.client.post(self.url).status_code, 405)
