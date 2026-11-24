"""The weighing ticket's text, in the prototype's layout (story 001, FR-18).

Training layout only: the prototype says "Label content is invented" (A-04,
Q18 unresolved). Values are the stored ones: batch header from the recipe
snapshot, targets and actuals from the weighing records (story 001 AC 3);
they are only formatted at display resolution here, never recomputed.
"""

from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from weighing.tolerance import format_amount

TITLE = "FCI DYEING — WEIGHING TICKET"
REPRINT = "*** REPRINT ***"
ALL_WITHIN = "ALL WITHIN TOLERANCE"
NOT_ALL_WITHIN = "NOT ALL WITHIN TOLERANCE"
LABEL_WIDTH = 8


@dataclass(frozen=True)
class TicketLine:
    name: str
    target: str
    actual: str
    unit: str


@dataclass(frozen=True)
class TicketData:
    batch_id: str
    order_id: str
    machine: str
    shade: str
    completed_at: datetime
    operator_name: str
    lines: tuple[TicketLine, ...]
    all_within: bool


def line_of(record) -> TicketLine:
    """One component line from a stored ``WeighingRecord``."""
    return TicketLine(
        name=record.component_name,
        target=format_amount(record.target, record.unit),
        actual=format_amount(record.actual_weight, record.unit),
        unit=record.unit,
    )


def barcode_text(batch_id: str) -> str:
    """Code 39 text form (start/stop ``*``); the symbology is unresolved (Q18)."""
    return f"*{batch_id}*"


def build_ticket(data: TicketData, reprint: bool) -> str:
    when = timezone.localtime(data.completed_at).strftime("%Y-%m-%d %H:%M")
    header = [
        _field("BATCH", data.batch_id),
        _field("ORDER", data.order_id),
        _field("MACHINE", data.machine),
        _field("SHADE", data.shade),
        _field("DATE", when),
        _field("OPER.", data.operator_name),
    ]
    table = _table(data.lines)
    summary = ALL_WITHIN if data.all_within else NOT_ALL_WITHIN
    centred = [TITLE, summary, barcode_text(data.batch_id), data.batch_id]
    if reprint:
        centred.append(REPRINT)
    width = max(len(line) for line in header + table + centred)
    rule = "-" * width
    lines = [REPRINT.center(width).rstrip()] if reprint else []
    lines += [TITLE.center(width).rstrip(), rule, *header, rule, *table, rule]
    lines += [
        summary.center(width).rstrip(),
        barcode_text(data.batch_id).center(width).rstrip(),
        data.batch_id.center(width).rstrip(),
    ]
    return "\n".join(lines) + "\n"


def _field(label: str, value: str) -> str:
    return f"{label:<{LABEL_WIDTH}}{value}"


def _table(lines) -> list[str]:
    name_w = max([len("COMPONENT")] + [len(ln.name) for ln in lines])
    target_w = max([len("TGT")] + [len(ln.target) for ln in lines])
    actual_w = max([len("ACT")] + [len(ln.actual) for ln in lines])
    head = f"{'COMPONENT':<{name_w}}  {'TGT':>{target_w}}  {'ACT':>{actual_w}}"
    rows = [
        f"{ln.name:<{name_w}}  {ln.target:>{target_w}}  {ln.actual:>{actual_w}} {ln.unit}"
        for ln in lines
    ]
    return [head.rstrip(), *rows]
