---
id: 005-batch-recipe-management
unit: 004-batch-recipe-management
intent: 001-assisted-weighing-station
type: ddd-construction-bolt
status: in-progress
stories:
  - 001-view-batch-queue
  - 002-select-batch
  - 003-load-read-only-recipe
created: 2026-11-20T05:15:14Z
started: 2026-11-20T08:37:50Z
completed: null
current_stage: test
stages_completed:
  - name: model
    completed: 2026-11-20T08:42:11Z
    artifact: ddd-01-domain-model.md
  - name: design
    completed: 2026-11-20T08:45:16Z
    artifact: ddd-02-technical-design.md
  - name: adr
    completed: 2026-11-20T08:48:48Z
    artifact: adr-001-server-authoritative-selection.md, adr-002-station-api-namespace.md, adr-003-immutable-recipe-snapshot.md
  - name: implement
    completed: 2026-11-20T08:52:43Z
    artifact: src/batches/

# Bolt Dependencies (for execution ordering)
requires_bolts: [003-orgatex-integration, 004-device-integration]
enables_bolts: [007-assisted-weighing-station-ui, 008-batch-recipe-management, 009-weighing-station]
requires_units: []  # unit ordering is enforced through requires_bolts (see body)
blocks: true

# Complexity Assessment (aggregate of included stories)
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
workbook_step: "STEP 19"
---

# Bolt: 005-batch-recipe-management

## Overview

Batch queue, selection and read-only recipe snapshot as a domain model. Serves workbook STEP 19.

## Objective

Batch queue, selection and read-only recipe snapshot as a domain model.

## Stories Included

- **001-view-batch-queue**: to see the batches waiting at my station (Must)
- **002-select-batch**: to open a batch by scanning its card or touching its row (Must)
- **003-load-read-only-recipe**: the recipe of the selected batch shown in sequence (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [x] **1. Domain Model**: ✅ Complete → ddd-01-domain-model.md
- [x] **2. Technical Design**: ✅ Complete → ddd-02-technical-design.md
- [x] **3. ADR Analysis (optional)**: ✅ Complete (ADR-001, ADR-002, ADR-003) → adr-*.md
- [x] **4. Implement**: ✅ Complete → source code
- [ ] **5. Test**: ⏳ Awaiting approval → ddd-03-test-report.md

## Expected Outcome

- `batches` app: Batch / Recipe / RecipeComponent snapshot (Decimal), selection rules (Batch not found; Recipe not available in training data), queue received time
- WeighingMS endpoints for selecting a batch (server snapshots the recipe via the OrgaTEX adapter)

## Test Expectations

- Django tests: queue from Dummy, unavailable, select ok / not found / not selectable, recipe order and values, no edit path, ≤ 3 s

## Dependencies

### Requires
- 003-orgatex-integration
- 004-device-integration

### Unit Dependencies (cross-unit, satisfied through the bolts above)
- 002-orgatex-integration
- 003-device-integration

### Enables
- 007-assisted-weighing-station-ui
- 008-batch-recipe-management
- 009-weighing-station

## Success Criteria

- [ ] All stories implemented
- [ ] All acceptance criteria met
- [ ] Tests passing (`npm test`; Playwright where listed)
- [ ] Code reviewed

## Notes

- Dummy APIs are training contracts, not the real OrgaTEX / device interfaces.
- Architecture (STEP 12 decision): the browser calls the Dummy APIs directly through one JS client per integration; the WeighingMS server stays the authority (re-reads the scale for confirmation, stores records, supplies write-back payload/key and ticket content).
