---
stage: test
bolt: 016-ticket-printing
created: 2026-11-24T04:00:00Z
---

## Test Report: ticket-printing

### Summary

- **Django: 584/584** (`npm test`): 543 earlier tests plus 41 new.
- **Playwright: 60/60** (`npx playwright test`): 58 earlier tests plus 2 new.
- **Lint:** `npm run lint` passes.
- **Coverage:** no percentage target (coding standards). Every acceptance criterion of stories 001 and 002 has at least one automated test.
- **Live, not mocked:**
  - B-24187 is completed with the prototype's actuals through the real flow (Dummy Scale and Scanner);
  - tickets go to the live Dummy Printer and are read back from it.
  - Only the malformed-response adapter tests stub `urlopen`.

### Test Files

- [x] `tests/devices/test_printer_adapter.py` - 7 tests for `fetch_ticket`:
  - a stored ticket is read back typed (ID, content, batch, printer time);
  - a ticket without a batch gives `None`;
  - an unknown ticket → not found;
  - a stored ticket stays readable while the printer is in error;
  - an unreachable printer → unavailable, logged with the URL;
  - malformed answers → unavailable.
- [x] `tests/tickets/test_content.py` - 7 tests:
  - the full prototype layout line by line (title, batch / order / machine / shade / date / operator, the component table with `Remazol Yellow RGB  94.0  94.2 g`, `ALL WITHIN TOLERANCE`, `*B-24187*`, the batch ID);
  - values at display resolution from the stored record (`24.000` / `23.980 kg`);
  - REPRINT only on a reprint and only as the first line;
  - `NOT ALL WITHIN TOLERANCE`;
  - Code 39 text;
  - the rule spans the widest line, with no trailing spaces;
  - the date in the server time zone (UTC 03:46 → Dhaka 09:46).
- [x] `tests/tickets/test_printing.py` - 16 tests on the service:
  - **print:** printed, with the printer's ticket stored exactly as sent and every listed field;
  - **preview:** before printing, it equals what is printed;
  - **record values:** the lines come from the records (Sodium Sulphate 23.980 kg against its 24.000 kg target);
  - **reprint:** the second print is a REPRINT whose remaining text equals the first;
  - **printer error and recovery:**
    - error → failed with the reason, nothing printed;
    - restored → printed, and not a reprint after a failed first attempt;
    - session state, `completed_at` and all record values are identical after failed and successful prints;
  - **the browser cannot fake a print** (Decision 1): an unknown ticket ID, another ticket's ID, or a ticket ID that already confirmed another job → failed; an unreadable printer → failed "Printer unavailable";
  - **finished jobs:** a finished job is final; the reason is trimmed to 200 characters;
  - **refusals:** before completion → `BATCH_NOT_COMPLETE` (no job created); no operator → `OPERATOR_REQUIRED`; unknown session / job → 404 reasons.
- [x] `tests/tickets/test_ticket_api.py` - 11 tests over HTTP:
  - the preview before any print;
  - start → 201 with the pending job and exactly the preview content;
  - print then reprint (the preview switches to REPRINT);
  - printer error then restored (job log `failed`, `printed`);
  - no operator → 403 on start and report;
  - report body validation → 400;
  - unknown job → 404;
  - CSRF → 403;
  - wrong methods → 405;
  - 4 of 5 → 409;
  - unknown session → 404.
- [x] `tests/architecture/test_integration_boundaries.py` - **updated:** `/tickets` is known by `devices/printer.py` and `printer-client.js` only.
- [x] `playwright/tickets.spec.js` - 2 tests. B-24187 is weighed 5 of 5 through the terminal UI, then the page's own `printTicket` runs:
  1. **Print, then reprint:**
     - the browser's `POST /api/tickets` carries the preview text and B-24187;
     - the job is printed and the Dummy stores the same text;
     - the second print is a REPRINT starting with `*** REPRINT ***`.
  2. **Printer error, then restored:** failed with a reason and no ticket ID; after restore, printed and not a reprint.
- [x] `playwright/helpers.js`, `playwright/write-back.spec.js` - the 5-of-5 weighing helper moved to `helpers.js` (`scanExpected`, `weighAllB24187`) and is shared by both specs. The write-back assertions are unchanged.

### Acceptance Criteria Validation

- ✅ **Story 001 AC 1** (ticket with every listed field sent to the printer): `test_prototype_layout_in_order`, `test_print_sends_the_ticket_and_is_printed`, Playwright test 1.
- ✅ **Story 001 AC 2** (the Dummy stores it; the preview shows the same content): `test_preview_shows_the_printed_content`, the API "print then reprint", Playwright test 1.
- ✅ **Story 001 AC 3** (values from the stored records): `test_values_are_the_stored_ones_at_display_resolution`, `test_ticket_lines_come_from_the_stored_records`.
- ✅ **Story 002 AC 1** (REPRINT): `test_second_print_is_a_reprint`, `test_reprint_is_marked_on_the_first_line`, Playwright test 1.
- ✅ **Story 002 AC 2** (error → failure shown, nothing printed): `test_printer_error_is_failed_and_nothing_printed`, the API test, Playwright test 2.
- ✅ **Story 002 AC 3** (restored → succeeds): `test_restored_printer_prints_and_a_failed_attempt_is_no_reprint`, Playwright test 2.
- ✅ **Story 002 AC 4** (batch and records unchanged): `test_batch_and_records_are_unchanged_by_any_print_outcome`.
- ✅ **Plan extras:** 409 before completion, 403 without an operator, the browser cannot mark an unprinted ticket printed, boundary test updated, lint clean.

### Issues Found

- **Two test-only corrections; no code changes:**
  - one of my log assertions expected a log line for an unknown session, which the existing refusal does not write; the assertion was removed;
  - two lint findings in the new tests were fixed.

### Notes

- **Workbook STEP 27** (ticket verification and evidence) follows the STEP 26 evidence. The ticket text is the server's content, and the Dummy Printer stores it unchanged (`GET /api/tickets/<id>`).
- **Dev database:** migration `tickets/0001` is applied; no data was reset.
