---
stage: plan
bolt: 007-assisted-weighing-station-ui
created: 2026-11-20T09:38:35Z
---

## Implementation Plan: assisted-weighing-station-ui (shell + View 1)

### Objective

This is the first UI bolt. It builds the operator terminal at `http://localhost:8000/`. It reproduces the prototype's device screen (`docs/customize-weighing-station.html`):

- the **header**, with the station, the open batch and the operator;
- the **status bar**, with the device states, EN and the clock;
- **View 1 · Select batch**, with the scan prompt and the live queue.

Every value on screen comes from an API at runtime, and the UI computes no business rule (FR-21). It also sets up the two pieces of tooling the later UI bolts reuse: **Alpine.js served locally** and **Playwright**.

### Deliverables

1. **New WeighingMS app `station`** (unit 007, presentation only; it has no models):
   - `GET /` renders `station/terminal.html`.
   - The view passes only configuration:
     - the station name from the setting `STATION_NAME = "STATION 01"` (NFR-13);
     - the CSRF token in a `<meta>` tag.
   - It passes no scenario data.
2. **Templates**:
   - `station/base.html`: the device frame;
   - `station/terminal.html`, which holds:
     - **Header (`.topbar`):**
       - "WeighingMS STATION 01";
       - the crumb "BATCH … · ORDER … · MACHINE …", only while a batch is open;
       - the operator chip "Operator R. Karim · Shift A".
     - **Operator choice:** shown while the station has no operator (story 005/001 AC 1). It lists the operators from `GET /station/api/operators` as large touch buttons. The prototype only shows the result in the header, so this panel is styled in the prototype's look.
     - **View 1 (`#v-queue`):**
       - "Scan a batch card to begin" with the scan beam;
       - "Or touch a row below. Queue received from OrgaTEX at hh:mm." The time is the Dummy's `receivedAt`, in local time;
       - the queue table: Batch, Order, Machine, Fabric / lot, Shade, Comp., Status, one row per API batch;
       - an error line for refusals.
     - **View 2 (`#v-weigh`), skeleton only:** it opens on a successful selection and shows the selected batch's recipe name and component count from the API. The full weigh view is bolt 011 (Decision 2).
     - **Status bar (`.strip`):**
       - SCALE 3 kg, SCALE 32 kg, SCANNER, PRINTER, ORGATEX, each with a coloured dot and its state;
       - EN;
       - the clock `hh:mm:ss`.
3. **Static files** (in `station/static/station/`):
   - `station.css`: the prototype's CSS for the device screen, header, view 1 and the status strip, with the same colour variables, fonts and sizes. The prototype's meeting-only parts are left out: the "Screen" switcher bar, the simulate buttons, the question pins and the notes (Decision 1). The view 2/3 styles come in bolts 011/017.
   - `station-client.js`: the only JS file that knows the `/station/api/` paths:
     - `listOperators`, `currentOperator`, `chooseOperator`;
     - `selectBatch(batchId, method)`;
     - `startSession(selectionId)`.
     - It sends `X-CSRFToken` from the meta tag, and on a refusal it throws the server's `error.code` / `error.message`.
   - `terminal.js`: the Alpine component `terminal()`, holding view state only:
     - the current view, operator, queue, open batch and recipe, device states, clock, and error message;
     - it uses the existing clients `orgatex-client.js`, `device-status.js`, `scanner-client.js`, `scale-client.js`, `printer-client.js` and the new `station-client.js`.
   - `vendor/alpine.min.js`: Alpine.js 3.x, copied from the npm package `alpinejs` (`dist/cdn.min.js`) and served by Django. There is no CDN.
4. **Selection flow** (stories 007/002 AC 2–3, ADR-001):
   1. The operator touches a row (`method: "touch"`), or a batch card is scanned. `scanner.watchScans` runs while view 1 is shown; a scan of `kind: "batch"` uses `method: "scan"`.
   2. `POST /station/api/selections`. The server decides; on a refusal, its `error.message` is shown on view 1 ("Batch not found", "Recipe not available in training data", "OrgaTEX unavailable", "Batch not released") and nothing opens.
   3. On `201`, `POST /station/api/sessions` with the `selectionId`. On `403 OPERATOR_REQUIRED`, the operator choice is shown again.
   4. The browser reads `GET /api/batches/<id>` and then `GET /api/batches/<id>/recipe` from the Dummy through `orgatex-client.js`, for display (ADR-001; these are the two requests T318 shows).
   5. View 2 opens, and the header crumb shows BATCH / ORDER / MACHINE.
5. **Status bar behaviour** (story 001 AC 2–3):
   - The devices come from `device-status.js`, which polls every 1 s, so a failure shows within 2 s. The label is "· READY" only when the state is `ready`, and "· DISCONNECTED", "· UNAVAILABLE" or "· ERROR" otherwise, with the dot changing from `up` to `down`. An unknown answer is never shown as READY; the client already maps it to `unavailable`.
   - **ORGATEX** (Decision 3) is re-checked every 10 s by re-reading the queue. That refreshes the rows and "received at" on view 1 (the "live queue"):
     - success → "ORGATEX · LINKED hh:mm", as in the prototype;
     - failure → "ORGATEX · UNAVAILABLE", and view 1 shows "OrgaTEX unavailable" instead of the rows. The rows are never left empty or stale.
6. **Playwright setup**:
   - `@playwright/test` and `alpinejs` are added as npm devDependencies, and Chromium is installed with `npx playwright install chromium`. I run these in Implement; they need network access.
   - `playwright.config.js` at the root, with the report in `playwright-report/`. Its `webServer` runs a separate E2E server on port **8001** with its own SQLite file `playwright/.cache/e2e.sqlite3`, which is already git-ignored. It runs `migrate` and `seed_training` before `runserver`. The adapter base URLs are pointed at 8001 through the existing environment settings.
   - This way the E2E runs never touch the dev database or the dev server on 8000.
   - `npx playwright test` works as agreed in CLAUDE.md.
   - `src/weighingms/settings.py` gains an optional `WEIGHINGMS_DB_PATH` environment variable; the default stays `db.sqlite3`.
7. **Wiring**:
   - `settings.py`: add `station` and `STATION_NAME`;
   - `urls.py`: `path("", include("station.urls"))`.

### Dependencies

- **Bolt 003 `orgatex-client.js`**: queue, batch and recipe reads from the Dummy OrgaTEX in the browser.
- **Bolt 004 device clients**: `device-status.js` (status polling), `scanner-client.js` (`watchScans`), and the scale and printer clients for their status.
- **Bolt 005**: `POST /station/api/selections` (the authority) and its refusal messages.
- **Bolt 006**: `GET /station/api/operators`, `GET` and `PUT /station/api/operator`, `POST /station/api/sessions`, `403 OPERATOR_REQUIRED`.
- **Training controls**: `PUT /api/training/modes/<target>` and `POST /api/training/scanner/scans`, used by the Playwright tests only. The UI's training panel is bolt 011.
- **New packages**: `alpinejs` 3.x (vendored static file), `@playwright/test` (devDependency) and its Chromium.

### Technical Approach

- **One page with three views**, switched with Alpine state, as in the prototype; there are no page reloads between views. A browser reload returns to view 1. Resuming an open batch after a reload is story 005/010 (bolt 010).
- **The JS does no arithmetic and holds no data**:
  - counts and quantities are shown exactly as the API strings;
  - the queue status is OrgaTEX's `status` text (`QUEUED`). The prototype's "WEIGHING" tag is WeighingMS session state and comes with resume (bolt 010);
  - there is no `batches` / `components` array literal in the templates or JS (workbook STEP 19, FR-21, story 009).
- **Boundary rules stay green**:
  - Dummy paths stay only in their owning client files; `station-client.js` knows only `/station/api/`;
  - the `station` app imports no `dummy_*` module.
- **Fidelity (NFR-10)**: the class names and structure follow the prototype (`.screen`, `.topbar`, `.brandmark`, `.crumb`, `.op-chip`, `.queue`, `.scan-prompt`, `table.q`, `.tag`, `.strip`, `.stat`, `.dot`). Touch rows and buttons are at least 57 px (NFR-8). All text is in English (NFR-11).
- **Clock**: the browser's local time, ticking every second, `hh:mm:ss`.

### Acceptance Criteria

**001-terminal-shell-and-status-bar**
- [ ] On every view, the header shows "WeighingMS STATION 01" and "Operator R. Karim · Shift A". After a batch opens, it also shows "BATCH B-24187 · ORDER SO-9931 · MACHINE JET-04". The clock ticks.
- [ ] The status bar shows SCALE 3 kg, SCALE 32 kg, SCANNER, PRINTER, ORGATEX with their current state, plus EN.
- [ ] With the Dummy scanner, a scale or the printer toggled into failure, the label changes within 2 s and is never READY. It returns to READY when restored.

**002-select-batch-view**
- [ ] View 1 shows "Scan a batch card to begin", "Or touch a row below. Queue received from OrgaTEX at hh:mm." and 4 rows (B-24187, B-24188, B-24190, B-24191) with all 7 columns, from `GET /api/batches`.
- [ ] Touching B-24187, or scanning B-24187, opens view 2 for that batch (header crumb and recipe "Teal 4C").
- [ ] B-24188 → "Recipe not available in training data"; scanning B-99999 → "Batch not found"; OrgaTEX unavailable → "OrgaTEX unavailable". In each case view 1 stays.

**005/001 (UI part, deferred from bolt 006)**
- [ ] With no operator chosen, the operator choice is shown first, and the header shows the operator after the choice.

**Bolt / STEP 19**
- [ ] The Network tab shows `GET /api/batches`, then on touch `GET /api/batches/B-24187` and `GET /api/batches/B-24187/recipe` (T317–T318).
- [ ] No hard-coded batch or recipe data in the templates or JS (T327).

### Tests (Test stage)

- **Playwright** (`playwright/` specs, Chromium):
  - **shell:** header values; operator choice → header; clock ticks; status bar labels;
  - **status:** toggling the scanner, `scale-3kg` and the printer to failure changes the label within 2 s, and back to READY;
  - **select-batch:**
    - the rows come from the API (the Dummy's values, and the request is seen with `page.waitForResponse`);
    - touch B-24187 → view 2, with the request order;
    - scan B-24187 → view 2;
    - B-24188, B-99999 and OrgaTEX unavailable each show their message.
- **Django** (`tests/station/`):
  - `GET /` → 200 with "STATION 01", the CSRF meta tag and the local Alpine script;
  - Alpine.js is served from static, not a CDN;
  - **the no-hard-coded-data check:** the templates and the station JS/CSS contain no seed values (`B-24187`, `SO-9931`, `JET-04`, `Teal 4C`, `Remazol`, `R. Karim`) and no `const batches` / `components` arrays;
  - the existing boundary tests also cover `station`.
- **Evidence (after the bolt, STEP 19):** the user's screenshots T315–T325.

### Decisions for the Human Checkpoint

1. **Prototype parts that are not part of the terminal:**
   - **Recommended: leave out** the "Screen" switcher bar, the simulate/reset buttons, the question pins and the meeting notes. They are discussion aids around the mockup, not the station UI. The training simulation panel is a separate story (008, bolt 011).
   - *Alternative:* keep the pins as hover hints.
2. **View 2 in this bolt:**
   - **Recommended: a skeleton** that opens for the selected batch and shows its recipe name and component count from the API. The recipe rail, readout and actions are bolt 011.
   - *Alternative:* stay on view 1 and only show "B-24187 opened", which wouldn't satisfy "view 2 opens".
3. **ORGATEX status:**
   - **Recommended: re-check every 10 s by re-reading the queue** (`GET /api/batches`). Success → "LINKED hh:mm"; failure → "UNAVAILABLE". This also keeps the queue live on view 1. The 2 s rule (FR-20) applies to the devices, which poll every 1 s.
   - *Alternative:* poll every 1–2 s like the devices. That floods the Network tab used for the STEP 19 evidence.
4. **E2E isolation:**
   - **Recommended: Playwright starts its own server on port 8001 with a separate, freshly migrated and seeded SQLite file**, so test runs never change the dev database or the modes on the dev server.
   - *Alternative:* run against the dev server on 8000. That is simpler, but the tests toggle failure modes and create selections in your dev data.
5. **Installing packages:**
   - **Recommended: I run `npm install --save-dev @playwright/test alpinejs` and `npx playwright install chromium` in Implement.** That changes `package.json` and adds `package-lock.json`, which should be committed.
   - *Alternative:* you run them yourself before Implement.
