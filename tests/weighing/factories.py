"""Stored batch selections for weighing tests (unit 004's aggregate).

Weighing works against a stored selection, never OrgaTEX, so these tests
create the selection row directly instead of going through the Dummy.
"""

from decimal import Decimal

from batches.models import BatchSelection, SnapshotComponent
from weighing.models import Operator, WeighingSession


def selection(batch_id="B-24187"):
    return BatchSelection.objects.create(
        batch_id=batch_id,
        order_id="SO-9931",
        machine="JET-04",
        fabric_lot="100% CTN knit · 480 kg",
        shade="Teal 4C",
        component_count=5,
        batch_status="QUEUED",
        method="touch",
        recipe_name="Teal 4C",
    )


# (sequence, code, name, unit, lot, container, tare, target, tolerance, max):
# the Teal 4C training seed (prototype components).
TEAL_4C = (
    (
        1,
        "DYE-1180",
        "Remazol Brill. Blue RSPL",
        "g",
        "2026-0341",
        "C-09",
        "214",
        "1240.0",
        "6.0",
        "1600",
    ),
    (
        2,
        "DYE-2204",
        "Remazol Red RB",
        "g",
        "2026-0298",
        "C-11",
        "214",
        "386.0",
        "2.0",
        "520",
    ),
    (
        3,
        "DYE-4471",
        "Remazol Yellow RGB",
        "g",
        "2026-0387",
        "C-12",
        "214",
        "94.0",
        "0.5",
        "125",
    ),
    (
        4,
        "AUX-0101",
        "Sodium Sulphate",
        "kg",
        "2026-0112",
        "D-03",
        "1.850",
        "24.000",
        "0.120",
        "32",
    ),
    (
        5,
        "AUX-0107",
        "Soda Ash",
        "kg",
        "2026-0155",
        "D-05",
        "1.850",
        "9.600",
        "0.048",
        "14",
    ),
)
YELLOW_RGB = 3
SODIUM_SULPHATE = 4


def teal_selection(overrides=None):
    """B-24187 with its five snapshot components.

    ``overrides`` maps a sequence to field changes, e.g. ``{3: {"lot": ""}}``.
    """
    overrides = overrides or {}
    stored = selection()
    for (
        sequence,
        code,
        name,
        unit,
        lot,
        container,
        tare,
        target,
        tolerance,
        maximum,
    ) in TEAL_4C:
        fields = {
            "code": code,
            "name": name,
            "colour": "#000000",
            "target_qty": Decimal(target),
            "unit": unit,
            "tolerance": Decimal(tolerance),
            "display_max": Decimal(maximum),
            "lot": lot,
            "container": container,
            "tare": Decimal(tare),
            "orgatex_state": "pending",
        }
        fields.update(overrides.get(sequence, {}))
        SnapshotComponent.objects.create(selection=stored, sequence=sequence, **fields)
    return stored


def session(selection_row=None, operator_id="OP-01"):
    """An open weighing session for ``selection_row`` (default: Teal 4C)."""
    selection_row = selection_row or teal_selection()
    return WeighingSession.objects.create(
        selection=selection_row,
        batch_id=selection_row.batch_id,
        operator=Operator.objects.get(operator_id=operator_id),
    )
