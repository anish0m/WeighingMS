---
stage: test
bolt: 008-batch-recipe-management
created: 2026-11-23T04:20:00Z
---

## Test Report: batch-recipe-management (material identity)

### Summary

- **Tests**:
  - **Django: 63/63 new tests passed.** `npm test` reports **301/301**: 238 earlier tests plus 63 new.
  - **Playwright: 19/19** still pass (no UI change in this bolt; regression run only).
- **Lint**: `npm run lint` passes. `makemigrations --check` finds no missing migration.
- **Coverage**: not measured. The coding standards set no percentage target; every acceptance criterion and every approved model decision is mapped below.
- **Live tests:** the scan tests run against the live Dummy Scanner and the seeded Dummy OrgaTEX (training contracts) through the real adapters, like the bolt 004 adapter tests. Training toggles switch the scanner to unavailable.

### Test Files

- [x] `tests/batches/test_material.py` - 14 tests:
  - `format_quantity`: `214 g`, `214.5 g`, `0.5 g`, `1240 g` (no exponent), `1.850 kg`, `24.000 kg`, and `1.8505 kg` not rounded;
  - the Yellow RGB and Sodium Sulphate headers; a blank lot and container shown as `—`;
  - `material_faults`: none, missing lot, blank lot, missing container, lot before container;
  - **live:** the real seeded B-24187, selected through the OrgaTEX adapter, gives the two AC headers.
- [x] `tests/weighing/test_identity_check.py` - 28 tests:
  - **verify (live scanner):** match → verified with operator and log; other code → wrong dyestuff, logged with expected and scanned code, readiness refused; exact (case-sensitive) comparison; surrounding spaces ignored; an auxiliary (AUX-0101) is verified; another component's code is wrong; a wrong scan after a verified one blocks again; a right scan after a wrong one unblocks; the same scan is recorded once; a scan stays with the component it was first checked for;
  - **refusals, nothing stored:** batch scan; a scan that is no longer the latest; an unknown scan ID; no scan at all; scanner unavailable (identity stays unverified); no operator (refused before the scanner is read); unknown component; unknown session;
  - **readiness (`check_material_ready`):** not verified; wrong dyestuff; verified and complete → ready; missing lot even when verified; missing container; lot checked before identity; per component; per session;
  - **append-only:** a check can't be changed or deleted.
- [x] `tests/weighing/test_identity_api.py` - 21 tests:
  - **`GET …/components`:** 5 components in sequence; the full Yellow RGB JSON (header, `tareText`, unverified, `IDENTITY_NOT_VERIFIED`); Sodium Sulphate D-03 / `1.8500` / `1.850 kg`; verified → ready; wrong dyestuff → `WRONG_DYESTUFF`; missing lot → `LOT —` and `LOT_MISSING`; readable without an operator; unknown session 404;
  - **`POST …/identity` before the scanner:** 8 invalid bodies → 400; no operator → 403; unknown session / component → 404; other methods → 405 (both endpoints); no CSRF token → 403, nothing stored;
  - **`POST …/identity` live:** match → 201 with the full check JSON; other code → 201 "Wrong dyestuff" and the component not ready; a `code` in the body is ignored; re-send → 200 with the first check; batch scan → 409; stale scan → 409; scanner unavailable → 503.
- `tests/weighing/factories.py` - extended with `teal_selection(overrides)` (B-24187's five snapshot components from the training seed) and `session()`.
- The architecture boundary tests (unchanged) pass: `weighing.identity` reaches the scanner only through `devices.scanner`, with no Dummy path and no `dummy_*` import.

### Acceptance Criteria Validation

**004-verify-dyestuff-identity**
- ✅ **AC 1: Yellow RGB active, DYE-4471 scanned → identity verified.** `test_matching_scan_verifies_yellow_rgb`, `test_matching_scan_is_201_verified`.
- ✅ **AC 2: a different code → "Wrong dyestuff" and confirmation stays blocked.** `test_different_code_is_wrong_dyestuff_and_blocks`, `test_other_code_is_201_wrong_dyestuff`, `test_wrong_dyestuff_is_shown`, `test_wrong_scan_after_a_verified_one_blocks_again`.
- ✅ **AC 3: not verified → confirmation refused.** `test_not_verified_is_refused` (`check_material_ready`, the gate bolt 010's confirm calls, ADR-007); `test_yellow_rgb_component` (`materialReady: false`).

**005-show-lot-and-container**
- ✅ **AC 1: the Yellow RGB header reads "Remazol Yellow RGB · DYE-4471 · LOT 2026-0387 · CONTAINER C-12 · TARE 214 g".** `test_yellow_rgb_header`, `test_yellow_rgb_component`, `test_b24187_headers_come_from_the_seed`.
- ✅ **AC 2: no lot → confirmation refused.** `test_missing_lot_is_refused_even_when_verified`, `test_lot_is_checked_before_identity`, `test_missing_lot_is_reported`.
- ✅ **AC 3: Sodium Sulphate shows container D-03 and tare 1.850 kg.** `test_sodium_sulphate_shows_d03_and_1850_kg` (service and API), `test_b24187_headers_come_from_the_seed`.

**Approved model decisions**
- ✅ **1. Readiness gate for bolt 010:** the `ReadinessTests` class.
- ✅ **2. The server reads the scan (ADR-006):** `test_code_in_the_body_is_ignored`, the stale / unknown / no-scan / unavailable refusals.
- ✅ **3. The latest check counts:** `test_wrong_scan_after_a_verified_one_blocks_again`, `test_right_scan_after_a_wrong_one_unblocks`.
- ✅ **4. Missing container refused:** `test_missing_container_is_refused`.
- ✅ **5. Auxiliaries scanned too:** `test_auxiliaries_are_verified_too`.

### Issues Found

- **In the application: none.**
- **In the tests (first drafts, fixed in the tests):**
  - the factory took overrides as `**kwargs` with integer keys (a `TypeError`); it now takes a dict;
  - two tests opened a second open session for B-24187 before closing the first, which the `one_open_session_per_batch` constraint correctly refused; the first session is now closed first;
  - ruff FURB157 (`Decimal("2")` → `Decimal(2)`) in the factory, fixed with `ruff --fix`.

### Notes

- The "confirmation refused" ACs are proven at the gate (`check_material_ready`). Bolt 010 must call it from confirm and repeat the refusals end to end (ADR-007).
- The "Scan dyestuff" step on the weigh screen and its Playwright test are bolt 011 (story 004 "Playwright: scan step").
- `[WebServer]`-style request lines and "Conflict" / "Service Unavailable" lines in the test output are the live server's log of the deliberate refusal cases.
