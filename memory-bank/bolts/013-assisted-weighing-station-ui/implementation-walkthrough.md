---
stage: implement
bolt: 013-assisted-weighing-station-ui
created: 2026-11-23T09:36:00Z
---

## Implementation Walkthrough: assisted-weighing-station-ui (View 2 · overshoot)

### Summary

View 2 now shows the STEP 24 training rule (OQ-4, ADR-012):
- While the server evaluates the weight as over tolerance, the prototype's red surplus panel appears with three server texts: the surplus heading, the recovery action and the override reason.
- The status line ("OVER TOLERANCE — SURPLUS +2.4 g") and the disabled OK · Confirm were already driven by the server and are unchanged.
- Supervisor override stays disabled; its tooltip is the server's reason.
- After Quit, the notice shows how the attempt ended, e.g. "Overshoot discarded (96.4 g). Empty the container and press Re-tare (F2)."
- No recalculation proposal is shown.

The training-panel failure switch now takes its wanted state from the checkbox. This fixes the race found in bolt 012's Playwright regression run.

### Structure Overview

No new file. Four existing files changed; the browser still does no arithmetic and holds no scenario data:
- the surplus panel and the override title are bindings to `evaluation.overshoot` (bolt 012);
- the quit message is `progress.ended.message`.

### Completed Work

- [x] `src/station/templates/station/terminal.html`:
  - **new surplus panel** (`data-testid="surplus-panel"`) between the weigh panel and the keys:
    - shown only while a component is active, `evaluation.overshoot` is set and the scale is not faulted;
    - children `surplus-heading`, `surplus-recovery` and `surplus-override` show `overshoot.heading`, `.recovery` and `.overrideReason`.
  - **Supervisor override:** still `disabled`. The static title "Supervisor override is decided in STEP 24" was replaced by `:title` = the server's `overrideReason` while over (no title otherwise).
  - **Failure switch:** it passes `$event.target.checked` to `toggle`.
- [x] `src/station/static/station/station.css`: a `.surplus` block with the prototype's border, background, padding and red `.h` heading, plus a muted `.sm` line. The prototype's table and arrow rules were not copied, because nothing uses them.
- [x] `src/station/static/station/weigh.js`: `runAction` shows `progress.ended.message` in the existing notice when the response has `ended` (only the quit response does).
- [x] `src/station/static/station/training-panel.js`: `toggle(target, checked)`. Checked → the target's failure mode; unchecked → `ok`. It no longer derives the mode from `this.modes`, which can still hold the previous answer while a request is in flight.

### Key Decisions

- **Override reason shown in the panel and as the tooltip** (plan Decision 1): visible in the STEP 24 screenshot, and the operator sees why the button is inactive.
- **The quit message comes from the server** (plan Decision 2): the operator is told to empty the container and re-tare; no text is built in the browser.
- **Race fix through the checkbox state** (plan Decision 3): a one-line change, with no extra in-flight state.

### Deviations from Plan

- **None in behaviour.** The plan described a "small variant of `runAction`" for Quit. It turned out to be one `if (progress.ended)` line in the shared `runAction`, because only the quit response carries `ended`.

### Dependencies Added

- None.

### Developer Notes

- **Regression run after the change:**
  - lint is clean;
  - Django 475/475;
  - Playwright **50/50**, including "the OrgaTEX failure switch sets and clears unavailable", which had failed twice in bolt 012's runs.
- **Alpine:** the panel's `x-show` hides it with an inline `display: none`; the CSS `display: flex` applies when it is shown.
- **The prototype's proposal values** (Sodium Sulphate 24.000 → 24.624 kg, Soda Ash 9.600 → 9.850 kg) are deliberately absent. The Test stage checks that they do not appear on the page.
