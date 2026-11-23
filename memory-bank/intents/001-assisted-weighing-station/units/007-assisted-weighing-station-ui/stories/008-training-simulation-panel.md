---
id: 008-training-simulation-panel
unit: 007-assisted-weighing-station-ui
intent: 001-assisted-weighing-station
status: complete
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 011-assisted-weighing-station-ui
implemented: true
---

# Story: 008-training-simulation-panel

## User Story

**As a** trainer running the demo
**I want** the prototype's Simulate dispense / overshoot / reset controls and failure switches
**So that** the demo and E2E tests can drive the Dummies like the prototype did

## Requirements

- DB-6, DB-4, DB-7, DB-8, DB-9
- Prototype "How to run this in the meeting" controls

## Acceptance Criteria

- [ ] **Given** Yellow RGB active, **When** Simulate dispense / Simulate overshoot / Reset is pressed, **Then** the Dummy Scale weight becomes 94.2 g / 96.4 g / 0.0 g and view 2 follows
- [ ] **Given** the panel, **When** a device or OrgaTEX failure switch is toggled, **Then** the matching Dummy enters/leaves its failure mode
- [ ] **Given** the operator view, **When** it renders, **Then** the panel is clearly marked as training-only and separate from operator controls

## UI/UX Impact

- Training controls equivalent to the prototype's demo buttons

## API Dependencies

- Consumes: Dummy Scale simulate endpoints and Dummy failure toggles (001) over HTTP

## Test Expectations

- Playwright: simulate buttons change the readout; toggles change status

## Technical Notes

- Training-only; would be removed with the Dummies

## Dependencies

### Requires
- 001-dummy-integrations/005-dummy-scale-api
- 001-dummy-integrations/007-dummy-failure-toggles

### Enables
- None

## Out of Scope

- None
