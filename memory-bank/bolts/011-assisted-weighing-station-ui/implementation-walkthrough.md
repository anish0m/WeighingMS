---
stage: implement
bolt: 011-assisted-weighing-station-ui
created: 2026-11-23T06:08:54Z
---

## Implementation Walkthrough: assisted-weighing-station-ui (View 2 · Weigh)

### Summary

View 2 now reproduces the prototype's Weigh screen:
- recipe rail;
- component header and Scale selected badge;
- scan dyestuff step;
- live readout and bar with the tolerance band and target line;
- status line;
- OK · Confirm F1, Re-tare F2, Quit F4, and a disabled Supervisor override.

Every value comes from the station API. The server decides the zone, still to weigh, whether OK is allowed, the scale, tare, records and the next component. The terminal resumes an open session on page load.

A separate panel marked TRAINING ONLY drives the Dummy APIs. It holds the prototype's simulate buttons, an exact weight, a simulated dyestuff scan and the failure switches.

### Structure Overview

- **One Alpine component per screen.**
  - The View 2 state and handlers live in their own script, merged into the terminal component.
  - The terminal script now resumes, passes the session in after a selection, and routes dyestuff scans to View 2.
- **Training panel.**
  - A separate Alpine component outside the device frame.
  - It follows the active component through a window event that View 2 sends. The operator screen never reads anything back from it.
- **Path ownership.** Every Dummy path is still known by exactly one JS client:
  - scale simulation is in the scale client;
  - simulated scans are in the scanner client;
  - the failure switches are in a new training client.
- **Display data from the server.** The server sends display data that the browser must not calculate:
  - swatch colour, display maximum and scale class text;
  - the name-free header line, the target amount;
  - bar percentages for the band, the target line and the fill.

### Completed Work

- [x] `src/station/static/station/weigh.js` - View 2 state:
  - session progress and components;
  - live readout with a 200 ms poll and at most one evaluation in flight;
  - rail touches, the dyestuff scan step;
  - confirm / re-tare / quit with F1 / F2 / F4;
  - the active-component event for the training panel.
- [x] `src/station/static/station/training-panel.js` - Training panel (story 008):
  - Simulate dispense / overshoot / Reset, Set weight;
  - Simulate scan, prefilled with the active component's code;
  - failure switches built from the Dummies' current modes.
- [x] `src/station/static/station/training-client.js` - The only JS file that knows the training failure-switch paths.
- [x] `src/station/static/station/station-client.js` - The station API calls for View 2: current session, progress, components, evaluation, identity, activate, tare, quit, confirm.
- [x] `src/station/static/station/terminal.js`:
  - merges the View 2 state;
  - resumes an open session after the operator is known;
  - opens View 2 with the session after a selection;
  - keeps watching the scanner on View 2.
- [x] `src/station/templates/station/terminal.html` - View 2 markup (rail, header, scan step, readout, bar, caption, status line, action keys) and the training panel block.
- [x] `src/station/templates/station/base.html` - Loads the new scripts before the terminal; adds a training block outside the device frame.
- [x] `src/station/static/station/station.css` - The prototype's View 2 styles (zone `ok` is the server's `within`), the key variants, and the training panel's page-style controls.
- [x] `src/devices/static/devices/scale-client.js` - A training-only call to the Dummy Scale's simulate control.
- [x] `src/devices/static/devices/scanner-client.js` - A training-only simulated scan.
- [x] `src/weighing/rules.py` - The bar scale of a component: Decimal percentages in 0.1 % steps, clamped to 0–100, with the prototype's minimum band width.
- [x] `src/weighing/scale_selection.py` - Short class text per scale class for the rail ("3 kg", "32 kg").
- [x] `src/batches/material.py` - The header's meta line (code, lot, container, tare) as its own value; the full header text is unchanged.
- [x] `src/weighing/views.py`:
  - **Component JSON** adds colour, display maximum (amount and text), header meta, target amount, scale class text and bar geometry.
  - **Evaluation JSON** adds the fill percentage.
- [x] `playwright.config.js` - Keeps a pristine copy of the freshly migrated and seeded E2E database.
- [x] `playwright/helpers.js` - Database reset, exact-weight helper, and "open B-24187" helper.
- [x] `playwright/select-batch.spec.js`, `playwright/shell.spec.js`, `playwright/status-bar.spec.js`:
  - each test starts from the seeded database;
  - the request-order test now checks the first four calls (server first, then OrgaTEX) and allows View 2's own calls after them.
- [x] `tests/architecture/test_integration_boundaries.py` - The training failure-switch path has a single JS owner.
- [x] `tests/weighing/test_identity_api.py`, `tests/weighing/test_rules_api.py` - The whole-object expectations include the new display fields.

### Key Decisions

- **Bar geometry from the server (Decision 1)**: the browser only places the server's percentages, so the JS does no arithmetic on quantities.
- **Training scan field (Decision 2)**:
  - It is prefilled from the API with the active component's code.
  - Editing the code shows "Wrong dyestuff".
  - No scenario value is written in the UI code.
- **Supervisor override disabled (Decision 3)**: shown as in the prototype; STEP 24 decides its behaviour in bolt 013.
- **E2E database reset (Decision 4)**:
  - Tests copy the seeded database back before they start.
  - This is test-only; the app gets no reset endpoint.
  - It works because Django opens a new SQLite connection per request.
- **Training panel as its own component**:
  - It stays outside the device frame and is marked TRAINING ONLY (story 008 AC 3).
  - It learns the active component only through an event.
- **Untared attempt after Quit**: the status line shows "TARE REQUIRED — PRESS RE-TARE (F2)" and OK stays disabled until F2 (bolt 010 decision 2).
- **Function keys**:
  - The keys run the same handlers as the buttons.
  - The browser's default F1 help is suppressed.
  - A key pressed while a request is running is ignored, like a click on a disabled button.

### Deviations from Plan

- **One extra file**: `training-panel.js` keeps the training panel separate from the operator screen.
- **Bar fields**: the bar's band is sent as `lowPercent` / `widthPercent` instead of `lowPercent` / `highPercent`, so the prototype's minimum band width is applied on the server.
- **Extra JSON fields**: `headerMeta` and `targetAmount` were added. The prototype shows the name above the meta line and the target as a number with a separate unit, and the browser must not split or format those values itself.
- **Status bar spec**: `status-bar.spec.js` also resets the database, because its ORGATEX test expects View 1.

### Dependencies Added

None.

### Developer Notes

- **Scale changes**: when the active scale changes (after Yellow RGB, or on touching Sodium Sulphate), the readout stops polling the old scale and polls the new one.
- **Training panel targets**: the failure-switch list comes from the Dummies' modes, so a new Dummy scale appears there without a UI change.
- **Verification**: Django 430/430, lint clean, and the existing Playwright suite 19/19 with the new View 2 in place.
- **Throwaway smoke run** (deleted afterwards):
  - scan mismatch → "Wrong dyestuff";
  - the five boundary weights (OK only at 93.5 / 94.0 / 94.5);
  - Overshoot → 96.4;
  - F4 → TARE REQUIRED, F2 → 0.0;
  - the 32 kg floor scale;
  - keys 62 px high;
  - the first confirm and resume after reload;
  - no console errors.
- **New Playwright specs**: these come in the Test stage.
