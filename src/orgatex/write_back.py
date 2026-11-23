"""Consumption write-back to OrgaTEX: key, body and status (FR-17, bolt 014).

The browser posts the body to (Dummy) OrgaTEX through its OrgaTEX client and
then reports back. The server never trusts that report: it reads OrgaTEX
through the adapter and shows CONFIRMED only when OrgaTEX holds a consumption
with this write-back's idempotency key (NFR-7). That read also settles an
ambiguous failure, such as a timeout after OrgaTEX stored the post.

Like the adapter read, OrgaTEX I/O happens before the short transaction that
writes the status (the pattern of ADR-011).
"""

import logging
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction

from orgatex import adapter
from orgatex.models import WriteBack, WriteBackStatus

logger = logging.getLogger(__name__)

UNAVAILABLE = "OrgaTEX unavailable"
NOT_STORED = "OrgaTEX did not store the consumption"
MAX_REASON = 200


@dataclass(frozen=True)
class Line:
    """One component's actual consumption, at display resolution."""

    code: str
    actual_qty: Decimal
    unit: str


def idempotency_key(batch_id: str, session_id: int) -> str:
    """Derived from the batch; the session part makes each weighing run unique."""
    return f"WMS-{batch_id}-S{session_id}"


def consumption_body(key: str, lines: list[Line]) -> dict:
    """The training contract's consumption body; quantities as decimal strings."""
    return {
        "idempotencyKey": key,
        "components": [
            {"code": line.code, "actualQty": f"{line.actual_qty:f}", "unit": line.unit}
            for line in lines
        ],
    }


def status_of(session_id: int) -> WriteBack | None:
    return WriteBack.objects.filter(session_id=session_id).first()


def open_write_back(batch_id: str, session_id: int, operator_id: str) -> WriteBack:
    """Batch completion (ADR-013): the write-back is due, nothing posted yet.

    Runs inside the caller's transaction and does no OrgaTEX I/O. Creates the
    row as ``pending`` with 0 attempts; an existing row is returned unchanged.
    The browser's first post (``start``) then counts as attempt 1.
    """
    write_back, _ = WriteBack.objects.get_or_create(
        session_id=session_id,
        defaults={
            "batch_id": batch_id,
            "idempotency_key": idempotency_key(batch_id, session_id),
            "operator_id": operator_id,
        },
    )
    return write_back


def start(batch_id: str, session_id: int, operator_id: str) -> WriteBack:
    """Start or retry: same row, same key; a CONFIRMED write-back stays confirmed."""
    key = idempotency_key(batch_id, session_id)
    with transaction.atomic():
        WriteBack.objects.get_or_create(
            session_id=session_id,
            defaults={
                "batch_id": batch_id,
                "idempotency_key": key,
                "operator_id": operator_id,
            },
        )
        write_back = WriteBack.objects.select_for_update().get(session_id=session_id)
        write_back.attempts += 1
        write_back.operator_id = operator_id
        if not write_back.is_confirmed:
            write_back.status = WriteBackStatus.PENDING
            write_back.last_error = ""
        write_back.save()
    logger.info(
        "WriteBackStarted batch=%s key=%s attempt=%s operator=%s status=%s",
        batch_id,
        key,
        write_back.attempts,
        operator_id,
        write_back.status,
    )
    return write_back


def verify(write_back: WriteBack, posted: bool, reason: str) -> WriteBack:
    """Set the status from what OrgaTEX holds, not from the browser's report."""
    if write_back.is_confirmed:
        return write_back
    key = write_back.idempotency_key
    try:
        stored = adapter.fetch_consumptions(write_back.batch_id)
    except adapter.OrgatexError as exc:
        logger.warning(
            "WriteBackCheckFailed batch=%s key=%s error=%s",
            write_back.batch_id,
            key,
            exc,
        )
        found, error = None, UNAVAILABLE
    else:
        found = next((c for c in stored if c.idempotency_key == key), None)
        error = _clean(reason) or (NOT_STORED if posted else UNAVAILABLE)

    with transaction.atomic():
        write_back = WriteBack.objects.select_for_update().get(pk=write_back.pk)
        if write_back.is_confirmed:
            return write_back
        if found is not None:
            write_back.status = WriteBackStatus.CONFIRMED
            write_back.confirmed_at = found.accepted_at
            write_back.last_error = ""
        else:
            write_back.status = WriteBackStatus.NOT_WRITTEN
            write_back.last_error = error
        write_back.save()

    if found is not None:
        logger.info(
            "WriteBackConfirmed batch=%s key=%s acceptedAt=%s browserPosted=%s",
            write_back.batch_id,
            key,
            found.accepted_at.isoformat(),
            posted,
        )
    else:
        logger.warning(
            "WriteBackNotWritten batch=%s key=%s attempt=%s reason=%s",
            write_back.batch_id,
            key,
            write_back.attempts,
            error,
        )
    return write_back


def _clean(reason) -> str:
    if not isinstance(reason, str):
        return ""
    return " ".join(reason.split())[:MAX_REASON]
