---
id: 006-confirm-weighing
unit: 005-weighing-station
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: null
implemented: false
---

# Story: 006-confirm-weighing

## User Story

**As an** operator
**I want** to confirm a weight that is within tolerance
**So that** a complete, immutable record exists for traceability (BO-02)

## Requirements

- FR-13 (a–d)
- NFR-5, NFR-12
- brief FR-18, FR-19, FR-25, DR-02, AC-04

## Acceptance Criteria

- [ ] **Given** weight within tolerance, identity verified, lot present, scale connected, **When** OK · Confirm (F1) is pressed, **Then** a record with actual weight, unit, operator, component, lot, container, tare, scale, target, tolerance min/max, result and UTC timestamp is saved in one transaction before the UI advances
- [ ] **Given** any precondition is not met, **When** confirm is requested directly on the server, **Then** it is rejected and nothing is saved
- [ ] **Given** a saved record, **When** an edit or delete is attempted through the app, **Then** it is impossible; corrections are new records

## UI/UX Impact

- View 2 OK · Confirm F1 enabled only within tolerance; rail entry shows ✓ actual

## API Dependencies

- Provides: WeighingMS weighing-session API for the UI (shape fixed in Bolt design)

## Test Expectations

- Django tests: all fields stored; server-side rejection out of tolerance; immutability (workbook STEP 25 evidence)

## Technical Notes

- None

## Dependencies

### Requires
- 005-evaluate-inclusive-tolerance
- 001-identify-operator
- 004-batch-recipe-management/004-verify-dyestuff-identity
- 004-batch-recipe-management/005-show-lot-and-container
- 003-device-integration/005-device-status-and-fail-safe

### Enables
- 005-weighing-station/008-progress-components
- 005-weighing-station/010-resume-after-reload
- 005-weighing-station/011-retrieve-batch-history
- 007-assisted-weighing-station-ui/005-weigh-view-actions-and-function-keys

## Out of Scope

- None
