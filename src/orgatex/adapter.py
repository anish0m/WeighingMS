"""OrgaTEX adapter: the only WeighingMS Python module that knows OrgaTEX (IR-07).

It currently talks to the Dummy OrgaTEX training contract over HTTP. That
contract is defined by this project and is not the real OrgaTEX interface
(A-01, A-02 are unresolved); replacing it should only change this module.

Every read returns typed, immutable results with quantities as ``Decimal``, or
raises ``OrgatexNotFound`` / ``OrgatexUnavailable``. A failure is never
returned as data (NFR-7) and is logged with the request details (IR-09).
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)


class OrgatexError(Exception):
    """Base class for OrgaTEX read failures."""


class OrgatexNotFound(OrgatexError):
    """OrgaTEX answered that the batch or its recipe does not exist."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class OrgatexUnavailable(OrgatexError):
    """OrgaTEX could not be read: down, unreachable, timed out or malformed."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class _MalformedResponse(Exception):
    pass


@dataclass(frozen=True)
class Batch:
    batch_id: str
    order_id: str
    machine: str
    fabric_lot: str
    shade: str
    component_count: int
    status: str


@dataclass(frozen=True)
class Queue:
    received_at: datetime
    batches: tuple[Batch, ...]


@dataclass(frozen=True)
class RecipeComponent:
    sequence: int
    code: str
    name: str
    colour: str
    target_qty: Decimal
    unit: str
    tolerance: Decimal
    display_max: Decimal
    lot: str
    container: str
    tare: Decimal
    state: str


@dataclass(frozen=True)
class Recipe:
    batch_id: str
    recipe_name: str
    components: tuple[RecipeComponent, ...]


def fetch_queue() -> Queue:
    """Return the batch queue released for this station."""
    return _read("/batches", None, _parse_queue)


def fetch_batch(batch_id: str) -> Batch:
    """Return one batch; raise ``OrgatexNotFound`` if OrgaTEX does not know it."""
    path = f"/batches/{quote(batch_id, safe='')}"
    return _read(path, batch_id, lambda data: _parse_batch(data, batch_id))


def fetch_recipe(batch_id: str) -> Recipe:
    """Return the batch's recipe; ``OrgatexNotFound`` if batch or recipe is missing."""
    path = f"/batches/{quote(batch_id, safe='')}/recipe"
    return _read(path, batch_id, lambda data: _parse_recipe(data, batch_id))


def _read(path, batch_id, parse):
    url = settings.ORGATEX_BASE_URL.rstrip("/") + path
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=settings.ORGATEX_TIMEOUT_SECONDS) as response:
            raw = response.read()
    except HTTPError as exc:
        _raise_for_http_error(exc, url, batch_id)
    except OSError as exc:
        logger.warning(
            "OrgaTEX GET %s failed: %s (batch %s)", url, _describe(exc), batch_id
        )
        raise OrgatexUnavailable(f"OrgaTEX not reachable: {_describe(exc)}") from exc

    try:
        return parse(_load_json(raw))
    except _MalformedResponse as exc:
        logger.warning(
            "OrgaTEX GET %s -> 200 with malformed response: %s (batch %s)",
            url,
            exc,
            batch_id,
        )
        raise OrgatexUnavailable(f"Malformed OrgaTEX response: {exc}") from exc


def _raise_for_http_error(exc, url, batch_id):
    error = _error_body(exc)
    code = error[0] if error else None
    if exc.code == 404 and error:
        logger.info("OrgaTEX GET %s -> 404 %s (batch %s)", url, code, batch_id)
        raise OrgatexNotFound(*error) from exc
    logger.warning(
        "OrgaTEX GET %s -> HTTP %s %s (batch %s)", url, exc.code, code, batch_id
    )
    reason = f"OrgaTEX answered HTTP {exc.code} {code or ''}".strip()
    raise OrgatexUnavailable(reason) from exc


def _error_body(exc):
    """Return ``(code, message)`` from a contract error body, or ``None``."""
    try:
        error = _load_json(exc.read())["error"]
        return _str(error, "code"), _str(error, "message")
    except (_MalformedResponse, KeyError, TypeError, OSError):
        return None


def _reject_float(value):
    raise _MalformedResponse(f"JSON number {value} where a decimal string is required")


def _load_json(raw):
    try:
        return json.loads(raw, parse_float=_reject_float)
    except ValueError as exc:
        raise _MalformedResponse(f"invalid JSON ({exc})") from exc


def _parse_queue(data):
    received_at = _str(data, "receivedAt")
    try:
        received = datetime.fromisoformat(received_at)
    except ValueError as exc:
        raise _MalformedResponse(f"receivedAt {received_at!r} is not ISO") from exc
    batches = _field(data, "batches", list)
    return Queue(received, tuple(_parse_batch(item) for item in batches))


def _parse_batch(data, expected_id=None):
    batch = Batch(
        batch_id=_str(data, "batchId"),
        order_id=_str(data, "orderId"),
        machine=_str(data, "machine"),
        fabric_lot=_str(data, "fabricLot"),
        shade=_str(data, "shade"),
        component_count=_int(data, "componentCount"),
        status=_str(data, "status"),
    )
    _check_batch_id(batch.batch_id, expected_id)
    return batch


def _parse_recipe(data, expected_id):
    components = _field(data, "components", list)
    recipe = Recipe(
        batch_id=_str(data, "batchId"),
        recipe_name=_str(data, "recipeName"),
        components=tuple(_parse_component(item) for item in components),
    )
    _check_batch_id(recipe.batch_id, expected_id)
    return recipe


def _parse_component(data):
    return RecipeComponent(
        sequence=_int(data, "sequence"),
        code=_str(data, "code"),
        name=_str(data, "name"),
        colour=_str(data, "colour"),
        target_qty=_decimal(data, "targetQty"),
        unit=_str(data, "unit"),
        tolerance=_decimal(data, "tolerance"),
        display_max=_decimal(data, "displayMax"),
        lot=_str(data, "lot"),
        container=_str(data, "container"),
        tare=_decimal(data, "tare"),
        state=_str(data, "state"),
    )


def _check_batch_id(actual, expected):
    if expected is not None and actual != expected:
        raise _MalformedResponse(f"asked for {expected}, got {actual}")


def _field(data, key, kind):
    if not isinstance(data, dict) or key not in data:
        raise _MalformedResponse(f"missing field {key!r}")
    value = data[key]
    if not isinstance(value, kind) or isinstance(value, bool):
        raise _MalformedResponse(f"field {key!r} has the wrong type")
    return value


def _str(data, key):
    return _field(data, key, str)


def _int(data, key):
    return _field(data, key, int)


def _decimal(data, key):
    text = _str(data, key)
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise _MalformedResponse(f"field {key!r} is not a decimal string") from exc
    if not value.is_finite():
        raise _MalformedResponse(f"field {key!r} is not a finite decimal")
    return value


def _describe(exc):
    reason = getattr(exc, "reason", None)
    return str(reason if reason is not None else exc) or type(exc).__name__
