---
stage: design
bolt: 005-batch-recipe-management
created: 2026-11-20T08:42:46Z
---

## Technical Design: batch-recipe-management

Based on the approved domain model (`ddd-01-domain-model.md`, APPROVE MODEL 2026-11-20T08:42:11Z) with its three recommended decisions: no server queue endpoint; scale class derived in bolt 009; every selection reads OrgaTEX fresh and stores a new snapshot.

### Architecture Pattern

**Layered Django app with a plain-Python service layer** (coding standards: business rules in service modules, thin views, one adapter per integration). A new WeighingMS app **`batches`** (unit 004, app name suggested by the unit brief).

- The bolt type's suggested `domain/ application/ infrastructure/ presentation/` folder tree is **not** used. The coding standards prescribe flat Django apps with `services.py` and thin views; a few small modules map onto the four layers instead (see below). The layering rules still hold: views → service → (adapter, models); the service never sees HTTP request objects; only the OrgaTEX adapter knows the Dummy paths.
- **Runtime split (STEP 12)**: the browser displays the queue and recipe from the Dummy OrgaTEX through `orgatex-client.js` (the calls the STEP 19 Network evidence shows). The server's select endpoint is the **authority** that decides whether a batch opens: it re-reads batch and recipe through the Python adapter and stores the snapshot that weighing (unit 005) works against.

### Layer Structure

```text
┌──────────────────────────────────────────────────────────────┐
│ Presentation   batches/views.py, batches/urls.py             │  JSON endpoints: parse → service → JSON
├──────────────────────────────────────────────────────────────┤
│ Application    batches/services.py  select_batch(code, method)│  use case, transaction, events (logs)
├──────────────────────────────────────────────────────────────┤
│ Domain         batches/services.py  SelectionPolicy, RefusalReason,
│                SelectionRefused;  batches/models.py invariants │  rules + immutable aggregate
├──────────────────────────────────────────────────────────────┤
│ Infrastructure batches/models.py (Django ORM = repository)   │  SQLite
│                orgatex/adapter.py (existing, unchanged)       │  Dummy OrgaTEX over HTTP
└──────────────────────────────────────────────────────────────┘
```

- **`batches/models.py`**: `BatchSelection`, `SnapshotComponent` (Django models). The ORM manager plays the repository role (`add` = create in a transaction, `get`, `latest_for_batch`); no update/delete.
- **`batches/services.py`**:
  - `RefusalReason` (enum: `BATCH_NOT_FOUND`, `RECIPE_NOT_AVAILABLE`, `NOT_RELEASED`, `ORGATEX_UNAVAILABLE`) with the operator message for each.
  - `SelectionRefused(reason, message, batch_code)` domain exception.
  - `SELECTABLE_STATUSES = frozenset({"QUEUED"})` and `check_selectable(batch) -> RefusalReason | None` (SelectionPolicy).
  - `select_batch(batch_code: str, method: str) -> BatchSelection` (BatchSelectionService): steps 1–4 of the domain model, snapshot written in one `transaction.atomic()`.
- **`batches/views.py`**: `selections` (POST) and `selection_detail` (GET); request validation, exception → HTTP mapping, JSON serialisation.
- **QueueService**: no new code. The existing `orgatex.adapter.fetch_queue()` already is the server-side queue contract (Decision 1); the UI reads the queue in the browser.

### API Design

WeighingMS's own endpoints live under **`/station/api/`**, separate from the Dummy training contracts under `/api/`. This keeps the boundary test's rule intact (only the OrgaTEX adapter and `orgatex-client.js` know `/batches`) and makes it obvious in the Network tab which calls go to the Dummy and which to WeighingMS.

- **`/station/api/selections`**: `POST` - Request: `{"batchId": "B-24187", "method": "touch" | "scan"}` - Response `201`: Selection JSON (below).
- **`/station/api/selections/<selection_id>`**: `GET` - Request: none - Response `200`: Selection JSON; `404 SELECTION_NOT_FOUND`. Serves story 003's "WeighingMS recipe endpoint" and later resume (unit 005 story 010).
- No `PUT`, `PATCH` or `DELETE` on either URL (Django `require_http_methods` → `405`), and no recipe URL at all that accepts a write (C-01, story 003 AC 2).

**Selection JSON** (camelCase keys; quantities as decimal strings with 4 places, never JSON numbers):

```json
{
  "selectionId": 1,
  "method": "touch",
  "selectedAt": "2026-11-20T08:45:00Z",
  "batch": {
    "batchId": "B-24187", "orderId": "SO-9931", "machine": "JET-04",
    "fabricLot": "100% CTN knit · 480 kg", "shade": "Teal 4C",
    "componentCount": 5, "status": "QUEUED"
  },
  "recipe": {
    "recipeName": "Teal 4C",
    "components": [
      {"sequence": 1, "code": "DYE-1180", "name": "Remazol Brill. Blue RSPL",
       "colour": "#1f4fa8", "targetQty": "1240.0000", "unit": "g",
       "tolerance": "6.0000", "displayMax": "1600.0000", "lot": "2026-0341",
       "container": "C-09", "tare": "214.0000", "state": "pending"}
    ]
  }
}
```

(The example shows one component; the response lists all of them in `sequence` order. Values come from the Dummy at request time, never from code.)

**Error responses** (coding standards: `{"error": {"code", "message"}}`, never `200` for a failure):

- **`400 INVALID_REQUEST`**: body not JSON, `batchId` missing/empty/over 32 characters, or `method` not `scan`/`touch`.
- **`404 BATCH_NOT_FOUND`**: "Batch not found" (OrgaTEX has no such batch).
- **`409 RECIPE_NOT_AVAILABLE`**: OrgaTEX's message, "Recipe not available in training data" (OQ-5).
- **`409 NOT_RELEASED`**: "Batch not released" (status not in `SELECTABLE_STATUSES`).
- **`503 ORGATEX_UNAVAILABLE`**: "OrgaTEX unavailable" (down, timeout, malformed response or recipe for another batch).
- **`404 SELECTION_NOT_FOUND`**: GET of an unknown selection ID.
- **`405`**: any other HTTP method.

`409` for the two "exists but cannot be opened" cases separates them from the "unknown" case (`404`), so the UI can show the reason text from the body in all cases.

### Data Model

Migration `batches/0001_initial`. Quantities `DecimalField(max_digits=12, decimal_places=4)`, timestamps timezone-aware UTC (data-stack standard).

- **`batches_batchselection`**: Columns:
  - `id` (auto PK = `selectionId`)
  - `batch_id` (char 32, indexed), `order_id` (char 32), `machine` (char 32), `fabric_lot` (char 100), `shade` (char 64), `component_count` (positive small int), `batch_status` (char 32)
  - `method` (char 5, choices `scan` / `touch`)
  - `recipe_name` (char 64)
  - `selected_at` (datetime, default now)
  - Relationships: has many `SnapshotComponent`. Ordering by `-selected_at` for `latest_for_batch`.
- **`batches_snapshotcomponent`**: Columns:
  - `id` (auto PK), `selection` (FK → BatchSelection, `on_delete=PROTECT`, `related_name="components"`)
  - `sequence` (positive small int), `code` (char 32), `name` (char 100), `colour` (char 16)
  - `target_qty`, `tolerance`, `display_max`, `tare` (decimal 12,4), `unit` (char 2, choices `g` / `kg`)
  - `lot` (char 32), `container` (char 32), `orgatex_state` (char 16)
  - Relationships: belongs to one BatchSelection. `UniqueConstraint(selection, sequence)`; default ordering `sequence`.

**Immutability (aggregate invariant 5)** is enforced in the models, not only by the absence of endpoints: `save()` refuses to update an existing row and `delete()` refuses to delete, both raising a domain error. The models are not registered in Django admin.

Recipe name lives on `BatchSelection` (1 : 1), so no separate recipe table is needed.

### Security Design

- **Authentication**: none in this bolt. Operator identification is bolt 006 (unit 005 story 001); the selection will be linked to the weighing session there. Local single-station training app (tech stack).
- **Authorization**: not applicable yet; there are no roles before bolt 006.
- **CSRF**: the POST endpoint keeps Django's CSRF protection (no `csrf_exempt`). The UI (bolt 007) sends the token from the page in the `X-CSRFToken` header.
- **Input validation**: at the view boundary (type, length, choices) before calling the service; the batch code is passed to OrgaTEX only through the adapter, which URL-encodes it.
- **Data encryption**: not applicable (local SQLite, no secrets, no personal data in this unit).
- **Read-only recipe (C-01)**: no write path to recipes anywhere; snapshot rows immutable as above.

### NFR Implementation

- **NFR-2 (recipe shown ≤ 3 s after selection)**: one select call = two local adapter reads (`fetch_batch`, `fetch_recipe`) + one transaction of 1 + N inserts (N = 5). Verified by a Django timing test on the seeded Dummy (≤ 3 s). If OrgaTEX is slow, the adapter timeout ends in `503 ORGATEX_UNAVAILABLE`, never in a late or partial success.
- **NFR-7 / fail-safe**: every adapter failure maps to a refusal; a selection row is written only after both reads succeeded and the invariants hold; the write is atomic, so a failure leaves nothing behind ("nothing opens").
- **NFR-16 (Decimal)**: values come from the adapter already as `Decimal`, are stored in `DecimalField`, and are serialised as strings.
- **DR-03 (cache never authoritative)**: every selection reads OrgaTEX fresh (Decision 3); a stored snapshot is only returned by the GET for that same selection.
- **Scalability**: not a concern (one station, A-11).

### Logging (IR-09, coding standards)

Module logger `batches.services`:

- `INFO` "BatchSelected" with selection ID, batch, method, recipe name, component count.
- `INFO` "BatchSelectionRefused" with batch code, method and reason (an expected operator outcome, not an integration fault). The adapter itself already logs OrgaTEX failures at `WARNING` with URL and status.

### External Dependencies

- **OrgaTEX adapter (`orgatex.adapter`, bolt 003)**: `fetch_batch(batch_id)`, `fetch_recipe(batch_id)`; exceptions `OrgatexNotFound(code, message)` and `OrgatexUnavailable(reason)` - Python call; the adapter talks HTTP to the Dummy OrgaTEX training contract. Mapping:
  - `fetch_batch` → `OrgatexNotFound` → `BATCH_NOT_FOUND`
  - `fetch_recipe` → `OrgatexNotFound` → `RECIPE_NOT_AVAILABLE` (message taken from OrgaTEX)
  - either → `OrgatexUnavailable` → `ORGATEX_UNAVAILABLE`
- **Scanner**: not called by the server. The browser's `scanner-client.js` delivers the scanned code; the UI posts it with `method: "scan"` (scan and touch take the same path).
- **UI (bolt 007)**: view 1 renders the queue from `orgatex-client.js`; on touch or scan it posts to `/station/api/selections` and opens view 2 only on `201`; on an error it shows `error.message` and stays on view 1.

### Files (planned for the Implement stage)

- **New**: `src/batches/__init__.py`, `apps.py`, `models.py`, `services.py`, `views.py`, `urls.py`, `migrations/0001_initial.py`
- **Modified**: `src/weighingms/settings.py` (register `batches`), `src/weighingms/urls.py` (include `station/api/`)
- **New tests (Test stage)**: `tests/batches/test_selection_service.py`, `tests/batches/test_selection_api.py`, `tests/batches/test_snapshot_immutability.py`; the architecture boundary test picks the new app up automatically (no `dummy_*` imports, no Dummy paths).
- **Unchanged**: `orgatex/` adapter and client, all `dummy_*` apps.
