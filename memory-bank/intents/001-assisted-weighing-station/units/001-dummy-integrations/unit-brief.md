---
unit: 001-dummy-integrations
intent: 001-assisted-weighing-station
phase: inception
status: ready
created: 2026-11-20T04:22:15Z
updated: 2026-11-20T04:51:01Z
---

# Unit Brief: Dummy Integrations (training substitutes)

## Purpose

Provide the training-time Dummy OrgaTEX API, Dummy Scale API, Dummy Scanner and Dummy Printer so WeighingMS can be built and tested without the real systems. These are **training contracts defined by this project, not the real OrgaTEX, scale, scanner or printer interfaces**. The brief's open questions (A-01…A-15) stay unresolved.

## Scope

### In Scope
- Four Django apps, one per Dummy (`dummy_orgatex`, `dummy_scale`, `dummy_scanner`, `dummy_printer`), each with its own state.
- HTTP JSON endpoints (minimum per workbook STEP 16; exact shapes fixed in the Bolt design).
- Seed data from the prototype `components` array and queue.
- Training-only simulate controls and failure toggles.

### Out of Scope
- Any WeighingMS business rule (tolerance, scale selection, progression): Units 004/005.
- WeighingMS-side clients/adapters: Units 002/003.
- Any claim about the real interfaces; the brief's §10.1 endpoint shape is not adopted.

---

## Assigned Requirements

No FR is owned here; this Unit implements the approved training-only Dummy behaviour.

| ID | Requirement | Priority |
|----|-------------|----------|
| DB-1 | Dummy OrgaTEX serves seeded queue B-24187, B-24188, B-24190, B-24191 and batch details | Must |
| DB-2 | Dummy OrgaTEX serves recipe "Teal 4C" for B-24187 with 5 components (code, name, colour, target, unit, tolerance, display max, lot, container, tare); other batches have no recipe (OQ-5) | Must |
| DB-3 | Dummy OrgaTEX accepts and stores consumption posts; same idempotency key → no duplicate | Must |
| DB-4 | Dummy OrgaTEX can be switched to unavailable | Must |
| DB-5 | Dummy Scale: `scale-3kg` and `scale-32kg` return net weight, unit, status | Must |
| DB-6 | Dummy Scale simulate controls: dispense (target + 0.4·tol), overshoot (target + 4.8·tol), reset, set exact weight | Must |
| DB-7 | Dummy Scale tare sets net zero; can be switched to disconnected | Must |
| DB-8 | Dummy Scanner: simulated batch / dyestuff scans; can be switched to unavailable | Must |
| DB-9 | Dummy Printer: accepts, stores and returns tickets; can be switched to error | Must |
| DB-10 | Dummies own their tables; reachable only over HTTP; seeded through Django | Must |

---

## Domain Concepts

### Key Entities
| Entity | Description | Attributes |
|--------|-------------|------------|
| DummyBatch | Seeded OrgaTEX batch | batch_id, order, machine, fabric/lot, shade, status, component count |
| DummyRecipeComponent | Seeded recipe line | sequence, code, name, colour, target, unit, tolerance, display max, lot, container, tare |
| DummyConsumption | Stored write-back | batch_id, idempotency key, per-component actuals, received_at |
| DummyScale | Simulated scale | scale_id, capacity, unit, current net weight, status |
| DummyScan | Simulated scan | kind (batch/dyestuff), code |
| DummyTicket | Stored printed ticket | ticket content, printed_at |
| FailureToggle | Training switch per Dummy | dummy, mode (ok / unavailable / disconnected / error) |

### Key Operations
| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| List / get batch | Queue and batch detail | batch_id | JSON |
| Get recipe | Recipe for a batch | batch_id | JSON components |
| Post consumption | Store write-back | batch_id, key, actuals | accepted / duplicate |
| Get weight / status, tare | Scale reading | scale_id | net weight, unit, status |
| Simulate | Drive scale weight | scale_id, action/value | new weight |
| Scan | Simulated scan | code | scan event |
| Print ticket | Store ticket | ticket | ticket id, preview |
| Toggle failure | Set failure mode | dummy, mode | mode |

---

## Story Summary

- **Total Stories**: 7
- **Must Have**: 7
- **Should Have**: 0
- **Could Have**: 0

### Stories

- [ ] **001-seed-training-scenario**: Seed the prototype training scenario - Must - Planned
- [ ] **002-dummy-orgatex-batch-endpoints**: Dummy OrgaTEX serves batch queue and batch details - Must - Planned
- [ ] **003-dummy-orgatex-recipe-endpoint**: Dummy OrgaTEX serves a batch's recipe - Must - Planned
- [ ] **004-dummy-orgatex-consumption-endpoint**: Dummy OrgaTEX accepts consumption write-back - Must - Planned
- [ ] **005-dummy-scale-api**: Dummy Scale API with tare and simulate controls - Must - Planned
- [ ] **006-dummy-scanner-and-printer**: Dummy Scanner and Dummy Printer - Must - Planned
- [ ] **007-dummy-failure-toggles**: Training failure toggles for every Dummy - Must - Planned

---

## Dependencies

### Depends On
None.

### Depended By
| Unit | Reason |
|------|--------|
| 002-orgatex-integration | Calls Dummy OrgaTEX over HTTP |
| 003-device-integration | Calls Dummy Scale, Scanner, Printer over HTTP |

### External Dependencies
None (it substitutes for them).

---

## Technical Context

### Suggested Technology
Django apps + JSON views, Django ORM on SQLite, seed via management command or fixtures (`memory-bank/standards/`).

### Integration Points
| Integration | Type | Protocol |
|-------------|------|----------|
| WeighingMS adapters (002, 003) | API | HTTP JSON |

### Data Storage
| Data | Type | Volume | Retention |
|------|------|--------|-----------|
| Seed + training state | SQLite | Tiny | Reset by re-seeding |

---

## Constraints

- Quantities as `Decimal` strings in JSON, never floats.
- Seed values come from the prototype; no invented scenario data.
- Must be replaceable/removable without changing WeighingMS domain code.

---

## Success Criteria

### Functional
- [ ] `GET /api/batches`, `/api/batches/B-24187`, `/api/batches/B-24187/recipe` return the prototype values
- [ ] Scales return weight/status; tare and simulate controls work; failure toggles take effect
- [ ] Consumption post is stored once per idempotency key; tickets are stored and returned

### Non-Functional
- [ ] Every Dummy can be switched into its failure mode for tests

### Quality
- [ ] Every approved acceptance criterion has an automated API test (coding standards)

---

## Bolt Suggestions

| Bolt | Type | Objective |
|------|------|-----------|
| dummy-integrations-1 | Simple | Dummy OrgaTEX + seed + API tests (STEP 16–18) |
| dummy-integrations-2 | Simple | Dummy Scale, Scanner, Printer + toggles |

---

## Notes

Endpoint evidence for STEP 17/18 (`STEP-17-dummy-data.json`, `STEP-18-api-tests.txt`) comes from this Unit.
