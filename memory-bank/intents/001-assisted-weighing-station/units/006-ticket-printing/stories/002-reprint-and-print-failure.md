---
id: 002-reprint-and-print-failure
unit: 006-ticket-printing
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 016-ticket-printing
implemented: false
---

# Story: 002-reprint-and-print-failure

## User Story

**As an** operator
**I want** to reprint a ticket and be told when printing failed
**So that** a missing ticket can always be produced and never assumed printed

## Requirements

- FR-18 (c, d)
- FR-20 (c)
- brief FR-28

## Acceptance Criteria

- [ ] **Given** a ticket was printed, **When** Print ticket is pressed again, **Then** the new ticket is marked "REPRINT"
- [ ] **Given** the Dummy Printer is in error, **When** Print ticket is pressed, **Then** failure is shown and nothing is marked printed
- [ ] **Given** the printer is restored, **When** Print ticket is pressed, **Then** printing succeeds
- [ ] **Given** any print outcome, **When** the batch is inspected, **Then** the completed batch and its records are unchanged

## UI/UX Impact

- View 3 print failure message, REPRINT marker in preview

## API Dependencies

- Consumes: 003 printer adapter + Dummy Printer toggle

## Test Expectations

- Django tests: reprint marker, error, recovery
- Playwright STEP 30 printer failure

## Technical Notes

- None

## Dependencies

### Requires
- 001-print-weighing-ticket
- 001-dummy-integrations/007-dummy-failure-toggles

### Enables
- 007-assisted-weighing-station-ui/007-confirm-and-print-view

## Out of Scope

- None
