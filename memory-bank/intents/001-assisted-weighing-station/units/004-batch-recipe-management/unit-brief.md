---
unit: 004-batch-recipe-management
intent: 001-assisted-weighing-station
phase: inception
default_bolt_type: ddd-construction-bolt
status: complete
created: 2026-11-20T04:22:15Z
updated: 2026-11-20T04:51:01Z
---

# Unit Brief: Batch & Recipe Management

## Purpose

Decide which batch is weighed and what it consists of: the batch queue, batch selection, the read-only recipe in sequence, and the material identity of each component (dyestuff code verification, lot, container). Merges the suggested "Batch Management" and "Recipe & Material Management", because selecting a batch is loading its recipe.

## Scope

### In Scope
- Queue read model (from 002) with received time; "OrgaTEX unavailable" state.
- Selection by scan or touch; "Batch not found"; non-selectable with reason ("Recipe not available in training data", OQ-5).
- Recipe snapshot in sequence, cached locally for resume (brief DR-03: cache never authoritative); recipes never editable.
- Dyestuff identity verification against the active component's code; "Wrong dyestuff" blocks confirmation.
- Lot and container per component from the Dummy OrgaTEX seed (OQ-7).

### Out of Scope
- Weighing, tolerance, confirmation, records (005).
- Talking to OrgaTEX or the scanner directly (002, 003).
- Screens (007).

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Batch queue from Dummy OrgaTEX with received time; unavailable message | Must |
| FR-2 | Select by scan or touch; unknown → "Batch not found"; not selectable → reason | Must |
| FR-3 | Recipe "Teal 4C" with 5 components in sequence, read-only; failure → weighing does not start | Must |
| FR-4 | Dyestuff scan verifies identity; mismatch "Wrong dyestuff"; confirm blocked until verified | Must |
| FR-5 | Lot captured and shown for every component | Must |
| FR-6 | Container identified, shown, available for the record | Must |

Also supports: NFR-2 (recipe shown ≤ 3 s).

---

## Domain Concepts

### Key Entities
| Entity | Description | Attributes |
|--------|-------------|------------|
| Batch | Snapshot of an OrgaTEX batch | batch_id, order, machine, fabric/lot, shade, status, selectable, received_at |
| Recipe | Read-only recipe of a batch | name, components (ordered) |
| RecipeComponent | One line | sequence, code, name, colour, target (Decimal), unit, tolerance (Decimal), display max, lot, container, tare |
| IdentityCheck | Result of a dyestuff scan | component, scanned code, verified, at |

### Key Operations
| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| list_queue | Queue for the station | – | batches or Unavailable |
| select_batch | Open a batch | batch_id (scan/touch) | Batch + Recipe or NotFound / NotSelectable |
| verify_identity | Check dyestuff code | component, scanned code | verified / WrongDyestuff |

---

## Story Summary

- **Total Stories**: 5
- **Must Have**: 5
- **Should Have**: 0
- **Could Have**: 0

### Stories

- [ ] **001-view-batch-queue**: See the batch queue released for the station - Must - Planned
- [ ] **002-select-batch**: Select a batch by scan or touch - Must - Planned
- [ ] **003-load-read-only-recipe**: Load the batch's recipe read-only - Must - Planned
- [ ] **004-verify-dyestuff-identity**: Verify the dyestuff by scanning it - Must - Planned
- [ ] **005-show-lot-and-container**: Show lot, container and tare of the active component - Must - Planned

---

## Dependencies

### Depends On
| Unit | Reason |
|------|--------|
| 002-orgatex-integration | Queue, batch and recipe reads |
| 003-device-integration | Batch and dyestuff scans |

### Depended By
| Unit | Reason |
|------|--------|
| 005-weighing-station | Weighs the selected batch's components |
| 007-assisted-weighing-station-ui | Select batch view, recipe rail, component header |

### External Dependencies
None directly (via 002/003).

---

## Technical Context

### Suggested Technology
Django app (e.g. `batches`) with plain-Python services; Django ORM for the snapshot.

### Integration Points
| Integration | Type | Protocol |
|-------------|------|----------|
| 002 adapter | Python call | – |
| 007 UI | API | HTTP JSON |

### Data Storage
| Data | Type | Volume | Retention |
|------|------|--------|-----------|
| Batch / recipe snapshot | SQLite | Few batches | With weighing records |

---

## Constraints

- C-01: recipes are read-only; WeighingMS is never a second source of truth.
- `Decimal` quantities.

---

## Success Criteria

### Functional
- [ ] Queue lists B-24187, B-24188, B-24190, B-24191 with prototype values from the Dummy API
- [ ] B-24187 opens with "Teal 4C" and 5 components in order; others show the reason
- [ ] Wrong dyestuff code blocks confirmation

### Non-Functional
- [ ] Recipe shown ≤ 3 s after selection

### Quality
- [ ] Every approved acceptance criterion has an automated test

---

## Bolt Suggestions

| Bolt | Type | Objective |
|------|------|-----------|
| batch-recipe-1 | DDD | Queue, selection, recipe snapshot (STEP 19) |
| batch-recipe-2 | DDD | Identity verification, lot, container |
