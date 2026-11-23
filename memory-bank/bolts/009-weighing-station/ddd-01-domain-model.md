---
stage: model
bolt: 009-weighing-station
created: 2026-11-23T04:44:23Z
---

## Static Model: weighing-station (weighing rules)

### Bounded Context

**Weighing Station**, weighing-rules part. Bolt 006 created the WeighingSession and the operator. Bolt 008 added the material gate (identity, lot, container). This bolt adds the **rules that judge a weight against a component**:

- which scale weighs the component (FR-8, NFR-13, brief FR-07 / BR-05 / AC-02 / A-06);
- the target and how much is still to weigh (FR-10, FR-11, brief FR-14);
- the inclusive tolerance band, the zone, the caption and the status line (FR-12, brief FR-15–FR-17 / BR-07 / BR-09 / A-07).

- **Owned here**:
  - the **ScaleSelectionPolicy** with its configurable threshold;
  - the **ToleranceBand** and the **WeightEvaluation** (zone, still to weigh, surplus, status line, tolerance verdict);
  - the **display format** of weights: 1 decimal for g, 3 for kg.
- **Not owned here**:
  - target, tolerance, unit and display maximum *values*: they come from the recipe snapshot (bolt 005, read-only);
  - reading the scale over HTTP, taring (unit 003 scale adapter);
  - which component is *active*, tare / re-tare / quit, confirming and storing the record (bolt 010). Bolt 010's confirm re-reads the scale on the server and must refuse unless this bolt's evaluation says *within*;
  - the overshoot recovery rule and the surplus panel (OQ-4, decided by a human at STEP 24, bolt 012). This bolt does **not** copy the prototype's recalculation;
  - colours, bar, signals and the "Scale selected" panel on screen (unit 007, bolt 011);
  - supervisor manual reselection and calibration blocking (OQ-9, out of scope).
- **Training contract:** the scales are the **Dummy Scale** devices `scale-3kg` (reports in g, capacity 3000 g) and `scale-32kg` (reports in kg, capacity 32 kg), seeded in bolts 001–002. They are not a real scale protocol; A-05 / A-06 stay open.

### Entities

None new. This bolt stores nothing.

- **SnapshotComponent** (existing, bolt 005, read-only): supplies `sequence`, `target` (Quantity), `tolerance` (Quantity), `unit`, `display_max`.
- **WeighingSession** (existing, bolt 006): the evaluation is asked for one component of one session.

### Value Objects

- **Quantity** (existing): `amount` (Decimal), `unit` (`g` | `kg`). New behaviour: **exact conversion** g ↔ kg (× / ÷ 1000 in Decimal) for comparisons. No float, ever (NFR-16).
- **ScaleThreshold**: `amount` (Decimal, in kg), default **3 kg**. Must be > 0. Read from configuration, never hard-coded in the rule (NFR-13, Decision 3).
- **ScaleClass** (enumeration, the training catalogue):
  - `scale-3kg`: label "3 kg precision", weighs in **g**;
  - `scale-32kg`: label "32 kg floor", weighs in **kg**.
- **ScaleAssignment**: `scale` (ScaleClass), `mode` = `automatic` (always; manual reselection is OQ-9). Derived each time it is asked, so a changed threshold applies the next time a component is activated (story 002 AC 4).
- **ToleranceBand**: `target`, `tolerance`, `low` = target − tolerance, `high` = target + tolerance, `near_from` = 90 % of target. All in the component's unit. **Inclusive**: low ≤ weight ≤ high is within.
  - Caption: `"TOLERANCE ±{tolerance} {unit} ({low} – {high})"` → Yellow RGB: "TOLERANCE ±0.5 g (93.5 – 94.5)" (story 005 AC 2).
- **Zone** (enumeration): `under` | `near` | `within` | `over`, decided in this order:
  1. weight > high → `over`;
  2. weight ≥ low → `within`;
  3. weight ≥ near_from → `near`;
  4. otherwise → `under`.
- **NetWeight**: the net reading (Decimal, unit) from the selected scale, converted to the component's unit (Decision 1) and taken at display resolution (Decision 2).
- **WeightEvaluation**: `net`, `zone`, `still_to_weigh` = max(0, target − net), `surplus` = net − target when `over` (else none), `within_tolerance` (= zone is `within`), `status_line`. Status line by zone:
  - `under` / `near` → "DISPENSE — {still_to_weigh} {unit} REMAINING" (at 90.0 g: "DISPENSE — 4.0 g REMAINING", story 004 AC 2);
  - `within` → "WITHIN TOLERANCE — PRESS OK TO CONFIRM";
  - `over` → "OVER TOLERANCE — SURPLUS +{surplus} {unit}" (Decision 5).
- **DisplayWeight**: a Quantity written with **1 decimal for g, 3 for kg** (FR-10b): "94.0 g", "4.0 g", "0.0 g", "24.000 kg". This is the weighing format. Bolt 008's tare text ("214 g") stays as it is, because story 005's header requires it.

### Aggregates

- **WeighingSession** (root, unit 005): unchanged. No new members. Rules added by this bolt:
  1. The scale of a component is always the one the ScaleSelectionPolicy returns. The operator cannot choose it.
  2. A weight is "within tolerance" only by the ToleranceEvaluator, and the server's verdict is the one that counts (bolt 010 uses it at confirm).
- **BatchSelection** (root, bolt 005): unchanged and read-only.

### Domain Events

None. Selection and evaluation are pure queries and change nothing. The events of a confirmation (WeighingConfirmed, ConfirmationRefused with `OUT_OF_TOLERANCE`) belong to bolt 010.

### Domain Services

- **ScaleSelectionPolicy**: Operations: `select(target: Quantity, threshold: ScaleThreshold) → ScaleAssignment` - Dependencies: none (pure). Rule: target converted to kg; **≤ threshold → `scale-3kg`**, **> threshold → `scale-32kg`**.
  - Yellow RGB 94.0 g (0.094 kg) → `scale-3kg` (AC 1). Blue RSPL 1240.0 g and Red RB 386.0 g → `scale-3kg`.
  - Sodium Sulphate 24.000 kg and Soda Ash 9.600 kg → `scale-32kg`, readings in kg (AC 2).
  - 3 kg → `scale-3kg`; 3.0001 kg → `scale-32kg` (AC 3). The same holds when the target is in g (3000 g / 3000.1 g).
  - With the threshold set to e.g. 0.05 kg, Yellow RGB → `scale-32kg` (AC 4).
- **ToleranceEvaluator**: Operations: `band(component) → ToleranceBand`, `evaluate(component, net) → WeightEvaluation` - Dependencies: none (pure, Decimal only).
  - Yellow RGB 94.0 ± 0.5 g: 93.4 → `near`, not within; 93.5 / 94.0 / 94.5 → `within`; 94.6 → `over`, not within (story 005 AC 1).
  - Below 84.6 g (90 % of 94.0) → `under` (story 005 AC 3).
  - 0.0 g → still to weigh 94.0 g; 90.0 g → 4.0 g; ≥ 94.0 g → 0.0 g, never negative (story 004 AC 1–3).
- **ComponentWeighingView** (read model): Operations: `for(session, sequence) → {target, scale assignment, band, caption}` and, with a reading, the evaluation - Dependencies: the snapshot, ScaleSelectionPolicy, ToleranceEvaluator. Unknown session / component → the refusals from bolt 008 (`SESSION_NOT_FOUND`, `COMPONENT_NOT_FOUND`).

### Repository Interfaces

None new. Read-only use of:

- **WeighingSessionRepository** (bolt 006): `get(session_id)`.
- **BatchSelectionRepository** (bolt 005): the session's snapshot components.
- **Configuration** (not a repository): `scale_threshold_kg → ScaleThreshold`.

### Ubiquitous Language

- **Precision scale**: `scale-3kg`, for targets up to the threshold; weighs in g.
- **Floor scale**: `scale-32kg`, for targets above the threshold; weighs in kg.
- **Threshold**: the configured target size (3 kg) that separates the two scales.
- **Automatic**: the scale was chosen by the rule, not by a person.
- **Target**: the quantity the recipe asks for this component.
- **Weighed now**: the net weight on the selected scale (after tare).
- **Still to weigh**: target − weighed now, never below 0.
- **Tolerance**: the allowed ± deviation from the target (absolute, in the component's unit).
- **Band**: target − tolerance … target + tolerance, ends included.
- **Under / near / within / over**: the zone of the weight. *Near* means at least 90 % of the target but still below the band.
- **Surplus**: how much the weight is above the target when it is over tolerance.

### Story Coverage

- **002-select-scale-automatically**:
  - AC 1 (Yellow RGB → `scale-3kg`, "automatic"): ScaleSelectionPolicy, ScaleAssignment `mode`.
  - AC 2 (Sodium Sulphate → `scale-32kg`, kg): ScaleSelectionPolicy, ScaleClass unit.
  - AC 3 (3 kg / 3.0001 kg): `≤` comparison in Decimal kg.
  - AC 4 (changed threshold): ScaleThreshold from configuration, derived on every request.
- **004-target-and-remaining**:
  - AC 1–3 (94.0 → 94.0; 90.0 → 4.0 and "DISPENSE — 4.0 g REMAINING"; never negative): WeightEvaluation `still_to_weigh`, `status_line`.
  - AC 4 ("24.000 kg"; 1 decimal g, 3 kg): DisplayWeight.
- **005-evaluate-inclusive-tolerance**:
  - AC 1 (five boundary weights): Zone order, inclusive band, `within_tolerance`.
  - AC 2 (caption): ToleranceBand caption.
  - AC 3 (below 90 % → under): Zone rule 4.
  - AC 4 (Decimal only): every value object is Decimal; no float conversion anywhere.

### Decisions for the Human Checkpoint

1. **Reading in a different unit than the component** - Recommended: **convert the reading to the component's unit** (exact Decimal × / ÷ 1000). It matters only when a g component goes above the threshold (e.g. 3000.1 g lands on `scale-32kg`, which reports kg). The seed never does this, but the 3.0001 kg AC can. Alternative: refuse with `UNIT_MISMATCH` and never evaluate.
2. **Display resolution vs evaluation** - Recommended: **take the reading at display resolution** (0.1 g / 0.001 kg, round half up) and use that one value everywhere: shown, evaluated, and stored by bolt 010. The operator then never sees "94.5 g" with OK disabled. Alternative: evaluate the raw reading. A reading of 94.54 g would then show "94.5 g" but count as over.
3. **Where the threshold is configured** - Recommended: **Django setting `WEIGHING_SCALE_THRESHOLD_KG`** (default `3`), which an environment variable of the same name can override. A value that isn't a positive number stops the app at startup. Alternative: a settings constant only (it changes only by editing `settings.py`).
4. **"can_confirm" in this bolt** - Recommended: **this bolt gives the tolerance verdict only (`within_tolerance`)**. Bolt 010's confirm combines it with the material gate (ADR-007) and "scale connected", and only then allows confirmation (FR-13). Story 005's `can_confirm` false / true / true / true / false is tested here as that verdict, and end to end in bolt 010. Alternative: build the full confirm precondition here (it needs the active component and scale state, which belong to bolt 010).
5. **Status line when over** - Recommended: **"OVER TOLERANCE — SURPLUS +0.6 g"** (at 94.6 g). FR-14 requires the surplus to be shown. It is only `net − target`: no percentage, no compensation, no recalculation (those stay with STEP 24 / bolt 012). Alternative: "OVER TOLERANCE" without an amount, leaving all surplus wording to bolt 012.
