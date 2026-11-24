"""Ticket endpoints under /station/api/ (ADR-002): preview, print, print result.

Thin views: validate, call ``tickets.printing``, return JSON. The current
operator comes only from the server-side session (ADR-005).
"""

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from tickets import printing
from tickets.models import PrintJob
from weighing.services import WeighingRefused
from weighing.views import REFUSAL_STATUS, SESSION_KEY
from weighingms.api import InvalidJson, json_error, read_json_object


class InvalidRequest(ValueError):
    pass


def _refusal(refused: WeighingRefused) -> JsonResponse:
    return json_error(
        REFUSAL_STATUS[refused.reason], refused.reason.code, refused.message
    )


def _operator_id(request):
    return request.session.get(SESSION_KEY)


@require_GET
def ticket_preview(request, session_id):
    try:
        result = printing.preview(session_id)
    except WeighingRefused as refused:
        return _refusal(refused)
    return JsonResponse(
        {
            "batchId": result.batch_id,
            "content": result.content,
            "reprint": result.reprint,
            "printed": result.printed,
            "jobs": [_job_json(job) for job in result.jobs],
        }
    )


@require_POST
def ticket_print(request, session_id):
    try:
        job = printing.start_print(session_id, _operator_id(request))
    except WeighingRefused as refused:
        return _refusal(refused)
    return JsonResponse(
        {"job": _job_json(job), "batchId": job.batch_id, "content": job.content},
        status=201,
    )


@require_POST
def ticket_print_result(request, session_id, job_id):
    try:
        printed, ticket_id, reason = _parse_report(request)
    except (InvalidJson, InvalidRequest) as exc:
        return json_error(400, "VALIDATION_ERROR", str(exc))
    try:
        job = printing.report_print(
            session_id, job_id, _operator_id(request), printed, ticket_id, reason
        )
    except WeighingRefused as refused:
        return _refusal(refused)
    return JsonResponse({"job": _job_json(job)})


def _parse_report(request):
    payload = read_json_object(request)
    printed = payload.get("printed")
    if not isinstance(printed, bool):
        raise InvalidRequest("printed must be true or false")
    ticket_id = payload.get("ticketId")
    if ticket_id is not None and (
        not isinstance(ticket_id, int) or isinstance(ticket_id, bool) or ticket_id < 1
    ):
        raise InvalidRequest("ticketId must be a positive integer")
    reason = payload.get("reason") or ""
    if not isinstance(reason, str):
        raise InvalidRequest("reason must be a string")
    return printed, ticket_id, reason


def _job_json(job: PrintJob) -> dict:
    return {
        "jobId": job.pk,
        "status": job.status,
        "reprint": job.is_reprint,
        "ticketId": job.printer_ticket_id,
        "printedAt": job.printed_at and job.printed_at.isoformat(),
        "reason": job.reason or None,
        "operatorId": job.operator_id,
        "createdAt": job.created_at.isoformat(),
    }
