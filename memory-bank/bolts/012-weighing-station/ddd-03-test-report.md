---
stage: test
bolt: 012-weighing-station
created: 2026-11-23T09:10:36Z
---

## Test Report: weighing-station (overshoot)

### Summary

- **Tests**:
  - **Django: 26/26 new tests pass.** `npm test` reports **475/475**: 449 earlier tests plus 26 new.
  - Two earlier tests compare exact JSON. At Implement, their expected values gained the designed new keys:
    - `test_rules_api.test_near_reading_json`: `surplusPercent` and `overshoot` are null;
    - `test_confirmation_api.test_out_of_tolerance_is_409_with_the_measured_weight`: the 94.6 g detail adds surplus 0.6 / 0.6 % / "0.6 g".
  - **Playwright: 49/50** in two full runs (regression only; this bolt changes no UI). See Issues Found: the one failure is an existing race in bolt 011's training panel, and the spec passes 12/12 when run alone.
- **Lint**: `npm run lint` passes. `makemigrations --check` finds no missing migration (0005 is included).
- **Coverage**: not measured; the coding standards set no percentage target. Every acceptance criterion, model decision and ADR-012 point is mapped below.
- **Live tests:** the recovery and API tests run against the live **Dummy Scale** and **Dummy Scanner** (training contracts) through the real adapters:
  - weights are set with the training `simulate` control (`set`, e.g. 96.4 g);
  - the disconnected scale uses the training mode toggle.

### Test Files

- [x] `tests/weighing/test_overshoot.py` - 10 tests (pure, no scale):
  - **Yellow RGB at 96.4 g:**
    - zone `over`, not within;
    - "OVER TOLERANCE — SURPLUS +2.4 g";
    - surplus 2.4, percent 2.6;
    - heading "Surplus +2.4 g (+2.6%) — over tolerance".
  - **94.6 g:** +0.6 g (+0.6%).
  - **kg:** Sodium Sulphate 24.200 kg → +0.200 kg (+0.8%).
  - **No surplus:** at 94.5 / 94.0 / 93.5 / 93.4 / 0.0 g.
  - **Rounding:** ROUND_HALF_UP (exactly 0.65 % → 0.7).
  - **Types:** `Decimal` only, and "float" does not appear in `overshoot.py`.
  - **Texts:** the refusal detail texts.
  - **Rule:** OVERSHOOT_RULE has no confirm, recalculation `none` and no override. It is frozen (an assignment raises).
  - **JSON:** the full `overshoot` JSON, and `None` when not over.
- [x] `tests/weighing/test_overshoot_recovery.py` - 10 tests (live):
  - **Blocked:**
    - confirm at 96.4 g is refused `OUT_OF_TOLERANCE` with net, zone, surplus, percent and text, and stores no record;
    - every recipe target, tolerance and unit is unchanged after an overshoot, a refused confirm, a discard, a re-tare and a confirm. The final record keeps 94.0 / 93.5 / 94.5;
    - no `override`, `recalculate`, `compensate` or `targets` URL exists (404), and `WeighingResult` has only `within`.
  - **Recovery (a):** 96.4 g is refused; 94.0 g on the same attempt is confirmed at 94.0 g, `within`.
  - **Recovery (b):**
    - Quit at 96.4 g → `overshoot_discarded` with 96.4 / 2.4 / g stored, and no record;
    - the new attempt is untared;
    - `ended` has its message;
    - one `OvershootDiscarded` log entry (surplus, percent, operator) and no `AttemptQuit`.
  - **After a discard:** Re-tare, then 94.2 g, then confirm. The attempt history reads `overshoot_discarded`, `confirmed`, then the next component open.
  - **Plain quit:** Quit at 94.0 g is a plain `quit`, with no snapshot and the "Attempt abandoned…" message.
  - **Disconnected scale:** Quit at 96.4 g on a disconnected scale is still allowed, as a plain `quit` (model Decision 3).
  - **Storage:** the discard snapshot can't be changed or deleted after the end (`AttemptImmutable`). The database check constraint rejects three wrong combinations: snapshot on `quit`, missing unit, missing net / surplus.
- [x] `tests/weighing/test_overshoot_api.py` - 6 tests (live, HTTP):
  - **Evaluation JSON at 96.4 g:** `surplusPercent` "2.6" and the full `overshoot` object. Within and near weights give null for both.
  - **Confirm:** at 96.4 g it returns 409 with surplus "2.4" / "2.6" / "2.4 g" in the detail.
  - **Quit JSON over tolerance:**
    - `ended` = attempt id, `overshoot_discarded`, 96.4, 2.4, g and the message;
    - the new active attempt is untared;
    - `weighed` stays 0.
  - **Plain quit JSON:** `reason` is `quit`, and net, surplus and unit are null.
  - **`ended` only on quit:** it appears only in the quit response, not in activate or progress.

### Acceptance Criteria Validation

- ✅ **Story 007 AC 1** (Yellow RGB at 96.4 g → "OVER TOLERANCE — SURPLUS +2.4 g" and "Surplus +2.4 g (+2.6%)", confirm blocked): `SurplusTests.test_yellow_rgb_at_96_4_g`, `BlockedTests.test_confirm_at_96_4_g_is_refused_with_the_surplus`, `OvershootApiTests.test_evaluation_at_96_4_g_has_the_overshoot`, `test_confirm_over_tolerance_is_409_with_the_surplus`.
- ✅ **Story 007 AC 2** (no remaining component target changes): `BlockedTests.test_no_target_changes_after_an_overshoot`, `test_no_override_or_recalculation_endpoint_exists`.
- ➖ **Story 007 AC 3** (override or compensation recorded with who and why): **not applicable** under the STEP 24 rule (OQ-4, requirements FR-14c). Checked instead: no override path exists, and `OVERSHOOT_RULE.override_available` is false.
- ✅ **Requirements FR-14d** (Quit over tolerance → overshoot discard, no record; reducing into the band allows confirm): `RecoveryTests` (5 tests).
- ✅ **Model decisions 1–6 and ADR-012:**
  1. % of target: `test_yellow_rgb_at_96_4_g`, `test_the_percent_rounds_half_up_to_0_1`;
  2. the server re-reads at Quit: the discard is stored from the server's reading, and the quit body is ignored;
  3. an unreadable scale gives a plain quit: `test_quit_on_a_disconnected_scale_is_never_blocked`;
  4. the discard is stored on the attempt, with the constraint: `DiscardStorageTests`;
  5. a fixed rule in code: `test_the_rule_is_a_frozen_constant`;
  6. no new logging for recovery (a): only `ConfirmationRefused` and `WeighingConfirmed` appear.

### Issues Found

- **Existing race in bolt 011's training panel (unit 007), not caused by this bolt.**
  - **Symptom:** in the full Playwright run, `training-panel.spec.js` › "the OrgaTEX failure switch sets and clears unavailable" failed twice ("Expected ok, Received unavailable"). Run alone, the spec passes 12/12.
  - **Cause:** in `training-panel.js`, `toggle(target)` derives the next mode from `this.modes`, the last server answer, instead of from the checkbox. The test unchecks as soon as the Dummy reports `unavailable`. If the browser has not stored the `setMode` response yet, `isFailing()` is still false, and the uncheck sends `unavailable` again.
  - **Bolt 012 changed** no JS, no template and no OrgaTEX or training code. It is reported to the human for a decision; fixing it belongs to unit 007 (bolt 013).
- No issue found in the overshoot behaviour.

### Notes

- **Training contract:** the surplus and the discard come from the Dummy Scale's weights. A-08, Q25, Q26 and Q33 stay unresolved (ADR-012).
- **For bolt 013:**
  - show `overshoot.heading` and `overshoot.recovery`;
  - show Supervisor override disabled, with `overshoot.overrideReason`;
  - show the quit `ended.message`;
  - show no recalculation table;
  - compute nothing in the browser.
