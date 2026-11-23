---
stage: plan
bolt: 011-assisted-weighing-station-ui
created: 2026-11-23T05:53:53Z
---

## Implementation Plan: assisted-weighing-station-ui (View 2 · Weigh)

### Objective

Turn the View 2 skeleton into the prototype's Weigh screen for B-24187. It has:
- the recipe rail;
- the component header;
- the scan dyestuff step (OQ-8);
- the live readout;
- the bar with the tolerance band;
- the status line;
- the OK · Confirm F1, Re-tare F2, Quit F4 and Supervisor override keys;
- a training-only simulation panel.

The browser shows what the APIs return:
- The server makes every weighing decision: zone, still to weigh, whether OK is allowed, scale selection, tare, record and next component (ADR-008, ADR-010, ADR-011).
- The JS does no arithmetic on quantities (NFR-16, FR-21).

### Deliverables

1. **Recipe rail** (story 003):
   - "Recipe · {recipe name}", batch id, "n of N components weighed".
   - One row per component:
     - swatch colour;
     - name;
     - code · scale class (e.g. "DYE-4471 · 3 kg");
     - target text;
     - state: "✓ {actual}" / WEIGHING / PENDING.
   - Touching a pending row → `POST …/activate`.
   - Touching a done row or the active row sends no request.
2. **Header** (story 003):
   - component name;
   - the server's header text "DYE-4471 · LOT 2026-0387 · CONTAINER C-12 · TARE 214 g";
   - the "Scale selected · {label} · automatic" badge.
3. **Scan dyestuff step** (story 003, OQ-8):
   - Shown while the active component's identity is not verified.
   - A dyestuff scan from the Dummy Scanner → `POST …/identity {scanId}`.
   - The server's message is shown ("Dyestuff verified" / "Wrong dyestuff").
   - Any material refusal (e.g. missing lot) is shown with the server's text.
4. **Live readout panel** (story 004):
   - Weighed now / Still to weigh / Target, in the active unit.
   - The bar has a fill, a tolerance band and a target line on a 0 – display-max scale.
   - Caption: "0", the server's "TOLERANCE ±0.5 g (93.5 – 94.5)", "125.0 g".
   - The status line uses the server's text.
   - The prototype's colours for under / near / within / over.
   - The active scale is polled every 200 ms (existing `scale-client.watchWeight`). Each changed reading goes to `GET …/evaluation`. At most one request is in flight, and the latest reading wins.
5. **Actions and function keys** (story 005):
   - OK · Confirm F1 is enabled only when all of these hold:
     - the server's evaluation says `withinTolerance`;
     - the component is material-ready;
     - the attempt is tared;
     - the scale is connected.
   - F1 / F2 / F4 run the same handlers as the buttons, with the browser's default actions suppressed.
   - Confirm → `POST …/confirm`, then the rail, header and scale are reloaded. The next component arrives active and tared. When the scale changes, the readout switches to that scale and its unit.
   - Re-tare → `POST …/tare`.
   - Quit → `POST …/quit` (untared restart, decision 2). The panel then shows "Re-tare (F2) before weighing".
   - Server refusals are shown with the server's message, e.g. SCALE_DISCONNECTED or OUT_OF_TOLERANCE.
   - All keys are at least 57 px high (they are already 62 px).
6. **Supervisor override key:** shown as in the prototype and disabled. It gets its behaviour in bolt 013 (STEP 24). See Decision 3.
7. **Training simulation panel** (story 008):
   - Separate from the operator screen and labelled **TRAINING ONLY · Dummy devices**.
   - Simulation buttons:
     - ▶ Simulate dispense / ▶ Simulate overshoot / Reset.
     - Set weight: a text field plus the active unit.
     - They call the Dummy Scale's `simulate` (`dispense` / `overshoot` send the active component's `target` and `tolerance` strings from the API; the Dummy calculates 94.2 g / 96.4 g).
   - Failure switches for OrgaTEX, scale-3kg, scale-32kg, scanner and printer (`/api/training/modes`). The status bar shows the effect.
   - A scan field, see Decision 2.
8. **Resume** (story 010, rendered here): on page load, once an operator is set, `GET /station/api/current-session`.
   - If a session is open, View 2 opens at its active component.
   - If no component is active, `nextPending` is activated.
   - Opening a batch from View 1 also activates `nextPending`.
9. **After the last component:**
   - The rail shows "5 of 5 components weighed" and the action keys are disabled.
   - View 3 is bolt 017; session completion is bolt 015.
10. **Server additions** (display data the UI must not compute, Decision 1):
    - **Component JSON** adds:
      - `colour` and `displayMax` / `displayMaxText` from the locked recipe snapshot;
      - `scale.classText` ("3 kg" / "32 kg");
      - `bar` {`lowPercent`, `highPercent`, `targetPercent`}.
    - **Evaluation JSON** adds `barPercent` (0 – 100, 0.1 % steps).

### Files

**Modified**
- `src/station/templates/station/terminal.html`: the View 2 markup (rail, header, scan step, readout, bar, status line, action keys) and the training panel.
- `src/station/static/station/terminal.js`: hands the session to the weigh view on selection and on resume.
- `src/station/static/station/station-client.js` adds:
  - `currentSession`, `sessionComponents`, `progress`, `evaluate`;
  - `activate`, `tare`, `quit`, `confirm`;
  - `verifyIdentity`.
- `src/station/static/station/station.css`: the prototype's rail, readout, bar, band, status-line and zone styles, plus the training panel style.
- `src/station/templates/station/base.html`: script tags for the new files. The training panel sits outside the device screen.
- `src/devices/static/devices/scale-client.js`: `simulate(scaleId, body)`, a training-only Dummy call. This file stays the only one that knows `/scales`.
- `src/devices/static/devices/scanner-client.js`: `simulateScan(kind, code)`, training-only. This file stays the only one that knows `/scanner` (only needed under Decision 2a).
- `src/weighing/rules.py`: bar geometry (Decimal percentages) for a component and a reading.
- `src/weighing/scale_selection.py`: `class_text` per scale class.
- `src/weighing/views.py`: the new component and evaluation JSON fields.
- `playwright/helpers.js`:
  - `resetDatabase()` (Decision 4);
  - `openB24187()`;
  - `setWeight`;
  - a comment update: the training panel now uses the training controls.
- `playwright.config.js`: keeps a pristine copy of the seeded E2E database (Decision 4).
- `playwright/select-batch.spec.js` and `playwright/shell.spec.js`: reset the database before each test, because an open session now resumes View 2.
- `tests/architecture/test_integration_boundaries.py`: `/training/modes` is owned by the new training client.

**Created**
- `src/station/static/station/weigh.js`: the View 2 Alpine state, merged into `terminal()`, so that `terminal.js` stays small.
- `src/station/static/station/training-client.js`: the only JS file that knows `/training/modes` (GET all modes, PUT one).
- `playwright/weigh.spec.js`: the View 2 E2E tests.
- `playwright/training-panel.spec.js`: the training panel E2E tests.
- `tests/weighing/test_bar_geometry.py`: the server's bar percentages.

### Requirements and stories

1. **003-weigh-view-recipe-rail-and-header:** FR-3, FR-4 (scan step, OQ-8), FR-5, FR-6, FR-15 rendering; NFR-8, NFR-10.
2. **004-weigh-view-live-readout-and-tolerance:** FR-8, FR-9, FR-10, FR-11, FR-12 rendering; NFR-1, NFR-10.
3. **005-weigh-view-actions-and-function-keys:** FR-7, FR-13 rendering; NFR-8, NFR-9.
4. **008-training-simulation-panel:** DB-4, DB-6, DB-7, DB-8, DB-9.

This bolt also renders story 005/010 (resume) and decisions 2 and 4 of bolt 010.

### APIs

**WeighingMS** (`/station/api/`, unchanged except the added display fields):
- `GET current-session`;
- `GET sessions/<id>/components`, which adds `colour`, `displayMax`, `bar`, `scale.classText`;
- `GET sessions/<id>/progress`;
- `GET sessions/<id>/components/<seq>/evaluation?net=&unit=`, which adds `barPercent`;
- `POST sessions/<id>/components/<seq>/activate | tare | quit | confirm`;
- `POST sessions/<id>/components/<seq>/identity {scanId}`.

**Dummy APIs** (training contracts, called by the browser clients):
- `GET /api/scales/<id>/weight` at 5 Hz;
- `GET /api/scanner/scans/latest`;
- `GET /api/batches/<id>` and `…/recipe`, for the crumb and the recipe name;
- **training only:**
  - `POST /api/training/scales/<id>/simulate` (`dispense` / `overshoot` / `reset` / `set`);
  - `GET /api/training/modes` and `PUT /api/training/modes/<target>`;
  - `POST /api/training/scanner/scans` (Decision 2a).

### Dependencies

- **Bolt 008:** components JSON, identity endpoint, material readiness (ADR-007).
- **Bolt 009:** rules JSON, evaluation endpoint, display resolution (ADR-008, ADR-009).
- **Bolt 010:** progress, current-session, activate / tare / quit / confirm (ADR-010, ADR-011).
- **Bolt 004:** the scale and scanner JS clients and device status.
- **Bolt 007:** the terminal shell, Alpine.js 3.17.5 and the Playwright setup (port 8001, own SQLite file).
- **New packages:** none.

### Technical Approach

- **Code layout:**
  - `weigh.js` holds the View 2 state and handlers, and is merged into `terminal()` (one Alpine component, one screen).
  - All text that comes from the server is rendered as given.
  - Fixed UI labels live in the template, not in JS logic (NFR-11).
- **Readout:**
  - It restarts `watchWeight` whenever the active `scaleId` changes.
  - A reading equal to the last one isn't re-evaluated.
  - A device failure blanks the readout, shows the client's message and disables OK.
- **Function keys:**
  - The `keydown` handler acts only while View 2 is visible and no request is busy.
  - F1 acts only if OK is enabled.
- **Bar:** the bar uses the server's percentages directly as CSS widths and positions.
- **Training panel:**
  - It reads the active component's `scale.scaleId`, `target`, `tolerance.tolerance` and `unit` from the components JSON, so it holds no scenario values.
  - The no-hard-coded-data test covers the new files.

### Decisions for approval

1. **Bar geometry.**
   - **(a) Recommended:** the server returns the bar percentages (band, target line, fill) as Decimals rounded to 0.1 %, so the JS does no maths on quantities.
   - (b) The JS calculates them with `Number` as the prototype does.
2. **Dyestuff scan during training.**
   - **(a) Recommended:** the training panel has a "Simulate scan" field. It is prefilled from the API with the active component's code, and the trainer can edit it to show "Wrong dyestuff" (DB-8). Without it, the demo and the STEP 20 screenshot can only pass the scan step with curl.
   - (b) No scan control; scans only through the API.
3. **Supervisor override key.**
   - **(a) Recommended:** visible and disabled until bolt 013 (STEP 24 decides its behaviour).
   - (b) Copy the prototype's "OVERRIDE REQUESTED — AWAITING SUPERVISOR" text now.
4. **E2E isolation.**
   - **(a) Recommended:**
     - the Playwright web server keeps a pristine copy of the freshly migrated and seeded E2E database;
     - `resetDatabase()` copies it back before each test that needs a clean state, with no open page;
     - it is test-only and adds no reset endpoint to the app.
   - (b) Order-dependent serial specs that share one B-24187 session.

### Acceptance Criteria

- [ ] **Rail:**
  - the rail shows "Recipe · Teal 4C", B-24187, "n of 5 components weighed" and the five rows from the API;
  - touching a pending row activates it;
  - touching a done row sends nothing.
- [ ] **Yellow RGB header:** "Remazol Yellow RGB" and "DYE-4471 · LOT 2026-0387 · CONTAINER C-12 · TARE 214 g".
- [ ] **Scan step:** shown until the identity is verified; a mismatch shows "Wrong dyestuff" and OK stays disabled.
- [ ] **Live readout:** "Weighed now" and the bar follow the Dummy Scale without a reload. The scale is polled every 200 ms or faster (NFR-1).
- [ ] **Yellow RGB panel:**
  - Target 94.0 g;
  - Still to weigh;
  - "TOLERANCE ±0.5 g (93.5 – 94.5)";
  - the band from 93.5 to 94.5 and the target line on a 0 – 125.0 g bar.
- [ ] **Zones:** the readout and bar take the prototype's colours for each zone, and the status line is the server's text, e.g. "DISPENSE — 94.0 g REMAINING".
- [ ] **Floor scale:** Sodium Sulphate shows "Scale selected · 32 kg floor · automatic" and kg.
- [ ] **OK enabled / disabled:** OK · Confirm F1 is disabled at 93.4 g and 94.6 g, and enabled at 93.5 g, 94.0 g and 94.5 g.
- [ ] **Function keys:** F1 / F2 / F4 act exactly like OK / Re-tare / Quit.
- [ ] **Key size:** every action key is at least 57 px.
- [ ] **Five components:** all five confirm in recipe order with "n of 5" advancing, and the scale switches after Yellow RGB.
- [ ] **Reload:** the reload resumes at the in-progress component with the earlier actual weights.
- [ ] **Training panel:**
  - Simulate dispense / Simulate overshoot / Reset set Yellow RGB to 94.2 g / 96.4 g / 0.0 g, and View 2 follows;
  - each failure switch puts its Dummy in failure mode and takes it out again;
  - the panel is marked training-only and sits outside the operator screen.
- [ ] **Checks:** `npm test`, `npm run lint` and `npx playwright test` all pass. The no-hard-coded-data and architecture-boundary tests stay green.
