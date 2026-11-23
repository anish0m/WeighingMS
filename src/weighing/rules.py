"""Weighing rules of one session component (bolt 009, ADR-008).

``component_rules`` gives the automatic scale, the tolerance band and the bar
scale of a recipe snapshot component. ``evaluate_reading`` judges a net
reading for it.
Bolt 010's confirm calls ``evaluate_reading`` with the server's own scale
re-read and refuses unless the result is within tolerance.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from batches.models import SnapshotComponent
from weighing.identity import load_component, load_session
from weighing.scale_selection import ScaleAssignment, select_scale
from weighing.tolerance import (
    ToleranceBand,
    WeightEvaluation,
    band_for,
    evaluate,
    format_weight,
)

HUNDRED = Decimal(100)
PERCENT_STEP = Decimal("0.1")
# The prototype keeps a very narrow band visible at 0.6 % of the bar.
MIN_BAND_PERCENT = Decimal("0.6")


@dataclass(frozen=True)
class BarScale:
    """The 0 – display-max bar of View 2 (bolt 011, plan Decision 1).

    Positions are Decimal percentages in 0.1 % steps, clamped to 0 – 100, so
    the browser only places them and does no arithmetic on quantities.
    """

    maximum: Decimal

    def percent(self, amount: Decimal) -> Decimal:
        if self.maximum <= 0:
            return Decimal(0)
        share = min(max(amount / self.maximum * HUNDRED, Decimal(0)), HUNDRED)
        return share.quantize(PERCENT_STEP, rounding=ROUND_HALF_UP)

    def band_width(self, band: ToleranceBand) -> Decimal:
        return max(self.percent(band.high) - self.percent(band.low), MIN_BAND_PERCENT)


@dataclass(frozen=True)
class ComponentRules:
    component: SnapshotComponent
    assignment: ScaleAssignment
    band: ToleranceBand
    bar: BarScale

    @property
    def target_text(self) -> str:
        return format_weight(self.band.target, self.band.unit)


def component_rules(component: SnapshotComponent) -> ComponentRules:
    return ComponentRules(
        component=component,
        assignment=select_scale(component.target_qty, component.unit),
        band=band_for(component),
        bar=BarScale(component.display_max),
    )


def evaluate_reading(
    session_id: int, sequence: int, net: Decimal, unit: str
) -> tuple[ComponentRules, WeightEvaluation]:
    """Evaluate ``net`` (in ``unit``) for component ``sequence`` of the session."""
    component = load_component(load_session(session_id), sequence)
    rules = component_rules(component)
    return rules, evaluate(rules.band, net, unit)
