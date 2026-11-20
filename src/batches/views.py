"""WeighingMS batch-selection endpoints under /station/api/ (ADR-002).

Thin views: validate the request, call the service, return JSON. There is
no endpoint that changes a recipe (C-01).
"""

from decimal import Decimal

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from batches import services
from batches.models import BatchSelection, SelectionMethod
from weighingms.api import InvalidJson, json_error, read_json_object

MAX_BATCH_CODE = 32
QUANTUM = Decimal("0.0001")

REFUSAL_STATUS = {
    services.RefusalReason.BATCH_NOT_FOUND: 404,
    services.RefusalReason.RECIPE_NOT_AVAILABLE: 409,
    services.RefusalReason.NOT_RELEASED: 409,
    services.RefusalReason.ORGATEX_UNAVAILABLE: 503,
}


class InvalidRequest(ValueError):
    pass


def _parse_selection_request(request):
    payload = read_json_object(request)
    batch_code = payload.get("batchId")
    if not isinstance(batch_code, str) or not batch_code.strip():
        raise InvalidRequest("batchId is required")
    batch_code = batch_code.strip()
    if len(batch_code) > MAX_BATCH_CODE:
        raise InvalidRequest(f"batchId is longer than {MAX_BATCH_CODE} characters")
    method = payload.get("method")
    if method not in SelectionMethod.values:
        raise InvalidRequest("method must be 'scan' or 'touch'")
    return batch_code, method


@require_POST
def selections(request):
    try:
        batch_code, method = _parse_selection_request(request)
    except (InvalidJson, InvalidRequest) as exc:
        return json_error(400, "INVALID_REQUEST", str(exc))
    try:
        selection = services.select_batch(batch_code, method)
    except services.SelectionRefused as refusal:
        status = REFUSAL_STATUS[refusal.reason]
        return json_error(status, refusal.reason.code, refusal.message)
    return JsonResponse(_selection_json(selection), status=201)


@require_GET
def selection_detail(request, selection_id):
    selection = BatchSelection.objects.filter(pk=selection_id).first()
    if selection is None:
        return json_error(
            404, "SELECTION_NOT_FOUND", f"Selection not found: {selection_id}"
        )
    return JsonResponse(_selection_json(selection))


def _selection_json(selection: BatchSelection) -> dict:
    q = _quantity_text
    return {
        "selectionId": selection.pk,
        "method": selection.method,
        "selectedAt": selection.selected_at.isoformat(),
        "batch": {
            "batchId": selection.batch_id,
            "orderId": selection.order_id,
            "machine": selection.machine,
            "fabricLot": selection.fabric_lot,
            "shade": selection.shade,
            "componentCount": selection.component_count,
            "status": selection.batch_status,
        },
        "recipe": {
            "recipeName": selection.recipe_name,
            "components": [
                {
                    "sequence": c.sequence,
                    "code": c.code,
                    "name": c.name,
                    "colour": c.colour,
                    "targetQty": q(c.target_qty),
                    "unit": c.unit,
                    "tolerance": q(c.tolerance),
                    "displayMax": q(c.display_max),
                    "lot": c.lot,
                    "container": c.container,
                    "tare": q(c.tare),
                    "state": c.orgatex_state,
                }
                for c in selection.components.all()
            ],
        },
    }


def _quantity_text(value: Decimal) -> str:
    """Quantities go out as fixed 4-place decimal strings, never JSON numbers."""
    return f"{value.quantize(QUANTUM):f}"
