---
stage: model
bolt: 010-weighing-station
created: 2026-11-23T05:09:30Z
---

## Static Model: weighing-station (confirmation and progression)

### Bounded Context

**Weighing Station**, confirmation part. Earlier bolts built the parts this bolt puts together:
- bolt 006: the session and the operator;
- bolt 008: the material gate (`check_material_ready`, ADR-007);
- bolt 009: the weighing rules (`evaluate_reading`, ADR-008 / ADR-009).

This bolt turns a weighing session into a **sequence of weighed components**:

- tare, re-tare and quit (FR-7, FR-13e, brief FR-11 / IR-12);
- confirmation with server-side preconditions and an immutable weighing record (FR-13, NFR-5, NFR-12, brief FR-18 / FR-19 / FR-25 / DR-02);
- progression in recipe order, touching a pending component, done components locked (FR-15, brief FR-06);
- resume after a reload or server restart (NFR-6, brief NFR-06);
- every record attributable to an operator (FR-19b).

- **Owned here**:
  - the **ComponentAttempt**: one try at weighing one component, from its tare to its end;
  - the **WeighingRecord**: the immutable result of a confirmation;
  - the **progression rule**: which component is active and which is next;
  - the **station resume rule**: which session the station reopens.
- **Not owned here**:
  - the rules themselves: scale choice, band, zone (bolt 009) and material readiness (bolt 008). This bolt **calls** them and never re-implements them;
  - HTTP to the scale (unit 003 scale adapter: `read_weight`, `tare`, `ScaleDisconnected`, `ScaleUnavailable`);
  - overshoot recovery and supervisor override (OQ-4, STEP 24, bolt 012). An over-tolerance weight is simply refused here;
  - batch completion, write-back, history API (bolt 015) and the ticket (unit 006);
  - the weigh screen, rail, keys F1 / F2 / F4 (unit 007, bolt 011).
- **Training contract:** taring and reading go to the **Dummy Scale** (`POST /api/scales/<id>/tare`, `GET /api/scales/<id>/weight`). It is not a real scale protocol; A-05 stays open.

### Entities

- **ComponentAttempt** (entity, identity `attempt_id`): `session`, `component_sequence`, `scale_id`, `started_at`, `tared_at` (or none), `ended_at` (or none), `end_reason` (AttemptEnd or none).
  - It is **open** while `ended_at` is none. A session has **at most one open attempt**: that component is the *active* one.
  - `scale_id` comes from bolt 009's `select_scale` **when the attempt starts**. A threshold change during an attempt does not move it to another scale.
  - An attempt is **tared** once a tare on its scale succeeded (`tared_at` set). Only a tared attempt can be confirmed.
  - Ending is final: an ended attempt is never reopened. Restarting a component starts a **new** attempt, so quits and re-tares stay traceable.
  - It is never deleted.
- **WeighingRecord** (entity, identity `record_id`): `session`, `batch_id`, `component_sequence`, `component_code`, `component_name`, `actual_weight`, `unit`, `operator`, `lot`, `container`, `tare`, `scale_id`, `target`, `tolerance_min`, `tolerance_max`, `result`, `recorded_at` (UTC), `attempt`.
  - Created only by a successful confirmation, in the same transaction that ends the attempt (NFR-5).
  - `actual_weight` is the **evaluated** net from bolt 009, at display resolution and in the component's unit (ADR-009). It is not the raw reading and not a value from the browser.
  - `lot`, `container`, `tare`, `target`, `tolerance_min` / `max`, `component_code` / `name` are **copied** from the recipe snapshot at confirmation (FR-10c, FR-12, FR-6b).
  - `result` = `within` in this bolt. Bolt 012 adds results for an approved override.
  - **Immutable** (NFR-12): never updated or deleted through the app. A correction is a new record (bolt 012 decides when one may exist).
  - At most **one record per component per session**: a done component cannot be confirmed again.
- **WeighingSession** (existing root, bolt 006): unchanged fields. Its components' states are **derived**, not stored (see ComponentState).

### Value Objects

- **ComponentState** (derived per session component):
  - `done`: a WeighingRecord exists for it;
  - `active`: it has the open attempt;
  - `pending`: neither.
- **AttemptEnd** (enumeration): `confirmed` | `quit` | `retared` | `switched` (another pending component was touched).
- **Progress**: `weighed` (number of records), `total` (number of components), text "n of N components weighed" (FR-15b).
- **ScaleRef**: `scale_id` (`scale-3kg` | `scale-32kg`) and its label, from bolt 009.
- **ConfirmRefusal** (RefusalReason members), each with the message shown to the operator:
  - `NO_ACTIVE_COMPONENT` → "Choose a component first". The session has no open attempt.
  - `COMPONENT_NOT_ACTIVE` → "This component is not active". Confirm or tare was asked for another component.
  - `COMPONENT_DONE` → "Component already weighed". The component is done; nothing changes (FR-15c).
  - `TARE_REQUIRED` → "Tare the container first (F2)". The open attempt is not tared.
  - `SCALE_DISCONNECTED` → "Scale disconnected". The server's re-read or tare failed because the scale is disconnected (FR-20a).
  - `SCALE_UNAVAILABLE` → "Scale unavailable". Any other scale failure; never treated as a reading.
  - `OUT_OF_TOLERANCE` → "Weight is not within tolerance". The server's evaluation is under, near or over (FR-13b).
  - `SESSION_NOT_OPEN` → "Weighing session is not in progress".
  - Reused: `OPERATOR_REQUIRED` (bolt 006); `SESSION_NOT_FOUND`, `COMPONENT_NOT_FOUND`, `LOT_MISSING`, `CONTAINER_MISSING`, `IDENTITY_NOT_VERIFIED`, `WRONG_DYESTUFF` (bolt 008).

### Aggregates

- **WeighingSession** (root): Members: IdentityCheck* (bolt 008), ComponentAttempt*, WeighingRecord*. Invariants added by this bolt:
  1. At most one open attempt per session.
  2. At most one WeighingRecord per component per session; a done component never gets a new attempt.
  3. A record exists only with a matching attempt that ended `confirmed` in the same transaction.
  4. Confirmation needs, **checked on the server in this order**:
     1. an operator;
     2. the session `in_progress`;
     3. the component active, not done;
     4. the attempt tared;
     5. the material ready (lot, container, identity: bolt 008);
     6. the scale re-read succeeds on the attempt's scale;
     7. the evaluation is within tolerance (bolt 009).
     Any failure refuses and stores nothing.
  5. Records and attempts are append-only (attempts only gain `tared_at` / `ended_at`, once each).

### Domain Events

Recorded as log entries (logger `weighing.confirmation`):

- **ComponentActivated**: Trigger: an attempt starts (session start, next after confirm, touch, quit / re-tare restart) - Payload: `session_id`, `sequence`, `scale_id`, `operator_id`.
- **ContainerTared**: Trigger: a tare succeeded - Payload: `session_id`, `sequence`, `scale_id`, `attempt_id`.
- **TareFailed**: Trigger: a tare could not be done (scale disconnected / unavailable) - Payload: `session_id`, `sequence`, `scale_id`, `reason`.
- **AttemptQuit** / **AttemptRetared** / **AttemptSwitched**: Trigger: an attempt ends without a record - Payload: `session_id`, `sequence`, `attempt_id`, `operator_id`.
- **WeighingConfirmed**: Trigger: a record is saved - Payload: `record_id`, `session_id`, `batch_id`, `sequence`, `actual_weight`, `unit`, `scale_id`, `operator_id`.
- **ConfirmationRefused**: Trigger: any precondition fails - Payload: `session_id`, `sequence`, `reason`, and for `OUT_OF_TOLERANCE` the evaluated net and zone.

### Domain Services

- **ProgressionService**: Operations:
  - `activate_first(session)`: when a session has no attempt and no record, start an attempt for the **first pending component in sequence** (Blue RSPL);
  - `touch(session, sequence)`:
    - pending → end the open attempt as `switched` (no record) and start one for this component;
    - active → nothing;
    - done → refuse `COMPONENT_DONE`, nothing changes (FR-15c);
  - `next_after(session)`: the first pending component in sequence, or none when all are done.
  Dependencies: `select_scale` (bolt 009), TareService, repositories.
- **TareService**: Operations: `tare(session, sequence)`. Requires an operator and the component active. Tares the attempt's scale through the scale adapter.
  - On success: an untared attempt gets `tared_at`. A tared attempt ends as `retared` and a new, tared attempt starts ("re-tare restarts the attempt", story 003 AC 2).
  - On failure: `SCALE_DISCONNECTED` / `SCALE_UNAVAILABLE`, and the attempt is unchanged.
  - Dependencies: scale adapter `tare`.
- **QuitService**: Operations: `quit(session, sequence)`. Requires an operator and the component active. Ends the attempt as `quit`, records nothing, and starts a new, **untared** attempt for the same component (Decision 2). Dependencies: none external.
- **ConfirmationService**: Operations: `confirm(session, sequence) → WeighingRecord + next active | ConfirmRefusal`.
  - Checks invariant 4 in order:
    - material: `check_material_ready`;
    - scale: `read_weight(attempt.scale_id)`;
    - tolerance: `evaluate_reading`.
  - Then, in **one transaction**: save the record, end the attempt as `confirmed`, start the next pending component's attempt (untared).
  - **After the commit**, it tries the automatic tare of the new attempt (Decision 4). A failed tare leaves it untared and visible; the record is already safe.
  - Dependencies: scale adapter, bolt 008 gate, bolt 009 rules, repositories.
- **StationResume**: Operations: `current(station) → session state | none`. Returns the **most recently active `in_progress` session** with its components (states), the active attempt (sequence, scale, tared), progress and records (Decision 5). Everything comes from the database, so a reload and a server restart give the same answer (story 010 AC 1–2).

### Repository Interfaces

- **ComponentAttemptRepository**: Entity: ComponentAttempt - Methods: `start(session, sequence, scale_id)`, `open_for(session)`, `mark_tared(attempt)`, `end(attempt, reason)`, `all_for(session)`. No delete.
- **WeighingRecordRepository**: Entity: WeighingRecord - Methods: `add(record)`, `for_session(session_id)` in sequence order, `exists(session_id, sequence)`, `count(session_id)`. No update, no delete.
- **WeighingSessionRepository** (existing): `get`, plus `latest_open()` for resume.
- Read-only use of BatchSelectionRepository (snapshot) and IdentityCheckRepository (bolt 008).

### Ubiquitous Language

- **Attempt**: one try at weighing a component: tare, dispense, then confirm, quit, re-tare or switch.
- **Tare (F2, "Re-tare")**: zero the selected scale with the empty container on it, so the reading is the net weight. The first tare of a component happens automatically when it becomes active.
- **Quit (F4)**: abandon the current attempt without recording; the operator empties the container and tares again.
- **Confirm (F1, "OK · Confirm")**: record the evaluated weight as the component's actual weight, then move on.
- **Active / pending / done**: the component being weighed / not yet weighed / recorded and locked.
- **Weighing record**: the immutable, attributable result of one confirmation.
- **Resume**: reopen the station at the session and component that were in progress.

### Story Coverage

- **003-tare-retare-and-quit**:
  - AC 1 (tare 214 g shown, empty container reads 0.0 g): automatic tare on activation; the tare text comes from bolt 008's header.
  - AC 2 (re-tare resets net to 0 and restarts the attempt): TareService on a tared attempt.
  - AC 3 (quit records nothing, the component restarts): QuitService.
  - AC 4 (tare stored on the record): WeighingRecord `tare` (Decision 3).
- **006-confirm-weighing**:
  - AC 1 (all preconditions met → full record, one transaction, before the UI advances): ConfirmationService, WeighingRecord.
  - AC 2 (any precondition not met → rejected on the server, nothing saved): invariant 4, ConfirmRefusal.
  - AC 3 (no edit or delete; corrections are new records): WeighingRecord immutability.
- **008-progress-components**:
  - AC 1 (order Blue RSPL → … → Soda Ash, "n of 5"): `activate_first`, `next_after`, Progress.
  - AC 2 (after Yellow RGB, Sodium Sulphate on the 32 kg floor scale in kg): the new attempt's `scale_id` from bolt 009.
  - AC 3 (touching a done component does nothing): `COMPONENT_DONE`, no change.
  - AC 4 (touching a pending component activates it with scale, units, tolerance and tare): `touch` and the bolt 009 rules.
- **010-resume-after-reload**:
  - AC 1 (reload with 2 of 5 done → same component, both confirmations kept): StationResume.
  - AC 2 (server restart → same state from the database): every state is stored; nothing lives only in memory.

### Decisions for the Human Checkpoint

1. **Who tares the scale** - Recommended: **the server, through its scale adapter** (`POST /station/api/…/tare`). The browser never calls the Dummy's tare directly. That way the server knows that an attempt was tared and can refuse an untared confirm (ADR-001 server authority). Alternative: the browser tares with `scale-client.js` and tells the server afterwards (the server could not check that it happened).
2. **Quit** - Recommended: **end the attempt and start a new, untared one.** The operator empties the container and presses Re-tare (F2) before weighing again; confirm is refused with `TARE_REQUIRED` until then. An automatic tare right after Quit would zero the scale with the discarded material still in the container. Alternative: Quit also tares automatically (fewer key presses, but unsafe if the container is not emptied).
3. **Tare stored on the record** - Recommended: **the container tare from the recipe snapshot** (214 g for C-12, 1.850 kg for D-03): the value shown on screen. The Dummy Scale's tare only zeroes the scale and reports no tare amount. Alternative: read the gross weight before taring and store that (the training contract has no gross reading).
4. **Next component after a confirm** - Recommended: **activate it in the same transaction and try its automatic tare after the commit.** The record never depends on the next tare. If that tare fails, the next component is active but untared, and confirm asks for F2. Alternative: activate the next component only when the browser asks (one more request; the UI decides what comes next).
5. **What the station reopens after a reload or restart** - Recommended: **the most recently active `in_progress` session**, at its open attempt. If none is open, view 1 (batch selection) as today. One station, one batch at a time (NFR-3). Alternative: always view 1, with the operator re-selecting the batch, which then resumes (one more step for the operator).
6. **Operator on the record** - Recommended: **the station's current operator at the moment of confirm** (ADR-005), required. This may differ from the operator who started the session (a shift change), and the record shows who actually confirmed. Alternative: always the session's operator.
