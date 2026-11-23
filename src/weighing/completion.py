"""Batch completion and its summary (story 009, FR-16, ADR-013).

A session completes inside the transaction that saves its last record: the
state becomes ``complete``, ``completed_at`` is that record's time, and the
OrgaTEX write-back becomes due (unit 002, ``open_write_back``). The summary is
derived from the records on every read and never stored.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from orgatex import write_back
from weighing.identity import load_session
from weighing.models import (
    SessionState,
    WeighingRecord,
    WeighingResult,
    WeighingSession,
)
from weighing.progression import refuse
from weighing.services import OperatorRef, RefusalReason
from weighing.tolerance import KILOGRAM, to_unit

logger = logging.getLogger(__name__)

KG_RESOLUTION = Decimal("0.001")


@dataclass(frozen=True)
class BatchSummary:
    session: WeighingSession
    weighed: int
    total: int
    all_within: bool
    total_dispensed_kg: Decimal
    elapsed_seconds: int
    operator: OperatorRef
    started_at: datetime
    completed_at: datetime

    @property
    def components_text(self) -> str:
        return f"{self.weighed} of {self.total}"

    @property
    def all_within_text(self) -> str:
        return "YES" if self.all_within else "NO"

    @property
    def total_text(self) -> str:
        return f"{self.total_dispensed_kg:f} kg"

    @property
    def elapsed_text(self) -> str:
        return elapsed_text(self.elapsed_seconds)


def total_dispensed_kg(records) -> Decimal:
    """Sum of the actual weights in kg, half up to 0.001 kg (35.322 kg)."""
    total = sum(
        (to_unit(r.actual_weight, r.unit, KILOGRAM) for r in records), Decimal(0)
    )
    return total.quantize(KG_RESOLUTION, rounding=ROUND_HALF_UP)


def elapsed_text(seconds: int) -> str:
    """The prototype's format: "6 min 41 s"."""
    minutes, rest = divmod(max(seconds, 0), 60)
    return f"{minutes} min {rest} s"


def _records(session: WeighingSession) -> list[WeighingRecord]:
    return list(session.records.order_by("component_sequence"))


def _missing(session: WeighingSession) -> int:
    done = set(session.records.values_list("component_sequence", flat=True))
    sequences = session.selection.components.values_list("sequence", flat=True)
    return sum(1 for sequence in sequences if sequence not in done)


def complete(
    session: WeighingSession, completed_at: datetime, operator_id: str
) -> WeighingSession:
    """Inside the last confirmation's transaction, with the session locked.

    ``operator_id`` is the operator who confirmed the last component; the
    triggered write-back is attributed to them (FR-19).

    Refuses below N of N (``BATCH_NOT_COMPLETE``) and on a session that is not
    in progress (``SESSION_NOT_OPEN``); a refusal rolls the caller back.
    """
    if session.state != SessionState.IN_PROGRESS:
        raise refuse(RefusalReason.SESSION_NOT_OPEN, session.pk, None)
    if _missing(session):
        raise refuse(RefusalReason.BATCH_NOT_COMPLETE, session.pk, None)
    session.state = SessionState.COMPLETE
    session.completed_at = completed_at
    session.save(update_fields=["state", "completed_at"])
    pending = write_back.open_write_back(session.batch_id, session.pk, operator_id)
    transaction.on_commit(lambda: _log_completed(session.pk, pending.idempotency_key))
    return session


def _log_completed(session_id: int, key: str) -> None:
    result = summary(session_id)
    session = result.session
    logger.info(
        "BatchCompleted session=%s batch=%s operator=%s weighed=%s total=%s"
        " totalDispensedKg=%s elapsedSeconds=%s allWithin=%s",
        session.pk,
        session.batch_id,
        result.operator.operator_id,
        result.weighed,
        result.total,
        result.total_dispensed_kg,
        result.elapsed_seconds,
        result.all_within_text,
    )
    logger.info(
        "WriteBackTriggered batch=%s session=%s key=%s status=pending",
        session.batch_id,
        session.pk,
        key,
    )


def summary(session_id: int) -> BatchSummary:
    """The completed batch's summary; refused until the session is complete."""
    session = load_session(session_id)
    if session.state != SessionState.COMPLETE:
        raise refuse(RefusalReason.BATCH_NOT_COMPLETE, session_id, None)
    records = _records(session)
    elapsed = session.completed_at - session.started_at
    return BatchSummary(
        session=session,
        weighed=len(records),
        total=session.selection.components.count(),
        all_within=all(r.result == WeighingResult.WITHIN for r in records),
        total_dispensed_kg=total_dispensed_kg(records),
        elapsed_seconds=int(elapsed.total_seconds()),
        operator=OperatorRef.of(session.operator),
        started_at=session.started_at,
        completed_at=session.completed_at,
    )
