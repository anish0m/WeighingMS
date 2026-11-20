---
id: 010-weighing-station
unit: 005-weighing-station
intent: 001-assisted-weighing-station
type: ddd-construction-bolt
status: planned
stories:
  - 003-tare-retare-and-quit
  - 006-confirm-weighing
  - 008-progress-components
  - 010-resume-after-reload
created: 2026-11-20T05:15:14Z
started: null
completed: null
current_stage: null
stages_completed: []

# Bolt Dependencies (for execution ordering)
requires_bolts: [004-device-integration, 006-weighing-station, 008-batch-recipe-management, 009-weighing-station]
enables_bolts: [011-assisted-weighing-station-ui, 015-weighing-station]
requires_units: []  # unit ordering is enforced through requires_bolts (see body)
blocks: true

# Complexity Assessment (aggregate of included stories)
complexity:
  avg_complexity: 3
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
workbook_step: "STEP 20"
---

# Bolt: 010-weighing-station

## Overview

Confirmation and progression: tare/re-tare/quit, immutable weighing record, component order, resume. Serves workbook STEP 20.

## Objective

Confirmation and progression: tare/re-tare/quit, immutable weighing record, component order, resume.

## Stories Included

- **003-tare-retare-and-quit**: to tare the container, re-tare when needed, and abandon a bad attempt (Must)
- **006-confirm-weighing**: to confirm a weight that is within tolerance (Must)
- **008-progress-components**: the next component to load automatically after each confirmation (Must)
- **010-resume-after-reload**: the batch to reopen where I was after a reload or restart (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. Domain Model**: Pending → ddd-01-domain-model.md
- [ ] **2. Technical Design**: Pending → ddd-02-technical-design.md
- [ ] **3. ADR Analysis (optional)**: Pending → adr-*.md
- [ ] **4. Implement**: Pending → source code
- [ ] **5. Test**: Pending → ddd-03-test-report.md

## Expected Outcome

- Server-side confirm (re-reads the scale via the adapter; checks tolerance, identity, lot, scale connected) writing WeighingRecord in one transaction
- Record: actualWeight, unit, operator, component, lot, container, tare, scale, target, tolerance min/max, result, UTC timestamp; immutable
- Progression in recipe order, touch pending / done locked, resume after reload

## Test Expectations

- Django tests: all record fields, server-side rejection, immutability, order Blue RSPL → … → Soda Ash, quit records nothing, resume (workbook STEP 23, 25 evidence)

## Dependencies

### Requires
- 004-device-integration
- 006-weighing-station
- 008-batch-recipe-management
- 009-weighing-station

### Unit Dependencies (cross-unit, satisfied through the bolts above)
- 004-batch-recipe-management
- 003-device-integration
- 002-orgatex-integration

### Enables
- 011-assisted-weighing-station-ui
- 015-weighing-station

## Success Criteria

- [ ] All stories implemented
- [ ] All acceptance criteria met
- [ ] Tests passing (`npm test`; Playwright where listed)
- [ ] Code reviewed

## Notes

- Dummy APIs are training contracts, not the real OrgaTEX / device interfaces.
- Architecture (STEP 12 decision): the browser calls the Dummy APIs directly through one JS client per integration; the WeighingMS server stays the authority (re-reads the scale for confirmation, stores records, supplies write-back payload/key and ticket content).
