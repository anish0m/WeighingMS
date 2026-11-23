---
stage: test
bolt: 009-weighing-station
created: 2026-11-23T05:02:30Z
---

## Test Report: weighing-station (weighing rules)

### Summary

- **Tests**:
  - **Django: 59/59 new tests pass.** `npm test` reports **360/360**: 301 earlier tests plus 59 new.
  - **Playwright: 19/19** still pass. This bolt has no UI, so this is a regression run only.
- **Lint**: `npm run lint` passes. `makemigrations --check` finds no changes; this bolt adds no model.
- **Coverage**: not measured. The coding standards set no percentage target. Every acceptance criterion, approved model decision and ADR is mapped below.
- **Live test:** one test reads the real seeded B-24187 through the OrgaTEX adapter (training contract), as in bolt 008.

### Test Files

- [x] `tests/weighing/test_scale_selection.py` - 13 tests:
  - Yellow RGB → `scale-3kg` "3 kg precision", `automatic`;
  - Sodium Sulphate → `scale-32kg` "32 kg floor", kg;
  - the five Teal 4C components → 3 × precision, 2 × floor;
  - 3 kg / 3.000 kg → precision and 3.0001 kg → floor; 3000 g → precision and 3000.1 g → floor;
  - an explicit threshold; an unknown unit is refused;
  - the configured threshold:
    - the default is 3 kg;
    - `override_settings` to 0.05 kg moves Yellow RGB to the floor scale, and to 30 kg moves Sodium Sulphate to the precision scale;
    - an invalid configured value (float, string, 0, −1, NaN, None) → `ImproperlyConfigured`;
  - the settings reader `positive_decimal`:
    - the default applies without the environment variable, and the environment value wins when set;
    - `abc`, empty, `0`, `-1`, `NaN` and `Infinity` stop startup.
- [x] `tests/weighing/test_tolerance.py` - 24 tests:
  - the five boundary weights 93.4 / 93.5 / 94.0 / 94.5 / 94.6 g;
  - the captions for g and kg;
  - 84.5 g is under and 84.6 g is near (90 % of 94.0);
  - the kg band 23.880 – 24.120 at its edges;
  - zero tolerance;
  - `band_for` on stored snapshot components;
  - still to weigh at 0.0 / 90.0 g and at or above target (never negative); a negative reading is under;
  - the status line for each zone, in g and kg; the surplus only when over;
  - display: "24.000 kg", "9.600 kg", "94.0 g", "4.0 g", "0.0 g", no exponent, −0.04 → "0.0 g";
  - rounding at resolution: 94.54 / 94.55 / 93.45 / 93.44 g, and in kg;
  - exact g ↔ kg conversion; a kg reading on a g component and a g reading on a kg component; an unknown unit;
  - every value is a `Decimal`; the three rule modules contain no `float(`.
- [x] `tests/weighing/test_rules_api.py` - 22 tests:
  - **`GET …/components`:**
    - Yellow RGB's `target`, `targetText`, `scale` and `tolerance` blocks;
    - Sodium Sulphate on the floor scale with "24.000 kg";
    - all five scales;
    - a changed threshold is followed through the API.
  - **`GET …/evaluation`:**
    - the five boundary weights;
    - the full JSON for 93.4 g; the surplus at 94.6 g;
    - target and still to weigh; under below 90 %; the within status line;
    - 94.54 → "94.5" within and 94.55 → over;
    - a kg reading judged in g; Sodium Sulphate in kg; a negative reading;
    - no operator needed.
  - **Refusals:**
    - 14 invalid parameter sets → `400 INVALID_REQUEST`: missing values, empty, exponent, NaN, Infinity, comma, leading space, trailing dot, plus sign, 7 digits, `lb`, `G`;
    - unknown session → `404 SESSION_NOT_FOUND`; unknown component → `404 COMPONENT_NOT_FOUND`;
    - `405` for POST / PUT / PATCH / DELETE.
  - **`rules.evaluate_reading`** (the bolt 010 contract): returns the scale, band, target text and zone; an unknown session is refused.
  - **Live:** the real B-24187 seed gives the five scales, the target texts and the captions.
- **Changed:**
  - `tests/weighing/factories.py`: `TEAL_4C` now carries each component's target, tolerance and display maximum from the prototype, instead of the placeholders 1 / 0 / 2.
  - `tests/weighing/test_identity_api.py`: `test_yellow_rgb_component` compares the whole component object, so it now expects the four new fields (bolt 008's fields are unchanged).
- The architecture boundary tests are unchanged and pass. The new modules import no `dummy_*` module and contain no Dummy path.

### Acceptance Criteria Validation

**002-select-scale-automatically**
- ✅ **AC 1: Yellow RGB (94.0 g) → `scale-3kg`, shown as "automatic".** `test_yellow_rgb_goes_to_the_precision_scale_automatically`, `test_yellow_rgb_rules`.
- ✅ **AC 2: Sodium Sulphate (24.000 kg) → `scale-32kg`, units kg.** `test_sodium_sulphate_goes_to_the_floor_scale_in_kg`, `test_sodium_sulphate_rules`.
- ✅ **AC 3: 3 kg → precision, 3.0001 kg → floor.** `test_exactly_3_kg_is_precision_and_3_0001_kg_is_floor`, `test_the_boundary_holds_for_targets_in_grams`.
- ✅ **AC 4: a changed threshold is followed without code change.** `test_a_changed_threshold_changes_the_selection`, `test_a_changed_threshold_is_followed_without_code_change`, `test_the_environment_overrides_the_default`.

**004-target-and-remaining**
- ✅ **AC 1: 0.0 g → target 94.0 g, still to weigh 94.0 g.** `test_at_zero_the_whole_target_is_still_to_weigh`, `test_target_and_still_to_weigh`.
- ✅ **AC 2: 90.0 g → 4.0 g and "DISPENSE — 4.0 g REMAINING".** `test_at_90_g_four_grams_remain`, `test_target_and_still_to_weigh`.
- ✅ **AC 3: at or above target → 0.0, never negative.** `test_never_negative_at_or_above_target`.
- ✅ **AC 4: "24.000 kg"; 3 decimals for kg, 1 for g.** `test_grams_have_one_decimal_and_kilograms_three`, `test_sodium_sulphate_rules`.

**005-evaluate-inclusive-tolerance**
- ✅ **AC 1: 93.4 / 93.5 / 94.0 / 94.5 / 94.6 g → near / within / within / within / over; can confirm false / true / true / true / false.** `test_the_five_boundary_weights` (rules and API). Here "can confirm" is the tolerance verdict `withinTolerance` (model Decision 4); bolt 010 adds the material gate and "scale connected".
- ✅ **AC 2: caption "TOLERANCE ±0.5 g (93.5 – 94.5)".** `test_the_caption`, `test_yellow_rgb_rules`.
- ✅ **AC 3: below 90 % of target → under.** `test_below_90_percent_of_target_is_under`, `test_below_90_percent_is_under`.
- ✅ **AC 4: Decimal arithmetic only.** `test_every_value_is_a_decimal`, `test_the_rule_modules_never_use_float`.

**Approved model decisions and ADRs**
- ✅ **1. Reading in another unit is converted:** the `ConversionTests` class, `test_a_reading_in_kg_is_judged_in_grams`.
- ✅ **2 / ADR-009. One value at display resolution:** the `ResolutionTests` class, `test_the_evaluated_value_is_the_display_value`.
- ✅ **3. Threshold setting with environment override, invalid value refused:** the `ConfiguredThresholdTests` and `ThresholdSettingTests` classes.
- ✅ **4. Tolerance verdict only, for bolt 010:** the `EvaluateReadingTests` class.
- ✅ **5. Over shows the surplus amount only:** `test_surplus_only_when_over`, `test_over_reading_shows_the_surplus`.
- ✅ **ADR-008. The server evaluates each reading:** the `EvaluationApiTests` class. The UI side of this decision is bolt 011.

### Issues Found

- **In the application: none.**
- **In the tests (first drafts, fixed in the tests):**
  - bolt 008's whole-object component test failed after the four new fields were added. That was expected; it now includes them;
  - the bolt 008 factory used placeholder targets (1 g, tolerance 0). They now come from the Teal 4C seed;
  - the "no float" check also matched the word in a docstring. It now looks for `float(` calls, as the design specifies.

### Notes

- Story 005's Playwright check ("confirm disabled at 93.4 and 94.6") needs the weigh screen. It is done in bolt 011, together with the evaluation calls on each changed reading (ADR-008).
- Bolt 010's confirm must use `rules.evaluate_reading` on the server's own scale re-read and store the evaluated `net` as `actualWeight` (ADR-009), together with `check_material_ready` (ADR-007).
- "Bad Request", "Not Found" and "Method Not Allowed" lines in the test output are Django's log of the deliberate refusal cases.
