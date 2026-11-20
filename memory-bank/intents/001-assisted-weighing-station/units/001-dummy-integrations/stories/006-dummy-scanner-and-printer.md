---
id: 006-dummy-scanner-and-printer
unit: 001-dummy-integrations
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 002-dummy-integrations
implemented: false
---

# Story: 006-dummy-scanner-and-printer

## User Story

**As a** trainer and WeighingMS
**I want** simulated barcode scans and a printer that stores tickets
**So that** scan-based selection, dyestuff verification and ticket printing work without hardware

## Requirements

- DB-8, DB-9
- Supports FR-2, FR-4, FR-18

## Acceptance Criteria

- [ ] **Given** the scanner is ready, **When** a batch code or dyestuff code is submitted as a simulated scan, **Then** the scan is available to WeighingMS as the latest scanned code
- [ ] **Given** the printer is ready, **When** `POST /api/tickets` is called with ticket content, **Then** the ticket is stored and returned with an ID for preview
- [ ] **Given** a stored ticket, **When** it is requested by ID, **Then** the same content is returned

## UI/UX Impact

- Indirect: scan prompt on view 1, scan step on view 2, ticket preview on view 3

## API Dependencies

- Provides: `POST /api/tickets` (workbook STEP 16) + ticket read; scanner endpoint shape fixed in Bolt design

## Test Expectations

- Django API tests: scan submit/read, ticket store/read

## Technical Notes

- Training contract only: not a claim about the real OrgaTEX / device interface (A-01…A-15 stay unresolved).

## Dependencies

### Requires
- 001-seed-training-scenario

### Enables
- 001-dummy-integrations/007-dummy-failure-toggles
- 003-device-integration/003-scanner-input
- 003-device-integration/004-printer-adapter

## Out of Scope

- None
