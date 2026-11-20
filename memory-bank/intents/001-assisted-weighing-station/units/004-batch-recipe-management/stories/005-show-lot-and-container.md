---
id: 005-show-lot-and-container
unit: 004-batch-recipe-management
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: null
implemented: false
---

# Story: 005-show-lot-and-container

## User Story

**As a** Lab/QA (via the record) and operator
**I want** the lot, container and tare of each component shown and kept
**So that** every weighing can be traced to a physical lot and container

## Requirements

- FR-5, FR-6
- OQ-7
- brief FR-10, BR-11

## Acceptance Criteria

- [ ] **Given** Yellow RGB is active, **When** the component header is built, **Then** it reads "Remazol Yellow RGB · DYE-4471 · LOT 2026-0387 · CONTAINER C-12 · TARE 214 g"
- [ ] **Given** a component without a lot, **When** confirmation is attempted, **Then** it is refused
- [ ] **Given** Sodium Sulphate is active, **When** the header is built, **Then** container D-03 and tare 1.850 kg are shown

## UI/UX Impact

- View 2 component header (w-meta line)

## API Dependencies

- Provides: lot/container/tare as part of the WeighingMS recipe/component endpoint

## Test Expectations

- Django tests: header values per component; missing-lot refusal

## Technical Notes

- None

## Dependencies

### Requires
- 003-load-read-only-recipe

### Enables
- 005-weighing-station/006-confirm-weighing

## Out of Scope

- None
