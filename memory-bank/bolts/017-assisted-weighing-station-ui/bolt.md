---
id: 017-assisted-weighing-station-ui
unit: 007-assisted-weighing-station-ui
intent: 001-assisted-weighing-station
type: simple-construction-bolt
status: in-progress
stories:
  - 007-confirm-and-print-view
  - 009-no-hard-coded-scenario-data
created: 2026-11-20T05:15:14Z
started: 2026-11-24T04:09:09Z
completed: null
current_stage: plan
stages_completed: []

# Bolt Dependencies (for execution ordering)
requires_bolts: [007-assisted-weighing-station-ui, 011-assisted-weighing-station-ui, 014-orgatex-integration, 015-weighing-station, 016-ticket-printing]
enables_bolts: []
requires_units: []  # unit ordering is enforced through requires_bolts (see body)
blocks: true

# Complexity Assessment (aggregate of included stories)
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 3
workbook_step: "STEP 26"
---

# Bolt: 017-assisted-weighing-station-ui

## Overview

View 3 · Confirm & print and the proof that no scenario data is hard-coded. Serves workbook STEP 26.

## Objective

View 3 · Confirm & print and the proof that no scenario data is hard-coded.

## Stories Included

- **007-confirm-and-print-view**: a completion screen with the summary, the OrgaTEX status and the ticket (Must)
- **009-no-hard-coded-scenario-data**: proof that no batch, recipe or component data is hard-coded in the UI (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [ ] **1. Plan**: Pending → implementation-plan.md
- [ ] **2. Implement**: Pending → source code + implementation-walkthrough.md
- [ ] **3. Test**: Pending → tests + test-walkthrough.md

## Expected Outcome

- View 3: summary, "Written to OrgaTEX CONFIRMED hh:mm:ss" / not written + Retry, ticket preview, Print ticket F1, Next batch F3
- Automated check: no batch/recipe/component data in templates/static; no `dummy_*` imports

## Test Expectations

- Playwright: complete B-24187 → view 3 values, CONFIRMED, print, next batch; modified-seed check
- Workbook STEP 26–29 evidence

## Dependencies

### Requires
- 007-assisted-weighing-station-ui
- 011-assisted-weighing-station-ui
- 014-orgatex-integration
- 015-weighing-station
- 016-ticket-printing

### Unit Dependencies (cross-unit, satisfied through the bolts above)
- 003-device-integration
- 004-batch-recipe-management
- 005-weighing-station
- 006-ticket-printing

### Enables
- None (final bolt)

## Success Criteria

- [ ] All stories implemented
- [ ] All acceptance criteria met
- [ ] Tests passing (`npm test`; Playwright where listed)
- [ ] Code reviewed

## Notes

- Dummy APIs are training contracts, not the real OrgaTEX / device interfaces.
- Architecture (STEP 12 decision): the browser calls the Dummy APIs directly through one JS client per integration; the WeighingMS server stays the authority (re-reads the scale for confirmation, stores records, supplies write-back payload/key and ticket content).
