# Tech Stack

## Overview
Core technology decisions for this project.

WeighingMS is a single-station, server-rendered web application. A Django monolith hosts both the operator terminal UI (a reproduction of `docs/customize-weighing-station.html`) and the training-time Dummy APIs that substitute for OrgaTEX, the scales, the scanner and the printer. The stack fits the brief's V1 scope (one station, one site, A-11), keeps every external integration behind an HTTP API boundary (IR-07), and runs locally without external services.

Status: **Approved** by the user on 2026-11-19 (STEP 4.5, `APPROVE TECH STACK`).

## Languages
- **Python 3.12**: application, domain logic, Dummy APIs, unit and API tests.
- **JavaScript (browser, ES2020+)**: UI interactivity through Alpine.js only. No transpilation or bundling step.
- **JavaScript (Node.js 18+; v24 on the development machine)**: tooling only (specs.md CLI/dashboard and Playwright). Node is not part of the application runtime.

Rationale: Python and Django give a batteries-included backend (ORM, test runner, templating) with little setup, which suits a training product built in Bolts. Quantities must use Python `decimal.Decimal`, never `float` (brief NFR-16). This is enforced in coding standards.

## Framework
- **Backend**: Django (5.2 LTS), serving both HTML pages and JSON endpoints.
- **Frontend**: Django templates + HTML/CSS + **Alpine.js 3.x**, reproducing the three prototype views (1 · Select batch, 2 · Weigh, 3 · Confirm & print) and the HMI visual design.
- **Dummy integrations**: Django views exposing training-contract JSON APIs (Dummy OrgaTEX, Dummy Scale, Dummy Scanner, Dummy Printer). The UI consumes them over HTTP like real external services. No scenario data is hard-coded in templates or JS.

Rationale:
- Server-rendered templates with Alpine.js reproduce the prototype's interactions (live readout, tolerance zones, scale switching, component progression) without a SPA build chain.
- Hosting the Dummy APIs in the same Django project keeps the training setup to one process while preserving the integration boundary required by the brief (IR-07) and the requirement PDF §9 ("mock APIs separate from business logic").
- Alpine.js is served as a **local static file** (no CDN), because the station must keep working without network access (brief BR-16, NFR-03).

## Authentication
**TBD (decided during Inception).**

The brief requires operator identification (FR-34) and supervisor authentication for overrides (FR-35), but the brief leaves the method open (A-09, brief Q37). If the approved Requirements need it, Django's built-in `django.contrib.auth` is the default candidate. No external auth provider is used.

## Infrastructure & Deployment
**Local development server only (training product).**

- `npm run dev` starts the app at `http://localhost:8000` via `.venv/bin/python manage.py runserver`.
- **Database**: SQLite (file database, git-ignored). Details belong to the data-stack standard.
- No cloud, container or production deployment is in scope for this training implementation. The real station hardware and network (brief D-03, D-04) are outside the project.

## Package Manager
- **Python**: `pip` with `requirements.txt`, inside a virtualenv at `.venv/`.
- **Node.js**: `npm` with `package.json` (dev tooling, Playwright, and the `dev`/`test` scripts).

## Testing
- **Unit and API tests**: Django test runner. Python tests live in `tests/`. Run them with `npm test`.
- **End-to-end tests**: Playwright (`@playwright/test`). Tests live in `playwright/`, the config is `playwright.config.js` at the project root, and the HTML report goes to `playwright-report/`. Run them with `npx playwright test`.

## Project Layout
```
src/                  # Django project and apps (application + Dummy APIs)
tests/                # Django unit/API tests
playwright/           # Playwright E2E tests
playwright.config.js  # Playwright config
package.json          # npm scripts: dev, test
requirements.txt      # Python dependencies
pyproject.toml        # Ruff config (see coding-standards.md)
manage.py             # Django entry point (used by npm run dev)
memory-bank/          # AI-DLC artifacts
```

## Decision Relationships
- Django + SQLite + Django ORM form one coherent persistence path with no external database service.
- The Dummy APIs live in Django, so they share the dev server and test runner, but the UI must reach them only over HTTP endpoints. This keeps them replaceable by real integrations later (IR-07).
- Playwright (Node) tests the running Django app end to end. Node is tooling only, so the Python runtime has no Node dependency.
- Serving Alpine.js locally plus SQLite means the app runs fully offline, which matches the continuity requirements (BR-16, NFR-03).
