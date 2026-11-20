---
stage: test
bolt: 007-assisted-weighing-station-ui
created: 2026-11-20T09:47:48Z
---

## Test Report: assisted-weighing-station-ui (shell + View 1)

### Summary

- **Tests**:
  - **Playwright E2E: 19/19 passed** (Chromium), on 2 consecutive runs of about 29 s each. They run against the isolated server on port 8001 with a fresh seeded DB.
  - **Django: 11/11 new tests passed.** `npm test` reports **238/238**: 227 earlier tests plus 11 new.
- **Lint**: `npm run lint` passes. `node --check` passes for every new JS file.
- **Coverage**: not measured. The coding standards set no percentage target; every acceptance criterion is mapped below.
- **Report**: the HTML report is in `playwright-report/` (git-ignored). It is copied to `docs/evidence/` at STEP 29.

### Test Files

- [x] `playwright/helpers.js` - Training-mode reset and toggles, scan simulation, "open as operator", and a status-bar locator. Training controls are used only by the tests.
- [x] `playwright/shell.spec.js` - 6 tests:
  - the operator choice comes first: the queue is hidden and the header says "No operator";
  - the header shows "WeighingMS STATION 01" and "Operator R. Karim · Shift A";
  - the operator survives a reload;
  - the crumb reads "BATCH B-24187 · ORDER SO-9931 · MACHINE JET-04" once the batch is open;
  - the clock shows `hh:mm:ss` and ticks;
  - the status bar shows the four devices READY, "ORGATEX · LINKED hh:mm" and EN.
- [x] `playwright/status-bar.spec.js` - 5 tests:
  - the scanner (UNAVAILABLE), `scale-3kg` and `scale-32kg` (DISCONNECTED) and the printer (ERROR) each change label **within 2 s**, with a red dot and no "READY", and return to READY within 2 s once restored;
  - with OrgaTEX unavailable, the bar shows "ORGATEX · UNAVAILABLE", view 1 shows "OrgaTEX unavailable" and no rows.
- [x] `playwright/select-batch.spec.js` - 8 tests:
  - **Rows from the API:** the scan prompt, the "Queue received from OrgaTEX at hh:mm." line, the 7 column headers, and 4 rows (B-24187, B-24188, B-24190, B-24191) whose cells equal `GET /api/batches`, field by field.
  - **Nothing hard-coded:** with the queue response replaced (`page.route`) by one invented batch, exactly that row is shown.
  - **Touch B-24187:** view 2 shows "Teal 4C". The request order is exactly `POST /station/api/selections` → `POST /station/api/sessions` → `GET /api/batches/B-24187` → `GET /api/batches/B-24187/recipe`.
  - **Scan the B-24187 card:** `POST selections` with `{"batchId": "B-24187", "method": "scan"}` → view 2 and the crumb.
  - **Refusals:**
    - B-24188 → "Recipe not available in training data", and view 1 stays;
    - scanning B-99999 → "Batch not found";
    - OrgaTEX down at selection → "OrgaTEX unavailable".
  - A dyestuff scan on view 1 is ignored.
- [x] `tests/station/test_terminal_page.py` - 7 tests:
  - `GET /` → 200 with WeighingMS / STATION 01;
  - the station name is configuration (`STATION_NAME` override);
  - the CSRF meta tag is present and the cookie is set;
  - Alpine.js is served locally (no CDN or unpkg);
  - the clients load before the terminal component and Alpine;
  - the rendered page contains no seed value;
  - `POST /` → 405.
- [x] `tests/station/test_no_hard_coded_data.py` - 4 tests:
  - the scan covers the templates and scripts;
  - no seed value (batch codes, order, machine, shade, dyestuff names and codes, operator and supervisor) appears in any station template, JS or CSS file. The vendored Alpine.js is excluded;
  - no `const/let/var batches|queue|recipe(s)|components|operators = [` literal;
  - the detector itself is checked.
- The architecture boundary tests (unchanged) pass and now also cover `station`: no `dummy_*` import, and the Dummy paths stay only in their owning clients.

### Acceptance Criteria Validation

**007/001-terminal-shell-and-status-bar**
- ✅ **AC 1: the header shows WeighingMS STATION 01, BATCH · ORDER · MACHINE when a batch is open, the operator's name and shift, and a clock.** `header shows the station and the chosen operator`, `header shows batch, order and machine once a batch is open`, `the clock shows hh:mm:ss and ticks`.
- ✅ **AC 2: SCALE 3 kg, SCALE 32 kg, SCANNER, PRINTER, ORGATEX each show their state, plus EN.** `status bar shows every device, ORGATEX and EN`.
- ✅ **AC 3: a device failure is visible within 2 s and never shows READY.** The 4 failure tests in `status-bar.spec.js` (2 s timeout), plus the ORGATEX unavailable test.

**007/002-select-batch-view**
- ✅ **AC 1: the prompt, "Queue received from OrgaTEX at hh:mm." and one row per batch with the 7 columns.** `view 1 shows the prompt and one row per batch from GET /api/batches`, `rows show whatever the API returns`.
- ✅ **AC 2: a touched row or a scanned card → view 2 for that batch.** `touching B-24187 opens view 2 …`, `scanning the B-24187 batch card opens view 2`.
- ✅ **AC 3: a failed selection or OrgaTEX unavailable → the message is shown.** The B-24188, B-99999 and OrgaTEX-down tests, and `ORGATEX shows UNAVAILABLE …`.

**005/001-identify-operator (UI part, deferred from bolt 006)**
- ✅ **The operator is chosen before weighing, and the header shows "Operator R. Karim · Shift A".** `the operator must be chosen …`, `header shows the station and the chosen operator`, `the chosen operator stays after a reload`.

**Bolt / workbook STEP 19**
- ✅ **The Network tab shows `GET /api/batches`, then `GET /api/batches/B-24187` and `GET /api/batches/B-24187/recipe` (T317–T318).** Asserted by the request-order test. The screenshots are the user's evidence.
- ✅ **No batch array in the templates or JS (T327).** `test_no_hard_coded_data.py`, `test_rendered_page_contains_no_scenario_data`, and the `page.route` test.

### Issues Found

- **In the application: none.**
- **In the tests:** two first-draft assertions used anchored regexes that didn't allow the template's surrounding whitespace (the operator chip and the "Queue received" line). I fixed the regexes, not the app, and both pass on the rerun.

### Notes

- The Playwright server (port 8001, DB in `playwright/.cache/`) starts and stops with each run. The dev server and dev DB are not touched.
- The scan tests wait about 0.5 s before simulating a scan. The scanner client ignores the scan that already exists when watching starts (bolt 004 design), so the wait lets it record its baseline.
- `[WebServer]` lines in the Playwright output are the E2E server's request log. The "Conflict" / "Not Found" lines are the deliberate refusal cases.
- Not covered here (later bolts): the weigh view (bolt 011); resume after a reload into an open batch (bolt 010); the queue "WEIGHING" tag; the training panel (bolt 011).
