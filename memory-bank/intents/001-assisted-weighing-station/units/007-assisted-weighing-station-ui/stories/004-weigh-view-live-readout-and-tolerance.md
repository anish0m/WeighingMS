---
id: 004-weigh-view-live-readout-and-tolerance
unit: 007-assisted-weighing-station-ui
intent: 001-assisted-weighing-station
status: complete
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 011-assisted-weighing-station-ui
implemented: true
---

# Story: 004-weigh-view-live-readout-and-tolerance

## User Story

**As an** operator
**I want** a live readout with a coloured bar and tolerance band
**So that** I can see where the weight is against the target while dispensing

## Requirements

- FR-8, FR-9, FR-10, FR-11, FR-12 (rendering)
- NFR-1, NFR-10

## Acceptance Criteria

- [ ] **Given** the scale weight changes, **When** ≤ 200 ms pass, **Then** "Weighed now" and the bar update without reload
- [ ] **Given** Yellow RGB, **When** the panel renders, **Then** Target 94.0 g, Still to weigh, "TOLERANCE ±0.5 g (93.5 – 94.5)", the band from 93.5 to 94.5 and the target line on a 0–125 g bar
- [ ] **Given** zones under / near / within / over from the API, **When** the panel renders, **Then** readout and bar use the prototype colours and the status line text (e.g. "DISPENSE — 94.0 g REMAINING")
- [ ] **Given** the active component changes scale, **When** the panel renders, **Then** "Scale selected · 32 kg floor · automatic" and kg units are shown

## UI/UX Impact

- View 2 weighing panel
- Matches the prototype `docs/customize-weighing-station.html` (labels, layout, colours, units) for the STEP 28 comparison

## API Dependencies

- Consumes: WeighingMS live-weight (003) and evaluation (005) endpoints

## Test Expectations

- Playwright STEP 20–22: readout follows simulate; zone colours; caption

## Technical Notes

- Zone and remaining come from the API; JS does not compute tolerance (no float logic)

## Dependencies

### Requires
- 003-device-integration/001-read-live-scale-weight
- 005-weighing-station/005-evaluate-inclusive-tolerance
- 005-weighing-station/002-select-scale-automatically

### Enables
- 007-assisted-weighing-station-ui/009-no-hard-coded-scenario-data

## Out of Scope

- None
