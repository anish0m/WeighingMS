"""Dummy Scale JSON endpoints (training contract, not a real scale interface)."""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from dummy_scale import services
from weighingms.api import InvalidJson, json_error, read_json_object


def _scale_not_found(scale_id: str) -> JsonResponse:
    return json_error(404, "SCALE_NOT_FOUND", f"Scale not found: {scale_id}")


def _disconnected(scale_id: str) -> JsonResponse:
    return json_error(503, "SCALE_DISCONNECTED", f"Scale disconnected: {scale_id}")


def _reading_json(scale) -> dict:
    return {
        "scaleId": scale.scale_id,
        "netWeight": str(scale.net_weight),
        "unit": scale.unit,
        "status": scale.status,
        "readAt": scale.read_at.isoformat(),
    }


@require_GET
def scale_list(request):
    return JsonResponse(
        {
            "scales": [
                {
                    "scaleId": s.scale_id,
                    "name": s.name,
                    "capacity": str(s.capacity),
                    "unit": s.unit,
                    "status": s.status,
                }
                for s in services.list_scales()
            ]
        }
    )


@require_GET
def scale_status(request, scale_id):
    try:
        scale = services.get_scale(scale_id)
    except services.ScaleNotFound:
        return _scale_not_found(scale_id)
    return JsonResponse({"scaleId": scale.scale_id, "status": scale.status})


@require_GET
def scale_weight(request, scale_id):
    try:
        scale = services.read_weight(scale_id)
    except services.ScaleNotFound:
        return _scale_not_found(scale_id)
    except services.ScaleDisconnected:
        return _disconnected(scale_id)
    return JsonResponse(_reading_json(scale))


@csrf_exempt
@require_POST
def scale_tare(request, scale_id):
    try:
        scale = services.tare(scale_id)
    except services.ScaleNotFound:
        return _scale_not_found(scale_id)
    except services.ScaleDisconnected:
        return _disconnected(scale_id)
    return JsonResponse(_reading_json(scale))


@csrf_exempt
@require_POST
def scale_simulate(request, scale_id):
    """Training-only control (mounted under /api/training/)."""
    try:
        payload = read_json_object(request)
        scale = services.simulate(scale_id, payload)
    except InvalidJson as exc:
        return json_error(400, "VALIDATION_ERROR", str(exc))
    except services.ScaleNotFound:
        return _scale_not_found(scale_id)
    except services.ScaleDisconnected:
        return _disconnected(scale_id)
    except services.InvalidSimulation as exc:
        return json_error(400, "VALIDATION_ERROR", str(exc))
    return JsonResponse(_reading_json(scale))
