"""Print, reprint and print failure of a batch's weighing ticket (stories 001, 002).

The browser sends the server's ticket text to the (Dummy) printer through
printer-client.js and reports back. The server marks a job ``printed`` only
after reading that ticket back from the printer (``devices.printer``) and
finding the same content and batch; otherwise the job is ``failed`` and
nothing counts as printed (FR-20c). A job is a REPRINT when an earlier job of
the session was printed. Printing never changes the batch or its records.
"""

import logging
from dataclasses import dataclass

from django.db import transaction

from devices import printer
from tickets.content import TicketData, build_ticket, line_of
from tickets.models import PrintJob, PrintStatus
from weighing import completion
from weighing.progression import refuse
from weighing.services import RefusalReason, require_operator

logger = logging.getLogger(__name__)

PRINTER_ERROR = "Printer error: ticket not printed"
PRINTER_UNAVAILABLE = "Printer unavailable: ticket not confirmed"
NOT_STORED = "The printer did not store this ticket"
MAX_REASON = 200


@dataclass(frozen=True)
class TicketPreview:
    batch_id: str
    content: str
    reprint: bool
    jobs: tuple[PrintJob, ...]

    @property
    def printed(self) -> bool:
        return any(job.status == PrintStatus.PRINTED for job in self.jobs)


def preview(session_id: int) -> TicketPreview:
    """The text the next print would send, and the session's print log."""
    summary = completion.summary(session_id)
    jobs = tuple(PrintJob.objects.filter(session_id=session_id))
    reprint = any(job.status == PrintStatus.PRINTED for job in jobs)
    return TicketPreview(
        summary.session.batch_id, _content(summary, reprint), reprint, jobs
    )


def start_print(session_id: int, operator_id: str | None) -> PrintJob:
    """Print ticket (F1): a pending job holding the exact text to send."""
    operator = require_operator(operator_id, "print_ticket")
    summary = completion.summary(session_id)
    with transaction.atomic():
        reprint = PrintJob.objects.filter(
            session_id=session_id, status=PrintStatus.PRINTED
        ).exists()
        job = PrintJob.objects.create(
            session_id=session_id,
            batch_id=summary.session.batch_id,
            is_reprint=reprint,
            content=_content(summary, reprint),
            operator_id=operator.operator_id,
        )
    logger.info(
        "TicketPrintStarted job=%s batch=%s reprint=%s operator=%s",
        job.pk,
        job.batch_id,
        reprint,
        operator.operator_id,
    )
    return job


def report_print(
    session_id: int,
    job_id: int,
    operator_id: str | None,
    printed: bool,
    ticket_id: int | None,
    reason: str,
) -> PrintJob:
    """The browser's report; ``printed`` is decided by reading the printer."""
    require_operator(operator_id, "print_ticket_result")
    completion.summary(session_id)
    job = PrintJob.objects.filter(pk=job_id, session_id=session_id).first()
    if job is None:
        raise refuse(RefusalReason.PRINT_JOB_NOT_FOUND, session_id, None)
    if job.status != PrintStatus.PENDING:
        return job

    stored, error = None, _clean(reason) or PRINTER_ERROR
    if printed and ticket_id is not None:
        stored, error = _read_back(job, ticket_id)

    with transaction.atomic():
        job = PrintJob.objects.select_for_update().get(pk=job.pk)
        if job.status != PrintStatus.PENDING:
            return job
        if (
            stored is not None
            and not PrintJob.objects.filter(printer_ticket_id=stored.ticket_id).exists()
        ):
            job.status = PrintStatus.PRINTED
            job.printer_ticket_id = stored.ticket_id
            job.printed_at = stored.printed_at
            job.reason = ""
        else:
            job.status = PrintStatus.FAILED
            job.reason = error if stored is None else NOT_STORED
        job.save()

    if job.status == PrintStatus.PRINTED:
        logger.info(
            "TicketPrinted job=%s batch=%s ticket=%s reprint=%s",
            job.pk,
            job.batch_id,
            job.printer_ticket_id,
            job.is_reprint,
        )
    else:
        logger.warning(
            "TicketNotPrinted job=%s batch=%s reason=%s",
            job.pk,
            job.batch_id,
            job.reason,
        )
    return job


def _read_back(job: PrintJob, ticket_id: int):
    """The stored ticket if it is this job's ticket, else ``(None, reason)``."""
    try:
        ticket = printer.fetch_ticket(ticket_id)
    except printer.TicketNotFound:
        return None, NOT_STORED
    except printer.PrinterUnavailable:
        return None, PRINTER_UNAVAILABLE
    if ticket.content != job.content or ticket.batch_id != job.batch_id:
        return None, NOT_STORED
    return ticket, ""


def _content(summary: completion.BatchSummary, reprint: bool) -> str:
    session = summary.session
    selection = session.selection
    records = session.records.order_by("component_sequence")
    data = TicketData(
        batch_id=session.batch_id,
        order_id=selection.order_id,
        machine=selection.machine,
        shade=selection.shade,
        completed_at=summary.completed_at,
        operator_name=summary.operator.name,
        lines=tuple(line_of(record) for record in records),
        all_within=summary.all_within,
    )
    return build_ticket(data, reprint)


def _clean(reason) -> str:
    if not isinstance(reason, str):
        return ""
    return " ".join(reason.split())[:MAX_REASON]
