"""Stories 004-target-and-remaining and 005-evaluate-inclusive-tolerance.

``weighing.tolerance``: band, zone, still to weigh, status line, display
format (FR-10–FR-12, workbook STEP 22) and the display-resolution rule
(ADR-009). Pure Decimal rules.
"""

from decimal import Decimal
from pathlib import Path

from django.test import SimpleTestCase, TestCase

from tests.weighing import factories
from weighing import rules, scale_selection, tolerance
from weighing.tolerance import (
    ToleranceBand,
    Zone,
    at_resolution,
    band_for,
    evaluate,
    format_weight,
    to_unit,
)

YELLOW = ToleranceBand(Decimal("94.0000"), Decimal("0.5000"), "g")
SODIUM = ToleranceBand(Decimal("24.0000"), Decimal("0.1200"), "kg")


def judge(net, band=YELLOW, unit=None):
    return evaluate(band, Decimal(net), unit or band.unit)


class InclusiveToleranceTests(SimpleTestCase):
    def test_the_five_boundary_weights(self):
        """Story 005 AC 1 (workbook STEP 22): only 93.5 / 94.0 / 94.5 confirm."""
        expected = {
            "93.4": (Zone.NEAR, False),
            "93.5": (Zone.WITHIN, True),
            "94.0": (Zone.WITHIN, True),
            "94.5": (Zone.WITHIN, True),
            "94.6": (Zone.OVER, False),
        }
        for net, (zone, within) in expected.items():
            with self.subTest(net=net):
                evaluation = judge(net)
                self.assertEqual(evaluation.zone, zone)
                self.assertIs(evaluation.within_tolerance, within)

    def test_the_caption(self):
        """Story 005 AC 2."""
        self.assertEqual(YELLOW.caption, "TOLERANCE ±0.5 g (93.5 – 94.5)")
        self.assertEqual(SODIUM.caption, "TOLERANCE ±0.120 kg (23.880 – 24.120)")

    def test_below_90_percent_of_target_is_under(self):
        """Story 005 AC 3: 90 % of 94.0 g is 84.6 g."""
        self.assertEqual(YELLOW.near_from, Decimal("84.6"))
        self.assertEqual(judge("84.5").zone, Zone.UNDER)
        self.assertEqual(judge("84.6").zone, Zone.NEAR)
        self.assertEqual(judge("0.0").zone, Zone.UNDER)

    def test_the_band_in_kilograms(self):
        self.assertEqual(
            (SODIUM.low, SODIUM.high), (Decimal("23.88"), Decimal("24.12"))
        )
        self.assertEqual(judge("23.879", SODIUM).zone, Zone.NEAR)
        self.assertEqual(judge("23.880", SODIUM).zone, Zone.WITHIN)
        self.assertEqual(judge("24.120", SODIUM).zone, Zone.WITHIN)
        self.assertEqual(judge("24.121", SODIUM).zone, Zone.OVER)

    def test_zero_tolerance_accepts_only_the_target(self):
        band = ToleranceBand(Decimal("94.0"), Decimal(0), "g")

        self.assertEqual(
            [evaluate(band, Decimal(w), "g").zone for w in ("93.9", "94.0", "94.1")],
            [Zone.NEAR, Zone.WITHIN, Zone.OVER],
        )


class SnapshotBandTests(TestCase):
    def test_band_for_reads_target_tolerance_and_unit(self):
        components = {
            c.sequence: c for c in factories.teal_selection().components.all()
        }

        self.assertEqual(band_for(components[factories.YELLOW_RGB]), YELLOW)
        self.assertEqual(band_for(components[factories.SODIUM_SULPHATE]), SODIUM)


class StillToWeighTests(SimpleTestCase):
    def test_at_zero_the_whole_target_is_still_to_weigh(self):
        """Story 004 AC 1."""
        evaluation = judge("0.0")

        self.assertEqual(evaluation.still_to_weigh, Decimal("94.0"))
        self.assertEqual(format_weight(YELLOW.target, "g"), "94.0 g")

    def test_at_90_g_four_grams_remain(self):
        """Story 004 AC 2."""
        evaluation = judge("90.0")

        self.assertEqual(evaluation.still_to_weigh, Decimal("4.0"))
        self.assertEqual(evaluation.status_line, "DISPENSE — 4.0 g REMAINING")

    def test_never_negative_at_or_above_target(self):
        """Story 004 AC 3."""
        for net in ("94.0", "94.5", "95.0", "200.0"):
            with self.subTest(net=net):
                self.assertEqual(judge(net).still_to_weigh, Decimal("0.0"))
                self.assertEqual(str(judge(net).still_to_weigh), "0.0")

    def test_a_negative_reading_is_under(self):
        """A lifted container reads negative: FR-11's max(0, target − net)."""
        evaluation = judge("-0.5")

        self.assertEqual(evaluation.zone, Zone.UNDER)
        self.assertEqual(evaluation.still_to_weigh, Decimal("94.5"))


class StatusLineTests(SimpleTestCase):
    def test_status_line_per_zone(self):
        self.assertEqual(judge("0.0").status_line, "DISPENSE — 94.0 g REMAINING")
        self.assertEqual(judge("93.4").status_line, "DISPENSE — 0.6 g REMAINING")
        self.assertEqual(
            judge("93.5").status_line, "WITHIN TOLERANCE — PRESS OK TO CONFIRM"
        )
        self.assertEqual(judge("94.6").status_line, "OVER TOLERANCE — SURPLUS +0.6 g")

    def test_surplus_only_when_over(self):
        """Model Decision 5: the amount only, no percentage or recalculation."""
        self.assertEqual(judge("94.6").surplus, Decimal("0.6"))
        self.assertIsNone(judge("94.5").surplus)
        self.assertIsNone(judge("90.0").surplus)

    def test_status_line_in_kilograms(self):
        self.assertEqual(
            judge("20.000", SODIUM).status_line, "DISPENSE — 4.000 kg REMAINING"
        )
        self.assertEqual(
            judge("24.200", SODIUM).status_line, "OVER TOLERANCE — SURPLUS +0.200 kg"
        )


class DisplayFormatTests(SimpleTestCase):
    def test_grams_have_one_decimal_and_kilograms_three(self):
        """Story 004 AC 4, FR-10b."""
        cases = {
            ("24.0000", "kg"): "24.000 kg",
            ("9.6", "kg"): "9.600 kg",
            ("94.0000", "g"): "94.0 g",
            ("4", "g"): "4.0 g",
            ("0", "g"): "0.0 g",
        }
        for (amount, unit), text in cases.items():
            with self.subTest(amount=amount, unit=unit):
                self.assertEqual(format_weight(Decimal(amount), unit), text)

    def test_no_exponent_notation(self):
        self.assertEqual(format_weight(Decimal("1240.0000"), "g"), "1240.0 g")
        self.assertEqual(format_weight(Decimal("1E+3"), "g"), "1000.0 g")

    def test_negative_zero_is_shown_as_zero(self):
        self.assertEqual(format_weight(Decimal("-0.04"), "g"), "0.0 g")


class ResolutionTests(SimpleTestCase):
    """ADR-009: one value at display resolution, rounded half up."""

    def test_the_reading_is_rounded_once_and_then_judged(self):
        expected = {
            "94.54": ("94.5", Zone.WITHIN),
            "94.55": ("94.6", Zone.OVER),
            "93.45": ("93.5", Zone.WITHIN),
            "93.44": ("93.4", Zone.NEAR),
        }
        for raw, (net, zone) in expected.items():
            with self.subTest(raw=raw):
                evaluation = judge(raw)
                self.assertEqual(str(evaluation.net), net)
                self.assertEqual(evaluation.zone, zone)

    def test_kilograms_are_rounded_to_grams(self):
        self.assertEqual(at_resolution(Decimal("24.1204"), "kg"), Decimal("24.120"))
        self.assertEqual(at_resolution(Decimal("24.1205"), "kg"), Decimal("24.121"))


class ConversionTests(SimpleTestCase):
    """Model Decision 1: a reading in the other unit is converted exactly."""

    def test_exact_conversion(self):
        self.assertEqual(to_unit(Decimal("94.0"), "g", "kg"), Decimal("0.094"))
        self.assertEqual(to_unit(Decimal("1.850"), "kg", "g"), Decimal(1850))
        self.assertEqual(to_unit(Decimal(3), "kg", "kg"), Decimal(3))

    def test_a_kg_reading_is_judged_in_the_component_unit(self):
        evaluation = judge("0.0945", unit="kg")

        self.assertEqual((evaluation.net, evaluation.unit), (Decimal("94.5"), "g"))
        self.assertTrue(evaluation.within_tolerance)

    def test_a_g_reading_on_a_kg_component(self):
        self.assertEqual(judge("23880", SODIUM, unit="g").zone, Zone.WITHIN)

    def test_an_unknown_unit_is_refused(self):
        with self.assertRaises(ValueError):
            judge("94.0", unit="lb")


class DecimalOnlyTests(SimpleTestCase):
    """Story 005 AC 4, NFR-16."""

    def test_every_value_is_a_decimal(self):
        evaluation = judge("94.6")
        values = (
            evaluation.net,
            evaluation.still_to_weigh,
            evaluation.surplus,
            YELLOW.low,
            YELLOW.high,
            YELLOW.near_from,
        )

        for value in values:
            self.assertIsInstance(value, Decimal)

    def test_the_rule_modules_never_use_float(self):
        for module in (tolerance, scale_selection, rules):
            with self.subTest(module=module.__name__):
                self.assertNotIn("float(", Path(module.__file__).read_text())
