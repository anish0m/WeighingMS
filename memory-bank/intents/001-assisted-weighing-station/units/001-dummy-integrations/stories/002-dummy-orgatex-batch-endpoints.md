---
id: 002-dummy-orgatex-batch-endpoints
unit: 001-dummy-integrations
intent: 001-assisted-weighing-station
status: complete
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 001-dummy-integrations
implemented: true
---

# Story: 002-dummy-orgatex-batch-endpoints

## User Story

**As a** WeighingMS (system)
**I want** to read the released batch queue and a batch's details from Dummy OrgaTEX over HTTP
**So that** the station never needs batch data hard-coded

## Requirements

- DB-1, DB-10
- Supports FR-1, FR-2, FR-21

## Acceptance Criteria

- [ ] **Given** the seed has run, **When** `GET /api/batches` is called, **Then** it returns the 4 seeded batches with batch, order, machine, fabric/lot, shade, component count, status and the queue received time
- [ ] **Given** the seed has run, **When** `GET /api/batches/B-24187` is called, **Then** it returns B-24187's details
- [ ] **Given** an unknown ID, **When** `GET /api/batches/B-99999` is called, **Then** it returns 404 in the standard error format

## UI/UX Impact

- None directly (feeds view 1 queue through 002/004)

## API Dependencies

- Provides: `GET /api/batches`, `GET /api/batches/:batchId` (workbook STEP 16 minimum; exact JSON shape fixed in the Bolt design)

## Test Expectations

- Django API tests for 200 and 404
- curl evidence `STEP-18-api-tests.txt` (workbook STEP 18)

## Technical Notes

- Training contract only: not a claim about the real OrgaTEX / device interface (A-01…A-15 stay unresolved).

## Dependencies

### Requires
- 001-seed-training-scenario

### Enables
- 001-dummy-integrations/007-dummy-failure-toggles
- 002-orgatex-integration/001-read-batches-and-recipe

## Out of Scope

- Station filtering, status changes (brief IR-06 not built)
