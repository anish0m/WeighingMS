---
id: 007-assisted-weighing-station-ui
unit: 007-assisted-weighing-station-ui
intent: 001-assisted-weighing-station
type: simple-construction-bolt
status: planned
stories:
  - 001-terminal-shell-and-status-bar
  - 002-select-batch-view
created: 2026-11-20T05:15:14Z
started: null
completed: null
current_stage: null
stages_completed: []

# Bolt Dependencies (for execution ordering)
requires_bolts: [004-device-integration, 005-batch-recipe-management, 006-weighing-station]
enables_bolts: [017-assisted-weighing-station-ui]
requires_units: []  # unit ordering is enforced through requires_bolts (see body)
blocks: true

# Complexity Assessment (aggregate of included stories)
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 3
workbook_step: "STEP 19"
---

# Bolt: 007-assisted-weighing-station-ui

## Overview

Terminal shell (header, clock, status bar) and View 1 · Select batch, fed only by the APIs. Serves workbook STEP 19.

## Objective

Terminal shell (header, clock, status bar) and View 1 · Select batch, fed only by the APIs.

## Stories Included

- **001-terminal-shell-and-status-bar**: a header and status bar that always show where I am and whether the devices work (Must)
- **002-select-batch-view**: the Select batch screen with the live queue (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [ ] **1. Plan**: Pending → implementation-plan.md
- [ ] **2. Implement**: Pending → source code + implementation-walkthrough.md
- [ ] **3. Test**: Pending → tests + test-walkthrough.md

## Expected Outcome

- Base template, local Alpine.js, CSS reproducing the prototype
- View 1: scan prompt, queue rows from `GET /api/batches`, touch/scan selection, error messages
- Header and status bar on every view

## Test Expectations

- Playwright: queue rows come from the API, select B-24187 by touch and scan, errors, status change on a toggled Dummy
- Workbook STEP 19 Network + screen evidence
- No batch array in templates/JS

## Dependencies

### Requires
- 004-device-integration
- 005-batch-recipe-management
- 006-weighing-station

### Unit Dependencies (cross-unit, satisfied through the bolts above)
- 003-device-integration
- 004-batch-recipe-management
- 005-weighing-station
- 006-ticket-printing

### Enables
- 017-assisted-weighing-station-ui

## Success Criteria

- [ ] All stories implemented
- [ ] All acceptance criteria met
- [ ] Tests passing (`npm test`; Playwright where listed)
- [ ] Code reviewed

## Notes

- Dummy APIs are training contracts, not the real OrgaTEX / device interfaces.
- Architecture (STEP 12 decision): the browser calls the Dummy APIs directly through one JS client per integration; the WeighingMS server stays the authority (re-reads the scale for confirmation, stores records, supplies write-back payload/key and ticket content).
