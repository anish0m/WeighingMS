---
stage: model
bolt: 012-weighing-station
created: 2026-11-23T08:52:26Z
---

## Static Model: weighing-station (overshoot)

### Bounded Context

**Weighing Station**, overshoot part. Earlier bolts built the parts this bolt uses:
- **bolt 009:** WeightEvaluation, with the zone `over` and `surplus` = net − target;
- **bolt 010:** ComponentAttempt, QuitService, and ConfirmationService, which refuses `OUT_OF_TOLERANCE`.

This bolt applies the **training rule decided at workbook STEP 24 (OQ-4, 2026-11-23T08:50:18Z)**:

> For this training implementation, an overweight component remains unconfirmed and the operator must use the defined recovery action. No automatic recipe recalculation will be performed unless explicitly specified by the approved business rule.

What it covers:
- **Signalled** (FR-14, brief FR-17 / FR-20): the surplus as an amount and a percentage, in `Decimal`, plus the recovery instruction.
- **Blocked** (FR-13b, FR-18): nothing over tolerance is confirmed; already true since bolt 010, and kept.
- **Defined recovery action** (BR-08, brief "Discard and re-weigh"):
  - **(a)** remove material until the weight is back inside the band, then confirm normally; or
  - **(b)** Quit F4, which means discard and re-weigh.
- **Audit:** a Quit while over tolerance is stored as an **overshoot discard** with its surplus. No weighing record is created.
- **No recalculation, no override** (FR-14b, story 007 AC 2): no target ever changes, and Supervisor override is not available under this rule.

**Owned here:**
- the **OvershootRule** (the approved training rule);
- the **Surplus** value (amount and percentage);
- the **overshoot discard** end of an attempt.

**Not owned here:**
- the band and the zone (bolt 009, called and not re-implemented);
- tare, quit and confirm mechanics (bolt 010, extended only for the discard);
- the surplus panel and the disabled Supervisor override button (unit 007, bolt 013);
- the recipe targets, which come from the OrgaTEX snapshot and are never written here.

**Training contract:** the weight comes from the **Dummy Scale**. Its "Simulate overshoot" control lands at target + 4.8 · tolerance (Yellow RGB: 96.4 g). The brief's A-08, Q25, Q26 and Q33 stay **unresolved**; this rule is the training build's answer only.

### Entities

- **ComponentAttempt** (existing, bolt 010): gains a **discard snapshot**, written once, only when the attempt ends as `overshoot_discarded`:
  - `end_net`: the evaluated net that was discarded, at display resolution;
  - `end_surplus`: net − target;
  - `end_unit`: the component's unit.
  The attempt stays append-only: these fields are set once, at the end, together with `ended_at`.
- **WeighingRecord** (existing, bolt 010): **unchanged**. `result` stays `within` only, because no override exists under this rule. No record is ever created for an over-tolerance weight.
- **WeighingSession** and the **recipe snapshot** (existing): unchanged. Targets are read-only.

### Value Objects

- **Surplus**: `amount` = net − target (> 0), and `percent` = amount ÷ target × 100.
  - Both are `Decimal`. The amount is at the display resolution of the unit (0.1 g / 0.001 kg, ADR-009). The percent is rounded to 0.1 with ROUND_HALF_UP.
  - It exists only when the zone is `over`.
  - Texts:
    - status line (bolt 009, unchanged): "OVER TOLERANCE — SURPLUS +2.4 g";
    - panel heading: "Surplus +2.4 g (+2.6%) — over tolerance".
  - Example: Yellow RGB at 96.4 g gives 2.4 g, and 2.4 ÷ 94.0 × 100 = 2.553… % → **+2.6%**.
  - At 94.6 g: 0.6 g, and 0.638… % → +0.6%.
- **OvershootRule** (the approved training rule, one fixed value):
  - `confirm_allowed = false`;
  - `recalculation = none`;
  - `override_available = false`, with the reason "Supervisor override is not available in this training build";
  - `recovery_text` = "Remove material until the weight is back in the band, or press Quit (F4) to discard and re-weigh."
  It is defined in code, not in a setting. Changing it needs a new approved business rule (OQ-4).
- **OvershootView** (part of the WeightEvaluation when the zone is `over`): the Surplus, the OvershootRule texts and `override_available`. The UI shows only these server values (ADR-008).
- **AttemptEnd** (existing enumeration): gains **`overshoot_discarded`**. The full set is: `confirmed`, `quit`, `retared`, `switched`, `overshoot_discarded`.

### Aggregates

- **WeighingSession** (root): Members: IdentityCheck*, ComponentAttempt*, WeighingRecord*.

  Invariants added or confirmed by this bolt:
  1. **Over is never confirmed.** A confirm whose server re-read evaluates `over` is refused with `OUT_OF_TOLERANCE` and stores nothing. This was already invariant 4.7 of bolt 010 and is kept unchanged.
  2. **Targets never change.** No operation in this bolt writes a component target, a tolerance or the recipe snapshot. The prototype's proportional proposal is not computed.
  3. **The discard snapshot belongs to the discard.**
     - `end_net`, `end_surplus` and `end_unit` are set if and only if `end_reason = overshoot_discarded`.
     - That end reason is set only when the **server's own re-read at Quit** evaluates `over`.
  4. **Discard, like quit, starts a new untared attempt** for the same component (bolt 010, Decision 2). The operator empties the container and presses Re-tare (F2) before weighing again.
  5. **Recovery (a) needs nothing new.** When the weight comes back into the band, the normal confirm applies, and the recorded actual weight is the within-tolerance value.

### Domain Events

Recorded as log entries (logger `weighing.confirmation`, as in bolt 010):

- **OvershootDiscarded**:
  - Trigger: Quit while the server's re-read evaluates `over`.
  - Payload: `session_id`, `sequence`, `attempt_id`, `net`, `surplus`, `percent`, `unit`, `operator_id`.
  - It replaces AttemptQuit for that quit.
- **ConfirmationRefused** (existing): for `OUT_OF_TOLERANCE` with zone `over`, the payload also carries `surplus`.
- **AttemptQuit** (existing): unchanged for a quit that is not over tolerance, or when the scale could not be read (see Decision 3).

### Domain Services

- **ToleranceEvaluator** (existing, bolt 009): `evaluate(component, net)` adds the **Surplus** (amount and percent) and the **OvershootView** when the zone is `over`. It stays pure and `Decimal` only.
- **QuitService** (existing, bolt 010): `quit(session, sequence)` now:
  1. checks operator and active component (unchanged);
  2. tries to **re-read the attempt's scale**, outside the transaction (ADR-011);
  3. if the reading evaluates `over`, ends the attempt as `overshoot_discarded` with the discard snapshot; otherwise ends it as `quit`;
  4. starts the new untared attempt (unchanged).

  Under the lock, it re-checks that the attempt is still the open one (ADR-011).
- **ConfirmationService** (existing): unchanged rules. A refusal for `over` reports the surplus.
- **No RecalculationService and no OverrideService**: deliberately absent under the STEP 24 rule.

### Repository Interfaces

- **ComponentAttemptRepository** (existing): `end(attempt, reason)` gains `end(attempt, overshoot_discarded, discard)`, which writes the snapshot once. It also gains `discards_for(session)`, used for the audit and the tests. No update after the end, and no delete.
- **WeighingRecordRepository**, **WeighingSessionRepository**: unchanged; no new method writes targets.

### Ubiquitous Language

- **Overshoot / over tolerance / overweight**: the net weight is above the upper tolerance limit (above 94.5 g for Yellow RGB).
- **Surplus**: how much the net weight is above the **target**, as an amount and a % of the target. This is the prototype's "Surplus +2.4 g (+2.6%)". It is not the distance above the upper limit.
- **Recovery action**: what the operator must do after an overshoot. Either remove material back into the band, or discard and re-weigh with Quit (F4).
- **Overshoot discard**: a Quit while over tolerance. The attempt ends with the discarded weight and surplus stored; nothing is recorded as weighed.
- **Surplus compensation / recalculation**: the brief's FR-21 / FR-22, an assumed meaning (A-08). **Not performed** in the training build.
- **Supervisor override**: the brief's FR-18 / FR-23 / BR-13. **Not available** under this rule; shown disabled with its reason.

### Story Coverage

- **007-handle-overshoot**:
  - **AC 1** (Yellow RGB at 96.4 g → "OVER TOLERANCE — SURPLUS +2.4 g" and "Surplus +2.4 g (+2.6%)", confirm blocked): Surplus, OvershootView, invariant 1.
  - **AC 2** (no remaining component target changes): invariant 2; tested by comparing all targets before and after an overshoot, a refused confirm and a discard.
  - **AC 3** (override or compensation recorded with who and why): **not applicable** under the STEP 24 rule (recorded in the story and in requirements FR-14c). OvershootRule `override_available = false`.
  - **Requirements FR-14d** (Quit over tolerance → overshoot discard and no record; reducing into the band allows confirm): QuitService, invariants 3–5.

### Decisions for the Human Checkpoint

1. **Basis of the surplus percentage** - Recommended: **% of the target** (2.4 ÷ 94.0 → +2.6%). This matches the prototype's text and the story's AC 1, rounded to 0.1 % with ROUND_HALF_UP. Alternative: % above the upper limit (1.9 g ÷ 94.5 → +2.0%), which contradicts the prototype's "+2.6%".
2. **How the discard is recognised** - Recommended: **the server re-reads the scale at Quit and evaluates it.** The browser's view of the zone is never trusted (ADR-008), and the stored net is the server's own value. The scale I/O stays outside the transaction (ADR-011). Alternative: the browser sends "over" with the quit (it cannot be checked).
3. **Quit when the scale cannot be read** - Recommended: **plain `quit`, never blocked.** The operator must always be able to abandon an attempt (FR-13e). Without a reading, there is no evidence of an overshoot to store. Alternative: refuse the quit until the scale answers (this could trap the operator on a faulty scale).
4. **Where the discard is stored** - Recommended: **on the ComponentAttempt**: the new end reason `overshoot_discarded` plus `end_net`, `end_surplus` and `end_unit` (one migration). The attempt is already the append-only audit of every try (ADR-010). Alternative: a separate OvershootEvent table (a second place for the same history).
5. **Where the rule lives** - Recommended: **a fixed OvershootRule in code**, with its texts served by the evaluation API (ADR-008). Changing it is a business decision, not a configuration. Alternative: settings flags such as `OVERRIDE_ENABLED` (this would let the rule change without an approved decision).
6. **What is logged for recovery (a)** - Recommended: **nothing new.** Over-tolerance confirms are already logged as ConfirmationRefused, and the final record shows the within-tolerance weight. Evaluations run on every reading change (every 200 ms), so logging each "over" reading would flood the log. Alternative: an OvershootObserved log entry on the first "over" evaluation per attempt (this needs state per attempt).
