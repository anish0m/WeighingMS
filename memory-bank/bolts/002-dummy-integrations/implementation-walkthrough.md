---
stage: implement
bolt: 002-dummy-integrations
created: 2026-11-20T06:53:02Z
---

## Implementation Walkthrough: dummy-integrations

### Summary

This bolt completes the Dummy layer:
- **Dummy Scale:** read weight and status, tare, and training simulate controls.
- **Dummy Scanner and Dummy Printer:** new apps; scans and tickets are stored and read back.
- **Failure modes:** each Dummy can be switched into its failure mode and back. While OrgaTEX is unavailable, every Dummy OrgaTEX endpoint returns 503.

All of these are training contracts, not real device or OrgaTEX interfaces.

### Structure Overview

Each Dummy is its own Django app with its own tables and failure state (DB-10): `dummy_orgatex`, `dummy_scale`, `dummy_scanner`, `dummy_printer`.
- **Contract endpoints** are mounted under `/api/`.
- **Training-only controls** (simulate, scan, failure modes) are mounted under `/api/training/`, so they are clearly separate from what WeighingMS integrates with.
- **Shared JSON helpers** live in `weighingms/api.py`: error body, body parsing, decimal-string parsing.
- **`weighingms/training.py`** only dispatches mode changes to each Dummy's own service.
- **`seed_training`** is still the single reset for all four Dummies.

### Completed Work

- [x] `src/weighingms/api.py` - Shared helpers: standard error body, JSON body reading, decimal-string parsing that rejects floats
- [x] `src/weighingms/training.py` - Lists all failure modes and dispatches a mode change to the right Dummy
- [x] `src/weighingms/urls.py` - Mounts the four Dummy APIs under `/api/` and the training controls under `/api/training/`
- [x] `src/weighingms/settings.py` - Registers `dummy_scanner` and `dummy_printer`
- [x] `src/dummy_scale/models.py` - Adds the `disconnected` status and the reading time
- [x] `src/dummy_scale/services.py` - Seeding, reading, tare, simulate (dispense, overshoot, reset, set), capacity and unit checks, mode switch; Decimal only
- [x] `src/dummy_scale/views.py`, `src/dummy_scale/urls.py` - Scale list, status, weight and tare endpoints, plus the simulate view
- [x] `src/dummy_scale/migrations/0002_*.py` - Status choices and reading time
- [x] `src/dummy_scanner/` (`apps`, `models`, `services`, `views`, `urls`, migration `0001`) - Simulated batch/dyestuff scans, latest scan, scanner status and failure mode
- [x] `src/dummy_printer/` (`apps`, `models`, `services`, `views`, `urls`, migration `0001`) - Stores tickets unchanged and returns them by ID, printer status and failure mode
- [x] `src/dummy_orgatex/models.py` and migration `0002` - OrgaTEX failure state (single row)
- [x] `src/dummy_orgatex/views.py` - 503 `ORGATEX_UNAVAILABLE` guard on every OrgaTEX endpoint; uses the shared helpers
- [x] `src/dummy_orgatex/services.py` - OrgaTEX mode; seeding now also resets scales, scanner, printer and every failure mode
- [x] `src/dummy_orgatex/seed_data.py` - `scale-3kg` reports in g with capacity 3000 (Decision 1)
- [x] `tests/dummy_scale/test_seed.py` - The bolt-001 capacity test now checks capacity and unit per scale (Decision 1)

### Key Decisions

- **Scale units (Decision 1, approved):** `scale-3kg` reports in g and `scale-32kg` in kg, matching the prototype's components. Simulate requests must use the scale's unit; nothing is converted.
- **Training controls under `/api/training/`:** simulate, scanner input and failure modes are not part of any integration contract, and are easy to remove with the Dummies.
- **Failure behaviour returns 503 with a specific code:**
  - `ORGATEX_UNAVAILABLE`, `SCALE_DISCONNECTED`, `SCANNER_UNAVAILABLE`, `PRINTER_ERROR`;
  - nothing is stored while a Dummy is failing;
  - a disconnected scale's `/status` still answers 200 with `disconnected`, so the status bar can show it.
- **Simulated weight cannot exceed the scale's capacity:** a request over capacity is rejected with 400.
- **Ticket content is stored unchanged:** WeighingMS will supply the content (bolt 016). The printer only stores and returns it.

### Deviations from Plan

- **Added a reading time** (`readAt`) to the scale weight response, so a reading can be identified.
- **Moved `parse_decimal_string` to the shared `weighingms/api.py`** with its own `InvalidQuantity` exception. Dummy OrgaTEX now uses it too, with no change in behaviour.

### Dependencies Added

None.

### Developer Notes

- After pulling, run `.venv/bin/python manage.py migrate` and then `.venv/bin/python manage.py seed_training`.
- Verified during Implement:
  - `manage.py check` is clean and `makemigrations --check` finds no changes;
  - `npm run lint` passes;
  - bolt 001's 31 tests pass.
- Smoke-checked:
  - `/api/scales` lists both scales;
  - dispense → 94.2000, overshoot → 96.4000, tare → 0.0000;
  - a disconnected scale gives weight 503 and status `disconnected`;
  - OrgaTEX unavailable gives `/api/batches` 503;
  - a scan becomes the latest scan;
  - a ticket is stored and read back.
