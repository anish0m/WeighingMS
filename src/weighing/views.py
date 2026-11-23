"""WeighingMS station endpoints for identity and sessions (ADR-002, ADR-005).

Thin views: validate the request, call the service, return JSON. The current
operator lives only in the server-side session; an operator in a request
body is never used for a weighing action.
"""

import re
from decimal import Decimal

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_http_methods

from weighing import identity, rules, services
from weighing.models import IdentityCheck, WeighingSession
from weighing.services import OperatorRef, RefusalReason, WeighingRefused
from weighing.tolerance import UNITS, WeightEvaluation, format_amount, format_weight
from weighingms.api import InvalidJson, json_error, read_json_object

SESSION_KEY = "weighing.operator_id"
QUANTUM = Decimal("0.0001")
MAX_OPERATOR_ID = 16
# A plain decimal as the scale client sends it: no exponent, NaN or Infinity.
NET_PATTERN = re.compile(r"-?\d{1,6}(\.\d{1,6})?")

REFUSAL_STATUS = {
    RefusalReason.OPERATOR_REQUIRED: 403,
    RefusalReason.OPERATOR_NOT_FOUND: 404,
    RefusalReason.SELECTION_NOT_FOUND: 404,
    RefusalReason.SESSION_NOT_FOUND: 404,
    RefusalReason.COMPONENT_NOT_FOUND: 404,
    RefusalReason.NOT_A_DYESTUFF_SCAN: 409,
    RefusalReason.SCAN_NOT_CURRENT: 409,
    RefusalReason.SCANNER_UNAVAILABLE: 503,
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


@require_GET
def session_components(request, session_id):
    """Component headers, identity status and material readiness (bolt 008)."""
    try:
        session, views = identity.session_components(session_id)
    except WeighingRefused as refused:
        return _refusal(refused)
    return JsonResponse(
        {
            "sessionId": session.pk,
            "batchId": session.batch_id,
            "components": [_component_json(v) for v in views],
        }
    )


@require_http_methods(["POST"])
def component_identity(request, session_id, sequence):
    """Verify a dyestuff scan by its scanId; the code comes from the scanner."""
    try:
        scan_id = _parse_scan_id(request)
    except (InvalidJson, InvalidRequest) as exc:
        return json_error(400, "INVALID_REQUEST", str(exc))
    try:
        check, created = identity.verify_identity(
            session_id, sequence, scan_id, _session_operator_id(request)
        )
    except WeighingRefused as refused:
        return _refusal(refused)
    return JsonResponse(_check_json(check), status=201 if created else 200)


@require_GET
def component_evaluation(request, session_id, sequence):
    """Judge a live net reading for a component (ADR-008); read-only."""
    try:
        net, unit = _parse_reading(request)
    except InvalidRequest as exc:
        return json_error(400, "INVALID_REQUEST", str(exc))
    try:
        _, evaluation = rules.evaluate_reading(session_id, sequence, net, unit)
    except WeighingRefused as refused:
        return _refusal(refused)
    return JsonResponse(_evaluation_json(session_id, sequence, evaluation))


def _parse_reading(request) -> tuple[Decimal, str]:
    net = request.GET.get("net", "")
    unit = request.GET.get("unit", "")
    if not NET_PATTERN.fullmatch(net):
        raise InvalidRequest("net must be a plain decimal, e.g. 93.4")
    if unit not in UNITS:
        raise InvalidRequest("unit must be g or kg")
    return Decimal(net), unit


def _parse_scan_id(request) -> int:
    scan_id = read_json_object(request).get("scanId")
    if not isinstance(scan_id, int) or isinstance(scan_id, bool) or scan_id < 1:
        raise InvalidRequest("scanId must be a positive integer")
    return scan_id


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


def _quantity_text(value) -> str:
    """Quantities go out as fixed 4-place decimal strings, as in bolt 005."""
    return f"{value.quantize(QUANTUM):f}"


def _component_json(view: identity.ComponentView) -> dict:
    component, check = view.component, view.latest_check
    return {
        "sequence": component.sequence,
        "code": component.code,
        "name": component.name,
        "lot": component.lot,
        "container": component.container,
        "tare": _quantity_text(component.tare),
        "unit": component.unit,
        "tareText": view.header.tare_text,
        "header": view.header.text,
        "identity": {
            "status": view.status.value,
            "scannedCode": check and check.scanned_code,
            "checkedAt": check and check.checked_at.isoformat(),
        },
        "materialReady": view.refusal is None,
        "materialRefusal": view.refusal
        and {"code": view.refusal.code, "message": view.refusal.value},
        **_rules_json(rules.component_rules(component)),
    }


def _rules_json(component_rules: rules.ComponentRules) -> dict:
    """Scale, target and band of a component (bolt 009). The band values are for
    drawing the bar; the zone always comes from the evaluation endpoint."""
    band, scale = component_rules.band, component_rules.assignment.scale
    return {
        "target": _quantity_text(band.target),
        "targetText": component_rules.target_text,
        "scale": {
            "scaleId": scale.scale_id,
            "label": scale.label,
            "unit": scale.unit,
            "mode": component_rules.assignment.mode,
        },
        "tolerance": {
            "tolerance": _quantity_text(band.tolerance),
            "low": _quantity_text(band.low),
            "high": _quantity_text(band.high),
            "nearFrom": _quantity_text(band.near_from),
            "caption": band.caption,
        },
    }


def _evaluation_json(session_id, sequence, evaluation: WeightEvaluation) -> dict:
    unit, surplus = evaluation.unit, evaluation.surplus
    return {
        "sessionId": session_id,
        "sequence": sequence,
        "net": format_amount(evaluation.net, unit),
        "unit": unit,
        "netText": format_weight(evaluation.net, unit),
        "zone": evaluation.zone.value,
        "withinTolerance": evaluation.within_tolerance,
        "stillToWeigh": format_amount(evaluation.still_to_weigh, unit),
        "stillToWeighText": format_weight(evaluation.still_to_weigh, unit),
        "surplus": surplus and format_amount(surplus, unit),
        "surplusText": surplus and format_weight(surplus, unit),
        "statusLine": evaluation.status_line,
    }


def _check_json(check: IdentityCheck) -> dict:
    return {
        "checkId": check.pk,
        "sessionId": check.session_id,
        "sequence": check.component_sequence,
        "scanId": check.scan_id,
        "expectedCode": check.expected_code,
        "scannedCode": check.scanned_code,
        "result": check.result,
        "message": identity.RESULT_MESSAGE[check.result],
        "operator": _operator_json(OperatorRef.of(check.operator)),
        "checkedAt": check.checked_at.isoformat(),
    }
