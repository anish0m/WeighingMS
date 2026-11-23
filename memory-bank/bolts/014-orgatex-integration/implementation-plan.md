---
stage: plan
bolt: 014-orgatex-integration
created: 2026-11-23T10:09:08Z
---

## Implementation Plan: orgatex-integration (consumption write-back)

### Objective

Post the actual consumption of a fully weighed batch to Dummy OrgaTEX exactly once, and keep a visible write-back status (FR-17, NFR-7, IR-05, IR-08, IR-09):
- the server prepares the payload and the idempotency key, and stores the status;
- the browser sends `POST /api/batches/:batchId/consumption` through its OrgaTEX client and reports back;
- the server shows CONFIRMED only after its own adapter has found the consumption in OrgaTEX;
- a failure is "not written" with a reason, and retry reuses the same key.

The Dummy consumption endpoint (bolt 001/002) is a training contract, not the real OrgaTEX interface (A-01, A-02 stay unresolved).

### Stories in Scope

- **002-post-consumption-idempotently:** one post with per-component actuals and a key derived from the batch (AC 1); a second trigger uses the same key and OrgaTEX still holds one record (AC 2); acceptance → CONFIRMED with the acceptance time (AC 3).
- **003-write-back-failure-and-retry:** OrgaTEX unavailable → "not written" with the reason, never CONFIRMED, records stay (AC 1); retry with the same key → CONFIRMED with time (AC 2); a timeout after the Dummy stored the post → no duplicate on retry (AC 3).

### Deliverables

1. **Write-back state (`orgatex` app, unit 002's entity `WriteBack`):**
   - new model `WriteBack`, one row per weighing session: `batch_id`, `session_id`, `idempotency_key` (unique), `status` (`pending` / `confirmed` / `not_written`), `attempts`, `confirmed_at` (OrgaTEX's `acceptedAt`), `last_error`, `operator_id`, `updated_at`; migration `orgatex/0001`;
   - `session_id` and `operator_id` are plain values, not foreign keys, so `orgatex` does not depend on `weighing` (the dependency stays `weighing` → `orgatex`, like `weighing` → `batches`).
2. **Adapter read `fetch_consumptions(batch_id)`** in `orgatex/adapter.py`: reads `GET /api/batches/:batchId/consumption` and returns typed consumptions (key, accepted time, lines with `Decimal` quantities), or raises `OrgatexNotFound` / `OrgatexUnavailable`. The server never posts; it only reads to verify.
3. **Write-back service `orgatex/write_back.py`:**
   - `idempotency_key(batch_id, session_id)` → `WMS-B-24187-S<session id>` (derived from the batch; the session part keeps a later re-weigh of the same batch from colliding);
   - `consumption_body(key, lines)` → the contract body `{idempotencyKey, components: [{code, actualQty, unit}]}`, quantities as decimal strings;
   - `start(...)`: creates or loads the row, counts the attempt, sets `pending` unless already `confirmed`, and returns the body;
   - `verify(...)`: reads OrgaTEX through the adapter; key found → `confirmed` with OrgaTEX's `acceptedAt`; not found → `not_written` with the browser's reason; read failed → `not_written` with "OrgaTEX unavailable"; a `confirmed` row is never downgraded;
   - INFO log for every start and result, WARNING for "not written" (IR-09).
4. **Station API (`weighing` app, under `/station/api/`, ADR-002), operator required (ADR-005):**
   - `GET  sessions/<id>/write-back` → the status (`not_started` if none), read-only;
   - `POST sessions/<id>/write-back` → start or retry: `{batchId, idempotencyKey, body, status, attempts}`; refused with 409 `BATCH_NOT_COMPLETE` unless every component has a record; the lines come from the stored `WeighingRecord`s (`actual_weight`, `unit`, `component_code`);
   - `POST sessions/<id>/write-back/result` with `{posted: true|false, reason}` → the server verifies (deliverable 3) and returns the status: `{status, confirmedAt, reason, attempts, idempotencyKey}`.
5. **Browser OrgaTEX client:** `orgatex-client.js` gains `postConsumption(batchId, body)`. It returns the Dummy's JSON on 200/201 and throws `OrgatexError('unavailable', …)` on 503, a network error or a malformed answer. No quantity arithmetic.
6. **Browser write-back helper:** `station-client.js` gains `writeBack(sessionId)`: start → (skip the post if already `confirmed`) → `postConsumption` → report `{posted, reason}` → return the server's status. Bolt 017 calls it from View 3; bolt 015 decides when completion happens.

### Dependencies

- **Bolt 001/002 (Dummy OrgaTEX):** the consumption endpoint with idempotency (`201` new / `200` duplicate), `GET` consumptions, the unavailable switch.
- **Bolt 003 (adapter):** `_read`, error mapping and Decimal parsing are reused.
- **Bolts 010–013 (weighing):** `WeighingRecord`, `progression.progress`, `require_operator`.
- No new library.

### Technical Approach

- **The browser is never trusted for CONFIRMED** (same principle as ADR-006 for scans): its report only triggers the server's own read through the adapter. This also covers story 003 AC 3: after a timeout the browser reports "not posted", but the server finds the stored key and shows CONFIRMED; a retry gets the Dummy's `200` duplicate and nothing new is stored.
- **One row per session**, created on the first start; retries update the same row (`attempts` + 1). The key never changes.
- **Records are never touched** by write-back; a failure leaves them as they are (FR-17d).
- **Completion:** in this bolt the precondition is "every component has a record". Bolt 015 adds the batch-completion state and triggers write-back.
- **Boundary rules:** `orgatex` must not import `dummy_orgatex` (existing architecture test); the Dummy paths stay in `adapter.py` and `orgatex-client.js` (IR-07).

### Acceptance Criteria

- [ ] **Story 002 AC 1:** with 5 of 5 records, start returns the key `WMS-B-24187-S<id>` and a body with the five codes, their actual weights as decimal strings and their units; posting it creates one Dummy consumption.
- [ ] **Story 002 AC 2:** a second start returns the same key; posting again gives the Dummy's `200` duplicate; `GET /api/batches/B-24187/consumption` still lists one consumption.
- [ ] **Story 002 AC 3:** reporting after acceptance → `confirmed` with `confirmedAt` = OrgaTEX's `acceptedAt`.
- [ ] **Story 003 AC 1:** Dummy unavailable → the report gives `not_written` with the reason, never `confirmed`; the five `WeighingRecord`s are unchanged.
- [ ] **Story 003 AC 2:** OrgaTEX back → retry uses the same key → `confirmed` with time; `attempts` = 2.
- [ ] **Story 003 AC 3:** the post was stored but the browser reports `posted: false` → the server finds it and shows `confirmed`; a retry creates no second consumption.
- [ ] Start at 4 of 5 → 409 `BATCH_NOT_COMPLETE`; no operator → refused; unknown session → 404.
- [ ] A browser report of `posted: true` that OrgaTEX does not hold → `not_written` (no false CONFIRMED, NFR-7).
- [ ] `orgatex` does not import `dummy_orgatex`; lint clean; `npm test` and `npx playwright test` pass.

### Tests (Test stage)

- **Django:** `tests/orgatex/test_write_back.py` (key, body, status changes, verify paths against a live Dummy), `tests/orgatex/test_adapter.py` (new consumption read), `tests/weighing/test_write_back_api.py` (the three endpoints and every AC above).
- **Playwright:** one small test that runs `writeBack` in the page against the live Dummy (confirmed, then unavailable → not written → retry → confirmed). The View 3 UI and the workbook STEP 26 Network evidence come with bolts 015–017.

### Decisions for the Human Checkpoint

1. **Who decides CONFIRMED** - Recommended: **the server, by reading OrgaTEX through its adapter after the browser's report.** It never trusts a browser claim and handles the timeout case of story 003 AC 3. Alternative: trust the browser's report of the Dummy response (simpler, but a browser could mark an unwritten batch CONFIRMED).
2. **Idempotency key** - Recommended: **`WMS-<batchId>-S<sessionId>`**: derived from the batch, stable across retries, unique per weighing run. Alternative: `WMS-<batchId>` only (a re-weighed batch would be rejected as a duplicate).
3. **Where `WriteBack` lives** - Recommended: **in the `orgatex` app** (unit 002 owns the entity), with plain `session_id` / `operator_id`, and the station endpoints in `weighing`. Alternative: a model in `weighing` with foreign keys (puts unit 002's entity in unit 005).
