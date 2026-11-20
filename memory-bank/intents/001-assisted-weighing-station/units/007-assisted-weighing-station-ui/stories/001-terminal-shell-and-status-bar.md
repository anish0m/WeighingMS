---
id: 001-terminal-shell-and-status-bar
unit: 007-assisted-weighing-station-ui
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 007-assisted-weighing-station-ui
implemented: false
---

# Story: 001-terminal-shell-and-status-bar

## User Story

**As an** operator
**I want** a header and status bar that always show where I am and whether the devices work
**So that** I can trust the station at a glance

## Requirements

- FR-20 (rendering)
- FR-19 (header operator)
- NFR-8, NFR-10, NFR-11

## Acceptance Criteria

- [ ] **Given** the station is open, **When** any view is shown, **Then** the header shows WeighingMS STATION 01, BATCH · ORDER · MACHINE (when a batch is open), Operator name · shift, and a clock
- [ ] **Given** device status from the API, **When** the status bar renders, **Then** SCALE 3 kg, SCALE 32 kg, SCANNER, PRINTER and ORGATEX each show their current state, and EN
- [ ] **Given** a device goes into failure, **When** ≤ 2 s pass, **Then** its status changes visibly, never showing READY

## UI/UX Impact

- Header and footer status strip of all three views
- Matches the prototype `docs/customize-weighing-station.html` (labels, layout, colours, units) for the STEP 28 comparison

## API Dependencies

- Consumes: WeighingMS device-status (003) and session (005) endpoints

## Test Expectations

- Playwright: header values, status change on a toggled Dummy

## Technical Notes

- Django base template + Alpine.js served locally

## Dependencies

### Requires
- 003-device-integration/005-device-status-and-fail-safe
- 005-weighing-station/001-identify-operator

### Enables
- 007-assisted-weighing-station-ui/002-select-batch-view

## Out of Scope

- None
