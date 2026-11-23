"""Weighing station foundation: identities and the weighing session (unit 005).

Operators and supervisors are seeded training identities, not Django users
(ADR-004). A ``WeighingSession`` is the weighing of one selected batch by one
operator. Its members are identity checks (bolt 008), component attempts and
weighing records (bolt 010); completion comes later.
"""

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone

from batches.models import BatchSelection


class SessionNotDeletable(Exception):
    """Raised when code tries to delete a weighing session (NFR-12)."""


class IdentityCheckImmutable(Exception):
    """Raised when code tries to change or delete a recorded identity check."""


class AttemptImmutable(Exception):
    """Raised when code tries to rewrite or delete a component attempt (ADR-010)."""


class WeighingRecordImmutable(Exception):
    """Raised when code tries to change or delete a weighing record (NFR-12)."""


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


class IdentityResult(models.TextChoices):
    VERIFIED = "verified", "Verified"
    WRONG_DYESTUFF = "wrong_dyestuff", "Wrong dyestuff"


class IdentityCheck(models.Model):
    """One dyestuff scan checked against a session component (ADR-006, ADR-007).

    ``expected_code`` comes from the recipe snapshot and ``scanned_code`` from
    the scanner, never from the browser. Every check is kept, wrong ones too
    (BR-10); rows are append-only.
    """

    session = models.ForeignKey(
        WeighingSession, on_delete=models.PROTECT, related_name="identity_checks"
    )
    component_sequence = models.PositiveSmallIntegerField()
    expected_code = models.CharField(max_length=32)
    scan_id = models.PositiveIntegerField()
    scanned_code = models.CharField(max_length=64)
    result = models.CharField(max_length=16, choices=IdentityResult.choices)
    operator = models.ForeignKey(Operator, on_delete=models.PROTECT)
    checked_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("session", "scan_id"), name="one_check_per_scan_per_session"
            ),
        )
        indexes = (
            models.Index(
                fields=("session", "component_sequence", "checked_at"),
                name="identity_latest_idx",
            ),
        )

    def __str__(self):
        return (
            f"Check {self.pk} session {self.session_id} #{self.component_sequence}"
            f" {self.scanned_code} ({self.result})"
        )

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise IdentityCheckImmutable(f"IdentityCheck {self.pk} is append-only")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise IdentityCheckImmutable(f"IdentityCheck {self.pk} cannot be deleted")


QUANTITY = {"max_digits": 12, "decimal_places": 4}


class AttemptEnd(models.TextChoices):
    CONFIRMED = "confirmed", "Confirmed"
    QUIT = "quit", "Quit"
    RETARED = "retared", "Re-tared"
    SWITCHED = "switched", "Switched"
    OVERSHOOT_DISCARDED = "overshoot_discarded", "Overshoot discarded"


class ComponentAttempt(models.Model):
    """One try at weighing one component, from its start to its end (ADR-010).

    Append-only: ``tared_at`` and ``ended_at`` / ``end_reason`` are each set
    once; an ended attempt is never reopened. The open attempt (``ended_at``
    null) is the session's active component.

    An attempt ended as ``overshoot_discarded`` (Quit while the server's
    re-read was over tolerance) also stores the discarded net, its surplus
    and the unit, once, together with the end (ADR-012).
    """

    session = models.ForeignKey(
        WeighingSession, on_delete=models.PROTECT, related_name="attempts"
    )
    component_sequence = models.PositiveSmallIntegerField()
    scale_id = models.CharField(max_length=16)
    started_at = models.DateTimeField(default=timezone.now)
    tared_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    end_reason = models.CharField(max_length=24, choices=AttemptEnd.choices, blank=True)
    end_net = models.DecimalField(**QUANTITY, null=True, blank=True)
    end_surplus = models.DecimalField(**QUANTITY, null=True, blank=True)
    end_unit = models.CharField(max_length=2, blank=True, default="")

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("session",),
                condition=models.Q(ended_at__isnull=True),
                name="one_open_attempt_per_session",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        end_reason=AttemptEnd.OVERSHOOT_DISCARDED,
                        end_net__isnull=False,
                        end_surplus__isnull=False,
                    )
                    & ~models.Q(end_unit="")
                )
                | (
                    ~models.Q(end_reason=AttemptEnd.OVERSHOOT_DISCARDED)
                    & models.Q(
                        end_net__isnull=True, end_surplus__isnull=True, end_unit=""
                    )
                ),
                name="discard_snapshot_only_on_overshoot_discard",
            ),
        )
        indexes = (
            models.Index(fields=("session", "started_at"), name="attempt_latest_idx"),
        )

    def __str__(self):
        return f"Attempt {self.pk} session {self.session_id} #{self.component_sequence}"

    @property
    def is_open(self) -> bool:
        return self.ended_at is None

    @property
    def is_tared(self) -> bool:
        return self.tared_at is not None

    def save(self, *args, **kwargs):
        if not self._state.adding:
            self._check_allowed_change()
        super().save(*args, **kwargs)

    def _check_allowed_change(self):
        stored = ComponentAttempt.objects.get(pk=self.pk)
        fixed = ("session_id", "component_sequence", "scale_id", "started_at")
        if any(getattr(stored, f) != getattr(self, f) for f in fixed):
            raise AttemptImmutable(f"Attempt {self.pk}: fixed fields cannot change")
        once = (
            ("tared_at",),
            ("ended_at", "end_reason", "end_net", "end_surplus", "end_unit"),
        )
        for group in once:
            if any(getattr(stored, f) for f in group) and any(
                getattr(stored, f) != getattr(self, f) for f in group
            ):
                raise AttemptImmutable(f"Attempt {self.pk}: {group[0]} is already set")

    def delete(self, *args, **kwargs):
        raise AttemptImmutable(f"Attempt {self.pk} cannot be deleted")


class WeighingResult(models.TextChoices):
    WITHIN = "within", "Within tolerance"


class WeighingRecord(models.Model):
    """The immutable result of one confirmation (FR-13c, NFR-12, ADR-010).

    ``actual_weight`` is the server's evaluated net at display resolution
    (ADR-009); lot, container, tare, target and band are copied from the
    recipe snapshot at confirmation.
    """

    session = models.ForeignKey(
        WeighingSession, on_delete=models.PROTECT, related_name="records"
    )
    attempt = models.OneToOneField(
        ComponentAttempt, on_delete=models.PROTECT, related_name="record"
    )
    batch_id = models.CharField(max_length=32)
    component_sequence = models.PositiveSmallIntegerField()
    component_code = models.CharField(max_length=32)
    component_name = models.CharField(max_length=100)
    actual_weight = models.DecimalField(**QUANTITY)
    unit = models.CharField(max_length=2)
    lot = models.CharField(max_length=32)
    container = models.CharField(max_length=32)
    tare = models.DecimalField(**QUANTITY)
    scale_id = models.CharField(max_length=16)
    target = models.DecimalField(**QUANTITY)
    tolerance_min = models.DecimalField(**QUANTITY)
    tolerance_max = models.DecimalField(**QUANTITY)
    result = models.CharField(max_length=16, choices=WeighingResult.choices)
    operator = models.ForeignKey(Operator, on_delete=models.PROTECT)
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("component_sequence",)
        constraints = (
            models.UniqueConstraint(
                fields=("session", "component_sequence"),
                name="one_record_per_component_per_session",
            ),
        )

    def __str__(self):
        return (
            f"Record {self.pk} {self.batch_id} #{self.component_sequence}"
            f" {self.actual_weight} {self.unit}"
        )

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise WeighingRecordImmutable(f"WeighingRecord {self.pk} is immutable")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise WeighingRecordImmutable(f"WeighingRecord {self.pk} cannot be deleted")
