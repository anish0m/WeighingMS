"""Stored batch selections for weighing tests (unit 004's aggregate).

Weighing works against a stored selection, never OrgaTEX, so these tests
create the selection row directly instead of going through the Dummy.
"""

from batches.models import BatchSelection


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
