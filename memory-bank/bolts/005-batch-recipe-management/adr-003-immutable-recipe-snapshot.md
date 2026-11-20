---
bolt: 005-batch-recipe-management
created: 2026-11-20T08:47:02Z
status: accepted
superseded_by: null
---

# ADR-003: The recipe snapshot is an immutable local cache, enforced in the models

## Context

WeighingMS needs a local copy of the selected batch's recipe: weighing (unit 005) evaluates targets and tolerances against it, weighing records snapshot target and tolerance, and resume after reload (unit 005 story 010) needs it after the page is gone. At the same time:

- **C-01 / BR-04**: recipes are owned by OrgaTEX and read-only at the station; WeighingMS must not become a second source of truth.
- **DR-03**: cached OrgaTEX data is never authoritative.
- **Story 003 AC 2**: no endpoint or UI exists to change a recipe.

"No edit endpoint" alone does not stop a later service, shell session or bug from changing stored recipe rows.

## Decision

1. Each batch selection stores its own **snapshot** of the batch header and recipe components (`BatchSelection`, `SnapshotComponent`), copied from OrgaTEX at selection time.
2. Snapshot rows are **immutable**: the models' `save()` refuses to update an existing row and `delete()` refuses to delete; the FK uses `on_delete=PROTECT`; the models are not registered in Django admin. There is no update or delete endpoint.
3. **Every selection reads OrgaTEX fresh** and creates a new snapshot. An older snapshot is never served as the current recipe; it is only returned for its own selection ID.

## Rationale

- Enforcing immutability at the model layer makes C-01 hold for all code paths, not just the HTTP API, and it is testable with plain Django tests.
- A new snapshot per selection keeps the history consistent with the weighing records that reference it, while never presenting old data as current (DR-03).

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| No local copy; read OrgaTEX on every use | Never stale | Weighing and resume break when OrgaTEX is unavailable; records cannot reference what was weighed against | Fails resume and record-keeping |
| One mutable recipe row per batch, refreshed on reselection | Fewer rows | Earlier weighing records would point at changed data; WeighingMS edits recipe data | Violates C-01 and record integrity |
| Immutability only by convention (no endpoint) | Less code | Any later code path can change rows silently | Not enforceable; not testable |

## Consequences

### Positive

- Recipe data in WeighingMS cannot change after selection, from any code path.
- Weighing records and resume can rely on a stable snapshot.

### Negative

- Reselecting the same batch creates another snapshot (small volume: one station, few batches).
- Correcting bad snapshot data means a new selection, not an edit (consistent with NFR-5/12: corrections are new records).

### Risks

- **Bulk ORM operations (`QuerySet.update()` / `delete()`) bypass `save()` / `delete()`.** Mitigation: no code uses them on these models; a reviewer checks for it; `PROTECT` still blocks deleting a selection that has components.

## Related

- **Stories**: 004-batch-recipe-management/003-load-read-only-recipe; later 005-weighing-station/006-confirm-weighing, 010-resume-after-reload
- **Standards**: none (C-01 and DR-03 already in requirements)
- **Previous ADRs**: ADR-001
