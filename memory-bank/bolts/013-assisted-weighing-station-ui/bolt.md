---
id: 013-assisted-weighing-station-ui
unit: 007-assisted-weighing-station-ui
intent: 001-assisted-weighing-station
type: simple-construction-bolt
status: in-progress
stories:
  - 006-weigh-view-surplus-panel-and-override
created: 2026-11-20T05:15:14Z
started: 2026-11-23T09:32:27Z
completed: null
current_stage: implement
stages_completed: [plan]

# Bolt Dependencies (for execution ordering)
requires_bolts: [011-assisted-weighing-station-ui, 012-weighing-station]
enables_bolts: []
requires_units: []  # unit ordering is enforced through requires_bolts (see body)
blocks: true

# Complexity Assessment (aggregate of included stories)
complexity:
  avg_complexity: 1
  avg_uncertainty: 2
  max_dependencies: 1
  testing_scope: 3
workbook_step: "STEP 24"
---

# Bolt: 013-assisted-weighing-station-ui

## Overview

Surplus panel, overshoot status line and supervisor override form on View 2. Serves workbook STEP 24.

## Objective

Surplus panel, overshoot status line and supervisor override form on View 2.

## Stories Included

- **006-weigh-view-surplus-panel-and-override**: to see clearly that I overshot and by how much (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [x] **1. Plan**: Complete → implementation-plan.md
- [ ] **2. Implement**: Pending → source code + implementation-walkthrough.md
- [ ] **3. Test**: Pending → tests + test-walkthrough.md

## Expected Outcome

- Surplus panel showing only what the STEP 24 rule defines (no hard-coded proposal)
- Override form (supervisor ID, PIN, reason) if the rule allows it

## Test Expectations

- Playwright: simulate overshoot → panel values, confirm disabled (workbook STEP 24 UI evidence)

## Dependencies

### Requires
- 011-assisted-weighing-station-ui
- 012-weighing-station

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

## Carried over from bolt 012 (APPROVE TESTS, 2026-11-23)

- Fix the existing training-panel race (bolt 011): `toggle(target)` in `src/station/static/station/training-panel.js` derives the next mode from `this.modes` (last server answer) instead of the checkbox's `checked` state, so a quick uncheck can re-send the failure mode. Symptom: `training-panel.spec.js` › "the OrgaTEX failure switch sets and clears unavailable" fails in the full Playwright run.
- Use bolt 012's server fields only: evaluation `overshoot` (heading, recovery, overrideAvailable, overrideReason), quit `ended.message`. No browser arithmetic, no recalculation table.
