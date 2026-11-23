---
id: 002-select-scale-automatically
unit: 005-weighing-station
intent: 001-assisted-weighing-station
status: complete
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 009-weighing-station
implemented: true
---

# Story: 002-select-scale-automatically

## User Story

**As an** operator
**I want** the station to pick the right scale for each component
**So that** I never weigh a small dye quantity on the floor scale

## Requirements

- FR-8
- NFR-13
- brief FR-07, BR-05, AC-02, A-06

## Acceptance Criteria

- [ ] **Given** threshold 3 kg, **When** Yellow RGB (94.0 g) becomes active, **Then** `scale-3kg` (3 kg precision) is selected and shown as "automatic"
- [ ] **Given** threshold 3 kg, **When** Sodium Sulphate (24.000 kg) becomes active, **Then** `scale-32kg` (32 kg floor) is selected and units switch to kg
- [ ] **Given** targets of exactly 3 kg and 3.0001 kg, **When** the scale is selected, **Then** 3 kg → precision, 3.0001 kg → floor
- [ ] **Given** the configured threshold is changed in settings, **When** a component is activated, **Then** selection follows the new threshold without code change

## UI/UX Impact

- View 2 "Scale selected · 3 kg precision · automatic"; status bar scale highlight

## API Dependencies

- Provides: WeighingMS weighing-session API for the UI (shape fixed in Bolt design)

## Test Expectations

- Django unit tests for the boundary (3 / 3.0001 kg) and a changed threshold (workbook STEP 21)

## Technical Notes

- Comparison in `Decimal`, converting g/kg as needed

## Dependencies

### Requires
- None

### Enables
- 005-weighing-station/004-target-and-remaining
- 005-weighing-station/008-progress-components
- 007-assisted-weighing-station-ui/004-weigh-view-live-readout-and-tolerance

## Out of Scope

- Supervisor manual reselection and calibration blocking (OQ-9)
