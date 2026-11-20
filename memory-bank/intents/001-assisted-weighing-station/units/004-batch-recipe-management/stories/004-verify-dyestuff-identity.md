---
id: 004-verify-dyestuff-identity
unit: 004-batch-recipe-management
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: null
implemented: false
---

# Story: 004-verify-dyestuff-identity

## User Story

**As an** operator
**I want** to scan the dyestuff before dispensing
**So that** the wrong dyestuff can never be confirmed

## Requirements

- FR-4
- OQ-8
- brief FR-09, BR-10, IR-15

## Acceptance Criteria

- [ ] **Given** the active component is Yellow RGB (DYE-4471), **When** DYE-4471 is scanned, **Then** identity is marked verified
- [ ] **Given** the active component is Yellow RGB, **When** a different code is scanned, **Then** "Wrong dyestuff" is shown and confirmation stays blocked
- [ ] **Given** identity is not verified, **When** confirmation is attempted, **Then** it is refused

## UI/UX Impact

- View 2 "Scan dyestuff" step near the component header (not drawn in the prototype; added per OQ-8)

## API Dependencies

- Consumes: 003 scanner adapter
- Provides: WeighingMS verify-identity endpoint

## Test Expectations

- Django tests: match, mismatch, unverified confirm refused
- Playwright: scan step

## Technical Notes

- None

## Dependencies

### Requires
- 003-load-read-only-recipe
- 003-device-integration/003-scanner-input

### Enables
- 005-weighing-station/006-confirm-weighing
- 007-assisted-weighing-station-ui/003-weigh-view-recipe-rail-and-header

## Out of Scope

- None
