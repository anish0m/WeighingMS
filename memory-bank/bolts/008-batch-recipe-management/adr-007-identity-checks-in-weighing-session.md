---
bolt: 008-batch-recipe-management
created: 2026-11-23T03:57:31Z
status: accepted
superseded_by: null
---

# ADR-007: Identity checks are stored in the `weighing` app as part of the WeighingSession; snapshot-only material rules stay in `batches`

## Context

Stories 004-verify-dyestuff-identity and 005-show-lot-and-container belong to unit 004 (Batch & Recipe), which is implemented in the `batches` app (bolt 005). But an identity check only has meaning for **one weighing run** of a batch: it needs the WeighingSession, the current operator and, later, the confirmation that it unblocks. Those live in the `weighing` app (unit 005, bolt 006).

`weighing` already depends on `batches` (`WeighingSession.selection` → `BatchSelection`). If `batches` stored identity checks with a reference to `WeighingSession`, the two apps would depend on each other.

## Decision

1. **`batches/material.py`** holds the rules that need only the recipe snapshot and have no state:
   - `format_tare` (Decimal: `214 g`, `1.850 kg`);
   - `ComponentHeader` and its text;
   - the material faults `LOT_MISSING` and `CONTAINER_MISSING`.
2. **`weighing`** holds the stateful part, as members of the WeighingSession aggregate:
   - the `IdentityCheck` model (FK to `WeighingSession` and `Operator`, append-only);
   - `weighing/identity.py`: `verify_identity`, `identity_status`, `check_material_ready`, `session_components`.
3. **The dependency is one-way:** `weighing` → `batches`, never the reverse.
4. **`check_material_ready(session, sequence)` is the single material gate** for confirmation. Bolt 010's confirm must call it before recording anything.

## Rationale

- The aggregate boundary follows the business: "is this the right dyestuff *for this run*" belongs to the run, not to the recipe, which is OrgaTEX's read-only copy (ADR-003).
- No circular imports between apps; the recipe snapshot app stays free of weighing state.
- Bolt 010 finds every confirmation precondition (operator, material, later tolerance) in one app.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Everything in `batches` (unit 004's app) | Follows the unit split literally | `batches` must reference `WeighingSession`: circular app dependency | Two-way coupling |
| Everything in `weighing` (including header and tare format) | One place | Snapshot formatting and lot/container rules would leave the context that owns the snapshot | Blurs the Batch & Recipe context |
| A new `material` app | Clean name | A third app for a few rules and one table; still needs both other apps | More structure than needed |

## Consequences

### Positive

- Clear placement: snapshot rules in `batches`, run state in `weighing`.
- One function, `check_material_ready`, for bolt 010 to call.

### Negative

- Unit 004's stories are implemented across two apps; the traceability (story → files) must name both. The bolt's test report and walkthroughs list them.

### Risks

- **A later bolt confirms without calling `check_material_ready`.** Mitigation: this ADR, the decision-index "Read when" entry, and bolt 010's tests (confirm refused when unverified, wrong dyestuff, no lot, no container).

## Related

- **Stories**: 004-batch-recipe-management/004-verify-dyestuff-identity, 005-show-lot-and-container; later 005-weighing-station/006-confirm-weighing (bolt 010), 010-resume-after-reload
- **Standards**: coding-standards (layering, business rules in services)
- **Previous ADRs**: ADR-003 (immutable snapshot), ADR-005 (operator from the server session), ADR-006 (server verifies the scan)
