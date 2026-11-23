---
bolt: 010-weighing-station
created: 2026-11-23T05:13:32Z
status: accepted
superseded_by: null
---

# ADR-011: Server-side scale I/O happens before the database transaction; the transaction re-checks the state under a lock before it writes

## Context

The server is the authority for weighing (ADR-001, ADR-008). Confirm re-reads the scale itself (FR-13b, FR-20a), and tare is done by the server through its adapter (bolt 010 Decision 1). Both are HTTP calls to the Dummy Scale (training contract), with a 2 s timeout (IR-13).

The database is SQLite. A write transaction holds the database's single write lock until it commits. A confirmation must be saved in one transaction before the UI advances (NFR-5). Two requests can arrive close together: a double click, or a second tab.

## Decision

Every weighing action that talks to the scale and writes state follows the same three steps:

1. **Check and call outside a transaction.** Validate the operator, the session, the active attempt and the material gate. Then call the scale adapter:
   - `read_weight` for confirm;
   - `tare` for re-tare and the automatic tare.
   A scale failure refuses (`SCALE_DISCONNECTED` / `SCALE_UNAVAILABLE`) before anything is written.
2. **Write in one short transaction**:
   - lock the session row (`select_for_update`);
   - **re-check** that the same attempt is still open and the component has no record, otherwise refuse (`COMPONENT_NOT_ACTIVE` / `COMPONENT_DONE`);
   - then write: the record, the ended attempt, the next attempt.
3. **Follow-up I/O after the commit.** The automatic tare of a newly activated component runs after the commit. Its failure is logged (`TareFailed`) and leaves that attempt untared. It never undoes the commit.

The database unique constraints (one open attempt per session, one record per component per session) are the last guard if two requests still race.

## Rationale

- No HTTP call ever holds the SQLite write lock, so a slow or hanging scale can't block other writes or time out the record.
- The re-check under the lock makes the outcome correct even if the state changed between step 1 and step 2. For example, a double confirm gives one record and one `409 COMPONENT_DONE`.
- The record never depends on a later device call. Once the commit returns, the weighing is durable (NFR-5), whatever happens to the next tare.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Call the scale inside the transaction | One block of code; no re-check needed | Write lock held for up to 2 s per call; a failure after a tare leaves scale and DB out of step | Blocks the station and couples durability to device latency |
| No lock, rely only on the unique constraints | Simplest | Races surface as `IntegrityError` deep in the write; the operator gets an unclear error | The constraints are the last guard, not the main check |
| Do the next component's tare inside the confirm transaction | One request does everything | A tare failure would roll back a valid record, or the record would depend on a device | A valid weighing must never be lost because of the next component |

## Consequences

### Positive

- Confirm is durable and fast at the database level.
- Device failures never corrupt or roll back recorded weighings.
- One pattern for bolts 012 (override / compensation) and 015 (completion and write-back).

### Negative

- The weight read in step 1 may be up to one request old when it is written in step 2. This is acceptable: it is the value the server evaluated, and it is what is recorded (ADR-009).
- Each action has two phases and is a little more code than a single transaction.

### Risks

- **The scale changes between the read and the commit.** Mitigation: the recorded value is the one that was evaluated. The live readout keeps polling, so the operator sees any later change.
- **A follow-up tare fails without the operator noticing.** Mitigation: Progress JSON shows `tared: false`, and confirm refuses with `TARE_REQUIRED` ("Tare the container first (F2)").

## Related

- **Stories**: 005-weighing-station/003-tare-retare-and-quit, 006-confirm-weighing, 008-progress-components; later 007-handle-overshoot (bolt 012), 009-complete-batch (bolt 015)
- **Standards**: coding-standards (fail-safe integrations)
- **Previous ADRs**: ADR-001 (server authority), ADR-008 (server evaluates), ADR-009 (recorded value), ADR-010 (attempts and records)
