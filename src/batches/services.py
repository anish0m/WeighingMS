"""Batch selection: which batch the station weighs and its recipe (FR-2, FR-3).

The server is the authority for opening a batch (ADR-001). Every selection
reads the batch and its recipe fresh from OrgaTEX through the OrgaTEX adapter,
applies the selection rules and only then stores an immutable snapshot
(ADR-003). Any refusal raises ``SelectionRefused`` and stores nothing.
"""

import logging
from enum import Enum

from django.db import transaction

from batches.models import BatchSelection, SelectionMethod, SnapshotComponent, Unit
from orgatex import adapter
from orgatex.adapter import Batch, OrgatexNotFound, OrgatexUnavailable, Recipe

logger = logging.getLogger(__name__)

# OrgaTEX statuses in which a batch is released for weighing (BR-03). The
# training seed uses only QUEUED.
SELECTABLE_STATUSES = frozenset({"QUEUED"})


class RefusalReason(Enum):
    BATCH_NOT_FOUND = "Batch not found"
    RECIPE_NOT_AVAILABLE = "Recipe not available in training data"
    NOT_RELEASED = "Batch not released"
    ORGATEX_UNAVAILABLE = "OrgaTEX unavailable"

    @property
    def code(self) -> str:
        return self.name


class SelectionRefused(Exception):
    """A scan or touch did not open a batch; nothing was stored."""

    def __init__(self, reason: RefusalReason, batch_code: str, message: str = ""):
        self.reason = reason
        self.batch_code = batch_code
        self.message = message or reason.value
        super().__init__(f"{reason.code}: {self.message} ({batch_code})")


class InvalidRecipe(ValueError):
    """The recipe OrgaTEX sent breaks a snapshot invariant."""


def check_selectable(batch: Batch) -> RefusalReason | None:
    """SelectionPolicy: ``None`` if the batch may be opened, else the reason."""
    if batch.status not in SELECTABLE_STATUSES:
        return RefusalReason.NOT_RELEASED
    return None


def check_recipe(recipe: Recipe) -> None:
    """Aggregate invariants for a recipe snapshot; raise ``InvalidRecipe``."""
    if not recipe.components:
        raise InvalidRecipe("recipe has no components")
    sequences = [component.sequence for component in recipe.components]
    if sequences != list(range(1, len(sequences) + 1)):
        raise InvalidRecipe(f"sequences {sequences} are not 1..N in order")
    for component in recipe.components:
        if component.unit not in Unit.values:
            raise InvalidRecipe(f"{component.code}: unknown unit {component.unit!r}")
        if component.target_qty <= 0:
            raise InvalidRecipe(f"{component.code}: target must be positive")
        if component.tolerance < 0:
            raise InvalidRecipe(f"{component.code}: tolerance must not be negative")


def select_batch(batch_code: str, method: str) -> BatchSelection:
    """Open ``batch_code`` (scanned or touched) and snapshot its recipe."""
    try:
        batch = adapter.fetch_batch(batch_code)
    except OrgatexNotFound as exc:
        raise _refused(RefusalReason.BATCH_NOT_FOUND, batch_code, method) from exc
    except OrgatexUnavailable as exc:
        raise _refused(RefusalReason.ORGATEX_UNAVAILABLE, batch_code, method) from exc

    reason = check_selectable(batch)
    if reason:
        raise _refused(reason, batch_code, method)

    try:
        recipe = adapter.fetch_recipe(batch_code)
    except OrgatexNotFound as exc:
        if exc.code == RefusalReason.RECIPE_NOT_AVAILABLE.code:
            reason = RefusalReason.RECIPE_NOT_AVAILABLE
            raise _refused(reason, batch_code, method, exc.message) from exc
        raise _refused(RefusalReason.BATCH_NOT_FOUND, batch_code, method) from exc
    except OrgatexUnavailable as exc:
        raise _refused(RefusalReason.ORGATEX_UNAVAILABLE, batch_code, method) from exc

    try:
        check_recipe(recipe)
    except InvalidRecipe as exc:
        logger.warning("OrgaTEX recipe for %s rejected: %s", batch_code, exc)
        raise _refused(RefusalReason.ORGATEX_UNAVAILABLE, batch_code, method) from exc

    selection = _store(batch, recipe, method)
    logger.info(
        "BatchSelected: selection %s, batch %s by %s, recipe %s, %s components",
        selection.pk,
        selection.batch_id,
        method,
        selection.recipe_name,
        len(recipe.components),
    )
    return selection


def _store(batch: Batch, recipe: Recipe, method: str) -> BatchSelection:
    with transaction.atomic():
        selection = BatchSelection.objects.create(
            batch_id=batch.batch_id,
            order_id=batch.order_id,
            machine=batch.machine,
            fabric_lot=batch.fabric_lot,
            shade=batch.shade,
            component_count=batch.component_count,
            batch_status=batch.status,
            method=SelectionMethod(method),
            recipe_name=recipe.recipe_name,
        )
        for component in recipe.components:
            SnapshotComponent.objects.create(
                selection=selection,
                sequence=component.sequence,
                code=component.code,
                name=component.name,
                colour=component.colour,
                target_qty=component.target_qty,
                unit=component.unit,
                tolerance=component.tolerance,
                display_max=component.display_max,
                lot=component.lot,
                container=component.container,
                tare=component.tare,
                orgatex_state=component.state,
            )
    return selection


def _refused(
    reason: RefusalReason, batch_code: str, method: str, message: str = ""
) -> SelectionRefused:
    """Log the BatchSelectionRefused event and return the exception to raise."""
    logger.info(
        "BatchSelectionRefused: batch %s by %s: %s", batch_code, method, reason.code
    )
    return SelectionRefused(reason, batch_code, message)
