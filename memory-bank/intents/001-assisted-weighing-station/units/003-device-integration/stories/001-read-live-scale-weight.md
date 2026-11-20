---
id: 001-read-live-scale-weight
unit: 003-device-integration
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 004-device-integration
implemented: false
---

# Story: 001-read-live-scale-weight

## User Story

**As an** operator
**I want** the weight on the selected scale to update continuously while I dispense
**So that** I can stop exactly at the target

## Requirements

- FR-9
- NFR-1 (≤ 200 ms)
- IR-10 (brief)

## Acceptance Criteria

- [ ] **Given** `scale-3kg` reports 90.0 g, **When** WeighingMS reads `scale-3kg`, **Then** 90.0 g (Decimal) with unit g and status ready is returned
- [ ] **Given** the Dummy weight changes, **When** the UI polls through WeighingMS, **Then** the new value is available within 200 ms, without page reload
- [ ] **Given** the active component uses `scale-32kg`, **When** weight is read, **Then** only `scale-32kg` is read

## UI/UX Impact

- View 2: "Weighed now" readout and progress bar (rendered by 007)

## API Dependencies

- Consumes: Dummy Scale `GET /api/scales/:scaleId/weight`, `/status`
- Provides: WeighingMS live-weight endpoint for the UI (shape fixed in Bolt design)

## Test Expectations

- Django tests: Decimal parsing, scale routing
- Playwright: readout changes after a simulate call (STEP 21)

## Technical Notes

- Poll at ≥ 5 Hz; the brief's 10 Hz is a real-scale assumption (A-05)

## Dependencies

### Requires
- 001-dummy-integrations/005-dummy-scale-api

### Enables
- 003-device-integration/005-device-status-and-fail-safe
- 007-assisted-weighing-station-ui/004-weigh-view-live-readout-and-tolerance

## Out of Scope

- None
