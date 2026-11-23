"""Automatic scale selection by the configurable threshold (bolt 009, FR-8, NFR-13).

Target ≤ threshold → ``scale-3kg`` (3 kg precision, g); target > threshold →
``scale-32kg`` (32 kg floor, kg). The scale IDs are those of the Dummy Scale
training contract. The threshold is read from settings on every call, so a
changed setting applies the next time a component is activated.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from weighing.tolerance import GRAM, KILOGRAM, to_unit

AUTOMATIC = "automatic"


class ScaleClass(Enum):
    PRECISION = ("scale-3kg", "3 kg precision", GRAM)
    FLOOR = ("scale-32kg", "32 kg floor", KILOGRAM)

    def __init__(self, scale_id: str, label: str, unit: str) -> None:
        self.scale_id = scale_id
        self.label = label
        self.unit = unit


@dataclass(frozen=True)
class ScaleAssignment:
    scale: ScaleClass
    mode: str = AUTOMATIC


def scale_threshold_kg() -> Decimal:
    """The configured threshold; anything but a positive finite Decimal is refused."""
    threshold = settings.WEIGHING_SCALE_THRESHOLD_KG
    if (
        not isinstance(threshold, Decimal)
        or not threshold.is_finite()
        or threshold <= 0
    ):
        raise ImproperlyConfigured(
            f"WEIGHING_SCALE_THRESHOLD_KG must be a positive number: {threshold!r}"
        )
    return threshold


def select_scale(
    target: Decimal, unit: str, threshold_kg: Decimal | None = None
) -> ScaleAssignment:
    """≤ threshold → precision scale; > threshold → floor scale (Decimal kg)."""
    if threshold_kg is None:
        threshold_kg = scale_threshold_kg()
    target_kg = to_unit(target, unit, KILOGRAM)
    scale = ScaleClass.PRECISION if target_kg <= threshold_kg else ScaleClass.FLOOR
    return ScaleAssignment(scale)
