"""Builders for OrgaTEX adapter results, used where the adapter is stubbed."""

from dataclasses import replace
from decimal import Decimal

from orgatex.adapter import Batch, Recipe, RecipeComponent


def batch(**changes) -> Batch:
    base = Batch(
        batch_id="B-24187",
        order_id="SO-9931",
        machine="JET-04",
        fabric_lot="100% CTN knit · 480 kg",
        shade="Teal 4C",
        component_count=2,
        status="QUEUED",
    )
    return replace(base, **changes)


def component(sequence=1, **changes) -> RecipeComponent:
    base = RecipeComponent(
        sequence=sequence,
        code=f"DYE-000{sequence}",
        name=f"Dye {sequence}",
        colour="#000000",
        target_qty=Decimal("94.0"),
        unit="g",
        tolerance=Decimal("0.5"),
        display_max=Decimal("125.0"),
        lot="2026-0001",
        container="C-01",
        tare=Decimal("214.0"),
        state="pending",
    )
    return replace(base, **changes)


def recipe(*components, batch_id="B-24187") -> Recipe:
    if not components:
        components = (component(1), component(2))
    return Recipe(batch_id=batch_id, recipe_name="Teal 4C", components=components)
