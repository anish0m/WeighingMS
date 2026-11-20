---
stage: test
bolt: 003-orgatex-integration
created: 2026-11-20T08:16:09Z
---

## Test Report: orgatex-integration

### Summary

- **Tests**: 96/96 passed (`npm test`). That is the 25 new tests from this bolt plus the 71 from bolts 001 and 002, which still pass.
- **Coverage**: not measured; the coding standards set no percentage target. Every acceptance criterion of story 001-read-batches-and-recipe has at least one automated test (see below).
- **Lint gate**: `npm run lint` passes (`ruff check`, `ruff format --check`).

### Test Files

- [x] `tests/orgatex/test_adapter.py` - 20 tests.
  - Tests that use real HTTP run against a `LiveServerTestCase`, which serves the seeded Dummy, with `ORGATEX_BASE_URL` pointed at it:
    - **Reads (5):**
      - the queue lists the 4 batches in seed order, with `received_at` as a datetime;
      - B-24187's details are typed;
      - the recipe has 5 components in sequence, every quantity a `Decimal`;
      - the values equal the prototype (Yellow RGB 94.0 ± 0.5 g; Sodium Sulphate 24.000 ± 0.120 kg);
      - results are immutable.
    - **NotFound (4):**
      - unknown batch → `BATCH_NOT_FOUND`, for both the batch and the recipe read;
      - B-24188 → `RECIPE_NOT_AVAILABLE`;
      - NotFound is never reported as Unavailable.
    - **Unavailable (5):**
      - with the Dummy switched off, every read raises Unavailable and logs a WARNING;
      - the log line has the URL, `503`, `ORGATEX_UNAVAILABLE` and the batch ID;
      - reads work again after the Dummy is switched back on;
      - an unreachable host is Unavailable and the URL is logged;
      - a bare 404 (wrong base URL) is Unavailable, not NotFound.
  - **Malformed responses (6):** these stub `urlopen` at the HTTP boundary. A valid stub parses; each of the following gives Unavailable with a "malformed" WARNING:
    - a float quantity;
    - a non-decimal string;
    - a missing field;
    - a non-JSON body;
    - a recipe for another batch.
- [x] `tests/architecture/test_integration_boundaries.py` - 5 tests:
  - the import scanner detects `dummy_*` imports (a self-check, so the scan can't pass trivially);
  - the scan covers the `orgatex` app;
  - no WeighingMS app imports a `dummy_*` module;
  - only `orgatex/adapter.py` among the Python files knows the `/batches` paths;
  - only `orgatex-client.js` among the JS files under `src/` knows them.

### Acceptance Criteria Validation

**001-read-batches-and-recipe**
- ✅ **Seeded Dummy → queue, B-24187 and its recipe come back as typed objects with `Decimal` quantities**: `test_queue_returns_seeded_batches_in_order`, `test_batch_details_are_typed`, `test_recipe_components_in_sequence_with_decimal_quantities`, `test_recipe_values_equal_the_prototype`
- ✅ **Unknown batch → a NotFound result, not a generic error**: `test_unknown_batch_raises_not_found`, `test_unknown_batch_recipe_raises_not_found`, `test_not_found_is_not_unavailable`
- ✅ **Dummy unavailable → an Unavailable result, with the failure logged with request details**: `test_every_read_is_unavailable_while_dummy_is_down`, `test_failure_log_has_request_details`, `test_unreachable_orgatex_is_unavailable`

**Story test expectations**
- ✅ **Tests run against the running Dummy endpoints (success, NotFound, Unavailable)**: every live test uses real HTTP
- ✅ **No WeighingMS module imports `dummy_*`**: `test_no_weighingms_app_imports_a_dummy`

**Plan acceptance criteria**
- ✅ **Malformed responses → Unavailable**: the 5 `MalformedResponseTests` rejection tests
- ✅ **One Python module and one JS file know the OrgaTEX paths**: `test_only_the_python_adapter_knows_the_orgatex_paths`, `test_only_the_js_client_knows_the_orgatex_paths`
- ✅ **`npm test` and `npm run lint` pass**

### Issues Found

None in the application code.
- Ruff flagged 5 nested `with` blocks in the new test file (SIM117). I combined them into parenthesised `with` statements.
- `ruff format` re-wrapped 2 lines.

### Notes

- Expected log lines appear in the test output: "Training scenario seeded", "Service Unavailable: /api/…", "Not Found: /wrong/…" and the adapter's own warnings. They come from the deliberate failure cases; they are not failures.
- The JS client is only syntax-checked here (`node --check`, Implement stage). Its real check comes in bolt 007 and the STEP 19 evidence: the Network tab must show `GET /api/batches`, `/api/batches/B-24187` and `/api/batches/B-24187/recipe`.
