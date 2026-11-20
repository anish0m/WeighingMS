"""Stories 002-select-batch and 003-load-read-only-recipe: selection rules.

``select_batch`` reads the seeded Dummy OrgaTEX over real HTTP. The few cases
the seed cannot produce (a status that is not released, a broken recipe)
stub the OrgaTEX adapter, the integration boundary.
"""

from decimal import Decimal
from unittest.mock import patch

from django.test import LiveServerTestCase, SimpleTestCase, override_settings

from batches import services
from batches.models import BatchSelection, SnapshotComponent
from batches.services import InvalidRecipe, RefusalReason, SelectionRefused
from dummy_orgatex.services import seed_training_scenario
from orgatex.adapter import OrgatexNotFound, Recipe
from tests.batches import factories
from tests.helpers import set_mode

LOGGER = "batches.services"
TEAL_4C = [
    "Remazol Brill. Blue RSPL",
    "Remazol Red RB",
    "Remazol Yellow RGB",
    "Sodium Sulphate",
    "Soda Ash",
]


class LiveSelectionTestCase(LiveServerTestCase):
    def setUp(self):
        seed_training_scenario()
        self.enterContext(
            override_settings(ORGATEX_BASE_URL=f"{self.live_server_url}/api")
        )

    def assert_refused(self, reason, batch_code="B-24187", method="touch"):
        with self.assertRaises(SelectionRefused) as caught:
            services.select_batch(batch_code, method)
        self.assertEqual(caught.exception.reason, reason)
        self.assertEqual(BatchSelection.objects.count(), 0)
        self.assertEqual(SnapshotComponent.objects.count(), 0)
        return caught.exception


class SelectBatchTests(LiveSelectionTestCase):
    def test_touching_b24187_opens_it_with_its_header(self):
        selection = services.select_batch("B-24187", "touch")

        self.assertEqual(
            (selection.batch_id, selection.order_id, selection.machine),
            ("B-24187", "SO-9931", "JET-04"),
        )
        self.assertEqual(
            (selection.shade, selection.batch_status), ("Teal 4C", "QUEUED")
        )
        self.assertEqual(selection.method, "touch")

    def test_scanning_opens_the_same_batch(self):
        selection = services.select_batch("B-24187", "scan")

        self.assertEqual((selection.batch_id, selection.method), ("B-24187", "scan"))
        self.assertEqual(selection.components.count(), 5)

    def test_selection_is_logged(self):
        with self.assertLogs(LOGGER, "INFO") as logs:
            services.select_batch("B-24187", "touch")

        self.assertIn("BatchSelected", logs.output[-1])
        self.assertIn("B-24187", logs.output[-1])


class RecipeSnapshotTests(LiveSelectionTestCase):
    def test_recipe_is_teal_4c_with_five_components_in_sequence(self):
        selection = services.select_batch("B-24187", "touch")

        components = list(selection.components.all())
        self.assertEqual(selection.recipe_name, "Teal 4C")
        self.assertEqual([c.name for c in components], TEAL_4C)
        self.assertEqual([c.sequence for c in components], [1, 2, 3, 4, 5])

    def test_quantities_are_decimals_with_prototype_values(self):
        services.select_batch("B-24187", "touch")

        stored = SnapshotComponent.objects.get(code="DYE-4471")
        self.assertIsInstance(stored.target_qty, Decimal)
        self.assertEqual(
            (stored.target_qty, stored.unit, stored.tolerance),
            (Decimal("94.0"), "g", Decimal("0.5")),
        )
        self.assertEqual(stored.display_max, Decimal("125.0"))

    def test_floor_scale_components_keep_kg(self):
        services.select_batch("B-24187", "touch")

        soda_ash = SnapshotComponent.objects.get(code="AUX-0107")
        self.assertEqual(
            (soda_ash.target_qty, soda_ash.unit, soda_ash.tolerance),
            (Decimal("9.6"), "kg", Decimal("0.048")),
        )

    def test_lot_container_and_tare_are_kept(self):
        services.select_batch("B-24187", "touch")

        blue = SnapshotComponent.objects.get(sequence=1)
        self.assertEqual(
            (blue.code, blue.lot, blue.container, blue.tare),
            ("DYE-1180", "2026-0341", "C-09", Decimal(214)),
        )

    def test_each_selection_stores_a_new_snapshot(self):
        first = services.select_batch("B-24187", "touch")
        second = services.select_batch("B-24187", "scan")

        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(SnapshotComponent.objects.count(), 10)
        self.assertEqual(BatchSelection.objects.latest_for_batch("B-24187"), second)

    def test_latest_for_unselected_batch_is_none(self):
        self.assertIsNone(BatchSelection.objects.latest_for_batch("B-24190"))


class RefusalTests(LiveSelectionTestCase):
    def test_unknown_batch_is_not_found_and_nothing_opens(self):
        refusal = self.assert_refused(RefusalReason.BATCH_NOT_FOUND, "B-99999", "scan")

        self.assertEqual(refusal.message, "Batch not found")

    def test_batch_without_training_recipe_is_not_selectable(self):
        refusal = self.assert_refused(RefusalReason.RECIPE_NOT_AVAILABLE, "B-24188")

        self.assertEqual(refusal.message, "Recipe not available in training data")

    def test_every_queued_batch_without_recipe_is_refused(self):
        for batch_code in ("B-24188", "B-24190", "B-24191"):
            with self.subTest(batch=batch_code):
                self.assert_refused(RefusalReason.RECIPE_NOT_AVAILABLE, batch_code)

    def test_orgatex_unavailable_means_weighing_does_not_start(self):
        set_mode(self.client, "orgatex", "unavailable")

        refusal = self.assert_refused(RefusalReason.ORGATEX_UNAVAILABLE)

        self.assertEqual(refusal.message, "OrgaTEX unavailable")

    def test_unreachable_orgatex_is_unavailable(self):
        with override_settings(ORGATEX_BASE_URL="http://127.0.0.1:9/api"):
            self.assert_refused(RefusalReason.ORGATEX_UNAVAILABLE)

    def test_refusal_is_logged_with_reason(self):
        with self.assertLogs(LOGGER, "INFO") as logs:
            self.assert_refused(RefusalReason.BATCH_NOT_FOUND, "B-99999")

        self.assertIn("BatchSelectionRefused", logs.output[-1])
        self.assertIn("BATCH_NOT_FOUND", logs.output[-1])


@patch("batches.services.adapter")
class StubbedAdapterTests(LiveSelectionTestCase):
    """Cases the seed cannot produce; the OrgaTEX adapter is the boundary."""

    def test_batch_that_is_not_released_is_refused_before_the_recipe(self, adapter):
        adapter.fetch_batch.return_value = factories.batch(status="WEIGHED")

        refusal = self.assert_refused(RefusalReason.NOT_RELEASED)

        self.assertEqual(refusal.message, "Batch not released")
        adapter.fetch_recipe.assert_not_called()

    def test_recipe_breaking_an_invariant_is_treated_as_unavailable(self, adapter):
        adapter.fetch_batch.return_value = factories.batch()
        adapter.fetch_recipe.return_value = factories.recipe(
            factories.component(1), factories.component(3)
        )

        with self.assertLogs(LOGGER, "WARNING") as logs:
            self.assert_refused(RefusalReason.ORGATEX_UNAVAILABLE)

        self.assertIn("rejected", logs.output[0])

    def test_batch_gone_when_reading_recipe_is_not_found(self, adapter):
        adapter.fetch_batch.return_value = factories.batch()
        adapter.fetch_recipe.side_effect = OrgatexNotFound(
            "BATCH_NOT_FOUND", "Batch not found: B-24187"
        )

        self.assert_refused(RefusalReason.BATCH_NOT_FOUND)


class SelectionPolicyTests(SimpleTestCase):
    def test_queued_batch_is_selectable(self):
        self.assertIsNone(services.check_selectable(factories.batch(status="QUEUED")))

    def test_other_status_is_not_released(self):
        for status in ("WEIGHED", "IN_PROGRESS", "queued", ""):
            with self.subTest(status=status):
                self.assertEqual(
                    services.check_selectable(factories.batch(status=status)),
                    RefusalReason.NOT_RELEASED,
                )


class RecipeInvariantTests(SimpleTestCase):
    def test_valid_recipe_passes(self):
        services.check_recipe(factories.recipe())

    def assert_invalid(self, *components):
        with self.assertRaises(InvalidRecipe):
            services.check_recipe(factories.recipe(*components))

    def test_recipe_without_components_is_invalid(self):
        with self.assertRaises(InvalidRecipe):
            services.check_recipe(Recipe("B-24187", "Teal 4C", ()))

    def test_sequence_gap_is_invalid(self):
        self.assert_invalid(factories.component(1), factories.component(3))

    def test_sequence_out_of_order_is_invalid(self):
        self.assert_invalid(factories.component(2), factories.component(1))

    def test_unknown_unit_is_invalid(self):
        self.assert_invalid(factories.component(1, unit="lb"))

    def test_zero_target_is_invalid(self):
        self.assert_invalid(factories.component(1, target_qty=Decimal(0)))

    def test_negative_tolerance_is_invalid(self):
        self.assert_invalid(factories.component(1, tolerance=Decimal("-0.1")))

    def test_zero_tolerance_is_valid(self):
        services.check_recipe(
            factories.recipe(factories.component(1, tolerance=Decimal(0)))
        )
