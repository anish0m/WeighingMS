---
id: 001-print-weighing-ticket
unit: 006-ticket-printing
intent: 001-assisted-weighing-station
status: complete
priority: must
created: 2026-11-20T04:51:01.000Z
assigned_bolt: 016-ticket-printing
implemented: true
---

# Story: 001-print-weighing-ticket

## User Story

**As an** operator
**I want** to print a ticket for the completed batch
**So that** the containers travel to the machine with a record of what was weighed

## Requirements

- FR-18 (a, b)
- brief FR-27, BR-15, IR-16, AC-10, A-04

## Acceptance Criteria

- [ ] **Given** B-24187 is complete, **When** Print ticket (F1) is pressed, **Then** a ticket with "FCI DYEING — WEIGHING TICKET", batch, order, machine, shade, date/time, operator, per-component name/target/actual/unit, "ALL WITHIN TOLERANCE" and the batch barcode is sent to the printer
- [ ] **Given** the printer accepts, **When** printing finishes, **Then** the Dummy Printer stores the ticket and the preview shows the same content
- [ ] **Given** the ticket is built, **When** values are read, **Then** targets and actuals come from the stored records, not recomputed

## UI/UX Impact

- View 3 ticket preview and Print ticket F1

## API Dependencies

- Consumes: 003 printer adapter (Dummy `POST /api/tickets`)
- Provides: WeighingMS print/preview endpoint

## Test Expectations

- Django tests: ticket content for B-24187
- Workbook STEP 27 evidence

## Technical Notes

- The prototype says "Label content is invented" (Q18); layout follows it for training only

## Dependencies

### Requires
- 005-weighing-station/009-complete-batch
- 003-device-integration/004-printer-adapter

### Enables
- 006-ticket-printing/002-reprint-and-print-failure

## Out of Scope

- None
