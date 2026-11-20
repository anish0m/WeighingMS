---
stage: model
bolt: 006-weighing-station
created: 2026-11-20T09:02:10Z
---

## Static Model: weighing-station (foundation: identities and session)

### Bounded Context

**Weighing Station** is the weighing domain and the system of record (unit 005). This bolt lays its foundation:

- **who** is weighing: the operator, and the supervisor who will later authorise overrides;
- **what** is being weighed: a WeighingSession for one selected batch.

- **Owned here**:
  - the station's operator and supervisor identities. Per system context, the master is the WeighingMS seed (OQ-3); a real FCI directory (A-09, Q37) is out of scope.
  - the *current operator* of the station;
  - the WeighingSession aggregate (skeleton).
- **Not owned here**:
  - the batch and its recipe snapshot (unit 004, `BatchSelection`, ADR-003): the session refers to it;
  - scale selection, tare, tolerance, confirmation, progression, overshoot, completion, resume (later bolts of this unit: 009, 010, 012, 015);
  - the header and the operator-choice screen (unit 007, bolt 007).
- **No Dummy API is involved.** Identities are WeighingMS data, not an OrgaTEX or device training contract.

### Entities

- **Operator** (identity `operator_id`): `operator_id`, `name`, `shift` (Shift), `active`.
  - Seeded, never created through the app (OQ-3: "chosen from a seeded operator list"). Training seed: **R. Karim · Shift A**, from the prototype header.
  - Chosen without a password (OQ-3).
  - Only `active` operators appear in the list and can be chosen.
  - Display form: "R. Karim · Shift A". The header reads "Operator R. Karim · Shift A" (story AC 2).
- **Supervisor** (identity `supervisor_id`): `supervisor_id`, `name`, `pin` (stored as a one-way hash, never in plain text), `active`.
  - Seeded (OQ-3: "a seeded supervisor's ID + PIN").
  - **Distinct from operators**: an operator identity can never authenticate as a supervisor (NFR-4: "no shared credentials between roles").
  - In this bolt the supervisor exists and can be verified (ID + PIN). The override that uses the verification is bolt 012, after the STEP 24 decision (OQ-4).
- **WeighingSession** (aggregate root, identity `session_id`): `session_id`, `selection` (reference to unit 004's BatchSelection, by id), `batch_id`, `operator` (reference to Operator, by id), `state` (SessionState), `started_at`, `completed_at`.
  - Can only be started by an identified operator. Without one, the start is refused (story AC 1 and AC 3, FR-19a).
  - `operator` is the operator who started it. It is fixed for the session's life, so the session is always attributable (FR-19, brief BR-14).
  - Works against the recipe snapshot of its `selection`, never a fresh OrgaTEX read (DR-03, ADR-003).
  - **Skeleton in this bolt:** components, records, completion and resume are added by bolts 009/010/012/015 as members of this aggregate.

### Value Objects

- **OperatorId** / **SupervisorId**: `value` (e.g. `OP-01`, `SUP-01`). Non-empty, trimmed; equal by value.
- **Shift**: `value` (e.g. `A`). Displayed as "Shift A".
- **OperatorRef**: `operator_id`, `name`, `shift`. The snapshot of "who" that is shown in the header, logged with events and, later, stored on weighing records (FR-19b).
- **SupervisorCredentials**: `supervisor_id`, `pin`. Input only; never stored or logged. The PIN is non-empty digits.
- **SessionState** (enumeration):
  - `in_progress`, the only state in this bolt;
  - `complete`, reached in bolt 015.
- **IdentityRefusal / StartRefusal** (RefusalReason enumeration):
  - `OPERATOR_REQUIRED` → "Choose an operator first". A weighing action was attempted with no operator identified (story AC 3).
  - `OPERATOR_NOT_FOUND` → "Operator not found". The chosen ID is not an active seeded operator.
  - `SELECTION_NOT_FOUND` → "Batch selection not found". The session refers to no stored selection.
  - `SUPERVISOR_NOT_VERIFIED` → "Supervisor ID or PIN incorrect". A single message, so it doesn't reveal which of the two was wrong.

### Aggregates

- **StationOperator** (the station's current operator; one station, NFR-3): Members: OperatorRef or none.
  - Invariants:
    1. It holds only an active seeded operator.
    2. Choosing replaces the current operator.
    3. Clearing leaves the station with no operator, so weighing actions are refused.
  - Where it lives (browser session vs. database) is Decision 2.
- **WeighingSession** (root): Members, in this bolt: none beyond its own fields. Later bolts add ComponentWeighing*, WeighingRecord* and Override*.
  - Invariants:
    1. It always has an operator and a selection.
    2. `operator` and `selection` never change after start.
    3. At most one `in_progress` session per batch (Decision 4).
    4. A session is never deleted (records attach to it; NFR-12).
- **Operator** and **Supervisor** are each their own small aggregate (reference data).

### Domain Events

Recorded as log entries, as in bolt 005 (no event bus):

- **OperatorIdentified**: Trigger: an operator was chosen at the station. Payload: `operator_id`, `name`, `shift`, `at`.
- **OperatorCleared**: Trigger: the station's operator was cleared. Payload: `operator_id`, `at`.
- **WeighingSessionStarted**: Trigger: a session was started for a selected batch. Payload: `session_id`, `batch_id`, `selection_id`, `operator_id`, `started_at`.
- **WeighingActionRefused**: Trigger: a weighing action was refused (this bolt: start without an operator). Payload: `action`, `reason`, `batch_id` if known, `at`.
- **SupervisorVerificationFailed**: Trigger: a wrong supervisor ID or PIN. Payload: `supervisor_id` as typed, `at`. The PIN is never logged.

### Domain Services

- **OperatorDirectory**: Operations:
  - `list_operators()`: the active seeded operators, ordered by name;
  - `get(operator_id)`.
  - Dependencies: OperatorRepository.
- **StationIdentityService**: Operations:
  - `choose_operator(operator_id)`: OperatorRef or `OPERATOR_NOT_FOUND`;
  - `current_operator()`: OperatorRef or none;
  - `clear_operator()`;
  - `require_operator()`: OperatorRef or `OPERATOR_REQUIRED`. This is the guard every weighing action (start now, and tare/confirm/override later) calls first.
- **SupervisorVerifier**: Operations: `verify(SupervisorCredentials)`: SupervisorRef or `SUPERVISOR_NOT_VERIFIED`. It compares the PIN against the stored hash. Dependencies: SupervisorRepository.
- **WeighingSessionService**: Operations: `start(selection_id)`: WeighingSession or a refusal. Dependencies: StationIdentityService, the unit 004 selection lookup, WeighingSessionRepository. Steps:
  1. `require_operator()`. With no operator → `OPERATOR_REQUIRED`, and nothing is stored.
  2. Load the selection. Missing → `SELECTION_NOT_FOUND`.
  3. Apply the one-open-session-per-batch rule (Decision 4).
  4. Create the session (`in_progress`, operator, `started_at`), store it and emit WeighingSessionStarted.

### Repository Interfaces

- **OperatorRepository**: Entity: Operator. Methods: `active()`, `get(operator_id)`. Read-only in the app; the seed is the only writer.
- **SupervisorRepository**: Entity: Supervisor. Methods: `get_active(supervisor_id)`. Read-only in the app.
- **WeighingSessionRepository**: Entity: WeighingSession. Methods:
  - `add(session)`;
  - `get(session_id)`;
  - `open_for_batch(batch_id)`: the session or none.
  - No `delete`. State changes (`complete`) come only through later bolts' domain operations.

### Ubiquitous Language

- **Operator**: the person weighing at the station; chosen from the seeded list, no password (OQ-3).
- **Shift**: the operator's shift, shown with the name ("R. Karim · Shift A").
- **Current operator**: the operator the station is working for right now; shown in the header on every view.
- **Identify / choose operator**: picking oneself from the list before weighing.
- **Supervisor**: the privileged person who authorises an override with ID + PIN + reason. The override itself comes after STEP 24.
- **Weighing session**: the weighing of one selected batch by one operator, from start to completion.
- **Weighing action**: anything that changes weighing state (start, tare, confirm, override). Every one requires an identified operator.
- **Seed**: training identities shipped with the app; not a real staff directory (A-09).

### Story Coverage

- **001-identify-operator**:
  - **AC 1** (operator must be chosen before any batch can be weighed): OperatorDirectory, StationIdentityService, and `WeighingSessionService.start` guarded by `require_operator`.
  - **AC 2** (header reads "Operator R. Karim · Shift A"): OperatorRef display form, and `current_operator()` for every view. Rendering is bolt 007, with the Playwright test.
  - **AC 3** (weighing action without an operator is refused): `OPERATOR_REQUIRED` from `require_operator`, logged as WeighingActionRefused.
- **Bolt expected outcome** (supervisor ID + PIN): Supervisor and SupervisorVerifier. The override is bolt 012.

### Decisions for the Human Checkpoint

1. **Identity model** - Recommended: **own `Operator` and `Supervisor` entities** in the `weighing` app, seeded by a data migration, with the supervisor PIN hashed by Django's password hasher.
   - This matches OQ-3: the operator has no password, and the supervisor uses an ID + PIN, not a login.
   - It keeps the roles separate (NFR-4).
   - Alternative: `django.contrib.auth` users and groups (the tech-stack's "default candidate"). That brings a login, passwords and an admin model the requirements don't ask for.
2. **Where the current operator lives** - Recommended: **the server-side Django session** (the station browser's session cookie).
   - The choice survives a reload, which story 010 needs.
   - Every view can read it for the header.
   - The server, the authority, checks it on every weighing action.
   - Alternative: a single database row "station operator" (one station, NFR-3). It has the same effect, but it is shared by every browser that opens the app.
3. **Seed identities** - Recommended:
   - operator **`OP-01` R. Karim · Shift A**, the only operator: the prototype names no one else, and none is invented;
   - one supervisor, **`SUP-01` "Training Supervisor", PIN `2468`**. These are training values the prototype doesn't give; they will be documented as training data in the seed and the README.
   - Alternative: add a second operator so the "choose from a list" step has a real choice. That person would be invented.
4. **Starting a session for a batch that already has one open** - Recommended: **return the existing open session** instead of creating a second one. This keeps invariant 3, and story 010 builds resume on it.
   - Alternative: refuse with "Batch already in progress". That needs a separate resume path.
