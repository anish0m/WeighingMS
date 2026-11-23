"""Bolt 011 display data for View 2 (plan Decision 1, story 007/004).

The bar's band, target line and fill are Decimal percentages from the server,
so the browser only places them. The component JSON also carries the rail's
swatch colour and scale class, the header line under the name and the bar's
maximum.
"""

from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from tests.weighing import factories
from weighing.rules import BarScale, component_rules
from weighing.scale_selection import ScaleClass
from weighing.tolerance import ToleranceBand

YELLOW = factories.YELLOW_RGB
SODIUM = factories.SODIUM_SULPHATE


def yellow_band():
    return ToleranceBand(Decimal("94.0"), Decimal("0.5"), "g")


class BarScaleTests(SimpleTestCase):
    def test_yellow_rgb_on_the_0_to_125_g_bar(self):
        bar, band = BarScale(Decimal(125)), yellow_band()

        self.assertEqual(
            (bar.percent(band.low), bar.band_width(band), bar.percent(band.target)),
            (Decimal("74.8"), Decimal("0.8"), Decimal("75.2")),
        )

    def test_percent_is_rounded_half_up_to_tenths(self):
        bar = BarScale(Decimal(125))

        self.assertEqual(bar.percent(Decimal("94.2")), Decimal("75.4"))  # 75.36
        self.assertEqual(bar.percent(Decimal("93.4")), Decimal("74.7"))  # 74.72
        self.assertEqual(bar.percent(Decimal("0.0625")), Decimal("0.1"))  # 0.05

    def test_percent_is_clamped_to_the_bar(self):
        bar = BarScale(Decimal(125))

        self.assertEqual(bar.percent(Decimal(250)), Decimal("100.0"))
        self.assertEqual(bar.percent(Decimal("-3.0")), Decimal("0.0"))
        self.assertEqual(bar.percent(Decimal(0)), Decimal("0.0"))

    def test_a_zero_maximum_draws_nothing(self):
        self.assertEqual(BarScale(Decimal(0)).percent(Decimal(5)), Decimal(0))

    def test_a_narrow_band_stays_visible(self):
        """The prototype keeps a band at least 0.6 % wide."""
        bar = BarScale(Decimal(1000))  # 93.5 – 94.5 g is 0.1 % of 1000 g

        self.assertEqual(bar.band_width(yellow_band()), Decimal("0.6"))

    def test_results_are_decimal(self):
        bar = BarScale(Decimal(125))

        self.assertIsInstance(bar.percent(Decimal("94.2")), Decimal)
        self.assertIsInstance(bar.band_width(yellow_band()), Decimal)

    def test_scale_class_text_for_the_rail(self):
        self.assertEqual(
            [(s.scale_id, s.class_text) for s in ScaleClass],
            [("scale-3kg", "3 kg"), ("scale-32kg", "32 kg")],
        )


class ComponentDisplayApiTests(TestCase):
    def setUp(self):
        self.session = factories.session()

    def components(self, session=None):
        session = session or self.session
        response = self.client.get(f"/station/api/sessions/{session.pk}/components")
        self.assertEqual(response.status_code, 200)
        return {c["sequence"]: c for c in response.json()["components"]}

    def test_the_component_bar_uses_its_display_max(self):
        yellow = self.session.selection.components.get(sequence=YELLOW)

        self.assertEqual(component_rules(yellow).bar, BarScale(Decimal(125)))

    def test_bar_geometry_of_every_teal_4c_component(self):
        """Prototype display max 1600 / 520 / 125 g, 32 / 14 kg."""
        self.assertEqual(
            {seq: c["bar"] for seq, c in self.components().items()},
            {
                1: {
                    "lowPercent": "77.1",
                    "widthPercent": "0.8",
                    "targetPercent": "77.5",
                },
                2: {
                    "lowPercent": "73.8",
                    "widthPercent": "0.8",
                    "targetPercent": "74.2",
                },
                3: {
                    "lowPercent": "74.8",
                    "widthPercent": "0.8",
                    "targetPercent": "75.2",
                },
                4: {
                    "lowPercent": "74.6",
                    "widthPercent": "0.8",
                    "targetPercent": "75.0",
                },
                5: {
                    "lowPercent": "68.2",
                    "widthPercent": "0.7",
                    "targetPercent": "68.6",
                },
            },
        )

    def test_rail_and_header_fields_of_yellow_rgb(self):
        yellow = self.components()[YELLOW]

        self.assertEqual(
            {k: yellow[k] for k in ("displayMax", "displayMaxText", "targetAmount")},
            {
                "displayMax": "125.0000",
                "displayMaxText": "125.0 g",
                "targetAmount": "94.0",
            },
        )
        self.assertEqual(yellow["scale"]["classText"], "3 kg")
        self.assertEqual(
            yellow["headerMeta"],
            "DYE-4471 · LOT 2026-0387 · CONTAINER C-12 · TARE 214 g",
        )
        self.assertEqual(
            yellow["header"], "Remazol Yellow RGB · " + yellow["headerMeta"]
        )

    def test_floor_scale_fields_of_sodium_sulphate(self):
        sodium = self.components()[SODIUM]

        self.assertEqual(
            (
                sodium["displayMaxText"],
                sodium["targetAmount"],
                sodium["scale"]["classText"],
            ),
            ("32.000 kg", "24.000", "32 kg"),
        )

    def test_colour_comes_from_the_recipe_snapshot(self):
        session = factories.session(
            factories.teal_selection({YELLOW: {"colour": "#d9a520"}}, batch_id="B-1")
        )

        self.assertEqual(self.components(session)[YELLOW]["colour"], "#d9a520")

    def test_a_missing_lot_shows_in_the_header_meta(self):
        session = factories.session(
            factories.teal_selection({YELLOW: {"lot": ""}}, batch_id="B-1")
        )

        self.assertEqual(
            self.components(session)[YELLOW]["headerMeta"],
            "DYE-4471 · LOT — · CONTAINER C-12 · TARE 214 g",
        )


class EvaluationBarApiTests(TestCase):
    def setUp(self):
        self.session = factories.session()

    def bar_percent(self, net, unit="g", sequence=YELLOW):
        response = self.client.get(
            f"/station/api/sessions/{self.session.pk}/components/{sequence}/evaluation",
            {"net": net, "unit": unit},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["barPercent"]

    def test_fill_follows_the_reading(self):
        self.assertEqual(
            [self.bar_percent(n) for n in ("0.0", "93.4", "94.2", "96.4", "200")],
            ["0.0", "74.7", "75.4", "77.1", "100.0"],
        )

    def test_fill_uses_the_value_at_display_resolution(self):
        """94.24 g is shown as 94.2 g (ADR-009), so it fills like 94.2 g."""
        self.assertEqual(self.bar_percent("94.24"), self.bar_percent("94.2"))

    def test_a_reading_in_kg_fills_the_g_bar(self):
        self.assertEqual(self.bar_percent("0.0942", "kg"), "75.4")

    def test_floor_scale_fill(self):
        self.assertEqual(self.bar_percent("24.048", "kg", SODIUM), "75.2")
