---
bolt: 005-batch-recipe-management
created: 2026-11-20T08:47:02Z
status: accepted
superseded_by: null
---

# ADR-002: WeighingMS's own API lives under `/station/api/`, separate from the Dummy contracts under `/api/`

## Context

Bolt 005 adds the first WeighingMS-owned JSON endpoint (select a batch). All existing JSON endpoints are Dummy training contracts under `/api/` (`/api/batches…`, `/api/scales…`, `/api/scanner…`, `/api/printer…`, `/api/tickets`, `/api/training/…`). Later bolts add more WeighingMS endpoints (weighing session, confirm, records, write-back and print results).

The architecture boundary test (bolt 004, `PATH_OWNERS`) asserts that each Dummy path is known by at most one Python adapter and exactly one JS client (IR-07, FR-21). A WeighingMS endpoint such as `/api/batches/<id>/select` would put `/batches` into WeighingMS views and UI code and break that rule. The coding standards fix the path style (lowercase, plural nouns, kebab-case) but not where WeighingMS's own endpoints live.

## Decision

All WeighingMS-owned JSON endpoints are mounted under **`/station/api/`** (first one: `/station/api/selections`). The `/api/` prefix stays reserved for the Dummy training contracts, which stand in for external systems. WeighingMS paths never contain a Dummy path segment (`/batches`, `/scales`, `/scanner`, `/printer`, `/tickets`).

## Rationale

- Keeps the one-adapter-per-integration boundary mechanically checkable: a Dummy path appearing outside its adapter/client is always a violation.
- In the browser's Network tab (workbook evidence) the reviewer can tell at a glance which calls go to the "external" systems (`/api/…`) and which go to WeighingMS (`/station/api/…`).
- Replacing a Dummy with the real system later moves `/api/…` to another host; `/station/api/…` is unaffected.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Nest under the Dummy paths (`/api/batches/<id>/select`) | Short, resource-oriented | Mixes WeighingMS into the external contract; breaks the boundary test; would move with the Dummy | Violates IR-07 / FR-21 boundary |
| Shared `/api/` with different nouns (`/api/selections`) | Short | Same prefix as the external contracts; Network tab ambiguous; a future Dummy noun could collide | Weak separation |
| Per-app prefixes (`/batches/api/…`, `/weighing/api/…`) | Mirrors app names | `/batches/` again collides with the Dummy path segment; several prefixes to remember | Collides; less uniform |

## Consequences

### Positive

- One uniform prefix for every WeighingMS endpoint in bolts 006–016.
- The boundary test keeps working without exceptions.

### Negative

- Slightly longer URLs.
- The selection resource is named `selections`, not `batches`, even though the operator thinks of "opening a batch".

### Risks

- **A later bolt places an endpoint under `/api/`.** Mitigation: this ADR in the decision index; the boundary test fails if the endpoint repeats a Dummy path segment.

## Related

- **Stories**: 004-batch-recipe-management/002-select-batch, 003-load-read-only-recipe; all later WeighingMS endpoints (units 005, 006)
- **Standards**: candidate addition to `coding-standards.md` → Naming Conventions (API URL paths)
- **Previous ADRs**: ADR-001
