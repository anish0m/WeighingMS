"""Write-back state: one consumption posting per weighing session (FR-17).

``session_id`` and ``operator_id`` are plain values, not foreign keys, so this
app does not depend on ``weighing`` (the dependency runs ``weighing`` ->
``orgatex``). The row is the status the operator sees; the weighing records
themselves are never touched by write-back.
"""

from django.db import models


class WriteBackStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    NOT_WRITTEN = "not_written", "Not written"


class WriteBack(models.Model):
    session_id = models.PositiveIntegerField(unique=True)
    batch_id = models.CharField(max_length=32, db_index=True)
    idempotency_key = models.CharField(max_length=128, unique=True)
    status = models.CharField(
        max_length=16, choices=WriteBackStatus.choices, default=WriteBackStatus.PENDING
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    # OrgaTEX's own acceptance time, as read back through the adapter.
    confirmed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=200, blank=True, default="")
    operator_id = models.CharField(max_length=16)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = (
            models.CheckConstraint(
                condition=models.Q(status="confirmed", confirmed_at__isnull=False)
                | (~models.Q(status="confirmed") & models.Q(confirmed_at__isnull=True)),
                name="confirmed_at_only_when_confirmed",
            ),
        )

    def __str__(self):
        return f"{self.idempotency_key} ({self.status})"

    @property
    def is_confirmed(self) -> bool:
        return self.status == WriteBackStatus.CONFIRMED
