---
id: 001-seed-training-scenario
unit: 001-dummy-integrations
intent: 001-assisted-weighing-station
status: complete
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 001-dummy-integrations
implemented: true
---

# Story: 001-seed-training-scenario

## User Story

**As a** trainer preparing the station
**I want** one command that loads the prototype scenario into the Dummy systems
**So that** every run starts from the same known batch, recipe and scale state

## Requirements

- DB-1, DB-2, DB-5, DB-10
- OQ-5 (only B-24187 has a recipe)
- OQ-6 (B-24187 starts with all 5 components pending)
- OQ-7 (lot/container from seed)

## Acceptance Criteria

- [ ] **Given** an empty database, **When** the seed command runs, **Then** Dummy OrgaTEX holds B-24187, B-24188, B-24190, B-24191 with the prototype's order, machine, fabric/lot, shade, component count
- [ ] **Given** the seed has run, **When** the recipe of B-24187 is inspected, **Then** it is "Teal 4C" with Blue RSPL, Red RB, Yellow RGB, Sodium Sulphate, Soda Ash and the prototype's code, target, unit, tolerance, display max, lot, container, tare, all pending
- [ ] **Given** the seed has run, **When** the scales are inspected, **Then** `scale-3kg` and `scale-32kg` exist, status ready, net weight 0
- [ ] **Given** the seed has already run, **When** it runs again, **Then** the scenario is reset to the same state without duplicates

## UI/UX Impact

- None directly; every value later shown on views 1–3 originates here

## API Dependencies

- None (loads Dummy tables through Django)

## Test Expectations

- Django test: seed loads exactly 4 batches and 5 components with `Decimal` values equal to the prototype's
- Django test: re-seed is idempotent
- Evidence: dump of seeded data → `STEP-17-dummy-data.json` (workbook STEP 17)

## Technical Notes

- Values are copied from the prototype `components` array and queue; nothing invented
- Quantities stored as `Decimal` (`DecimalField(12,4)`)
- Training contract only: not a claim about the real OrgaTEX / device interface (A-01…A-15 stay unresolved).

## Dependencies

### Requires
- None

### Enables
- 001-dummy-integrations/002-dummy-orgatex-batch-endpoints
- 001-dummy-integrations/003-dummy-orgatex-recipe-endpoint
- 001-dummy-integrations/004-dummy-orgatex-consumption-endpoint
- 001-dummy-integrations/005-dummy-scale-api
- 001-dummy-integrations/006-dummy-scanner-and-printer

## Out of Scope

- Operators and supervisors (seeded by 005-weighing-station)
