---
stage: test
bolt: 004-device-integration
created: 2026-11-20T08:32:10Z
---

## Test Report: device-integration

### Summary

- **Tests**: 123/123 passed (`npm test`). That is the 27 new tests from this bolt plus the 96 from bolts 001–003, which still pass. Bolt 003's 2 OrgaTEX path tests are now 1 table-driven test covering all five integration paths.
- **Coverage**: not measured; the coding standards set no percentage target. Every acceptance criterion of stories 001–005 is covered: by a Python test here, or by the approved Playwright tests in bolts 007 and 011 (Decision 2).
- **Lint gate**: `npm run lint` passes (`ruff check`, `ruff format --check`).

### Test Files

- [x] `tests/devices/test_scale_adapter.py` - 18 tests. All except the malformed-response group run over real HTTP against a `LiveServerTestCase` with the seeded Dummy Scale.
  - **Read (5):**
    - simulated 90.0 g → `Decimal("90.0")`, g, ready, with `read_at`;
    - `scale-32kg` reads in kg (24.048);
    - the next read returns the new weight;
    - reading `scale-32kg` opens only `/scales/scale-32kg/weight` (URLs recorded through the real `urlopen`);
    - status is `ready`.
  - **Tare (2):**
    - tare → net 0, and a re-read is 0;
    - tare while disconnected raises `ScaleDisconnected`, and the weight is unchanged afterwards (214 g).
  - **Disconnected (4):**
    - weight read raises `ScaleDisconnected`, logged with URL, `503` and `SCALE_DISCONNECTED`;
    - `read_status` → `disconnected`;
    - the other scale is unaffected;
    - reads resume after `ok`.
  - **Unavailable (2):**
    - unknown scale → `ScaleUnavailable`;
    - unreachable host → `ScaleUnavailable`, not disconnected, and the URL is logged.
  - **Malformed (5),** stubbed at `urlopen`:
    - a valid stub parses;
    - each of these gives `ScaleUnavailable` with a "malformed" WARNING: a float weight, a reading from another scale, an unknown status, a non-JSON body.
- [x] `tests/devices/test_scanner_adapter.py` - 8 tests over real HTTP.
  - **Receive (4):**
    - no scan → `None`;
    - a batch scan of B-24187 is received;
    - `read_new_scan(previous id)` → `None`, so each scan is received once;
    - a later dyestuff scan is received as new.
  - **Unavailable (4):**
    - reading gives `ScannerUnavailable`, logged with `503` and `SCANNER_UNAVAILABLE`;
    - a scan attempt while unavailable is refused, and nothing appears after recovery;
    - reads resume after `ok`;
    - unreachable host → `ScannerUnavailable`.
- [x] `tests/architecture/test_integration_boundaries.py` - Reworked: 6 tests, previously 5.
  - The import tests are unchanged: the scanner self-check, the coverage check, no `dummy_*` imports.
  - **New `PATH_OWNERS` table:** `/batches`, `/scales`, `/scanner`, `/printer` and `/tickets` are each known by at most one Python adapter and exactly one JS client.
  - `device-status.js` knows no device paths.

### Acceptance Criteria Validation

**001-read-live-scale-weight**
- ✅ **`scale-3kg` at 90.0 g → 90.0 g `Decimal`, unit g, ready**: `test_reading_is_decimal_with_unit_and_ready`
- ✅ **A changed Dummy weight is available on the next poll, without a reload**:
  - server side: `test_next_read_returns_the_new_weight`;
  - browser 200 ms polling: Implement-stage Node smoke test (6 polls in ≈ 1.15 s), plus Playwright in bolt 011 ("readout follows simulate").
- ✅ **Active component on `scale-32kg` → only `scale-32kg` is read**: `test_only_the_requested_scale_is_read`, `test_floor_scale_reads_in_kg`

**002-tare-command**
- ✅ **Tare → net 0.0 g**: `test_tare_sets_net_weight_to_zero`
- ✅ **Disconnected → failure, nothing tared**: `test_tare_on_disconnected_scale_fails_and_tares_nothing`

**003-scanner-input**
- ✅ **B-24187 scanned → received once**: `test_batch_scan_is_received`, `test_each_scan_is_received_once`
- ✅ **Scanner unavailable → error, no state change**: `test_unavailable_scanner_reports_an_error`, `test_scan_attempt_while_unavailable_changes_nothing`

**004-printer-adapter** (JS client only, Decision 1)
- ✅ **Printer ready → ticket ID returned**: Implement-stage Node smoke test (`printed ticketId 2`); Playwright in bolt 016 / STEP 27
- ✅ **Printer error → PrinterError**: Implement-stage Node smoke test (`error PRINTER_ERROR`). The Dummy side is tested by bolt 002's `test_error_print_returns_error_and_stores_nothing`.

**005-device-status-and-fail-safe**
- ✅ **All ready → SCALE 3 kg, SCALE 32 kg, SCANNER, PRINTER report READY**: Implement-stage Node smoke test; Playwright in bolt 007 ("status change on a toggled Dummy")
- ✅ **`scale-3kg` disconnected → not ready within 2 s; confirmation blocked**:
  - status poll every 1 s;
  - server re-read raises `ScaleDisconnected`: `test_disconnected_scale_gives_no_weight`, `test_disconnected_status_is_not_ready`;
  - the confirm check itself is bolt 010.
- ✅ **Any failure is never shown as ready**:
  - Python: an unreachable host or malformed body is Unavailable, never a reading;
  - JS: covered in the Node smoke test.

**Plan acceptance criteria**
- ✅ **One module per device knows its paths; no `dummy_*` imports**: `SingleAdapterTests`, `NoDummyImportTests`
- ✅ **`npm test` and `npm run lint` pass**

### Issues Found

None in the application code. Ruff's formatter re-wrapped some long lines in the new test files.

### Notes

- The test output contains expected log lines from the deliberate failure cases ("Service Unavailable", device WARNINGs). They are not failures.
- The JS behaviour checks above come from the Implement-stage Node smoke test, which is not an automated test. Per Decision 2, the automated browser tests are the Playwright tests in bolts 007, 011 and 016.
