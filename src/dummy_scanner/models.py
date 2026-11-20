"""Dummy Scanner state. Training contract only, not a real scanner interface."""

from django.db import models


class DummyScan(models.Model):
    KIND_BATCH = "batch"
    KIND_DYESTUFF = "dyestuff"
    KIND_CHOICES = ((KIND_BATCH, "Batch"), (KIND_DYESTUFF, "Dyestuff"))

    kind = models.CharField(max_length=16, choices=KIND_CHOICES)
    code = models.CharField(max_length=64)
    scanned_at = models.DateTimeField()

    class Meta:
        ordering = ("scanned_at", "id")

    def __str__(self):
        return f"{self.kind} {self.code}"


class DummyScannerState(models.Model):
    """Training failure switch for the Dummy Scanner (single row)."""

    MODE_OK = "ok"
    MODE_UNAVAILABLE = "unavailable"
    MODE_CHOICES = ((MODE_OK, "OK"), (MODE_UNAVAILABLE, "Unavailable"))

    mode = models.CharField(max_length=16, choices=MODE_CHOICES, default=MODE_OK)

    def __str__(self):
        return self.mode
