"""Batch selection and its read-only recipe snapshot (unit 004, ADR-003).

A ``BatchSelection`` is the station's record that a batch was opened, with a
copy of the batch header and the recipe as OrgaTEX sent them at that moment.
The copy is a cache for resume and records, never the source of truth
(C-01, DR-03). Rows are immutable: they can be created, never changed or
deleted.
"""

from django.db import models
from django.utils import timezone

QUANTITY = {"max_digits": 12, "decimal_places": 4}


class SnapshotImmutable(Exception):
    """Raised when code tries to change or delete a stored snapshot row."""


class ImmutableModel(models.Model):
    """Rows can be inserted once; ``save()`` on a stored row and ``delete()`` fail.

    Bulk ``QuerySet.update()`` / ``delete()`` bypass these checks and must not be
    used on snapshot models (ADR-003).
    """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise SnapshotImmutable(
                f"{type(self).__name__} {self.pk} is a read-only snapshot"
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise SnapshotImmutable(f"{type(self).__name__} {self.pk} cannot be deleted")


class SelectionMethod(models.TextChoices):
    SCAN = "scan", "Scan"
    TOUCH = "touch", "Touch"


class Unit(models.TextChoices):
    GRAM = "g", "g"
    KILOGRAM = "kg", "kg"


class BatchSelectionManager(models.Manager):
    def latest_for_batch(self, batch_id: str):
        """Most recent selection of ``batch_id``, or ``None``."""
        return self.filter(batch_id=batch_id).first()


class BatchSelection(ImmutableModel):
    batch_id = models.CharField(max_length=32, db_index=True)
    order_id = models.CharField(max_length=32)
    machine = models.CharField(max_length=32)
    fabric_lot = models.CharField(max_length=100)
    shade = models.CharField(max_length=64)
    component_count = models.PositiveSmallIntegerField()
    batch_status = models.CharField(max_length=32)
    method = models.CharField(max_length=5, choices=SelectionMethod.choices)
    recipe_name = models.CharField(max_length=64)
    selected_at = models.DateTimeField(default=timezone.now)

    objects = BatchSelectionManager()

    class Meta:
        ordering = ("-selected_at", "-pk")

    def __str__(self):
        return f"{self.batch_id} ({self.recipe_name}) selected {self.selected_at}"


class SnapshotComponent(ImmutableModel):
    selection = models.ForeignKey(
        BatchSelection, on_delete=models.PROTECT, related_name="components"
    )
    sequence = models.PositiveSmallIntegerField()
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=100)
    colour = models.CharField(max_length=16)
    target_qty = models.DecimalField(**QUANTITY)
    unit = models.CharField(max_length=2, choices=Unit.choices)
    tolerance = models.DecimalField(**QUANTITY)
    display_max = models.DecimalField(**QUANTITY)
    lot = models.CharField(max_length=32)
    container = models.CharField(max_length=32)
    tare = models.DecimalField(**QUANTITY)
    orgatex_state = models.CharField(max_length=16)

    class Meta:
        ordering = ("sequence",)
        constraints = (
            models.UniqueConstraint(
                fields=("selection", "sequence"), name="unique_sequence_per_selection"
            ),
        )

    def __str__(self):
        return f"{self.sequence}. {self.code} {self.name}"
