---
intent: 001-assisted-weighing-station
phase: inception
status: units-decomposed
updated: 2026-11-20T04:26:59Z
---

# Assisted Dyestuff Weighing Station (WeighingMS) - Unit Decomposition

> **Status: approved 2026-11-20T04:26:59Z (`APPROVE UNITS`, CHECKPOINT 3), 7 units as proposed.**
>
> Project type `full-stack-web` (`memory-bank/project.yaml`): backend Units are decomposed domain-driven (default `ddd-construction-bolt`), plus one frontend Unit `{intent}-ui` (`simple-construction-bolt`). Units are **capabilities, not screens**: the three prototype views (Select batch, Weigh, Confirm & print) are all rendered by the one UI Unit, and the rules behind them live in the backend Units.

## Units Overview

This intent decomposes into 7 units of work.

| # | Unit | Capability | Owns (FR) | Bolt type |
|---|---|---|---|---|
| 1 | `001-dummy-integrations` | Training substitutes: Dummy OrgaTEX, Scale, Scanner, Printer + seed + failure toggles | DB-1…DB-10 (no FR) | Simple |
| 2 | `002-orgatex-integration` | The single OrgaTEX adapter: read queue/batch/recipe, post consumption idempotently | FR-17 | Simple |
| 3 | `003-device-integration` | Scale, Scanner and Printer adapters + device status, fail-safe | FR-9, FR-20 | Simple |
| 4 | `004-batch-recipe-management` | Batch queue, batch selection, recipe and material (identity, lot, container) | FR-1, FR-2, FR-3, FR-4, FR-5, FR-6 | DDD |
| 5 | `005-weighing-station` | Core domain: scale selection, tare, tolerance, confirmation records, overshoot, progression, completion, operator traceability | FR-7, FR-8, FR-10, FR-11, FR-12, FR-13, FR-14, FR-15, FR-16, FR-19 | DDD |
| 6 | `006-ticket-printing` | Weighing ticket content, print, reprint | FR-18 | Simple |
| 7 | `007-assisted-weighing-station-ui` | Operator terminal reproducing the prototype's three views | FR-21 | Simple |

### Unit 1: 001-dummy-integrations

**Description**: Training-time Dummy OrgaTEX API, Dummy Scale API, Dummy Scanner and Dummy Printer. Each is its own Django app (`dummy_*`) with its own state, a training-only failure toggle, and seed data taken from the prototype (B-24187 "Teal 4C" with 5 components, queued B-24188/90/91, scales `scale-3kg` and `scale-32kg`, seeded operator and supervisor). **Training contracts, not the real interfaces.**

- **Responsibility**: stand in for every external party, reachable only over HTTP.
- **Included capabilities**: Dummy OrgaTEX (queue, batch, recipe, consumption store, unavailable), Dummy Scale (two scales, weight/status, tare, simulate dispense/overshoot/reset/set exact weight, disconnected), Dummy Scanner (simulated batch/dyestuff scans, unavailable), Dummy Printer (store ticket, preview, error), seed loading.
- **Why separate**: it replaces systems WeighingMS does not own. It must be removable when real integrations arrive without touching WeighingMS code, and it is built and API-tested first (workbook STEP 16–18).
- **Bolt type**: Simple (endpoints + seed, no domain rules).

**Deliverables**: Dummy apps, HTTP endpoints (minimum per workbook STEP 16), seed command/fixtures, failure toggles, API tests.

**Dependencies**: Depends on: none. Depended by: 002, 003 (over HTTP only).

**Estimated Complexity**: M

### Unit 2: 002-orgatex-integration

**Description**: The single WeighingMS-side OrgaTEX adapter (IR-07). Reads the batch queue, batch details and recipe from (Dummy) OrgaTEX; posts actual consumption with an idempotency key; tracks write-back status and retry; maps failures to "OrgaTEX unavailable" / "not written".

- **Responsibility**: be the only place that knows the OrgaTEX contract.
- **Included capabilities**: queue/batch/recipe client, `Decimal` parsing of quantities, consumption posting with idempotency and retry, write-back status, failure logging (IR-09).
- **Why separate**: brief IR-07 requires all OrgaTEX interaction in one replaceable part; when the real interface is known, only this Unit changes. Its failure modes (unavailable read, ambiguous write) differ from the devices'.
- **Bolt type**: Simple (integration work).

**Deliverables**: OrgaTEX adapter module, write-back status model, adapter tests against Dummy OrgaTEX (including unavailable and retry).

**Dependencies**: Depends on: 001 (HTTP contract). Depended by: 004 (reads), 005 (completion triggers write-back).

**Estimated Complexity**: S

### Unit 3: 003-device-integration

**Description**: WeighingMS-side adapters for the Scale, Scanner and Printer, one module per device, plus the device status shown in the status bar (SCALE 3 kg / SCALE 32 kg / SCANNER / PRINTER; ORGATEX status comes from 002). Supplies live net weight from a named scale, the tare command, scanned codes and the print call, and makes every device failure fail safe.

- **Responsibility**: turn device APIs into reliable readings and commands, never reporting a failure as success.
- **Included capabilities**: scale weight/status polling (≥ 5 Hz, NFR-1), disconnection detection within 2 s, tare command, scanner input, printer submit/result, device status aggregation.
- **Why separate**: devices share one pattern (status, failure toggle, fail-safe, status bar) that is different from OrgaTEX's master-data contract, and the real devices' protocols (A-05, A-10, A-04) will change independently of OrgaTEX. Scanner and Printer adapters are too thin to be Units of their own; each is still its own module, so integrations stay separated.
- **Bolt type**: Simple (integration work).

**Deliverables**: scale, scanner, printer adapter modules; device status service; tests including disconnected / unavailable / error.

**Dependencies**: Depends on: 001 (HTTP contract). Depended by: 004 (scans), 005 (weight, tare, scale status), 006 (printer), 007 (status bar).

**Estimated Complexity**: M

### Unit 4: 004-batch-recipe-management

**Description**: Which batch is weighed and what it consists of. The batch queue and selection (by scan or touch, with "Batch not found" and "Recipe not available in training data"), the recipe and component list in sequence (read-only, cached for resume), and the material identity of each component: dyestuff code verification by scan, lot, container.

- **Responsibility**: provide a selected batch and its verified recipe/material data to the weighing domain.
- **Included capabilities**: Batch Management (FR-1, FR-2) + Recipe & Material Management (FR-3…FR-6), merged.
- **Why separate**: everything here is OrgaTEX-owned, read-only data with its own lifecycle (released → selected), distinct from the weighing rules. Batch and Recipe are merged because selecting a batch *is* loading its recipe and neither is useful alone.
- **Bolt type**: DDD (selection rules, read-only recipe snapshot with `Decimal` values, identity-verification rule).

**Deliverables**: batch/recipe/component read model, selection and identity-verification services, API for the UI, tests.

**Dependencies**: Depends on: 002 (OrgaTEX reads), 003 (scanner). Depended by: 005, 007.

**Estimated Complexity**: M

### Unit 5: 005-weighing-station

**Description**: The weighing domain, not the Weigh screen. Selects the scale per component from a configurable threshold, applies tare, evaluates the weight against the inclusive tolerance in `Decimal`, enforces confirmation preconditions server-side, writes the immutable weighing record (actualWeight, operator, component, lot, container, tare, scale, timestamp, target, tolerance) in one transaction, handles overshoot (rule decided at STEP 24, OQ-4), progresses components, completes the batch and triggers write-back, identifies operator and supervisor, and resumes after reload.

- **Responsibility**: guarantee that only valid, traceable weighings are recorded.
- **Included capabilities**: Weighing Station; scale *selection* (the rule), operator/supervisor identification (OQ-3), weighing records and history retrieval (FR-19c).
- **Why separate**: it holds every business rule the course grades (STEP 21–26) and the system of record. It must be testable without any UI and without real devices.
- **Bolt type**: DDD (domain-heavy: entities, invariants, transactions).

**Deliverables**: WeighingSession/ComponentWeighing/WeighingRecord/Override model, scale-selection, tolerance, confirmation, progression and completion services, configuration (threshold), API for the UI, tests (incl. 93.4/93.5/94.0/94.5/94.6 g and 3 kg boundary).

**Dependencies**: Depends on: 004 (batch + recipe), 003 (weight, tare, status), 002 (write-back on completion). Depended by: 006, 007.

**Estimated Complexity**: L

### Unit 6: 006-ticket-printing

**Description**: Builds the weighing ticket from the completed batch's records (prototype layout: header, batch, order, machine, shade, date/time, operator, per-component target/actual/unit, tolerance summary, batch barcode), sends it through the printer adapter, provides the preview, marks reprints "REPRINT", and reports print failure so it can be printed again.

- **Responsibility**: produce the printed evidence of a completed batch.
- **Included capabilities**: Ticket & Printing.
- **Why separate**: the ticket layout is unconfirmed (A-04, Q18) and will change on its own; printing must never affect the completed batch or its records.
- **Bolt type**: Simple.

**Deliverables**: ticket builder, print/reprint service, print log, tests (content, reprint, printer error).

**Dependencies**: Depends on: 005 (completed batch records), 003 (printer adapter). Depended by: 007.

**Estimated Complexity**: S

### Unit 7: 007-assisted-weighing-station-ui

**Description**: The operator terminal reproducing `docs/customize-weighing-station.html`: view 1 Select batch, view 2 Weigh (recipe rail, live readout, progress bar and tolerance band, target/now/left, scale indicator, scan step, Confirm/Re-tare/Override/Quit, surplus panel), view 3 Confirm & print, header and device status bar. Django templates + Alpine.js served locally. All data comes from WeighingMS APIs, which get it from the Dummies; no scenario data in templates or JS.

- **Responsibility**: present the backend Units' behaviour faithfully and accessibly.
- **Included capabilities**: the three views, F-keys, touch targets, English UI, live polling, prototype fidelity (NFR-8…NFR-11).
- **Why separate**: `full-stack-web` requires one frontend Unit; presentation changes (fidelity, layout) must not alter domain rules, and rules are not allowed to live in templates.
- **Bolt type**: Simple (UI).

**Deliverables**: templates, static CSS/JS (Alpine.js local), page views, Playwright E2E tests.

**Dependencies**: Depends on: 003 (status), 004, 005, 006. Depended by: none.

**Estimated Complexity**: L

## Requirement-to-Unit Mapping

Each FR has exactly one owning Unit. The UI Unit renders the user-facing part of every FR but owns only FR-21.

- **FR-1** Batch queue → `004-batch-recipe-management`
- **FR-2** Batch selection → `004-batch-recipe-management`
- **FR-3** Recipe loading → `004-batch-recipe-management`
- **FR-4** Component identification (dyestuff scan) → `004-batch-recipe-management`
- **FR-5** Dyestuff lot → `004-batch-recipe-management`
- **FR-6** Container → `004-batch-recipe-management`
- **FR-7** Tare / re-tare → `005-weighing-station`
- **FR-8** Scale selection → `005-weighing-station`
- **FR-9** Live weight → `003-device-integration`
- **FR-10** Target quantity → `005-weighing-station`
- **FR-11** Remaining quantity → `005-weighing-station`
- **FR-12** Tolerance → `005-weighing-station`
- **FR-13** Confirmation → `005-weighing-station`
- **FR-14** Overshoot → `005-weighing-station` (rule decided at STEP 24, OQ-4)
- **FR-15** Component progression → `005-weighing-station`
- **FR-16** Batch completion → `005-weighing-station`
- **FR-17** OrgaTEX write-back → `002-orgatex-integration`
- **FR-18** Ticket generation → `006-ticket-printing`
- **FR-19** Operator traceability → `005-weighing-station`
- **FR-20** Scale, scanner and printer failure → `003-device-integration`
- **FR-21** Data only from Dummy APIs over HTTP → `007-assisted-weighing-station-ui` (AC-a no data in templates/JS; AC-b "no Dummy model imports" is also checked in 002 and 003)

### Non-functional and Dummy requirements

| Requirement | Unit(s) |
|---|---|
| NFR-1 weight refresh ≤ 200 ms | 003 (polling), 007 (render) |
| NFR-2 recipe shown ≤ 3 s | 004 |
| NFR-3 one station | all |
| NFR-4 supervisor identity for override | 005 |
| NFR-5 durable confirmation, NFR-6 resume, NFR-12 immutable records | 005 |
| NFR-7 fail-safe devices / OrgaTEX | 002, 003 |
| NFR-8 touch targets, NFR-9 F-keys, NFR-10 fidelity, NFR-11 English | 007 |
| NFR-13 configurable threshold / device config | 005 (threshold), 003 (device config) |
| DB-1…DB-10 Dummy behaviour | 001 |

## Evaluation of the Suggested Capabilities

| Suggested | Decision |
|---|---|
| Batch Management | Merged with Recipe & Material into **004**: selecting a batch loads its recipe; both are read-only OrgaTEX data with one lifecycle |
| Recipe & Material Management | Merged into **004** (see above) |
| Weighing Station | **005**, as a domain Unit (rules + records), not a screen. The Weigh screen is in 007 |
| Scale Integration | Inside **003 Device Integration** with Scanner and Printer: same fail-safe/status pattern; each device keeps its own adapter module. The scale *selection rule* is domain logic in 005 |
| OrgaTEX Integration | **002**, its own Unit (IR-07 single adapter, different contract and failure modes) |
| Ticket & Printing | **006** (ticket content and print lifecycle). The printer *adapter* is in 003 |
| *(added)* Dummy integrations | **001**: the training substitutes, built first, removable later |
| *(added)* UI | **007**: required frontend Unit for `full-stack-web` |

## Unit Dependency Graph

```text
                    ┌──────────────────────────┐
                    │ 001-dummy-integrations   │  (training substitutes, HTTP only)
                    └────────────┬─────────────┘
                 HTTP ┌──────────┴──────────┐ HTTP
                      ▼                     ▼
        ┌──────────────────────┐  ┌──────────────────────┐
        │ 002-orgatex-         │  │ 003-device-          │
        │ integration          │  │ integration          │
        └───┬──────────────┬───┘  └──┬──────┬─────────┬──┘
            │ reads        │ write-   │scans │weight,  │printer, status
            ▼              │ back     ▼      │tare     │
        ┌──────────────────────────┐ │       │         │
        │ 004-batch-recipe-        │◄┘(scan) │         │
        │ management               │         │         │
        └────────────┬─────────────┘         │         │
                     ▼                       │         │
        ┌──────────────────────────┐◄────────┘         │
        │ 005-weighing-station     │◄── write-back (002)│
        └────────────┬─────────────┘                   │
                     ▼                                 │
        ┌──────────────────────────┐◄──────────────────┘
        │ 006-ticket-printing      │
        └────────────┬─────────────┘
                     ▼
        ┌──────────────────────────────────────────────┐
        │ 007-assisted-weighing-station-ui             │ ← 003 (status), 004, 005, 006
        └──────────────────────────────────────────────┘
```

Edges (A → B means B depends on A):

- 001 → 002, 001 → 003 (HTTP only)
- 002 → 004 (reads), 002 → 005 (write-back)
- 003 → 004 (scanner), 003 → 005 (weight, tare, status), 003 → 006 (printer), 003 → 007 (status bar)
- 004 → 005, 004 → 007
- 005 → 006, 005 → 007
- 006 → 007

No cycles.

## Execution Order

Based on dependencies (exact Bolts come at STEP 12):

1. 001-dummy-integrations (workbook STEP 16–18)
2. 002-orgatex-integration (reads for STEP 19, write-back for STEP 26) and 003-device-integration (scale for STEP 21), in parallel
3. 004-batch-recipe-management (STEP 19)
4. 005-weighing-station (STEP 21–26; overshoot pauses for the STEP 24 decision)
5. 006-ticket-printing (STEP 27)
6. 007-assisted-weighing-station-ui, built in slices alongside 004–006 so each view consumes real APIs (STEP 19–20, 23, 28)
