---
stage: test
bolt: 011-assisted-weighing-station-ui
created: 2026-11-23T06:38:23Z
---

## Test Report: assisted-weighing-station-ui (View 2 · Weigh)

### Summary

- **Tests**:
  - **Django: 449/449** (`npm test`): 430 earlier tests plus 19 new.
  - **Playwright: 50/50** (`npx playwright test`): 19 earlier tests plus 31 new.
  - The full Playwright suite passed twice in a row.
  - `weigh.spec.js` passed 4 runs in a row and `training-panel.spec.js` 3 runs in a row after the fixes below.
- **Lint**: `npm run lint` passes.
- **Coverage**:
  - Not measured; the coding standards set no percentage target.
  - Every acceptance criterion of stories 003, 004, 005 and 008 is mapped below.
- **Live tests:** the Playwright tests run against the real terminal on its own server (port 8001), with the Dummy Scale, Scanner, Printer and OrgaTEX as training contracts.
  - Weights are set with the Dummy Scale's training `simulate` control, or with the training panel itself.
  - Each test starts from the freshly seeded database (Decision 4).

### Test Files

- [x] `tests/weighing/test_bar_geometry.py` - 17 tests:
  - **bar scale:**
    - Yellow RGB band from 74.8 %, 0.8 % wide, target line 75.2 %;
    - rounding half-up to 0.1 % (94.2 g → 75.4 %);
    - clamped to 0 – 100 %;
    - a zero maximum draws nothing;
    - the 0.6 % minimum band width;
    - results are `Decimal`;
    - scale class text "3 kg" / "32 kg".
  - **components API:**
    - the bar of all five Teal 4C components;
    - Yellow RGB display max "125.0 g", target amount "94.0", class text and header meta;
    - Sodium Sulphate "32.000 kg" / "24.000" / "32 kg";
    - colour from the recipe snapshot;
    - a missing lot shows "LOT —";
    - a component's bar uses its display max.
  - **evaluation API:**
    - the fill at 0.0 / 93.4 / 94.2 / 96.4 / 200 g → 0.0 / 74.7 / 75.4 / 77.1 / 100.0 %;
    - 94.24 g fills like 94.2 g (ADR-009);
    - a kg reading on the g bar;
    - the floor-scale fill.
- [x] `tests/station/test_terminal_page.py` - 2 new tests:
  - **training panel:** after the status bar (outside the device), "TRAINING ONLY" only in the panel, no template comment leaking into the page;
  - **keys:** OK · Confirm / Re-tare / Quit / Supervisor override present, override disabled.
  - The script-order test now covers the three new scripts.
- [x] `tests/station/test_no_hard_coded_data.py` - The scan now explicitly covers `weigh.js`, `training-panel.js` and `training-client.js`. None of them contains a seed value or a data-array literal.
- [x] `playwright/weigh.spec.js` - 19 tests:
  - **rail (story 003):**
    - "Teal 4C", B-24187, "0 of 5 components weighed";
    - the five rows with name, code · class, target and state;
    - the swatch colour from the API;
    - rows show whatever the components API returns (response rewritten in the test).
  - **header:** Yellow RGB name and "DYE-4471 · LOT 2026-0387 · CONTAINER C-12 · TARE 214 g"; touching a pending row activates it.
  - **done row:** touching it sends no POST and changes nothing.
  - **scan step:**
    - shown before verification, and OK stays disabled at 94.0 g;
    - a wrong code shows "Wrong dyestuff" and OK stays disabled;
    - the right code hides the step and enables OK.
  - **readout (story 004):**
    - it follows the Dummy Scale within 1 s without a reload;
    - the scale is polled at least 9 times in 2 s with a median gap ≤ 220 ms (NFR-1).
  - **Yellow RGB panel:**
    - Target 94.0, Still to weigh 94.0, unit g;
    - caption "TOLERANCE ±0.5 g (93.5 – 94.5)" and "125.0 g";
    - band at 74.8 % / 0.8 %, target line at 75.2 %;
    - "DISPENSE — 94.0 g REMAINING".
  - **zones:** under / near / within / over at 50.0 / 90.0 / 94.2 / 96.4 g colour the readout, the fill and the status line with the prototype colours, and show the server's status text.
  - **Sodium Sulphate:**
    - "Scale selected · 32 kg floor · automatic", kg in all three cells, 0.000;
    - caption "TOLERANCE ±0.120 kg (23.880 – 24.120)" and "32.000 kg".
  - **actions (story 005):**
    - OK disabled at 93.4 and 94.6, enabled at 93.5, 94.0 and 94.5;
    - F1 at 94.6 g sends no confirm.
  - **F1 confirm:** the rail shows "✓ 94.2", "1 of 5", and the first pending component becomes active.
  - **F4 / F2:**
    - F4 records nothing and shows "TARE REQUIRED — PRESS RE-TARE (F2)" with OK disabled;
    - F2 brings the reading back to 0.0.
  - **buttons:** they do what the keys do (Quit, Re-tare, OK).
  - **key size:** every key is ≥ 57 px (62 px), with the F1 / F2 / F4 labels.
  - **Supervisor override:** shown and disabled.
  - **whole batch:**
    - five components in recipe order;
    - after Yellow RGB, Sodium Sulphate is active on the 32 kg floor scale at 0.000 kg;
    - all five rows end ✓ and the keys are disabled.
  - **resume:** reloading after 2 of 5 reopens Yellow RGB with both ✓ kept and the crumb restored.
- [x] `playwright/training-panel.spec.js` - 12 tests (4 of them from one loop over the device switches):
  - **simulate buttons:**
    - Simulate dispense / overshoot / Reset → 94.2 / 96.4 / 0.0 g on the Dummy Scale, with View 2 following and the zone changing;
    - on Sodium Sulphate, dispense lands at 24.048 kg on `scale-32kg`.
  - **Set weight:** 93.5 g.
  - **rejected simulation:** 5000 g shows the Dummy's capacity message.
  - **Simulate scan:** prefilled "DYE-4471", and it verifies the component.
  - **failure switches:**
    - for `scale-3kg`, `scale-32kg`, `scanner` and `printer`, the status bar shows the failure within 2 s and READY again after the switch is cleared;
    - OrgaTEX goes unavailable and back to ok.
  - **disconnected scale:** the readout blanks, OK is disabled and the status line says "Scale disconnected"; reconnecting restores 94.2 and OK.
  - **panel placement:** marked TRAINING ONLY, not inside the device, no simulate control on the operator screen.
- **Changed earlier specs** (already reported at Implement):
  - `select-batch.spec.js`, `shell.spec.js` and `status-bar.spec.js` start from the seeded database.
  - The request-order test checks the first four calls.

### Acceptance Criteria Validation

**Story 003-weigh-view-recipe-rail-and-header**
- ✅ **AC 1: rail with "Recipe · Teal 4C", B-24187, "n of 5 components weighed", swatch, name, code · scale class, target and state.** `the rail shows Teal 4C, …`, `rows show whatever the components API returns`, `a reload resumes …`.
- ✅ **AC 2: Yellow RGB header "Remazol Yellow RGB" and "DYE-4471 · LOT 2026-0387 · CONTAINER C-12 · TARE 214 g".** `Yellow RGB header shows …`, `test_rail_and_header_fields_of_yellow_rgb`.
- ✅ **AC 3: "Scan dyestuff" step while unverified; a mismatch shows "Wrong dyestuff".** `scan dyestuff step: a mismatch …`.
- ✅ **AC 4: a touched pending row becomes active; a done row does nothing.** `Yellow RGB header …`, `touching a done row sends nothing and changes nothing`.

**Story 004-weigh-view-live-readout-and-tolerance**
- ✅ **AC 1: the scale weight changes → within 200 ms "Weighed now" and the bar update without a reload.** `the readout follows the Dummy Scale without a reload`, `the active scale is polled at least every 200 ms`.
- ✅ **AC 2: Yellow RGB panel: Target 94.0 g, Still to weigh, the caption, the band 93.5 – 94.5 and the target line on a 0 – 125 g bar.**
  - E2E: `Yellow RGB panel: …`.
  - Bar maths: `test_yellow_rgb_on_the_0_to_125_g_bar`.
- ✅ **AC 3: zones from the API → prototype colours and status text.** `zones from the API colour the readout, bar and status line`.
- ✅ **AC 4: scale change → "Scale selected · 32 kg floor · automatic" and kg.** `Sodium Sulphate switches …`, `five components in recipe order …`.

**Story 005-weigh-view-actions-and-function-keys**
- ✅ **AC 1: OK · Confirm F1 enabled within tolerance, disabled outside.** `OK · Confirm F1 is enabled only within tolerance`, `F1 at 94.6 g records nothing`.
- ✅ **AC 2: F1 / F2 / F4 run Confirm / Re-tare / Quit exactly like the buttons.** `F1 confirms …`, `F4 quits … F2 re-tares …`, `the buttons do what the keys do`.
- ✅ **AC 3: each primary button ≥ 15 mm (≈ 57 px).** `every action key is at least 57 px`. All four keys measure 62 px.

**Story 008-training-simulation-panel**
- ✅ **AC 1: Simulate dispense / overshoot / Reset → 94.2 / 96.4 / 0.0 g and View 2 follows.** `Simulate dispense / overshoot / Reset land at …`.
- ✅ **AC 2: a device or OrgaTEX failure switch puts its Dummy into the failure mode and takes it out again.** The four device switch tests, `the OrgaTEX failure switch …`, `a disconnected scale blanks the readout and blocks OK`.
- ✅ **AC 3: the panel is marked training-only and separate from the operator controls.** `the panel is marked TRAINING ONLY …`, `test_training_panel_is_marked_and_outside_the_device`.

**Plan decisions**
- ✅ **1. Server bar percentages:** `test_bar_geometry.py`, plus the E2E band / target-line / fill style checks.
- ✅ **2. Simulate scan field:** `Simulate scan is prefilled …`, `scan dyestuff step: a mismatch …`.
- ✅ **3. Supervisor override disabled:** `Supervisor override is shown and disabled until STEP 24`, `test_view_2_keys_and_supervisor_override`.
- ✅ **4. E2E database reset:** every new test and the three earlier specs start from the seed. Both full runs passed 50/50.

### Issues Found

**In the application (fixed during this stage):**
1. **Rail state cell and status line.**
   - **Problem:** each was made of three spans toggled by `x-show`. The hidden spans were still in the text, e.g. "✓ null" on pending rows for screen readers and in `textContent`.
   - **Fix:** each is now one element whose text comes from a single template expression.
2. **Scan during a running request.**
   - **Problem:** a dyestuff scan arriving while a request was running (opening the session, or finishing a confirm) was dropped. The scanner reports each scan only once, so the operator would have had to scan again.
   - **Fix:** such a scan is now held and checked when the request ends.
3. **Order of the update after an action.**
   - **Problem:** the rail counter switched to the new progress before the new component's data had loaded. For a moment the header and the training panel still showed the previous component.
   - **Fix:** the components are now read first, and the screen switches in one step.

**In the tests (first drafts, fixed in the tests):**
- The expected rail actuals used the prototype's training values (1241.5 / 385.4). Simulate dispense lands at target + 0.4 × tolerance, i.e. 1242.4 / 386.8.
- Three timing problems:
  - the test set a weight before Yellow RGB's activation had tared the scale;
  - the test read the OrgaTEX mode before the PUT finished (now polled);
  - the expected "Scale disconnected" text was missing the scale id that the Dummy's message carries.

### Notes

- **What the user sees:** with fixes 2 and 3, a scan made right after a confirm verifies the new component without a second scan, and the training panel always shows the active component's code.
- **Total of the UI flow:** with Simulate dispense the five actuals are 1242.4 g, 386.8 g, 94.2 g, 24.048 kg and 9.619 kg. FR-16's total and View 3 belong to bolts 015 and 017.
- **Overshoot:** at 96.4 g the status line shows "OVER TOLERANCE — SURPLUS +2.4 g" and OK stays disabled. The surplus panel and the override are STEP 24 (bolt 013).
- **Log output:** "Conflict" / "Service Unavailable" and `[WebServer]` lines in the Playwright output are the live server's log of the deliberate refusal and failure cases.
