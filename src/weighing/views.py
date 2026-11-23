"""WeighingMS station endpoints for identity and sessions (ADR-002, ADR-005).

Thin views: validate the request, call the service, return JSON. The current
operator lives only in the server-side session; an operator in a request
body is never used for a weighing action.
"""

import re
from decimal import Decimal

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_http_methods

from batches.material import format_quantity
from orgatex.models import WriteBack
from weighing import (
    confirmation,
    consumption,
    identity,
    overshoot,
    progression,
    rules,
    services,
)
from weighing.models import IdentityCheck, WeighingRecord, WeighingSession
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
    RefusalReason.LOT_MISSING: 409,
    RefusalReason.CONTAINER_MISSING: 409,
    RefusalReason.IDENTITY_NOT_VERIFIED: 409,
    RefusalReason.WRONG_DYESTUFF: 409,
    RefusalReason.SESSION_NOT_OPEN: 409,
    RefusalReason.NO_ACTIVE_COMPONENT: 409,
    RefusalReason.COMPONENT_NOT_ACTIVE: 409,
    RefusalReason.COMPONENT_DONE: 409,
    RefusalReason.TARE_REQUIRED: 409,
    RefusalReason.OUT_OF_TOLERANCE: 409,
    RefusalReason.SCALE_DISCONNECTED: 503,
    RefusalReason.SCALE_UNAVAILABLE: 503,
    RefusalReason.BATCH_NOT_COMPLETE: 409,
    RefusalReason.WRITE_BACK_NOT_STARTED: 409,
}


class InvalidRequest(ValueError):
    pass


def _refusal(refused: WeighingRefused) -> JsonResponse:
    response = json_error(
        REFUSAL_STATUS[refused.reason], refused.reason.code, refused.message
    )
    if refused.detail is None:
        return response
    body = {
        "error": {
            "code": refused.reason.code,
            "message": refused.message,
            "detail": refused.detail,
        }
    }
    return JsonResponse(body, status=response.status_code)


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
        component_rules, evaluation = rules.evaluate_reading(
            session_id, sequence, net, unit
        )
    except WeighingRefused as refused:
        return _refusal(refused)
    body = _evaluation_json(session_id, sequence, evaluation)
    body["barPercent"] = str(component_rules.bar.percent(evaluation.net))
    surplus = overshoot.surplus_of(evaluation, component_rules.band.target)
    body["surplusPercent"] = surplus and f"{surplus.percent:f}"
    body["overshoot"] = overshoot.overshoot_json(surplus)
    return JsonResponse(body)


@require_GET
def current_session(request):
    """Resume (NFR-6): the most recently active open session, or null."""
    state = progression.current_session()
    return JsonResponse({"session": state and _progress_json(state)})


@require_GET
def session_progress(request, session_id):
    try:
        state = progression.progress(session_id)
    except WeighingRefused as refused:
        return _refusal(refused)
    return JsonResponse(_progress_json(state))


def _component_action(action):
    """A POST on the active component: activate, tare or quit (bolt 010)."""

    @require_http_methods(["POST"])
    def view(request, session_id, sequence):
        try:
            state = action(session_id, sequence, _session_operator_id(request))
        except WeighingRefused as refused:
            return _refusal(refused)
        return JsonResponse(_progress_json(state))

    view.__name__ = f"component_{action.__name__}"
    return view


component_activate = _component_action(progression.activate)
component_tare = _component_action(progression.tare)
component_quit = _component_action(progression.quit_attempt)


@require_http_methods(["POST"])
def component_confirm(request, session_id, sequence):
    """F1 · OK: the server reads the scale itself; the body carries no weight."""
    try:
        record, state = confirmation.confirm(
            session_id, sequence, _session_operator_id(request)
        )
    except WeighingRefused as refused:
        return _refusal(refused)
    return JsonResponse(
        {"record": _record_json(record), "progress": _progress_json(state)},
        status=201,
    )


@require_http_methods(["GET", "POST"])
def session_write_back(request, session_id):
    """GET: the write-back status. POST: start or retry (FR-17, bolt 014)."""
    try:
        if request.method == "GET":
            record = consumption.status(session_id)
            return JsonResponse({"writeBack": record and _write_back_json(record)})
        record, body = consumption.start(session_id, _session_operator_id(request))
    except WeighingRefused as refused:
        return _refusal(refused)
    return JsonResponse(
        {
            "writeBack": _write_back_json(record),
            "batchId": record.batch_id,
            "body": body,
        }
    )


@require_http_methods(["POST"])
def session_write_back_result(request, session_id):
    """The browser's report of its post; the server checks OrgaTEX itself."""
    try:
        posted, reason = _parse_write_back_report(request)
    except (InvalidJson, InvalidRequest) as exc:
        return json_error(400, "VALIDATION_ERROR", str(exc))
    try:
        record = consumption.report(
            session_id, _session_operator_id(request), posted, reason
        )
    except WeighingRefused as refused:
        return _refusal(refused)
    return JsonResponse({"writeBack": _write_back_json(record)})


def _parse_write_back_report(request) -> tuple[bool, str]:
    payload = read_json_object(request)
    posted = payload.get("posted")
    if not isinstance(posted, bool):
        raise InvalidRequest("posted must be true or false")
    reason = payload.get("reason", "")
    if reason is None:
        reason = ""
    if not isinstance(reason, str):
        raise InvalidRequest("reason must be a string")
    return posted, reason


def _write_back_json(record: WriteBack) -> dict:
    return {
        "status": record.status,
        "idempotencyKey": record.idempotency_key,
        "attempts": record.attempts,
        "confirmedAt": record.confirmed_at and record.confirmed_at.isoformat(),
        "reason": record.last_error or None,
        "operatorId": record.operator_id,
    }


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
        "colour": component.colour,
        "displayMax": _quantity_text(component.display_max),
        "displayMaxText": format_weight(component.display_max, component.unit),
        "tareText": view.header.tare_text,
        "header": view.header.text,
        "headerMeta": view.header.meta,
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
    bar = component_rules.bar
    return {
        "target": _quantity_text(band.target),
        "targetAmount": format_amount(band.target, band.unit),
        "targetText": component_rules.target_text,
        "scale": {
            "scaleId": scale.scale_id,
            "label": scale.label,
            "classText": scale.class_text,
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
        "bar": {
            "lowPercent": str(bar.percent(band.low)),
            "widthPercent": str(bar.band_width(band)),
            "targetPercent": str(bar.percent(band.target)),
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


def _progress_json(state: progression.SessionProgress) -> dict:
    session, attempt = state.session, state.active_attempt
    return {
        "sessionId": session.pk,
        "batchId": session.batch_id,
        "state": session.state,
        "weighed": state.weighed,
        "total": state.total,
        "progressText": state.text,
        "active": attempt
        and {
            "sequence": attempt.component_sequence,
            "attemptId": attempt.pk,
            "scaleId": attempt.scale_id,
            "tared": attempt.is_tared,
            "startedAt": attempt.started_at.isoformat(),
        },
        "nextPending": state.next_pending,
        "components": [_component_progress_json(c) for c in state.components],
        **({"ended": _ended_json(state.ended)} if state.ended else {}),
    }


def _ended_json(ended: progression.EndedAttempt) -> dict:
    """How Quit ended the old attempt (bolt 012); only in the quit response."""
    discard = ended.discard
    unit = discard and discard.surplus.unit
    return {
        "attemptId": ended.attempt_id,
        "reason": ended.reason.value,
        "net": discard and format_amount(discard.net, unit),
        "surplus": discard and format_amount(discard.surplus.amount, unit),
        "unit": unit,
        "message": ended.message,
    }


def _component_progress_json(component: progression.ComponentProgress) -> dict:
    record = component.record
    return {
        "sequence": component.sequence,
        "state": component.state,
        "actualWeight": record and format_amount(record.actual_weight, record.unit),
        "unit": component.unit,
        "actualText": record and format_weight(record.actual_weight, record.unit),
        "recordId": record and record.pk,
    }


def _record_json(record: WeighingRecord) -> dict:
    return {
        "recordId": record.pk,
        "sessionId": record.session_id,
        "batchId": record.batch_id,
        "sequence": record.component_sequence,
        "componentCode": record.component_code,
        "componentName": record.component_name,
        "actualWeight": format_amount(record.actual_weight, record.unit),
        "unit": record.unit,
        "actualText": format_weight(record.actual_weight, record.unit),
        "lot": record.lot,
        "container": record.container,
        "tare": _quantity_text(record.tare),
        "tareText": format_quantity(record.tare, record.unit),
        "scaleId": record.scale_id,
        "target": _quantity_text(record.target),
        "toleranceMin": _quantity_text(record.tolerance_min),
        "toleranceMax": _quantity_text(record.tolerance_max),
        "result": record.result,
        "operator": _operator_json(OperatorRef.of(record.operator)),
        "recordedAt": record.recorded_at.isoformat(),
    }
