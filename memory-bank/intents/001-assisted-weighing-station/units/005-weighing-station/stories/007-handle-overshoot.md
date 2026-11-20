---
id: 007-handle-overshoot
unit: 005-weighing-station
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 012-weighing-station
implemented: false
---

# Story: 007-handle-overshoot

## User Story

**As an** operator and supervisor
**I want** an over-tolerance weight to be blocked and handled by an agreed rule
**So that** a surplus never silently changes the recipe

## Requirements

- FR-14
- OQ-4 (open)
- NFR-4
- brief FR-20–FR-24, BR-08, BR-13, AC-05, AC-06, A-08

## Acceptance Criteria

- [ ] **Given** Yellow RGB at 96.4 g, **When** it is evaluated, **Then** "OVER TOLERANCE — SURPLUS +2.4 g" and "Surplus +2.4 g (+2.6%)" are produced and confirm is blocked
- [ ] **Given** an overshoot, **When** nothing else is done, **Then** no remaining component target changes
- [ ] **Given** the rule decided at STEP 24 allows an override/compensation, **When** a supervisor applies it with ID + PIN + reason, **Then** it is recorded with who authorised it and why

## UI/UX Impact

- View 2 surplus panel and status line; Supervisor override button

## API Dependencies

- Provides: WeighingMS weighing-session API for the UI (shape fixed in Bolt design)

## Test Expectations

- Django tests: surplus amount/percent in Decimal; no automatic recalculation; override recorded (after STEP 24)

## Technical Notes

- Do NOT copy the prototype's recalculation (≈ remaining × 1.026). The third criterion is refined after the STEP 24 human decision

## Dependencies

### Requires
- 005-evaluate-inclusive-tolerance
- 001-identify-operator

### Enables
- 007-assisted-weighing-station-ui/006-weigh-view-surplus-panel-and-override

## Out of Scope

- None
