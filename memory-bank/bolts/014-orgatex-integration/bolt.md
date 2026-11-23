---
id: 014-orgatex-integration
unit: 002-orgatex-integration
intent: 001-assisted-weighing-station
type: simple-construction-bolt
status: in-progress
stories:
  - 002-post-consumption-idempotently
  - 003-write-back-failure-and-retry
created: 2026-11-20T05:15:14Z
started: 2026-11-23T10:09:08Z
completed: null
current_stage: test
stages_completed:
  - name: plan
    completed: 2026-11-23T10:11:18Z
    artifact: implementation-plan.md
  - name: implement
    completed: 2026-11-23T10:14:25Z
    artifact: implementation-walkthrough.md

# Bolt Dependencies (for execution ordering)
requires_bolts: [001-dummy-integrations, 002-dummy-integrations, 003-orgatex-integration]
enables_bolts: [015-weighing-station, 017-assisted-weighing-station-ui]
requires_units: []  # unit ordering is enforced through requires_bolts (see body)
blocks: true

# Complexity Assessment (aggregate of included stories)
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
workbook_step: "STEP 26"
---

# Bolt: 014-orgatex-integration

## Overview

OrgaTEX write-back: idempotent consumption post with visible status and retry. Serves workbook STEP 26.

## Objective

OrgaTEX write-back: idempotent consumption post with visible status and retry.

## Stories Included

- **002-post-consumption-idempotently**: actual consumption of a completed batch posted to (Dummy) OrgaTEX exactly once (Must)
- **003-write-back-failure-and-retry**: to see when consumption was not written to OrgaTEX and to retry it (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [x] **1. Plan**: Complete → implementation-plan.md
- [x] **2. Implement**: Complete → source code + implementation-walkthrough.md
- [ ] **3. Test**: Pending → tests + test-walkthrough.md

## Expected Outcome

- Server prepares the consumption payload and idempotency key and stores write-back status
- Browser OrgaTEX client sends `POST /api/batches/:batchId/consumption` and reports the result to the server (CONFIRMED + time / not written)
- Retry with the same key

## Test Expectations

- Django tests: one post one record, repeat no duplicate, unavailable → not written, retry → CONFIRMED
- Workbook STEP 26 Network evidence

## Dependencies

### Requires
- 001-dummy-integrations
- 002-dummy-integrations
- 003-orgatex-integration

### Unit Dependencies (cross-unit, satisfied through the bolts above)
- 001-dummy-integrations

### Enables
- 015-weighing-station
- 017-assisted-weighing-station-ui

## Success Criteria

- [ ] All stories implemented
- [ ] All acceptance criteria met
- [ ] Tests passing (`npm test`; Playwright where listed)
- [ ] Code reviewed

## Notes

- Dummy APIs are training contracts, not the real OrgaTEX / device interfaces.
- Architecture (STEP 12 decision): the browser calls the Dummy APIs directly through one JS client per integration; the WeighingMS server stays the authority (re-reads the scale for confirmation, stores records, supplies write-back payload/key and ticket content).
