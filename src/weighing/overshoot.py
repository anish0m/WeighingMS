"""The training overshoot rule decided at workbook STEP 24 (OQ-4, ADR-012).

An overweight component remains unconfirmed and the operator must use the
defined recovery action: remove material back into the band, or Quit (F4) to
discard and re-weigh. No recipe recalculation and no supervisor override
exist. The rule is a fixed code constant, not a setting; changing it needs a
new approved business rule. Pure rules in ``Decimal`` only (NFR-16).
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from weighing.tolerance import WeightEvaluation, format_amount, format_weight

HUNDRED = Decimal(100)
PERCENT_STEP = Decimal("0.1")


@dataclass(frozen=True)
class OvershootRule:
    confirm_allowed: bool
    recalculation: str
    override_available: bool
    override_reason: str
    recovery_text: str
    decision: str


OVERSHOOT_RULE = OvershootRule(
    confirm_allowed=False,
    recalculation="none",
    override_available=False,
    override_reason="Supervisor override is not available in this training build",
    recovery_text=(
        "Remove material until the weight is back in the band, "
        "or press Quit (F4) to discard and re-weigh."
    ),
    decision="OQ-4, workbook STEP 24, 2026-11-23",
)


def surplus_percent(surplus: Decimal, target: Decimal) -> Decimal:
    """The surplus as a % of the target, 0.1 % steps, round half up."""
    return (surplus / target * HUNDRED).quantize(PERCENT_STEP, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Surplus:
    """How far an over-tolerance net is above the target (amount and %)."""

    amount: Decimal
    percent: Decimal
    unit: str

    @property
    def amount_text(self) -> str:
        return format_weight(self.amount, self.unit)

    @property
    def heading(self) -> str:
        """e.g. "Surplus +2.4 g (+2.6%) — over tolerance"."""
        return f"Surplus +{self.amount_text} (+{self.percent:f}%) — over tolerance"

    def detail(self) -> dict:
        return {
            "surplus": format_amount(self.amount, self.unit),
            "surplusPercent": f"{self.percent:f}",
            "surplusText": self.amount_text,
        }


def surplus_of(evaluation: WeightEvaluation, target: Decimal) -> Surplus | None:
    """The Surplus of an ``over`` evaluation, otherwise None."""
    if evaluation.surplus is None:
        return None
    return Surplus(
        amount=evaluation.surplus,
        percent=surplus_percent(evaluation.surplus, target),
        unit=evaluation.unit,
    )


def overshoot_json(surplus: Surplus | None) -> dict | None:
    """The ``overshoot`` object of the evaluation JSON (the UI only shows it)."""
    if surplus is None:
        return None
    rule = OVERSHOOT_RULE
    return {
        "heading": surplus.heading,
        "recovery": rule.recovery_text,
        "confirmAllowed": rule.confirm_allowed,
        "recalculation": rule.recalculation,
        "overrideAvailable": rule.override_available,
        "overrideReason": rule.override_reason,
    }
