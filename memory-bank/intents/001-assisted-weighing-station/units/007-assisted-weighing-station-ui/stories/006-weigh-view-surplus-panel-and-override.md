---
id: 006-weigh-view-surplus-panel-and-override
unit: 007-assisted-weighing-station-ui
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: null
implemented: false
---

# Story: 006-weigh-view-surplus-panel-and-override

## User Story

**As an** operator
**I want** to see clearly that I overshot and by how much
**So that** I stop and follow the agreed overshoot rule

## Requirements

- FR-14 (rendering)
- OQ-4
- NFR-4

## Acceptance Criteria

- [ ] **Given** Yellow RGB at 96.4 g, **When** view 2 renders, **Then** the status line reads "OVER TOLERANCE — SURPLUS +2.4 g", the surplus panel shows "Surplus +2.4 g (+2.6%) — over tolerance" and Confirm is disabled
- [ ] **Given** the overshoot rule is decided at STEP 24, **When** the panel renders, **Then** it shows only what that rule defines (no hard-coded proposal)
- [ ] **Given** Supervisor override is pressed, **When** the rule allows it, **Then** a form asks for supervisor ID, PIN and reason

## UI/UX Impact

- View 2 surplus panel and Supervisor override button
- Matches the prototype `docs/customize-weighing-station.html` (labels, layout, colours, units) for the STEP 28 comparison

## API Dependencies

- Consumes: WeighingMS evaluation and override endpoints (005)

## Test Expectations

- Playwright STEP 24: overshoot via simulate, panel values, confirm disabled

## Technical Notes

- The prototype's recalculated values (24.624 kg, 9.850 kg) are a guess and must not be copied

## Dependencies

### Requires
- 005-weighing-station/007-handle-overshoot

### Enables
- None

## Out of Scope

- None
