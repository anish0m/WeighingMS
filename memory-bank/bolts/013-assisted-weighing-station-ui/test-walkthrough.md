---
stage: test
bolt: 013-assisted-weighing-station-ui
created: 2026-11-23T09:45:00Z
---

## Test Walkthrough: assisted-weighing-station-ui (View 2 · overshoot)

### Summary

- **Playwright: 56/56** (`npx playwright test`): 50 earlier tests plus 6 new in `playwright/overshoot.spec.js`. The failure-switch test that failed twice in bolt 012's runs passes in both full runs since the race fix.
- **Django: 475/475** (`npm test`). The UI hard-coded-data scan covers the changed `weigh.js` and `training-panel.js`.
- **Lint:** `npm run lint` passes.
- **Live:** weights are set through the Dummy Scale's training controls ("▶ Simulate overshoot" = target + 4.8 · tolerance; `set` for exact weights). Operator actions go through the terminal UI (touch, F1, F2, F4).

### Test Files

- [x] `playwright/overshoot.spec.js` - 6 tests (items 5 and 6 are one test):
  1. **Yellow RGB at 96.4 g (AC 1):**
     - the status line reads "OVER TOLERANCE — SURPLUS +2.4 g" in red;
     - the panel is visible with "Surplus +2.4 g (+2.6%) — over tolerance" in red;
     - OK · Confirm is disabled, and F1 records nothing ("0 of 5").
  2. **Only the STEP 24 rule (AC 2):**
     - the panel has exactly three lines: heading, recovery text and override reason;
     - no other component's name, no "→" and no table;
     - neither "24.624", "9.850" nor "Proposal" appears on View 2;
     - the Sodium Sulphate / Soda Ash targets on the rail stay 24.000 kg and 9.600 kg.
  3. **Supervisor override (AC 3 not applicable):** disabled, its `title` is the server's reason, and no form exists.
  4. **Recovery (a):**
     - Set weight 94.0 → the panel hides, the status line reads "WITHIN TOLERANCE — PRESS OK TO CONFIRM" and the override title is removed;
     - OK is enabled, and the click records ("1 of 5").
  5. **Recovery (b), first part:** F4 while over →
     - the notice reads "Overshoot discarded (96.4 g). Empty the container and press Re-tare (F2).";
     - Yellow RGB stays active and "0 of 5";
     - the status line reads "TARE REQUIRED — PRESS RE-TARE (F2)";
     - the panel is hidden and OK is disabled.
  6. **Recovery (b), re-weigh:** the empty container → F2 (the notice clears) → Simulate dispense → F1 records ("1 of 5").
  7. **kg component:** Sodium Sulphate, Simulate overshoot → 24.576 kg, "OVER TOLERANCE — SURPLUS +0.576 kg", "Surplus +0.576 kg (+2.4%) — over tolerance", OK disabled.

### Acceptance Criteria Validation

- ✅ **Story 006 AC 1** (96.4 g: status line, panel heading, Confirm disabled): item 1, plus item 7 for kg.
- ✅ **Story 006 AC 2** (only what the rule defines, no hard-coded proposal): item 2.
- ➖ **Story 006 AC 3** (override form): **not applicable** under the STEP 24 rule (OQ-4). Item 3 checks that the button is disabled with the server's reason and that no form exists.
- ✅ **Plan: recovery (a) and (b), kg component, race fixed, no browser arithmetic:** items 4–7, the full Playwright run, and the Django hard-coded-data scan.

### Issues Found and Fixed

- **The surplus panel came back after Quit.**
  - **Symptom:** Quit ends the attempt, but the emptied-container step hasn't happened yet, so the scale still reads 96.4 g. The re-evaluation then showed the panel again ("… press Quit (F4) …") while the status line asked for Re-tare.
  - **Fix (`terminal.html`):** the panel is shown only on a **tared** attempt (`isTared()`), the same precedence the status line already uses. Item 5 covers it.
- **Training-panel race** (carried over from bolt 012): fixed in Implement. The full runs pass (50/50, then 56/56).

### Notes

- **Workbook STEP 24 UI evidence (T397–T399):**
  - in the browser: Yellow RGB → Simulate scan → ▶ Simulate overshoot;
  - the screenshot shows the red status line, the surplus panel with its three lines, OK · Confirm disabled and Supervisor override disabled.
- **The test evidence (T395)** is the Terminal 1 output of `npm test` (Django, including `test_overshoot*`).
