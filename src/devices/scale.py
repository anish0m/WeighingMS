"""Scale adapter: the only WeighingMS Python module that knows the scale paths.

It reads the Dummy Scale training contract over HTTP, which is not the real
scale indicator interface (A-05). The server uses it to re-read the weight
before accepting a confirmation; the browser polls through scale-client.js.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from urllib.parse import quote

from django.conf import settings

from devices.http import (
    DeviceCallFailed,
    Malformed,
    call,
    choice_field,
    datetime_field,
    decimal_field,
    field,
)

STATUSES = ("ready", "disconnected")


class ScaleError(Exception):
    """Base class for scale failures; never treat as a valid reading."""

    def __init__(self, scale_id: str, reason: str) -> None:
        super().__init__(f"{scale_id}: {reason}")
        self.scale_id = scale_id
        self.reason = reason


class ScaleDisconnected(ScaleError):
    """The scale reports that it is disconnected (IR-13)."""


class ScaleUnavailable(ScaleError):
    """The scale could not be read: unknown, unreachable, timed out, malformed."""


@dataclass(frozen=True)
class ScaleReading:
    scale_id: str
    net_weight: Decimal
    unit: str
    status: str
    read_at: datetime


def read_weight(scale_id: str) -> ScaleReading:
    """Return the current net weight of ``scale_id`` (and of no other scale)."""
    return _call("GET", scale_id, "weight", _reading_parser(scale_id))


def read_status(scale_id: str) -> str:
    """Return ``"ready"`` or ``"disconnected"`` for ``scale_id``."""

    def parse(data):
        _check_scale_id(data, scale_id)
        return choice_field(data, "status", STATUSES)

    return _call("GET", scale_id, "status", parse)


def tare(scale_id: str) -> ScaleReading:
    """Zero the net weight of ``scale_id``; return the zeroed reading."""
    return _call("POST", scale_id, "tare", _reading_parser(scale_id))


def _call(method, scale_id, action, parse):
    base = settings.SCALE_BASE_URL.rstrip("/")
    url = f"{base}/scales/{quote(scale_id, safe='')}/{action}"
    try:
        return call(method, url, parse, device=f"Scale {scale_id}")
    except DeviceCallFailed as exc:
        if exc.status == 503 and exc.code == "SCALE_DISCONNECTED":
            raise ScaleDisconnected(scale_id, "scale disconnected") from exc
        raise ScaleUnavailable(scale_id, exc.reason) from exc


def _reading_parser(scale_id):
    def parse(data):
        _check_scale_id(data, scale_id)
        return ScaleReading(
            scale_id=scale_id,
            net_weight=decimal_field(data, "netWeight"),
            unit=field(data, "unit", str),
            status=choice_field(data, "status", STATUSES),
            read_at=datetime_field(data, "readAt"),
        )

    return parse


def _check_scale_id(data, scale_id):
    actual = field(data, "scaleId", str)
    if actual != scale_id:
        raise Malformed(f"asked for {scale_id}, got {actual}")
