---
id: 005-device-status-and-fail-safe
unit: 003-device-integration
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 004-device-integration
implemented: false
---

# Story: 005-device-status-and-fail-safe

## User Story

**As an** operator
**I want** to see the state of every device and be stopped when one fails
**So that** I never confirm a weight from a disconnected scale or trust a failed print

## Requirements

- FR-20 (a, d)
- NFR-7
- IR-13, IR-18 (brief)

## Acceptance Criteria

- [ ] **Given** all devices are ready, **When** status is read, **Then** SCALE 3 kg, SCALE 32 kg, SCANNER, PRINTER report READY
- [ ] **Given** `scale-3kg` is switched to disconnected, **When** ≤ 2 s pass, **Then** its status is not ready and confirmation on it is blocked
- [ ] **Given** any device fails, **When** the status is shown, **Then** it is never shown as ready/success

## UI/UX Impact

- Status bar on every view (rendered by 007)

## API Dependencies

- Consumes: Dummy status endpoints + failure toggles
- Provides: WeighingMS device-status endpoint for the UI

## Test Expectations

- Django tests per failure mode
- Playwright STEP 30 failure scenarios

## Technical Notes

- None

## Dependencies

### Requires
- 001-read-live-scale-weight
- 003-scanner-input
- 004-printer-adapter
- 001-dummy-integrations/007-dummy-failure-toggles

### Enables
- 005-weighing-station/006-confirm-weighing
- 007-assisted-weighing-station-ui/001-terminal-shell-and-status-bar

## Out of Scope

- None
