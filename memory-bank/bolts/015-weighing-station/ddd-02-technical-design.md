---
stage: design
bolt: 015-weighing-station
created: 2026-11-23T10:24:09Z
---

## Technical Design: weighing-station (batch completion and history)

This design is based on the approved domain model (`ddd-01-domain-model.md`, APPROVE MODEL 2026-11-23T10:24:09Z) and its four recommended decisions:
1. completion happens in the transaction that saves the last record;
2. completion creates the pending WriteBack in that same transaction;
3. elapsed runs from session start to completion, shown as "M min S s";
4. history covers all records of the batch, served as an API only.

### Architecture Pattern

**Same layered Django app and plain-Python service layer as bolts 006–012.**

- **Two new domain / application modules in `weighing`:**
  - `completion.py`: the completion rule, `BatchSummary`, the elapsed text;
  - `history.py`: the batch-history read.
- **Existing code is extended, not copied:** `confirmation.confirm` calls `completion.complete` inside its existing transaction for the N-th record.
- **Unit 002 is called, not re-implemented:** `orgatex.write_back` gains `open_write_back`; the dependency stays `weighing` → `orgatex` (bolt 014, Decision 3).
- **No schema change in `weighing`:** `WeighingSession.state` (`complete`) and `completed_at` already exist (bolt 006). No new migration in `orgatex` either: `attempts` already defaults to 0.

### Layer Structure

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Presentation   weighing/views.py + urls.py                           │
│                confirm JSON + "completion" (last record only)        │
│                GET sessions/<id>/summary            (new)            │
│                GET batch-history/<batch_id>         (new)            │
├──────────────────────────────────────────────────────────────────────┤
│ Application    weighing/confirmation.py  N-th record → complete()    │
│                weighing/completion.py (new)  complete(), summary()   │
│                weighing/history.py (new)     records(batch_id)       │
├──────────────────────────────────────────────────────────────────────┤
│ Domain         completion.py  BatchSummary, total_dispensed_kg,      │  pure, Decimal
│                               elapsed_text                           │
├──────────────────────────────────────────────────────────────────────┤
│ Infrastructure weighing/models.py   WeighingSession (state,          │  no migration
│                                     completed_at), WeighingRecord    │
│                orgatex/write_back.py open_write_back (new)           │
└──────────────────────────────────────────────────────────────────────┘
```

- **`weighing/completion.py`** (new):
  - **`complete(session, now)`**:
    - must be called inside a transaction, with the session row locked (the confirmation's lock, ADR-011);
    - refuses with `BATCH_NOT_COMPLETE` unless every snapshot component has a record;
    - refuses with `SESSION_NOT_OPEN` if the session is not `in_progress`;
    - sets `state = complete` and `completed_at = now` (the new record's `recorded_at`);
    - calls `orgatex.write_back.open_write_back(batch_id, session_id, operator_id)`;
    - logs **BatchCompleted** and **WriteBackTriggered** at INFO after the commit (`transaction.on_commit`), so a rolled-back completion logs nothing.
  - **`BatchSummary`** (frozen dataclass): `session`, `weighed`, `total`, `all_within`, `total_dispensed_kg`, `elapsed_seconds`, `operator` (OperatorRef), `started_at`, `completed_at`; properties `components_text` ("5 of 5"), `all_within_text` ("YES" / "NO"), `total_text` ("35.322 kg"), `elapsed_text` ("6 min 41 s").
  - **`total_dispensed_kg(records)`**: each actual weight is converted to kg (g ÷ 1000, through the existing `tolerance` conversion), summed in `Decimal`, then quantized to 0.001 kg with ROUND_HALF_UP.
  - **`elapsed_text(seconds)`**: "M min S s", with whole seconds rounded down.
  - **`summary(session_id)`** → BatchSummary; `SESSION_NOT_FOUND` if unknown, `BATCH_NOT_COMPLETE` if not complete.
- **`weighing/confirmation.py`** (existing): inside the existing confirm transaction, after the record is created, if no pending component is left → `completion.complete(session, record.recorded_at)`. The automatic activation of the next component (after the commit) already does nothing when no component is pending; this is re-checked in tests.
- **`weighing/history.py`** (new): **`records(batch_id)`** → the batch's `WeighingRecord`s ordered by `component_sequence`, then `recorded_at`, with the operator loaded (`select_related`). Read-only; an empty list for an unknown batch.
- **`orgatex/write_back.py`** (existing, unit 002): new **`open_write_back(batch_id, session_id, operator_id)`**: creates the row in `pending` with 0 attempts if none exists (idempotent), using the existing key rule. It runs inside the caller's transaction; `start` (bolt 014) is unchanged.

### API Design

All under `/station/api/` (ADR-002). JSON keys in camelCase; quantities as decimal strings.

- **`POST sessions/<id>/components/<seq>/confirm`** (existing, 201): unchanged for records 1 to N−1. For the N-th record:
  - `progress.state` is `"complete"`;
  - the response gains **`completion`**: `{summary, writeBack}` (the same shapes as below). For other records, `completion` is absent.
- **`GET sessions/<id>/summary`** (new): 200 `{summary, writeBack}`.
  - `summary`:
    - `sessionId`, `batchId`;
    - `weighed`, `total`, `componentsText` ("5 of 5");
    - `allWithin` (boolean), `allWithinText` ("YES");
    - `totalDispensedKg` ("35.322"), `totalDispensedText` ("35.322 kg");
    - `elapsedSeconds` (401), `elapsedText` ("6 min 41 s");
    - `operator` (the existing operator JSON), `startedAt`, `completedAt` (ISO).
  - `writeBack`: bolt 014's write-back JSON (`status`, `idempotencyKey`, `attempts`, `confirmedAt`, `reason`, `operatorId`).
  - 404 `SESSION_NOT_FOUND`; 409 `BATCH_NOT_COMPLETE` while not complete.
  - Read-only; no operator needed (like `progress`).
- **`GET batch-history/<batch_id>`** (new): 200 `{batchId, records: [...]}`.
  - Each record has the existing record JSON (bolt 010): `recordId`, `sessionId`, `sequence`, `componentCode`, `componentName`, `target`, `toleranceMin`, `toleranceMax`, `actualWeight`, `unit`, `actualText`, `result`, `operator` {`operatorId`, `name`, `shift`, `display`}, `scaleId`, `lot`, `container`, `tare`, `tareText`, `recordedAt`.
  - An unknown batch, or a batch with no records → 200 with an empty list (it is a query, not a resource lookup).
  - The path segment is `batch-history`, not `batches`, so no WeighingMS path contains a Dummy path segment (ADR-002, boundary test).
  - Read-only; no operator needed (brief AC-07: Lab/QA reads it).
- **Bolt 014's write-back endpoints are unchanged.** After completion, `GET sessions/<id>/write-back` returns `pending` with 0 attempts until the browser's first post.
- **`GET current-session`** (existing): unchanged. A complete session is no longer "current", so a reload after completion opens the queue. Showing View 3 again after a reload is bolt 017's concern (it can read `summary`).

### Data Model

- **No migration.**
- **`weighing_weighingsession`**: `state` (`in_progress` → `complete`) and `completed_at` are now written. The existing partial unique constraint `one_open_session_per_batch` applies only to `in_progress`, so a completed session no longer blocks it.
- **`weighing_weighingrecord`**: read-only here. `history` uses the existing `batch_id` column; an index on `(batch_id, component_sequence)` is not needed at training volume.
- **`orgatex_writeback`**: one row is inserted by completion (`pending`, `attempts = 0`).

### Security Design

- **Completion needs an identified operator:** it happens only inside `confirm`, which already requires one (ADR-005). There is no separate completion endpoint, so nothing else can complete a batch.
- **No browser input decides completion:** the server counts the records itself under the session lock.
- **Read endpoints** (`summary`, `batch-history`) expose no secret: training data, operator names and IDs are already shown on the terminal.
- **CSRF:** unchanged. The new endpoints are GET only; other methods → 405.

### NFR Implementation

- **NFR-16 / Decimal:** the total is summed and rounded in `Decimal`, never float; the JSON carries strings.
- **Consistency (FR-13, NFR-4):** the N-th record, the completion and the pending WriteBack are written in one transaction; a failure rolls all three back and refuses the confirmation.
- **ADR-011:** no device or OrgaTEX I/O is added inside the transaction. The confirmation's scale re-read stays before it; `open_write_back` is database only.
- **IR-09 / logging:** BatchCompleted and WriteBackTriggered are logged at INFO with batch, session, operator, total and key.
- **Performance:** five records per batch; all reads are single queries with `select_related`.

### Integration Points

- **Unit 002 (`orgatex.write_back.open_write_back`):** a Python call inside the confirmation transaction; no HTTP.
- **Unit 006 (bolt 016):** will read `completion.summary` and `history.records` for the ticket.
- **Unit 007 (bolt 017):** View 3 reads `completion` from the confirm response, or `GET summary` after a reload, and runs bolt 014's `writeBack`.

### Tests Planned (Test stage)

- **Domain:**
  - prototype actuals → 35.322 kg;
  - g + kg mixing;
  - rounding half up at the 4th decimal;
  - elapsed 401 s → "6 min 41 s", 59 s → "0 min 59 s";
  - all within YES / NO.
- **Completion:**
  - 5th confirm → session complete, `completed_at` = the record's time, a pending WriteBack with 0 attempts, no new attempt started;
  - 4 of 5 → `complete` refused;
  - a complete session refuses activate / tare / quit / confirm;
  - a completion failure rolls back the 5th record.
- **API:**
  - the confirm response has `completion` only for the last record;
  - `summary` 200 / 409 / 404;
  - `batch-history` with all traceability fields and the operator ID, empty for an unknown batch, and a path free of Dummy segments;
  - write-back then works from the pending row (bolt 014 flow, attempt 1).
- **Playwright:** the full run must stay green. View 3 itself is bolt 017.
