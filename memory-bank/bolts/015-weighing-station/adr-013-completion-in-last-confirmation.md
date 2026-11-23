---
bolt: 015-weighing-station
created: 2026-11-23T10:35:24Z
status: accepted
superseded_by: null
---

# ADR-013: Batch completion happens in the transaction that saves the last record, together with the pending OrgaTEX write-back; the summary is derived, never stored

## Context

Story 009 requires that the batch completes "when the last confirmation is saved", that it cannot complete at 4 of 5, and that completion triggers the write-back to OrgaTEX (FR-16, FR-17). Bolt 014 built the write-back so that the browser posts to (Dummy) OrgaTEX and the server confirms by reading OrgaTEX back. The browser can close at any moment, though. If nothing on the server marked the write-back as due, a completed batch could be silently missing from OrgaTEX, which story 002/003 forbids.

Constraints:
- ADR-010: records and attempts are append-only;
- ADR-011: no device or OrgaTEX I/O inside a database transaction; re-check under the session lock;
- bolt 014: `WriteBack` belongs to unit 002 (`orgatex`); the dependency runs `weighing` → `orgatex` only.

## Decision

1. **Completion is part of confirming the N-th component.** Inside the existing confirm transaction, with the session row locked, once the new record exists and no component is left without a record:
   - the session moves `in_progress` → `complete`, once and never back;
   - `completed_at` is set to the last record's `recorded_at`.
   There is no separate "complete batch" endpoint or operator action. A completion request below N of N is refused with `BATCH_NOT_COMPLETE` (service level).
2. **The same transaction creates the batch's WriteBack in `pending` with 0 attempts** through `orgatex.write_back.open_write_back`. This is database work only, with no OrgaTEX call. The first browser post (bolt 014 `start`) then counts as attempt 1.
3. **The BatchSummary is derived on every read, never stored:**
   - n of N and all-within YES / NO;
   - total dispensed in kg (`Decimal`, half up to 0.001 kg);
   - elapsed `completed_at − started_at`, as "M min S s";
   - the session's operator.
4. **BatchCompleted and WriteBackTriggered are logged after the commit** (`on_commit`), so a rolled-back completion logs nothing.

## Rationale

- **Story 009 AC 1 is literal:** completion happens when the last confirmation is saved. One transaction means there is never a state with N records but an in-progress session, or a complete session without a write-back.
- **The write-back cannot be lost:** whatever the browser does, a completed batch shows `pending`, `confirmed` or `not written`. It is never absent (FR-17, NFR-7).
- **ADR-011 holds:** the scale re-read stays before the transaction, and `open_write_back` does no I/O.
- **A derived summary cannot disagree with the records** (ADR-010). It is cheap to compute: five records per batch.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| A separate "Complete batch" action (endpoint / key) | Explicit operator step | A step the prototype does not have; N records with an open session in between | Story 009 AC 1: complete when the last confirmation is saved |
| The browser starts the write-back after it sees completion | No cross-unit write in the transaction | A closed page leaves no write-back row; the batch is silently missing from OrgaTEX | Violates FR-17 / story 003 intent |
| Post to OrgaTEX from the server inside the confirm | Write-back in one step | OrgaTEX I/O inside the transaction (ADR-011); the browser-posts architecture (STEP 12) | Rejected by ADR-011 and the STEP 12 decision |
| Store the summary (total, elapsed) on the session | One read | A second copy that can drift from the records; a migration | Derived values are cheap and always consistent |

## Consequences

### Positive

- One atomic step: the last record, the completion and the pending write-back.
- Bolts 016 (ticket) and 017 (View 3) get a simple contract: `complete` is final, and the summary and write-back status are always available.
- No migration: the session's `state` / `completed_at` already exist.

### Negative

- `weighing` writes unit 002's table inside its own transaction (through unit 002's function, not its model).
- A complete session is no longer `current-session`, so a reload after completion lands on the queue. Bolt 017 must reopen View 3 from `GET sessions/<id>/summary` if needed.

### Risks

- **A failure in `open_write_back` would refuse the last confirmation.** Mitigation: the whole transaction rolls back, the scale weight is still there, and the operator confirms again. A test covers the rollback.
- **The same batch is selected again after completion** (B-24187 stays in the Dummy queue because brief IR-06 is not built). Mitigation: a new session gets its own key (`WMS-<batchId>-S<sessionId>`, bolt 014). Refusing a re-weigh is not in any story and is not added.

## Related

- **Stories**: 005-weighing-station/009-complete-batch; 002-orgatex-integration/002-post-consumption-idempotently, 003-write-back-failure-and-retry
- **Requirements**: FR-16, FR-17, NFR-7, NFR-16
- **Standards**: coding-standards (Decimal quantities, fail-safe integrations)
- **Previous ADRs**: ADR-010 (append-only attempts and records), ADR-011 (I/O outside the transaction), ADR-012 (records are always `within`, so all-within is YES)
