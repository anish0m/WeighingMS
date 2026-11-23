"""Component progression: activate, tare, quit, progress and resume (bolt 010).

Component state is derived, never stored (ADR-010): *done* = a weighing
record exists, *active* = the session's open attempt, *pending* = neither.
Scale calls go through ``devices.scale`` before any transaction; the
transaction then re-checks the state under a lock before it writes (ADR-011).
Quit (F4) re-reads the scale first: over tolerance ends the attempt as an
overshoot discard with its surplus (bolt 012, ADR-012).
"""

import logging
from dataclasses import dataclass, replace
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from batches.models import SnapshotComponent
from devices import scale
from weighing.identity import load_component, load_session
from weighing.models import (
    AttemptEnd,
    ComponentAttempt,
    SessionState,
    WeighingRecord,
    WeighingSession,
)
from weighing.overshoot import Surplus, surplus_of
from weighing.rules import component_rules
from weighing.scale_selection import select_scale
from weighing.services import RefusalReason, WeighingRefused, require_operator
from weighing.tolerance import evaluate, format_weight

logger = logging.getLogger(__name__)

PENDING = "pending"
ACTIVE = "active"
DONE = "done"


@dataclass(frozen=True)
class ComponentProgress:
    sequence: int
    unit: str
    state: str
    record: WeighingRecord | None


@dataclass(frozen=True)
class Discard:
    """What an overshoot discard stores: the server's evaluated net and surplus."""

    net: Decimal
    surplus: Surplus


@dataclass(frozen=True)
class EndedAttempt:
    """How Quit ended the old attempt (quit JSON ``ended``, bolt 012)."""

    attempt_id: int
    reason: AttemptEnd
    discard: Discard | None

    @property
    def message(self) -> str:
        if self.discard is None:
            return "Attempt abandoned. Empty the container and press Re-tare (F2)."
        net = format_weight(self.discard.net, self.discard.surplus.unit)
        return (
            f"Overshoot discarded ({net}). Empty the container and press Re-tare (F2)."
        )


@dataclass(frozen=True)
class SessionProgress:
    session: WeighingSession
    components: list[ComponentProgress]
    active_attempt: ComponentAttempt | None
    next_pending: int | None
    ended: EndedAttempt | None = None

    @property
    def weighed(self) -> int:
        return sum(1 for c in self.components if c.state == DONE)

    @property
    def total(self) -> int:
        return len(self.components)

    @property
    def text(self) -> str:
        """FR-15b: e.g. "2 of 5 components weighed"."""
        return f"{self.weighed} of {self.total} components weighed"


def refuse(reason: RefusalReason, session_id, sequence, detail=None):
    logger.info(
        "WeighingActionRefused session=%s sequence=%s reason=%s",
        session_id,
        sequence,
        reason.code,
    )
    return WeighingRefused(reason, detail)


def open_attempt(session: WeighingSession) -> ComponentAttempt | None:
    return session.attempts.filter(ended_at__isnull=True).first()


def progress(session_id: int) -> SessionProgress:
    """The derived state of every component, in recipe sequence (read-only)."""
    return _progress(load_session(session_id))


def _progress(session: WeighingSession) -> SessionProgress:
    records = {r.component_sequence: r for r in session.records.all()}
    attempt = open_attempt(session)
    components = []
    for component in session.selection.components.all():
        sequence = component.sequence
        if sequence in records:
            state = DONE
        elif attempt is not None and attempt.component_sequence == sequence:
            state = ACTIVE
        else:
            state = PENDING
        components.append(
            ComponentProgress(sequence, component.unit, state, records.get(sequence))
        )
    pending = [c.sequence for c in components if c.state == PENDING]
    if attempt is not None:
        next_pending = attempt.component_sequence
    else:
        next_pending = pending[0] if pending else None
    return SessionProgress(session, components, attempt, next_pending)


def _open_session(session_id: int) -> WeighingSession:
    session = load_session(session_id)
    if session.state != SessionState.IN_PROGRESS:
        raise refuse(RefusalReason.SESSION_NOT_OPEN, session_id, None)
    return session


def locked(session: WeighingSession) -> WeighingSession:
    """Lock the session row for the write phase and re-check it (ADR-011)."""
    locked = WeighingSession.objects.select_for_update().get(pk=session.pk)
    if locked.state != SessionState.IN_PROGRESS:
        raise refuse(RefusalReason.SESSION_NOT_OPEN, session.pk, None)
    return locked


def _start_attempt(
    session: WeighingSession, component: SnapshotComponent, operator_id, tared=False
) -> ComponentAttempt:
    assignment = select_scale(component.target_qty, component.unit)
    now = timezone.now()
    attempt = ComponentAttempt.objects.create(
        session=session,
        component_sequence=component.sequence,
        scale_id=assignment.scale.scale_id,
        started_at=now,
        tared_at=now if tared else None,
    )
    logger.info(
        "ComponentActivated session=%s sequence=%s scale=%s attempt=%s operator=%s",
        session.pk,
        component.sequence,
        attempt.scale_id,
        attempt.pk,
        operator_id,
    )
    return attempt


def end_attempt(
    attempt: ComponentAttempt,
    reason: AttemptEnd,
    operator_id,
    discard: Discard | None = None,
) -> None:
    attempt.ended_at = timezone.now()
    attempt.end_reason = reason
    fields = ["ended_at", "end_reason"]
    if discard is not None:
        attempt.end_net = discard.net
        attempt.end_surplus = discard.surplus.amount
        attempt.end_unit = discard.surplus.unit
        fields += ["end_net", "end_surplus", "end_unit"]
    attempt.save(update_fields=fields)
    if reason == AttemptEnd.OVERSHOOT_DISCARDED:
        logger.info(
            "OvershootDiscarded session=%s sequence=%s attempt=%s net=%s"
            " surplus=%s percent=%s unit=%s operator=%s",
            attempt.session_id,
            attempt.component_sequence,
            attempt.pk,
            discard.net,
            discard.surplus.amount,
            discard.surplus.percent,
            discard.surplus.unit,
            operator_id,
        )
    elif reason != AttemptEnd.CONFIRMED:
        event = {
            AttemptEnd.QUIT: "AttemptQuit",
            AttemptEnd.RETARED: "AttemptRetared",
            AttemptEnd.SWITCHED: "AttemptSwitched",
        }[reason]
        logger.info(
            "%s session=%s sequence=%s attempt=%s operator=%s",
            event,
            attempt.session_id,
            attempt.component_sequence,
            attempt.pk,
            operator_id,
        )


def start_next(session: WeighingSession, operator_id) -> ComponentAttempt | None:
    """Inside a transaction: start the first pending component, if any."""
    done = set(session.records.values_list("component_sequence", flat=True))
    for component in session.selection.components.all():
        if component.sequence not in done:
            return _start_attempt(session, component, operator_id)
    return None


def auto_tare(attempt: ComponentAttempt | None) -> None:
    """After the commit: tare a newly started attempt. Never raises (ADR-011)."""
    if attempt is None:
        return
    try:
        scale.tare(attempt.scale_id)
    except scale.ScaleError as exc:
        logger.warning(
            "TareFailed session=%s sequence=%s scale=%s reason=%s",
            attempt.session_id,
            attempt.component_sequence,
            attempt.scale_id,
            exc.reason,
        )
        return
    _mark_tared(attempt.pk)


def _mark_tared(attempt_id: int) -> None:
    with transaction.atomic():
        attempt = ComponentAttempt.objects.select_for_update().get(pk=attempt_id)
        if not attempt.is_open or attempt.is_tared:
            return
        attempt.tared_at = timezone.now()
        attempt.save(update_fields=("tared_at",))
    logger.info(
        "ContainerTared session=%s sequence=%s scale=%s attempt=%s",
        attempt.session_id,
        attempt.component_sequence,
        attempt.scale_id,
        attempt.pk,
    )


def activate(
    session_id: int, sequence: int, operator_id: str | None
) -> SessionProgress:
    """First activation and touch (FR-15): pending → active; done → refused."""
    operator = require_operator(operator_id, "activate")
    session = _open_session(session_id)
    component = load_component(session, sequence)
    with transaction.atomic():
        session = locked(session)
        if session.records.filter(component_sequence=sequence).exists():
            raise refuse(RefusalReason.COMPONENT_DONE, session_id, sequence)
        current = open_attempt(session)
        if current is not None and current.component_sequence == sequence:
            return _progress(session)
        if current is not None:
            end_attempt(current, AttemptEnd.SWITCHED, operator.operator_id)
        attempt = _start_attempt(session, component, operator.operator_id)
    auto_tare(attempt)
    return _progress(session)


def _active_attempt(session: WeighingSession, sequence: int) -> ComponentAttempt:
    if session.records.filter(component_sequence=sequence).exists():
        raise refuse(RefusalReason.COMPONENT_DONE, session.pk, sequence)
    attempt = open_attempt(session)
    if attempt is None:
        raise refuse(RefusalReason.NO_ACTIVE_COMPONENT, session.pk, sequence)
    if attempt.component_sequence != sequence:
        raise refuse(RefusalReason.COMPONENT_NOT_ACTIVE, session.pk, sequence)
    return attempt


def active_attempt(session: WeighingSession, sequence: int) -> ComponentAttempt:
    """The open attempt of ``sequence``, or the refusal that explains why not."""
    load_component(session, sequence)
    return _active_attempt(session, sequence)


def same_attempt_still_open(session, sequence, attempt_id) -> ComponentAttempt:
    """Write-phase re-check under the session lock (ADR-011)."""
    attempt = _active_attempt(session, sequence)
    if attempt.pk != attempt_id:
        raise refuse(RefusalReason.COMPONENT_NOT_ACTIVE, session.pk, sequence)
    return attempt


def tare(session_id: int, sequence: int, operator_id: str | None) -> SessionProgress:
    """F2: zero the attempt's scale. A tared attempt restarts (story 003 AC 2)."""
    operator = require_operator(operator_id, "tare")
    session = _open_session(session_id)
    attempt = active_attempt(session, sequence)
    try:
        scale.tare(attempt.scale_id)
    except scale.ScaleDisconnected as exc:
        _log_tare_failed(attempt, exc)
        raise refuse(RefusalReason.SCALE_DISCONNECTED, session_id, sequence) from exc
    except scale.ScaleError as exc:
        _log_tare_failed(attempt, exc)
        raise refuse(RefusalReason.SCALE_UNAVAILABLE, session_id, sequence) from exc
    with transaction.atomic():
        session = locked(session)
        attempt = same_attempt_still_open(session, sequence, attempt.pk)
        if attempt.is_tared:
            end_attempt(attempt, AttemptEnd.RETARED, operator.operator_id)
            component = load_component(session, sequence)
            attempt = _start_attempt(
                session, component, operator.operator_id, tared=True
            )
        else:
            attempt.tared_at = timezone.now()
            attempt.save(update_fields=("tared_at",))
    logger.info(
        "ContainerTared session=%s sequence=%s scale=%s attempt=%s operator=%s",
        session.pk,
        sequence,
        attempt.scale_id,
        attempt.pk,
        operator.operator_id,
    )
    return _progress(session)


def _log_tare_failed(attempt: ComponentAttempt, exc: scale.ScaleError) -> None:
    logger.warning(
        "TareFailed session=%s sequence=%s scale=%s reason=%s",
        attempt.session_id,
        attempt.component_sequence,
        attempt.scale_id,
        exc.reason,
    )


def _overshoot_at_quit(attempt: ComponentAttempt, component) -> Discard | None:
    """The server's own re-read at Quit (ADR-012): a Discard when it is over.

    A scale that cannot be read never blocks Quit (model Decision 3): there
    is no measured overshoot to store, so the quit is a plain quit.
    """
    try:
        reading = scale.read_weight(attempt.scale_id)
    except scale.ScaleError:
        return None
    if reading.status != "ready":
        return None
    band = component_rules(component).band
    evaluation = evaluate(band, reading.net_weight, reading.unit)
    surplus = surplus_of(evaluation, band.target)
    return None if surplus is None else Discard(evaluation.net, surplus)


def quit_attempt(
    session_id: int, sequence: int, operator_id: str | None
) -> SessionProgress:
    """F4: abandon the attempt, record nothing, restart untared (Decision 2).

    Over tolerance this is the STEP 24 recovery action "discard and re-weigh":
    the attempt ends as ``overshoot_discarded`` with its net and surplus.
    """
    operator = require_operator(operator_id, "quit")
    session = _open_session(session_id)
    attempt = active_attempt(session, sequence)
    component = load_component(session, sequence)
    discard = _overshoot_at_quit(attempt, component)
    reason = AttemptEnd.QUIT if discard is None else AttemptEnd.OVERSHOOT_DISCARDED
    with transaction.atomic():
        session = locked(session)
        attempt = same_attempt_still_open(session, sequence, attempt.pk)
        end_attempt(attempt, reason, operator.operator_id, discard)
        _start_attempt(session, component, operator.operator_id)
    ended = EndedAttempt(attempt.pk, reason, discard)
    return replace(_progress(session), ended=ended)


def current_session() -> SessionProgress | None:
    """Resume (NFR-6): the most recently active in-progress session, or None."""
    sessions = WeighingSession.objects.filter(state=SessionState.IN_PROGRESS)
    latest = None
    latest_at = None
    for session in sessions:
        attempt = session.attempts.order_by("-started_at", "-pk").first()
        at = attempt.started_at if attempt is not None else session.started_at
        if latest_at is None or at >= latest_at:
            latest, latest_at = session, at
    return None if latest is None else _progress(latest)
