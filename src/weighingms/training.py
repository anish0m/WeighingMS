"""Training-only failure switches for every Dummy (/api/training/modes).

Each mode is stored in its own Dummy app (DB-10); this module only dispatches.
Training controls are never part of the integration contracts.
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from dummy_orgatex import services as orgatex
from dummy_printer import services as printer
from dummy_scale import services as scale
from dummy_scanner import services as scanner
from weighingms.api import InvalidJson, json_error, read_json_object

SINGLE_TARGETS = {
    "orgatex": (orgatex.get_mode, orgatex.set_mode),
    "scanner": (scanner.get_mode, scanner.set_mode),
    "printer": (printer.get_mode, printer.set_mode),
}


def all_modes() -> dict:
    modes = {"orgatex": orgatex.get_mode()}
    for scale_id in scale.scale_ids():
        modes[scale_id] = scale.get_mode(scale_id)
    modes["scanner"] = scanner.get_mode()
    modes["printer"] = printer.get_mode()
    return modes


def _setter(target: str):
    if target in SINGLE_TARGETS:
        return SINGLE_TARGETS[target][1]
    if target in scale.scale_ids():
        return lambda mode: scale.set_mode(target, mode)
    return None


@require_GET
def modes(request):
    return JsonResponse({"modes": all_modes()})


@csrf_exempt
@require_http_methods(["PUT"])
def set_mode(request, target):
    setter = _setter(target)
    if setter is None:
        return json_error(400, "INVALID_TARGET", f"Unknown training target: {target}")
    try:
        payload = read_json_object(request)
        setter(payload.get("mode"))
    except InvalidJson as exc:
        return json_error(400, "VALIDATION_ERROR", str(exc))
    except ValueError as exc:
        return json_error(400, "INVALID_MODE", str(exc))
    return JsonResponse({"modes": all_modes()})
