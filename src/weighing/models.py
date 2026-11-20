"""Weighing station foundation: identities and the weighing session (unit 005).

Operators and supervisors are seeded training identities, not Django users
(ADR-004). A ``WeighingSession`` is the weighing of one selected batch by one
operator; later bolts add components, records and completion to it.
"""

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone

from batches.models import BatchSelection


class SessionNotDeletable(Exception):
    """Raised when code tries to delete a weighing session (NFR-12)."""


class OperatorManager(models.Manager):
    def active(self):
        return self.filter(active=True)


class Operator(models.Model):
    """A seeded operator, chosen from a list without a password (OQ-3)."""

    operator_id = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=64)
    shift = models.CharField(max_length=8)
    active = models.BooleanField(default=True)

    objects = OperatorManager()

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.display

    @property
    def display(self) -> str:
        """Header form, e.g. "R. Karim · Shift A"."""
        return f"{self.name} · Shift {self.shift}"


class Supervisor(models.Model):
    """A seeded supervisor; authenticates with ID + PIN (OQ-3, NFR-4).

    Only a hash of the PIN is stored (ADR-004).
    """

    supervisor_id = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=64)
    pin_hash = models.CharField(max_length=128)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.supervisor_id} {self.name}"

    def set_pin(self, pin: str) -> None:
        self.pin_hash = make_password(pin)

    def check_pin(self, pin: str) -> bool:
        return check_password(pin, self.pin_hash)


class SessionState(models.TextChoices):
    IN_PROGRESS = "in_progress", "In progress"
    COMPLETE = "complete", "Complete"


class WeighingSessionManager(models.Manager):
    def open_for_batch(self, batch_id: str):
        """The batch's in-progress session, or ``None``."""
        return self.filter(batch_id=batch_id, state=SessionState.IN_PROGRESS).first()


class WeighingSession(models.Model):
    selection = models.ForeignKey(BatchSelection, on_delete=models.PROTECT)
    batch_id = models.CharField(max_length=32, db_index=True)
    operator = models.ForeignKey(Operator, on_delete=models.PROTECT)
    state = models.CharField(
        max_length=16, choices=SessionState.choices, default=SessionState.IN_PROGRESS
    )
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    objects = WeighingSessionManager()

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("batch_id",),
                condition=models.Q(state="in_progress"),
                name="one_open_session_per_batch",
            ),
        )

    def __str__(self):
        return f"Session {self.pk} {self.batch_id} ({self.state})"

    def delete(self, *args, **kwargs):
        raise SessionNotDeletable(f"WeighingSession {self.pk} cannot be deleted")
