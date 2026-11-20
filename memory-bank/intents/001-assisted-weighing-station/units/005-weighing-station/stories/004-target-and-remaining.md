---
id: 004-target-and-remaining
unit: 005-weighing-station
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: null
implemented: false
---

# Story: 004-target-and-remaining

## User Story

**As an** operator
**I want** to see the target and how much is still to weigh
**So that** I know when to slow down

## Requirements

- FR-10, FR-11
- brief FR-14

## Acceptance Criteria

- [ ] **Given** Yellow RGB at 0.0 g, **When** it is evaluated, **Then** Target 94.0 g, still to weigh 94.0 g
- [ ] **Given** Yellow RGB at 90.0 g, **When** it is evaluated, **Then** still to weigh 4.0 g and status "DISPENSE — 4.0 g REMAINING"
- [ ] **Given** weight at or above target, **When** it is evaluated, **Then** still to weigh is 0.0, never negative
- [ ] **Given** Sodium Sulphate, **When** it is displayed, **Then** "24.000 kg" (3 decimals for kg, 1 for g)

## UI/UX Impact

- View 2 "Target", "Weighed now", "Still to weigh", status line

## API Dependencies

- Provides: WeighingMS weighing-session API for the UI (shape fixed in Bolt design)

## Test Expectations

- Django unit tests for remaining and display precision

## Technical Notes

- None

## Dependencies

### Requires
- 002-select-scale-automatically

### Enables
- 005-weighing-station/005-evaluate-inclusive-tolerance

## Out of Scope

- None
