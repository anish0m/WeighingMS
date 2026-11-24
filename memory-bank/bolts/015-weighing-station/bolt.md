---
id: 015-weighing-station
unit: 005-weighing-station
intent: 001-assisted-weighing-station
type: ddd-construction-bolt
status: complete
stories:
  - 009-complete-batch
  - 011-retrieve-batch-history
created: 2026-11-20T05:15:14.000Z
started: 2026-11-23T10:22:15.000Z
completed: "2026-11-24T03:40:29Z"
current_stage: null
stages_completed:
  - name: model
    completed: 2026-11-23T10:24:09.000Z
    artifact: ddd-01-domain-model.md
  - name: design
    completed: 2026-11-23T10:35:24.000Z
    artifact: ddd-02-technical-design.md
  - name: adr
    completed: 2026-11-23T10:39:21.000Z
    artifact: adr-013-completion-in-last-confirmation.md, adr-014-batch-history-read.md
  - name: implement
    completed: 2026-11-23T10:41:27.000Z
    artifact: source code
  - name: test
    completed: 2026-11-24T03:40:29Z
    artifact: ddd-03-test-report.md
requires_bolts:
  - 010-weighing-station
  - 014-orgatex-integration
enables_bolts:
  - 016-ticket-printing
  - 017-assisted-weighing-station-ui
requires_units: []
blocks: true
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
workbook_step: STEP 26
---

# Bolt: 015-weighing-station

## Overview

Batch completion summary, write-back trigger and batch history. Serves workbook STEP 26.

## Objective

Batch completion summary, write-back trigger and batch history.

## Stories Included

- **009-complete-batch**: the batch to complete when all components are confirmed (Must)
- **011-retrieve-batch-history**: all weighing records of a batch (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [x] **1. Domain Model**: Complete → ddd-01-domain-model.md
- [x] **2. Technical Design**: Complete → ddd-02-technical-design.md
- [x] **3. ADR Analysis (optional)**: Complete → adr-*.md
- [x] **4. Implement**: Complete → source code
- [x] **5. Test**: Complete → ddd-03-test-report.md

## Expected Outcome

- Completion at 5 of 5 only; summary (all within, total 35.322 kg for prototype actuals, elapsed, operator); write-back triggered
- Batch records endpoint (target, actual, operator, scale, lot, container, tare, timestamp)

## Test Expectations

- Django tests: total in Decimal, refusal at 4 of 5, write-back triggered, history fields

## Dependencies

### Requires
- 010-weighing-station
- 014-orgatex-integration

### Unit Dependencies (cross-unit, satisfied through the bolts above)
- 004-batch-recipe-management
- 003-device-integration
- 002-orgatex-integration

### Enables
- 016-ticket-printing
- 017-assisted-weighing-station-ui

## Success Criteria

- [ ] All stories implemented
- [ ] All acceptance criteria met
- [ ] Tests passing (`npm test`; Playwright where listed)
- [ ] Code reviewed

## Notes

- Dummy APIs are training contracts, not the real OrgaTEX / device interfaces.
- Architecture (STEP 12 decision): the browser calls the Dummy APIs directly through one JS client per integration; the WeighingMS server stays the authority (re-reads the scale for confirmation, stores records, supplies write-back payload/key and ticket content).
