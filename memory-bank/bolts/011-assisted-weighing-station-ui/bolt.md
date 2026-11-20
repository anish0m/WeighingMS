---
id: 011-assisted-weighing-station-ui
unit: 007-assisted-weighing-station-ui
intent: 001-assisted-weighing-station
type: simple-construction-bolt
status: planned
stories:
  - 003-weigh-view-recipe-rail-and-header
  - 004-weigh-view-live-readout-and-tolerance
  - 005-weigh-view-actions-and-function-keys
  - 008-training-simulation-panel
created: 2026-11-20T05:15:14Z
started: null
completed: null
current_stage: null
stages_completed: []

# Bolt Dependencies (for execution ordering)
requires_bolts: [002-dummy-integrations, 004-device-integration, 008-batch-recipe-management, 009-weighing-station, 010-weighing-station]
enables_bolts: [013-assisted-weighing-station-ui, 017-assisted-weighing-station-ui]
requires_units: []  # unit ordering is enforced through requires_bolts (see body)
blocks: true

# Complexity Assessment (aggregate of included stories)
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 3
workbook_step: "STEP 20"
---

# Bolt: 011-assisted-weighing-station-ui

## Overview

View 2 · Weigh: rail, header, scan step, live readout, tolerance band, actions, F-keys and the training panel. Serves workbook STEP 20.

## Objective

View 2 · Weigh: rail, header, scan step, live readout, tolerance band, actions, F-keys and the training panel.

## Stories Included

- **003-weigh-view-recipe-rail-and-header**: to see the recipe, which component is active and its lot/container/tare (Must)
- **004-weigh-view-live-readout-and-tolerance**: a live readout with a coloured bar and tolerance band (Must)
- **005-weigh-view-actions-and-function-keys**: large buttons and F-keys for confirm, re-tare and quit (Must)
- **008-training-simulation-panel**: the prototype's Simulate dispense / overshoot / reset controls and failure switches (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [ ] **1. Plan**: Pending → implementation-plan.md
- [ ] **2. Implement**: Pending → source code + implementation-walkthrough.md
- [ ] **3. Test**: Pending → tests + test-walkthrough.md

## Expected Outcome

- View 2 reproducing the prototype: Component, Code, Lot, Container, Tare, Scale selected, Weighed now, Still to weigh, Target, progress bar, tolerance band and caption, status line, OK · Confirm F1, Re-tare F2, Quit F4, Supervisor override
- Live polling of `GET /api/scales/:scaleId/weight`; zone/can_confirm from the server (no float logic in JS)
- Training panel: Simulate dispense / overshoot / reset / set weight, failure switches

## Test Expectations

- Playwright: readout follows simulate, confirm enabled/disabled at the five boundary weights, scale switch to 32 kg floor + kg, F-keys, ≥ 57 px buttons, five-component flow
- Workbook STEP 20–23, 25 browser evidence

## Dependencies

### Requires
- 002-dummy-integrations
- 004-device-integration
- 008-batch-recipe-management
- 009-weighing-station
- 010-weighing-station

### Unit Dependencies (cross-unit, satisfied through the bolts above)
- 003-device-integration
- 004-batch-recipe-management
- 005-weighing-station
- 006-ticket-printing

### Enables
- 013-assisted-weighing-station-ui
- 017-assisted-weighing-station-ui

## Success Criteria

- [ ] All stories implemented
- [ ] All acceptance criteria met
- [ ] Tests passing (`npm test`; Playwright where listed)
- [ ] Code reviewed

## Notes

- Dummy APIs are training contracts, not the real OrgaTEX / device interfaces.
- Architecture (STEP 12 decision): the browser calls the Dummy APIs directly through one JS client per integration; the WeighingMS server stays the authority (re-reads the scale for confirmation, stores records, supplies write-back payload/key and ticket content).
