"""Story 007-handle-overshoot: the surplus and the STEP 24 training rule.

``weighing.overshoot`` (bolt 012, ADR-012): surplus amount and % of target in
Decimal; the fixed OVERSHOOT_RULE (no confirm, no recalculation, no override).
Pure rules, no scale.
"""

from decimal import Decimal

from django.test import SimpleTestCase

from weighing import overshoot
from weighing.overshoot import OVERSHOOT_RULE, overshoot_json, surplus_of
from weighing.tolerance import ToleranceBand, Zone, evaluate

YELLOW = ToleranceBand(Decimal("94.0000"), Decimal("0.5000"), "g")
SODIUM = ToleranceBand(Decimal("24.0000"), Decimal("0.1200"), "kg")


def surplus(net, band=YELLOW):
    return surplus_of(evaluate(band, Decimal(net), band.unit), band.target)


class SurplusTests(SimpleTestCase):
    def test_yellow_rgb_at_96_4_g(self):
        """Story 007 AC 1: "OVER TOLERANCE — SURPLUS +2.4 g", "+2.4 g (+2.6%)"."""
        evaluation = evaluate(YELLOW, Decimal("96.4"), "g")
        value = surplus_of(evaluation, YELLOW.target)

        self.assertEqual(evaluation.zone, Zone.OVER)
        self.assertFalse(evaluation.within_tolerance)
        self.assertEqual(evaluation.status_line, "OVER TOLERANCE — SURPLUS +2.4 g")
        self.assertEqual(value.amount, Decimal("2.4"))
        self.assertEqual(value.percent, Decimal("2.6"))
        self.assertEqual(value.heading, "Surplus +2.4 g (+2.6%) — over tolerance")

    def test_just_over_the_band_at_94_6_g(self):
        value = surplus("94.6")

        self.assertEqual(
            (value.amount, value.percent), (Decimal("0.6"), Decimal("0.6"))
        )
        self.assertEqual(value.heading, "Surplus +0.6 g (+0.6%) — over tolerance")

    def test_a_kg_component(self):
        """Sodium Sulphate 24.200 kg: +0.200 kg, 0.833 % → +0.8%."""
        value = surplus("24.200", SODIUM)

        self.assertEqual(value.amount, Decimal("0.200"))
        self.assertEqual(value.percent, Decimal("0.8"))
        self.assertEqual(value.heading, "Surplus +0.200 kg (+0.8%) — over tolerance")

    def test_no_surplus_inside_or_below_the_band(self):
        for net in ("94.5", "94.0", "93.5", "93.4", "0.0"):
            with self.subTest(net=net):
                self.assertIsNone(surplus(net))

    def test_the_percent_rounds_half_up_to_0_1(self):
        """1.3 g over a 200.0 g target is exactly 0.65 % → 0.7 (not 0.6)."""
        band = ToleranceBand(Decimal("200.0"), Decimal("1.0"), "g")

        self.assertEqual(surplus("201.3", band).percent, Decimal("0.7"))

    def test_only_decimal_is_used(self):
        value = surplus("96.4")

        self.assertIsInstance(value.amount, Decimal)
        self.assertIsInstance(value.percent, Decimal)
        self.assertNotIn("float", overshoot.__loader__.get_source(overshoot.__name__))

    def test_the_detail_texts(self):
        self.assertEqual(
            surplus("96.4").detail(),
            {"surplus": "2.4", "surplusPercent": "2.6", "surplusText": "2.4 g"},
        )


class OvershootRuleTests(SimpleTestCase):
    def test_the_step_24_rule(self):
        """OQ-4: overweight stays unconfirmed; no recalculation; no override."""
        self.assertFalse(OVERSHOOT_RULE.confirm_allowed)
        self.assertEqual(OVERSHOOT_RULE.recalculation, "none")
        self.assertFalse(OVERSHOOT_RULE.override_available)

    def test_the_rule_is_a_frozen_constant(self):
        with self.assertRaises(AttributeError):
            OVERSHOOT_RULE.override_available = True

    def test_the_overshoot_json(self):
        self.assertEqual(
            overshoot_json(surplus("96.4")),
            {
                "heading": "Surplus +2.4 g (+2.6%) — over tolerance",
                "recovery": (
                    "Remove material until the weight is back in the band, "
                    "or press Quit (F4) to discard and re-weigh."
                ),
                "confirmAllowed": False,
                "recalculation": "none",
                "overrideAvailable": False,
                "overrideReason": (
                    "Supervisor override is not available in this training build"
                ),
            },
        )
        self.assertIsNone(overshoot_json(None))
