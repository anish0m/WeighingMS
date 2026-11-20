---
id: 006-weighing-station
unit: 005-weighing-station
intent: 001-assisted-weighing-station
type: ddd-construction-bolt
status: in-progress
stories:
  - 001-identify-operator
created: 2026-11-20T05:15:14Z
started: 2026-11-20T09:02:10Z
completed: null
current_stage: design
stages_completed:
  - name: model
    completed: 2026-11-20T09:16:48Z
    artifact: ddd-01-domain-model.md

# Bolt Dependencies (for execution ordering)
requires_bolts: [001-dummy-integrations]
enables_bolts: [007-assisted-weighing-station-ui, 009-weighing-station, 010-weighing-station, 012-weighing-station]
requires_units: []  # unit ordering is enforced through requires_bolts (see body)
blocks: true

# Complexity Assessment (aggregate of included stories)
complexity:
  avg_complexity: 1
  avg_uncertainty: 1
  max_dependencies: 1
  testing_scope: 2
workbook_step: "STEP 19"
---

# Bolt: 006-weighing-station

## Overview

Weighing-session foundation: operator and supervisor identities and the WeighingSession aggregate. Serves workbook STEP 19.

## Objective

Weighing-session foundation: operator and supervisor identities and the WeighingSession aggregate.

## Stories Included

- **001-identify-operator**: to choose myself from the operator list before weighing (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [x] **1. Domain Model**: ✅ Complete → ddd-01-domain-model.md
- [ ] **2. Technical Design**: ⏳ Awaiting approval → ddd-02-technical-design.md
- [ ] **3. ADR Analysis (optional)**: Pending → adr-*.md
- [ ] **4. Implement**: Pending → source code
- [ ] **5. Test**: Pending → ddd-03-test-report.md

## Expected Outcome

- `weighing` app: seeded Operator (R. Karim · Shift A) and Supervisor (ID + PIN), WeighingSession skeleton, operator choice at session start, refusal without operator

## Test Expectations

- Django tests: seeded operators, header data, refusal without operator

## Dependencies

### Requires
- 001-dummy-integrations

### Unit Dependencies (cross-unit, satisfied through the bolts above)
- 004-batch-recipe-management
- 003-device-integration
- 002-orgatex-integration

### Enables
- 007-assisted-weighing-station-ui
- 009-weighing-station
- 010-weighing-station
- 012-weighing-station

## Success Criteria

- [ ] All stories implemented
- [ ] All acceptance criteria met
- [ ] Tests passing (`npm test`; Playwright where listed)
- [ ] Code reviewed

## Notes

- Dummy APIs are training contracts, not the real OrgaTEX / device interfaces.
- Architecture (STEP 12 decision): the browser calls the Dummy APIs directly through one JS client per integration; the WeighingMS server stays the authority (re-reads the scale for confirmation, stores records, supplies write-back payload/key and ticket content).
