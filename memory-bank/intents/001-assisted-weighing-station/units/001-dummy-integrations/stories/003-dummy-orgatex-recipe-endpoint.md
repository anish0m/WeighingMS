---
id: 003-dummy-orgatex-recipe-endpoint
unit: 001-dummy-integrations
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 001-dummy-integrations
implemented: false
---

# Story: 003-dummy-orgatex-recipe-endpoint

## User Story

**As a** WeighingMS (system)
**I want** to read the recipe and component list of a batch from Dummy OrgaTEX
**So that** the recipe rail and weighing targets come from the (Dummy) master system

## Requirements

- DB-2
- OQ-5
- Supports FR-3, FR-5, FR-6, FR-7, FR-10, FR-12

## Acceptance Criteria

- [ ] **Given** the seed has run, **When** `GET /api/batches/B-24187/recipe` is called, **Then** it returns "Teal 4C" with 5 components in sequence, each with code, name, colour, target, unit, tolerance, display max, lot, container, tare as decimal strings
- [ ] **Given** B-24188 has no recipe in training data, **When** its recipe is requested, **Then** a clear "recipe not available" error is returned (not an empty recipe)

## UI/UX Impact

- None directly (feeds recipe rail and component header)

## API Dependencies

- Provides: `GET /api/batches/:batchId/recipe`

## Test Expectations

- Django API test: values equal prototype; quantities are strings, not floats
- Django API test: recipe-not-available case

## Technical Notes

- Training contract only: not a claim about the real OrgaTEX / device interface (A-01…A-15 stay unresolved).

## Dependencies

### Requires
- 001-seed-training-scenario

### Enables
- 002-orgatex-integration/001-read-batches-and-recipe

## Out of Scope

- None
