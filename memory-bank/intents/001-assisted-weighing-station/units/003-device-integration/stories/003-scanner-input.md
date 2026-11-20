---
id: 003-scanner-input
unit: 003-device-integration
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: null
implemented: false
---

# Story: 003-scanner-input

## User Story

**As an** operator
**I want** my batch card and dyestuff barcode scans to reach the station
**So that** I can select batches and verify dyestuffs without typing

## Requirements

- Supports FR-2, FR-4
- FR-20 (b)
- IR-15 (brief)

## Acceptance Criteria

- [ ] **Given** the scanner is ready, **When** B-24187 is scanned, **Then** WeighingMS receives code B-24187 once
- [ ] **Given** the scanner is unavailable, **When** a scan is attempted, **Then** an error is reported and no state changes

## UI/UX Impact

- View 1 scan prompt; view 2 scan step; SCANNER status

## API Dependencies

- Consumes: Dummy Scanner endpoint (shape fixed in Bolt design)

## Test Expectations

- Django tests: receive, unavailable

## Technical Notes

- None

## Dependencies

### Requires
- 001-dummy-integrations/006-dummy-scanner-and-printer

### Enables
- 003-device-integration/005-device-status-and-fail-safe
- 004-batch-recipe-management/002-select-batch
- 004-batch-recipe-management/004-verify-dyestuff-identity

## Out of Scope

- None
