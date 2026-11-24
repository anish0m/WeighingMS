---
stage: implement
bolt: 016-ticket-printing
created: 2026-11-24T03:50:00Z
---

## Implementation Walkthrough: ticket-printing

### Summary

A completed batch's weighing ticket can now be previewed and printed, with the same pattern as the bolt 014 write-back:
- the server builds the ticket text from the stored data and logs every print attempt;
- the browser's printer client sends the text to the Dummy Printer and reports back;
- the server marks a job printed only after reading the stored ticket back from the printer.

Later successful prints are marked `*** REPRINT ***`. A printer failure leaves the job failed, and nothing counts as printed.

### Structure Overview

- **New app `tickets` (unit 006):**
  - a pure text builder;
  - the print log model;
  - the print service;
  - three station endpoints.
- **Reads, never writes:** it reads the completed batch through `weighing` (bolt 015's summary and the stored records) and the batch header from the stored selection.
- **Printer read:** it reads the printer through a new read-only adapter in `devices`.
- **Browser:** the existing printer client is reused unchanged; the station client chains start → print → report.

### Completed Work

- [x] `src/tickets/__init__.py`, `apps.py` - **new app**, registered in settings.
- [x] `src/tickets/models.py` - **new.** `PrintJob` and `PrintStatus`:
  - one row per print attempt: session, batch, reprint flag, the exact text sent, status (pending / printed / failed), the printer's ticket ID and time, the reason, the operator;
  - a printer ticket can confirm only one job (unique);
  - a database check allows the ticket ID and print time only on a printed job.
- [x] `src/tickets/migrations/0001_initial.py` - **new.** Creates the print log table.
- [x] `src/tickets/content.py` - **new.** The ticket text in the prototype's layout:
  - optional `*** REPRINT ***`, then the title, batch / order / machine / shade / date / operator;
  - the component table with target, actual and unit;
  - `ALL WITHIN TOLERANCE` (or `NOT ALL WITHIN TOLERANCE`);
  - the barcode as Code 39 text and the readable batch ID.
  Columns size themselves to the longest stored name. Values are the stored ones, only formatted at display resolution.
- [x] `src/tickets/printing.py` - **new.**
  - **preview:** the next print's text plus the print log;
  - **start a print:** requires an operator and a complete batch; reprint if an earlier job was printed;
  - **report:** the server reads the ticket back and requires the same text and batch; otherwise failed with a reason;
  - logging: INFO on start and on printed, WARNING on not printed (IR-09).
- [x] `src/tickets/views.py`, `src/tickets/urls.py` - **new.** Under `/station/api/sessions/<id>/`:
  - `GET ticket`: preview and log; 409 before completion;
  - `POST ticket/prints`: start, 201;
  - `POST ticket/prints/<jobId>/result`: the browser's report.
  Refusals use the existing refusal status table.
- [x] `src/devices/printer.py` - **new**, read-only. Reads one stored ticket from the printer; not-found and unavailable are separate errors (fail safe, IR-09 logging through `devices/http.py`).
- [x] `src/weighing/services.py`, `src/weighing/views.py` - new refusal reason `PRINT_JOB_NOT_FOUND` (404).
- [x] `src/weighingms/settings.py`:
  - `tickets` added to the installed apps;
  - new `PRINTER_BASE_URL` (environment-configurable, like the scale and scanner URLs).
- [x] `src/weighingms/urls.py` - the ticket endpoints are mounted under `/station/api/`.
- [x] `playwright.config.js` - the E2E server gets `PRINTER_BASE_URL` for its own port.
- [x] `src/station/static/station/station-client.js` - `ticketPreview(sessionId)` and `printTicket(sessionId)`:
  - start → `WeighingMS.printer.printTicket` → report;
  - resolves to the server's job.
- [x] `tests/architecture/test_integration_boundaries.py` - the Python owner of `/tickets` is now `devices/printer.py` (approved Decision 1). `/printer` stays browser-only.

### Key Decisions

- **The server decides "printed" (approved Decision 1):** the ticket read back must exist, hold exactly the job's text and batch, and not already confirm another job.
- **Stored component names (Decision 2):** e.g. "Remazol Brill. Blue RSPL", not the prototype's invented short forms.
- **Barcode as Code 39 text `*B-24187*` (Decision 3)**, plus the readable line. Bolt 017's preview can draw it.
- **Ticket date = completion time (Decision 4):** `YYYY-MM-DD HH:MM`, server time zone (UTC). Every reprint shows the same date.
- **The REPRINT line is the first line, centred,** above the title.
- **A failed job stays failed;** pressing Print again creates a new job, so the log keeps every attempt.

### Deviations from Plan

- **None in behaviour.**
- The preview response includes `batchId`.
- A new setting `PRINTER_BASE_URL` was needed for the server's printer read. It mirrors `SCANNER_BASE_URL` and is set for the E2E server.

### Dependencies Added

- None.

### Developer Notes

- **Dev database:** migration `tickets/0001` was applied with `migrate`. It only adds the empty print-log table; no data was reset.
- **Regression:** lint clean, Django 543/543 (including the boundary test with the new owner).
- **Sample ticket:** rendered with the prototype values and checked against the prototype's layout. The line `Remazol Yellow RGB  94.0  94.2 g` is present.
- **Bolt 017** shows the preview text, Print ticket (F1) and the failure message, using `ticketPreview` / `printTicket`.
