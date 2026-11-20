---
id: 011-retrieve-batch-history
unit: 005-weighing-station
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 015-weighing-station
implemented: false
---

# Story: 011-retrieve-batch-history

## User Story

**As a** Lab/QA investigating a shade failure
**I want** all weighing records of a batch
**So that** a bad recipe can be told apart from a bad weighing

## Requirements

- FR-19 (b, c)
- brief FR-29, BR-19, AC-07

## Acceptance Criteria

- [ ] **Given** B-24187 is complete, **When** its records are requested, **Then** each component's target, actual, operator, scale, lot, container, tare and timestamp are returned
- [ ] **Given** any confirmed record, **When** it is inspected, **Then** it stores the operator ID

## UI/UX Impact

- None in the prototype; served as an API/page (OQ-2: no further reporting)

## API Dependencies

- Provides: WeighingMS batch-records endpoint

## Test Expectations

- Django API test for B-24187 records

## Technical Notes

- None

## Dependencies

### Requires
- 006-confirm-weighing

### Enables
- None

## Out of Scope

- Reports, dashboards, supervisor remote view (OQ-2)
