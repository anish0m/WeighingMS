---
id: 003-load-read-only-recipe
unit: 004-batch-recipe-management
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: null
implemented: false
---

# Story: 003-load-read-only-recipe

## User Story

**As an** operator
**I want** the recipe of the selected batch shown in sequence
**So that** I weigh exactly what OrgaTEX specified

## Requirements

- FR-3
- NFR-2 (≤ 3 s)
- C-01
- brief FR-05, FR-06, BR-04, IR-02

## Acceptance Criteria

- [ ] **Given** B-24187 is selected, **When** the recipe loads, **Then** "Teal 4C" with Blue RSPL, Red RB, Yellow RGB, Sodium Sulphate, Soda Ash in order, with code, scale class, target, unit, tolerance and state, is available within 3 s
- [ ] **Given** the recipe is loaded, **When** any edit is attempted, **Then** no endpoint or UI exists to change it
- [ ] **Given** the recipe cannot be retrieved, **When** the batch is selected, **Then** weighing does not start and the reason is shown

## UI/UX Impact

- View 2 recipe rail "Recipe · Teal 4C" and "n of 5 components weighed" (rendered by 007)

## API Dependencies

- Consumes: 002 adapter (Dummy `GET /api/batches/:batchId/recipe`)
- Provides: WeighingMS recipe endpoint

## Test Expectations

- Django tests: order, Decimal values, failure
- Timing check ≤ 3 s locally

## Technical Notes

- Local snapshot is a cache for resume, never authoritative (brief DR-03)

## Dependencies

### Requires
- 002-select-batch

### Enables
- 004-batch-recipe-management/004-verify-dyestuff-identity
- 004-batch-recipe-management/005-show-lot-and-container
- 007-assisted-weighing-station-ui/003-weigh-view-recipe-rail-and-header

## Out of Scope

- None
