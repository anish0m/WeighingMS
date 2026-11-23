---
id: 012-weighing-station
unit: 005-weighing-station
intent: 001-assisted-weighing-station
type: ddd-construction-bolt
status: in-progress
stories:
  - 007-handle-overshoot
created: 2026-11-20T05:15:14Z
started: 2026-11-23T08:52:26Z
completed: null
current_stage: implement
stages_completed: [model, design, adr]

# Bolt Dependencies (for execution ordering)
requires_bolts: [006-weighing-station, 009-weighing-station]
enables_bolts: [013-assisted-weighing-station-ui]
requires_units: []  # unit ordering is enforced through requires_bolts (see body)
blocks: true

# Complexity Assessment (aggregate of included stories)
complexity:
  avg_complexity: 2
  avg_uncertainty: 3
  max_dependencies: 1
  testing_scope: 2
workbook_step: "STEP 24"
---

# Bolt: 012-weighing-station

## Overview

Overshoot handling according to the human decision taken at workbook STEP 24 (OQ-4). Serves workbook STEP 24.

## Objective

Overshoot handling according to the human decision taken at workbook STEP 24 (OQ-4).

## Stories Included

- **007-handle-overshoot**: an over-tolerance weight to be blocked and handled by an agreed rule (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [x] **1. Domain Model**: Complete → ddd-01-domain-model.md
- [x] **2. Technical Design**: Complete → ddd-02-technical-design.md
- [x] **3. ADR Analysis (optional)**: Complete (ADR-012) → adr-*.md
- [ ] **4. Implement**: Pending → source code
- [ ] **5. Test**: Pending → ddd-03-test-report.md

## Expected Outcome

- Surplus amount/percent in Decimal, confirm blocked, recovery action and (if decided) supervisor override with ID + PIN + reason recorded
- No automatic recipe recalculation unless the approved rule says so

## Test Expectations

- Django tests: 96.4 g → +2.4 g (+2.6%), confirm blocked, no target change, override recorded (per decision)

## Dependencies

### Requires
- 006-weighing-station
- 009-weighing-station

### Unit Dependencies (cross-unit, satisfied through the bolts above)
- 004-batch-recipe-management
- 003-device-integration
- 002-orgatex-integration

### Enables
- 013-assisted-weighing-station-ui

## Success Criteria

- [ ] All stories implemented
- [ ] All acceptance criteria met
- [ ] Tests passing (`npm test`; Playwright where listed)
- [ ] Code reviewed

## Notes

- Dummy APIs are training contracts, not the real OrgaTEX / device interfaces.
- Architecture (STEP 12 decision): the browser calls the Dummy APIs directly through one JS client per integration; the WeighingMS server stays the authority (re-reads the scale for confirmation, stores records, supplies write-back payload/key and ticket content).
- ⚠️ Uncertainty high until STEP 24: run the STEP 24 decision prompt BEFORE starting this bolt; the Model stage must use the recorded decision.
