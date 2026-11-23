"""Batch history: every weighing record of a batch (story 011, ADR-014).

A read-only query over the immutable records (ADR-010), from all of the
batch's sessions, in component sequence and then record time. An unknown
batch, or one with no records, gives an empty list. No filters (OQ-2).
"""

from weighing.models import WeighingRecord


def records(batch_id: str) -> list[WeighingRecord]:
    return list(
        WeighingRecord.objects.filter(batch_id=batch_id)
        .select_related("operator")
        .order_by("component_sequence", "recorded_at", "pk")
    )
