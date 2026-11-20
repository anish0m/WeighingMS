---
id: 004-printer-adapter
unit: 003-device-integration
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 004-device-integration
implemented: false
---

# Story: 004-printer-adapter

## User Story

**As a** WeighingMS (system)
**I want** to submit a ticket to the printer and know whether it printed
**So that** a ticket is never reported as printed when it was not

## Requirements

- Supports FR-18
- FR-20 (c)
- IR-16 (brief)

## Acceptance Criteria

- [ ] **Given** the printer is ready, **When** a ticket is submitted, **Then** the printed ticket ID is returned
- [ ] **Given** the printer is in error, **When** a ticket is submitted, **Then** a PrinterError is returned

## UI/UX Impact

- View 3 Print ticket result; PRINTER status

## API Dependencies

- Consumes: Dummy Printer `POST /api/tickets`

## Test Expectations

- Django tests: print ok, printer error

## Technical Notes

- None

## Dependencies

### Requires
- 001-dummy-integrations/006-dummy-scanner-and-printer

### Enables
- 003-device-integration/005-device-status-and-fail-safe
- 006-ticket-printing/001-print-weighing-ticket

## Out of Scope

- None
