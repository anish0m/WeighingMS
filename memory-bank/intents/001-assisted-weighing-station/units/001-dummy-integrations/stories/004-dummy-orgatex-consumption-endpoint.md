---
id: 004-dummy-orgatex-consumption-endpoint
unit: 001-dummy-integrations
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 001-dummy-integrations
implemented: false
---

# Story: 004-dummy-orgatex-consumption-endpoint

## User Story

**As a** WeighingMS (system)
**I want** to post actual consumption for a completed batch to Dummy OrgaTEX
**So that** the write-back flow can be demonstrated end to end

## Requirements

- DB-3
- Supports FR-17

## Acceptance Criteria

- [ ] **Given** a valid payload with idempotency key K, **When** `POST /api/batches/B-24187/consumption` is called, **Then** the consumption is stored and success is returned with the acceptance time
- [ ] **Given** K was already accepted, **When** the same post is repeated, **Then** success is returned and no second consumption record exists
- [ ] **Given** a malformed payload, **When** it is posted, **Then** a validation error is returned and nothing is stored

## UI/UX Impact

- None directly (drives "Written to OrgaTEX CONFIRMED hh:mm:ss" on view 3 through 002)

## API Dependencies

- Provides: `POST /api/batches/:batchId/consumption` (+ a read-back endpoint for tests, shape fixed in Bolt design)

## Test Expectations

- Django API tests: accept, duplicate key, invalid payload
- Workbook STEP 26 evidence uses this endpoint

## Technical Notes

- Training contract only: not a claim about the real OrgaTEX / device interface (A-01…A-15 stay unresolved).

## Dependencies

### Requires
- 001-seed-training-scenario

### Enables
- 002-orgatex-integration/002-post-consumption-idempotently

## Out of Scope

- None
