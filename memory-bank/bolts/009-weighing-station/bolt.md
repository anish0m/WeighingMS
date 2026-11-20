---
id: 009-weighing-station
unit: 005-weighing-station
intent: 001-assisted-weighing-station
type: ddd-construction-bolt
status: planned
stories:
  - 002-select-scale-automatically
  - 004-target-and-remaining
  - 005-evaluate-inclusive-tolerance
created: 2026-11-20T05:15:14Z
started: null
completed: null
current_stage: null
stages_completed: []

# Bolt Dependencies (for execution ordering)
requires_bolts: [005-batch-recipe-management, 006-weighing-station]
enables_bolts: [010-weighing-station, 011-assisted-weighing-station-ui, 012-weighing-station]
requires_units: []  # unit ordering is enforced through requires_bolts (see body)
blocks: true

# Complexity Assessment (aggregate of included stories)
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 1
  testing_scope: 2
workbook_step: "STEP 20"
---

# Bolt: 009-weighing-station

## Overview

Weighing rules: automatic scale selection, target/remaining and inclusive tolerance in Decimal. Serves workbook STEP 20.

## Objective

Weighing rules: automatic scale selection, target/remaining and inclusive tolerance in Decimal.

## Stories Included

- **002-select-scale-automatically**: the station to pick the right scale for each component (Must)
- **004-target-and-remaining**: to see the target and how much is still to weigh (Must)
- **005-evaluate-inclusive-tolerance**: the station to tell me clearly when I am under, near, within or over tolerance (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. Domain Model**: Pending → ddd-01-domain-model.md
- [ ] **2. Technical Design**: Pending → ddd-02-technical-design.md
- [ ] **3. ADR Analysis (optional)**: Pending → adr-*.md
- [ ] **4. Implement**: Pending → source code
- [ ] **5. Test**: Pending → ddd-03-test-report.md

## Expected Outcome

- Scale selection by configurable threshold (3 kg → `scale-3kg`, > 3 kg → `scale-32kg`)
- Target/remaining (never negative), zones under/near/within/over, caption, can_confirm

## Test Expectations

- Django unit tests: 3 kg / 3.0001 kg boundary, changed threshold; 93.4 / 93.5 / 94.0 / 94.5 / 94.6 g (workbook STEP 21–22 evidence)

## Dependencies

### Requires
- 005-batch-recipe-management
- 006-weighing-station

### Unit Dependencies (cross-unit, satisfied through the bolts above)
- 004-batch-recipe-management
- 003-device-integration
- 002-orgatex-integration

### Enables
- 010-weighing-station
- 011-assisted-weighing-station-ui
- 012-weighing-station

## Success Criteria

- [ ] All stories implemented
- [ ] All acceptance criteria met
- [ ] Tests passing (`npm test`; Playwright where listed)
- [ ] Code reviewed

## Notes

- Dummy APIs are training contracts, not the real OrgaTEX / device interfaces.
- Architecture (STEP 12 decision): the browser calls the Dummy APIs directly through one JS client per integration; the WeighingMS server stays the authority (re-reads the scale for confirmation, stores records, supplies write-back payload/key and ticket content).
