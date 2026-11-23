---
intent: 001-assisted-weighing-station
phase: inception
status: complete
created: 2026-11-19T10:18:31Z
updated: 2026-11-20T03:57:49Z
---

# Requirements: Assisted Dyestuff Weighing Station (WeighingMS)

> **Status: Intent approved (2026-11-20T03:33:25Z, `APPROVE INTENT`); Requirements approved 2026-11-20T03:57:49Z (CHECKPOINT 2, `APPROVE REQUIREMENTS`), accepted as written including the proposed training defaults for OQ-1–OQ-3 and OQ-5–OQ-9; OQ-4 decided at workbook STEP 24 (2026-11-23T08:50:18Z, user DECISION: overweight stays unconfirmed, defined recovery action, no recalculation).**
>
> **How to read this file.** Nothing in `docs/brief.md` is confirmed by FCI. In this file:
> - **Confirmed requirements** (FR/NFR) = behaviour stated by the brief and/or shown in the prototype, adopted for this training build once approved here. Each cites its source.
> - **Assumptions** = brief §12 positions the build relies on but nobody has confirmed.
> - **Unresolved questions** = open items. FCI-level questions stay unresolved; training-build questions carry the training decision accepted at CHECKPOINT 2; OQ-4 was decided at STEP 24.
> - **Training-only Dummy behaviour** = how the Dummy OrgaTEX/Scale/Scanner/Printer behave. These are training contracts, not real interfaces.

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
- Over-dose (surplus) handling: blocked, signalled, defined recovery action; no recalculation and no supervisor override in the training build (OQ-4, decided at STEP 24; A-08 unresolved)
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
Brief §5.1 also lists **offline operation with deferred synchronisation** (A-03) and **basic operational reporting** (A-11). The prototype does not show either. Whether they are in this training build's scope is an unresolved question (OQ-1, OQ-2 below).

---

## Functional Requirements (confirmed for this build once approved)

Sources: brief §7 (BR), §8 (FR-xx), §9 (data), §10 (IR), §15 (AC); prototype views 1 · Select batch, 2 · Weigh, 3 · Confirm & print. Brief IDs are written `brief FR-xx` to distinguish them from this file's `FR-n`. All quantities are `Decimal` (data-stack standard).

### FR-1: Batch queue
- **Description**: The Select batch screen shows the batch queue released for this station, obtained from the Dummy OrgaTEX API. Each row shows batch, order, machine, fabric/lot, shade, component count and status. The screen shows the time the queue was received from OrgaTEX.
- **Acceptance Criteria**: (a) With the seed data, the queue lists B-24187, B-24188, B-24190, B-24191 with the prototype's values. (b) The queue data comes from an HTTP call to the Dummy OrgaTEX API; no batch list exists in templates or JS. (c) If Dummy OrgaTEX is unavailable, the screen shows an "OrgaTEX unavailable" message instead of an empty or stale list.
- **Priority**: Must
- **Source**: brief FR-01, BR-01, IR-01; prototype view 1; workbook STEP 19

### FR-2: Batch selection
- **Description**: The operator selects a batch by scanning its batch barcode (Dummy Scanner) or by touching its row. The station header then shows batch, order and machine. A batch that is not in a selectable state, or that is unknown, is rejected with the reason shown.
- **Acceptance Criteria**: (a) Scanning or touching B-24187 opens it. (b) An unknown batch ID shows "Batch not found" and nothing opens. (c) A batch that is not selectable shows the reason (see OQ-5) and nothing opens.
- **Priority**: Must
- **Source**: brief FR-02, FR-03, FR-04, BR-02, BR-03; AC-01; prototype view 1 ("Scan a batch card to begin / Or touch a row below")

### FR-3: Recipe loading
- **Description**: On selection, the recipe and its component list are retrieved from Dummy OrgaTEX and shown as the recipe rail in recipe sequence: name, code, scale class, target quantity with unit, and state (done with actual / weighing / pending), plus "n of N components weighed". Recipes are read-only (C-01).
- **Acceptance Criteria**: (a) B-24187 shows recipe "Teal 4C" with 5 components in the order Blue RSPL, Red RB, Yellow RGB, Sodium Sulphate, Soda Ash and the prototype's targets, units and tolerances. (b) Recipe data comes from the Dummy OrgaTEX API only. (c) WeighingMS offers no way to edit a recipe. (d) If the recipe cannot be retrieved, weighing does not start and the reason is shown.
- **Priority**: Must
- **Source**: brief FR-05, FR-06, BR-04, IR-02; NFR-02; prototype recipe rail

### FR-4: Component identification
- **Description**: For the active component the Weigh screen shows its name, code, lot, container and tare. Before dispensing is accepted, the dyestuff identity is verified by scanning the dyestuff barcode (Dummy Scanner) against the active component's code. A mismatch is refused.
- **Acceptance Criteria**: (a) Active component header shows e.g. "Remazol Yellow RGB · DYE-4471 · LOT 2026-0387 · CONTAINER C-12 · TARE 214 g". (b) Scanning the matching code marks identity verified. (c) Scanning a different code shows "Wrong dyestuff" and confirmation stays blocked. (d) Confirmation is impossible until identity is verified.
- **Priority**: Must
- **Source**: brief FR-09, BR-10, IR-15; prototype w-meta line. See A-10 / OQ-8 (prototype draws no scan step for the dyestuff).

### FR-5: Dyestuff lot
- **Description**: The lot of the dyestuff being consumed is captured for every weighing and shown on the Weigh screen.
- **Acceptance Criteria**: (a) The active component shows its lot (e.g. 2026-0387). (b) Every confirmed weighing record stores the lot. (c) Confirmation is impossible without a lot.
- **Priority**: Must
- **Source**: brief FR-10, BR-11, IR-04; prototype "LOT"; Q28 / A-09 (where the lot comes from is unresolved, OQ-7)

### FR-6: Container
- **Description**: The container used for the active component is identified and shown, and stored on the weighing record.
- **Acceptance Criteria**: (a) The active component shows its container (e.g. C-12, D-03). (b) Every confirmed weighing record stores the container ID.
- **Priority**: Must
- **Source**: brief §9.2 CONTAINER, WEIGHING_RECORD.container_id; prototype "CONTAINER"; Q29 (container identity unresolved, OQ-7)

### FR-7: Tare
- **Description**: The container tare is applied so the weight shown is net of the container. The tare value is shown. The operator can re-tare, which resets the net reading to zero and restarts the component's weighing.
- **Acceptance Criteria**: (a) The active component shows its tare (214 g for C-12; 1.850 kg for D-03). (b) After tare, an empty container reads 0.0 g / 0.000 kg net. (c) Re-tare (F2) resets the net reading to zero. (d) The tare used is stored on the confirmed weighing record.
- **Priority**: Must
- **Source**: brief FR-11, IR-12; prototype TARE and "Re-tare F2"

### FR-8: Scale selection
- **Description**: The system selects the scale per component from its target quantity: target ≤ 3 kg → 3 kg precision scale; target > 3 kg → 32 kg floor scale. The threshold is configurable without code change. The selected scale is shown as "automatic"; units follow the component (g for precision, kg for floor in the seed). The operator cannot change the scale.
- **Acceptance Criteria**: (a) Yellow RGB (94.0 g) → 3 kg precision. (b) Sodium Sulphate (24.000 kg) → 32 kg floor and units switch to kg. (c) Exactly 3 kg → precision; 3.0001 kg → floor. (d) Changing the configured threshold changes the selection without code change. (e) The live weight is read from the selected scale only.
- **Priority**: Must
- **Source**: brief FR-07, BR-05, AC-02, A-06; prototype "Scale selected · automatic", "Touch Sodium Sulphate … the scale switches to the 32 kg floor scale"; workbook STEP 21. Manual reselection by supervisor (brief FR-08) and calibration blocking (brief FR-12, BR-24, AC-14) are in OQ-9.

### FR-9: Live weight
- **Description**: While a component is active, the Weigh screen shows the current net weight from the selected (Dummy) scale, updating continuously, with a progress bar scaled to the component's display maximum and the tolerance band marked.
- **Acceptance Criteria**: (a) "Weighed now" updates as the Dummy scale weight changes, without page reload. (b) The weight shown is the value returned by the Dummy Scale API. (c) The progress bar fill reflects weight / display maximum, and the band marks target − tol to target + tol.
- **Priority**: Must
- **Source**: brief FR-13, FR-15, BR-06, IR-10, AC-03, A-05; prototype "Weighed now", progress bar, band, target line

### FR-10: Target quantity
- **Description**: The active component's target quantity and unit are shown, as supplied by the recipe.
- **Acceptance Criteria**: (a) Yellow RGB shows "Target 94.0 g"; Sodium Sulphate shows "24.000 kg". (b) Display precision: 1 decimal for g, 3 decimals for kg. (c) The target is snapshotted onto the weighing record at confirmation.
- **Priority**: Must
- **Source**: brief FR-14, §9.2 target_qty snapshot; prototype "Target"

### FR-11: Remaining quantity
- **Description**: "Still to weigh" = max(0, target − current net weight), shown in the component's unit, and the status line reads "DISPENSE — x REMAINING" while below tolerance.
- **Acceptance Criteria**: (a) At 0.0 g on Yellow RGB: 94.0 g remaining. (b) At 90.0 g: 4.0 g. (c) At or above target: 0.0 (never negative).
- **Priority**: Must
- **Source**: brief FR-14; prototype "Still to weigh", status line

### FR-12: Tolerance
- **Description**: Each component carries a tolerance from the recipe (absolute ± value in the component's unit in the seed). The band target − tol … target + tol is **inclusive**. The weight is evaluated into zones: under, near (≥ 90 % of target, below band), within, over. The screen shows "TOLERANCE ±tol (low – high)", colours the readout/bar by zone, and signals entering tolerance and exceeding it distinctly.
- **Acceptance Criteria** (Yellow RGB 94.0 ± 0.5 g): 93.4 g → not within (confirm disabled); 93.5 g → within; 94.0 g → within; 94.5 g → within; 94.6 g → over (confirm disabled). Caption reads "TOLERANCE ±0.5 g (93.5 – 94.5)". Evaluation uses Decimal. Tolerance min/max are snapshotted onto the weighing record.
- **Priority**: Must
- **Source**: brief FR-15–FR-17, BR-07, BR-09, A-07; prototype zone logic and caption; workbook STEP 22

### FR-13: Confirmation
- **Description**: "OK · Confirm" (F1) is enabled only while the weight is within tolerance and the preconditions are met (identity verified, lot present, scale connected). On confirm the system records a weighing record and only then advances.
- **Acceptance Criteria**: (a) Confirm is disabled outside tolerance (see FR-12) and enabled inside it. (b) A confirm request sent to the server with an out-of-tolerance weight is rejected server-side (not only by the disabled button). (c) The record contains: actual weight, unit, operator, component, lot, container, tare, scale, target, tolerance min/max, result, timestamp (UTC). (d) The record is persisted in one DB transaction before the UI advances, and is immutable afterwards (corrections are new records). (e) Quit (F4) abandons the active component's current attempt without recording and restarts it.
- **Priority**: Must
- **Source**: brief FR-18, FR-19, FR-25, BR-07, BR-11, DR-02, NFR-05, AC-04; prototype "OK · Confirm F1", "Quit F4"; workbook STEP 25

### FR-14: Overshoot
- **Description**: When the weight exceeds the upper tolerance, the system shows "OVER TOLERANCE — SURPLUS +x", shows the surplus panel with surplus amount and percentage, and keeps confirmation blocked. **Training rule (OQ-4, decided 2026-11-23 at STEP 24):** an overweight component remains unconfirmed and the operator must use the defined recovery action: either remove material until the weight is back inside the band and confirm normally, or Quit F4 (discard and re-weigh), which starts a fresh attempt. An attempt abandoned while over tolerance is stored as an overshoot discard with its surplus, and no weighing record is created. No recipe recalculation is performed, and the prototype's recalculation proposal is not shown. "Supervisor override" stays visible but disabled under this rule. Full record: `docs/evidence/STEP-24-overshoot-decision.md`.
- **Acceptance Criteria**: (a) Yellow RGB at 96.4 g shows "Surplus +2.4 g (+2.6%)" and confirm is disabled. (b) No remaining-component target changes automatically. (c) Every override or compensation applied is recorded with who authorised it and why. Under the STEP 24 rule none can be applied, so (c) is not applicable to the training build. (d) Quit F4 while over tolerance records an overshoot discard and no weighing record; reducing the weight into the band allows confirmation.
- **Priority**: Must
- **Source**: brief FR-20–FR-24, BR-08, BR-13, AC-05, AC-06, A-08, Q25/Q26/Q33; prototype surplus panel ("Proposal: … deliberately a guess"); workbook STEP 24

### FR-15: Component progression
- **Description**: Components progress in recipe sequence. After a confirmation, the confirmed component is shown as done with its actual weight, and the next pending component becomes active with its scale, units, tolerance and tare loaded. A component cannot be completed without a valid (within-tolerance, or later-approved override) weight. The operator may touch a pending component to make it active; done components cannot be reopened.
- **Acceptance Criteria**: (a) Confirming Blue RSPL → Red RB → Yellow RGB → Sodium Sulphate → Soda Ash advances in that order. (b) The rail counter increments ("n of 5 components weighed"). (c) Touching a done component does nothing. (d) Moving from Yellow RGB to Sodium Sulphate switches the scale to 32 kg floor and units to kg.
- **Priority**: Must
- **Source**: brief FR-06, §6.2; prototype select()/rail; workbook STEP 23

### FR-16: Batch completion
- **Description**: When all components are confirmed, the batch is complete and the Confirm & print screen shows: components weighed n of N, all within tolerance YES/NO, total dispensed (kg), elapsed time, operator, OrgaTEX write-back status and time. A batch cannot complete while any component is unconfirmed.
- **Acceptance Criteria**: (a) After the 5th confirmation, view 3 opens showing "Components weighed 5 of 5". (b) Total dispensed = sum of actuals converted to kg (Decimal), e.g. 35.322 kg for the prototype actuals. (c) With 4 of 5 confirmed, completion is impossible.
- **Priority**: Must
- **Source**: brief §6.2, FR-25; prototype view 3; workbook STEP 23, 26

### FR-17: OrgaTEX write-back
- **Description**: On batch completion, the actual consumption per component is posted to Dummy OrgaTEX against the batch, through the single OrgaTEX adapter. The UI shows "Written to OrgaTEX CONFIRMED hh:mm:ss" only after Dummy OrgaTEX accepts it. Posting is idempotent: a retry must not double-post. If the post fails, the UI shows it as not written, the records stay in WeighingMS, and the operator can retry.
- **Acceptance Criteria**: (a) Completing B-24187 sends `POST` consumption for B-24187 to Dummy OrgaTEX, which returns success and stores the consumption record. (b) UI shows CONFIRMED with time only after success. (c) Retrying the same post does not create a second consumption record. (d) With Dummy OrgaTEX failing, UI shows "not written" and a retry action; never CONFIRMED.
- **Priority**: Must
- **Source**: brief FR-26, BR-12, IR-05, IR-07, IR-08, IR-09, AC-08, A-02; prototype "Written to OrgaTEX CONFIRMED"; workbook STEP 26

### FR-18: Ticket generation
- **Description**: On batch completion, a weighing ticket is generated and sent to the Dummy Printer ("Print ticket" F1), with a print preview. Content follows the prototype: header "FCI DYEING — WEIGHING TICKET", batch, order, machine, shade, date/time, operator, per component name/target/actual/unit, tolerance summary ("ALL WITHIN TOLERANCE") and a batch barcode. A reprint is marked as a reprint. "Next batch" (F3) returns to the queue.
- **Acceptance Criteria**: (a) Printing B-24187 produces a ticket containing all listed fields with the confirmed actuals. (b) The Dummy Printer stores/returns the printed ticket. (c) A second print is marked "REPRINT". (d) Printer failure is shown and the ticket can be printed again later (see FR-20).
- **Priority**: Must
- **Source**: brief FR-27, FR-28, BR-15, IR-16, AC-10, A-04; prototype ticket ("Label content is invented", Q18); workbook STEP 27

### FR-19: Operator traceability
- **Description**: An operator is identified at session start and shown in the header ("Operator R. Karim · Shift A"). Every confirmed weighing, override, compensation and write-back is attributable to that operator. Any past batch's weighings can be retrieved (target, actual, operator, scale, lot, container, tare, timestamp).
- **Acceptance Criteria**: (a) No weighing can start without an identified operator. (b) Every weighing record stores the operator ID. (c) The weighing records of B-24187 can be retrieved after completion with all traceability fields (e.g. through an API or page).
- **Priority**: Must
- **Source**: brief FR-25, FR-29, FR-34, BR-11, BR-14, BR-19, AC-07, A-09, Q37; prototype header. Identification method: OQ-3.

### FR-20: Scale, scanner and printer failure
- **Description**: Device failures fail safe and are visible. The status bar shows each device's state (SCALE 3 kg / SCALE 32 kg / SCANNER / PRINTER / ORGATEX). Scale disconnected or unavailable → live weight shows unavailable and confirmation is blocked. Scanner unavailable → scan-based steps cannot complete (batch can still be chosen by touch). Printer unavailable or error → ticket reported as not printed and can be printed again; the completed batch and its records are unaffected.
- **Acceptance Criteria**: (a) With the Dummy Scale set to disconnected, status shows the scale not ready and confirm is disabled within 2 s. (b) With the Dummy Scanner failing, a scan shows an error and changes nothing. (c) With the Dummy Printer failing, "Print ticket" reports failure, nothing is marked printed, and a later print succeeds once the printer is restored. (d) No device failure is ever shown as success.
- **Priority**: Must
- **Source**: brief IR-13, IR-18, IR-09; prototype status bar; coding-standards (fail-safe integrations)

### FR-21: Data only from Dummy APIs over HTTP
- **Description**: The UI obtains batches, recipes, components, tolerances, weights and print results only from the Dummy APIs over HTTP. WeighingMS reaches each external system only through one adapter per integration.
- **Acceptance Criteria**: (a) No batch, recipe or component array exists in templates or JS. (b) Domain code does not import Dummy app models.
- **Priority**: Must
- **Source**: brief IR-07; workbook STEP 19 ("Do not hard-code const batches"); CLAUDE.md domain rules

---

## Non-Functional Requirements

Project-wide rules (Decimal quantities, UTC timestamps, migrations, error format, logging) live in `memory-bank/standards/` and are not repeated here.

### Performance
| Requirement | Metric | Target | Source |
|-------------|--------|--------|--------|
| NFR-1 Live weight refresh | Interval between displayed weight updates | ≤ 200 ms (Dummy scale polled at ≥ 5 Hz; brief's 10 Hz is a real-scale assumption, A-05) | brief NFR-01, IR-10 |
| NFR-2 Recipe display | Batch selection → recipe shown (local) | ≤ 3 s | brief NFR-02, AC-01 |

### Scalability
| Requirement | Metric | Target | Source |
|-------------|--------|--------|--------|
| NFR-3 Scope | Stations / sites | One station, one site (no multi-station features) | A-11 |

### Security
| Requirement | Standard | Notes | Source |
|-------------|----------|-------|--------|
| NFR-4 Privileged actions | Supervisor identity required for override | Method per OQ-3; no shared credentials between roles | brief NFR-12, FR-35, FR-36 |

### Reliability
| Requirement | Metric | Target | Source |
|-------------|--------|--------|--------|
| NFR-5 Durability | Confirmed weighing persisted before UI advances | 100 % (single DB transaction) | brief NFR-05 |
| NFR-6 Resume | Reload / restart during a batch | Batch reopens at the in-progress component with prior confirmations kept | brief NFR-06 |
| NFR-7 Fail-safe devices | Device or OrgaTEX failure shown as success | Never | brief IR-13, IR-09 |

### Usability
| Requirement | Metric | Target | Source |
|-------------|--------|--------|--------|
| NFR-8 Touch targets | Primary action button size | ≥ 15 mm (≈ 57 px at 96 dpi) | brief NFR-07, BR-20 |
| NFR-9 Function keys | OK/Re-tare/Quit/Print/Next reachable by key | F1 Confirm, F2 Re-tare, F4 Quit; F1 Print, F3 Next batch on view 3 | prototype; brief IR-17 |
| NFR-10 Fidelity | Prototype views, labels, units, states reproduced | All three views match the prototype (workbook STEP 28 comparison) | Intent goal |
| NFR-11 Language | Interface language | English; operator-facing text not scattered in logic | brief FR-37, NFR-11, A-10 |

### Compliance / Auditability
| Requirement | Standard | Notes | Source |
|-------------|----------|-------|--------|
| NFR-12 Immutable records | Weighing, override, compensation records | Not editable or deletable through the app; corrections are new records | brief DR-02, NFR-13 |
| NFR-13 Configuration | Scale threshold, station/device config | Changeable without code change (settings/config) | brief NFR-14 |

---

## Training-only Dummy Behaviour (training contracts, not real interfaces)

These describe what the Dummy systems do in this build. They are **not** the real OrgaTEX, scale, scanner or printer contracts. The brief's illustrative OrgaTEX endpoint shape (§10.1, "for FCI/SETEX to correct") is **not** adopted as a real contract; exact Dummy endpoints are defined in the approved API contract (System Context / Units).

| ID | Dummy | Training behaviour |
|----|-------|--------------------|
| DB-1 | Dummy OrgaTEX | Serves the seeded queue (B-24187, B-24188, B-24190, B-24191) and batch details from the prototype. |
| DB-2 | Dummy OrgaTEX | Serves recipe "Teal 4C" for B-24187 with the prototype's 5 components (code, name, colour, target, unit, tolerance, display max, lot, container, tare). Recipes for other batches: OQ-5. |
| DB-3 | Dummy OrgaTEX | Accepts consumption posts for a batch, stores them, returns success; same idempotency key → no duplicate. |
| DB-4 | Dummy OrgaTEX | Can be switched to "unavailable" for failure tests. |
| DB-5 | Dummy Scale | Two scales: 3 kg precision and 32 kg floor. Returns current net weight, unit and status (ready / disconnected) per scale. |
| DB-6 | Dummy Scale | Weight is driven for training by controls equivalent to the prototype's "Simulate dispense" (lands inside tolerance, target + 0.4·tol), "Simulate overshoot" (target + 4.8·tol) and reset, plus "set exact weight" (for 93.4 / 93.5 / 94.0 / 94.5 / 94.6 g tests). |
| DB-7 | Dummy Scale | Tare command sets net zero; can be switched to "disconnected". |
| DB-8 | Dummy Scanner | Simulated scans of a batch barcode or a dyestuff code; can be switched to "unavailable". |
| DB-9 | Dummy Printer | Accepts a ticket, stores it, returns it for preview; can be switched to "error". |
| DB-10 | All Dummies | State lives in their own Django app(s)/tables; reachable only over HTTP from WeighingMS (IR-07). Seed data is loaded through Django from the prototype values. |

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
| A-08 Surplus compensation = proportional recalculation; non-compensable → supervisor override | High: most likely misunderstanding | Decided for training at STEP 24 (OQ-4): no recalculation, no override; A-08 itself stays unresolved |
| A-09 Per-operator traceability; lots captured at weighing | Moderate | Record operator and lot on every confirmation |
| A-10 Dyestuffs carry barcodes; English UI; 21-key terminal duplicates touch | Moderate | Dummy scanner; English UI |
| A-11 One station, one site in V1 | Low | Single-station design |
| A-12 Powder dyestuffs and dry auxiliaries only | Moderate | No liquid handling |
| A-13 Today's process is paper-based and unrecorded | High: business case | Not testable in training |
| A-14 Baselines and targets set by FCI later | Low | Metrics left as placeholders |
| A-15 Batch volume fits one station | Moderate | Not tested in training |

---

## Unresolved Questions

### FCI-level (real product) — stay unresolved by design
| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Prototype pins / brief §9: Q6–Q13 OrgaTEX interface (A-01, A-02, A-03); Q15–Q16 scale protocol, threshold, continuous weight (A-05, A-06); Q18 printer and label (A-04); Q24 tolerance definition (A-07); Q25–Q26 surplus compensation (A-08); Q28–Q29 lots and containers (A-09); Q33 override authority (A-08); Q35 language (A-10); Q37 operator login (A-09) | FCI (real product) | Before PRD (brief D-01…D-05) | Pending. Dummy APIs used in training; none of these is answered by this build |

### Training build — decisions (defaults accepted by the user at CHECKPOINT 2, 2026-11-20T03:57:49Z; OQ-4 decided at STEP 24, 2026-11-23T08:50:18Z)
| ID | Question | Training decision | Owner | Status |
|----|----------|-------------------|-------|--------|
| OQ-1 | Is offline operation with deferred sync (brief FR-30–33, A-03) in scope? | **Out of scope.** Only write-back failure + retry (FR-17) is built. | User | Accepted (CHECKPOINT 2) |
| OQ-2 | Is operational reporting / supervisor remote view (BR-22, BR-23) in scope? | **Out of scope** beyond retrieving a batch's weighing records (FR-19c). | User | Accepted (CHECKPOINT 2) |
| OQ-3 | How is the operator identified, and how is the supervisor authenticated for override? | Operator chosen from a seeded operator list at session start (no password; seed "R. Karim · Shift A"). Supervisor override needs a seeded supervisor's ID + PIN and a reason, recorded. | User | Accepted (CHECKPOINT 2) |
| OQ-4 | Overshoot rule: recalculate remaining components, display excess only, or escalate? | Overweight stays unconfirmed; recovery = remove excess back into the band, or Quit F4 (discard and re-weigh, logged as overshoot discard). No recalculation, no supervisor override. | User | Decided 2026-11-23T08:50:18Z (STEP 24 DECISION) |
| OQ-5 | The prototype has a recipe only for B-24187. What happens when B-24188/B-24190/B-24191 are selected? | They are listed (QUEUED) but not selectable: "Recipe not available in training data". | User | Accepted (CHECKPOINT 2) |
| OQ-6 | Does the seeded B-24187 start with all 5 components pending, or mid-batch as in the prototype (2 of 5 done)? | **All 5 pending**, so the full five-component flow can be demonstrated (workbook STEP 23). The prototype's actuals (1241.5 g, 385.4 g …) are not pre-seeded. | User | Accepted (CHECKPOINT 2) |
| OQ-7 | Where do lot and container come from (Q28, Q29)? | Supplied per component by Dummy OrgaTEX seed (prototype values); not entered by the operator. | User | Accepted (CHECKPOINT 2) |
| OQ-8 | The prototype draws no dyestuff-scan step. Is identity verification (FR-4) by Dummy Scanner required before confirm? | Yes: a "Scan dyestuff" step on the Weigh screen; mismatch blocks confirm. | User | Accepted (CHECKPOINT 2) |
| OQ-9 | Are calibration blocking (brief FR-12, BR-24, AC-14) and supervisor manual scale reselection (brief FR-08) in scope? | **Out of scope** for training; Dummy scales are always in calibration. | User | Accepted (CHECKPOINT 2) |
