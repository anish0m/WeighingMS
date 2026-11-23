---
stage: test
bolt: 014-orgatex-integration
created: 2026-11-23T10:20:00Z
---

## Test Report: orgatex-integration (consumption write-back)

### Summary

- **Django: 516/516** (`npm test`): 475 earlier tests plus 41 new.
- **Playwright: 58/58** (`npx playwright test`): 56 earlier tests plus 2 new.
- **Lint:** `npm run lint` passes.
- **Coverage:** no percentage target (coding standards). Every acceptance criterion of stories 002 and 003 has at least one automated test (below).
- **No mocks for the write-back paths:** the Django tests run against the live Dummy OrgaTEX on a `LiveServerTestCase`; the endpoint tests weigh B-24187 5 of 5 through the live Dummy Scale and Scanner. Only the malformed-response tests stub `urlopen`, as bolt 003's adapter tests do.

### Test Files

- [x] `tests/orgatex/test_adapter_consumption.py` - 8 tests for `fetch_consumptions`:
  - empty before any post;
  - typed results with `Decimal` quantities and OrgaTEX's `acceptedAt`;
  - a duplicate post is still one consumption;
  - unknown batch → not found; Dummy unavailable → unavailable, logged with the URL;
  - malformed answers (float quantity, non-ISO time, another batch) → unavailable.
- [x] `tests/orgatex/test_write_back.py` - 18 tests:
  - **key and body:** `WMS-B-24187-S7`; the five components as decimal strings; never an exponent;
  - **start:** pending with one attempt; a retry reuses the row and key (attempts 2); after "not written" it is pending again; a confirmed row stays confirmed; the database refuses a confirmation time on an unconfirmed row;
  - **verify** against the live Dummy:
    - an accepted post → CONFIRMED with OrgaTEX's time;
    - a repeat trigger → same key, Dummy `200` duplicate, one consumption;
    - unavailable → not written "OrgaTEX unavailable";
    - retry when back → CONFIRMED, attempts 2;
    - timeout after storing → CONFIRMED, no duplicate;
    - "posted" but not stored → not written "OrgaTEX did not store the consumption";
    - another key's consumption does not confirm;
    - unreachable OrgaTEX → not written, logged;
    - the browser's reason is trimmed to 200 characters;
    - a confirmed write-back is never changed back.
- [x] `tests/weighing/test_write_back_api.py` - 15 tests over HTTP after a real 5-of-5 weighing:
  - status `null` before the first start;
  - the start response holds the exact body (five codes, actual weights `1241.5`, `385.4`, `94.2`, `24.048`, `9.612`, units) and the status;
  - one post → one consumption → CONFIRMED with OrgaTEX's `acceptedAt`, and the GET status matches;
  - triggering again keeps one consumption;
  - unavailable → not written with the reason, and the five records unchanged;
  - retry with the same key → CONFIRMED, attempts 2;
  - ambiguous failure → CONFIRMED, no duplicate;
  - a "posted" report without a stored consumption → not written;
  - refusals:
    - 4 of 5 → 409 `BATCH_NOT_COMPLETE` (and no row is created);
    - a report before start → 409 `WRITE_BACK_NOT_STARTED`;
    - no operator → 403;
    - unknown session → 404 on all three endpoints;
    - an invalid report body → 400;
    - no CSRF token → 403;
    - a wrong method → 405.
- [x] `playwright/write-back.spec.js` - 2 tests. B-24187 is weighed 5 of 5 through the terminal UI, then the page's own `writeBack` runs:
  1. **CONFIRMED:**
     - the browser's `POST /api/batches/B-24187/consumption` carries the server's key and the five codes, with quantities as strings;
     - triggering again stays confirmed (attempts 2), and the Dummy holds one consumption.
  2. **Dummy OrgaTEX unavailable:**
     - the result is not written, "OrgaTEX unavailable", with no confirmation time;
     - after switching back to ok, a retry with the same key → CONFIRMED, attempts 2, one consumption.

### Acceptance Criteria Validation

- ✅ **Story 002 AC 1** (one post with per-component actuals and a key derived from the batch): API test "start returns key and body", API test "one post creates one consumption", Playwright test 1.
- ✅ **Story 002 AC 2** (same key again, still one record): `test_repeat_trigger_keeps_one_consumption`, API test "triggering again", Playwright test 1.
- ✅ **Story 002 AC 3** (CONFIRMED with the acceptance time): `test_accepted_post_is_confirmed_with_orgatex_time`, and the API test compares `confirmedAt` with the Dummy's `acceptedAt`.
- ✅ **Story 003 AC 1** (unavailable → not written with reason, never CONFIRMED, records stay): service and API tests, Playwright test 2.
- ✅ **Story 003 AC 2** (retry with the same key → CONFIRMED with time): service and API tests, Playwright test 2.
- ✅ **Story 003 AC 3** (timeout after storing → no duplicate): `test_timeout_after_the_dummy_stored_the_post_is_confirmed`, API test "ambiguous failure".
- ✅ **Plan extras:**
  - 4 of 5 refused, no operator refused, unknown session 404;
  - a browser claim alone never gives CONFIRMED (NFR-7);
  - boundary test still passes;
  - lint clean.

### Issues Found

- **One test expectation was wrong; the code was fine:**
  - The Dummy stores quantities as `decimal(12,4)`, so its `GET` returns `"1241.5000"`, while the `201` answer echoes `"1241.5"`.
  - The API test now compares the stored quantities as `Decimal`s. They are equal in value.
- No code changes were needed.

### Notes

- **Workbook STEP 26 Network evidence** (`STEP-26-request.png`, `STEP-26-response.png`) needs the View 3 flow (bolts 015–017). The browser request is already the real one: DevTools will show `POST /api/batches/B-24187/consumption` with the key and five components, answered `201`.
- **Dev database:** unchanged by this stage. B-24187 is still 1 of 5, and migration `orgatex/0001` is applied.
