---
stage: model
bolt: 005-batch-recipe-management
created: 2026-11-20T08:40:29Z
---

## Static Model: batch-recipe-management

### Bounded Context

**Batch & Recipe** decides *which* batch the station weighs and *what it consists of*. It is a downstream, read-only consumer of the OrgaTEX context (C-01, BR-04): batch headers and recipes are owned by OrgaTEX and reach this context only through the OrgaTEX adapter (unit 002), which is the anti-corruption layer. In this training build that adapter reads the **Dummy OrgaTEX training contract**, not the real OrgaTEX interface.

- **Owned here**: the *selection* of a batch at the station, and the read-only *recipe snapshot* taken at selection time (brief DR-03: a cache for resume, never authoritative).
- **Not owned here**: the batch queue itself, the recipe content (OrgaTEX); weighing progress, scale class, tolerance evaluation, confirmation (unit 005); the screens (unit 007); talking HTTP to OrgaTEX or the scanner (units 002, 003).
- **Runtime split (STEP 12 decision)**: the browser shows the queue by calling the Dummy OrgaTEX directly through `orgatex-client.js`. The server is the authority for *selection*: it re-reads the batch and recipe through its own Python adapter and stores the snapshot that later weighing works against.

### Entities

- **BatchSelection** (aggregate root): `selection_id`, `batch` (BatchHeader), `method` (SelectionMethod), `selected_at`, `recipe` (RecipeSnapshot) - Business rules:
  - Created only for a batch that OrgaTEX reports and that is selectable (see `SelectionPolicy`); otherwise no selection exists ("nothing opens", FR-2b/c).
  - Created only together with its complete recipe snapshot; a selection without a recipe never exists (FR-3d: weighing does not start).
  - Immutable after creation: no operation changes its batch header or recipe (C-01).
- **RecipeSnapshot** (entity inside the aggregate): `recipe_name`, ordered `components` - Business rules:
  - Belongs to exactly one BatchSelection; copied from OrgaTEX at selection time.
  - Components are kept in OrgaTEX recipe sequence (1…N, unique, no gaps); the order is never changed (FR-3a).
  - Read-only: no add, remove, reorder or edit operation exists (C-01, story 003 AC 2).
- **SnapshotComponent** (entity inside the aggregate, identity = `sequence` within its recipe): `sequence`, `code` (MaterialCode), `name`, `colour`, `target` (Quantity), `tolerance` (Quantity), `display_max` (Quantity), `lot`, `container`, `tare` (Quantity), `orgatex_state` - Business rules:
  - `target`, `tolerance`, `display_max`, `tare` are `Decimal` quantities in the component's unit (g or kg), never float (NFR-16).
  - `target` > 0; `tolerance` ≥ 0.
  - `orgatex_state` is the state OrgaTEX sent (training seed: `pending`). The live done / weighing / pending state of the recipe rail is weighing progress, owned by unit 005.
  - Lot, container and tare are carried as received; their display and verification are bolt 008 (stories 004, 005).

### Value Objects

- **BatchId**: `value` (e.g. `B-24187`) - Non-empty, trimmed. Equal by value. A scanned batch card and a touched row produce the same BatchId.
- **BatchHeader**: `batch_id`, `order_id`, `machine`, `fabric_lot`, `shade`, `component_count`, `status` - Copy of the OrgaTEX batch at selection time; provides the header line "BATCH … · ORDER … · MACHINE …" (story 002 AC 1).
- **QueueEntry**: same fields as BatchHeader - One row of the batch queue (story 001). Read model only; never stored.
- **BatchQueue**: `received_at`, `entries` (ordered QueueEntry list) - The queue as OrgaTEX released it, with the time it was received ("Queue received from OrgaTEX at hh:mm"). Never stored, so it can never be shown stale (FR-1c).
- **Quantity**: `amount` (Decimal), `unit` (`g` | `kg`) - Decimal only; equality by amount and unit; no conversion in this context (scale selection compares across units in unit 005).
- **MaterialCode**: `value` (e.g. `DYE-4471`, `AUX-0101`) - Identity of a dyestuff/auxiliary; compared by bolt 008's identity check.
- **SelectionMethod**: `scan` | `touch` - How the operator opened the batch (FR-2, BR-02).
- **SelectionRefusal**: `batch_code`, `reason` (RefusalReason), `message` - Returned instead of a selection; carries the text shown to the operator.
- **RefusalReason** (enumeration):
  - `BATCH_NOT_FOUND` → "Batch not found" (FR-2b; OrgaTEX knows no such batch).
  - `RECIPE_NOT_AVAILABLE` → "Recipe not available in training data" (FR-2c, OQ-5; OrgaTEX has the batch but no recipe).
  - `NOT_RELEASED` → "Batch not released" (BR-03, brief FR-03; batch status is not a selectable status. The seed has only `QUEUED`, which is selectable).
  - `ORGATEX_UNAVAILABLE` → "OrgaTEX unavailable" (FR-3d; batch or recipe could not be retrieved, so weighing does not start).

### Aggregates

- **BatchSelection** (root): Members: BatchHeader, RecipeSnapshot, SnapshotComponent* - Invariants:
  1. A BatchSelection always has a RecipeSnapshot with ≥ 1 component.
  2. The header's `batch_id` equals the recipe's batch; a recipe for another batch is rejected (it is treated as OrgaTEX unavailable, as in the adapter).
  3. Component sequences are 1…N, unique and in ascending order.
  4. All quantities are Decimal with a unit.
  5. Nothing in the aggregate changes after creation; there is no update or delete operation.

The batch queue is **not** an aggregate: it is an OrgaTEX read model (BatchQueue value object) that this context never stores.

### Domain Events

Recorded as log entries (no event bus in this build):

- **BatchSelected**: Trigger: a selectable batch was opened and its recipe snapshotted - Payload: `selection_id`, `batch_id`, `method`, `recipe_name`, `component_count`, `selected_at`.
- **BatchSelectionRefused**: Trigger: a scan or touch did not open a batch - Payload: `batch_code`, `method`, `reason`, `at`.

### Domain Services

- **SelectionPolicy**: Operations: `check(header) → ok | RefusalReason` - Dependencies: none (pure rule). Selectable statuses: `{QUEUED}` (OrgaTEX "released for this station", BR-03).
- **BatchSelectionService**: Operations: `select(batch_code, method) → BatchSelection | SelectionRefusal` - Dependencies: OrgaTEX adapter (`fetch_batch`, `fetch_recipe`), SelectionPolicy, BatchSelectionRepository. Steps:
  1. Read the batch from OrgaTEX. Not found → `BATCH_NOT_FOUND`; unavailable → `ORGATEX_UNAVAILABLE`.
  2. Apply SelectionPolicy. Not selectable → `NOT_RELEASED`.
  3. Read the recipe from OrgaTEX. Not available → `RECIPE_NOT_AVAILABLE` (message from OrgaTEX, OQ-5); unavailable → `ORGATEX_UNAVAILABLE`.
  4. Build the BatchSelection (invariants checked), save it, emit BatchSelected.
  Every selection reads OrgaTEX fresh; an earlier snapshot is never served as the current recipe (DR-03).
- **QueueService**: Operations: `list_queue() → BatchQueue | ORGATEX_UNAVAILABLE` - Dependencies: OrgaTEX adapter (`fetch_queue`). See Decision 1 for whether the server exposes it.

### Repository Interfaces

- **BatchSelectionRepository**: Entity: BatchSelection - Methods:
  - `add(selection)`: stores the selection with its header and recipe snapshot in one transaction.
  - `get(selection_id) → BatchSelection | None`
  - `latest_for_batch(batch_id) → BatchSelection | None`: for later resume (unit 005 story 010) and the weighing session.
  - No `update` or `delete` (invariant 5, C-01).

### Ubiquitous Language

- **Batch**: one dyeing job released by OrgaTEX to the station (e.g. B-24187 / SO-9931 / JET-04 / Teal 4C).
- **Batch queue**: the list of batches OrgaTEX released for this station, with the time it was received.
- **Released / selectable**: a batch whose OrgaTEX status allows weighing (training: `QUEUED`) and that has a recipe.
- **Select (open) a batch**: scan its batch card or touch its queue row; on success the weigh view opens with its recipe.
- **Selection refusal**: the reason a scan/touch did not open a batch; nothing opens.
- **Recipe**: the OrgaTEX formulation of a batch (e.g. "Teal 4C"); read-only at the station.
- **Recipe snapshot**: the station's copy of the recipe taken at selection; a cache for resume and record-keeping, never the source of truth.
- **Component**: one recipe line (dyestuff or auxiliary) with sequence, code, target, unit, tolerance, lot, container, tare.
- **Sequence**: the order OrgaTEX specifies for weighing the components.
- **Training contract**: the Dummy OrgaTEX API shape used in this build; not the real OrgaTEX interface.

### Story Coverage

- **001-view-batch-queue**: BatchQueue / QueueEntry, QueueService, `ORGATEX_UNAVAILABLE` (never empty or stale).
- **002-select-batch**: BatchId, SelectionMethod (scan = touch), SelectionPolicy, BatchSelectionService, refusals `BATCH_NOT_FOUND` / `RECIPE_NOT_AVAILABLE` / `NOT_RELEASED`, BatchHeader for the header line.
- **003-load-read-only-recipe**: RecipeSnapshot / SnapshotComponent in sequence with Decimal Quantities, aggregate invariants (read-only), `ORGATEX_UNAVAILABLE` → weighing does not start.

### Decisions for the Human Checkpoint

1. **Queue on the server (story 001's "WeighingMS queue endpoint")** - Recommended: **no server queue endpoint.** Per the STEP 12 decision the browser reads `GET /api/batches` through `orgatex-client.js` (that is what STEP 19's Network evidence shows). The queue's Django tests (values from the Dummy, unavailable) already exist from bolt 003's adapter tests, and bolt 007 adds the Playwright test. QueueService then exists only as the domain contract. Alternative: add a server queue endpoint that the UI does not use.
2. **Scale class (story 003 AC 1 lists "scale class")** - Recommended: **not in this bolt.** The 3 kg threshold is configurable and owned by unit 005 (bolt 009, story 002-select-scale-automatically); it needs g/kg comparison. The snapshot carries target and unit; bolt 009 derives the scale class and bolt 011 shows it on the recipe rail. Alternative: compute it here with a provisional threshold.
3. **Re-selecting a batch** - Recommended: **every selection reads OrgaTEX fresh and stores a new snapshot**; resuming an interrupted weighing is unit 005 story 010. Alternative: reuse the latest snapshot of the same batch (risks a stale recipe, against DR-03).
