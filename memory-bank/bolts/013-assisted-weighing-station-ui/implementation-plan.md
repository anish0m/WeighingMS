---
stage: plan
bolt: 013-assisted-weighing-station-ui
created: 2026-11-23T09:32:27Z
---

## Implementation Plan: assisted-weighing-station-ui (View 2 · overshoot)

### Objective

Show the STEP 24 training rule (OQ-4, ADR-012) on View 2:
- an over-tolerance weight shows the prototype's status line and surplus panel;
- OK · Confirm stays disabled;
- the operator sees the defined recovery action;
- Supervisor override stays disabled with its reason;
- no recalculation proposal is shown.

Every text comes from bolt 012's server fields. The browser computes nothing (ADR-008, NFR-16, FR-21).

Also fix the training-panel failure-switch race carried over from bolt 012 (APPROVE TESTS, option 1).

### Deliverables

1. **Surplus panel** (story 006 AC 1, AC 2) in `terminal.html`, between the weigh panel and the keys, as in the prototype:
   - It is shown only while `evaluation.overshoot` is not null and the scale is not faulted.
   - **Heading** (`data-testid="surplus-heading"`): `overshoot.heading`, e.g. "Surplus +2.4 g (+2.6%) — over tolerance". Prototype class `.surplus .h`, red.
   - **Recovery line** (`surplus-recovery`): `overshoot.recovery`, i.e. "Remove material until the weight is back in the band, or press Quit (F4) to discard and re-weigh."
   - **Override line** (`surplus-override`): `overshoot.overrideReason`, i.e. "Supervisor override is not available in this training build".
   - **No proposal table and no "→" values:** the prototype's 24.624 kg / 9.850 kg are a guess and are not copied.
2. **Status line:** unchanged. It already shows the server's `statusLine`, "OVER TOLERANCE — SURPLUS +2.4 g", with `data-zone="over"` (red).
3. **OK · Confirm:** unchanged. It is disabled because `withinTolerance` is false; the server refuses as well (bolt 012).
4. **Supervisor override button:**
   - stays disabled;
   - its `title` is bound to `overshoot.overrideReason` while over tolerance, and is absent otherwise;
   - the old static title "Supervisor override is decided in STEP 24" is removed.
   No form is built: story 006 AC 3 is not applicable under the STEP 24 rule.
5. **Quit message** (recovery b):
   - after Quit, the existing `weigh-message` notice shows the server's `ended.message`, e.g. "Overshoot discarded (96.4 g). Empty the container and press Re-tare (F2)." or "Attempt abandoned. …";
   - it clears at the next action, as other messages already do.
6. **CSS:** `station.css` gains the prototype's `.surplus` rules (border, background, padding, `.h`). The table / arrow rules are not copied, because nothing uses them.
7. **Training-panel race fix:** `training-panel.js` `toggle(target)` takes the wanted state from the checkbox (`@change="toggle(target, $event.target.checked)"`): checked → the failure mode, unchecked → `ok`. It no longer reads the possibly stale `this.modes`.

### Dependencies

- **Bolt 012 (server):**
  - evaluation `overshoot` / `surplusPercent`;
  - quit `ended`;
  - 409 detail with the surplus.
- **Bolt 011 (UI):**
  - `weigh.js` state (`evaluation`, `runAction`, `weighMessage`);
  - `station-client.js` (`quit` already returns the JSON);
  - TRAINING ONLY panel "▶ Simulate overshoot" (Dummy Scale: target + 4.8 · tolerance = 96.4 g for Yellow RGB).
- No new library and no new endpoint.

### Acceptance Criteria

- [ ] **AC 1:** Yellow RGB, Simulate scan, ▶ Simulate overshoot → the weight reads 96.4 g. The status line reads "OVER TOLERANCE — SURPLUS +2.4 g", the panel reads "Surplus +2.4 g (+2.6%) — over tolerance", and OK · Confirm is disabled.
- [ ] **AC 2:**
  - the panel shows only the heading, the recovery and the override reason;
  - no recalculated target and no other component's name or quantity appears in it;
  - the page contains neither 24.624 nor 9.850.
- [ ] **AC 3:** not applicable. Supervisor override is disabled and its title is the server's reason.
- [ ] **Recovery (a):** Set weight 94.0 → the panel disappears, the status line is green, and OK is enabled.
- [ ] **Recovery (b):** Quit while over → the notice shows "Overshoot discarded (96.4 g). Empty the container and press Re-tare (F2).", Yellow RGB stays WEIGHING, the status line asks for Re-tare, and nothing is recorded ("0 of 5").
- [ ] **kg component:** Sodium Sulphate, overshoot → the panel uses kg (e.g. "Surplus +0.576 kg (+2.4%)", the value the server returns for 24.576 kg).
- [ ] **Race fixed:** the full Playwright run passes 50/50 or more, including "the OrgaTEX failure switch sets and clears unavailable".
- [ ] No quantity arithmetic and no hard-coded scenario data in the changed JS (the existing hard-coded-data scan still passes).

### Technical Approach

- **`terminal.html`:**
  - one `<div class="surplus" data-testid="surplus-panel" x-show="evaluation && evaluation.overshoot && !scaleFault">` with three `x-text` children;
  - the override button gets `:title="evaluation && evaluation.overshoot ? evaluation.overshoot.overrideReason : null"`;
  - the training toggle passes `$event.target.checked`.
- **`weigh.js`:**
  - `quitComponent()` uses a small variant of `runAction` that keeps `ended.message` after `applyProgress` (`this.weighMessage = progress.ended ? progress.ended.message : ''`);
  - nothing else changes.
- **`training-panel.js`:** `toggle(target, checked)`.
- **`station.css`:** the `.surplus` block from the prototype.
- **Tests (Test stage):**
  - Playwright `playwright/overshoot.spec.js`: AC 1, AC 2, AC 3, recovery (a), recovery (b), kg;
  - workbook STEP 24 UI evidence path;
  - a full regression run;
  - Django: the existing UI hard-coded-data scan covers the changed JS.

### Decisions for the Human Checkpoint

1. **Override reason visible in the panel** - Recommended: **yes, as a third line in the panel, and also as the disabled button's title.** A tooltip alone does not show in the STEP 24 screenshot, and the operator should see why the button is inactive. Alternative: tooltip only, keeping the panel to heading and recovery.
2. **Quit message** - Recommended: **show the server's `ended.message` in the existing notice.** It tells the operator to empty the container and re-tare. Alternative: no message (the status line already says "TARE REQUIRED").
3. **Race fix scope** - Recommended: **take the state from the checkbox** (one-line change). Alternative: disable the switch while a request is in flight (more code, same result).
