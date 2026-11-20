"""Dummy OrgaTEX behaviour: seeding, batch and recipe reads, consumption intake.

Training contract only, not the real OrgaTEX interface.
"""

import logging
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.utils import timezone

from dummy_orgatex import seed_data
from dummy_orgatex.models import (
    DummyBatch,
    DummyConsumption,
    DummyConsumptionLine,
    DummyRecipe,
    DummyRecipeComponent,
)
from dummy_scale.models import DummyScale

logger = logging.getLogger(__name__)


class BatchNotFound(Exception):
    """No batch with this ID exists in Dummy OrgaTEX."""


class RecipeNotAvailable(Exception):
    """The batch exists but has no recipe in the training data (OQ-5)."""


class InvalidConsumption(Exception):
    """The consumption payload is malformed."""


class IdempotencyKeyConflict(Exception):
    """The idempotency key was already used for a different batch."""


@transaction.atomic
def seed_training_scenario() -> None:
    """Reset Dummy OrgaTEX and Dummy Scale to the prototype scenario.

    Deletes all existing rows first, so running it again gives the same state
    without duplicates.
    """
    DummyBatch.objects.all().delete()
    DummyScale.objects.all().delete()

    for position, row in enumerate(seed_data.BATCHES, start=1):
        batch = DummyBatch.objects.create(
            status=DummyBatch.STATUS_QUEUED, queue_position=position, **row
        )
        recipe_data = seed_data.RECIPES.get(batch.batch_id)
        if recipe_data is None:
            continue
        recipe = DummyRecipe.objects.create(batch=batch, name=recipe_data["name"])
        for sequence, comp in enumerate(recipe_data["components"], start=1):
            DummyRecipeComponent.objects.create(
                recipe=recipe,
                sequence=sequence,
                code=comp["code"],
                name=comp["name"],
                colour=comp["colour"],
                target_qty=Decimal(comp["target_qty"]),
                unit=comp["unit"],
                tolerance=Decimal(comp["tolerance"]),
                display_max=Decimal(comp["display_max"]),
                lot=comp["lot"],
                container=comp["container"],
                tare=Decimal(comp["tare"]),
                state=DummyRecipeComponent.STATE_PENDING,
            )

    for scale in seed_data.SCALES:
        DummyScale.objects.create(
            scale_id=scale["scale_id"],
            name=scale["name"],
            capacity=Decimal(scale["capacity"]),
            unit=scale["unit"],
            net_weight=Decimal(0),
            status=DummyScale.STATUS_READY,
        )
    logger.info("Training scenario seeded")


def list_batches():
    return list(DummyBatch.objects.all())


def get_batch(batch_id: str) -> DummyBatch:
    try:
        return DummyBatch.objects.get(batch_id=batch_id)
    except DummyBatch.DoesNotExist as exc:
        raise BatchNotFound(batch_id) from exc


def get_recipe(batch_id: str) -> DummyRecipe:
    batch = get_batch(batch_id)
    try:
        return DummyRecipe.objects.prefetch_related("components").get(batch=batch)
    except DummyRecipe.DoesNotExist as exc:
        raise RecipeNotAvailable(batch_id) from exc


def _parse_quantity(value) -> Decimal:
    """Accept only decimal strings; JSON numbers would be floats."""
    if not isinstance(value, str):
        raise InvalidConsumption("actualQty must be a decimal string")
    try:
        qty = Decimal(value)
    except InvalidOperation as exc:
        raise InvalidConsumption("actualQty is not a decimal") from exc
    if not qty.is_finite() or qty < 0:
        raise InvalidConsumption("actualQty must be a finite, non-negative decimal")
    return qty


def _validate_lines(recipe: DummyRecipe, components) -> list[dict]:
    if not isinstance(components, list) or not components:
        raise InvalidConsumption("components must be a non-empty list")
    units_by_code = {c.code: c.unit for c in recipe.components.all()}
    seen = set()
    lines = []
    for item in components:
        if not isinstance(item, dict):
            raise InvalidConsumption("each component must be an object")
        code = item.get("code")
        if code not in units_by_code:
            raise InvalidConsumption(f"unknown component code: {code}")
        if code in seen:
            raise InvalidConsumption(f"duplicate component code: {code}")
        seen.add(code)
        unit = item.get("unit")
        if unit != units_by_code[code]:
            raise InvalidConsumption(f"unit for {code} must be {units_by_code[code]}")
        lines.append(
            {
                "code": code,
                "actual_qty": _parse_quantity(item.get("actualQty")),
                "unit": unit,
            }
        )
    return lines


def _existing(batch: DummyBatch, key: str):
    existing = DummyConsumption.objects.filter(idempotency_key=key).first()
    if existing is not None and existing.batch_id != batch.pk:
        raise IdempotencyKeyConflict(key)
    return existing


def accept_consumption(batch_id: str, payload) -> tuple[DummyConsumption, bool]:
    """Store a consumption post once per idempotency key.

    Returns the stored consumption and ``True`` if it was a duplicate.
    """
    batch = get_batch(batch_id)
    if not isinstance(payload, dict):
        raise InvalidConsumption("body must be a JSON object")
    key = payload.get("idempotencyKey")
    if not isinstance(key, str) or not key.strip():
        raise InvalidConsumption("idempotencyKey is required")

    existing = _existing(batch, key)
    if existing is not None:
        logger.info("Duplicate consumption post %s for %s", key, batch_id)
        return existing, True

    recipe = get_recipe(batch_id)
    lines = _validate_lines(recipe, payload.get("components"))
    try:
        with transaction.atomic():
            consumption = DummyConsumption.objects.create(
                batch=batch, idempotency_key=key, accepted_at=timezone.now()
            )
            DummyConsumptionLine.objects.bulk_create(
                DummyConsumptionLine(consumption=consumption, **line) for line in lines
            )
    except IntegrityError:
        # A concurrent post with the same key won the race.
        existing = _existing(batch, key)
        if existing is None:
            raise
        return existing, True
    logger.info("Consumption %s accepted for %s", key, batch_id)
    return consumption, False


def list_consumptions(batch_id: str):
    batch = get_batch(batch_id)
    return list(batch.consumptions.prefetch_related("lines"))
