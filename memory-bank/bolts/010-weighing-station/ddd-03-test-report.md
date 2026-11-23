---
stage: test
bolt: 010-weighing-station
created: 2026-11-23T05:46:38Z
---

## Test Report: weighing-station (confirmation and progression)

### Summary

- **Tests**:
  - **Django: 70/70 new tests pass.** `npm test` reports **430/430**: 360 earlier tests plus 70 new.
  - **Playwright: 19/19** still pass. This bolt has no UI, so this is a regression run only.
- **Lint**: `npm run lint` passes. `makemigrations --check` finds no missing migration (0004 is included).
- **Coverage**: not measured. The coding standards set no percentage target. Every acceptance criterion, model decision and ADR is mapped below.
- **Live tests:** tare, re-read and the identity scans run against the live **Dummy Scale** and **Dummy Scanner** (training contracts) through the real adapters:
  - weights are set with the Dummy Scale's training `simulate` control (`set`);
  - the scale is disconnected with the training mode toggle;
  - an unreachable scale is simulated by pointing `SCALE_BASE_URL` at a closed port.

### Test Files

- [x] `tests/weighing/flow.py` (helper, no tests): `LiveFlowTestCase` provides:
  - the training seed and operator OP-01;
  - scanner and scale URLs pointing at the live server;
  - an open B-24187 session;
  - helpers `set_weight`, `scale_weight`, `scale_mode`, `verify`;
  - `TEAL`, a within-tolerance weight per component.
- [x] `tests/weighing/test_progression.py` - 28 tests:
  - **activation:**
    - all pending before the first activation, `nextPending` 1, "0 of 5";
    - Blue RSPL first, automatically tared to 0;
    - Yellow RGB with its 214 g container reads 0.0000 after the automatic tare;
    - a touch switches: the old attempt ends `switched`, Sodium Sulphate becomes active on `scale-32kg` in kg, and nothing is recorded;
    - touching the active component changes nothing;
    - touching a done component is refused and leaves attempts unchanged;
    - refusals: no operator; unknown component; closed session;
    - a failed automatic tare leaves the component active but untared (`TareFailed`);
    - an attempt keeps its scale when the threshold changes.
  - **tare and quit:**
    - re-tare of a tared attempt ends it `retared` and starts a new, tared attempt; the scale reads 0;
    - tare of an untared attempt keeps the same attempt;
    - quit ends `quit`, starts an untared attempt, records nothing, and doesn't touch the scale;
    - tare on a disconnected scale → `SCALE_DISCONNECTED`, and on an unreachable scale → `SCALE_UNAVAILABLE`; both change nothing;
    - tare / quit on a component that isn't active, or with no operator, are refused;
    - tare with no active component is refused.
  - **resume:**
    - after 2 confirmations, `current_session` returns the session at Yellow RGB with "2 of 5" and both actual weights;
    - the most recently active of two open sessions is chosen;
    - with no open session, nothing is resumed.
  - **stored state:** progress is derived from attempt and record rows that were written directly (the "server restart" case); a new session starts at component 1.
  - **append-only attempts:**
    - fixed fields can't change;
    - `tared_at` and the end are set once;
    - an attempt can't be deleted;
    - a second open attempt violates `one_open_attempt_per_session`.
- [x] `tests/weighing/test_confirmation.py` - 24 tests:
  - **record:**
    - every FR-13c field at 94.2 g (Yellow RGB, lot 2026-0387, C-12, tare 214 g, `scale-3kg`, target 94.0, band 93.5 – 94.5, `within`, OP-01, UTC);
    - the attempt ends `confirmed`;
    - 94.24 g is recorded as 94.2 g (ADR-009);
    - 93.5 g and 94.5 g are accepted;
    - the record names the operator who confirmed (OP-02, while the session's operator is OP-01);
    - the record uses the attempt's scale after a threshold change;
    - a failed tare of the next component keeps the record.
  - **refusals, where every test checks that no record is stored and no attempt changes:**
    - 93.4 g (`near`) and 94.6 g (`over`) → `OUT_OF_TOLERANCE` with the measured `detail`;
    - untared; unverified; wrong dyestuff; missing lot;
    - scale disconnected; scale unreachable;
    - no operator; another component active; no active component; closed session;
    - a double confirm records once.
  - **immutability:** a record can't be changed or deleted, and its attempt can't be removed (`PROTECT`).
  - **order:**
    - all five components in recipe order, on `scale-3kg` × 3 then `scale-32kg` × 2, with units g / kg and "n of 5" after each; every record's attempt ended `confirmed`;
    - after Yellow RGB, Sodium Sulphate is active on `scale-32kg` in kg, already tared;
    - after a component touched out of order, the first pending component comes next.
- [x] `tests/weighing/test_confirmation_api.py` - 18 tests:
  - **`GET …/progress`:** the JSON shape before activation;
  - **`POST …/activate`, `…/quit`, `…/tare`:**
    - activate returns the active, tared component;
    - quit returns an untared restart;
    - tare returns a tared attempt; a disconnected scale gives `503`.
  - **`POST …/confirm`:**
    - `201` with the full record JSON and progress ("1 of 5", component 3 done with "94.2 g");
    - a weight in the body is ignored;
    - `409 OUT_OF_TOLERANCE` with `detail`;
    - `409 IDENTITY_NOT_VERIFIED`, `TARE_REQUIRED`, `COMPONENT_NOT_ACTIVE`;
    - `503 SCALE_DISCONNECTED`;
    - a double confirm → `409 COMPONENT_DONE`;
    - touching a done component → `409`, nothing changes;
    - without a CSRF token → `403`, nothing stored.
  - **`GET /current-session`:**
    - a fresh client after 2 confirmations gets "2 of 5", Yellow RGB active, and "1241.5 g" / "385.4 g";
    - with no open session → `{"session": null}`.
  - **rules:**
    - the 4 actions need an operator (`403`, nothing stored);
    - unknown session / component → `404`;
    - wrong methods → `405` on all 6 endpoints.
- **Changed:** `tests/weighing/factories.py`: `teal_selection` takes a `batch_id`, so a second open session can be created.
- The architecture boundary tests are unchanged and pass. `progression` and `confirmation` reach the scale only through `devices.scale`.

### Acceptance Criteria Validation

**003-tare-retare-and-quit**
- ✅ **AC 1: Yellow RGB on C-12 (tare 214 g) → tare shown, empty container reads 0.0 g net.**
  - `test_yellow_rgb_starts_tared_and_an_empty_container_reads_zero`.
  - The "TARE 214 g" text is bolt 008's header (`test_yellow_rgb_header`).
- ✅ **AC 2: re-tare resets net to 0 and restarts the attempt.** `test_retare_resets_net_to_zero_and_restarts_the_attempt`.
- ✅ **AC 3: quit records nothing and the component restarts.** `test_quit_records_nothing_and_restarts_the_component`, `test_quit_returns_an_untared_restart`.
- ✅ **AC 4: the tare used is stored on the record.** `test_the_record_has_every_traceability_field` (`tare` 214), `test_confirm_is_201_with_the_record_and_the_progress` (`tareText` "214 g").

**006-confirm-weighing**
- ✅ **AC 1: all preconditions met → full record in one transaction before the UI advances.** `test_the_record_has_every_traceability_field`, `test_confirm_is_201_with_the_record_and_the_progress`, `test_the_attempt_ends_confirmed_with_its_record`.
- ✅ **AC 2: any precondition not met → rejected on the server, nothing saved.** The `ConfirmRefusalTests` class, `test_out_of_tolerance_is_409_with_the_measured_weight`, `test_precondition_refusals`, `test_a_weight_in_the_body_is_ignored`.
- ✅ **AC 3: no edit or delete; corrections are new records.** `test_a_record_cannot_be_changed_or_deleted`, `test_the_attempt_of_a_record_cannot_be_removed`, `test_confirming_twice_records_once`. The app has no update or delete path. Correction records belong to bolt 012.

**008-progress-components**
- ✅ **AC 1: Blue RSPL → Red RB → Yellow RGB → Sodium Sulphate → Soda Ash, "n of 5".** `test_the_five_components_in_recipe_order`.
- ✅ **AC 2: after Yellow RGB, the 32 kg floor scale and kg.** `test_after_yellow_rgb_the_floor_scale_and_kg_take_over`.
- ✅ **AC 3: touching a done component does nothing.** `test_touching_a_done_component_does_nothing`, `test_touching_a_done_component_is_409_and_changes_nothing`.
- ✅ **AC 4: touching a pending component activates it with its scale, units, tolerance and tare.**
  - `test_touching_a_pending_component_switches_to_it`.
  - Tolerance and tare text come with `GET …/components` (bolts 008 / 009).

**010-resume-after-reload**
- ✅ **AC 1: reload with 2 of 5 → same component, both confirmations kept.** `test_reload_reopens_at_the_in_progress_component`, `test_reload_resumes_with_both_confirmations`.
- ✅ **AC 2: server restart → the same state from the database.** `test_progress_is_derived_from_attempts_and_records`, which uses rows only and keeps no in-memory state. A fresh `Client()` gets the same state in the API test.

**Approved model decisions and ADRs**
- ✅ **1. The server tares:** the tare tests read the Dummy Scale back as 0.0000 after `progression.tare` / `activate`.
- ✅ **2. Quit restarts untared:** `test_quit_records_nothing_and_restarts_the_component`, `test_untared_is_refused`.
- ✅ **3. Record tare = snapshot tare:** `test_the_record_has_every_traceability_field`.
- ✅ **4. Next component in the confirm transaction, tared after the commit:** `test_after_yellow_rgb_the_floor_scale_and_kg_take_over` (tared), `test_a_failed_tare_of_the_next_component_keeps_the_record`.
- ✅ **5. Resume the most recently active open session:** `test_the_most_recently_active_open_session_is_resumed`, `test_no_open_session_resumes_nothing`.
- ✅ **6. Record operator = current operator:** `test_the_record_names_the_operator_who_confirmed`.
- ✅ **ADR-010:** the `AttemptAppendOnlyTests` and `StoredStateTests` classes.
- ✅ **ADR-011:** the refusal tests show that a scale failure changes nothing; `test_confirming_twice_records_once`; `test_a_failed_tare_of_the_next_component_keeps_the_record`.

### Issues Found

- **In the application: none.**
- **In the tests (first drafts, fixed in the tests):**
  - Three confirmation tests assumed that the component after Yellow RGB comes next even when Blue RSPL and Red RB are still pending. The approved design takes the **first pending component in recipe order**. The tests now confirm Blue RSPL and Red RB first, or check that Blue RSPL comes next.
  - A test passed the threshold override as a string. It now passes a `Decimal`, as bolt 009's setting requires.
  - Ruff flagged one unused variable (RUF059).

### Notes

- Bolt 011 (UI) uses:
  - `GET /current-session` on page load (resume);
  - `POST …/activate` for `nextPending` and for rail touches;
  - F1 / F2 / F4 → `…/confirm`, `…/tare`, `…/quit`;
  - Progress JSON for the rail and the "n of 5" counter.

  Its Playwright tests cover the screen flow.
- With the training actuals used here, the total for the five components is 1.2415 + 0.3854 + 0.0942 + 24.048 + 9.612 = 35.3811 kg. FR-16's 35.322 kg uses the prototype's actuals, and completion is bolt 015.
- "Bad Request", "Conflict", "Service Unavailable" and `[WebServer]` request lines in the output are the live server's log of the deliberate refusal cases.
