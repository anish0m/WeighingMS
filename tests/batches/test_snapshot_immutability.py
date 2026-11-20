"""ADR-003 / C-01: a stored recipe snapshot can never be changed or deleted."""

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from batches.models import BatchSelection, SnapshotComponent, SnapshotImmutable


def make_selection():
    selection = BatchSelection.objects.create(
        batch_id="B-24187",
        order_id="SO-9931",
        machine="JET-04",
        fabric_lot="100% CTN knit · 480 kg",
        shade="Teal 4C",
        component_count=1,
        batch_status="QUEUED",
        method="touch",
        recipe_name="Teal 4C",
    )
    SnapshotComponent.objects.create(
        selection=selection,
        sequence=1,
        code="DYE-4471",
        name="Remazol Yellow RGB",
        colour="#d9a520",
        target_qty=Decimal("94.0000"),
        unit="g",
        tolerance=Decimal("0.5000"),
        display_max=Decimal("125.0000"),
        lot="2026-0387",
        container="C-12",
        tare=Decimal("214.0000"),
        orgatex_state="pending",
    )
    return selection


class SnapshotImmutabilityTests(TestCase):
    def setUp(self):
        self.selection = make_selection()
        self.component = self.selection.components.get()

    def test_changed_selection_cannot_be_saved(self):
        self.selection.recipe_name = "Changed"

        with self.assertRaises(SnapshotImmutable):
            self.selection.save()

        self.assertEqual(BatchSelection.objects.get().recipe_name, "Teal 4C")

    def test_changed_component_cannot_be_saved(self):
        self.component.target_qty = Decimal("95.0")

        with self.assertRaises(SnapshotImmutable):
            self.component.save()

        self.assertEqual(SnapshotComponent.objects.get().target_qty, Decimal("94.0"))

    def test_selection_cannot_be_deleted(self):
        with self.assertRaises(SnapshotImmutable):
            self.selection.delete()

        self.assertEqual(BatchSelection.objects.count(), 1)

    def test_component_cannot_be_deleted(self):
        with self.assertRaises(SnapshotImmutable):
            self.component.delete()

        self.assertEqual(SnapshotComponent.objects.count(), 1)

    def test_selection_with_components_is_protected_even_in_bulk(self):
        with self.assertRaises(ProtectedError):
            BatchSelection.objects.all().delete()

        self.assertEqual(BatchSelection.objects.count(), 1)

    def test_sequence_is_unique_within_a_selection(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            SnapshotComponent.objects.create(
                selection=self.selection,
                sequence=1,
                code="DYE-1180",
                name="Remazol Brill. Blue RSPL",
                colour="#1f4fa8",
                target_qty=Decimal(1240),
                unit="g",
                tolerance=Decimal(6),
                display_max=Decimal(1600),
                lot="2026-0341",
                container="C-09",
                tare=Decimal(214),
                orgatex_state="pending",
            )

    def test_new_rows_can_still_be_created(self):
        make_selection()

        self.assertEqual(BatchSelection.objects.count(), 2)
