"""Dummy Scale state. Training contract only, not a real scale interface.

Endpoints, tare, simulate controls and failure modes are added in bolt 002.
"""

from django.db import models


class DummyScale(models.Model):
    STATUS_READY = "ready"
    STATUS_CHOICES = ((STATUS_READY, "Ready"),)

    scale_id = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=64)
    capacity = models.DecimalField(max_digits=12, decimal_places=4)
    unit = models.CharField(max_length=8)
    net_weight = models.DecimalField(max_digits=12, decimal_places=4)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)

    class Meta:
        ordering = ("scale_id",)

    def __str__(self):
        return self.scale_id
