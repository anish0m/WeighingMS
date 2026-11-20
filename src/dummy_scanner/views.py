"""Dummy Scanner JSON endpoints (training contract, not a real scanner)."""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from dummy_scanner import services
from weighingms.api import InvalidJson, json_error, read_json_object


def _unavailable() -> JsonResponse:
    return json_error(503, "SCANNER_UNAVAILABLE", "Scanner unavailable")


def _scan_json(scan) -> dict:
    return {
        "scanId": scan.pk,
        "kind": scan.kind,
        "code": scan.code,
        "scannedAt": scan.scanned_at.isoformat(),
    }


@require_GET
def scanner_status(request):
    return JsonResponse({"status": services.status()})


@require_GET
def latest_scan(request):
    try:
        scan = services.latest_scan()
    except services.ScannerUnavailable:
        return _unavailable()
    return JsonResponse({"scan": _scan_json(scan) if scan else None})


@csrf_exempt
@require_POST
def simulate_scan(request):
    """Training-only control (mounted under /api/training/)."""
    try:
        payload = read_json_object(request)
        scan = services.submit_scan(payload.get("kind"), payload.get("code"))
    except InvalidJson as exc:
        return json_error(400, "VALIDATION_ERROR", str(exc))
    except services.ScannerUnavailable:
        return _unavailable()
    except services.InvalidScan as exc:
        return json_error(400, "VALIDATION_ERROR", str(exc))
    return JsonResponse(_scan_json(scan), status=201)
