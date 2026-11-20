---
id: 001-dummy-integrations
unit: 001-dummy-integrations
intent: 001-assisted-weighing-station
type: simple-construction-bolt
status: in-progress
stories:
  - 001-seed-training-scenario
  - 002-dummy-orgatex-batch-endpoints
  - 003-dummy-orgatex-recipe-endpoint
  - 004-dummy-orgatex-consumption-endpoint
created: 2026-11-20T05:15:14Z
started: 2026-11-20T05:50:02Z
completed: null
current_stage: implement
stages_completed:
  - name: plan
    completed: 2026-11-20T06:02:26Z
    artifact: implementation-plan.md

# Bolt Dependencies (for execution ordering)
requires_bolts: []
enables_bolts: [002-dummy-integrations, 003-orgatex-integration, 006-weighing-station, 014-orgatex-integration]
requires_units: []  # unit ordering is enforced through requires_bolts (see body)
blocks: false

# Complexity Assessment (aggregate of included stories)
complexity:
  avg_complexity: 1
  avg_uncertainty: 1
  max_dependencies: 1
  testing_scope: 2
workbook_step: "STEP 14–16"
---

# Bolt: 001-dummy-integrations

## Overview

Create the project skeleton and the Dummy OrgaTEX training contract with the prototype seed. Serves workbook STEP 14–16.

## Objective

Create the project skeleton and the Dummy OrgaTEX training contract with the prototype seed.

## Stories Included

- **001-seed-training-scenario**: one command that loads the prototype scenario into the Dummy systems (Must)
- **002-dummy-orgatex-batch-endpoints**: to read the released batch queue and a batch's details from Dummy OrgaTEX over HTTP (Must)
- **003-dummy-orgatex-recipe-endpoint**: to read the recipe and component list of a batch from Dummy OrgaTEX (Must)
- **004-dummy-orgatex-consumption-endpoint**: to post actual consumption for a completed batch to Dummy OrgaTEX (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- ✅ **1. Plan**: Approved → implementation-plan.md
- ⏳ **2. Implement**: In progress → source code + implementation-walkthrough.md
- [ ] **3. Test**: Pending → tests + test-walkthrough.md

## Expected Outcome

- Project skeleton per approved tech stack: `manage.py`, Django project under `src/`, `requirements.txt`, `package.json` with `npm run dev` (runserver :8000) and `npm test` (Django tests), `pyproject.toml` (Ruff), `tests/`
- `dummy_orgatex` app with models, seed command (B-24187 "Teal 4C" + 5 components, B-24188/90/91) and endpoints `GET /api/batches`, `GET /api/batches/:batchId`, `GET /api/batches/:batchId/recipe`, `POST /api/batches/:batchId/consumption`
- Seed also creates the two Dummy scales `scale-3kg`, `scale-32kg` (models come with this bolt; their endpoints in bolt 002)

## Test Expectations

- Django API tests: queue, batch, recipe values equal the prototype, decimal strings (no floats), 404, recipe-not-available, consumption accept / duplicate key / invalid
- Seed idempotency test
- `npm test` passes

## Dependencies

### Requires
- None (first bolt)

### Unit Dependencies (cross-unit, satisfied through the bolts above)
- None

### Enables
- 002-dummy-integrations
- 003-orgatex-integration
- 006-weighing-station
- 014-orgatex-integration

## Success Criteria

- [ ] All stories implemented
- [ ] All acceptance criteria met
- [ ] Tests passing (`npm test`; Playwright where listed)
- [ ] Code reviewed

## Notes

- Dummy APIs are training contracts, not the real OrgaTEX / device interfaces.
- Architecture (STEP 12 decision): the browser calls the Dummy APIs directly through one JS client per integration; the WeighingMS server stays the authority (re-reads the scale for confirmation, stores records, supplies write-back payload/key and ticket content).
- First executable bolt (workbook STEP 14–15). Skeleton work is included because no build tooling exists yet (CLAUDE.md).
- Seed is delivered here, so workbook STEP 17 is verification + JSON export only.
