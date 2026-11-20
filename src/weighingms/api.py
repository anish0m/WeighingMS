"""Small helpers shared by the JSON endpoints."""

import json
from decimal import Decimal, InvalidOperation

from django.http import JsonResponse


class InvalidJson(ValueError):
    """The request body is not a JSON object."""


class InvalidQuantity(ValueError):
    """A quantity is not a finite, non-negative decimal string."""


def json_error(status: int, code: str, message: str) -> JsonResponse:
    """Standard error body: {"error": {"code": ..., "message": ...}}."""
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)


def read_json(request):
    """Parse the request body as JSON; raise InvalidJson if it is not valid."""
    try:
        return json.loads(request.body or b"")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise InvalidJson("Body must be valid JSON") from exc


def read_json_object(request) -> dict:
    payload = read_json(request)
    if not isinstance(payload, dict):
        raise InvalidJson("Body must be a JSON object")
    return payload


def parse_decimal_string(value, field: str) -> Decimal:
    """Parse a finite, non-negative decimal from a JSON string.

    JSON numbers are rejected because they would arrive as floats (NFR-16).
    """
    if not isinstance(value, str):
        raise InvalidQuantity(f"{field} must be a decimal string")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise InvalidQuantity(f"{field} is not a decimal") from exc
    if not number.is_finite() or number < 0:
        raise InvalidQuantity(f"{field} must be a finite, non-negative decimal")
    return number
