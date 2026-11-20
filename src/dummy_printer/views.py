"""Dummy Printer JSON endpoints (training contract, not a real printer)."""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from dummy_printer import services
from weighingms.api import InvalidJson, json_error, read_json_object


def _ticket_json(ticket) -> dict:
    return {
        "ticketId": ticket.pk,
        "content": ticket.content,
        "batchId": ticket.batch_id or None,
        "printedAt": ticket.printed_at.isoformat(),
    }


@require_GET
def printer_status(request):
    return JsonResponse({"status": services.status()})


@csrf_exempt
@require_POST
def ticket_create(request):
    try:
        payload = read_json_object(request)
        ticket = services.print_ticket(payload.get("content"), payload.get("batchId"))
    except InvalidJson as exc:
        return json_error(400, "VALIDATION_ERROR", str(exc))
    except services.PrinterError:
        return json_error(503, "PRINTER_ERROR", "Printer error: ticket not printed")
    except services.InvalidTicket as exc:
        return json_error(400, "VALIDATION_ERROR", str(exc))
    return JsonResponse(_ticket_json(ticket), status=201)


@require_GET
def ticket_detail(request, ticket_id):
    try:
        ticket = services.get_ticket(ticket_id)
    except services.TicketNotFound:
        return json_error(404, "TICKET_NOT_FOUND", f"Ticket not found: {ticket_id}")
    return JsonResponse(_ticket_json(ticket))
