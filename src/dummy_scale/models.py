"""Dummy Scale state. Training contract only, not a real scale interface.

Quantities are Decimal (decimal(12,4)) in the scale's own unit: the 3 kg
precision scale reports in g, the 32 kg floor scale in kg.
"""

from django.db import models


class DummyScale(models.Model):
    STATUS_READY = "ready"
    STATUS_DISCONNECTED = "disconnected"
    STATUS_CHOICES = (
        (STATUS_READY, "Ready"),
        (STATUS_DISCONNECTED, "Disconnected"),
    )

    scale_id = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=64)
    capacity = models.DecimalField(max_digits=12, decimal_places=4)
    unit = models.CharField(max_length=8)
    net_weight = models.DecimalField(max_digits=12, decimal_places=4)
    read_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)

    class Meta:
        ordering = ("scale_id",)

    def __str__(self):
        return self.scale_id
