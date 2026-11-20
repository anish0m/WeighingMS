---
stage: test
bolt: 001-dummy-integrations
created: 2026-11-20T06:38:40Z
---

## Test Report: dummy-integrations

### Summary

- **Tests**: 31/31 passed (`npm test`, Django test runner, 0.2 s)
- **Coverage**: not measured; the coding standards set no percentage target. Every acceptance criterion of the 4 stories has at least one automated test (see below).
- **Lint gate**: `npm run lint` passes (`ruff check`, `ruff format --check`)

### Test Files

- [x] `tests/dummy_orgatex/test_seed.py` - 6 tests: 4 queued batches with prototype fields, only B-24187 has a recipe, Teal 4C components with exact `Decimal` values, all pending, re-seed idempotent (also clears consumptions), `seed_training` command
- [x] `tests/dummy_scale/test_seed.py` - 3 tests: `scale-3kg` / `scale-32kg` ready at 0, capacities 3 and 32, no duplicates on re-seed
- [x] `tests/dummy_orgatex/test_batches_api.py` - 6 tests: queue order and fields, `receivedAt` timezone-aware, B-24187 row equals the prototype, POST rejected (405), detail 200, unknown batch 404 `BATCH_NOT_FOUND` in the standard error format
- [x] `tests/dummy_orgatex/test_recipe_api.py` - 6 tests: Teal 4C with 5 components in sequence, values equal the prototype, quantities are JSON strings, name and colour, `RECIPE_NOT_AVAILABLE` for B-24188/90/91 (no `components` key), unknown batch 404
- [x] `tests/dummy_orgatex/test_consumption_api.py` - 10 tests: accept 201 + `acceptedAt`, duplicate key 200 + one record, separate keys stored separately, 12 malformed cases → 400 with nothing stored, unknown batch 404, batch without recipe 404, key reused on another batch 409, read-back with string quantities, read-back 404, POST works without a CSRF token

### Acceptance Criteria Validation

**001-seed-training-scenario**
- ✅ **Empty DB → seed → 4 batches with prototype order, machine, fabric/lot, shade, component count**: `test_seed_loads_four_queued_batches_with_prototype_fields`
- ✅ **Recipe of B-24187 is Teal 4C with the 5 prototype components, all pending**: `test_teal_4c_has_five_components_with_exact_decimal_values`, `test_all_components_start_pending`, `test_only_b24187_has_a_recipe`
- ✅ **`scale-3kg` and `scale-32kg` exist, ready, net weight 0**: `test_seed_creates_both_scales_ready_at_zero`
- ✅ **Seed again → same state, no duplicates**: `test_reseed_resets_to_the_same_state_without_duplicates`, `test_reseed_does_not_duplicate_scales`

**002-dummy-orgatex-batch-endpoints**
- ✅ **`GET /api/batches` → 4 batches with all fields and the received time**: `test_queue_returns_the_four_seeded_batches_in_order`, `test_queue_row_carries_prototype_values`, `test_queue_includes_received_time`
- ✅ **`GET /api/batches/B-24187` → details**: `test_known_batch_returns_its_details`
- ✅ **`GET /api/batches/B-99999` → 404 standard error**: `test_unknown_batch_returns_404_in_standard_error_format`

**003-dummy-orgatex-recipe-endpoint**
- ✅ **Teal 4C, 5 components in sequence, all fields, decimal strings**: `test_b24187_recipe_is_teal_4c_with_five_components_in_sequence`, `test_component_values_equal_the_prototype`, `test_quantities_are_json_strings_not_numbers`, `test_component_carries_name_and_colour`
- ✅ **B-24188 → clear "recipe not available" error, not an empty recipe**: `test_batch_without_recipe_returns_recipe_not_available`

**004-dummy-orgatex-consumption-endpoint**
- ✅ **Valid post with key K → stored, success with acceptance time**: `test_valid_post_is_stored_and_returns_acceptance_time`
- ✅ **Same K again → success, no second record**: `test_repeated_key_returns_success_without_second_record`
- ✅ **Malformed payload → validation error, nothing stored**: `test_malformed_payloads_return_validation_error_and_store_nothing`

**Plan acceptance criteria**
- ✅ `npm run dev` serves the app on port 8000 (checked in Implement: `GET /api/batches` → 200)
- ✅ `npm test` passes; `ruff check` and `ruff format --check` pass

### Issues Found

None. Ruff's auto-fix sorted the imports in the new test files; no application code changed in this stage.

### Notes

- The services log at INFO ("Training scenario seeded", "Consumption … accepted"), so those lines appear in the test output. They are not failures.
- curl evidence against the running server belongs to workbook STEP 17/18.
