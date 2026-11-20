---
id: 001-identify-operator
unit: 005-weighing-station
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 006-weighing-station
implemented: false
---

# Story: 001-identify-operator

## User Story

**As an** operator
**I want** to choose myself from the operator list before weighing
**So that** every weighing is attributable to me

## Requirements

- FR-19 (a)
- OQ-3
- brief FR-34, BR-14

## Acceptance Criteria

- [ ] **Given** seeded operators exist (R. Karim · Shift A), **When** the station starts, **Then** the operator must be chosen before any batch can be weighed
- [ ] **Given** R. Karim is chosen, **When** any view is shown, **Then** the header reads "Operator R. Karim · Shift A"
- [ ] **Given** no operator is identified, **When** a weighing action is attempted, **Then** it is refused

## UI/UX Impact

- Operator choice before view 1 (prototype shows only the header result); header operator field

## API Dependencies

- Provides: WeighingMS weighing-session API for the UI (shape fixed in Bolt design)

## Test Expectations

- Django tests: seeded operators; refusal without operator
- Playwright: header shows operator

## Technical Notes

- Training method per OQ-3: choose from a seeded list, no password

## Dependencies

### Requires
- None

### Enables
- 005-weighing-station/006-confirm-weighing
- 005-weighing-station/007-handle-overshoot
- 007-assisted-weighing-station-ui/001-terminal-shell-and-status-bar

## Out of Scope

- Real login / FCI directory (A-09, Q37)
