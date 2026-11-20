---
id: 008-progress-components
unit: 005-weighing-station
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 010-weighing-station
implemented: false
---

# Story: 008-progress-components

## User Story

**As an** operator
**I want** the next component to load automatically after each confirmation
**So that** I work through the recipe without hunting for the next line

## Requirements

- FR-15
- brief FR-06, §6.2

## Acceptance Criteria

- [ ] **Given** B-24187 with all 5 pending, **When** each component is confirmed in turn, **Then** Blue RSPL → Red RB → Yellow RGB → Sodium Sulphate → Soda Ash become active in that order and the counter reads n of 5
- [ ] **Given** Yellow RGB is confirmed, **When** Sodium Sulphate becomes active, **Then** scale switches to 32 kg floor and units to kg
- [ ] **Given** a done component, **When** it is touched, **Then** nothing happens
- [ ] **Given** a pending component, **When** it is touched, **Then** it becomes active with its scale, units, tolerance and tare loaded

## UI/UX Impact

- View 2 recipe rail states (done ✓ actual / WEIGHING / PENDING) and counter

## API Dependencies

- Provides: WeighingMS weighing-session API for the UI (shape fixed in Bolt design)

## Test Expectations

- Django tests: order, touch rules
- Playwright five-component flow (workbook STEP 23 video)

## Technical Notes

- None

## Dependencies

### Requires
- 006-confirm-weighing
- 002-select-scale-automatically

### Enables
- 005-weighing-station/009-complete-batch
- 007-assisted-weighing-station-ui/003-weigh-view-recipe-rail-and-header

## Out of Scope

- None
