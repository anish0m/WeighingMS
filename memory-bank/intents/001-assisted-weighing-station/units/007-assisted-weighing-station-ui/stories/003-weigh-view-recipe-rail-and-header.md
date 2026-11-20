---
id: 003-weigh-view-recipe-rail-and-header
unit: 007-assisted-weighing-station-ui
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 011-assisted-weighing-station-ui
implemented: false
---

# Story: 003-weigh-view-recipe-rail-and-header

## User Story

**As an** operator
**I want** to see the recipe, which component is active and its lot/container/tare
**So that** I always know what I am weighing

## Requirements

- FR-3, FR-4, FR-5, FR-6, FR-15 (rendering)
- NFR-8, NFR-10

## Acceptance Criteria

- [ ] **Given** B-24187 is open, **When** view 2 renders, **Then** the rail shows "Recipe · Teal 4C", B-24187, "n of 5 components weighed" and each component with swatch, name, code · scale class, target and state (✓ actual / WEIGHING / PENDING)
- [ ] **Given** Yellow RGB is active, **When** the header renders, **Then** "Remazol Yellow RGB" and "DYE-4471 · LOT 2026-0387 · CONTAINER C-12 · TARE 214 g"
- [ ] **Given** identity not yet verified, **When** view 2 renders, **Then** the "Scan dyestuff" step is shown; a mismatch shows "Wrong dyestuff"
- [ ] **Given** a pending row is touched, **When** the API accepts, **Then** it becomes active; touching a done row does nothing

## UI/UX Impact

- View 2 left rail and component header; scan step added per OQ-8
- Matches the prototype `docs/customize-weighing-station.html` (labels, layout, colours, units) for the STEP 28 comparison

## API Dependencies

- Consumes: WeighingMS recipe, verify-identity and session endpoints (004, 005)

## Test Expectations

- Playwright: rail content from API, active change, scan mismatch

## Technical Notes

- None

## Dependencies

### Requires
- 004-batch-recipe-management/003-load-read-only-recipe
- 004-batch-recipe-management/004-verify-dyestuff-identity
- 005-weighing-station/008-progress-components

### Enables
- 007-assisted-weighing-station-ui/009-no-hard-coded-scenario-data

## Out of Scope

- None
