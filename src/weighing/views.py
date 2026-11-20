"""WeighingMS station endpoints for identity and sessions (ADR-002, ADR-005).

Thin views: validate the request, call the service, return JSON. The current
operator lives only in the server-side session; an operator in a request
body is never used for a weighing action.
"""

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_http_methods

from weighing import services
from weighing.models import WeighingSession
from weighing.services import OperatorRef, RefusalReason, WeighingRefused
from weighingms.api import InvalidJson, json_error, read_json_object

SESSION_KEY = "weighing.operator_id"
MAX_OPERATOR_ID = 16

REFUSAL_STATUS = {
    RefusalReason.OPERATOR_REQUIRED: 403,
    RefusalReason.OPERATOR_NOT_FOUND: 404,
    RefusalReason.SELECTION_NOT_FOUND: 404,
}


class InvalidRequest(ValueError):
    pass


def _refusal(refused: WeighingRefused) -> JsonResponse:
    return json_error(
        REFUSAL_STATUS[refused.reason], refused.reason.code, refused.message
    )


def _session_operator_id(request) -> str | None:
    return request.session.get(SESSION_KEY)


@require_GET
def operators(request):
    return JsonResponse(
        {"operators": [_operator_json(o) for o in services.list_operators()]}
    )


@require_http_methods(["GET", "PUT", "DELETE"])
def current_operator(request):
    if request.method == "PUT":
        return _choose_operator(request)
    if request.method == "DELETE":
        services.log_operator_cleared(request.session.pop(SESSION_KEY, None))
        return HttpResponse(status=204)
    operator = services.current_operator(_session_operator_id(request))
    return JsonResponse({"operator": operator and _operator_json(operator)})


def _choose_operator(request):
    try:
        operator_id = _parse_operator_id(request)
    except (InvalidJson, InvalidRequest) as exc:
        return json_error(400, "INVALID_REQUEST", str(exc))
    try:
        operator = services.find_operator(operator_id)
    except WeighingRefused as refused:
        return _refusal(refused)
    request.session[SESSION_KEY] = operator.operator_id
    services.log_operator_identified(operator)
    return JsonResponse({"operator": _operator_json(operator)})


def _parse_operator_id(request) -> str:
    operator_id = read_json_object(request).get("operatorId")
    if not isinstance(operator_id, str) or not operator_id.strip():
        raise InvalidRequest("operatorId is required")
    operator_id = operator_id.strip()
    if len(operator_id) > MAX_OPERATOR_ID:
        raise InvalidRequest(f"operatorId is longer than {MAX_OPERATOR_ID} characters")
    return operator_id


@require_http_methods(["POST"])
def sessions(request):
    try:
        selection_id = _parse_selection_id(request)
    except (InvalidJson, InvalidRequest) as exc:
        return json_error(400, "INVALID_REQUEST", str(exc))
    try:
        session, created = services.start_session(
            selection_id, _session_operator_id(request)
        )
    except WeighingRefused as refused:
        return _refusal(refused)
    return JsonResponse(_session_json(session), status=201 if created else 200)


def _parse_selection_id(request) -> int:
    selection_id = read_json_object(request).get("selectionId")
    if (
        not isinstance(selection_id, int)
        or isinstance(selection_id, bool)
        or selection_id < 1
    ):
        raise InvalidRequest("selectionId must be a positive integer")
    return selection_id


@require_GET
def session_detail(request, session_id):
    session = (
        WeighingSession.objects.select_related("operator").filter(pk=session_id).first()
    )
    if session is None:
        return json_error(
            404, "SESSION_NOT_FOUND", f"Weighing session not found: {session_id}"
        )
    return JsonResponse(_session_json(session))


def _operator_json(operator: OperatorRef) -> dict:
    return {
        "operatorId": operator.operator_id,
        "name": operator.name,
        "shift": operator.shift,
        "display": operator.display,
    }


def _session_json(session: WeighingSession) -> dict:
    return {
        "sessionId": session.pk,
        "selectionId": session.selection_id,
        "batchId": session.batch_id,
        "state": session.state,
        "operator": _operator_json(OperatorRef.of(session.operator)),
        "startedAt": session.started_at.isoformat(),
        "completedAt": session.completed_at and session.completed_at.isoformat(),
    }
