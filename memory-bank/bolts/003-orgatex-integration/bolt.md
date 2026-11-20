---
id: 003-orgatex-integration
unit: 002-orgatex-integration
intent: 001-assisted-weighing-station
type: simple-construction-bolt
status: planned
stories:
  - 001-read-batches-and-recipe
created: 2026-11-20T05:15:14Z
started: null
completed: null
current_stage: null
stages_completed: []

# Bolt Dependencies (for execution ordering)
requires_bolts: [001-dummy-integrations]
enables_bolts: [005-batch-recipe-management, 014-orgatex-integration]
requires_units: []  # unit ordering is enforced through requires_bolts (see body)
blocks: true

# Complexity Assessment (aggregate of included stories)
complexity:
  avg_complexity: 1
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
workbook_step: "STEP 19"
---

# Bolt: 003-orgatex-integration

## Overview

OrgaTEX read access: the browser-side OrgaTEX client and the server-side OrgaTEX adapter. Serves workbook STEP 19.

## Objective

OrgaTEX read access: the browser-side OrgaTEX client and the server-side OrgaTEX adapter.

## Stories Included

- **001-read-batches-and-recipe**: one adapter that reads the queue, batch details and recipe from (Dummy) OrgaTEX (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [ ] **1. Plan**: Pending → implementation-plan.md
- [ ] **2. Implement**: Pending → source code + implementation-walkthrough.md
- [ ] **3. Test**: Pending → tests + test-walkthrough.md

## Expected Outcome

- Browser JS OrgaTEX client module (only JS file that knows the OrgaTEX paths): `GET /api/batches`, `/api/batches/:batchId`, `/api/batches/:batchId/recipe` — visible in the Network tab (workbook STEP 19)
- Server Python OrgaTEX adapter (only Python module that knows them), used to snapshot the selected batch's recipe authoritatively
- Unavailable / NotFound results; `Decimal` parsing; IR-09 logging

## Test Expectations

- Django tests: adapter success, NotFound, Unavailable (Dummy toggled)
- Import check: no WeighingMS module imports `dummy_*`

## Dependencies

### Requires
- 001-dummy-integrations

### Unit Dependencies (cross-unit, satisfied through the bolts above)
- 001-dummy-integrations

### Enables
- 005-batch-recipe-management
- 014-orgatex-integration

## Success Criteria

- [ ] All stories implemented
- [ ] All acceptance criteria met
- [ ] Tests passing (`npm test`; Playwright where listed)
- [ ] Code reviewed

## Notes

- Dummy APIs are training contracts, not the real OrgaTEX / device interfaces.
- Architecture (STEP 12 decision): the browser calls the Dummy APIs directly through one JS client per integration; the WeighingMS server stays the authority (re-reads the scale for confirmation, stores records, supplies write-back payload/key and ticket content).
