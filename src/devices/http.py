"""Shared HTTP plumbing for the device adapters (scale, scanner).

Each adapter module keeps its own paths and result types; this module only
sends the request, rejects floats, and logs every failure with the request
details (IR-09). Callers map ``DeviceCallFailed`` to their own fail-safe
exceptions, so a failure is never returned as data (NFR-7).
"""

import json
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger("devices")


class DeviceCallFailed(Exception):
    """A device call failed. ``status``/``code`` are set for HTTP errors."""

    def __init__(self, reason: str, status: int | None = None, code: str | None = None):
        super().__init__(reason)
        self.reason = reason
        self.status = status
        self.code = code


class Malformed(Exception):
    """The response does not match the training contract."""


def call(method, url, parse, device):
    """Send ``method url`` and return ``parse(json_body)``.

    Raises ``DeviceCallFailed`` on an HTTP error, a network error or a
    malformed body, after logging it at WARNING.
    """
    request = Request(url, data=b"" if method == "POST" else None, method=method)
    request.add_header("Accept", "application/json")
    try:
        with urlopen(request, timeout=settings.DEVICE_TIMEOUT_SECONDS) as response:
            raw = response.read()
    except HTTPError as exc:
        code = _error_code(exc)
        logger.warning(
            "%s %s %s -> HTTP %s %s", device, method, url, exc.code, code or ""
        )
        raise DeviceCallFailed(
            f"HTTP {exc.code} {code or ''}".strip(), exc.code, code
        ) from exc
    except OSError as exc:
        reason = str(getattr(exc, "reason", None) or exc) or type(exc).__name__
        logger.warning("%s %s %s failed: %s", device, method, url, reason)
        raise DeviceCallFailed(f"not reachable: {reason}") from exc

    try:
        return parse(load_json(raw))
    except Malformed as exc:
        logger.warning(
            "%s %s %s -> 200 with malformed response: %s", device, method, url, exc
        )
        raise DeviceCallFailed(f"malformed response: {exc}") from exc


def _error_code(exc):
    try:
        return field(load_json(exc.read())["error"], "code", str)
    except (Malformed, KeyError, TypeError, OSError):
        return None


def _reject_float(value):
    raise Malformed(f"JSON number {value} where a decimal string is required")


def load_json(raw):
    try:
        return json.loads(raw, parse_float=_reject_float)
    except ValueError as exc:
        raise Malformed(f"invalid JSON ({exc})") from exc


def field(data, key, kind):
    if not isinstance(data, dict) or key not in data:
        raise Malformed(f"missing field {key!r}")
    value = data[key]
    if not isinstance(value, kind) or isinstance(value, bool):
        raise Malformed(f"field {key!r} has the wrong type")
    return value


def decimal_field(data, key):
    text = field(data, key, str)
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise Malformed(f"field {key!r} is not a decimal string") from exc
    if not value.is_finite():
        raise Malformed(f"field {key!r} is not a finite decimal")
    return value


def datetime_field(data, key):
    text = field(data, key, str)
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise Malformed(f"field {key!r} is not an ISO datetime") from exc


def choice_field(data, key, allowed):
    value = field(data, key, str)
    if value not in allowed:
        raise Malformed(f"field {key!r} has unexpected value {value!r}")
    return value
