"""Target, still to weigh and the inclusive tolerance band (bolt 009, ADR-008/-009).

Pure rules in ``Decimal`` only (NFR-16); ``float`` never appears. A reading is
converted to the component's unit and taken once at display resolution
(0.1 g / 0.001 kg, round half up). That one value is shown, evaluated and
recorded (ADR-009). The browser holds no copy of these rules (ADR-008).
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

GRAM = "g"
KILOGRAM = "kg"
UNITS = (GRAM, KILOGRAM)
RESOLUTION = {GRAM: Decimal("0.1"), KILOGRAM: Decimal("0.001")}
GRAMS_PER_KG = Decimal(1000)
NEAR_FRACTION = Decimal("0.9")
ZERO = Decimal(0)

WITHIN_STATUS = "WITHIN TOLERANCE — PRESS OK TO CONFIRM"


class Zone(str, Enum):
    UNDER = "under"
    NEAR = "near"
    WITHIN = "within"
    OVER = "over"


def _check_unit(unit: str) -> None:
    if unit not in UNITS:
        raise ValueError(f"Unknown unit: {unit!r}")


def to_unit(amount: Decimal, from_unit: str, to_unit: str) -> Decimal:
    """Exact g <-> kg conversion (model Decision 1)."""
    _check_unit(from_unit)
    _check_unit(to_unit)
    if from_unit == to_unit:
        return amount
    if from_unit == GRAM:
        return amount / GRAMS_PER_KG
    return amount * GRAMS_PER_KG


def at_resolution(amount: Decimal, unit: str) -> Decimal:
    """Round half up to 0.1 g / 0.001 kg (ADR-009). Never returns -0."""
    _check_unit(unit)
    value = amount.quantize(RESOLUTION[unit], rounding=ROUND_HALF_UP)
    return abs(value) if value == 0 else value


def format_amount(amount: Decimal, unit: str) -> str:
    """The number only: "94.0", "24.000" (FR-10b), never an exponent."""
    return f"{at_resolution(amount, unit):f}"


def format_weight(amount: Decimal, unit: str) -> str:
    """Weighing format: "94.0 g", "24.000 kg". Tare text is bolt 008's format."""
    return f"{format_amount(amount, unit)} {unit}"


@dataclass(frozen=True)
class ToleranceBand:
    """target ± tolerance in the component's unit; both ends are within."""

    target: Decimal
    tolerance: Decimal
    unit: str

    @property
    def low(self) -> Decimal:
        return self.target - self.tolerance

    @property
    def high(self) -> Decimal:
        return self.target + self.tolerance

    @property
    def near_from(self) -> Decimal:
        return self.target * NEAR_FRACTION

    @property
    def caption(self) -> str:
        """e.g. "TOLERANCE ±0.5 g (93.5 – 94.5)"."""
        return (
            f"TOLERANCE ±{format_weight(self.tolerance, self.unit)}"
            f" ({format_amount(self.low, self.unit)}"
            f" – {format_amount(self.high, self.unit)})"
        )


def band_for(component) -> ToleranceBand:
    """The band of a recipe snapshot component (``SnapshotComponent``)."""
    return ToleranceBand(
        target=component.target_qty,
        tolerance=component.tolerance,
        unit=component.unit,
    )


def zone_of(band: ToleranceBand, net: Decimal) -> Zone:
    if net > band.high:
        return Zone.OVER
    if net >= band.low:
        return Zone.WITHIN
    if net >= band.near_from:
        return Zone.NEAR
    return Zone.UNDER


@dataclass(frozen=True)
class WeightEvaluation:
    net: Decimal
    unit: str
    zone: Zone
    still_to_weigh: Decimal
    surplus: Decimal | None

    @property
    def within_tolerance(self) -> bool:
        return self.zone is Zone.WITHIN

    @property
    def status_line(self) -> str:
        if self.zone is Zone.WITHIN:
            return WITHIN_STATUS
        if self.zone is Zone.OVER:
            return f"OVER TOLERANCE — SURPLUS +{format_weight(self.surplus, self.unit)}"
        return f"DISPENSE — {format_weight(self.still_to_weigh, self.unit)} REMAINING"


def evaluate(
    band: ToleranceBand, reading: Decimal, reading_unit: str
) -> WeightEvaluation:
    """Judge a net reading against the band (FR-11, FR-12)."""
    net = at_resolution(to_unit(reading, reading_unit, band.unit), band.unit)
    zone = zone_of(band, net)
    still = at_resolution(max(ZERO, band.target - net), band.unit)
    surplus = at_resolution(net - band.target, band.unit) if zone is Zone.OVER else None
    return WeightEvaluation(
        net=net, unit=band.unit, zone=zone, still_to_weigh=still, surplus=surplus
    )
