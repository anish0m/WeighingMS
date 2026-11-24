---
stage: test
bolt: 017-assisted-weighing-station-ui
created: 2026-11-24T04:40:00Z
---

## Test Walkthrough: assisted-weighing-station-ui (View 3 · Confirm & print, no hard-coded data)

### Summary

- **Playwright: 68/68** (`npx playwright test`): 60 earlier tests plus 8 new; 5 earlier tests updated for View 3.
- **Django: 584/584** (`npm test`), including the extended no-hard-coded-data scan and the import boundary test.
- **Lint:** `npm run lint` passes.
- **Live, no mocks:** B-24187 is weighed 5 of 5 through the terminal UI against the live Dummies. Failures are switched through the training controls. The seed change edits the E2E database itself.

### Test Files

- [x] `playwright/confirm-print.spec.js` - **new**, 6 tests:
  1. **Summary and CONFIRMED (AC 1, AC 2):**
     - "Batch B-24187 weighed";
     - every summary row equals `GET summary` (5 of 5, YES in green, the total in kg, the elapsed text, R. Karim);
     - "CONFIRMED hh:mm:ss" in green;
     - the prototype's sentence with JET-04;
     - no Retry; the header crumb still shows the batch.
  2. **OrgaTEX unavailable before the last F1 (AC 2):**
     - "NOT WRITTEN" in red, the reason "Not written to OrgaTEX: OrgaTEX unavailable", Retry visible, no "posted" sentence;
     - after restore, Retry → CONFIRMED; Retry and the reason are hidden; Dummy OrgaTEX holds one consumption.
  3. **F1 Print ticket (AC 3):**
     - the preview text equals the ticket the Dummy Printer stored;
     - "Ticket printed hh:mm:ss";
     - the preview switches to REPRINT; the second print shows "REPRINT printed hh:mm:ss".
  4. **Printer error (AC 3):**
     - "Printer error: ticket not printed" in red, and the preview is not a REPRINT;
     - after restore, F1 prints.
  5. **F3 Next batch (AC 3):** View 1 with B-24187 in the queue; a reload stays on View 1.
  6. **Reload on View 3:** View 3 reopens with the same CONFIRMED time, the sentence, the crumb and the ticket; still one consumption.
- [x] `playwright/no-hard-coded-data.spec.js` - **new**, 2 tests (story 009 AC 2):
  - the B-24190 shade changed in the Dummy seed → the queue shows "Navy 14 (seed changed)" after a reload;
  - the Yellow RGB target changed to 95.0 g in the Dummy seed → the rail shows "95.0 g", the weigh panel's target shows 95.0, and the server's band caption shows 94.5 – 95.5.
  - The pristine database is restored after each test.
- [x] `tests/station/test_no_hard_coded_data.py` (Django, story 009 AC 1): the scan covers `done.js`; the seed values now include "Sodium Sulphate", "Soda Ash", "35.322", "6 min 41 s", "FCI DYEING" and "WMS-".
- [x] `tests/architecture/test_integration_boundaries.py` (story 009 AC 3): unchanged and passing; no WeighingMS module imports `dummy_*`.
- [x] **Updated for View 3** (it replaces View 2 when the batch completes, and starts the write-back by itself):
  - `playwright/helpers.js` `weighAllB24187`: waits for View 3 after the 5th F1 and for the write-back status to settle; takes an optional `beforeLast` hook;
  - `playwright/weigh.spec.js` "the whole batch": checks the first four rail ticks, then View 3, and the five stored actuals through `batch-history`;
  - `playwright/write-back.spec.js` (2 tests): the automatic write-back is attempt 1 (CONFIRMED, one consumption). Failure: OrgaTEX is switched off before the last F1 → not written; retry → CONFIRMED (attempt 2);
  - `playwright/tickets.spec.js`: unchanged; passes with the updated helper.

### Acceptance Criteria Validation

- ✅ **Story 007 AC 1** (summary from the API): confirm-print test 1.
- ✅ **Story 007 AC 2** (CONFIRMED hh:mm:ss / not written with Retry): confirm-print tests 1 and 2.
- ✅ **Story 007 AC 3** (F1 prints and the preview shows; F3 opens View 1): confirm-print tests 3, 4 and 5.
- ✅ **Story 009 AC 1** (no arrays or literal values in templates / JS): the extended Django scan.
- ✅ **Story 009 AC 2** (a changed seed shows after a reload): no-hard-coded-data tests 1 and 2.
- ✅ **Story 009 AC 3** (no `dummy_*` imports): the architecture boundary test.
- ✅ **Plan extras:** reload on View 3 reopens it; after Next batch a reload shows View 1; lint clean.

### Issues Found and Fixed

- **View 3 after a reload lacked the batch details (fixed in `done.js`).**
  - **Symptom:** the header crumb and the "released for transport to JET-04" sentence were missing, because the OrgaTEX batch was only read when weighing started.
  - **Fix:** resuming View 3 reads the batch from OrgaTEX for display (it falls back to the batch ID if OrgaTEX is unavailable).
  - Covered by confirm-print test 6.
- **Test-side corrections:**
  - my first View 3 test wrongly expected the header crumb to hide; it now expects the crumb to stay, like the prototype;
  - one test pressed F1 before OK was enabled; it now waits;
  - the seed-change test's last check was tightened to the weigh panel's target and the server's band caption.

### Notes

- **Workbook STEP 26 evidence path (T418–T430):**
  1. In the browser (Network tab, filter `api`), select B-24187 and confirm all five.
  2. View 3 opens and shows "Written to OrgaTEX CONFIRMED hh:mm:ss".
  3. The Network tab lists `POST /api/batches/B-24187/consumption` (Payload: key and five components), answered `201`.
- **Dev database:** B-24187 is at 1 of 5 there (STEP 25), so the STEP 26 run continues with Blue RSPL.
