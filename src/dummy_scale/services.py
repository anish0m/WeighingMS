"""Dummy Scale behaviour: readings, tare, training simulate controls, modes.

Training contract only, not a real scale interface.
"""

import logging
from decimal import Decimal

from django.db import transaction

from dummy_scale.models import DummyScale
from weighingms.api import InvalidQuantity, parse_decimal_string

logger = logging.getLogger(__name__)

FOUR_PLACES = Decimal("0.0001")

# Prototype buttons: "Simulate dispense" lands inside tolerance,
# "Simulate overshoot" lands well above it.
DISPENSE_FACTOR = Decimal("0.4")
OVERSHOOT_FACTOR = Decimal("4.8")

MODE_OK = "ok"
MODE_DISCONNECTED = "disconnected"
MODES = (MODE_OK, MODE_DISCONNECTED)


class ScaleNotFound(Exception):
    """No Dummy scale with this ID."""


class ScaleDisconnected(Exception):
    """The scale is switched to "disconnected" (training failure mode)."""


class InvalidSimulation(Exception):
    """The simulate request is malformed."""


@transaction.atomic
def seed_scales(scales) -> None:
    """Replace all Dummy scales with the given rows: status ready, weight 0."""
    DummyScale.objects.all().delete()
    for scale in scales:
        DummyScale.objects.create(
            scale_id=scale["scale_id"],
            name=scale["name"],
            capacity=Decimal(scale["capacity"]),
            unit=scale["unit"],
            net_weight=Decimal(0),
            status=DummyScale.STATUS_READY,
        )


def list_scales():
    return list(DummyScale.objects.all())


def scale_ids() -> list[str]:
    return list(DummyScale.objects.values_list("scale_id", flat=True))


def get_scale(scale_id: str) -> DummyScale:
    try:
        return DummyScale.objects.get(scale_id=scale_id)
    except DummyScale.DoesNotExist as exc:
        raise ScaleNotFound(scale_id) from exc


def _connected_scale(scale_id: str) -> DummyScale:
    scale = get_scale(scale_id)
    if scale.status == DummyScale.STATUS_DISCONNECTED:
        raise ScaleDisconnected(scale_id)
    return scale


def read_weight(scale_id: str) -> DummyScale:
    return _connected_scale(scale_id)


def _set_weight(scale: DummyScale, weight: Decimal) -> DummyScale:
    scale.net_weight = weight.quantize(FOUR_PLACES)
    scale.save(update_fields=["net_weight", "read_at"])
    return scale


def tare(scale_id: str) -> DummyScale:
    scale = _connected_scale(scale_id)
    logger.info("Dummy scale %s tared", scale_id)
    return _set_weight(scale, Decimal(0))


def _decimal(payload: dict, field: str) -> Decimal:
    try:
        return parse_decimal_string(payload.get(field), field)
    except InvalidQuantity as exc:
        raise InvalidSimulation(str(exc)) from exc


def _check_unit(scale: DummyScale, payload: dict) -> None:
    if payload.get("unit") != scale.unit:
        raise InvalidSimulation(f"unit must be {scale.unit} for {scale.scale_id}")


def simulate(scale_id: str, payload: dict) -> DummyScale:
    """Training control: drive the scale weight like the prototype's buttons.

    Actions: dispense (target + 0.4 x tolerance), overshoot (target + 4.8 x
    tolerance), reset (0) and set (an exact weight).
    """
    scale = _connected_scale(scale_id)
    action = payload.get("action")
    if action == "reset":
        weight = Decimal(0)
    elif action in ("dispense", "overshoot"):
        _check_unit(scale, payload)
        factor = DISPENSE_FACTOR if action == "dispense" else OVERSHOOT_FACTOR
        weight = _decimal(payload, "target") + factor * _decimal(payload, "tolerance")
    elif action == "set":
        _check_unit(scale, payload)
        weight = _decimal(payload, "weight")
    else:
        raise InvalidSimulation("action must be dispense, overshoot, reset or set")
    if weight > scale.capacity:
        raise InvalidSimulation(
            f"weight exceeds the capacity of {scale.scale_id} "
            f"({scale.capacity.normalize():f} {scale.unit})"
        )
    logger.info("Dummy scale %s simulate %s -> %s", scale_id, action, weight)
    return _set_weight(scale, weight)


def get_mode(scale_id: str) -> str:
    scale = get_scale(scale_id)
    return (
        MODE_DISCONNECTED if scale.status == DummyScale.STATUS_DISCONNECTED else MODE_OK
    )


def set_mode(scale_id: str, mode: str) -> None:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {', '.join(MODES)}")
    scale = get_scale(scale_id)
    scale.status = (
        DummyScale.STATUS_DISCONNECTED
        if mode == MODE_DISCONNECTED
        else DummyScale.STATUS_READY
    )
    scale.save(update_fields=["status"])
    logger.info("Dummy scale %s mode set to %s", scale_id, mode)
