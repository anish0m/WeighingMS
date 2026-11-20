---
stage: design
bolt: 006-weighing-station
created: 2026-11-20T09:16:48Z
---

## Technical Design: weighing-station (foundation: identities and session)

This design is based on the approved domain model (`ddd-01-domain-model.md`, APPROVE MODEL 2026-11-20T09:16:48Z) and its four recommended decisions:
1. own `Operator` / `Supervisor` entities with a hashed PIN;
2. the current operator kept in the server-side Django session;
3. the seed `OP-01` R. Karim · Shift A plus `SUP-01` "Training Supervisor" / PIN `2468`;
4. an existing open session for the batch is returned.

### Architecture Pattern

**Layered Django app with a plain-Python service layer**, as in bolt 005 (coding standards: business rules in service modules, thin views).

- It is a new WeighingMS app, **`weighing`** (unit 005; the name the unit brief suggests). Later unit-005 bolts (009, 010, 012, 015) extend the same app.
- The bolt type's `domain/ application/ infrastructure/ presentation/` tree is not used. Small flat modules map onto the layers, as in bolt 005.
- Layering rules:
  - views → services → models;
  - services never see a request object. The current operator is passed in as a value, read from the session by a thin helper in the view layer;
  - `weighing` imports only `batches.models.BatchSelection` from another WeighingMS app; it has no `dummy_*` imports and no Dummy paths (boundary test).
- **No Dummy API and no adapter** are involved in this bolt.

### Layer Structure

```text
┌──────────────────────────────────────────────────────────────────┐
│ Presentation   weighing/views.py, weighing/urls.py               │  JSON endpoints; session helper
├──────────────────────────────────────────────────────────────────┤
│ Application    weighing/services.py                              │  choose_operator, require_operator,
│                                                                  │  start_session, verify_supervisor
├──────────────────────────────────────────────────────────────────┤
│ Domain         weighing/services.py  RefusalReason, WeighingRefused│ rules, refusals, events (logs)
│                weighing/models.py    invariants                  │
├──────────────────────────────────────────────────────────────────┤
│ Infrastructure weighing/models.py (Django ORM = repositories)    │  SQLite
│                Django session store (current operator)           │
│                migrations/0002_seed_identities.py                │  training seed
└──────────────────────────────────────────────────────────────────┘
```

- **`weighing/models.py`**:
  - `Operator`: managers `active()` and `get(operator_id)` (OperatorRepository).
  - `Supervisor`: `set_pin(pin)` and `check_pin(pin)` via `django.contrib.auth.hashers.make_password` / `check_password`. Only the hasher is used, not the `auth` user model.
  - `SessionState` (TextChoices `in_progress` / `complete`).
  - `WeighingSession`: manager `open_for_batch(batch_id)`. `delete()` is refused (invariant 4).
  - None of these models is registered in the Django admin.
- **`weighing/services.py`**:
  - `RefusalReason` enum. The value is the message; `.code` is the name, as in bolt 005:
    - `OPERATOR_REQUIRED` "Choose an operator first";
    - `OPERATOR_NOT_FOUND` "Operator not found";
    - `SELECTION_NOT_FOUND` "Batch selection not found";
    - `SUPERVISOR_NOT_VERIFIED` "Supervisor ID or PIN incorrect".
  - `WeighingRefused(reason, message)`: the domain exception.
  - `OperatorRef` (frozen dataclass: `operator_id`, `name`, `shift`, with `display` → "R. Karim · Shift A").
  - `list_operators() -> list[OperatorRef]`
  - `find_operator(operator_id) -> OperatorRef`, or raise `OPERATOR_NOT_FOUND`. This is the core of `choose_operator`; the view stores the result in the session and logs OperatorIdentified.
  - `require_operator(operator_id | None) -> OperatorRef`, or raise `OPERATOR_REQUIRED`. It re-reads the operator, so an operator who has been deactivated or removed counts as no operator. Every weighing action calls this first (start now; tare, confirm and override in later bolts).
  - `start_session(selection_id, operator_id | None) -> (WeighingSession, created: bool)`. The domain-model steps run in one `transaction.atomic()`:
    1. `require_operator`;
    2. load the selection, or `SELECTION_NOT_FOUND`;
    3. if an `in_progress` session exists for the batch, return it with `created=False` (Decision 4);
    4. otherwise create the session.
  - `verify_supervisor(supervisor_id, pin) -> SupervisorRef`, or raise `SUPERVISOR_NOT_VERIFIED`. There is no endpoint in this bolt; bolt 012's override calls it.
- **`weighing/views.py`**: four view functions (below). Request validation; the session key `weighing.operator_id`; refusal → HTTP mapping; JSON serialisation. Reuses `weighingms.api` (`json_error`, `read_json_object`, `InvalidJson`) from bolt 005.

### API Design

All endpoints are under **`/station/api/`** (ADR-002), with camelCase JSON. The error shape is `{"error": {"code", "message"}}`; a failure is never returned with `200`.

- **`/station/api/operators`**: `GET`. Response `200`: `{"operators": [Operator JSON, …]}`, the active seeded operators ordered by name. These are the operator-choice list for bolt 007.
- **`/station/api/operator`** (the station's current operator, singular):
  - `GET`: response `200` `{"operator": Operator JSON | null}`. Bolt 007 reads this for the header on every view.
  - `PUT`: request `{"operatorId": "OP-01"}`. Response `200` `{"operator": Operator JSON}`. The operator is stored in the session; it replaces any earlier choice.
  - `DELETE`: response `204`. The operator is cleared from the session; later weighing actions are refused.
- **`/station/api/sessions`**: `POST`. Request `{"selectionId": 1}`. The operator is taken from the server session, never from the body.
  - `201`: Session JSON, newly started.
  - `200`: Session JSON, the batch's already-open session (Decision 4).
- **`/station/api/sessions/<session_id>`**: `GET`. Response `200`: Session JSON; `404 SESSION_NOT_FOUND`.
- Any other method → `405`.

**Operator JSON**: `{"operatorId": "OP-01", "name": "R. Karim", "shift": "A", "display": "R. Karim · Shift A"}`. The header text is "Operator " + `display` (story AC 2). The server gives the `display` string, so the UI builds no name format of its own.

**Session JSON**:

```json
{
  "sessionId": 1,
  "selectionId": 1,
  "batchId": "B-24187",
  "state": "in_progress",
  "operator": {"operatorId": "OP-01", "name": "R. Karim", "shift": "A", "display": "R. Karim · Shift A"},
  "startedAt": "2026-11-20T09:20:00Z",
  "completedAt": null
}
```

**Error responses:**

- `400 INVALID_REQUEST`:
  - the body is not a JSON object;
  - `operatorId` is missing, not a string, blank, or over 16 characters;
  - `selectionId` is missing or not a positive integer (a boolean is rejected).
- `404 OPERATOR_NOT_FOUND`: "Operator not found". Nothing changes; an earlier choice stays.
- `403 OPERATOR_REQUIRED`: "Choose an operator first". A session start with no operator in the session (story AC 3); nothing is stored.
- `404 SELECTION_NOT_FOUND`: "Batch selection not found".
- `404 SESSION_NOT_FOUND`: "Weighing session not found".
- `405`: any other method.

`403` means the request is understood but not allowed until an operator is identified. It is not `401`, because there is no HTTP authentication scheme. A missing CSRF token also gives Django's `403`, but without the JSON `error` body, so the UI can tell the two apart.

### Data Model

The migrations are `weighing/0001_initial` (schema) and `weighing/0002_seed_identities` (data). Timestamps are timezone-aware UTC (data-stack standard).

- **`weighing_operator`**:
  - Columns:
    - `id` (auto PK);
    - `operator_id` (char 16, unique);
    - `name` (char 64);
    - `shift` (char 8);
    - `active` (bool, default true).
  - Ordering: `name`.
- **`weighing_supervisor`**:
  - Columns:
    - `id` (auto PK);
    - `supervisor_id` (char 16, unique);
    - `name` (char 64);
    - `pin_hash` (char 128; Django hasher format, never the plain PIN);
    - `active` (bool).
- **`weighing_weighingsession`**:
  - Columns:
    - `id` (auto PK, which is the `sessionId`);
    - `selection` (FK → `batches.BatchSelection`, `PROTECT`);
    - `batch_id` (char 32, indexed; copied from the selection for the open-session rule);
    - `operator` (FK → `Operator`, `PROTECT`);
    - `state` (char 16, choices, default `in_progress`);
    - `started_at` (default now);
    - `completed_at` (null).
  - Constraint: `UniqueConstraint(fields=("batch_id",), condition=Q(state="in_progress"), name="one_open_session_per_batch")` (invariant 3; SQLite supports partial unique indexes).
  - Relationships: a session belongs to one selection and one operator. Later bolts hang ComponentWeighing, WeighingRecord and Override off the session.
- **Seed (`0002_seed_identities`, `RunPython`)**:
  - `OP-01` / "R. Karim" / shift "A";
  - `SUP-01` / "Training Supervisor" / PIN `2468`, stored only as a hash made with `make_password` at migrate time.
  - The reverse step deletes exactly these two rows.
  - The seed values are training data, marked as such in the migration's docstring (and in the README in a later step).
- The test database is built from the migrations, so the tests see the same seed.

### Security Design

- **Operator identification (OQ-3)**:
  - The operator is chosen without a password, as approved.
  - The current operator lives only in the server-side Django session (signed session cookie, data in the database session store). The client can't set or forge it in a request body: `POST /sessions` ignores any operator in the body.
- **Supervisor verification (NFR-4)**:
  - Supervisors are a separate table from operators; no operator ID can pass supervisor verification.
  - The PIN is hashed with Django's default hasher (PBKDF2) and compared with `check_password`, which runs in constant time.
  - A wrong ID and a wrong PIN produce the same refusal.
  - The PIN never appears in logs, responses or error messages.
- **CSRF**: kept on `PUT` / `DELETE /operator` and `POST /sessions` (no `csrf_exempt`). Bolt 007 sends `X-CSRFToken`.
- **Input validation**: type, length and positive-integer checks at the view boundary, before calling services.
- **Authorization**: the only role check in this bolt is `require_operator` on weighing actions. Supervisor authority is applied by bolt 012.
- **Out of scope (A-09, Q37)**: a real login, a staff directory, lockout after failed PINs.

### NFR Implementation

- **FR-19 (a) / story AC 1, AC 3**: `require_operator` is the single guard, and it runs before any write. A refusal leaves nothing stored.
- **FR-19 (b) groundwork**: the session stores `operator`. Later records copy the acting operator from `require_operator`.
- **NFR-3 (one station)**: one current operator per browser session. A single station browser is the expected setup.
- **NFR-6 (resume) groundwork**: the operator survives a reload (session cookie). An open session is found again through `open_for_batch` and returned by `POST /sessions` (Decision 4).
- **NFR-12 (immutable records)**: sessions can't be deleted (`delete()` refused, the FK is `PROTECT`); identities are seed-only.
- **Performance**: reads of a few rows; not a concern.

### Logging (IR-09, coding standards)

The module logger is `weighing.services`:

- `INFO` "OperatorIdentified": operator ID, name, shift. "OperatorCleared": operator ID.
- `INFO` "WeighingSessionStarted": session ID, batch, selection ID, operator ID. When an existing session is returned, a resumed variant is logged instead.
- `INFO` "WeighingActionRefused": action, reason code, batch if known.
- `WARNING` "SupervisorVerificationFailed": the supervisor ID as typed; never the PIN.

### External Dependencies

- **`batches.models.BatchSelection`** (unit 004, bolt 005): a read by primary key; the FK target. Python, same database.
- **Django sessions** (`django.contrib.sessions` + `SessionMiddleware`): Django's default project setup. The Implement stage verifies both are enabled and enables them if not.
- **`django.contrib.auth.hashers`**: password hashing utilities only.
- **UI (bolt 007)**, the consumer:
  - before view 1, `GET /operator`; if it is `null`, show the operator choice from `GET /operators`, then `PUT /operator`;
  - the header shows "Operator " + `display`;
  - on opening a batch, after the selection's `201`, `POST /sessions`.

### ADR Candidates (Stage 3)

1. **Station identities are own seeded entities, not `django.contrib.auth` users.** The tech-stack standard names `contrib.auth` as the default candidate, so this departure should be recorded.
2. **The current operator is held in the server-side Django session**, and weighing actions read it from there, never from the request body.

### Files (planned for the Implement stage)

- **New**: `src/weighing/__init__.py`, `apps.py`, `models.py`, `services.py`, `views.py`, `urls.py`, `migrations/__init__.py`, `migrations/0001_initial.py`, `migrations/0002_seed_identities.py`.
- **Modified**:
  - `src/weighingms/settings.py`: register `weighing`, and the sessions app and middleware if missing;
  - `src/weighingms/urls.py`: include `weighing.urls` under `station/api/`.
- **New tests (Test stage)**:
  - `tests/weighing/test_identity.py`: seed, list, choose, clear, current operator, display text, supervisor verification and PIN hashing;
  - `tests/weighing/test_session.py`: start refused without an operator, start with an operator, the existing open session, unknown selection, delete refused;
  - `tests/weighing/test_station_api.py`: endpoints, status codes, validation, CSRF, `405`.
  - The architecture boundary tests pick the new app up automatically.
- **Unchanged**: `batches/`, the adapters, the clients, and all `dummy_*` apps.
