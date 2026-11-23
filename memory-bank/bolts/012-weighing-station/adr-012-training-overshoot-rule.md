---
bolt: 012-weighing-station
created: 2026-11-23T08:55:58Z
status: accepted
superseded_by: null
---

# ADR-012: The training overshoot rule is fixed in code: no recalculation, no override, and an overshoot discard is stored on the attempt as decided by the server's own re-read

## Context

The brief describes overshoot handling (FR-20 – FR-24, BR-08, BR-13, AC-05, AC-06) as surplus compensation (a proportional recalculation of the remaining components) or a supervisor override. That rests on assumption A-08, which the brief rates "High: most likely misunderstanding". FCI has not answered Q25, Q26 or Q33.

The prototype's surplus panel is "deliberately a guess", and the workbook says: "Do not simply copy its proposed calculation."

At workbook STEP 24 the human decided the training rule (OQ-4, 2026-11-23T08:50:18Z):

> An overweight component remains unconfirmed and the operator must use the defined recovery action. No automatic recipe recalculation will be performed unless explicitly specified by the approved business rule.

The defined recovery action is to remove material back into the band, or to press Quit F4 (discard and re-weigh). This decision constrains more than bolt 012:
- the UI (bolt 013) must not show a proposal or an active override;
- completion and write-back (bolt 015) and the ticket (bolt 016) must not expect override results or adjusted targets.

## Decision

1. **The rule is one frozen code constant, `weighing.overshoot.OVERSHOOT_RULE`:**
   - `confirm_allowed = False`;
   - `recalculation = "none"`;
   - `override_available = False`, with its reason;
   - the recovery text.

   It is not a setting or environment flag. The server serves its texts in the evaluation JSON (`overshoot`), and the UI only displays them (ADR-008).
2. **No recalculation and no override code exist:** no service, endpoint or record result for them. No code writes a target, a tolerance or the recipe snapshot. `WeighingResult` stays `within` only.
3. **The surplus is part of the server evaluation:** the amount (net − target, at display resolution, ADR-009) and the % of the target (Decimal, ROUND_HALF_UP to 0.1).
4. **An overshoot discard is decided by the server's own scale re-read at Quit,** outside the transaction (ADR-011).
   - If it evaluates `over`, the attempt ends as `overshoot_discarded`, with `end_net`, `end_surplus` and `end_unit` stored once on the ComponentAttempt (ADR-010). A database check constraint ties the three fields to that end reason.
   - If the scale cannot be read, Quit still succeeds as a plain `quit`.
   - No weighing record is created in either case.

## Rationale

- **It implements exactly the approved business rule and adds no assumption** about A-08, Q25, Q26 or Q33. An over-tolerance weight can never become a record, and OrgaTEX-owned targets can never change.
- **A code constant, not a setting:** the rule can change only through a new approved decision and a code change, not through configuration.
- **Storing the discard on the attempt:** the attempt is already the append-only audit of every try (ADR-010). This keeps one history and satisfies BR-08 ("a defined response rather than an ad-hoc one") without a second event table.
- **The server's re-read decides:** the browser can neither fake an overshoot nor hide one (ADR-008).

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Option B: add a supervisor override (ID + PIN + reason, `result = override`) | Covers brief FR-18 / BR-13 / AC-06 | Accepts an off-ratio component; not in the approved rule | Not chosen at STEP 24 |
| Option C: proportional recalculation proposal accepted by a supervisor | Closest to the brief's flow chart | Builds A-08 as if known; needs an invented compensability limit (Q26); changes targets that later steps depend on | Not chosen at STEP 24; the workbook warns against copying the prototype's calculation |
| Rule as settings flags (`OVERRIDE_ENABLED`, …) | Switchable without code | The rule could change without an approved decision; untested combinations | A business rule is not configuration |
| Separate `OvershootEvent` table | Overshoot history in one place | A second record of the same attempt; must be kept consistent | The attempt already is the audit (ADR-010) |
| Browser tells the server "this quit was over" | No extra scale read | Unverifiable client claim | Violates ADR-008 |

## Consequences

### Positive

- The training build can never record an over-tolerance weight or change a recipe target.
- Overshoot discards are auditable per attempt, with the server-measured weight and surplus.
- Later bolts have a simple contract: records are always `within`; targets are always the OrgaTEX snapshot.

### Negative

- Brief FR-18's "or after authorised override", FR-21 – FR-24, BR-13 and AC-06 are **not demonstrated** in the training build. Story 005/007 AC 3 and story 007/006 AC 3 are not applicable.
- One extra scale read per Quit.

### Risks

- **FCI later answers Q25 / Q26 / Q33 differently.** Mitigation: this ADR is superseded by a new one. An override or compensation would add a new `WeighingResult`, a new service and endpoint, and a new `OvershootRule`. The stored discards stay valid history.
- **The operator removes material but stays over and keeps trying.** Mitigation: confirm stays refused; the status line and the recovery text show the surplus and both recovery paths.

## Related

- **Stories**: 005-weighing-station/007-handle-overshoot; 007-assisted-weighing-station-ui/006-weigh-view-surplus-panel-and-override (bolt 013)
- **Requirements**: FR-14 (training rule, a–d), OQ-4, A-08; evidence `docs/evidence/STEP-24-overshoot-decision.md`
- **Standards**: coding-standards (Decimal quantities, fail-safe integrations)
- **Previous ADRs**: ADR-008 (server is the single source of the weighing rules), ADR-009 (one value at display resolution), ADR-010 (stored attempts), ADR-011 (scale I/O outside the transaction)
