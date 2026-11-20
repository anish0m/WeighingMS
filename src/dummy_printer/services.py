"""Dummy Printer behaviour: store and return tickets, failure mode.

Training contract only, not a real printer interface. The ticket content is
supplied by WeighingMS; the Dummy stores it unchanged.
"""

import logging

from django.utils import timezone

from dummy_printer.models import DummyPrinterState, DummyTicket

logger = logging.getLogger(__name__)

MODES = (DummyPrinterState.MODE_OK, DummyPrinterState.MODE_ERROR)
MAX_BATCH_ID_LENGTH = 32


class PrinterError(Exception):
    """The printer is switched to "error" (training failure mode)."""


class InvalidTicket(Exception):
    """The print request is malformed."""


class TicketNotFound(Exception):
    """No stored ticket with this ID."""


def _state() -> DummyPrinterState:
    state, _ = DummyPrinterState.objects.get_or_create(pk=1)
    return state


def get_mode() -> str:
    return _state().mode


def set_mode(mode: str) -> None:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {', '.join(MODES)}")
    state = _state()
    state.mode = mode
    state.save(update_fields=["mode"])
    logger.info("Dummy printer mode set to %s", mode)


def status() -> str:
    return "error" if get_mode() == DummyPrinterState.MODE_ERROR else "ready"


def reset() -> None:
    """Clear all tickets and switch the printer back to ok."""
    DummyTicket.objects.all().delete()
    DummyPrinterState.objects.all().delete()


def print_ticket(content, batch_id=None) -> DummyTicket:
    if get_mode() == DummyPrinterState.MODE_ERROR:
        raise PrinterError()
    if not isinstance(content, str) or not content.strip():
        raise InvalidTicket("content is required")
    if batch_id is not None and (
        not isinstance(batch_id, str) or len(batch_id) > MAX_BATCH_ID_LENGTH
    ):
        raise InvalidTicket("batchId must be a string of at most 32 characters")
    ticket = DummyTicket.objects.create(
        content=content, batch_id=batch_id or "", printed_at=timezone.now()
    )
    logger.info("Dummy printer stored ticket %s for %s", ticket.pk, batch_id)
    return ticket


def get_ticket(ticket_id: int) -> DummyTicket:
    try:
        return DummyTicket.objects.get(pk=ticket_id)
    except DummyTicket.DoesNotExist as exc:
        raise TicketNotFound(ticket_id) from exc
