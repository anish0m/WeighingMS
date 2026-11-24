---
id: 016-ticket-printing
unit: 006-ticket-printing
intent: 001-assisted-weighing-station
type: simple-construction-bolt
status: in-progress
stories:
  - 001-print-weighing-ticket
  - 002-reprint-and-print-failure
created: 2026-11-20T05:15:14Z
started: 2026-11-24T03:42:20Z
completed: null
current_stage: plan
stages_completed: []

# Bolt Dependencies (for execution ordering)
requires_bolts: [002-dummy-integrations, 004-device-integration, 015-weighing-station]
enables_bolts: [017-assisted-weighing-station-ui]
requires_units: []  # unit ordering is enforced through requires_bolts (see body)
blocks: true

# Complexity Assessment (aggregate of included stories)
complexity:
  avg_complexity: 1
  avg_uncertainty: 2
  max_dependencies: 2
  testing_scope: 2
workbook_step: "STEP 26"
---

# Bolt: 016-ticket-printing

## Overview

Weighing ticket content, print, preview, reprint and printer failure. Serves workbook STEP 26.

## Objective

Weighing ticket content, print, preview, reprint and printer failure.

## Stories Included

- **001-print-weighing-ticket**: to print a ticket for the completed batch (Must)
- **002-reprint-and-print-failure**: to reprint a ticket and be told when printing failed (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [ ] **1. Plan**: Pending → implementation-plan.md
- [ ] **2. Implement**: Pending → source code + implementation-walkthrough.md
- [ ] **3. Test**: Pending → tests + test-walkthrough.md

## Expected Outcome

- `tickets` app: ticket built from stored records (prototype layout), print log, REPRINT marker
- Browser printer client sends `POST /api/tickets`; result reported to the server

## Test Expectations

- Django tests: ticket fields for B-24187, reprint marker, printer error and recovery (workbook STEP 27 evidence)

## Dependencies

### Requires
- 002-dummy-integrations
- 004-device-integration
- 015-weighing-station

### Unit Dependencies (cross-unit, satisfied through the bolts above)
- 005-weighing-station
- 003-device-integration

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
- Runs at STEP 26 because View 3 (bolt 017) needs it; workbook STEP 27 then verifies the ticket and collects evidence.
