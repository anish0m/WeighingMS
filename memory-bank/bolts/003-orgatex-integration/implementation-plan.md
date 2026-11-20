---
stage: plan
bolt: 003-orgatex-integration
created: 2026-11-20T07:47:39Z
---

## Implementation Plan: orgatex-integration

### Objective

Build the WeighingMS side of OrgaTEX **reads**, as one replaceable module per runtime (STEP 12 decision, IR-07):
- a **browser JS OrgaTEX client**: the only JS file that knows the OrgaTEX paths. Its calls show in the Network tab (STEP 19).
- a **server Python OrgaTEX adapter**: the only Python module that knows them. Later bolts use it to snapshot the selected batch and recipe authoritatively.

Both call the Dummy OrgaTEX **training contract** over HTTP. It is not the real OrgaTEX interface; A-01 and A-02 stay open. Write-back is bolt 014.

### Stories

- **001-read-batches-and-recipe** (unit 002): IR-07, IR-09; supports FR-1, FR-2, FR-3, FR-21b; NFR-7

### 1. What will change?

- **New WeighingMS app `orgatex`**. It is the home of unit 002, and bolt 014 adds the write-back model here. It has no models in this bolt.
- **Python adapter** with three reads that return typed, immutable results:
  - `fetch_queue()` → `Queue(received_at, batches: list[Batch])`
  - `fetch_batch(batch_id)` → `Batch`
  - `fetch_recipe(batch_id)` → `Recipe(batch_id, recipe_name, components: list[RecipeComponent])`
  - Every quantity is `Decimal`, parsed from the JSON string (`targetQty`, `tolerance`, `displayMax`, `tare`). A JSON number (float) is rejected.
- **Two failure results** (exceptions), so callers can fail safe (NFR-7):
  - `OrgatexNotFound(code, message)` for a 404 from the Dummy. It covers both `BATCH_NOT_FOUND` and `RECIPE_NOT_AVAILABLE`, keeping the code so FR-2b and FR-3d can show the reason.
  - `OrgatexUnavailable(reason)` for connection refused, timeout, any 5xx (including `503 ORGATEX_UNAVAILABLE`), or a malformed body.
  - Each failure is logged at `WARNING` with method, URL, HTTP status (or the network error), the error code and the batch ID (IR-09).
- **Configuration** (NFR-13), in settings, overridable by environment variable:
  - `ORGATEX_BASE_URL`, default `http://localhost:8000/api` (the `npm run dev` port);
  - `ORGATEX_TIMEOUT_SECONDS`, default `5`.
- **Browser JS client**: `fetchQueue()`, `fetchBatch(batchId)`, `fetchRecipe(batchId)` call the same-origin `/api/...` paths with `fetch`.
  - On failure they throw an `OrgatexError` with `kind` `not-found` (carrying the Dummy's code and message) or `unavailable`.
  - Quantities stay strings, and JS does no arithmetic on them. Tolerance checks are server-side Decimal rules in later bolts.
  - It is a classic script that exposes `window.WeighingMS.orgatex`, so the Alpine.js views (bolt 007) can use it without module-loading order issues.
- **No HTTP library added.** The adapter uses Python's standard `urllib.request`.

### 2. Which files will be created/modified?

**Created**
- `src/orgatex/__init__.py`, `src/orgatex/apps.py`: app `orgatex` ("OrgaTEX integration")
- `src/orgatex/adapter.py`: the Python adapter, result types and exceptions
- `src/orgatex/static/orgatex/orgatex-client.js`: the browser client
- `tests/orgatex/__init__.py`, `tests/orgatex/test_adapter.py`
- `tests/architecture/__init__.py`, `tests/architecture/test_integration_boundaries.py`

**Modified**
- `src/weighingms/settings.py`: register `orgatex`; add `ORGATEX_BASE_URL` and `ORGATEX_TIMEOUT_SECONDS`

No migrations, no URL changes, no template changes. The JS client is first loaded by the UI in bolt 007.

### 3. Which requirements and stories are being implemented?

| Story AC | Covered by |
|---|---|
| Seeded Dummy → queue, B-24187 and its recipe come back as typed objects with `Decimal` quantities | `fetch_queue`, `fetch_batch`, `fetch_recipe` |
| Unknown batch → NotFound result, not a generic error | `OrgatexNotFound("BATCH_NOT_FOUND")` |
| Dummy unavailable → Unavailable result, failure logged with request details | `OrgatexUnavailable` + WARNING log (IR-09) |

Requirements:
- **IR-07 / FR-21b:** one adapter per runtime, no `dummy_*` imports.
- **IR-09:** failure logging.
- **NFR-7:** a failure is never returned as data.
- **FR-1, FR-2, FR-3:** this provides the data source. Their screens are bolts 005 and 007.

### 4. Which APIs are involved?

These are consumed only; no API is added or changed. All are Dummy OrgaTEX training contracts from bolt 001:
- `GET /api/batches` → `{receivedAt, batches[]}`
- `GET /api/batches/:batchId` → batch; unknown → `404 BATCH_NOT_FOUND`
- `GET /api/batches/:batchId/recipe` → recipe; no recipe → `404 RECIPE_NOT_AVAILABLE`
- Any of them → `503 ORGATEX_UNAVAILABLE` while the Dummy is toggled unavailable

Tests also use the bolt-002 training control `PUT /api/training/modes/orgatex` to toggle the failure.

### 5. How will this be tested?

**`tests/orgatex/test_adapter.py`**
- Uses Django `LiveServerTestCase`: a real HTTP server on a free port with the seeded Dummy, and `ORGATEX_BASE_URL` pointed at it.
- These tests make real HTTP calls with no mocks, as the story asks.

| Case | Expected |
|---|---|
| queue | 4 batches in seed order (B-24187, B-24188, B-24190, B-24191); `received_at` is a datetime; fields typed |
| batch B-24187 | SO-9931, JET-04, Teal 4C, 5 components |
| recipe B-24187 | "Teal 4C"; 5 components in sequence; e.g. Yellow RGB `Decimal("94.0")` ± `Decimal("0.5")` g; Sodium Sulphate `Decimal("24.000")` kg; every quantity is a `Decimal` |
| unknown batch B-99999 | `OrgatexNotFound`, code `BATCH_NOT_FOUND` |
| B-24188 recipe | `OrgatexNotFound`, code `RECIPE_NOT_AVAILABLE` |
| Dummy toggled unavailable | queue, batch and recipe each raise `OrgatexUnavailable`; `assertLogs` WARNING contains the URL, `503` and the batch ID |
| toggled back to `ok` | reads succeed again |
| nothing listening (base URL on a closed port) | `OrgatexUnavailable`, logged |

**Malformed responses** (a unit test with a stubbed `urlopen`; coding standards allow mocks only at the integration boundary):
- a float quantity, missing field or non-JSON body raises `OrgatexUnavailable` and never yields a partial result.

**`tests/architecture/test_integration_boundaries.py`** (static checks, FR-21b / IR-07)
- An AST scan of every Python file in WeighingMS apps under `src/` finds no import of `dummy_*`.
  - The scan covers all apps except the `dummy_*` apps and the `weighingms` project package.
  - `weighingms` is excluded because its `urls.py` mounts the Dummies and `training.py` holds the Dummy training controls. It is project wiring, not domain code.
- Only `orgatex/adapter.py` contains the OrgaTEX paths (`/batches`) among WeighingMS Python files.
- Only `orgatex-client.js` contains `/api/batches` among JS files under `src/`.

**Gate:** `npm test` (the existing 71 tests plus the new ones) and `npm run lint` pass.

**Manual:** with `npm run dev` running, run `fetch_queue()` from a `manage.py shell` one-liner. The browser Network-tab evidence comes after bolt 007 (STEP 19 T315–T322).

### Dependencies

- Bolt 001 (complete): Dummy OrgaTEX endpoints and seed
- Bolt 002 (complete): `/api/training/modes/orgatex` toggle (used by tests only)
- No new packages

### Technical Approach

- **Adapter flow:** build the URL from settings, open it with a timeout, then map the response.
  - 200 → parse into the result types.
  - 404 → `OrgatexNotFound`.
  - Anything else → `OrgatexUnavailable`.
  - `json.loads` is called with `parse_float` set to reject floats. Quantities go through `Decimal(str_value)` with validation.
- **Result types** are frozen dataclasses, so callers cannot mutate a snapshot.
- **The adapter has no state and no database access.** Persisting a snapshot is bolt 005's job.
- **Self-calls work in dev:** `runserver` is threaded, so the server can call its own `/api/` while serving a request.

### Decisions for the user

1. **App name `orgatex`** for unit 002's code. Bolt 014 adds the write-back model to the same app. The alternative is a generic `integrations` app shared with the device adapters (bolt 004). **Recommended: `orgatex`**: one app per unit keeps IR-07's "one replaceable part" literal.
2. **Malformed Dummy response is treated as Unavailable**, not a third error type. The UI then shows "OrgaTEX unavailable", so it fails safe, and the log says "malformed response".

### Acceptance Criteria

- [ ] `fetch_queue`, `fetch_batch`, `fetch_recipe` return typed objects with `Decimal` quantities equal to the seed
- [ ] Unknown batch → `OrgatexNotFound` (`BATCH_NOT_FOUND`); missing recipe → `OrgatexNotFound` (`RECIPE_NOT_AVAILABLE`)
- [ ] Dummy unavailable, unreachable or malformed → `OrgatexUnavailable`, logged at WARNING with URL, status and batch ID
- [ ] Only one Python module and one JS file know the OrgaTEX paths; no WeighingMS app imports `dummy_*`
- [ ] `npm test` and `npm run lint` pass

### Out of scope for this bolt

- Consumption write-back, idempotency key, retry (bolt 014)
- Recipe snapshot model, selection rules, the queue and recipe screens (bolts 005, 007)
- Device adapters and the status bar (bolt 004)
- Playwright setup
