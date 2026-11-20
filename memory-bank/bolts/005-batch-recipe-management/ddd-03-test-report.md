---
stage: test
bolt: 005-batch-recipe-management
created: 2026-11-20T08:54:23Z
---

## Test Report: batch-recipe-management

### Summary

- **Unit Tests**: 22/22 passed
  - selection policy (2), recipe invariants (8), snapshot immutability (7), stubbed-adapter rules (3), API `NOT_RELEASED` (1), CSRF (1)
- **Integration Tests**: 30/30 passed. They run the service and the API over real HTTP against a `LiveServerTestCase` with the seeded Dummy OrgaTEX training contract.
- **Security Tests**: covered by the counts above (CSRF, input validation, no write path). There is no separate security suite.
- **Performance Tests**: 1/1 passed (selection to recipe in < 3 s).
- **Full suite**: `npm test` reports **175/175 passed**: 52 new tests plus the 123 from bolts 001–004, which still pass.
- **Lint gate**: `npm run lint` passes (`ruff check`, `ruff format --check`); `makemigrations --check` finds no changes.
- **Coverage**: not measured. The coding standards set no percentage target ("every approved acceptance criterion must have at least one automated test"), so the template's "> 80 %" item does not apply. Every acceptance criterion is mapped below.

### Test Files

- [x] `tests/batches/test_selection_service.py` - 28 tests for `select_batch` and the domain rules.
  - **Select (3):**
    - touch opens B-24187 with SO-9931 / JET-04 / Teal 4C / QUEUED;
    - scan opens the same batch with 5 components;
    - `BatchSelected` is logged.
  - **Recipe snapshot (6):**
    - Teal 4C, with the 5 components in prototype order and sequence 1–5;
    - Yellow RGB is `Decimal` 94.0 g ± 0.5 (display max 125.0);
    - Soda Ash is 9.6 kg ± 0.048;
    - lot, container and tare are kept;
    - each selection stores a new snapshot, and `latest_for_batch` returns the newest;
    - an unselected batch → `None`.
  - **Refusals (6):** for each one nothing is stored.
    - B-99999 → "Batch not found";
    - B-24188 → "Recipe not available in training data", and the same for B-24190 and B-24191;
    - OrgaTEX unavailable or unreachable → "OrgaTEX unavailable";
    - `BatchSelectionRefused` is logged with the reason.
  - **Stubbed adapter (3),** for cases the seed can't produce:
    - status `WEIGHED` → "Batch not released", and the recipe is never read;
    - a recipe with a sequence gap is treated as unavailable, with a WARNING log;
    - a batch gone by the time its recipe is read → not found.
  - **Pure rules (10):**
    - only `QUEUED` is selectable;
    - the recipe invariants: empty recipe, sequence gap, out-of-order sequences, unknown unit, zero target and negative tolerance are rejected; a zero tolerance is allowed.
- [x] `tests/batches/test_selection_api.py` - 17 tests for `/station/api/selections` (ADR-002).
  - **Success (6):**
    - touch and scan → `201`;
    - the full header;
    - Yellow RGB's full component JSON (`"94.0000"`, `"0.5000"`, …);
    - every quantity is a string, never a JSON number;
    - ≤ 3 s;
    - the `batchId` is trimmed.
  - **Refusals (4):** `404 BATCH_NOT_FOUND`, `409 RECIPE_NOT_AVAILABLE`, `503 ORGATEX_UNAVAILABLE`, `409 NOT_RELEASED`.
  - **Validation (1 test, 8 sub-cases)** → `400 INVALID_REQUEST`, nothing stored: not JSON, an array, `batchId` missing / blank / a number / 33 characters, `method` missing / unknown.
  - **Detail (3):**
    - GET returns exactly the POST body;
    - the stored snapshot is still served while OrgaTEX is down;
    - an unknown ID → `404 SELECTION_NOT_FOUND`.
  - **No edit path (2):**
    - `PUT` / `PATCH` / `POST` / `DELETE` on a selection → `405`, and the recipe name is unchanged;
    - the collection accepts only `POST`.
  - **CSRF (1):** a POST without a token → `403`, nothing stored.
- [x] `tests/batches/test_snapshot_immutability.py` - 7 tests for ADR-003.
  - Saving a changed selection or component → `SnapshotImmutable`, and the database is unchanged.
  - `delete()` on either model → `SnapshotImmutable`.
  - A bulk delete of a selection with components → `ProtectedError`.
  - A duplicate sequence → `IntegrityError`.
  - New rows can still be created.
- [x] `tests/batches/factories.py` - Builders for adapter results (`Batch`, `RecipeComponent`, `Recipe`), used only where the adapter is stubbed.
- The architecture boundary tests (unchanged) now also scan `batches`: no `dummy_*` imports, and no Dummy path in the new app.

### Acceptance Criteria Validation

**001-view-batch-queue** (no server queue endpoint, per the approved Decision 1)
- ✅ **Seeded queue returns B-24187, B-24188, B-24190, B-24191 with all fields and the received time**:
  - bolt 003's adapter tests (`fetch_queue`), against the same Dummy;
  - the browser rows are covered by Playwright in bolt 007.
- ✅ **OrgaTEX unavailable → "OrgaTEX unavailable", not an empty or stale list**:
  - bolt 003's adapter unavailable tests;
  - the queue is never stored (domain model), so it can't be stale;
  - the screen message is Playwright in bolt 007.

**002-select-batch**
- ✅ **B-24187 scanned or touched → opens with batch, order and machine**: `test_touching_b24187_opens_it_with_its_header`, `test_scanning_opens_the_same_batch`, `test_touch_b24187_returns_201_with_header`, `test_scan_b24187_returns_201`
- ✅ **Unknown code → "Batch not found", nothing opens**: `test_unknown_batch_is_not_found_and_nothing_opens`, `test_unknown_batch_is_404_batch_not_found`
- ✅ **B-24188 → "Recipe not available in training data", nothing opens**: `test_batch_without_training_recipe_is_not_selectable`, `test_every_queued_batch_without_recipe_is_refused`, `test_batch_without_recipe_is_409_with_reason`
- ✅ **Not released → reason shown** (BR-03): `test_batch_that_is_not_released_is_refused_before_the_recipe`, `test_batch_not_released_is_409`

**003-load-read-only-recipe**
- ✅ **B-24187 → "Teal 4C" with 5 components in order, with code, target, unit, tolerance and state, within 3 s**: `test_recipe_is_teal_4c_with_five_components_in_sequence`, `test_recipe_components_in_sequence_with_all_fields`, `test_quantities_are_decimals_with_prototype_values`, `test_recipe_is_available_within_3_seconds`
  - **Scale class**, part of this criterion, is derived in bolt 009 (approved Decision 2), which owns the configurable 3 kg threshold. The snapshot supplies its inputs: target and unit.
- ✅ **No endpoint or UI to change the recipe**: `NoEditPathTests` (2), `SnapshotImmutabilityTests` (7)
- ✅ **Recipe can't be retrieved → weighing doesn't start, reason shown**: `test_orgatex_unavailable_means_weighing_does_not_start`, `test_unreachable_orgatex_is_unavailable`, `test_orgatex_unavailable_is_503`

**ADRs**
- ✅ **ADR-001** (the server decides; nothing opens on a refusal): every refusal test asserts that nothing is stored.
- ✅ **ADR-002** (`/station/api/`): all API tests use it; the boundary tests stay green.
- ✅ **ADR-003** (immutable snapshot): `SnapshotImmutabilityTests`, `NoEditPathTests`, `test_each_selection_stores_a_new_snapshot`

### Performance

- **NFR-2: selection → recipe shown:** target ≤ 3 s. Actual: 0.08 s locally (Implement-stage smoke test); the test asserts < 3 s. ✅

### Issues Found

- None in the application code.
- Ruff re-wrapped long lines and applied FURB157 (`Decimal(214)` instead of `Decimal("214")` for whole numbers) in the new test files.

### Recommendations

- **Bolt 007** (UI): post selections with the page's CSRF token in `X-CSRFToken`; show `error.message` on view 1 for every refusal.
- **Bolt 009:** add the scale class from the snapshot's target and unit, closing story 003's "scale class" detail.
- The test output contains expected log lines from the deliberate failure cases ("Not Found", "Conflict", "Service Unavailable", OrgaTEX WARNINGs). They are not failures.
