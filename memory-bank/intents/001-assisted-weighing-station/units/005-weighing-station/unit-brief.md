---
unit: 005-weighing-station
intent: 001-assisted-weighing-station
phase: inception
default_bolt_type: ddd-construction-bolt
status: complete
created: 2026-11-20T04:22:15.000Z
updated: 2026-11-20T04:51:01.000Z
---

# Unit Brief: Weighing Station (domain)

## Purpose

The weighing domain and system of record, not the Weigh screen. It guarantees that only valid, traceable weighings are recorded: scale selection, tare, inclusive tolerance in `Decimal`, server-side confirmation, immutable records, overshoot handling, component progression, batch completion, operator/supervisor identity and resume.

## Scope

### In Scope
- Scale selection: target ≤ threshold (3 kg) → `scale-3kg`, > threshold → `scale-32kg`; threshold configurable.
- Tare / re-tare (via 003); Quit restarts the component's attempt without recording.
- Target, remaining (never negative), zones (under / near ≥ 90 % / within / over), inclusive band.
- Confirmation preconditions (within tolerance, identity verified, lot present, scale connected), checked server-side.
- Weighing record in one transaction: actual weight, unit, operator, component, lot, container, tare, scale, target, tolerance min/max, result, UTC timestamp; immutable.
- Overshoot: surplus shown, confirm blocked; recovery rule decided by a human at STEP 24 (OQ-4).
- Progression in recipe sequence; touch a pending component; done cannot reopen.
- Completion summary (n of N, all within, total kg, elapsed, operator) and trigger of write-back (002).
- Operator chosen from seeded list; supervisor ID + PIN + reason (OQ-3); batch history retrieval.
- Resume after reload (NFR-6).

### Out of Scope
- Fetching batches/recipes, identity scan (004); device I/O (003); posting to OrgaTEX (002); ticket (006); screens (007).
- Offline sync (OQ-1), reporting (OQ-2), calibration blocking / manual reselection (OQ-9).

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-7 | Tare applied and shown; re-tare (F2) resets net to zero; tare stored on record | Must |
| FR-8 | Scale selection by configurable threshold (3 kg → precision, 3.0001 kg → floor); weight read from selected scale only | Must |
| FR-10 | Target quantity and unit; 1 dp g, 3 dp kg; snapshotted on record | Must |
| FR-11 | Remaining = max(0, target − net) | Must |
| FR-12 | Inclusive tolerance zones; 93.4 ✗, 93.5 ✓, 94.0 ✓, 94.5 ✓, 94.6 ✗ | Must |
| FR-13 | Confirm only when within + preconditions; rejected server-side otherwise; record persisted in one transaction, immutable; Quit restarts | Must |
| FR-14 | Overshoot: surplus shown, confirm blocked, no automatic recalculation; rule per STEP 24 | Must |
| FR-15 | Progression in recipe order; counter; scale/unit switch | Must |
| FR-16 | Batch completion summary; cannot complete with unconfirmed components; total 35.322 kg for prototype actuals | Must |
| FR-19 | Operator identified; every record attributable; batch records retrievable | Must |

Also supports: NFR-4, NFR-5, NFR-6, NFR-12, NFR-13 (threshold).

---

## Domain Concepts

### Key Entities
| Entity | Description | Attributes |
|--------|-------------|------------|
| Operator / Supervisor | Seeded identities | id, name, shift; supervisor PIN |
| WeighingSession | Weighing of one batch | batch, operator, started_at, state, completed_at |
| ComponentWeighing | Progress of one component | component, scale, tare, state (pending / active / done) |
| WeighingRecord | Immutable confirmation | actual weight, unit, operator, component, lot, container, tare, scale, target, tol min/max, result, timestamp |
| Override | Supervisor decision (after STEP 24) | supervisor, reason, timestamp, linked record |

### Key Operations
| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| select_scale | Choose scale for target | target, unit, threshold | scale_id |
| evaluate | Zone and remaining | weight, target, tol | zone, remaining, can_confirm |
| confirm | Record a weighing | session, component, weight | WeighingRecord or rejection |
| retare / quit | Restart component attempt | session, component | reset state |
| advance | Next pending component | session | active component |
| complete | Close batch, trigger write-back | session | summary |
| history | Records of a batch | batch_id | records |

---

## Story Summary

- **Total Stories**: 11
- **Must Have**: 11
- **Should Have**: 0
- **Could Have**: 0

### Stories

- [ ] **001-identify-operator**: Identify the operator at session start - Must - Planned
- [ ] **002-select-scale-automatically**: Select the scale automatically from the target - Must - Planned
- [ ] **003-tare-retare-and-quit**: Tare, re-tare and quit a component attempt - Must - Planned
- [ ] **004-target-and-remaining**: Show target and remaining quantity - Must - Planned
- [ ] **005-evaluate-inclusive-tolerance**: Evaluate the weight against the inclusive tolerance - Must - Planned
- [ ] **006-confirm-weighing**: Confirm a weighing and record it - Must - Planned
- [ ] **007-handle-overshoot**: Handle overshoot (rule decided at STEP 24) - Must - Planned
- [ ] **008-progress-components**: Progress through components in recipe order - Must - Planned
- [ ] **009-complete-batch**: Complete the batch and trigger write-back - Must - Planned
- [ ] **010-resume-after-reload**: Resume an in-progress batch after reload - Must - Planned
- [ ] **011-retrieve-batch-history**: Retrieve a batch's weighing records - Must - Planned

---

## Dependencies

### Depends On
| Unit | Reason |
|------|--------|
| 004-batch-recipe-management | Selected batch, recipe, identity status, lot, container |
| 003-device-integration | Weight, tare, scale status |
| 002-orgatex-integration | Write-back on completion |

### Depended By
| Unit | Reason |
|------|--------|
| 006-ticket-printing | Completed batch records |
| 007-assisted-weighing-station-ui | Weigh and Confirm views |

### External Dependencies
None directly.

---

## Technical Context

### Suggested Technology
Django app (e.g. `weighing`) with plain-Python services (`tolerance.py`, `scale_selection.py`, …); threshold in Django settings; `transaction.atomic` for confirmation.

### Integration Points
| Integration | Type | Protocol |
|-------------|------|----------|
| 002, 003, 004 | Python call | – |
| 007 UI | API | HTTP JSON |

### Data Storage
| Data | Type | Volume | Retention |
|------|------|--------|-----------|
| Sessions, weighing records, overrides | SQLite | Small | Kept (immutable) |

---

## Constraints

- `Decimal` only; never float (brief NFR-16).
- Do not copy the prototype's surplus recalculation (≈ remaining × 1.026); OQ-4 is decided by a human at STEP 24.
- Records are never edited or deleted through the app.

---

## Success Criteria

### Functional
- [ ] 94.0 ± 0.5 g: 93.4/94.6 refused, 93.5/94.0/94.5 accepted (also server-side)
- [ ] 3 kg → precision, 3.0001 kg → floor; threshold change needs no code change
- [ ] Five components confirmed in order; record has all traceability fields; completion only at 5 of 5
- [ ] Reload resumes at the in-progress component

### Non-Functional
- [ ] Confirmation persisted before the UI advances

### Quality
- [ ] Every approved acceptance criterion has an automated test

---

## Bolt Suggestions

| Bolt | Type | Objective |
|------|------|-----------|
| weighing-1 | DDD | Scale selection + tolerance (STEP 21–22) |
| weighing-2 | DDD | Confirmation record + progression + completion (STEP 23, 25) |
| weighing-3 | DDD | Overshoot per STEP 24 decision + supervisor override |

---

## Notes

OQ-4 is open. The overshoot Bolt must stop for the human decision before implementation.
