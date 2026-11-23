---
id: 005-evaluate-inclusive-tolerance
unit: 005-weighing-station
intent: 001-assisted-weighing-station
status: complete
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 009-weighing-station
implemented: true
---

# Story: 005-evaluate-inclusive-tolerance

## User Story

**As an** operator
**I want** the station to tell me clearly when I am under, near, within or over tolerance
**So that** out-of-tolerance weighings never reach production (BO-01)

## Requirements

- FR-12
- brief FR-15–FR-17, BR-07, BR-09, A-07

## Acceptance Criteria

- [ ] **Given** Yellow RGB 94.0 ± 0.5 g, **When** weights 93.4 / 93.5 / 94.0 / 94.5 / 94.6 g are evaluated, **Then** zones are near / within / within / within / over and can_confirm is false / true / true / true / false
- [ ] **Given** Yellow RGB, **When** the caption is built, **Then** it reads "TOLERANCE ±0.5 g (93.5 – 94.5)"
- [ ] **Given** a weight below 90 % of target, **When** it is evaluated, **Then** the zone is under
- [ ] **Given** any evaluation, **When** it runs, **Then** only `Decimal` arithmetic is used

## UI/UX Impact

- View 2 readout/bar colours per zone, tolerance band, caption, distinct signals for entering and exceeding tolerance

## API Dependencies

- Provides: WeighingMS weighing-session API for the UI (shape fixed in Bolt design)

## Test Expectations

- Django unit tests for the five boundary weights (workbook STEP 22 evidence)
- Playwright: confirm disabled at 93.4 and 94.6

## Technical Notes

- Near zone = ≥ 90 % of target below the band (prototype zone())

## Dependencies

### Requires
- 004-target-and-remaining

### Enables
- 005-weighing-station/006-confirm-weighing
- 005-weighing-station/007-handle-overshoot
- 007-assisted-weighing-station-ui/004-weigh-view-live-readout-and-tolerance

## Out of Scope

- None
