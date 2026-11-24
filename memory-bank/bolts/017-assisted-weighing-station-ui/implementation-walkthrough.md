---
stage: implement
bolt: 017-assisted-weighing-station-ui
created: 2026-11-24T04:20:00Z
---

## Implementation Walkthrough: assisted-weighing-station-ui (View 3 · Confirm & print)

### Summary

The terminal now has View 3 · Confirm & print, in the prototype's layout:
- the server's batch summary;
- "Written to OrgaTEX" with WRITING… / CONFIRMED hh:mm:ss / NOT WRITTEN and Retry;
- the exact ticket text on the ticket paper;
- Print ticket (F1) and Next batch (F3).

It opens by itself when the 5th confirmation completes the batch, starts the OrgaTEX write-back automatically, and reopens after a reload until Next batch. The static "no hard-coded data" scan now also covers View 3's values.

### Structure Overview

View 3 is a third view module (`done.js`), merged into the terminal's Alpine component like `weigh.js`. It only calls the existing station client functions from bolts 014–016 and shows their answers; there is no server change and no new endpoint. `weigh.js` hands over to it when a confirm response carries `completion`. `terminal.js` reopens it on load.

### Completed Work

- [x] `src/station/static/station/done.js` - **new.** View 3's state and actions:
  - open with the completion (or the summary after a reload);
  - load the ticket preview;
  - start the write-back automatically unless it is already confirmed;
  - Retry while not written;
  - Print ticket with its result line ("Ticket printed …" / "REPRINT printed …" / the failure reason), then reload the preview;
  - Next batch;
  - remember the completed session in `sessionStorage` until Next batch.
- [x] `src/station/templates/station/terminal.html` - new View 3 (`#v-done`):
  - heading "Batch … weighed";
  - six summary rows with the prototype's labels;
  - the prototype's "Actual consumption posted …" sentence, shown only when CONFIRMED (the machine comes from the OrgaTEX batch read);
  - the not-written reason;
  - the keys Print ticket F1, Next batch F3 and Retry write-back;
  - the ticket text in a `<pre>` and the print result.
- [x] `src/station/templates/station/base.html` - loads `done.js`.
- [x] `src/station/static/station/terminal.js`:
  - merges `doneView()`; adds the view state `done`;
  - on load with no in-progress session, View 3 is reopened if a completed session is remembered; otherwise View 1.
- [x] `src/station/static/station/weigh.js`:
  - the last confirm opens View 3 with the response's `completion`;
  - the key table now covers F1 / F2 / F4 on View 2 and F1 / F3 on View 3 (NFR-9).
- [x] `src/station/static/station/station-client.js` - `summary(sessionId)` (`GET sessions/<id>/summary`).
- [x] `src/station/static/station/station.css` - the prototype's View 3 rules (`.done-stage`, `.done-msg`, `.summary`, `.ticket`), plus red `.v.bad` and the print-result line. The ticket keeps the server's spacing (`white-space: pre`).
- [x] `tests/station/test_no_hard_coded_data.py` - the scan covers `done.js`. The seed-value list gains "Sodium Sulphate", "Soda Ash", "35.322", "6 min 41 s", "FCI DYEING" and "WMS-" (story 009 AC 1).

### Key Decisions

- **The write-back starts when View 3 opens (approved Decision 1).** Retry appears only for NOT WRITTEN; repeating it cannot double-post (bolt 014 key).
- **View 3 survives a reload until Next batch (Decision 2),** through `sessionStorage` and `GET summary`.
- **The preview is the exact ticket text (Decision 3).** No decorative bars; the barcode is the text `*B-24187*`.
- **The browser formats only time:** `confirmedAt` and the printer's `printedAt` are shown as station-local `hh:mm:ss`, like the existing clock.

### Deviations from Plan

- **None in behaviour.**
- The print result line also shows the print time.
- A second notice shows a station error during the write-back (e.g. WeighingMS unreachable); the status then falls back to the last value read with `GET write-back`.

### Dependencies Added

- None.

### Developer Notes

- **Regression after the change:**
  - lint clean; Django station and architecture tests 19/19;
  - Playwright 55/60. The 5 failing tests all expect the View 2 rail to read "5 of 5" after the last F1; View 3 now replaces View 2 at that moment (approved behaviour). The write-back spec also has to account for the automatic write-back. These tests are updated in the Test stage:
    - the `weighAllB24187` helper;
    - `weigh.spec.js` "the whole batch";
    - `write-back.spec.js` (2 tests);
    - `tickets.spec.js` (2 tests).
- **Not yet written:** the seed-change Playwright test (story 009 AC 2) and the View 3 Playwright spec. Both come in the Test stage.
