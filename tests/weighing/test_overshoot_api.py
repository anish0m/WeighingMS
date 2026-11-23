"""Story 007-handle-overshoot over HTTP (bolt 012, ADR-012).

The evaluation JSON's ``surplusPercent`` / ``overshoot``, the quit JSON's
``ended`` and the 409 refusal detail, against the live Dummy Scale
(training contract).
"""

from tests.weighing.flow import YELLOW
from tests.weighing.test_confirmation_api import FlowApiTestCase

RECOVERY = (
    "Remove material until the weight is back in the band, "
    "or press Quit (F4) to discard and re-weigh."
)


class OvershootApiTests(FlowApiTestCase):
    def evaluate(self, net):
        url = (
            f"/station/api/sessions/{self.session.pk}/components/{YELLOW}"
            f"/evaluation?net={net}&unit=g"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_evaluation_at_96_4_g_has_the_overshoot(self):
        """Story 007 AC 1 over HTTP; the UI only shows these server texts."""
        body = self.evaluate("96.4")

        self.assertEqual(body["zone"], "over")
        self.assertFalse(body["withinTolerance"])
        self.assertEqual(body["statusLine"], "OVER TOLERANCE — SURPLUS +2.4 g")
        self.assertEqual((body["surplus"], body["surplusPercent"]), ("2.4", "2.6"))
        self.assertEqual(
            body["overshoot"],
            {
                "heading": "Surplus +2.4 g (+2.6%) — over tolerance",
                "recovery": RECOVERY,
                "confirmAllowed": False,
                "recalculation": "none",
                "overrideAvailable": False,
                "overrideReason": (
                    "Supervisor override is not available in this training build"
                ),
            },
        )

    def test_no_overshoot_inside_or_below_the_band(self):
        for net in ("94.5", "94.0", "93.4"):
            with self.subTest(net=net):
                body = self.evaluate(net)
                self.assertIsNone(body["surplusPercent"])
                self.assertIsNone(body["overshoot"])

    def test_confirm_over_tolerance_is_409_with_the_surplus(self):
        self.ready(YELLOW, "96.4")

        with self.assertLogs("weighing.confirmation", "INFO"):
            response = self.post(YELLOW, "confirm")

        self.assert_error(response, 409, "OUT_OF_TOLERANCE")
        detail = response.json()["error"]["detail"]
        self.assertEqual(
            (detail["surplus"], detail["surplusPercent"], detail["surplusText"]),
            ("2.4", "2.6", "2.4 g"),
        )

    def test_quit_over_tolerance_reports_the_discard(self):
        self.ready(YELLOW, "96.4")
        attempt_id = self.post(YELLOW, "activate").json()["active"]["attemptId"]

        response = self.post(YELLOW, "quit")

        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(
            body["ended"],
            {
                "attemptId": attempt_id,
                "reason": "overshoot_discarded",
                "net": "96.4",
                "surplus": "2.4",
                "unit": "g",
                "message": (
                    "Overshoot discarded (96.4 g). "
                    "Empty the container and press Re-tare (F2)."
                ),
            },
        )
        self.assertEqual(body["active"]["sequence"], YELLOW)
        self.assertFalse(body["active"]["tared"])
        self.assertEqual(body["weighed"], 0)

    def test_a_plain_quit_reports_no_discard(self):
        self.ready(YELLOW, "40.0")

        ended = self.post(YELLOW, "quit").json()["ended"]

        self.assertEqual(
            {k: ended[k] for k in ("reason", "net", "surplus", "unit")},
            {"reason": "quit", "net": None, "surplus": None, "unit": None},
        )

    def test_only_the_quit_response_has_ended(self):
        body = self.post(YELLOW, "activate").json()

        self.assertNotIn("ended", body)
        progress = self.client.get(f"/station/api/sessions/{self.session.pk}/progress")
        self.assertNotIn("ended", progress.json())
