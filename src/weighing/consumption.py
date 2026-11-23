"""Write-back of a weighed batch's actual consumption (FR-17, bolt 014).

The lines come from the stored ``WeighingRecord``s, which write-back never
changes: a failed write-back leaves every record in WeighingMS (FR-17d). The
key, body and status belong to the OrgaTEX unit (``orgatex.write_back``).
Bolt 015 adds batch completion and triggers write-back from it; until then
the precondition is that every component has a record.
"""

from orgatex import write_back
from orgatex.models import WriteBack
from weighing import progression
from weighing.identity import load_session
from weighing.services import RefusalReason, require_operator
from weighing.tolerance import at_resolution


def start(session_id: int, operator_id: str | None) -> tuple[WriteBack, dict]:
    """Start or retry the write-back; return its state and the body to post."""
    operator = require_operator(operator_id, "write_back")
    state = progression.progress(session_id)
    if state.weighed < state.total:
        raise progression.refuse(RefusalReason.BATCH_NOT_COMPLETE, session_id, None)
    lines = [
        write_back.Line(
            code=c.record.component_code,
            actual_qty=at_resolution(c.record.actual_weight, c.record.unit),
            unit=c.record.unit,
        )
        for c in state.components
    ]
    session = state.session
    record = write_back.start(session.batch_id, session.pk, operator.operator_id)
    return record, write_back.consumption_body(record.idempotency_key, lines)


def report(
    session_id: int, operator_id: str | None, posted: bool, reason: str
) -> WriteBack:
    """The browser's report; the status is decided by reading OrgaTEX."""
    require_operator(operator_id, "write_back_result")
    load_session(session_id)
    record = write_back.status_of(session_id)
    if record is None:
        raise progression.refuse(RefusalReason.WRITE_BACK_NOT_STARTED, session_id, None)
    return write_back.verify(record, posted, reason)


def status(session_id: int) -> WriteBack | None:
    """Read-only: the session's write-back, or ``None`` before the first start."""
    load_session(session_id)
    return write_back.status_of(session_id)
