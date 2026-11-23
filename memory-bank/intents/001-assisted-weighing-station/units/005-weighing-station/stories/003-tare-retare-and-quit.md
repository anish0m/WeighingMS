---
id: 003-tare-retare-and-quit
unit: 005-weighing-station
intent: 001-assisted-weighing-station
status: complete
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 010-weighing-station
implemented: true
---

# Story: 003-tare-retare-and-quit

## User Story

**As an** operator
**I want** to tare the container, re-tare when needed, and abandon a bad attempt
**So that** the reading is always net and I can start over safely

## Requirements

- FR-7
- FR-13 (e)
- brief FR-11, IR-12

## Acceptance Criteria

- [ ] **Given** Yellow RGB on container C-12 (tare 214 g), **When** the component starts, **Then** tare 214 g is shown and an empty container reads 0.0 g net
- [ ] **Given** a partial dispense, **When** Re-tare (F2) is pressed, **Then** the net reading resets to 0 and the component's attempt restarts
- [ ] **Given** a partial dispense, **When** Quit (F4) is pressed, **Then** nothing is recorded and the component restarts
- [ ] **Given** a confirmed weighing, **When** its record is read, **Then** the tare used is stored

## UI/UX Impact

- View 2 "TARE" in component header; Re-tare F2, Quit F4 buttons

## API Dependencies

- Consumes: 003 tare command
- Provides: WeighingMS weighing-session API for the UI (shape fixed in Bolt design)

## Test Expectations

- Django tests: tare stored on record; quit records nothing

## Technical Notes

- Prototype treats Re-tare and Quit identically; here Quit records nothing and Re-tare zeroes the scale

## Dependencies

### Requires
- 003-device-integration/002-tare-command

### Enables
- 007-assisted-weighing-station-ui/005-weigh-view-actions-and-function-keys

## Out of Scope

- None
