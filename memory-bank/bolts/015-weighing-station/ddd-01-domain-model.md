---
stage: model
bolt: 015-weighing-station
created: 2026-11-23T10:22:15Z
---

## Static Model: weighing-station (batch completion and history)

### Bounded Context

**Weighing Station**, end of a batch. Earlier bolts built the parts this bolt uses:
- **bolt 006:** WeighingSession (`in_progress` / `complete`, `started_at`, `completed_at`), Operator;
- **bolt 010:** ConfirmationService, WeighingRecord (immutable), ComponentAttempt, the derived progress "n of N";
- **bolt 012:** the STEP 24 overshoot rule (no override, so every record's `result` is `within`);
- **bolt 014 (unit 002):** WriteBack (pending / confirmed / not written), its key and body, and the start / verify operations.

This bolt adds two things:
- **Batch completion** (story 009, FR-16, brief §6.2 / FR-25): when the last component is confirmed, the session becomes **complete** and a **BatchSummary** exists: components weighed n of N, all within tolerance YES/NO, total dispensed in kg, elapsed time, operator. Completing **triggers the write-back** to OrgaTEX (FR-17).
- **Batch history** (story 011, FR-19 b/c, brief FR-29 / BR-19 / AC-07): every weighing record of a batch can be read back with target, actual, operator, scale, lot, container, tare and timestamp.

**Owned here:** the completion rule, the BatchSummary, the BatchHistory read.

**Not owned here:**
- posting to OrgaTEX and the write-back status (unit 002, bolt 014: called, not re-implemented);
- the ticket (unit 006, bolt 016), which reads the completed batch;
- View 3 (unit 007, bolt 017), which shows the summary and the write-back status;
- the batch's status in OrgaTEX: brief IR-06 (batch status write-back) is not built (System Context decision), so B-24187 stays in the Dummy queue.

**Training contracts:** the actual weights come from the Dummy Scale; the write-back goes to Dummy OrgaTEX. A-01, A-02 and A-09 stay unresolved.

### Entities

- **WeighingSession** (existing, aggregate root): gains its **completion**:
  - `state` moves `in_progress` → `complete` once, and never back;
  - `completed_at` is set at the same moment (the time the last record was saved), and only then;
  - the **elapsed time** is `completed_at − started_at`.
- **WeighingRecord** (existing): **unchanged**. It already holds every history field: component code and name, target, tolerance min / max, actual weight, unit, lot, container, tare, scale, result, operator, `recorded_at` (UTC).
- **Operator** (existing): unchanged. The summary shows the **session's operator**; each history row shows **its own record's operator** (story 011 AC 2: the operator ID is stored on every record).
- **WriteBack** (unit 002, existing): **created by completion** in status `pending` with 0 attempts. Its first post is then made by the browser (bolt 014 flow), which counts attempt 1.

### Value Objects

- **BatchSummary** (read-only, derived from the session and its records):
  - `weighed` and `total`: "5 of 5";
  - `all_within`: YES when every record's `result` is `within`, otherwise NO. Under the STEP 24 rule every record is `within`, so it is YES; the value is still computed, not assumed;
  - `total_dispensed_kg`: the sum of every actual weight converted to kg (g ÷ 1000), in `Decimal`, rounded half up to 0.001 kg;
    - prototype actuals 1241.5 g + 385.4 g + 94.2 g + 23.980 kg + 9.621 kg = 35.3221 kg → **35.322 kg** (story 009 AC 2);
  - `elapsed`: a duration shown as "6 min 41 s" (the prototype's format); whole seconds, rounded down;
  - `operator`: the session's operator ("R. Karim · Shift A");
  - `completed_at`.
- **ElapsedTime**: whole seconds ≥ 0. Text "M min S s"; minutes are not split into hours (a batch is weighed in minutes); under one minute it is "0 min S s".
- **BatchHistoryEntry**: one WeighingRecord as read back: sequence, component code and name, target, tolerance min / max, actual weight, unit, result, operator (ID, name, shift), scale, lot, container, tare, timestamp.
- **SessionState** (existing enumeration): `in_progress`, `complete`. No new value.

### Aggregates

- **WeighingSession** (root): Members: IdentityCheck*, ComponentAttempt*, WeighingRecord*.

  Invariants added by this bolt:
  1. **Complete only at N of N.** A session becomes complete only when every recipe component has a record. A completion request at 4 of 5 is refused (`BATCH_NOT_COMPLETE`) and changes nothing (story 009 AC 3).
  2. **Completion is part of the last confirmation.** The transaction that saves the N-th record also sets `complete` and `completed_at` (story 009 AC 1: "when the last confirmation is saved"). There is no state where all records exist but the session is still in progress.
  3. **Complete is final.** A complete session accepts no activate, tare, quit, identity or confirm action (the existing `SESSION_NOT_OPEN` refusal), and its records stay immutable.
  4. **A completed session always has a write-back.** The pending WriteBack is created in the same transaction as the completion (story 009 AC 4). A completed batch can therefore never be silently missing from OrgaTEX: its status is pending, confirmed or not written.
  5. **The summary is derived, never stored.** Total, all-within and elapsed are computed from the records and the session times on every read, so they cannot disagree with the records.

- **WriteBack** (unit 002's aggregate): unchanged rules (bolt 014). This bolt only creates it.

### Domain Events

Recorded as log entries (INFO), as in earlier bolts:

- **BatchCompleted**:
  - Trigger: the N-th record is saved.
  - Payload: `session_id`, `batch_id`, `operator_id`, `weighed`, `total`, `total_dispensed_kg`, `elapsed_seconds`, `all_within`.
- **WriteBackTriggered**:
  - Trigger: BatchCompleted.
  - Payload: `batch_id`, `session_id`, `idempotency_key`, status `pending`.
- **BatchHistoryRead** is not logged: it is a plain read.

### Domain Services

- **CompletionService**:
  - `complete(session)`: checks N of N, sets `complete` / `completed_at`, creates the pending WriteBack. Refuses with `BATCH_NOT_COMPLETE` below N of N. Called inside the confirmation transaction for the N-th record; it is not a separate operator action.
  - `summary(session)` → BatchSummary; refused with `BATCH_NOT_COMPLETE` unless the session is complete.
- **ConfirmationService** (existing): after saving a record, if it was the last one, calls `complete` in the same transaction and does **not** start a next attempt (there is no next pending component).
- **BatchHistoryService**: `records(batch_id)` → BatchHistoryEntry*, in recipe sequence. All records of the batch, from every session of it. An unknown batch, or one with no records, gives an empty history.
- **Write-back (unit 002)**: `open_write_back(batch_id, session_id, operator_id)`, a new small operation that creates the pending row with 0 attempts. The existing `start` (bolt 014) then counts the browser's first post as attempt 1.

### Repository Interfaces

- **WeighingSessionRepository** (existing): gains `mark_complete(session, completed_at)`, which writes once and only from `in_progress`.
- **WeighingRecordRepository** (existing): gains `for_batch(batch_id)`: the records of a batch in sequence order, read-only.
- **WriteBackRepository** (unit 002): gains `open(...)`; no other change.

### Ubiquitous Language

- **Batch complete**: every component of the batch's recipe has a confirmed weighing record. The weighing session is then closed.
- **Total dispensed**: the sum of all actual weights of the batch, in kg (prototype "Total dispensed 35.322 kg").
- **All within tolerance**: every confirmed weighing was inside its band (prototype "All within tolerance YES").
- **Elapsed**: the time from opening the batch for weighing (session start) to its completion (prototype "Elapsed 6 min 41 s").
- **Write-back triggered**: a pending write-back exists for the completed batch. The consumption itself is posted by the browser and confirmed by the server (bolt 014).
- **Batch history**: all weighing records of one batch with their traceability fields (brief AC-07). It is not a report: no filtering by date, operator or dyestuff (OQ-2).

### Story Coverage

- **009 AC 1** (5 of 5 → complete with summary): invariants 1–2, CompletionService, BatchSummary.
- **009 AC 2** (35.322 kg in Decimal): BatchSummary `total_dispensed_kg`.
- **009 AC 3** (4 of 5 refused): invariant 1.
- **009 AC 4** (write-back triggered): invariant 4, WriteBackTriggered.
- **011 AC 1** (target, actual, operator, scale, lot, container, tare, timestamp per component): BatchHistoryService, BatchHistoryEntry.
- **011 AC 2** (operator ID on every record): already stored (bolt 010); the history returns it per record.

### Decisions for the Human Checkpoint

1. **When completion happens** - Recommended: **automatically, in the transaction that saves the last record** (story 009 AC 1). A completion request below N of N is refused in the service, and the summary read is refused until complete. Alternative: a separate "Complete batch" action by the operator (an extra step that the prototype does not have).
2. **What "write-back triggered" means** - Recommended: **completion creates the pending WriteBack in the same transaction; the browser then posts it (bolt 014 flow).** A completed batch always shows a write-back status. Alternative: the browser starts the write-back after it sees the completion (if the page closes first, no write-back row exists).
3. **Elapsed time** - Recommended: **session start to completion, shown as "M min S s".** Alternative: from the first tare or first confirmation (excludes the time before weighing started).
4. **History scope** - Recommended: **all records of the batch from all its sessions, in sequence order, as an API only** (OQ-2: no reports). Alternative: only the completed session's records.
