"""Dummy Scanner behaviour: simulated scans, latest scan, failure mode.

Training contract only, not a real scanner interface.
"""

import logging

from django.utils import timezone

from dummy_scanner.models import DummyScan, DummyScannerState

logger = logging.getLogger(__name__)

MODES = (DummyScannerState.MODE_OK, DummyScannerState.MODE_UNAVAILABLE)
KINDS = (DummyScan.KIND_BATCH, DummyScan.KIND_DYESTUFF)
MAX_CODE_LENGTH = 64


class ScannerUnavailable(Exception):
    """The scanner is switched to "unavailable" (training failure mode)."""


class InvalidScan(Exception):
    """The simulated scan is malformed."""


def _state() -> DummyScannerState:
    state, _ = DummyScannerState.objects.get_or_create(pk=1)
    return state


def get_mode() -> str:
    return _state().mode


def set_mode(mode: str) -> None:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {', '.join(MODES)}")
    state = _state()
    state.mode = mode
    state.save(update_fields=["mode"])
    logger.info("Dummy scanner mode set to %s", mode)


def status() -> str:
    return (
        "unavailable" if get_mode() == DummyScannerState.MODE_UNAVAILABLE else "ready"
    )


def _ensure_available() -> None:
    if get_mode() == DummyScannerState.MODE_UNAVAILABLE:
        raise ScannerUnavailable()


def reset() -> None:
    """Clear all scans and switch the scanner back to ok."""
    DummyScan.objects.all().delete()
    DummyScannerState.objects.all().delete()


def submit_scan(kind, code) -> DummyScan:
    """Training control: simulate scanning a batch or dyestuff barcode."""
    _ensure_available()
    if kind not in KINDS:
        raise InvalidScan("kind must be batch or dyestuff")
    if not isinstance(code, str) or not code.strip():
        raise InvalidScan("code is required")
    if len(code) > MAX_CODE_LENGTH:
        raise InvalidScan(f"code must be at most {MAX_CODE_LENGTH} characters")
    scan = DummyScan.objects.create(
        kind=kind, code=code.strip(), scanned_at=timezone.now()
    )
    logger.info("Dummy scan %s %s", kind, scan.code)
    return scan


def latest_scan() -> DummyScan | None:
    _ensure_available()
    return DummyScan.objects.order_by("-scanned_at", "-id").first()
