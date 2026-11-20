---
id: 002-select-batch-view
unit: 007-assisted-weighing-station-ui
intent: 001-assisted-weighing-station
status: complete
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 007-assisted-weighing-station-ui
implemented: true
---

# Story: 002-select-batch-view

## User Story

**As an** operator
**I want** the Select batch screen with the live queue
**So that** I can start a batch by scan or touch

## Requirements

- FR-1, FR-2 (rendering)
- FR-21
- NFR-8, NFR-10

## Acceptance Criteria

- [ ] **Given** the queue API returns 4 batches, **When** view 1 opens, **Then** "Scan a batch card to begin", "Or touch a row below. Queue received from OrgaTEX at hh:mm." and a row per batch (Batch, Order, Machine, Fabric / lot, Shade, Comp., Status) are shown
- [ ] **Given** a row is touched or a card scanned, **When** selection succeeds, **Then** view 2 opens for that batch
- [ ] **Given** selection fails or OrgaTEX is unavailable, **When** the API returns the error, **Then** the message ("Batch not found", "Recipe not available in training data", "OrgaTEX unavailable") is shown

## UI/UX Impact

- View 1 in full
- Matches the prototype `docs/customize-weighing-station.html` (labels, layout, colours, units) for the STEP 28 comparison

## API Dependencies

- Consumes: WeighingMS queue and select-batch endpoints (004)

## Test Expectations

- Playwright STEP 19: rows come from the API; touch and scan open B-24187; error messages

## Technical Notes

- No `const batches` or similar array in templates/JS (workbook STEP 19)

## Dependencies

### Requires
- 004-batch-recipe-management/001-view-batch-queue
- 004-batch-recipe-management/002-select-batch
- 001-terminal-shell-and-status-bar

### Enables
- 007-assisted-weighing-station-ui/009-no-hard-coded-scenario-data

## Out of Scope

- None
