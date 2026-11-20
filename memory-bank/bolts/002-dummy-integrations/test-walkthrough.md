---
stage: test
bolt: 002-dummy-integrations
created: 2026-11-20T06:58:20Z
---

## Test Report: dummy-integrations

### Summary

- **Tests**: 71/71 passed (`npm test`): the 40 new tests from this bolt plus bolt 001's 31, which still pass
- **Coverage**: not measured; the coding standards set no percentage target. Every acceptance criterion of stories 005–007 has at least one automated test (see below).
- **Lint gate**: `npm run lint` passes (`ruff check`, `ruff format --check`)

### Test Files

- [x] `tests/helpers.py` - Shared JSON post/put helpers and a failure-mode helper
- [x] `tests/dummy_scale/test_scale_api.py` - 6 tests: list (precision in g, floor in kg), status, weight as a decimal string with unit/status/readAt, tare sets 0, tare needs POST, unknown scale 404
- [x] `tests/dummy_scale/test_simulate.py` - 8 tests: dispense 94.2 g, overshoot 96.4 g, reset 0, set 93.4/93.5/94.0/94.5/94.6, kg dispense 24.048, response is the new reading, 9 invalid requests → 400 with the weight unchanged, unknown scale 404
- [x] `tests/dummy_scanner/test_scanner_api.py` - 6 tests: no scan → `null`, batch scan becomes the latest, dyestuff scan replaces it, status ready, 5 invalid scans → 400 with nothing stored, re-seed clears scans
- [x] `tests/dummy_printer/test_printer_api.py` - 5 tests: print stores and returns an ID, read back unchanged by ID, unknown ticket 404, status ready, 5 invalid tickets → 400 with nothing stored
- [x] `tests/training/test_modes.py` - 15 tests:
  - all modes start `ok`; invalid target or mode → 400; a mode change needs PUT; re-seed resets every mode;
  - OrgaTEX unavailable → 503 on all 4 endpoints, a consumption post stores nothing, back to `ok` resumes;
  - scale disconnected → `disconnected` status with no weight, tare and simulate refused, the other scale is unaffected, back to `ok` resumes;
  - scanner unavailable → 503 with nothing stored, back to `ok` resumes;
  - printer error → 503 with nothing stored, back to `ok` resumes.
- [x] `tests/dummy_scale/test_seed.py` - bolt-001 capacity test updated for Decision 1 (`scale-3kg` 3000 g, `scale-32kg` 32 kg)

### Acceptance Criteria Validation

**005-dummy-scale-api**
- ✅ **`GET /api/scales` lists `scale-3kg` (precision) and `scale-32kg` (floor)**: `test_list_returns_precision_and_floor_scale`
- ✅ **weight/status return a decimal-string net weight, unit and ready/disconnected**: `test_weight_returns_decimal_string_unit_and_status`, `test_status_returns_ready`, `test_disconnected_scale_reports_status_and_no_weight`
- ✅ **tare sets net weight to 0**: `test_tare_sets_net_weight_to_zero`
- ✅ **94.0 g ± 0.5 g: dispense / overshoot / reset / set 93.4 → 94.2 / 96.4 / 0.0 / 93.4 g**: `test_dispense_lands_at_target_plus_0_4_tolerance`, `test_overshoot_lands_at_target_plus_4_8_tolerance`, `test_reset_returns_weight_to_zero`, `test_set_exact_weight_for_tolerance_boundaries`

**006-dummy-scanner-and-printer**
- ✅ **A batch or dyestuff scan becomes the latest scanned code**: `test_batch_scan_becomes_the_latest_scan`, `test_dyestuff_scan_replaces_the_previous_latest`
- ✅ **`POST /api/tickets` stores the ticket and returns an ID**: `test_print_stores_ticket_and_returns_id`
- ✅ **The stored ticket is returned with the same content by ID**: `test_stored_ticket_is_returned_unchanged_by_id`

**007-dummy-failure-toggles**
- ✅ **OrgaTEX unavailable → every OrgaTEX endpoint returns 503**: `test_unavailable_returns_503_on_every_orgatex_endpoint`, `test_unavailable_consumption_post_stores_nothing`
- ✅ **`scale-3kg` disconnected → status disconnected, no weight**: `test_disconnected_scale_reports_status_and_no_weight`
- ✅ **Scanner unavailable / printer error → error and nothing stored**: `test_unavailable_scan_returns_error_and_stores_nothing`, `test_error_print_returns_error_and_stores_nothing`
- ✅ **Back to ok → normal responses resume**: `test_back_to_ok_resumes_normal_responses`, `test_back_to_ok_resumes_readings`, `test_back_to_ok_resumes_scanning`, `test_back_to_ok_resumes_printing`

**Plan acceptance criteria**
- ✅ `npm test` (bolt 001 + bolt 002) and `npm run lint` pass

### Issues Found

None in the application code. Ruff's auto-fix made 5 small changes in the new test files (import order and `Decimal("0")` → `Decimal(0)`).

### Notes

- The services log at INFO, so lines such as "Dummy scale scale-3kg simulate dispense" appear in the test output. They are not failures.
- STEP 16 evidence (`curl -s http://localhost:8000/api/scales | jq`) is taken by the user against `npm run dev`.
