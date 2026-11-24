"""Print log: one row per attempt to print a batch's weighing ticket (FR-18).

``session_id`` and ``operator_id`` are plain values, as in ``orgatex``'s
WriteBack. A job is ``printed`` only after the server has read the ticket
back from the printer; a failed job stays failed and a new print is a new job.
"""

from django.db import models
from django.utils import timezone


class PrintStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PRINTED = "printed", "Printed"
    FAILED = "failed", "Failed"


class PrintJob(models.Model):
    session_id = models.PositiveIntegerField(db_index=True)
    batch_id = models.CharField(max_length=32)
    is_reprint = models.BooleanField()
    # Exactly the text that was sent to the printer.
    content = models.TextField()
    status = models.CharField(
        max_length=16, choices=PrintStatus.choices, default=PrintStatus.PENDING
    )
    printer_ticket_id = models.PositiveIntegerField(null=True, blank=True, unique=True)
    # The printer's own time, as read back.
    printed_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=200, blank=True, default="")
    operator_id = models.CharField(max_length=16)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("created_at", "pk")
        constraints = (
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status="printed",
                        printer_ticket_id__isnull=False,
                        printed_at__isnull=False,
                    )
                    | (
                        ~models.Q(status="printed")
                        & models.Q(printer_ticket_id__isnull=True)
                        & models.Q(printed_at__isnull=True)
                    )
                ),
                name="printed_fields_only_when_printed",
            ),
        )

    def __str__(self):
        return f"print {self.pk} {self.batch_id} ({self.status})"
