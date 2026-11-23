"""Confirm a weighing: server-side preconditions and the immutable record (bolt 010).

The weight is never taken from the browser: the server re-reads the attempt's
scale and evaluates it with bolt 009's rules (ADR-008); the evaluated net is
the recorded actual weight (ADR-009). The material gate is bolt 008's
``check_material_ready`` (ADR-007). Scale I/O happens before the
transaction; the transaction re-checks the state under a lock (ADR-011).
"""

import logging

from django.db import transaction

from devices import scale
from weighing import progression
from weighing.identity import check_material_ready, load_component, load_session
from weighing.models import (
    AttemptEnd,
    Operator,
    SessionState,
    WeighingRecord,
    WeighingResult,
)
from weighing.progression import SessionProgress, refuse
from weighing.rules import component_rules
from weighing.services import RefusalReason, WeighingRefused, require_operator
from weighing.tolerance import evaluate, format_amount

logger = logging.getLogger(__name__)


def confirm(
    session_id: int, sequence: int, operator_id: str | None
) -> tuple[WeighingRecord, SessionProgress]:
    """F1 · OK: record the component's weight if every precondition holds.

    Order (aggregate invariant 4): operator, session open, component active
    and not done, attempt tared, material ready, scale re-read, within
    tolerance. Any refusal raises ``WeighingRefused`` and stores nothing.
    """
    operator = require_operator(operator_id, "confirm")
    try:
        return _confirm(session_id, sequence, operator.operator_id)
    except WeighingRefused as refused:
        logger.info(
            "ConfirmationRefused session=%s sequence=%s reason=%s detail=%s",
            session_id,
            sequence,
            refused.reason.code,
            refused.detail,
        )
        raise


def _confirm(session_id, sequence, operator_id):
    session = load_session(session_id)
    if session.state != SessionState.IN_PROGRESS:
        raise refuse(RefusalReason.SESSION_NOT_OPEN, session_id, sequence)
    attempt = progression.active_attempt(session, sequence)
    if not attempt.is_tared:
        raise refuse(RefusalReason.TARE_REQUIRED, session_id, sequence)
    check_material_ready(session, sequence)
    component = load_component(session, sequence)
    rules = component_rules(component)
    reading = _read(attempt, session_id, sequence)
    evaluation = evaluate(rules.band, reading.net_weight, reading.unit)
    if not evaluation.within_tolerance:
        raise refuse(
            RefusalReason.OUT_OF_TOLERANCE,
            session_id,
            sequence,
            {
                "net": format_amount(evaluation.net, evaluation.unit),
                "unit": evaluation.unit,
                "zone": evaluation.zone.value,
            },
        )
    with transaction.atomic():
        session = progression.locked(session)
        attempt = progression.same_attempt_still_open(session, sequence, attempt.pk)
        record = WeighingRecord.objects.create(
            session=session,
            attempt=attempt,
            batch_id=session.batch_id,
            component_sequence=sequence,
            component_code=component.code,
            component_name=component.name,
            actual_weight=evaluation.net,
            unit=evaluation.unit,
            lot=component.lot,
            container=component.container,
            tare=component.tare,
            scale_id=attempt.scale_id,
            target=rules.band.target,
            tolerance_min=rules.band.low,
            tolerance_max=rules.band.high,
            result=WeighingResult.WITHIN,
            operator=Operator.objects.get(operator_id=operator_id),
        )
        progression.end_attempt(attempt, AttemptEnd.CONFIRMED, operator_id)
        next_attempt = progression.start_next(session, operator_id)
    logger.info(
        "WeighingConfirmed record=%s session=%s batch=%s sequence=%s actual=%s %s"
        " scale=%s operator=%s",
        record.pk,
        session.pk,
        session.batch_id,
        sequence,
        record.actual_weight,
        record.unit,
        record.scale_id,
        operator_id,
    )
    progression.auto_tare(next_attempt)
    return record, progression.progress(session.pk)


def _read(attempt, session_id, sequence):
    """The server's own re-read of the attempt's scale (FR-13b, FR-20a)."""
    try:
        reading = scale.read_weight(attempt.scale_id)
    except scale.ScaleDisconnected as exc:
        raise refuse(RefusalReason.SCALE_DISCONNECTED, session_id, sequence) from exc
    except scale.ScaleError as exc:
        raise refuse(RefusalReason.SCALE_UNAVAILABLE, session_id, sequence) from exc
    if reading.status != "ready":
        raise refuse(RefusalReason.SCALE_DISCONNECTED, session_id, sequence)
    return reading
