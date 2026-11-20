---
id: 002-select-batch
unit: 004-batch-recipe-management
intent: 001-assisted-weighing-station
status: complete
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 005-batch-recipe-management
implemented: true
---

# Story: 002-select-batch

## User Story

**As an** operator
**I want** to open a batch by scanning its card or touching its row
**So that** weighing starts on the right batch

## Requirements

- FR-2
- OQ-5
- brief FR-02–FR-04, BR-02, BR-03, AC-01

## Acceptance Criteria

- [ ] **Given** the queue is shown, **When** B-24187 is scanned or touched, **Then** B-24187 opens and the header shows batch, order and machine
- [ ] **Given** an unknown code, **When** it is scanned, **Then** "Batch not found" is shown and nothing opens
- [ ] **Given** B-24188 (no recipe in training data), **When** it is touched, **Then** "Recipe not available in training data" is shown and nothing opens

## UI/UX Impact

- View 1 → view 2 transition; header line "BATCH … · ORDER … · MACHINE …"

## API Dependencies

- Consumes: 002 adapter, 003 scanner adapter
- Provides: WeighingMS select-batch endpoint

## Test Expectations

- Django tests: open, not found, not selectable
- Playwright STEP 19: touch and scan selection

## Technical Notes

- None

## Dependencies

### Requires
- 001-view-batch-queue
- 003-device-integration/003-scanner-input

### Enables
- 004-batch-recipe-management/003-load-read-only-recipe
- 007-assisted-weighing-station-ui/002-select-batch-view

## Out of Scope

- None
