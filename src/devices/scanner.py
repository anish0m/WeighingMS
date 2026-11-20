"""Scanner adapter: the only WeighingMS Python module that knows the scanner paths.

It reads the Dummy Scanner training contract over HTTP, which is not the real
keyboard-wedge / serial scanner (A-10). The browser watches scans through
scanner-client.js; the server uses this adapter to check a scanned code.
"""

from dataclasses import dataclass
from datetime import datetime

from django.conf import settings

from devices.http import (
    DeviceCallFailed,
    Malformed,
    call,
    choice_field,
    datetime_field,
    field,
)

KINDS = ("batch", "dyestuff")


class ScannerUnavailable(Exception):
    """The scanner could not be read; no scan may be assumed."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Scan:
    scan_id: int
    kind: str
    code: str
    scanned_at: datetime


def read_latest_scan() -> Scan | None:
    """Return the most recent scan, or ``None`` if nothing was scanned."""
    url = settings.SCANNER_BASE_URL.rstrip("/") + "/scanner/scans/latest"
    try:
        return call("GET", url, _parse_latest, device="Scanner")
    except DeviceCallFailed as exc:
        raise ScannerUnavailable(exc.reason) from exc


def read_new_scan(after_scan_id: int | None) -> Scan | None:
    """Return the latest scan only if it is newer than ``after_scan_id``.

    Passing the last received ``scan_id`` makes each scan arrive once.
    """
    scan = read_latest_scan()
    if scan is None or (after_scan_id is not None and scan.scan_id <= after_scan_id):
        return None
    return scan


def _parse_latest(data):
    if not isinstance(data, dict) or "scan" not in data:
        raise Malformed("missing field 'scan'")
    scan = data["scan"]
    if scan is None:
        return None
    return Scan(
        scan_id=field(scan, "scanId", int),
        kind=choice_field(scan, "kind", KINDS),
        code=field(scan, "code", str),
        scanned_at=datetime_field(scan, "scannedAt"),
    )
