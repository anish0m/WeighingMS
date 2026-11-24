---
stage: plan
bolt: 017-assisted-weighing-station-ui
created: 2026-11-24T04:09:09Z
---

## Implementation Plan: assisted-weighing-station-ui (View 3 · Confirm & print, no hard-coded data)

### Objective

1. **View 3 · Confirm & print (story 007):** the prototype's completion screen. It opens when the 5th confirmation completes the batch and shows:
   - the server's batch summary;
   - the OrgaTEX write-back status, with Retry when not written;
   - the ticket preview;
   - Print ticket (F1) and Next batch (F3).
   Every value comes from the APIs built in bolts 014–016. The browser computes nothing (ADR-008, FR-21).
2. **No hard-coded scenario data (story 009):** prove it with a **real seed change** shown in the UI, and extend the existing static scan to View 3. Both other checks already exist and stay green:
   - the template / JS scan (bolt 011);
   - the "no `dummy_*` import" test (architecture).

### Stories in Scope

- **007-confirm-and-print-view:**
  - **AC 1:** "Batch B-24187 weighed", Components weighed 5 of 5, All within tolerance YES, Total dispensed, Elapsed, Operator, all from the API;
  - **AC 2:** "Written to OrgaTEX CONFIRMED hh:mm:ss", or "not written" with Retry;
  - **AC 3:** Print ticket (F1) prints and the preview shows the ticket; Next batch (F3) opens View 1.
- **009-no-hard-coded-scenario-data:**
  - **AC 1:** no batch / recipe / component arrays or literal values in templates and static JS;
  - **AC 2:** a changed seed value shows after a reload;
  - **AC 3:** no WeighingMS module imports `dummy_*`.

### Deliverables

1. **`terminal.html`: new View 3 (`#v-done`)** in the prototype's layout (`.done-stage`: message column and ticket column):
   - **heading:** "Batch {batchId} weighed" (green);
   - **summary rows**, with the prototype's labels and the server's texts:
     - Components weighed → `componentsText`;
     - All within tolerance → `allWithinText` (green when YES);
     - Total dispensed → `totalDispensedText`;
     - Elapsed → `elapsedText`;
     - Operator → `operator.name`;
     - Written to OrgaTEX → see deliverable 3.
   - **the prototype's sentence,** shown only when CONFIRMED: "Actual consumption posted against the batch. Container released for transport to {machine}.", with the machine taken from the OrgaTEX batch read;
   - **keys:** Print ticket F1 and Next batch F3, plus **Retry write-back** while not written;
   - **ticket column:** the ticket paper (`.ticket`) showing the server's ticket text exactly (`ticketPreview(...).content`, kept in a `<pre>`), and the print result line (e.g. "Ticket printed" / "REPRINT printed" / the failure reason).
2. **`done.js`** (new, merged into `terminal()` like `weigh.js`): View 3 state and actions:
   - `openDone(sessionId, completion)`: shows the summary, loads the ticket preview, then **starts the write-back automatically** (`station.writeBack`, bolt 014). The status is "WRITING…" until the server answers;
   - `retryWriteBack()`: the same call; no duplicate is possible (same key);
   - `printTicket()` (F1): `station.printTicket` (bolt 016), shows the result and reloads the preview (which then carries REPRINT);
   - `nextBatch()` (F3): clears View 3 and opens View 1 (the queue);
   - F1 / F3 run exactly what the buttons run (NFR-9). F1 does nothing while a print is running.
3. **Write-back display (story 007 AC 2):**
   - `confirmed` → "CONFIRMED hh:mm:ss" (green; the time is the server's `confirmedAt` shown as station-local `hh:mm:ss`);
   - `pending` → "WRITING…";
   - `not_written` → "NOT WRITTEN" (red), the server's reason and Retry.
   The status bar's ORGATEX chip is unchanged.
4. **`weigh.js`:** when a confirm response carries `completion` (bolt 015), the terminal leaves View 2 and opens View 3 with it. Nothing else in View 2 changes.
5. **Resume of View 3 after a reload** (Decision 2): the browser remembers the completed session ID in `sessionStorage`. On load, with no in-progress session, it reopens View 3 from `GET sessions/<id>/summary`. Next batch forgets it.
6. **`station.css`:** the prototype's View 3 rules (`.done-stage`, `.done-msg`, `.summary`, `.ticket`), plus a red `.v.bad` for NOT WRITTEN.
7. **Story 009:**
   - **`tests/station/test_no_hard_coded_data.py`:** the seed-value list gains the View 3 / ticket values ("35.322", "6 min 41 s", "Sodium Sulphate", "Soda Ash", "SO-9931" already present, "FCI DYEING"), so View 3's code is checked too;
   - **new Playwright `playwright/no-hard-coded-data.spec.js`:** changes the **Dummy OrgaTEX seed in the E2E database** (Yellow RGB target 94.0 → 95.0 g, and the B-24190 shade) through Node's built-in SQLite, reloads, and expects the changed values in View 1 and View 2. The pristine copy is restored after the test.

### Dependencies

- **Bolt 014:** `station.writeBack`, `writeBackStatus`.
- **Bolt 015:** the confirm response's `completion`, `GET sessions/<id>/summary`.
- **Bolt 016:** `station.ticketPreview`, `station.printTicket`.
- **Bolts 007 / 011 / 013:** the terminal shell, View 1 and View 2, the status bar, the training panel.
- **No new library;** Node's built-in `node:sqlite` (Node 24) is used only by the E2E test.

### Technical Approach

- **The browser formats only:** all values are the server's strings; the only browser formatting is `hh:mm:ss` of `confirmedAt` (as the existing clock and the queue's "received" time already do).
- **No new endpoint and no server change.**
- **Next batch** returns to the queue. B-24187 stays in the Dummy queue, because brief IR-06 is not built.
- **The training panel** keeps working on View 1 and View 2. On View 3, its weighing buttons have no active component, as before.

### Acceptance Criteria

- [ ] **007 AC 1:** after the 5th F1, View 3 shows "Batch B-24187 weighed", 5 of 5, YES, the total, elapsed and "R. Karim", equal to `GET summary`.
- [ ] **007 AC 2:** the write-back starts by itself and shows "CONFIRMED hh:mm:ss". With Dummy OrgaTEX unavailable it shows "NOT WRITTEN" and Retry; after OrgaTEX is restored, Retry → CONFIRMED, and one consumption is stored.
- [ ] **007 AC 3:**
  - F1 prints: the preview shows the ticket text, the Dummy Printer stores the same text, and the second F1 prints a REPRINT;
  - a printer error shows the failure; restored → printed;
  - F3 opens View 1.
- [ ] **009 AC 1:** the extended static scan passes over all station templates / JS / CSS.
- [ ] **009 AC 2:** the changed seed (95.0 g target, the new shade) appears after a reload.
- [ ] **009 AC 3:** the import boundary test passes.
- [ ] Reload on View 3 → View 3 again; after Next batch, a reload shows View 1.
- [ ] Lint clean; `npm test` and `npx playwright test` pass.

### Tests (Test stage)

- **Playwright `playwright/confirm-print.spec.js`:**
  - summary values;
  - CONFIRMED;
  - not written → Retry → CONFIRMED;
  - print and reprint;
  - printer failure and recovery;
  - F3 → queue;
  - reload on View 3.
- **Playwright `playwright/no-hard-coded-data.spec.js`:** the modified seed.
- **Django:** the extended static scan.
- **Workbook STEP 26 evidence path:** select B-24187, confirm all five, View 3 shows "Written to OrgaTEX CONFIRMED", and the Network tab shows `POST /api/batches/B-24187/consumption` (T418–T430).

### Decisions for the Human Checkpoint

1. **When the write-back starts** - Recommended: **automatically when View 3 opens** (prototype: View 3 already shows CONFIRMED; FR-17 "on batch completion"), with Retry only when not written. Alternative: an operator "Write to OrgaTEX" button (a step the prototype does not have).
2. **View 3 after a reload** - Recommended: **reopen it from `sessionStorage` + `GET summary`** until Next batch, so a not-written write-back or an unprinted ticket is not lost from the screen. Alternative: a reload shows the queue (the batch then has no screen until a history view exists).
3. **Ticket preview** - Recommended: **the server's ticket text exactly, on the prototype's ticket paper** (preview = what is printed, story 006 AC 2). The prototype's drawn barcode bars are decoration with no data; they are not drawn, and the barcode appears as `*B-24187*`. Alternative: also draw decorative bars like the prototype (they would not match the printed text).
4. **Seed-change proof** - Recommended: **change the Dummy OrgaTEX data in the E2E database and reload** (a real seed change, no request interception). Alternative: Playwright route interception (already used in bolts 007 / 011; it does not change the seed).
