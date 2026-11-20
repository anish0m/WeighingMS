---
id: 009-no-hard-coded-scenario-data
unit: 007-assisted-weighing-station-ui
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: null
implemented: false
---

# Story: 009-no-hard-coded-scenario-data

## User Story

**As a** course assessor
**I want** proof that no batch, recipe or component data is hard-coded in the UI
**So that** the station really runs on the Dummy APIs (and later on real ones)

## Requirements

- FR-21 (a, b)
- IR-07 (brief)

## Acceptance Criteria

- [ ] **Given** the templates and static JS, **When** they are searched, **Then** no batch, recipe or component array or literal scenario values exist
- [ ] **Given** the seed is changed (e.g. a different target), **When** the UI is reloaded, **Then** the UI shows the changed value
- [ ] **Given** WeighingMS Python modules, **When** imports are checked, **Then** none imports `dummy_*` models

## UI/UX Impact

- All views (no visible change)

## API Dependencies

- All WeighingMS endpoints

## Test Expectations

- Automated check over templates/static and imports
- Playwright with a modified seed value

## Technical Notes

- None

## Dependencies

### Requires
- 002-select-batch-view
- 003-weigh-view-recipe-rail-and-header
- 004-weigh-view-live-readout-and-tolerance
- 007-confirm-and-print-view

### Enables
- None

## Out of Scope

- None
