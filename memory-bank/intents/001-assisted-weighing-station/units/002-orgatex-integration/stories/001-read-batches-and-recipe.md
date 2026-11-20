---
id: 001-read-batches-and-recipe
unit: 002-orgatex-integration
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 003-orgatex-integration
implemented: false
---

# Story: 001-read-batches-and-recipe

## User Story

**As a** WeighingMS (system)
**I want** one adapter that reads the queue, batch details and recipe from (Dummy) OrgaTEX
**So that** only one replaceable module knows the OrgaTEX contract (brief IR-07)

## Requirements

- IR-07, IR-09 (brief)
- Supports FR-1, FR-2, FR-3, FR-21b
- NFR-7

## Acceptance Criteria

- [ ] **Given** Dummy OrgaTEX is seeded, **When** the adapter fetches the queue, B-24187 and its recipe, **Then** it returns typed objects with quantities as `Decimal`
- [ ] **Given** an unknown batch, **When** the adapter fetches it, **Then** it raises a NotFound result, not a generic error
- [ ] **Given** Dummy OrgaTEX is unavailable, **When** any read is made, **Then** it returns an Unavailable result and logs the failure with request details

## UI/UX Impact

- None directly (results drive view 1 and the recipe rail via 004)

## API Dependencies

- Consumes: Dummy OrgaTEX `GET /api/batches`, `GET /api/batches/:batchId`, `GET /api/batches/:batchId/recipe`

## Test Expectations

- Django tests against the running Dummy endpoints (test client / live server): success, NotFound, Unavailable
- Test that no WeighingMS module imports `dummy_*` models

## Technical Notes

- Base URL from settings; floats never used when parsing JSON

## Dependencies

### Requires
- 001-dummy-integrations/002-dummy-orgatex-batch-endpoints
- 001-dummy-integrations/003-dummy-orgatex-recipe-endpoint

### Enables
- 004-batch-recipe-management/001-view-batch-queue

## Out of Scope

- None
