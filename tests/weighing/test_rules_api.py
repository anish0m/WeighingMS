"""Stories 002, 004 and 005 over HTTP (ADR-008).

``GET /station/api/sessions/<id>/components`` carries each component's scale,
target and band; ``GET …/components/<seq>/evaluation`` judges a live reading.
One live test checks the real seeded B-24187 taken through the OrgaTEX adapter.
"""

from decimal import Decimal

from django.test import LiveServerTestCase, TestCase, override_settings

from batches.services import select_batch
from dummy_orgatex.services import seed_training_scenario
from tests.weighing import factories
from weighing import rules
from weighing.services import RefusalReason, WeighingRefused
from weighing.tolerance import Zone

YELLOW = factories.YELLOW_RGB
SODIUM = factories.SODIUM_SULPHATE
PRECISION = {
    "scaleId": "scale-3kg",
    "label": "3 kg precision",
    "classText": "3 kg",
    "unit": "g",
    "mode": "automatic",
}
FLOOR = {
    "scaleId": "scale-32kg",
    "label": "32 kg floor",
    "classText": "32 kg",
    "unit": "kg",
    "mode": "automatic",
}


def components_url(session_id):
    return f"/station/api/sessions/{session_id}/components"


def evaluation_url(session_id, sequence=YELLOW):
    return f"/station/api/sessions/{session_id}/components/{sequence}/evaluation"


class ComponentRulesApiTests(TestCase):
    def setUp(self):
        self.session = factories.session()

    def components(self):
        response = self.client.get(components_url(self.session.pk))
        self.assertEqual(response.status_code, 200)
        return {c["sequence"]: c for c in response.json()["components"]}

    def test_yellow_rgb_rules(self):
        """Story 002 AC 1, story 004 AC 1, story 005 AC 2."""
        yellow = self.components()[YELLOW]

        self.assertEqual(
            {k: yellow[k] for k in ("target", "targetText", "scale", "tolerance")},
            {
                "target": "94.0000",
                "targetText": "94.0 g",
                "scale": PRECISION,
                "tolerance": {
                    "tolerance": "0.5000",
                    "low": "93.5000",
                    "high": "94.5000",
                    "nearFrom": "84.6000",
                    "caption": "TOLERANCE ±0.5 g (93.5 – 94.5)",
                },
            },
        )

    def test_sodium_sulphate_rules(self):
        """Story 002 AC 2, story 004 AC 4."""
        sodium = self.components()[SODIUM]

        self.assertEqual(sodium["targetText"], "24.000 kg")
        self.assertEqual(sodium["scale"], FLOOR)
        self.assertEqual(
            sodium["tolerance"]["caption"], "TOLERANCE ±0.120 kg (23.880 – 24.120)"
        )

    def test_every_component_has_its_scale(self):
        scales = [c["scale"]["scaleId"] for c in self.components().values()]

        self.assertEqual(
            scales, ["scale-3kg", "scale-3kg", "scale-3kg", "scale-32kg", "scale-32kg"]
        )

    def test_a_changed_threshold_is_followed_without_code_change(self):
        """Story 002 AC 4, through the API."""
        with override_settings(WEIGHING_SCALE_THRESHOLD_KG=Decimal("0.05")):
            yellow = self.components()[YELLOW]

        self.assertEqual(yellow["scale"], FLOOR)
        self.assertEqual(self.components()[YELLOW]["scale"], PRECISION)


class EvaluationApiTests(TestCase):
    def setUp(self):
        self.session = factories.session()

    def evaluate(self, net, unit="g", sequence=YELLOW):
        response = self.client.get(
            evaluation_url(self.session.pk, sequence), {"net": net, "unit": unit}
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_the_five_boundary_weights(self):
        """Story 005 AC 1 over HTTP (workbook STEP 22)."""
        expected = {
            "93.4": ("near", False),
            "93.5": ("within", True),
            "94.0": ("within", True),
            "94.5": ("within", True),
            "94.6": ("over", False),
        }
        for net, (zone, within) in expected.items():
            with self.subTest(net=net):
                body = self.evaluate(net)
                self.assertEqual(
                    (body["zone"], body["withinTolerance"]), (zone, within)
                )

    def test_near_reading_json(self):
        self.assertEqual(
            self.evaluate("93.4"),
            {
                "sessionId": self.session.pk,
                "sequence": YELLOW,
                "net": "93.4",
                "unit": "g",
                "netText": "93.4 g",
                "zone": "near",
                "withinTolerance": False,
                "stillToWeigh": "0.6",
                "stillToWeighText": "0.6 g",
                "surplus": None,
                "surplusText": None,
                "statusLine": "DISPENSE — 0.6 g REMAINING",
                "barPercent": "74.7",
                "surplusPercent": None,
                "overshoot": None,
            },
        )

    def test_over_reading_shows_the_surplus(self):
        body = self.evaluate("94.6")

        self.assertEqual(
            {k: body[k] for k in ("stillToWeigh", "surplus", "surplusText")},
            {"stillToWeigh": "0.0", "surplus": "0.6", "surplusText": "0.6 g"},
        )
        self.assertEqual(body["statusLine"], "OVER TOLERANCE — SURPLUS +0.6 g")

    def test_target_and_still_to_weigh(self):
        """Story 004 AC 1–3."""
        self.assertEqual(self.evaluate("0.0")["stillToWeighText"], "94.0 g")
        at_90 = self.evaluate("90.0")
        self.assertEqual(at_90["stillToWeighText"], "4.0 g")
        self.assertEqual(at_90["statusLine"], "DISPENSE — 4.0 g REMAINING")
        self.assertEqual(self.evaluate("94.0")["stillToWeigh"], "0.0")

    def test_below_90_percent_is_under(self):
        """Story 005 AC 3."""
        self.assertEqual(self.evaluate("84.5")["zone"], "under")

    def test_within_status_line(self):
        self.assertEqual(
            self.evaluate("94.0")["statusLine"],
            "WITHIN TOLERANCE — PRESS OK TO CONFIRM",
        )

    def test_the_evaluated_value_is_the_display_value(self):
        """ADR-009: 94.54 g is shown, judged and returned as 94.5 g."""
        body = self.evaluate("94.54")

        self.assertEqual((body["net"], body["zone"]), ("94.5", "within"))
        self.assertEqual(self.evaluate("94.55")["zone"], "over")

    def test_a_reading_in_kg_is_judged_in_grams(self):
        body = self.evaluate("0.0945", unit="kg")

        self.assertEqual(
            (body["net"], body["unit"], body["zone"]), ("94.5", "g", "within")
        )

    def test_sodium_sulphate_in_kilograms(self):
        body = self.evaluate("24.000", unit="kg", sequence=SODIUM)

        self.assertEqual((body["netText"], body["zone"]), ("24.000 kg", "within"))

    def test_a_negative_reading_is_under(self):
        self.assertEqual(self.evaluate("-0.5")["zone"], "under")

    def test_no_operator_is_needed(self):
        self.assertEqual(
            self.client.get(
                evaluation_url(self.session.pk), {"net": "1", "unit": "g"}
            ).status_code,
            200,
        )


class EvaluationApiRefusalTests(TestCase):
    def setUp(self):
        self.session = factories.session()

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status)
        self.assertEqual(response.json()["error"]["code"], code)

    def test_invalid_readings_are_400(self):
        cases = (
            {},
            {"unit": "g"},
            {"net": "94.0"},
            {"net": "", "unit": "g"},
            {"net": "1e2", "unit": "g"},
            {"net": "NaN", "unit": "g"},
            {"net": "Infinity", "unit": "g"},
            {"net": "94,5", "unit": "g"},
            {"net": " 94.5", "unit": "g"},
            {"net": "94.", "unit": "g"},
            {"net": "+94.5", "unit": "g"},
            {"net": "1234567", "unit": "g"},
            {"net": "94.5", "unit": "lb"},
            {"net": "94.5", "unit": "G"},
        )
        for params in cases:
            with self.subTest(params=params):
                self.assert_error(
                    self.client.get(evaluation_url(self.session.pk), params),
                    400,
                    "INVALID_REQUEST",
                )

    def test_unknown_session_is_404(self):
        self.assert_error(
            self.client.get(evaluation_url(999), {"net": "1", "unit": "g"}),
            404,
            "SESSION_NOT_FOUND",
        )

    def test_unknown_component_is_404(self):
        with self.assertLogs("weighing.identity", "INFO"):
            response = self.client.get(
                evaluation_url(self.session.pk, 9), {"net": "1", "unit": "g"}
            )

        self.assert_error(response, 404, "COMPONENT_NOT_FOUND")

    def test_other_methods_are_405(self):
        for method in ("post", "put", "patch", "delete"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(evaluation_url(self.session.pk))
                self.assertEqual(response.status_code, 405)


class EvaluateReadingTests(TestCase):
    """``rules.evaluate_reading``: the function bolt 010's confirm calls."""

    def test_returns_the_rules_and_the_evaluation(self):
        session = factories.session()

        component_rules, evaluation = rules.evaluate_reading(
            session.pk, YELLOW, Decimal("94.5"), "g"
        )

        self.assertEqual(component_rules.assignment.scale.scale_id, "scale-3kg")
        self.assertEqual(
            (component_rules.band.low, component_rules.band.high),
            (Decimal("93.5"), Decimal("94.5")),
        )
        self.assertEqual(component_rules.target_text, "94.0 g")
        self.assertEqual(evaluation.zone, Zone.WITHIN)

    def test_unknown_session_is_refused(self):
        with self.assertRaises(WeighingRefused) as refused:
            rules.evaluate_reading(999, YELLOW, Decimal(1), "g")

        self.assertEqual(refused.exception.reason, RefusalReason.SESSION_NOT_FOUND)


class SeededRulesTests(LiveServerTestCase):
    """The real Dummy OrgaTEX seed (B-24187), via the adapter and the snapshot."""

    def test_b24187_scales_targets_and_captions(self):
        seed_training_scenario()
        self.enterContext(
            override_settings(ORGATEX_BASE_URL=f"{self.live_server_url}/api")
        )

        selection = select_batch("B-24187", "touch")
        seen = [
            (
                r.component.name,
                r.assignment.scale.scale_id,
                r.target_text,
                r.band.caption,
            )
            for r in map(rules.component_rules, selection.components.all())
        ]

        self.assertEqual(
            seen,
            [
                (
                    "Remazol Brill. Blue RSPL",
                    "scale-3kg",
                    "1240.0 g",
                    "TOLERANCE ±6.0 g (1234.0 – 1246.0)",
                ),
                (
                    "Remazol Red RB",
                    "scale-3kg",
                    "386.0 g",
                    "TOLERANCE ±2.0 g (384.0 – 388.0)",
                ),
                (
                    "Remazol Yellow RGB",
                    "scale-3kg",
                    "94.0 g",
                    "TOLERANCE ±0.5 g (93.5 – 94.5)",
                ),
                (
                    "Sodium Sulphate",
                    "scale-32kg",
                    "24.000 kg",
                    "TOLERANCE ±0.120 kg (23.880 – 24.120)",
                ),
                (
                    "Soda Ash",
                    "scale-32kg",
                    "9.600 kg",
                    "TOLERANCE ±0.048 kg (9.552 – 9.648)",
                ),
            ],
        )
