---
bolt: 010-weighing-station
created: 2026-11-23T05:13:32Z
status: accepted
superseded_by: null
---

# ADR-010: Weighing attempts are stored append-only; component state is derived from attempts and records

## Context

A weighing session moves through its components one at a time (FR-15). For each component the station must know:
- whether it is pending, active or done;
- which scale it uses;
- whether the container has been tared.

Several things change this state:
- re-tare restarts the attempt (FR-7c);
- quit abandons it without a record (FR-13e);
- touching a pending component switches to it;
- a confirmation records it and makes it done.

The state must survive a reload and a server restart unchanged (NFR-6). Records must be immutable (NFR-12).

Bolt 012 (overshoot, override) and bolt 015 (completion, history) will build on the same state. Abandoned attempts are useful evidence when a weighing is questioned (brief BR-11 traceability).

## Decision

1. Each try at a component is a **`ComponentAttempt`** row: `session`, `component_sequence`, `scale_id` (fixed when it starts), `started_at`, `tared_at`, `ended_at`, `end_reason` (`confirmed` / `quit` / `retared` / `switched`).
2. Attempts are **append-only**:
   - `tared_at` and `ended_at` / `end_reason` are each set at most once;
   - an ended attempt is never reopened, and restarting a component creates a new attempt;
   - no attempt is ever deleted.
3. A database constraint allows **at most one open attempt** (`ended_at` null) per session. The component of that attempt is the *active* one.
4. **Component state is derived, not stored:**
   - `done` = a `WeighingRecord` exists for it (unique per session and component);
   - `active` = it has the open attempt;
   - `pending` = otherwise.
5. A `WeighingRecord` references the attempt that produced it (one-to-one). It is created in the same transaction that ends that attempt as `confirmed`.

## Rationale

- One source of truth: there is no separate state column that could disagree with the records. Resume only has to read rows. Nothing has to be repaired after a crash.
- Quits, re-tares and switches stay visible as ended attempts, so the full history of a component can be explained.
- Fixing the scale on the attempt keeps a confirm on the scale the operator actually used, even if the threshold setting changes meanwhile.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| A mutable `ComponentWeighing` row per component with `state` and `tared` columns | Simple queries; matches the unit brief's first sketch | State can drift from the records; quits and re-tares leave no trace; updates on a weighing table | Weaker traceability and a second source of truth |
| A `state` / `active_sequence` field on `WeighingSession` | Smallest change | Same drift problem; no history; mutable session row on every key press | As above |
| Keep the active component only in the browser | No server state | Lost on reload or on a second tab; the server can't enforce "tared" or "active" | Fails NFR-6 and server authority (ADR-001) |

## Consequences

### Positive

- Resume after a reload or a restart is a pure read (story 010).
- Every attempt and every record is attributable and kept.
- Bolts 012 and 015 can add end reasons or record results without changing how state is derived.

### Negative

- Deriving the state needs two small queries per session (records, open attempt) instead of one column.
- The attempt table grows with every quit, re-tare and switch. It stays small at one station (NFR-3).

### Risks

- **Two open attempts after a race (double click on two components).** Mitigation: the partial unique constraint `one_open_attempt_per_session` makes the second insert fail; the service locks the session row first.
- **A record without a confirmed attempt.** Mitigation: both are written in one transaction; a test checks every record's attempt ended `confirmed`.

## Related

- **Stories**: 005-weighing-station/003-tare-retare-and-quit, 006-confirm-weighing, 008-progress-components, 010-resume-after-reload; later 007-handle-overshoot (bolt 012), 009-complete-batch, 011-retrieve-batch-history (bolt 015)
- **Standards**: coding-standards (business rules in services)
- **Previous ADRs**: ADR-003 (immutable snapshot), ADR-007 (checks as session members), ADR-009 (the recorded value); ADR-011 (how attempts and records are written)
