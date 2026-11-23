---
stage: design
bolt: 010-weighing-station
created: 2026-11-23T05:11:30Z
---

## Technical Design: weighing-station (confirmation and progression)

This design is based on the approved domain model (`ddd-01-domain-model.md`, APPROVE MODEL 2026-11-23T05:11:30Z) and its six recommended decisions:
1. the server tares through its scale adapter;
2. quit starts a new, untared attempt;
3. the record's tare is the snapshot container tare;
4. the next component is activated inside the confirm transaction, and tared after the commit;
5. the station resumes the most recently active open session;
6. the record's operator is the station's current operator at confirm.

### Architecture Pattern

**Layered Django app with a plain-Python service layer**, as in bolts 006–009. No new app.

- **Two new service modules in `weighing`:**
  - `progression.py`: attempts, activation, touch, tare, quit, progress, resume;
  - `confirmation.py`: confirm.
- They **call** the existing rules and never copy them:
  - `identity.check_material_ready` (bolt 008, ADR-007);
  - `rules.component_rules` / `tolerance.evaluate` (bolt 009, ADR-008 / ADR-009);
  - `scale_selection.select_scale` (bolt 009).
- **Scale I/O only through `devices.scale`** (bolt 004): `tare(scale_id)` and `read_weight(scale_id) → ScaleReading(net_weight, unit, status, read_at)`, which raise `ScaleDisconnected` / `ScaleUnavailable`. No Dummy path or `dummy_*` import in `weighing` (boundary tests).
- **HTTP calls never run inside a database transaction.** The scale is read or tared first. The transaction then re-checks the state under a lock and writes. A slow scale therefore can't hold the SQLite write lock.

### Layer Structure

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Presentation   weighing/views.py, weighing/urls.py                   │  5 POST + 2 GET endpoints
├──────────────────────────────────────────────────────────────────────┤
│ Application    weighing/progression.py   activate, tare, quit,       │
│                                          progress, current_session   │
│                weighing/confirmation.py  confirm                     │
├──────────────────────────────────────────────────────────────────────┤
│ Domain         weighing/identity.py (bolt 008), weighing/rules.py,   │  unchanged rules
│                weighing/tolerance.py, weighing/scale_selection.py    │
│                (bolt 009); RefusalReason members (services.py)       │
├──────────────────────────────────────────────────────────────────────┤
│ Infrastructure weighing/models.py  ComponentAttempt, WeighingRecord  │  SQLite, migration 0004
│                devices/scale.py    tare, read_weight (existing)      │  Dummy Scale (training contract)
└──────────────────────────────────────────────────────────────────────┘
```

- **`weighing/models.py`** (extended):
  - `AttemptEnd` (TextChoices): `confirmed`, `quit`, `retared`, `switched`.
  - `WeighingResult` (TextChoices): `within`. Bolt 012 adds the override results.
  - `ComponentAttempt` and `WeighingRecord` (see Data Model). They are append-only, with guards like bolt 008's `IdentityCheck`:
    - a `ComponentAttempt` may only set `tared_at` once and `ended_at` / `end_reason` once; every other update and every `delete()` raises `AttemptImmutable`;
    - a `WeighingRecord` refuses any update and `delete()` (`WeighingRecordImmutable`).
- **`weighing/services.py`** (extended): new `RefusalReason` members, with value = message:
  - `NO_ACTIVE_COMPONENT` "Choose a component first";
  - `COMPONENT_NOT_ACTIVE` "This component is not active";
  - `COMPONENT_DONE` "Component already weighed";
  - `TARE_REQUIRED` "Tare the container first (F2)";
  - `SCALE_DISCONNECTED` "Scale disconnected";
  - `SCALE_UNAVAILABLE` "Scale unavailable";
  - `OUT_OF_TOLERANCE` "Weight is not within tolerance";
  - `SESSION_NOT_OPEN` "Weighing session is not in progress".
- **`weighing/progression.py`** (new):
  - `ComponentProgress` (frozen dataclass): `sequence`, `state` (`pending` / `active` / `done`), `record` (or none).
  - `SessionProgress` (frozen dataclass): `session`, `components` (in sequence), `active_attempt` (or none), `next_pending` (or none), `weighed`, `total`, `text` = "n of N components weighed".
  - `progress(session_id) -> SessionProgress`: read-only. States are derived from records and the open attempt.
  - `activate(session_id, sequence, operator_id) -> SessionProgress`. This is first activation and touch in one operation.
    1. Checks, in order: operator; session; session `in_progress`; component exists.
    2. Done → `COMPONENT_DONE`, with no change. Already active → no change, returned as is.
    3. Otherwise, in one transaction (session row locked): end the open attempt as `switched` (if any), then start an attempt with `scale_id = select_scale(...)`.
    4. After the commit: `_auto_tare(attempt)`.
  - `tare(session_id, sequence, operator_id) -> SessionProgress`.
    1. Checks, in order: operator; session open; the component is the active one, otherwise `NO_ACTIVE_COMPONENT` / `COMPONENT_NOT_ACTIVE`.
    2. `devices.scale.tare(attempt.scale_id)`. `ScaleDisconnected` → `SCALE_DISCONNECTED`; `ScaleUnavailable` → `SCALE_UNAVAILABLE`. In both cases nothing changes.
    3. Then, in one transaction: an untared attempt gets `tared_at`. A tared attempt ends `retared`, and a new attempt starts already tared.
  - `quit(session_id, sequence, operator_id) -> SessionProgress`: the same checks. In one transaction, end the attempt as `quit` and start a new, **untared** attempt for the same component. No scale call.
  - `_auto_tare(attempt)`: tries the tare and logs `TareFailed` on failure. It **never raises**: activation has already succeeded.
  - `current_session() -> SessionProgress | None`: the `in_progress` session with the most recent attempt `started_at` (falling back to the session's `started_at`), or none.
  - Logger `weighing.progression`: `ComponentActivated`, `ContainerTared`, `TareFailed`, `AttemptQuit`, `AttemptRetared`, `AttemptSwitched`.
- **`weighing/confirmation.py`** (new):
  - `confirm(session_id, sequence, operator_id) -> (WeighingRecord, SessionProgress)`, in the order of the aggregate's invariant 4:
    1. `require_operator`;
    2. load the session (`SESSION_NOT_FOUND`); `in_progress`, otherwise `SESSION_NOT_OPEN`;
    3. the component: unknown → `COMPONENT_NOT_FOUND`; done → `COMPONENT_DONE`; no open attempt → `NO_ACTIVE_COMPONENT`; another component active → `COMPONENT_NOT_ACTIVE`;
    4. the attempt is tared, otherwise `TARE_REQUIRED`;
    5. `check_material_ready(session, sequence)`;
    6. `read_weight(attempt.scale_id)`: `ScaleDisconnected` → `SCALE_DISCONNECTED`; `ScaleUnavailable` → `SCALE_UNAVAILABLE`;
    7. `evaluate(band, reading.net_weight, reading.unit)`: not within → `OUT_OF_TOLERANCE`, with `evaluation` attached to the refusal;
    8. **one `transaction.atomic()`**, with the session row locked (`select_for_update`):
       - re-check that the same attempt is still open and the component has no record, otherwise `COMPONENT_NOT_ACTIVE` / `COMPONENT_DONE`;
       - create the `WeighingRecord`;
       - end the attempt as `confirmed`;
       - if a component is still pending, start an attempt for the next one in sequence;
    9. after the commit: `_auto_tare` of the new attempt; log `WeighingConfirmed`.
    Every refusal raises `WeighingRefused`, stores nothing, and is logged as `ConfirmationRefused`.
  - `WeighingRefused` gains an optional `detail` (a dict). For `OUT_OF_TOLERANCE` it carries `{"net", "unit", "zone"}`, so the operator sees what the server measured.
  - Logger `weighing.confirmation`.
- **`weighing/views.py` / `urls.py`** (extended): the endpoints below. `REFUSAL_STATUS` gains the new reasons and bolt 008's material reasons, which until now were only reported inside the component JSON.

### API Design

Under **`/station/api/`** (ADR-002), camelCase JSON, error shape `{"error": {"code", "message"}}`. For `OUT_OF_TOLERANCE` the error also has a `detail` object.
- The POST endpoints need the current operator (`403 OPERATOR_REQUIRED`) and the CSRF token. Their body is empty or `{}`; nothing in it is used.
- The GET endpoints are read-only and need no operator.

| Method + path | Purpose | Success |
|---|---|---|
| `GET /station/api/current-session` | Resume (story 010) | `200 {"session": Progress JSON or null}` |
| `GET /station/api/sessions/<id>/progress` | State of one session | `200` Progress JSON |
| `POST /station/api/sessions/<id>/components/<seq>/activate` | First activation and touch (story 008) | `200` Progress JSON |
| `POST /station/api/sessions/<id>/components/<seq>/tare` | F2 Re-tare (story 003) | `200` Progress JSON |
| `POST /station/api/sessions/<id>/components/<seq>/quit` | F4 Quit (story 003) | `200` Progress JSON |
| `POST /station/api/sessions/<id>/components/<seq>/confirm` | F1 OK · Confirm (story 006) | `201 {"record": Record JSON, "progress": Progress JSON}` |

**Errors**:
- `403 OPERATOR_REQUIRED`;
- `404 SESSION_NOT_FOUND`, `404 COMPONENT_NOT_FOUND`;
- `409`: `SESSION_NOT_OPEN`, `NO_ACTIVE_COMPONENT`, `COMPONENT_NOT_ACTIVE`, `COMPONENT_DONE`, `TARE_REQUIRED`, `OUT_OF_TOLERANCE`, `LOT_MISSING`, `CONTAINER_MISSING`, `IDENTITY_NOT_VERIFIED`, `WRONG_DYESTUFF`;
- `503 SCALE_DISCONNECTED`, `503 SCALE_UNAVAILABLE`;
- `405` for other methods.

**Progress JSON**:

```json
{
  "sessionId": 1,
  "batchId": "B-24187",
  "state": "in_progress",
  "weighed": 2,
  "total": 5,
  "progressText": "2 of 5 components weighed",
  "active": {"sequence": 3, "attemptId": 7, "scaleId": "scale-3kg", "tared": true, "startedAt": "2026-11-23T05:20:00Z"},
  "nextPending": 3,
  "components": [
    {"sequence": 1, "state": "done", "actualWeight": "1241.5", "unit": "g", "actualText": "1241.5 g", "recordId": 1},
    {"sequence": 2, "state": "done", "actualWeight": "385.4", "unit": "g", "actualText": "385.4 g", "recordId": 2},
    {"sequence": 3, "state": "active", "actualWeight": null, "unit": "g", "actualText": null, "recordId": null},
    {"sequence": 4, "state": "pending", "actualWeight": null, "unit": "kg", "actualText": null, "recordId": null},
    {"sequence": 5, "state": "pending", "actualWeight": null, "unit": "kg", "actualText": null, "recordId": null}
  ]
}
```

- `active` is `null` when no attempt is open. Before the first activation, `nextPending` is 1 and the UI activates it. When all components are done, `nextPending` is `null`.
- Names, headers, targets and scales stay in `GET …/components` (bolts 008 / 009); Progress JSON does not repeat them.

**Record JSON** (FR-13c):

```json
{
  "recordId": 3,
  "sessionId": 1,
  "batchId": "B-24187",
  "sequence": 3,
  "componentCode": "DYE-4471",
  "componentName": "Remazol Yellow RGB",
  "actualWeight": "94.2",
  "unit": "g",
  "actualText": "94.2 g",
  "lot": "2026-0387",
  "container": "C-12",
  "tare": "214.0000",
  "tareText": "214 g",
  "scaleId": "scale-3kg",
  "target": "94.0000",
  "toleranceMin": "93.5000",
  "toleranceMax": "94.5000",
  "result": "within",
  "operator": {"operatorId": "OP-01", "name": "R. Karim", "shift": "A", "display": "R. Karim · Shift A"},
  "recordedAt": "2026-11-23T05:21:04Z"
}
```

`OUT_OF_TOLERANCE` error example: `{"error": {"code": "OUT_OF_TOLERANCE", "message": "Weight is not within tolerance", "detail": {"net": "94.6", "unit": "g", "zone": "over"}}}`.

### Data Model

Migration `weighing/0004_componentattempt_weighingrecord` (schema only). Decimals are `max_digits=12, decimal_places=4`, as in `SnapshotComponent`. Timestamps are timezone-aware UTC.

- **`weighing_componentattempt`**:
  - Columns:
    - `id`;
    - `session` (FK → WeighingSession, `PROTECT`, `related_name="attempts"`);
    - `component_sequence` (positive small int);
    - `scale_id` (char 16);
    - `started_at` (default now);
    - `tared_at` (null);
    - `ended_at` (null);
    - `end_reason` (char 16, choices, blank).
  - Constraint `one_open_attempt_per_session`: `UniqueConstraint(fields=["session"], condition=Q(ended_at__isnull=True))` (invariant 1).
  - Index: `(session, started_at)` for resume.
- **`weighing_weighingrecord`**:
  - Columns:
    - `id`;
    - `session` (FK, `PROTECT`, `related_name="records"`);
    - `attempt` (OneToOne → ComponentAttempt, `PROTECT`);
    - `batch_id` (char 32);
    - `component_sequence`;
    - `component_code` (char 32), `component_name` (char 100);
    - `actual_weight`, `target`, `tolerance_min`, `tolerance_max`, `tare` (decimals);
    - `unit` (char 2);
    - `lot` (char 32), `container` (char 32);
    - `scale_id` (char 16);
    - `operator` (FK → Operator, `PROTECT`);
    - `result` (char 16, choices);
    - `recorded_at` (default now).
  - Constraint `one_record_per_component_per_session`: `UniqueConstraint(fields=["session", "component_sequence"])` (invariant 2).
- Both tables are not registered in the admin (NFR-12).

### Security Design

- **The weight is never taken from the client.** Confirm has no weight in its body. The server reads the attempt's scale and evaluates it itself (ADR-008, ADR-009, FR-13b).
- **The scale is the attempt's scale**, fixed when the attempt started. The browser can't redirect a confirm to another scale.
- **Attributable:** every record and every logged attempt event carries the current operator from the server session (ADR-005, Decision 6); no operator → `403`, nothing changes.
- **Double confirm** (double click, resend): the second request finds the component done → `409 COMPONENT_DONE`. The unique constraint and the in-transaction re-check stop a race.
- **Immutable records:** model guards, `PROTECT` foreign keys, not in the admin, no update or delete endpoint.
- **CSRF** on every POST. Path IDs come from `<int:…>` converters.
- **Fail safe (FR-20):** a scale failure refuses with `503` and changes nothing. A failed automatic tare leaves the attempt untared, and confirm then asks for F2.

### NFR Implementation

- **NFR-5:**
  - the record, the attempt's end and the next activation are saved in one transaction;
  - the `201` is returned only after the commit, so the UI advances only after the record is durable.
- **NFR-6:** every state lives in SQLite (attempts, records, sessions). `GET /current-session` rebuilds it after a reload or a restart.
- **NFR-12:** append-only models; the record copies its snapshot values, so later recipe changes can't alter it.
- **NFR-16:** all quantities stay `Decimal`; `actualWeight` is the evaluated value (ADR-009).
- **FR-20a:** confirm reads the scale itself, so a disconnected scale is refused even if the browser missed it.

### External Dependencies

- **`devices.scale`** (bolt 004): `tare`, `read_weight`, `ScaleDisconnected`, `ScaleUnavailable`. These reach the **Dummy Scale** training contract.
- **`weighing.identity`** (bolt 008): `load_session`, `load_component`, `check_material_ready`.
- **`weighing.rules` / `tolerance` / `scale_selection`** (bolt 009).
- **`weighing.services`** (bolt 006): `require_operator`, `RefusalReason`, `WeighingRefused`.
- **Consumers:**
  - bolt 011 (UI): F1 / F2 / F4, the rail touch, the "n of 5" counter, resume on page load;
  - bolt 012: overshoot on top of `OUT_OF_TOLERANCE`;
  - bolt 015: completion and history on top of `WeighingRecord`.

### ADR Candidates (Stage 3)

1. **The component attempt is a stored, append-only entity, and component states are derived from attempts and records.** The alternative is a mutable `state` column per component. This shapes resume, audit of quits and re-tares, and bolts 012 / 015.
2. **The server tares and confirms by its own scale I/O, outside the database transaction. The transaction re-checks the state under a lock before it writes** (Decisions 1, 4). This fixes how every later weighing action must be written.

### Files (planned for the Implement stage)

- **New**:
  - `src/weighing/progression.py`;
  - `src/weighing/confirmation.py`;
  - `src/weighing/migrations/0004_componentattempt_weighingrecord.py`.
- **Modified**:
  - `src/weighing/models.py`: `AttemptEnd`, `WeighingResult`, `ComponentAttempt`, `WeighingRecord` and their guards;
  - `src/weighing/services.py`: new `RefusalReason` members, `WeighingRefused.detail`;
  - `src/weighing/views.py`, `src/weighing/urls.py`: the 6 endpoints, the error `detail`, the status mapping.
- **New tests (Test stage)**, run against the live Dummy Scale with its training simulate controls:
  - `tests/weighing/test_progression.py`: first activation is Blue RSPL; the automatic tare zeroes the scale; touch pending / active / done; switched attempts; quit records nothing and leaves the attempt untared; re-tare zeroes the scale and starts a new attempt; a tare on a disconnected scale changes nothing; progress text; resume picks the latest open session and rebuilds the state;
  - `tests/weighing/test_confirmation.py`: the full record at 94.2 g; each refusal stores nothing (the 93.4 g and 94.6 g boundaries, untared, unverified, wrong dyestuff, missing lot, scale disconnected, no operator, not active, done, session not open); double confirm; immutability; all five in order with the scale switch to `scale-32kg` / kg after Yellow RGB, and "5 of 5";
  - `tests/weighing/test_confirmation_api.py`: the 6 endpoints, status codes, `detail` on `OUT_OF_TOLERANCE`, CSRF, `405`, resume through `GET /current-session`.
- **Unchanged**: the adapters, the JS clients, the station UI, `batches`, and all `dummy_*` apps.
