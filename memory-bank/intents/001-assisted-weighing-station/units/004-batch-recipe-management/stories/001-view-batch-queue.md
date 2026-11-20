---
id: 001-view-batch-queue
unit: 004-batch-recipe-management
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: null
implemented: false
---

# Story: 001-view-batch-queue

## User Story

**As an** operator
**I want** to see the batches waiting at my station
**So that** I know what to weigh next

## Requirements

- FR-1
- brief FR-01, BR-01, IR-01

## Acceptance Criteria

- [ ] **Given** the seed has run, **When** the queue is requested, **Then** B-24187, B-24188, B-24190, B-24191 are returned with batch, order, machine, fabric/lot, shade, comp. count, status, and the time the queue was received
- [ ] **Given** Dummy OrgaTEX is unavailable, **When** the queue is requested, **Then** an "OrgaTEX unavailable" result is returned instead of an empty or stale list

## UI/UX Impact

- View 1 queue table and "Queue received from OrgaTEX at hh:mm" (rendered by 007)

## API Dependencies

- Consumes: 002 adapter (Dummy `GET /api/batches`)
- Provides: WeighingMS queue endpoint for the UI

## Test Expectations

- Django tests: values from Dummy, unavailable case
- Playwright STEP 19: queue rows come from the API

## Technical Notes

- None

## Dependencies

### Requires
- 002-orgatex-integration/001-read-batches-and-recipe

### Enables
- 004-batch-recipe-management/002-select-batch
- 007-assisted-weighing-station-ui/002-select-batch-view

## Out of Scope

- None
