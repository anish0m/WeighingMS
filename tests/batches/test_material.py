"""Story 005-show-lot-and-container: component header, tare text, lot/container faults.

Pure rules on the recipe snapshot (``batches.material``, ADR-007). One live test
checks the headers of the real seeded B-24187 taken through the OrgaTEX adapter.
"""

from decimal import Decimal

from django.test import LiveServerTestCase, SimpleTestCase, TestCase, override_settings

from batches.material import (
    MaterialFault,
    format_quantity,
    header_for,
    material_faults,
)
from batches.models import SnapshotComponent
from batches.services import select_batch
from dummy_orgatex.services import seed_training_scenario
from tests.weighing import factories

YELLOW_HEADER = (
    "Remazol Yellow RGB · DYE-4471 · LOT 2026-0387 · CONTAINER C-12 · TARE 214 g"
)
SODIUM_HEADER = (
    "Sodium Sulphate · AUX-0101 · LOT 2026-0112 · CONTAINER D-03 · TARE 1.850 kg"
)


class FormatQuantityTests(SimpleTestCase):
    def test_whole_grams_have_no_decimals(self):
        self.assertEqual(format_quantity(Decimal("214.0000"), "g"), "214 g")

    def test_grams_keep_their_meaningful_decimals(self):
        self.assertEqual(format_quantity(Decimal("214.5000"), "g"), "214.5 g")
        self.assertEqual(format_quantity(Decimal("0.5000"), "g"), "0.5 g")

    def test_kilograms_have_three_decimals(self):
        self.assertEqual(format_quantity(Decimal("1.8500"), "kg"), "1.850 kg")
        self.assertEqual(format_quantity(Decimal("24.0000"), "kg"), "24.000 kg")

    def test_kilograms_are_never_rounded_away(self):
        self.assertEqual(format_quantity(Decimal("1.8505"), "kg"), "1.8505 kg")

    def test_large_whole_grams_are_not_written_as_exponents(self):
        self.assertEqual(format_quantity(Decimal("1240.0000"), "g"), "1240 g")


class HeaderTests(TestCase):
    def setUp(self):
        self.components = {
            c.sequence: c for c in factories.teal_selection().components.all()
        }

    def test_yellow_rgb_header(self):
        """Story 005 AC 1."""
        header = header_for(self.components[factories.YELLOW_RGB])

        self.assertEqual(header.text, YELLOW_HEADER)

    def test_sodium_sulphate_shows_d03_and_1850_kg(self):
        """Story 005 AC 3."""
        header = header_for(self.components[factories.SODIUM_SULPHATE])

        self.assertEqual((header.container, header.tare_text), ("D-03", "1.850 kg"))
        self.assertEqual(header.text, SODIUM_HEADER)

    def test_missing_lot_and_container_are_shown_as_a_dash(self):
        component = SnapshotComponent(
            code="DYE-4471",
            name="Remazol Yellow RGB",
            unit="g",
            lot=" ",
            container="",
            tare=Decimal(214),
        )

        self.assertEqual(
            header_for(component).text,
            "Remazol Yellow RGB · DYE-4471 · LOT — · CONTAINER — · TARE 214 g",
        )


class MaterialFaultTests(SimpleTestCase):
    def component(self, lot="2026-0387", container="C-12"):
        return SnapshotComponent(lot=lot, container=container)

    def test_complete_component_has_no_faults(self):
        self.assertEqual(material_faults(self.component()), [])

    def test_missing_lot(self):
        self.assertEqual(
            material_faults(self.component(lot="")), [MaterialFault.LOT_MISSING]
        )

    def test_blank_lot_counts_as_missing(self):
        self.assertEqual(
            material_faults(self.component(lot="  ")), [MaterialFault.LOT_MISSING]
        )

    def test_missing_container(self):
        self.assertEqual(
            material_faults(self.component(container="")),
            [MaterialFault.CONTAINER_MISSING],
        )

    def test_lot_is_reported_before_container(self):
        self.assertEqual(
            material_faults(self.component(lot="", container="")),
            [MaterialFault.LOT_MISSING, MaterialFault.CONTAINER_MISSING],
        )


class SeededHeaderTests(LiveServerTestCase):
    """The headers of the real Dummy OrgaTEX seed (OQ-7), via the adapter."""

    def test_b24187_headers_come_from_the_seed(self):
        seed_training_scenario()
        self.enterContext(
            override_settings(ORGATEX_BASE_URL=f"{self.live_server_url}/api")
        )

        selection = select_batch("B-24187", "touch")
        headers = {c.sequence: header_for(c).text for c in selection.components.all()}

        self.assertEqual(headers[3], YELLOW_HEADER)
        self.assertEqual(headers[4], SODIUM_HEADER)
        self.assertEqual(len(headers), 5)
