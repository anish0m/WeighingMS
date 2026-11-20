---
stage: plan
bolt: 001-dummy-integrations
created: 2026-11-20T06:02:11Z
---

## Implementation Plan: dummy-integrations

### Objective

Create the project skeleton (approved tech stack) and the **Dummy OrgaTEX** training contract: a seed command that loads the prototype scenario, and the four Dummy OrgaTEX HTTP endpoints. The Dummy is a training contract defined by this project, **not** the real OrgaTEX interface (A-01…A-15 stay unresolved).

### Stories

- **001-seed-training-scenario**: DB-1, DB-2, DB-5, DB-10; OQ-5, OQ-6, OQ-7
- **002-dummy-orgatex-batch-endpoints**: DB-1, DB-10 (supports FR-1, FR-2, FR-21)
- **003-dummy-orgatex-recipe-endpoint**: DB-2, OQ-5 (supports FR-3, FR-5, FR-6, FR-7, FR-10, FR-12)
- **004-dummy-orgatex-consumption-endpoint**: DB-3 (supports FR-17)

### Deliverables

**Project skeleton**
- `requirements.txt`: Django 5.2 (LTS), Ruff
- `package.json`: scripts `dev` (`.venv/bin/python manage.py runserver 8000`), `test` (`.venv/bin/python manage.py test tests`), `lint` (`ruff check` + `ruff format --check`)
- `pyproject.toml`: Ruff config (line length 88, rules default + `I`)
- `manage.py` at the root; adds `src/` to the Python path
- `src/weighingms/`: Django project (`settings.py`, `urls.py`, `wsgi.py`, `asgi.py`, `__init__.py`). SQLite `db.sqlite3`, `USE_TZ = True`, UTC
- `tests/__init__.py`
- `.venv/` created locally with Python 3.12 (git-ignored, not committed)

**Dummy OrgaTEX app** `src/dummy_orgatex/`
- `models.py`: `DummyBatch`, `DummyRecipe`, `DummyRecipeComponent`, `DummyConsumption`. All quantities `DecimalField(max_digits=12, decimal_places=4)`
- `seed_data.py`: the prototype values (queue rows + Teal 4C `components` array), as strings → `Decimal`
- `services.py`: seed/reset, batch queries, recipe lookup, consumption acceptance with idempotency
- `views.py`, `urls.py`: thin JSON views; errors as `{"error": {"code", "message"}}`
- `management/commands/seed_training.py`: `python manage.py seed_training`
- `migrations/0001_initial.py`

**Dummy Scale models only** `src/dummy_scale/`
- `models.py`: `DummyScale` (`scale_id`, capacity, unit, net weight `Decimal`, status), seeded by the same command as `scale-3kg` and `scale-32kg`, status `ready`, net weight 0 (story 001 AC 3)
- `migrations/0001_initial.py`. No endpoints (bolt 002)

**Tests** `tests/dummy_orgatex/`, `tests/dummy_scale/`

### Seed values (copied from `docs/customize-weighing-station.html`, nothing invented)

Queue:
- B-24187 · SO-9931 · JET-04 · 100% CTN knit · 480 kg · Teal 4C · 5
- B-24188 · SO-9931 · JET-07 · 100% CTN knit · 520 kg · Teal 4C · 5
- B-24190 · SO-9944 · JET-02 · CVC fleece · 310 kg · Navy 12 · 7
- B-24191 · SO-9947 · WINCH-01 · Viscose jersey · 190 kg · Rose 08 · 4

Recipe "Teal 4C" for B-24187 only (OQ-5). All 5 components `pending`, no actuals pre-seeded (OQ-6). Lot and container from the seed (OQ-7):

| Seq | Code | Name | Colour | Target | Unit | Tol | Max | Lot | Container | Tare |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | DYE-1180 | Remazol Brill. Blue RSPL | #1f4fa8 | 1240.0 | g | 6.0 | 1600 | 2026-0341 | C-09 | 214 |
| 2 | DYE-2204 | Remazol Red RB | #b8253a | 386.0 | g | 2.0 | 520 | 2026-0298 | C-11 | 214 |
| 3 | DYE-4471 | Remazol Yellow RGB | #d9a520 | 94.0 | g | 0.5 | 125 | 2026-0387 | C-12 | 214 |
| 4 | AUX-0101 | Sodium Sulphate | #c9d2dc | 24.000 | kg | 0.120 | 32 | 2026-0112 | D-03 | 1.850 |
| 5 | AUX-0107 | Soda Ash | #e4eaf0 | 9.600 | kg | 0.048 | 14 | 2026-0155 | D-05 | 1.850 |

Not seeded: the prototype's `scale` label (scale selection is a WeighingMS rule, bolt 009), its `state`/`actual` (OQ-6) and its `id` field.

### API contract (training contract; JSON keys camelCase, quantities as decimal strings)

- `GET /api/batches` → 200 `{"receivedAt": "<ISO now>", "batches": [{batchId, orderId, machine, fabricLot, shade, componentCount, status}]}`
- `GET /api/batches/:batchId` → 200 one batch object; unknown → 404 `BATCH_NOT_FOUND`
- `GET /api/batches/:batchId/recipe` → 200 `{batchId, recipeName, components: [{sequence, code, name, colour, targetQty, unit, tolerance, displayMax, lot, container, tare}]}`; no recipe → 404 `RECIPE_NOT_AVAILABLE` "Recipe not available in training data"; unknown batch → 404 `BATCH_NOT_FOUND`
- `POST /api/batches/:batchId/consumption` body `{idempotencyKey, components: [{code, actualQty, unit}]}`
  - new key → 201 `{batchId, idempotencyKey, acceptedAt, duplicate: false}`
  - same key again → 200 same body with original `acceptedAt`, `duplicate: true`; no second record
  - malformed (missing key, empty list, non-decimal `actualQty`, unknown component code, invalid JSON) → 400 `VALIDATION_ERROR`, nothing stored
  - unknown batch → 404 `BATCH_NOT_FOUND`
- `GET /api/batches/:batchId/consumption` → 200 list of stored consumptions (read-back for tests and STEP 26 evidence; story 004 API dependency)

### Dependencies

- Python 3.12 (`/usr/bin/python3.12`) for `.venv`
- Django 5.2 and Ruff from PyPI (`pip install -r requirements.txt`)
- No other unit; this is the first bolt

### Technical Approach

- Views stay thin and call `services.py`; services raise domain exceptions that views map to HTTP errors.
- Dummy endpoints are `csrf_exempt`: they stand in for an external system that the browser calls directly (STEP 12 decision).
- Seeding runs in one transaction: delete Dummy OrgaTEX and Dummy Scale rows (consumptions included), then recreate them. Running it twice gives the same state with no duplicates.
- `dummy_*` apps import nothing from WeighingMS apps (there are none yet), and WeighingMS will never import them (IR-07).
- `receivedAt` is the server time of the response. It is what the UI later shows as "Queue received from OrgaTEX at hh:mm"; the prototype's 06:12 is not hard-coded.
- Batch `status` is seeded as `QUEUED` for all four. The prototype's "WEIGHING" tag shows the operator's active batch, which is WeighingMS state (bolt 005+), not OrgaTEX data.

### Acceptance Criteria

- [ ] `npm run dev` serves the app at http://localhost:8000
- [ ] `python manage.py seed_training` loads 4 batches, 1 recipe with 5 pending components, 2 scales (`ready`, 0); a second run gives the identical state with no duplicates
- [ ] `GET /api/batches` returns the 4 seeded batches with all fields and `receivedAt`
- [ ] `GET /api/batches/B-24187` returns its details; `GET /api/batches/B-99999` → 404 standard error
- [ ] `GET /api/batches/B-24187/recipe` returns Teal 4C with 5 components in sequence, all quantities as strings equal to the prototype values
- [ ] `GET /api/batches/B-24188/recipe` → 404 `RECIPE_NOT_AVAILABLE`
- [ ] Consumption: accept (201 + `acceptedAt`), duplicate key (200, one record), invalid payload (400, nothing stored)
- [ ] `npm test` passes; `ruff check` and `ruff format --check` pass

### Test Plan

Django test runner (`npm test`), in `tests/`:
- `tests/dummy_orgatex/test_seed.py`: 4 batches with prototype fields; Teal 4C has 5 components with exact `Decimal` values, all pending; only B-24187 has a recipe; re-seed is idempotent
- `tests/dummy_scale/test_seed.py`: `scale-3kg`, `scale-32kg` exist, `ready`, net weight 0
- `tests/dummy_orgatex/test_batches_api.py`: queue 200 with all fields, detail 200, unknown 404 in error format
- `tests/dummy_orgatex/test_recipe_api.py`: values equal the prototype, quantities are JSON strings (not numbers), recipe-not-available 404
- `tests/dummy_orgatex/test_consumption_api.py`: accept 201, duplicate key 200 + single record, each malformed case 400 + nothing stored, unknown batch 404, read-back

Manual: `npm run dev`, then `curl` the endpoints (that evidence is workbook STEP 17/18).

### Out of scope for this bolt

- Dummy Scale/Scanner/Printer endpoints, simulate controls and failure toggles (bolt 002), including "Dummy OrgaTEX unavailable" (DB-4, story 007)
- Any WeighingMS business rule, client, adapter or UI
- Playwright setup (first E2E bolt)
