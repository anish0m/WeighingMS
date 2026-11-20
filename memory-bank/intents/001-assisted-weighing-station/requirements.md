---
intent: 001-assisted-weighing-station
phase: inception
status: draft
created: 2026-11-19T10:18:31Z
updated: 2026-11-20T03:33:25Z
---

# Requirements: Assisted Dyestuff Weighing Station (WeighingMS)

> **Status: Intent approved; requirements draft.** This file holds the Intent, approved by the user on 2026-11-20T03:33:25Z (`APPROVE INTENT`): overview, goals, scope, constraints, assumptions and open questions. Detailed functional and non-functional requirements are elaborated next by the `requirements` skill.

## Intent Overview

WeighingMS is a guided weighing station that sits between OrgaTEX MES and the weighing operator in FCI's dyehouse. The recipe arrives digitally from OrgaTEX, the correct scale is selected automatically per component, dispensing is guided in real time against the target, out-of-tolerance weights are refused, every confirmed weighing is recorded, actual consumption is written back to OrgaTEX, and a ticket/label is printed.

**Business problem** (brief §2, §6.1, A-13): today the weighing step is manual and unrecorded. The recipe is printed on paper, the operator weighs by eye, and actual quantities are never captured. When a batch fails shade approval, a bad recipe cannot be told apart from a bad weighing, so the failure cannot be attributed and the error recurs.

**Primary user**: the weighing operator (brief §4). Secondary: dyehouse supervisor (override authority), Lab/QA (shade-failure investigation), store/inventory (consumption reconciliation).

**Type**: New Feature (green-field).

**Training implementation**: this build reproduces the functional experience of the supplied operator-terminal prototype (`docs/customize-weighing-station.html`) and uses **Dummy APIs** for OrgaTEX, the weighing scales, the barcode scanner and the ticket printer. The Dummy APIs are **training contracts** defined by this project. They are **not** the real OrgaTEX, scale, scanner or printer interfaces, and they do not resolve any assumption in brief §12.

### Source artifacts
| Source | Role |
|---|---|
| `docs/brief.md` | Business Requirements Document v1.1 draft (FCI). Business intent, rules (BR), functional (FR), integration (IR), non-functional (NFR) requirements, data model, assumptions register §12. Nothing in it is confirmed by FCI. |
| `docs/customize-weighing-station.html` | Operator-terminal UI/UX prototype. Three views: **1 · Select batch** (OrgaTEX batch queue, barcode), **2 · Weigh** (recipe rail, live weight readout, tolerance band, target/now/left, scale indicator, confirm / re-tare / override / quit, surplus display), **3 · Confirm & print**. Seed scenario: batch B-24187 with five components, plus queued batches. |
| `memory-bank/standards/` | Approved tech-stack, data-stack, coding-standards (constraints on Construction). |

## Business Goals

| Goal | Success Metric | Priority |
|------|----------------|----------|
| BO-01 Eliminate out-of-tolerance weighings reaching production | Confirmation is impossible outside the inclusive tolerance band (e.g. 94.0 ± 0.5 g: 93.5–94.5 g confirmable, 93.4 / 94.6 g refused) | Must |
| BO-02 Component-level traceability for every batch | 100% of confirmed weighings record actual weight, operator, component, lot, container, tare, scale, timestamp | Must |
| BO-04 Reconcile actual vs theoretical consumption | Actual consumption of a completed batch is posted to (Dummy) OrgaTEX | Must |
| Reproduce the prototype's functional experience | All three prototype views and their interactions work against the Dummy APIs, with no hard-coded scenario data in the UI | Must |
| BO-06 Preserve operator throughput (guard) | Baseline to be set by FCI (A-14); not measurable in training | Should |
| BO-03 / BO-05 Reduce weighing-attributable rework and investigation time | Baselines to be set by FCI (A-14); not measurable in training | Could |

---

## Scope

### In scope (brief §5.1, as reproduced in the prototype)
- Batch selection from the (Dummy) OrgaTEX batch queue, by barcode scan or touch
- Digital recipe retrieval per batch
- Automatic scale selection per component: target ≤ 3 kg → 3 kg precision scale; > 3 kg → 32 kg floor scale (configurable threshold, A-06)
- Container tare handling and dyestuff identity verification (scan)
- Real-time guided weighing with live target-vs-actual feedback from the (Dummy) scale
- Inclusive tolerance enforcement at confirmation, using `Decimal` quantities
- Over-dose (surplus) handling and supervisor override with logging (behaviour to be decided by a human, A-08)
- Dyestuff lot capture and component-level weighing records
- Actual-consumption write-back to (Dummy) OrgaTEX
- Weighing ticket/label printing via the (Dummy) printer
- Operator identification
- Dummy OrgaTEX, Scale, Scanner and Printer APIs reachable only over HTTP (IR-07), seeded with the prototype scenario

### Out of scope (brief §5.2)
- Connection to or control of dispensing machines or an automated dye kitchen
- Automated container transport; dissolving stations; liquid dosing; salt/soda bulk systems
- Recipe authoring or modification (recipes stay owned by OrgaTEX, C-01)
- Replacing or modifying any OrgaTEX functionality (C-02)
- Lab colour matching / shade approval; procurement; machine-side dyeing control
- Any real OrgaTEX, scale, scanner or printer integration (training build uses Dummy APIs only)

### To be decided during Requirements
Brief §5.1 also lists **offline operation with deferred synchronisation** (A-03) and **basic operational reporting** (A-11). The prototype does not show either. Whether they are in this training build's scope is an open question (OQ-1, OQ-2 below).

---

## Functional Requirements

To be elaborated by the `requirements` skill after Intent approval (brief §8 FR-01…FR-37 is the source).

## Non-Functional Requirements

To be elaborated by the `requirements` skill after Intent approval (brief §11 NFR-01…NFR-16 is the source; NFR-16 fixed-point quantities is already fixed by the data-stack standard).

---

## Constraints

### Technical Constraints

**Project-wide standards**: Required standards will be loaded from memory-bank standards folder by Construction Agent

**Intent-specific constraints**:
- The UI must obtain all scenario data (batches, recipe, components, tolerances, weights) from the Dummy APIs. No hard-coded batch or recipe data in templates or JS.
- Dummy APIs are training contracts and must be replaceable by real integrations without touching domain logic (IR-07).
- Do not invent real external API contracts; do not present Dummy contracts as OrgaTEX's.

### Business Constraints (brief §13.1)
- C-01 Recipes and batch scheduling remain owned by OrgaTEX; WeighingMS must not become a second source of truth
- C-02 No modification to OrgaTEX is permitted
- C-03 The system must not connect to or control dispensing machinery
- C-05 Operators may have limited computer literacy; the interface must not assume otherwise
- C-06 Physical scale capacities bound what can be weighed

---

## Assumptions

All brief §12 assumptions are **unconfirmed by FCI**. The training build proceeds on them only through Dummy APIs.

| Assumption | Risk if Invalid | Mitigation |
|------------|-----------------|------------|
| A-01 OrgaTEX exposes a documented REST API (queue, recipe, components, tolerances, dyestuff master) | Severe: project premise fails | Dummy OrgaTEX behind one HTTP adapter; replace when D-01 delivers |
| A-02 OrgaTEX accepts actual-consumption postings | Severe: BO-04 unachievable | Dummy write-back endpoint; record stays in WeighingMS regardless |
| A-03 Weighing continues through an OrgaTEX outage and syncs later | Moderate | Scope decision OQ-1 |
| A-04 A ticket printer exists; label content defined by FCI | Low | Dummy printer; label fields from the prototype |
| A-05 Scales stream weight continuously (≥10 Hz) with a stability flag | Severe: live guidance redesigned | Dummy scale simulates continuous readings |
| A-06 Scale selection is rule-based with a threshold; calibration status known | Moderate | Configurable 3 kg threshold |
| A-07 Tolerances are per-component, from OrgaTEX | Moderate | Tolerance supplied by Dummy OrgaTEX per component |
| A-08 Surplus compensation = proportional recalculation; non-compensable → supervisor override | High: most likely misunderstanding | Human decision before implementation (workbook STEP 24); do not copy the prototype's recalculation |
| A-09 Per-operator traceability; lots captured at weighing | Moderate | Record operator and lot on every confirmation |
| A-10 Dyestuffs carry barcodes; English UI; 21-key terminal duplicates touch | Moderate | Dummy scanner; English UI |
| A-11 One station, one site in V1 | Low | Single-station design |
| A-12 Powder dyestuffs and dry auxiliaries only | Moderate | No liquid handling |
| A-13 Today's process is paper-based and unrecorded | High: business case | Not testable in training |
| A-14 Baselines and targets set by FCI later | Low | Metrics left as placeholders |
| A-15 Batch volume fits one station | Moderate | Not tested in training |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Brief §12 / prototype pins: Q6–Q13 OrgaTEX interface (A-01, A-02, A-03); Q15–Q16 scale protocol, threshold, continuous weight (A-05, A-06); Q18 printer and label (A-04); Q24 tolerance definition (A-07); Q25–Q26 surplus compensation (A-08); Q28–Q29 lots and containers (A-09); Q33 override authority (A-08); Q35 language (A-10); Q37 operator login (A-09) | FCI (real product) | Before PRD (brief D-01…D-05) | Pending — unresolved by design; Dummy APIs used in training |
| OQ-1 Is offline operation with deferred sync (A-03) in this training build's scope? | User | Requirements (STEP 7) | Pending |
| OQ-2 Is basic operational reporting in this training build's scope? | User | Requirements (STEP 7) | Pending |
| OQ-3 How are operators identified and supervisors authenticated for overrides (A-09; tech-stack Authentication TBD)? | User | Requirements (STEP 7) | Pending |
| OQ-4 What happens on an over-dose: recalculate remaining, display excess only, or escalate (A-08)? | User | Before the overshoot Bolt (STEP 24) | Pending |
