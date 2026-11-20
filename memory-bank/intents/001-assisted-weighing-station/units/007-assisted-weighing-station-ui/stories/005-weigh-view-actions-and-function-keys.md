---
id: 005-weigh-view-actions-and-function-keys
unit: 007-assisted-weighing-station-ui
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 011-assisted-weighing-station-ui
implemented: false
---

# Story: 005-weigh-view-actions-and-function-keys

## User Story

**As an** operator
**I want** large buttons and F-keys for confirm, re-tare and quit
**So that** I can work with gloves or the terminal keypad

## Requirements

- FR-7, FR-13 (rendering)
- NFR-8, NFR-9

## Acceptance Criteria

- [ ] **Given** weight within tolerance, **When** OK · Confirm F1 renders, **Then** it is enabled; outside tolerance it is disabled
- [ ] **Given** view 2 is active, **When** F1 / F2 / F4 is pressed, **Then** Confirm / Re-tare / Quit run exactly like the buttons
- [ ] **Given** the buttons render, **When** they are measured, **Then** each primary button is ≥ 15 mm (≈ 57 px)

## UI/UX Impact

- View 2 action bar
- Matches the prototype `docs/customize-weighing-station.html` (labels, layout, colours, units) for the STEP 28 comparison

## API Dependencies

- Consumes: WeighingMS confirm, tare, quit endpoints (005)

## Test Expectations

- Playwright: enabled/disabled states, F-keys, button size

## Technical Notes

- None

## Dependencies

### Requires
- 005-weighing-station/003-tare-retare-and-quit
- 005-weighing-station/006-confirm-weighing

### Enables
- None

## Out of Scope

- None
