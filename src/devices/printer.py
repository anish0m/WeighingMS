"""Printer adapter: the only WeighingMS Python module that knows the ticket path.

It reads the Dummy Printer training contract over HTTP, which is not the real
ticket printer (A-04, Q18 unresolved). The browser prints through
printer-client.js; the server only reads a stored ticket back to confirm that
a print really happened (bolt 016), never prints itself.
"""

from dataclasses import dataclass
from datetime import datetime

from django.conf import settings

from devices.http import DeviceCallFailed, Malformed, call, datetime_field, field


class PrinterUnavailable(Exception):
    """The printer could not be read; no print may be assumed."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class TicketNotFound(Exception):
    """The printer holds no ticket with this ID."""


@dataclass(frozen=True)
class PrintedTicket:
    ticket_id: int
    content: str
    batch_id: str | None
    printed_at: datetime


def fetch_ticket(ticket_id: int) -> PrintedTicket:
    url = f"{settings.PRINTER_BASE_URL.rstrip('/')}/tickets/{int(ticket_id)}"
    try:
        return call("GET", url, _parse_ticket, device="Printer")
    except DeviceCallFailed as exc:
        if exc.status == 404 and exc.code == "TICKET_NOT_FOUND":
            raise TicketNotFound(ticket_id) from exc
        raise PrinterUnavailable(exc.reason) from exc


def _parse_ticket(data):
    batch_id = data.get("batchId") if isinstance(data, dict) else None
    if batch_id is not None and not isinstance(batch_id, str):
        raise Malformed("field 'batchId' has the wrong type")
    return PrintedTicket(
        ticket_id=field(data, "ticketId", int),
        content=field(data, "content", str),
        batch_id=batch_id,
        printed_at=datetime_field(data, "printedAt"),
    )
