"""Dummy OrgaTEX JSON endpoints (training contract, not the real interface).

The endpoints are CSRF-exempt because they stand in for an external system
that the browser calls directly (STEP 12 decision).
"""

import json

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from dummy_orgatex import services


def _error(status: int, code: str, message: str) -> JsonResponse:
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)


def _batch_not_found(batch_id: str) -> JsonResponse:
    return _error(404, "BATCH_NOT_FOUND", f"Batch not found: {batch_id}")


def _batch_json(batch) -> dict:
    return {
        "batchId": batch.batch_id,
        "orderId": batch.order_id,
        "machine": batch.machine,
        "fabricLot": batch.fabric_lot,
        "shade": batch.shade,
        "componentCount": batch.component_count,
        "status": batch.status,
    }


def _component_json(comp) -> dict:
    return {
        "sequence": comp.sequence,
        "code": comp.code,
        "name": comp.name,
        "colour": comp.colour,
        "targetQty": str(comp.target_qty),
        "unit": comp.unit,
        "tolerance": str(comp.tolerance),
        "displayMax": str(comp.display_max),
        "lot": comp.lot,
        "container": comp.container,
        "tare": str(comp.tare),
        "state": comp.state,
    }


def _consumption_json(consumption, duplicate=None) -> dict:
    body = {
        "batchId": consumption.batch.batch_id,
        "idempotencyKey": consumption.idempotency_key,
        "acceptedAt": consumption.accepted_at.isoformat(),
        "components": [
            {"code": ln.code, "actualQty": str(ln.actual_qty), "unit": ln.unit}
            for ln in consumption.lines.all()
        ],
    }
    if duplicate is not None:
        body["duplicate"] = duplicate
    return body


@require_GET
def batch_list(request):
    batches = services.list_batches()
    return JsonResponse(
        {
            "receivedAt": timezone.now().isoformat(),
            "batches": [_batch_json(b) for b in batches],
        }
    )


@require_GET
def batch_detail(request, batch_id):
    try:
        batch = services.get_batch(batch_id)
    except services.BatchNotFound:
        return _batch_not_found(batch_id)
    return JsonResponse(_batch_json(batch))


@require_GET
def batch_recipe(request, batch_id):
    try:
        recipe = services.get_recipe(batch_id)
    except services.BatchNotFound:
        return _batch_not_found(batch_id)
    except services.RecipeNotAvailable:
        return _error(
            404, "RECIPE_NOT_AVAILABLE", "Recipe not available in training data"
        )
    return JsonResponse(
        {
            "batchId": batch_id,
            "recipeName": recipe.name,
            "components": [_component_json(c) for c in recipe.components.all()],
        }
    )


@csrf_exempt
@require_http_methods(["GET", "POST"])
def batch_consumption(request, batch_id):
    if request.method == "GET":
        try:
            consumptions = services.list_consumptions(batch_id)
        except services.BatchNotFound:
            return _batch_not_found(batch_id)
        return JsonResponse(
            {
                "batchId": batch_id,
                "consumptions": [_consumption_json(c) for c in consumptions],
            }
        )

    try:
        payload = json.loads(request.body or b"")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error(400, "VALIDATION_ERROR", "Body must be valid JSON")
    try:
        consumption, duplicate = services.accept_consumption(batch_id, payload)
    except services.BatchNotFound:
        return _batch_not_found(batch_id)
    except services.RecipeNotAvailable:
        return _error(
            404, "RECIPE_NOT_AVAILABLE", "Recipe not available in training data"
        )
    except services.InvalidConsumption as exc:
        return _error(400, "VALIDATION_ERROR", str(exc))
    except services.IdempotencyKeyConflict:
        return _error(
            409,
            "IDEMPOTENCY_KEY_CONFLICT",
            "Idempotency key already used for another batch",
        )
    return JsonResponse(
        _consumption_json(consumption, duplicate), status=200 if duplicate else 201
    )
