---
stage: test
bolt: 015-weighing-station
created: 2026-11-23T10:50:00Z
---

## Test Report: weighing-station (batch completion and history)

### Summary

- **Django: 543/543** (`npm test`): 516 earlier tests plus 27 new; 1 bolt 014 test updated.
- **Playwright: 58/58** (`npx playwright test`); `playwright/write-back.spec.js` updated.
- **Lint:** `npm run lint` passes.
- **Coverage:** no percentage target (coding standards). Every acceptance criterion of stories 009 and 011 has at least one automated test.
- **Live, not mocked:** completion runs through the real confirmation against the live Dummy Scale and Scanner. The only patch is in the rollback test, which makes `open_write_back` fail.

### Test Files

- [x] `tests/weighing/test_completion.py` - 16 tests:
  - **total dispensed:** the prototype actuals → **35.322 kg** as `Decimal` (`"35.322"`); g and kg summed in kg (500.0 g + 1 kg = 1.500); half up to 1 g (0.5 g → 0.001, 0.4 g → 0.000); no records → 0.000;
  - **elapsed text:** 401 s → "6 min 41 s", 59 → "0 min 59 s", 0 → "0 min 0 s", 3600 → "60 min 0 s";
  - **summary texts:** "5 of 5", YES / NO, "35.322 kg";
  - **completion through the real flow:**
    - the 5th confirmation completes the session with `completed_at` equal to the last record's time; no attempt stays open; BatchCompleted (with `totalDispensedKg=35.322`) and WriteBackTriggered are logged;
    - the summary of the prototype actuals (operator "R. Karim · Shift A", elapsed from the session times);
    - completion opens a pending write-back with 0 attempts, the key `WMS-B-24187-S<id>` and operator OP-01;
    - at 4 of 5 the session stays in progress, has no write-back, and its summary is refused;
    - `complete` at 4 of 5 → `BATCH_NOT_COMPLETE`; on a complete session → `SESSION_NOT_OPEN`;
    - a complete session refuses activate / tare / quit / confirm, and the records stay 5;
    - a failing `open_write_back` rolls back the 5th record and the completion; confirming again completes the batch;
    - `open_write_back` is idempotent.
- [x] `tests/weighing/test_completion_api.py` - 11 tests over HTTP:
  - **confirm:** only the last confirm carries `completion`; `progress.state` becomes `complete`, with no active component and the total 35.322;
  - **`GET sessions/<id>/summary`:**
    - every summary field, with `completedAt` equal to the last record's `recordedAt`, and the body equal to the confirm's `completion`;
    - the pending write-back (0 attempts);
    - 409 at 4 of 5, 404 for an unknown session, 405 on POST;
  - **`GET batch-history/B-24187`:**
    - five records in sequence, each with every traceability field (target, actual, unit, operator, scale, lot, container, tare, timestamp, tolerance, result);
    - Yellow RGB 94.0000 / 94.2 g on scale-3kg, lot 2026-0387, C-12, tare 214.0000; Sodium Sulphate on scale-32kg at 23.980 kg;
    - the operator ID OP-01 on every record;
    - records of two sessions in sequence order;
    - an unknown batch → an empty list;
    - 405 on POST.
- [x] `tests/weighing/test_write_back_api.py` (bolt 014) - one test updated: "status before the first start is null" became **"completion leaves a pending write-back before the first start"** (pending, 0 attempts, OP-01). The old premise no longer holds under ADR-013.
- [x] `playwright/write-back.spec.js` (bolt 014) - updated: it reads the session id before weighing, because a complete session is no longer the current session. Its assertions are unchanged; the first `writeBack` is still attempt 1.

### Acceptance Criteria Validation

- ✅ **Story 009 AC 1** (5 of 5 → complete with n of N, all within, total kg, elapsed, operator): `test_fifth_confirmation_completes_the_batch`, `test_summary_of_the_prototype_actuals`, `test_summary_of_the_completed_batch`.
- ✅ **Story 009 AC 2** (35.322 kg in `Decimal`): `test_prototype_actuals_total_35_322_kg`, plus the API summary through the real flow.
- ✅ **Story 009 AC 3** (4 of 5 refused): `test_four_of_five_is_not_complete`, `test_completion_request_at_four_of_five_is_refused`, `test_summary_at_four_of_five_is_refused`.
- ✅ **Story 009 AC 4** (write-back triggered): `test_completion_triggers_the_write_back`, `test_summary_carries_the_pending_write_back`, and the Playwright write-back run after completion.
- ✅ **Story 011 AC 1** (target, actual, operator, scale, lot, container, tare, timestamp per component): `test_every_component_with_all_traceability_fields`.
- ✅ **Story 011 AC 2** (operator ID on every record): `test_every_record_carries_the_operator_id`.
- ✅ **ADR-013 risk** (rollback of the last confirmation) and **ADR-014 scope** (all sessions, empty for unknown): tested.

### Issues Found

- **One new test expectation was wrong; the code was fine.** The record JSON from bolt 010 sends the target and tare as 4-place strings (`"94.0000"`, `"214.0000"`), while the actual weight is at display resolution (`"94.2"`). The history test now expects the existing format.
- **Two bolt 014 tests depended on the old behaviour** and were updated as listed above (planned in the Technical Design).
- No code changes were needed.

### Notes

- **Dev database:** unchanged by this bolt. B-24187 is still 1 of 5 there; no migration was added.
- **For bolt 017:** a reload after completion opens the queue, because `current-session` returns only in-progress sessions. View 3 can be rebuilt from `GET sessions/<id>/summary`.
- **The workbook STEP 26 evidence** comes after bolts 016–017.
