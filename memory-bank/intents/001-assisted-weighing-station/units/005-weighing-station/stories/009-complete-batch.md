---
id: 009-complete-batch
unit: 005-weighing-station
intent: 001-assisted-weighing-station
status: complete
priority: must
created: 2026-11-20T04:51:01.000Z
assigned_bolt: 015-weighing-station
implemented: true
---

# Story: 009-complete-batch

## User Story

**As an** operator
**I want** the batch to complete when all components are confirmed
**So that** consumption is posted and the ticket can be printed

## Requirements

- FR-16
- brief §6.2, FR-25

## Acceptance Criteria

- [ ] **Given** 5 of 5 confirmed, **When** the last confirmation is saved, **Then** the batch completes with components 5 of 5, all within YES/NO, total dispensed in kg, elapsed time, operator
- [ ] **Given** the prototype actuals 1241.5 g, 385.4 g, 94.2 g, 23.980 kg, 9.621 kg, **When** the total is computed, **Then** it is 35.322 kg (Decimal)
- [ ] **Given** 4 of 5 confirmed, **When** completion is requested, **Then** it is refused
- [ ] **Given** the batch completes, **When** completion is saved, **Then** write-back (002) is triggered

## UI/UX Impact

- View 3 summary values

## API Dependencies

- Consumes: 002 write-back
- Provides: WeighingMS weighing-session API for the UI (shape fixed in Bolt design)

## Test Expectations

- Django tests: total 35.322 kg; refusal at 4 of 5; write-back triggered

## Technical Notes

- None

## Dependencies

### Requires
- 008-progress-components
- 002-orgatex-integration/002-post-consumption-idempotently

### Enables
- 006-ticket-printing/001-print-weighing-ticket
- 007-assisted-weighing-station-ui/007-confirm-and-print-view

## Out of Scope

- None
