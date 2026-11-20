---
stage: implement
bolt: 007-assisted-weighing-station-ui
created: 2026-11-20T09:46:28Z
---

## Implementation Walkthrough: assisted-weighing-station-ui (shell + View 1)

### Summary

The operator terminal is served at `/`. It reproduces the prototype's device screen:

- the header, with the station, the open batch and the operator;
- an operator choice, shown when no operator is set;
- View 1 · Select batch, with the live queue and touch or scan selection;
- a View 2 skeleton;
- the device status bar, with EN and the clock.

Every value comes from the APIs at runtime. Alpine.js is served locally, and Playwright is set up with its own isolated server for this and the later UI bolts.

### Structure Overview

A new presentation-only Django app, `station`, renders one page. The page carries only configuration: the station name and the CSRF token.

In the browser, an Alpine component holds the view state and talks to the APIs only through the per-integration clients:

- the existing OrgaTEX, device-status, scale, scanner and printer clients;
- the new station-API client.

Selection is decided by the server first (ADR-001). Then the browser reads the batch and recipe from the Dummy OrgaTEX for display, and view 2 opens. The current operator lives in the server session (ADR-005).

### Completed Work

- [x] `src/station/__init__.py`, `src/station/apps.py` - The `station` app (operator terminal; it has no models).
- [x] `src/station/urls.py`, `src/station/views.py` - `GET /` renders the terminal with the configured station name. No scenario data is passed.
- [x] `src/station/templates/station/base.html` - The page frame (wrap, device bezel). It loads the CSS, the integration clients in dependency order and the local Alpine.js, and puts the CSRF token in a meta tag.
- [x] `src/station/templates/station/terminal.html` - The screen:
  - **Header:** brandmark and station; the BATCH · ORDER · MACHINE crumb, only while a batch is open; the operator chip.
  - **Operator choice:** one large button per operator from the API, with a message line.
  - **View 1:** scan prompt with the beam, the "Queue received from OrgaTEX at hh:mm." line, a notice line, and the queue table with the 7 prototype columns and one row per API batch. A row can be touched, or activated with Enter.
  - **View 2:** a skeleton with the recipe name and the component count.
  - **Status strip:** the four devices, ORGATEX, EN and the clock.
  - Test hooks are `data-testid` and `data-batch` / `data-device` attributes.
- [x] `src/station/static/station/station.css` - The prototype's tokens and its device, top bar, view 1, status strip and action-key styles, unchanged in values. Added: a `down` dot state, a `.notice` refusal line, the operator-choice layout, and 57 px queue rows (NFR-8).
- [x] `src/station/static/station/station-client.js` - The only file that knows the `/station/api/` paths:
  - operators: list, current and choose;
  - batch selection and session start.
  - It sends `X-CSRFToken` and reports the server's error code and message.
- [x] `src/station/static/station/terminal.js` - The Alpine component:
  - the clock (1 s) and the device status (`device-status.js`, polled every 1 s);
  - the queue and ORGATEX status, re-read every 10 s;
  - operator load and choice; scan watching while view 1 is shown (batch scans only);
  - the selection flow: server selection → session start → Dummy batch and recipe reads → view 2. A refusal shows the server's message; `OPERATOR_REQUIRED` returns to the operator choice.
  - It holds no data literals and does no arithmetic on quantities.
- [x] `src/station/static/station/vendor/alpine.min.js` - Alpine.js 3.17.5 (the package's `cdn.min.js` build), served locally.
- [x] `src/weighingms/settings.py`:
  - registers `station`;
  - `STATION_NAME`, default "STATION 01", which can be overridden by an environment variable (NFR-13);
  - an optional `WEIGHINGMS_DB_PATH` for the database file. The default is unchanged.
- [x] `src/weighingms/urls.py` - Mounts the terminal at `/`.
- [x] `playwright.config.js` - Chromium. One worker, because the tests share one server and toggle its training modes. HTML report in `playwright-report/`. The web server is a fresh migrated and seeded SQLite file under `playwright/.cache/` (git-ignored), served on port 8001, with the adapter base URLs pointing at it.
- [x] `package.json`, `package-lock.json` - The new devDependencies.

### Key Decisions

- **Server-first selection** (ADR-001): the station API decides and supplies the refusal text. The browser then reads the batch and recipe from the Dummy for display, which gives the two requests T318 expects (`GET /api/batches/B-24187`, then `/recipe`). The UI keeps no message table of its own.
- **One page, view state in Alpine**, as in the prototype. A reload returns to view 1; resume is bolt 010.
- **ORGATEX status from the 10 s queue re-read** (plan Decision 3). Success shows "LINKED hh:mm"; failure shows "UNAVAILABLE", and view 1 shows "OrgaTEX unavailable" instead of the rows, so the queue is never stale. Until the first answer, the state is "CHECKING" (amber dot), never "LINKED".
- **Device states are always spelled out** ("SCANNER · READY", "PRINTER · ERROR"), because story 001 AC 2 asks for each device's current state. The prototype shows the state text only for the scales.
- **The queue Status column shows OrgaTEX's text** (`QUEUED`). The prototype's "WEIGHING" tag is WeighingMS session state and comes with resume.

### Deviations from Plan

- None in scope.
- **View 2 skeleton:** the plan said "recipe name and component count". It shows the recipe name and "N components", using the batch's `componentCount` from the Dummy.

### Dependencies Added

- [x] `@playwright/test` 1.65.1 (devDependency) - The E2E test runner (approved stack). Chromium headless shell v1255 is installed in the user cache (`~/.cache/ms-playwright`), not in the repo.
- [x] `alpinejs` 3.17.5 (devDependency) - The source of the vendored `alpine.min.js`. The runtime uses the copied static file, not `node_modules`.

### Developer Notes

- **Smoke run** (a throwaway Playwright spec, then deleted):
  - choosing the operator works, and the header reads "Operator R. Karim · Shift A";
  - 4 queue rows come from the API;
  - B-24188 shows "Recipe not available in training data";
  - touching B-24187 opens view 2 "Teal 4C", with the crumb "BATCH B-24187 · ORDER SO-9931 · MACHINE JET-04";
  - the status bar reads all READY / "ORGATEX · LINKED hh:mm".
  - Request order: `GET /api/batches`, the operator calls, then `POST /station/api/selections` → `POST /station/api/sessions` → `GET /api/batches/B-24187` → `GET /api/batches/B-24187/recipe`.
- **Dev server:** `GET /` → 200; the served HTML contains no seed values; Alpine.js is served from `/static/`.
- **Checks:** `npm test` 227/227, lint clean, no migrations.
- **Running E2E:** `npx playwright test` starts its own server on 8001, so port 8001 must be free. The dev server on 8000 can keep running.
- **Selecting a batch during STEP 19 evidence on the dev server creates a selection and an open session in the dev DB.** That is the intended behaviour; selecting again returns the same open session.
