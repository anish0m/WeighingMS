"""Weighing rules of one session component (bolt 009, ADR-008).

``component_rules`` gives the automatic scale and the tolerance band of a
recipe snapshot component. ``evaluate_reading`` judges a net reading for it.
Bolt 010's confirm calls ``evaluate_reading`` with the server's own scale
re-read and refuses unless the result is within tolerance.
"""

from dataclasses import dataclass
from decimal import Decimal

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


@dataclass(frozen=True)
class ComponentRules:
    component: SnapshotComponent
    assignment: ScaleAssignment
    band: ToleranceBand

    @property
    def target_text(self) -> str:
        return format_weight(self.band.target, self.band.unit)


def component_rules(component: SnapshotComponent) -> ComponentRules:
    return ComponentRules(
        component=component,
        assignment=select_scale(component.target_qty, component.unit),
        band=band_for(component),
    )


def evaluate_reading(
    session_id: int, sequence: int, net: Decimal, unit: str
) -> tuple[ComponentRules, WeightEvaluation]:
    """Evaluate ``net`` (in ``unit``) for component ``sequence`` of the session."""
    component = load_component(load_session(session_id), sequence)
    rules = component_rules(component)
    return rules, evaluate(rules.band, net, unit)
