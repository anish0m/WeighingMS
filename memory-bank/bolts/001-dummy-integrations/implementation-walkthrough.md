---
stage: implement
bolt: 001-dummy-integrations
created: 2026-11-20T06:05:12Z
---

## Implementation Walkthrough: dummy-integrations

### Summary

This bolt adds the project skeleton (Django 5.2, SQLite, Ruff, npm scripts) and the Dummy OrgaTEX training contract. A seed command loads the prototype scenario (4 queued batches, recipe "Teal 4C" with 5 pending components, and the two Dummy scales). Four HTTP endpoints serve the batch queue, batch details and recipe, and accept consumption idempotently. The Dummy is a training contract, not the real OrgaTEX interface.

### Structure Overview

The Django project `weighingms` lives under `src/`, and `manage.py` at the root puts `src/` on the Python path. Each Dummy is its own Django app with its own tables:
- `dummy_orgatex`: models, endpoints, seed;
- `dummy_scale`: models only in this bolt.

Views are thin. They parse the request, call `services.py` and map service exceptions to the standard JSON error body. The seed values live in one data module copied from the prototype; services turn them into `Decimal` values.

### Completed Work

- [x] `requirements.txt` - Python dependencies: Django 5.2 LTS and Ruff
- [x] `package.json` - npm scripts `dev` (runserver on port 8000), `test` (Django tests in `tests/`), `lint` (Ruff check + format check)
- [x] `pyproject.toml` - Ruff settings: line length 88, default rules plus import sorting; migrations excluded
- [x] `manage.py` - Django entry point; adds `src/` to the path
- [x] `src/weighingms/settings.py` - Local training settings: SQLite `db.sqlite3`, UTC with `USE_TZ`, the two Dummy apps, console logging
- [x] `src/weighingms/urls.py` - Mounts the Dummy OrgaTEX endpoints under `/api/`
- [x] `src/weighingms/wsgi.py`, `src/weighingms/asgi.py` - Server entry points
- [x] `src/dummy_orgatex/models.py` - Batch, recipe, recipe component, consumption and consumption line tables; quantities are `decimal(12,4)`
- [x] `src/dummy_orgatex/seed_data.py` - Queue rows and the Teal 4C components copied from the prototype, quantities as strings
- [x] `src/dummy_orgatex/services.py` - Seed/reset, batch and recipe lookup, consumption validation and idempotent storage, domain exceptions
- [x] `src/dummy_orgatex/views.py` - JSON endpoints and the standard error body; CSRF-exempt because the browser calls the Dummy directly
- [x] `src/dummy_orgatex/urls.py` - Routes for `batches`, `batches/<id>`, `batches/<id>/recipe`, `batches/<id>/consumption`
- [x] `src/dummy_orgatex/management/commands/seed_training.py` - `python manage.py seed_training` loads or resets the scenario
- [x] `src/dummy_orgatex/migrations/0001_initial.py` - Initial Dummy OrgaTEX schema
- [x] `src/dummy_orgatex/apps.py`, `src/dummy_scale/apps.py` - App configs labelled as training contracts
- [x] `src/dummy_scale/models.py` - Dummy scale table (id, name, capacity, unit, net weight, status)
- [x] `src/dummy_scale/migrations/0001_initial.py` - Initial Dummy Scale schema
- [x] `tests/__init__.py`, `tests/dummy_orgatex/__init__.py`, `tests/dummy_scale/__init__.py` - Test packages; the test modules come in the Test stage
- [x] `.gitignore` - `pycache/` corrected to `__pycache__/` (approved with the plan)

### Key Decisions

- **Consumption lines in their own table**: each post stores one row per component, so the read-back and later evidence show exactly what was posted.
- **Quantities accepted only as decimal strings**: JSON numbers would be floats. They are rejected with `VALIDATION_ERROR` (NFR-16, coding standards).
- **Decimal output keeps the stored precision**: quantities come back as `decimal(12,4)` strings (for example `"94.0000"`), equal to the prototype values as `Decimal`. Display formatting (1 decimal for g, 3 for kg) belongs to the UI bolts.
- **Idempotency key is unique across batches**: reusing a key on another batch returns `409 IDEMPOTENCY_KEY_CONFLICT`. A repeat on the same batch returns the original record with `duplicate: true`.
- **Consumption is validated against the recipe**: every component code must belong to the batch's recipe, appear once, and use the recipe unit. A batch without a recipe returns `RECIPE_NOT_AVAILABLE`.
- **Model choices and ordering use tuples**: this is the Django convention and satisfies Ruff rule RUF012 (mutable class attributes).

### Deviations from Plan

- **Added `DummyConsumptionLine`**: the plan listed only `DummyConsumption`. The second table stores the per-component lines.
- **Added `409 IDEMPOTENCY_KEY_CONFLICT`**: the plan did not cover a key reused on another batch.
- **Added a `state` field to each recipe component in the recipe response** (`pending`): it comes from OQ-6.

### Dependencies Added

- [x] `Django 5.2.19` - Web framework (approved stack)
- [x] `ruff 0.17.6` - Formatter and linter (coding standards)

### Developer Notes

- Run `.venv/bin/python manage.py migrate` and then `.venv/bin/python manage.py seed_training` before `npm run dev`. Re-running the seed resets all Dummy state, including stored consumptions.
- `ALLOWED_HOSTS` is `localhost` and `127.0.0.1`. The Django test runner adds `testserver` itself.
- Verified during Implement:
  - `manage.py check` reports no issues;
  - `makemigrations --check` detects no changes;
  - seeding twice gives 4 batches, 5 components and 2 scales;
  - all endpoints were smoke-checked;
  - `npm run dev` answered `GET /api/batches` with 200;
  - `ruff check` and `ruff format --check` pass.
