---
id: 002-dummy-integrations
unit: 001-dummy-integrations
intent: 001-assisted-weighing-station
type: simple-construction-bolt
status: in-progress
stories:
  - 005-dummy-scale-api
  - 006-dummy-scanner-and-printer
  - 007-dummy-failure-toggles
created: 2026-11-20T05:15:14Z
started: 2026-11-20T06:39:40Z
completed: null
current_stage: test
stages_completed:
  - name: plan
    completed: 2026-11-20T06:48:11Z
    artifact: implementation-plan.md
  - name: implement
    completed: 2026-11-20T06:53:50Z
    artifact: implementation-walkthrough.md

# Bolt Dependencies (for execution ordering)
requires_bolts: [001-dummy-integrations]
enables_bolts: [004-device-integration, 011-assisted-weighing-station-ui, 014-orgatex-integration, 016-ticket-printing]
requires_units: []  # unit ordering is enforced through requires_bolts (see body)
blocks: true

# Complexity Assessment (aggregate of included stories)
complexity:
  avg_complexity: 1
  avg_uncertainty: 1
  max_dependencies: 1
  testing_scope: 2
workbook_step: "STEP 16"
---

# Bolt: 002-dummy-integrations

## Overview

Complete the Dummy layer: Scale, Scanner, Printer and the training failure toggles. Serves workbook STEP 16.

## Objective

Complete the Dummy layer: Scale, Scanner, Printer and the training failure toggles.

## Stories Included

- **005-dummy-scale-api**: two simulated scales whose weight I can drive (Must)
- **006-dummy-scanner-and-printer**: simulated barcode scans and a printer that stores tickets (Must)
- **007-dummy-failure-toggles**: to switch each Dummy into its failure mode and back (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- ✅ **1. Plan**: Approved → implementation-plan.md
- ✅ **2. Implement**: Approved → source code + implementation-walkthrough.md
- ⏳ **3. Test**: In progress → tests + test-walkthrough.md

## Expected Outcome

- `dummy_scale`: `GET /api/scales`, `GET /api/scales/:scaleId/status`, `GET /api/scales/:scaleId/weight`, `POST /api/scales/:scaleId/tare`, training simulate endpoints (dispense target+0.4·tol, overshoot target+4.8·tol, reset, set exact weight)
- `dummy_scanner`: simulated scan submit/read
- `dummy_printer`: `POST /api/tickets` + ticket read
- Failure toggle per Dummy (OrgaTEX unavailable, scale disconnected, scanner unavailable, printer error)

## Test Expectations

- Django API tests per endpoint and per simulate action
- Toggle on/off tests for each Dummy
- Workbook STEP 16 `curl /api/scales`; STEP 18 curl evidence

## Dependencies

### Requires
- 001-dummy-integrations

### Unit Dependencies (cross-unit, satisfied through the bolts above)
- None

### Enables
- 004-device-integration
- 011-assisted-weighing-station-ui
- 014-orgatex-integration
- 016-ticket-printing

## Success Criteria

- [ ] All stories implemented
- [ ] All acceptance criteria met
- [ ] Tests passing (`npm test`; Playwright where listed)
- [ ] Code reviewed

## Notes

- Dummy APIs are training contracts, not the real OrgaTEX / device interfaces.
- Architecture (STEP 12 decision): the browser calls the Dummy APIs directly through one JS client per integration; the WeighingMS server stays the authority (re-reads the scale for confirmation, stores records, supplies write-back payload/key and ticket content).
