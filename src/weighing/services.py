"""Who is weighing and what: operator identity, supervisor check, sessions.

The current operator is held in the server-side session (ADR-005). Views pass
its ID in; services never see the request. Every weighing action calls
``require_operator`` first, so no weighing happens without an identified
operator (FR-19a). Refusals raise ``WeighingRefused`` and store nothing.
"""

import logging
from dataclasses import dataclass
from enum import Enum

from django.db import transaction

from batches.models import BatchSelection
from weighing.models import Operator, Supervisor, WeighingSession

logger = logging.getLogger(__name__)


class RefusalReason(Enum):
    OPERATOR_REQUIRED = "Choose an operator first"
    OPERATOR_NOT_FOUND = "Operator not found"
    SELECTION_NOT_FOUND = "Batch selection not found"
    SUPERVISOR_NOT_VERIFIED = "Supervisor ID or PIN incorrect"
    SESSION_NOT_FOUND = "Weighing session not found"
    COMPONENT_NOT_FOUND = "Component not found"
    NOT_A_DYESTUFF_SCAN = "Scan a dyestuff code"
    SCAN_NOT_CURRENT = "Scan again"
    SCANNER_UNAVAILABLE = "Scanner unavailable"
    LOT_MISSING = "Lot missing for this component"
    CONTAINER_MISSING = "Container missing for this component"
    IDENTITY_NOT_VERIFIED = "Scan the dyestuff first"
    WRONG_DYESTUFF = "Wrong dyestuff"

    @property
    def code(self) -> str:
        return self.name


class WeighingRefused(Exception):
    """A weighing or identity action was refused; nothing was stored."""

    def __init__(self, reason: RefusalReason):
        self.reason = reason
        self.message = reason.value
        super().__init__(f"{reason.code}: {self.message}")


@dataclass(frozen=True)
class OperatorRef:
    operator_id: str
    name: str
    shift: str
    display: str

    @classmethod
    def of(cls, operator: Operator) -> "OperatorRef":
        return cls(
            operator.operator_id, operator.name, operator.shift, operator.display
        )


@dataclass(frozen=True)
class SupervisorRef:
    supervisor_id: str
    name: str


def list_operators() -> list[OperatorRef]:
    """The active seeded operators, ordered by name (the operator choice)."""
    return [OperatorRef.of(o) for o in Operator.objects.active()]


def find_operator(operator_id: str) -> OperatorRef:
    """Choose-operator rule: only an active seeded operator can be chosen."""
    operator = Operator.objects.active().filter(operator_id=operator_id).first()
    if operator is None:
        raise WeighingRefused(RefusalReason.OPERATOR_NOT_FOUND)
    return OperatorRef.of(operator)


def current_operator(operator_id: str | None) -> OperatorRef | None:
    """The station's operator, or ``None`` if none (or no longer active)."""
    if not operator_id:
        return None
    try:
        return find_operator(operator_id)
    except WeighingRefused:
        return None


def require_operator(operator_id: str | None, action: str) -> OperatorRef:
    """Guard for every weighing action: refuse without an identified operator."""
    operator = current_operator(operator_id)
    if operator is None:
        logger.info(
            "WeighingActionRefused action=%s reason=%s",
            action,
            RefusalReason.OPERATOR_REQUIRED.code,
        )
        raise WeighingRefused(RefusalReason.OPERATOR_REQUIRED)
    return operator


def log_operator_identified(operator: OperatorRef) -> None:
    logger.info(
        "OperatorIdentified operator=%s name=%s shift=%s",
        operator.operator_id,
        operator.name,
        operator.shift,
    )


def log_operator_cleared(operator_id: str | None) -> None:
    logger.info("OperatorCleared operator=%s", operator_id)


def start_session(
    selection_id: int, operator_id: str | None
) -> tuple[WeighingSession, bool]:
    """Start weighing a selected batch; return ``(session, created)``.

    If the batch already has an open session, that session is returned
    unchanged with ``created=False`` (one open session per batch).
    """
    operator = require_operator(operator_id, "start_session")
    with transaction.atomic():
        selection = BatchSelection.objects.filter(pk=selection_id).first()
        if selection is None:
            logger.info(
                "WeighingActionRefused action=start_session reason=%s selection=%s",
                RefusalReason.SELECTION_NOT_FOUND.code,
                selection_id,
            )
            raise WeighingRefused(RefusalReason.SELECTION_NOT_FOUND)
        existing = WeighingSession.objects.open_for_batch(selection.batch_id)
        if existing is not None:
            logger.info(
                "WeighingSessionResumed session=%s batch=%s operator=%s",
                existing.pk,
                existing.batch_id,
                existing.operator.operator_id,
            )
            return existing, False
        session = WeighingSession.objects.create(
            selection=selection,
            batch_id=selection.batch_id,
            operator=Operator.objects.get(operator_id=operator.operator_id),
        )
    logger.info(
        "WeighingSessionStarted session=%s batch=%s selection=%s operator=%s",
        session.pk,
        session.batch_id,
        selection.pk,
        operator.operator_id,
    )
    return session, True


def verify_supervisor(supervisor_id: str, pin: str) -> SupervisorRef:
    """Check a supervisor's ID + PIN (NFR-4). One message for any mismatch.

    The PIN is never logged. The override that uses this comes in bolt 012.
    """
    supervisor = Supervisor.objects.filter(
        supervisor_id=supervisor_id, active=True
    ).first()
    if supervisor is None or not pin or not supervisor.check_pin(pin):
        logger.warning("SupervisorVerificationFailed supervisor=%s", supervisor_id)
        raise WeighingRefused(RefusalReason.SUPERVISOR_NOT_VERIFIED)
    return SupervisorRef(supervisor.supervisor_id, supervisor.name)
