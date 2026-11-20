"""Story 001-seed-training-scenario: the prototype scenario is seeded exactly."""

from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from dummy_orgatex.models import (
    DummyBatch,
    DummyConsumption,
    DummyRecipe,
    DummyRecipeComponent,
)
from dummy_orgatex.services import accept_consumption, seed_training_scenario

EXPECTED_BATCHES = [
    ("B-24187", "SO-9931", "JET-04", "100% CTN knit · 480 kg", "Teal 4C", 5),
    ("B-24188", "SO-9931", "JET-07", "100% CTN knit · 520 kg", "Teal 4C", 5),
    ("B-24190", "SO-9944", "JET-02", "CVC fleece · 310 kg", "Navy 12", 7),
    ("B-24191", "SO-9947", "WINCH-01", "Viscose jersey · 190 kg", "Rose 08", 4),
]

# (code, name, colour, target, unit, tolerance, display max, lot, container, tare)
EXPECTED_COMPONENTS = [
    ("DYE-1180", "Remazol Brill. Blue RSPL", "#1f4fa8", "1240.0", "g", "6.0",
     "1600", "2026-0341", "C-09", "214"),
    ("DYE-2204", "Remazol Red RB", "#b8253a", "386.0", "g", "2.0",
     "520", "2026-0298", "C-11", "214"),
    ("DYE-4471", "Remazol Yellow RGB", "#d9a520", "94.0", "g", "0.5",
     "125", "2026-0387", "C-12", "214"),
    ("AUX-0101", "Sodium Sulphate", "#c9d2dc", "24.000", "kg", "0.120",
     "32", "2026-0112", "D-03", "1.850"),
    ("AUX-0107", "Soda Ash", "#e4eaf0", "9.600", "kg", "0.048",
     "14", "2026-0155", "D-05", "1.850"),
]  # fmt: skip


def _snapshot():
    batches = list(
        DummyBatch.objects.values_list(
            "batch_id", "order_id", "machine", "fabric_lot", "shade",
            "component_count", "status", "queue_position",
        )
    )  # fmt: skip
    components = list(
        DummyRecipeComponent.objects.order_by("sequence").values_list(
            "recipe__batch__batch_id", "sequence", "code", "target_qty", "unit",
            "tolerance", "display_max", "lot", "container", "tare", "state",
        )
    )  # fmt: skip
    return batches, components


class SeedTrainingScenarioTests(TestCase):
    def setUp(self):
        seed_training_scenario()

    def test_seed_loads_four_queued_batches_with_prototype_fields(self):
        rows = list(
            DummyBatch.objects.values_list(
                "batch_id", "order_id", "machine", "fabric_lot", "shade",
                "component_count",
            )
        )  # fmt: skip
        self.assertEqual(rows, EXPECTED_BATCHES)
        self.assertEqual(
            set(DummyBatch.objects.values_list("status", flat=True)), {"QUEUED"}
        )

    def test_only_b24187_has_a_recipe(self):
        self.assertEqual(
            list(DummyRecipe.objects.values_list("batch__batch_id", "name")),
            [("B-24187", "Teal 4C")],
        )

    def test_teal_4c_has_five_components_with_exact_decimal_values(self):
        components = list(
            DummyRecipeComponent.objects.filter(recipe__batch__batch_id="B-24187")
        )
        self.assertEqual([c.sequence for c in components], [1, 2, 3, 4, 5])
        for comp, expected in zip(components, EXPECTED_COMPONENTS, strict=True):
            code, name, colour, target, unit, tol, dmax, lot, cont, tare = expected
            with self.subTest(code=code):
                self.assertEqual(comp.code, code)
                self.assertEqual(comp.name, name)
                self.assertEqual(comp.colour, colour)
                self.assertIsInstance(comp.target_qty, Decimal)
                self.assertEqual(comp.target_qty, Decimal(target))
                self.assertEqual(comp.unit, unit)
                self.assertEqual(comp.tolerance, Decimal(tol))
                self.assertEqual(comp.display_max, Decimal(dmax))
                self.assertEqual(comp.lot, lot)
                self.assertEqual(comp.container, cont)
                self.assertEqual(comp.tare, Decimal(tare))

    def test_all_components_start_pending(self):
        self.assertEqual(
            set(DummyRecipeComponent.objects.values_list("state", flat=True)),
            {"pending"},
        )

    def test_reseed_resets_to_the_same_state_without_duplicates(self):
        before = _snapshot()
        accept_consumption(
            "B-24187",
            {
                "idempotencyKey": "K-reseed",
                "components": [{"code": "DYE-4471", "actualQty": "94.2", "unit": "g"}],
            },
        )

        seed_training_scenario()

        self.assertEqual(_snapshot(), before)
        self.assertEqual(DummyBatch.objects.count(), 4)
        self.assertEqual(DummyRecipeComponent.objects.count(), 5)
        self.assertEqual(DummyConsumption.objects.count(), 0)

    def test_seed_training_command_loads_the_scenario(self):
        DummyBatch.objects.all().delete()
        out = StringIO()

        call_command("seed_training", stdout=out)

        self.assertEqual(DummyBatch.objects.count(), 4)
        self.assertIn("Seeded", out.getvalue())
