---
id: 005-dummy-scale-api
unit: 001-dummy-integrations
intent: 001-assisted-weighing-station
status: complete
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 002-dummy-integrations
implemented: true
---

# Story: 005-dummy-scale-api

## User Story

**As a** trainer and WeighingMS
**I want** two simulated scales whose weight I can drive
**So that** live weighing, tolerance and overshoot can be demonstrated and tested without hardware

## Requirements

- DB-5, DB-6, DB-7
- Supports FR-7, FR-8, FR-9, FR-12, FR-14

## Acceptance Criteria

- [ ] **Given** the seed has run, **When** `GET /api/scales` is called, **Then** `scale-3kg` (precision) and `scale-32kg` (floor) are listed
- [ ] **Given** a scale, **When** `GET /api/scales/:scaleId/weight` and `/status` are called, **Then** net weight (decimal string), unit and status ready/disconnected are returned
- [ ] **Given** a scale with weight on it, **When** `POST /api/scales/:scaleId/tare` is called, **Then** net weight becomes 0
- [ ] **Given** active target 94.0 g ± 0.5 g, **When** simulate dispense / overshoot / reset / set exact weight 93.4 is called, **Then** weight becomes 94.2 / 96.4 / 0.0 / 93.4 g respectively

## UI/UX Impact

- Indirect: drives the live readout on view 2; the training panel is story 007-…-ui/008

## API Dependencies

- Provides: `GET /api/scales`, `GET /api/scales/:scaleId/status`, `GET /api/scales/:scaleId/weight`, `POST /api/scales/:scaleId/tare`, training-only simulate endpoints

## Test Expectations

- Django API tests for each endpoint and each simulate action (target + 0.4·tol, target + 4.8·tol)

## Technical Notes

- Simulate formulas follow the prototype's buttons; values must be Decimal
- Training contract only: not a claim about the real OrgaTEX / device interface (A-01…A-15 stay unresolved).

## Dependencies

### Requires
- 001-seed-training-scenario

### Enables
- 001-dummy-integrations/007-dummy-failure-toggles
- 003-device-integration/001-read-live-scale-weight
- 003-device-integration/002-tare-command
- 007-assisted-weighing-station-ui/008-training-simulation-panel

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Tare while disconnected | Error, weight unchanged |
| Set weight with float-like input "93.4" | Parsed as Decimal, returned as "93.4" |

## Out of Scope

- None
