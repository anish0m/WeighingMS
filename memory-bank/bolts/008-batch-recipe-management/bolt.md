---
id: 008-batch-recipe-management
unit: 004-batch-recipe-management
intent: 001-assisted-weighing-station
type: ddd-construction-bolt
status: in-progress
stories:
  - 004-verify-dyestuff-identity
  - 005-show-lot-and-container
created: 2026-11-20T05:15:14Z
started: 2026-11-23T03:52:11Z
completed: null
current_stage: implement
stages_completed:
  - name: model
    completed: 2026-11-23T03:54:07Z
    artifact: ddd-01-domain-model.md
  - name: design
    completed: 2026-11-23T03:56:02Z
    artifact: ddd-02-technical-design.md
  - name: adr
    completed: 2026-11-23T04:01:39Z
    artifact: adr-006-server-verifies-dyestuff-scan.md, adr-007-identity-checks-in-weighing-session.md

# Bolt Dependencies (for execution ordering)
requires_bolts: [005-batch-recipe-management]
enables_bolts: [010-weighing-station, 011-assisted-weighing-station-ui]
requires_units: []  # unit ordering is enforced through requires_bolts (see body)
blocks: true

# Complexity Assessment (aggregate of included stories)
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
workbook_step: "STEP 20"
---

# Bolt: 008-batch-recipe-management

## Overview

Material identity: dyestuff scan verification, lot, container and tare per component. Serves workbook STEP 20.

## Objective

Material identity: dyestuff scan verification, lot, container and tare per component.

## Stories Included

- **004-verify-dyestuff-identity**: to scan the dyestuff before dispensing (Must)
- **005-show-lot-and-container**: the lot, container and tare of each component shown and kept (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [x] **1. Domain Model**: ✅ Complete → ddd-01-domain-model.md
- [x] **2. Technical Design**: ✅ Complete → ddd-02-technical-design.md
- [x] **3. ADR Analysis (optional)**: ✅ Complete → adr-*.md
- [ ] **4. Implement**: ⏳ Awaiting approval → source code
- [ ] **5. Test**: Pending → ddd-03-test-report.md

## Expected Outcome

- IdentityCheck model and verify service (Wrong dyestuff blocks confirm)
- Lot / container / tare exposed for the component header and the record

## Test Expectations

- Django tests: match, mismatch, unverified confirm refused, header values (C-12 214 g, D-03 1.850 kg), missing lot refused

## Dependencies

### Requires
- 005-batch-recipe-management

### Unit Dependencies (cross-unit, satisfied through the bolts above)
- 002-orgatex-integration
- 003-device-integration

### Enables
- 010-weighing-station
- 011-assisted-weighing-station-ui

## Success Criteria

- [ ] All stories implemented
- [ ] All acceptance criteria met
- [ ] Tests passing (`npm test`; Playwright where listed)
- [ ] Code reviewed

## Notes

- Dummy APIs are training contracts, not the real OrgaTEX / device interfaces.
- Architecture (STEP 12 decision): the browser calls the Dummy APIs directly through one JS client per integration; the WeighingMS server stays the authority (re-reads the scale for confirmation, stores records, supplies write-back payload/key and ticket content).
