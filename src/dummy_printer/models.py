"""Dummy Printer state. Training contract only, not a real printer interface."""

from django.db import models


class DummyTicket(models.Model):
    content = models.TextField()
    batch_id = models.CharField(max_length=32, blank=True)
    printed_at = models.DateTimeField()

    class Meta:
        ordering = ("printed_at", "id")

    def __str__(self):
        return f"ticket {self.pk}"


class DummyPrinterState(models.Model):
    """Training failure switch for the Dummy Printer (single row)."""

    MODE_OK = "ok"
    MODE_ERROR = "error"
    MODE_CHOICES = ((MODE_OK, "OK"), (MODE_ERROR, "Error"))

    mode = models.CharField(max_length=16, choices=MODE_CHOICES, default=MODE_OK)

    def __str__(self):
        return self.mode
