---
stage: test
bolt: 006-weighing-station
created: 2026-11-20T09:27:17Z
---

## Test Report: weighing-station (foundation: identities and session)

### Summary

- **Domain / service tests**: 32/32 passed.
  - 19 for identities: seed, operator list, choose, `require_operator`, supervisor verification.
  - 13 for sessions: start, one open session per batch, integrity.
  - They run against the migrated test database, so the seed comes from `0002_seed_identities` and is not duplicated in the tests.
- **API tests**: 20/20 passed, through the Django test client, which keeps the session cookie the way the station browser does. They cover the operator list, choose / current / clear, session start and detail, validation, `405`, and CSRF.
- **Security tests**: included in the counts above:
  - CSRF on `PUT /operator` and `POST /sessions`;
  - an operator in the request body is ignored;
  - the PIN is stored only as a hash and never logged;
  - one refusal for every supervisor mismatch;
  - no shared credentials between roles.
- **Performance**: no NFR target applies to this bolt; the 52 tests run in about 2 s.
- **Full suite**: `npm test` reports **227/227 passed**: 52 new tests, plus the 175 from bolts 001–005, which all still pass with the sessions app and middleware enabled.
- **Lint gate**: `npm run lint` passes (`ruff check`, `ruff format --check`); `makemigrations --check` finds no changes.
- **Coverage**: not measured. The coding standards ask for at least one automated test per approved acceptance criterion and set no percentage; the mapping is below.
- **No Dummy API is involved.** The tests create the stored `BatchSelection` row directly (`tests/weighing/factories.py`), because weighing works against the stored selection, never OrgaTEX (ADR-003).

### Test Files

- [x] `tests/weighing/test_identity.py` - 19 tests.
  - **Seed (3):**
    - R. Karim · Shift A (OP-01) is seeded and active;
    - SUP-01 "Training Supervisor" is seeded with a `pbkdf2_sha256` hash that doesn't contain "2468";
    - operator and supervisor IDs are separate.
  - **List (3):** R. Karim only; inactive operators are hidden; ordered by name.
  - **Choose (4):**
    - the display is "R. Karim · Shift A";
    - unknown, inactive and supervisor IDs → `OPERATOR_NOT_FOUND`.
  - **`require_operator` (4):**
    - an identified operator passes;
    - `None` or `""` → `OPERATOR_REQUIRED` "Choose an operator first";
    - an operator who is no longer active counts as none;
    - the refusal is logged with the action.
  - **Supervisor (5):**
    - the correct ID + PIN verifies;
    - a wrong PIN, an empty PIN, an unknown ID and an operator's ID → the same `SUPERVISOR_NOT_VERIFIED` "Supervisor ID or PIN incorrect";
    - an inactive supervisor is refused;
    - the PIN is not in the WARNING log;
    - `set_pin` stores only a hash.
- [x] `tests/weighing/test_session.py` - 13 tests.
  - **Start (5):**
    - without an operator → refused, nothing stored;
    - with OP-01 → the session holds the operator, the selection and B-24187, `in_progress`;
    - `WeighingSessionStarted` is logged;
    - an unknown selection → `SELECTION_NOT_FOUND`;
    - the operator is checked before the selection.
  - **One open session per batch (6):**
    - starting again returns the same session (`created=False`);
    - a newer selection of the same batch returns the open session;
    - the returned session keeps its original operator;
    - another batch gets its own session;
    - the database's partial unique index rejects a second open session;
    - a completed session doesn't block a new one.
  - **Integrity (2):** `delete()` → `SessionNotDeletable`; an operator with a session can't be deleted (`ProtectedError`).
- [x] `tests/weighing/test_station_api.py` - 20 tests.
  - **Operator (8):**
    - `GET operators` → `[R. Karim]`;
    - the station starts with `null`;
    - after choosing, the header text is "Operator R. Karim · Shift A";
    - the choice persists across requests;
    - it belongs to one browser session (a second client sees `null`);
    - an unknown operator → `404` and the earlier choice is kept;
    - `DELETE` → `204` and then `null`;
    - 6 invalid bodies → `400`.
  - **Session (9):**
    - no operator → **`403 OPERATOR_REQUIRED`**, nothing stored;
    - after clearing → `403`;
    - with an operator → `201` and the full Session JSON;
    - an `operatorId` in the body is ignored (still `403`);
    - a repeat start → `200` with the same body;
    - an unknown selection → `404`;
    - `None`, `"1"`, `0`, `-1`, `1.5` and `true` → `400`, nothing stored;
    - `GET` returns exactly the `POST` body;
    - an unknown session → `404`.
  - **Methods (1):** all methods that aren't allowed → `405`, on all four URLs.
  - **CSRF (2):** a `PUT /operator` or `POST /sessions` without a token → `403`, nothing changed.
- [x] `tests/weighing/factories.py` - `selection(batch_id)`: a stored BatchSelection row.
- The architecture boundary tests (unchanged) now also scan `weighing`: no `dummy_*` imports, no Dummy path.

### Acceptance Criteria Validation

**001-identify-operator**
- ✅ **AC 1: seeded operators exist (R. Karim · Shift A); the operator must be chosen before any batch can be weighed.**
  - `test_r_karim_shift_a_is_seeded`, `test_operator_list_holds_r_karim`, `test_station_starts_without_an_operator`
  - `test_session_cannot_start_without_an_operator`, `test_weighing_without_an_operator_is_refused`
- ✅ **AC 2: R. Karim chosen → the header reads "Operator R. Karim · Shift A".**
  - `test_choosing_r_karim_gives_the_header_text`, `test_header_text_is_name_and_shift`, `test_operator_stays_chosen_across_requests`
  - The header shown on screen is bolt 007 (story 007/001), with the Playwright test the story lists.
- ✅ **AC 3: no operator identified → a weighing action is refused.**
  - `RequireOperatorTests` (4)
  - `test_weighing_without_an_operator_is_refused`, `test_weighing_after_clearing_the_operator_is_refused`, `test_operator_in_the_body_is_ignored`
  - Later actions (tare, confirm, override) reuse the same guard in bolts 010 and 012.

**Bolt expected outcome**
- ✅ **Seeded supervisor (ID + PIN):** `SupervisorVerificationTests` (5), `test_training_supervisor_is_seeded_with_a_hashed_pin`. The override that uses it is bolt 012, after STEP 24.
- ✅ **WeighingSession skeleton:** `StartSessionTests`, `OpenSessionPerBatchTests`, `SessionIntegrityTests`.

**ADRs**
- ✅ **ADR-004** (seeded identities, hashed PIN, roles separate): `SeedTests`, `SupervisorVerificationTests`, `test_supervisor_id_is_not_an_operator`.
- ✅ **ADR-005** (current operator only from the server session): `OperatorApiTests`, `test_operator_is_per_browser_session`, `test_operator_in_the_body_is_ignored`.

### Issues Found

- None in the application code.
- Ruff applied its usual fixes to the new tests: wrapping, and an unused unpacked variable.

### Recommendations

- **Bolt 007 (UI):**
  - before view 1, `GET /station/api/operator`; if it is `null`, show the choice from `GET /operators` and `PUT /operator` with `X-CSRFToken`;
  - the header shows "Operator " + `display`;
  - after a selection's `201`, `POST /station/api/sessions` and show `error.message` on a refusal.
- **Bolts 010 and 012:** call `require_operator()` first in every weighing action, and store its operator on each record (FR-19b).
- **README (later step):** document OP-01 and SUP-01 / PIN `2468` as training identities (ADR-004).
- The test output contains expected log lines from the deliberate refusal cases ("Forbidden", "Not Found", "Bad Request", "Method Not Allowed", the WARNINGs). They are not failures.
