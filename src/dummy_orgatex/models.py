"""Dummy OrgaTEX state.

Training contract defined by this project. It is not the real OrgaTEX
interface; the brief's open questions (A-01 to A-15) stay unresolved.
All quantities are Decimal (decimal(12,4)), never float.
"""

from django.db import models


class DummyBatch(models.Model):
    STATUS_QUEUED = "QUEUED"
    STATUS_CHOICES = ((STATUS_QUEUED, "Queued"),)

    batch_id = models.CharField(max_length=32, unique=True)
    order_id = models.CharField(max_length=32)
    machine = models.CharField(max_length=32)
    fabric_lot = models.CharField(max_length=128)
    shade = models.CharField(max_length=64)
    component_count = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    queue_position = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ("queue_position",)

    def __str__(self):
        return self.batch_id


class DummyRecipe(models.Model):
    batch = models.OneToOneField(
        DummyBatch, on_delete=models.CASCADE, related_name="recipe"
    )
    name = models.CharField(max_length=64)

    def __str__(self):
        return f"{self.batch.batch_id} {self.name}"


class DummyRecipeComponent(models.Model):
    STATE_PENDING = "pending"
    STATE_CHOICES = ((STATE_PENDING, "Pending"),)

    recipe = models.ForeignKey(
        DummyRecipe, on_delete=models.CASCADE, related_name="components"
    )
    sequence = models.PositiveSmallIntegerField()
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=128)
    colour = models.CharField(max_length=7)
    target_qty = models.DecimalField(max_digits=12, decimal_places=4)
    unit = models.CharField(max_length=8)
    tolerance = models.DecimalField(max_digits=12, decimal_places=4)
    display_max = models.DecimalField(max_digits=12, decimal_places=4)
    lot = models.CharField(max_length=32)
    container = models.CharField(max_length=32)
    tare = models.DecimalField(max_digits=12, decimal_places=4)
    state = models.CharField(max_length=16, choices=STATE_CHOICES)

    class Meta:
        ordering = ("sequence",)
        constraints = (
            models.UniqueConstraint(
                fields=("recipe", "sequence"), name="unique_component_sequence"
            ),
            models.UniqueConstraint(
                fields=("recipe", "code"), name="unique_component_code"
            ),
        )

    def __str__(self):
        return f"{self.sequence} {self.code}"


class DummyConsumption(models.Model):
    batch = models.ForeignKey(
        DummyBatch, on_delete=models.CASCADE, related_name="consumptions"
    )
    idempotency_key = models.CharField(max_length=128, unique=True)
    accepted_at = models.DateTimeField()

    class Meta:
        ordering = (
            "accepted_at",
            "id",
        )

    def __str__(self):
        return f"{self.batch.batch_id} {self.idempotency_key}"


class DummyConsumptionLine(models.Model):
    consumption = models.ForeignKey(
        DummyConsumption, on_delete=models.CASCADE, related_name="lines"
    )
    code = models.CharField(max_length=32)
    actual_qty = models.DecimalField(max_digits=12, decimal_places=4)
    unit = models.CharField(max_length=8)

    class Meta:
        ordering = ("id",)

    def __str__(self):
        return f"{self.code} {self.actual_qty} {self.unit}"


class DummyOrgatexState(models.Model):
    """Training failure switch for Dummy OrgaTEX (single row)."""

    MODE_OK = "ok"
    MODE_UNAVAILABLE = "unavailable"
    MODE_CHOICES = ((MODE_OK, "OK"), (MODE_UNAVAILABLE, "Unavailable"))

    mode = models.CharField(max_length=16, choices=MODE_CHOICES, default=MODE_OK)

    def __str__(self):
        return self.mode
