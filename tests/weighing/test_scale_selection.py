"""Story 002-select-scale-automatically: the scale follows the configurable threshold.

``weighing.scale_selection`` (FR-8, NFR-13, workbook STEP 21). Pure rules;
the threshold comes from ``WEIGHING_SCALE_THRESHOLD_KG``.
"""

import os
from decimal import Decimal
from unittest import mock

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from tests.weighing import factories
from weighing.scale_selection import (
    ScaleClass,
    scale_threshold_kg,
    select_scale,
)
from weighingms.settings import positive_decimal

PRECISION = "scale-3kg"
FLOOR = "scale-32kg"


def scale_id(target, unit, threshold_kg=None):
    return select_scale(Decimal(target), unit, threshold_kg).scale.scale_id


class SelectScaleTests(SimpleTestCase):
    def test_yellow_rgb_goes_to_the_precision_scale_automatically(self):
        """Story 002 AC 1."""
        assignment = select_scale(Decimal("94.0"), "g")

        self.assertIs(assignment.scale, ScaleClass.PRECISION)
        self.assertEqual(
            (assignment.scale.scale_id, assignment.scale.label, assignment.mode),
            (PRECISION, "3 kg precision", "automatic"),
        )

    def test_sodium_sulphate_goes_to_the_floor_scale_in_kg(self):
        """Story 002 AC 2."""
        assignment = select_scale(Decimal("24.000"), "kg")

        self.assertEqual(
            (assignment.scale.scale_id, assignment.scale.label, assignment.scale.unit),
            (FLOOR, "32 kg floor", "kg"),
        )

    def test_the_five_teal_4c_components(self):
        scales = [scale_id(row[7], row[3]) for row in factories.TEAL_4C]  # target, unit

        self.assertEqual(scales, [PRECISION, PRECISION, PRECISION, FLOOR, FLOOR])

    def test_exactly_3_kg_is_precision_and_3_0001_kg_is_floor(self):
        """Story 002 AC 3."""
        self.assertEqual(scale_id("3", "kg"), PRECISION)
        self.assertEqual(scale_id("3.000", "kg"), PRECISION)
        self.assertEqual(scale_id("3.0001", "kg"), FLOOR)

    def test_the_boundary_holds_for_targets_in_grams(self):
        self.assertEqual(scale_id("3000", "g"), PRECISION)
        self.assertEqual(scale_id("3000.1", "g"), FLOOR)

    def test_an_explicit_threshold_is_used(self):
        self.assertEqual(scale_id("5", "kg", Decimal(10)), PRECISION)
        self.assertEqual(scale_id("94.0", "g", Decimal("0.05")), FLOOR)

    def test_an_unknown_unit_is_refused(self):
        with self.assertRaises(ValueError):
            select_scale(Decimal(1), "lb")


class ConfiguredThresholdTests(SimpleTestCase):
    def test_the_default_threshold_is_3_kg(self):
        self.assertEqual(settings.WEIGHING_SCALE_THRESHOLD_KG, Decimal(3))
        self.assertEqual(scale_threshold_kg(), Decimal(3))

    def test_a_changed_threshold_changes_the_selection(self):
        """Story 002 AC 4: no code change, the next activation follows it."""
        with override_settings(WEIGHING_SCALE_THRESHOLD_KG=Decimal("0.05")):
            self.assertEqual(scale_id("94.0", "g"), FLOOR)
        with override_settings(WEIGHING_SCALE_THRESHOLD_KG=Decimal(30)):
            self.assertEqual(scale_id("24.000", "kg"), PRECISION)
        self.assertEqual(scale_id("94.0", "g"), PRECISION)

    def test_an_invalid_configured_threshold_is_refused(self):
        for value in (3.0, "3", Decimal(0), Decimal(-1), Decimal("NaN"), None):
            with (
                self.subTest(value=value),
                override_settings(WEIGHING_SCALE_THRESHOLD_KG=value),
                self.assertRaises(ImproperlyConfigured),
            ):
                select_scale(Decimal("94.0"), "g")


class ThresholdSettingTests(SimpleTestCase):
    """``positive_decimal`` reads the environment when settings load."""

    NAME = "WEIGHING_SCALE_THRESHOLD_KG"

    def read(self, value=None):
        environ = {} if value is None else {self.NAME: value}
        with mock.patch.dict(os.environ, environ, clear=False):
            if value is None:
                os.environ.pop(self.NAME, None)
            return positive_decimal(self.NAME, "3")

    def test_default_without_the_variable(self):
        self.assertEqual(self.read(), Decimal(3))

    def test_the_environment_overrides_the_default(self):
        self.assertEqual(self.read("2.5"), Decimal("2.5"))
        self.assertEqual(self.read(" 4 "), Decimal(4))

    def test_invalid_values_stop_startup(self):
        for value in ("abc", "", "0", "-1", "NaN", "Infinity"):
            with self.subTest(value=value), self.assertRaises(ImproperlyConfigured):
                self.read(value)
