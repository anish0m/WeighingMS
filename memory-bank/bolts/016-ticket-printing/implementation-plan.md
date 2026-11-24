---
stage: plan
bolt: 016-ticket-printing
created: 2026-11-24T03:42:20Z
---

## Implementation Plan: ticket-printing

### Objective

Print the weighing ticket of a completed batch on the (Dummy) printer, show a preview with the same content, mark every later print "REPRINT", and report a printer failure so that nothing is marked printed and the ticket can be printed again (FR-18, FR-20c, brief FR-27 / FR-28 / BR-15 / IR-16 / AC-10).

The architecture is the bolt 014 pattern (STEP 12 decision):
- the server builds the ticket from the stored records and keeps the print log;
- the browser's printer client sends `POST /api/tickets` and reports back;
- the server decides "printed".

The Dummy Printer is a training contract, not a real printer. The label content follows the prototype for training only ("Label content is invented", A-04 / Q18 stay unresolved).

### Stories in Scope

- **001-print-weighing-ticket:**
  - **AC 1:** the ticket with header, batch, order, machine, shade, date/time, operator, per-component name / target / actual / unit, "ALL WITHIN TOLERANCE" and the batch barcode is sent to the printer;
  - **AC 2:** the Dummy Printer stores it and the preview shows the same content;
  - **AC 3:** targets and actuals come from the stored records, not recomputed.
- **002-reprint-and-print-failure:**
  - **AC 1:** a second print is marked "REPRINT";
  - **AC 2:** printer error → failure shown, nothing marked printed;
  - **AC 3:** printer restored → printing succeeds;
  - **AC 4:** the completed batch and its records are unchanged by any print outcome.

### Deliverables

1. **New app `tickets` (unit 006)** in `src/tickets/`, under `/station/api/` (ADR-002).
2. **Ticket content `tickets/content.py`** (pure): `build_ticket(...)` returns the plain-text ticket in the prototype's layout:
   - `*** REPRINT ***` as the first line on a reprint;
   - `FCI DYEING — WEIGHING TICKET`, then a dashed line;
   - `BATCH`, `ORDER`, `MACHINE`, `SHADE`, `DATE` (the batch's completion time, `YYYY-MM-DD HH:MM`, server time zone), `OPER.` (operator name);
   - a dashed line, then `COMPONENT  TGT  ACT` and one line per component in recipe sequence: the stored component name, the stored target and the stored actual at display resolution, and the unit;
   - a dashed line, then `ALL WITHIN TOLERANCE` (or `NOT ALL WITHIN TOLERANCE` if any record is not `within`);
   - the barcode as Code 39 text `*B-24187*`, then the human-readable `B-24187`.
   Batch header values come from the stored batch selection (the OrgaTEX snapshot); the lines come from the stored `WeighingRecord`s (story 001 AC 3); the summary uses bolt 015's `completion.summary`.
3. **Print log `PrintJob` model** (+ migration `tickets/0001`), one row per print attempt:
   - `session_id`, `batch_id`, `is_reprint`, `content` (exactly what was sent);
   - `status` (`pending` / `printed` / `failed`), `printer_ticket_id`, `printed_at` (the printer's time), `reason`;
   - `operator_id`, `created_at`.
4. **Service `tickets/printing.py`:**
   - `preview(session_id)`: the content the next print would send (with REPRINT once a print succeeded), plus the print history;
   - `start_print(session_id, operator_id)`: requires an operator and a **complete** batch (`BATCH_NOT_COMPLETE` otherwise); a job is a reprint if any earlier job of the session is `printed`; creates a `pending` job and returns its content;
   - `report_print(session_id, job_id, operator_id, printed, ticket_id, reason)`: the server checks the printer before it marks the job `printed` (Decision 1); otherwise `failed` with the reason;
   - INFO for printed, WARNING for failed (IR-09).
5. **Printer read adapter `devices/printer.py`** (Decision 1): `fetch_ticket(ticket_id)` reads `GET /api/tickets/<id>` through the existing `devices/http.py`. The job is `printed` only if that ticket exists and its content and batch match the job.
6. **Station API (`tickets/urls.py`, `tickets/views.py`):**
   - `GET  sessions/<id>/ticket` → `{content, reprint, printed, jobs: [...]}`; 409 `BATCH_NOT_COMPLETE` before completion;
   - `POST sessions/<id>/ticket/prints` → `{job: {jobId, status, reprint}, batchId, content}`;
   - `POST sessions/<id>/ticket/prints/<jobId>/result` with `{printed, ticketId, reason}` → `{job}`.
7. **Browser:** `station-client.js` gains `ticketPreview(sessionId)` and `printTicket(sessionId)`: start → `WeighingMS.printer.printTicket(content, batchId)` → report → the server's job. The existing `printer-client.js` is unchanged.

### Dependencies

- **Bolt 002 (Dummy Printer):** `POST /api/tickets` (201 with `ticketId`, 503 `PRINTER_ERROR`), `GET /api/tickets/<id>`, the error switch.
- **Bolt 004 (devices):** `printer-client.js`, `devices/http.py`.
- **Bolt 015:** `completion.summary`, `history` / records, the `complete` session state.
- **Bolt 005 (batches):** the stored selection (order, machine, shade).
- No new library.

### Technical Approach

- **Never trust the browser** (as ADR-006 and bolt 014): a print counts only when the server reads the stored ticket back.
- **A failed print is not a print:** a REPRINT is marked only after an earlier job was confirmed `printed`. A failed first attempt does not make the next one a reprint.
- **Records and session are read-only here:** no code in `tickets` writes `weighing` data (story 002 AC 4).
- **Boundary test:** `PATH_OWNERS["/tickets"]` changes from no Python owner to `devices/printer.py`. `/printer` (status) stays browser-only.
- **No arithmetic in the browser;** the preview text is the server's content.

### Acceptance Criteria

- [ ] **001 AC 1:** for B-24187 at the prototype actuals, the content holds every listed field, including all five component lines (e.g. `Remazol Yellow RGB  94.0  94.2 g`), `ALL WITHIN TOLERANCE` and `*B-24187*`; a print sends it to the Dummy Printer.
- [ ] **001 AC 2:** after a successful print, `GET /api/tickets/<id>` returns exactly the job's content, and the preview equals it.
- [ ] **001 AC 3:** the ticket's targets and actuals equal the stored records (also when a record differs from the snapshot target, e.g. 23.980 kg).
- [ ] **002 AC 1:** the second successful print's content starts with `*** REPRINT ***`; the first does not.
- [ ] **002 AC 2:** with the printer in error, the job is `failed` with the reason, nothing is `printed`, and the next print is not a reprint.
- [ ] **002 AC 3:** after the printer is restored, the print succeeds.
- [ ] **002 AC 4:** session state, `completed_at` and the five records are identical before and after printed and failed prints.
- [ ] Print before completion → 409 `BATCH_NOT_COMPLETE`; no operator → 403; a browser report of "printed" with an unknown or different ticket → `failed`.
- [ ] Lint clean; `npm test` and `npx playwright test` pass.

### Tests (Test stage)

- **Django:**
  - `tests/tickets/test_content.py` (layout and values);
  - `tests/tickets/test_printing.py` (jobs, reprint, failure, recovery, verification against the live Dummy Printer);
  - `tests/tickets/test_ticket_api.py`;
  - `tests/devices/test_printer.py`;
  - the boundary test updated.
- **Playwright:** one test that weighs 5 of 5, runs `printTicket` in the page (printed, then REPRINT), and one with the printer in error then restored. The View 3 preview and buttons come in bolt 017.

### Decisions for the Human Checkpoint

1. **Who decides "printed"** - Recommended: **the server, by reading the ticket back from the printer** (new read-only `devices/printer.py`). This is the same rule as bolt 014 and ADR-006. Alternative: trust the browser's report of the printer's ticket ID (no server printer adapter; a browser could mark an unprinted ticket as printed).
2. **Component names on the ticket** - Recommended: **the stored names** (e.g. "Remazol Brill. Blue RSPL"). The prototype's short forms ("Blue RSPL", "Na2SO4") are invented and would be hard-coded data. Alternative: copy the prototype's abbreviations.
3. **Barcode** - Recommended: **the batch ID as Code 39 text `*B-24187*` plus the readable line**. The symbology is unresolved (Q18), and the Dummy Printer stores text. Bolt 017's preview can draw it as bars. Alternative: only the readable batch ID.
4. **Ticket date** - Recommended: **the batch's completion time** (`YYYY-MM-DD HH:MM` in the server's time zone, currently UTC). It is the same on every reprint. Alternative: the print time.
