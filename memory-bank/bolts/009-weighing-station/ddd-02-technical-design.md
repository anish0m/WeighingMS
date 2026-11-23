---
stage: design
bolt: 009-weighing-station
created: 2026-11-23T04:45:57Z
---

## Technical Design: weighing-station (weighing rules)

This design is based on the approved domain model (`ddd-01-domain-model.md`, APPROVE MODEL 2026-11-23T04:45:57Z) and its five recommended decisions:
1. a reading in another unit is converted exactly to the component's unit;
2. the reading is taken once at display resolution (0.1 g / 0.001 kg, round half up), and that value is shown, evaluated and recorded;
3. the threshold is the setting `WEIGHING_SCALE_THRESHOLD_KG` (default 3), overridable by an environment variable of the same name;
4. this bolt gives the tolerance verdict only; bolt 010's confirm combines it with the material gate and "scale connected";
5. the over status line shows the surplus amount only.

### Architecture Pattern

**Layered Django app with a plain-Python service layer**, as in bolts 006 and 008 (coding standards: rules in service modules, thin views). No new app, no new model, no migration.

- The rules are **pure functions on Decimal values** in two new `weighing` modules. They know nothing about Django requests, the database or the Dummy APIs, so they are unit-tested directly and reused unchanged by bolt 010's confirm.
- **The server is the single source of the rules** (design choice A, below). The browser never re-implements zone or tolerance logic. It shows what the server returns:
  - the component's scale, target, band and caption come with `GET …/components` (extended);
  - the zone, still-to-weigh and status line of a live reading come from a new read-only evaluation endpoint.
- The live reading itself stays where STEP 12 put it: the browser's scale client polls `GET /api/scales/<scaleId>/weight` on the Dummy Scale (training contract). This bolt only tells it **which** `scaleId` to poll.
- `weighing` still imports no `dummy_*` module and knows no Dummy path (boundary tests).

### Layer Structure

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Presentation   weighing/views.py, weighing/urls.py                   │  GET …/components (extended)
│                                                                      │  GET …/components/<seq>/evaluation (new)
├──────────────────────────────────────────────────────────────────────┤
│ Application    weighing/identity.py   session_components (extended)  │  session + component lookup (bolt 008)
│                weighing/rules.py      component_rules, evaluate_     │
│                                       reading                        │
├──────────────────────────────────────────────────────────────────────┤
│ Domain         weighing/scale_selection.py  ScaleClass, select_scale │  pure, Decimal only
│                weighing/tolerance.py        quantities, band, zone,  │
│                                             evaluation, format       │
├──────────────────────────────────────────────────────────────────────┤
│ Configuration  settings: WEIGHING_SCALE_THRESHOLD_KG                 │  env override, validated at startup
└──────────────────────────────────────────────────────────────────────┘
```

- **`weighing/scale_selection.py`** (new, pure):
  - `ScaleClass` enum with `scale_id`, `label`, `unit`:
    - `PRECISION` → `scale-3kg`, "3 kg precision", `g`;
    - `FLOOR` → `scale-32kg`, "32 kg floor", `kg`.
  - `ScaleAssignment` (frozen dataclass): `scale` (ScaleClass), `mode = "automatic"`.
  - `scale_threshold_kg() -> Decimal`: reads `settings.WEIGHING_SCALE_THRESHOLD_KG` **on every call**, so a changed setting applies the next time a component is asked for (story 002 AC 4) and tests can use `override_settings`.
  - `select_scale(target: Decimal, unit: str, threshold_kg: Decimal | None = None) -> ScaleAssignment`: target in kg (`tolerance.to_unit`); `≤ threshold → PRECISION`, `> threshold → FLOOR`.
- **`weighing/tolerance.py`** (new, pure):
  - `UNITS = ("g", "kg")`; `RESOLUTION = {"g": Decimal("0.1"), "kg": Decimal("0.001")}`.
  - `to_unit(amount, from_unit, to_unit) -> Decimal`: exact × / ÷ 1000 (Decision 1); unknown unit → `ValueError`.
  - `at_resolution(amount, unit) -> Decimal`: `quantize(RESOLUTION[unit], ROUND_HALF_UP)` (Decision 2).
  - `format_weight(amount, unit) -> str`: "94.0 g", "4.0 g", "24.000 kg" (FR-10b). Quantizes to the resolution first and never prints an exponent. Bolt 008's `batches.material.format_quantity` stays the **tare** format ("214 g"); the two are deliberately different.
  - `Zone` (str enum): `under`, `near`, `within`, `over`.
  - `ToleranceBand` (frozen dataclass): `target`, `tolerance`, `unit`; properties `low`, `high`, `near_from` (= target × 0.9, exact Decimal), `caption` → `"TOLERANCE ±0.5 g (93.5 – 94.5)"`. Built with `band_for(component)` from a `SnapshotComponent`.
  - `zone_of(band, net) -> Zone`: `net > high` → over; `net ≥ low` → within; `net ≥ near_from` → near; else under.
  - `WeightEvaluation` (frozen dataclass): `net`, `unit`, `zone`, `still_to_weigh` (= max(0, target − net)), `surplus` (net − target when over, else `None`), `within_tolerance`, `status_line`.
  - `evaluate(band, reading, reading_unit) -> WeightEvaluation`: converts the reading to the band's unit, takes it at resolution, then decides. Status lines:
    - under / near: `"DISPENSE — {still_to_weigh} REMAINING"`, e.g. "DISPENSE — 4.0 g REMAINING";
    - within: `"WITHIN TOLERANCE — PRESS OK TO CONFIRM"`;
    - over: `"OVER TOLERANCE — SURPLUS +{surplus}"`, e.g. "OVER TOLERANCE — SURPLUS +0.6 g".
  - Text values are built only with `format_weight`. Arithmetic is `Decimal` only; `float` never appears (NFR-16).
- **`weighing/rules.py`** (new, application layer):
  - `ComponentRules` (frozen dataclass): `component`, `assignment` (ScaleAssignment), `band` (ToleranceBand).
  - `component_rules(component) -> ComponentRules`: scale + band for one snapshot component.
  - `evaluate_reading(session_id, sequence, net: Decimal, unit: str) -> (ComponentRules, WeightEvaluation)`: loads the session and component with the **existing bolt 008 lookups** (`SESSION_NOT_FOUND`, `COMPONENT_NOT_FOUND`), then evaluates. **This is the function bolt 010's confirm calls** with the server's own scale re-read; it refuses unless `within_tolerance` (Decision 4).
- **`weighing/identity.py`** (extended): `ComponentView` gains `rules: ComponentRules`, so `session_components` returns header, identity **and** weighing rules in one pass.
- **`weighing/views.py` / `urls.py`** (extended): the evaluation view and the extra fields in `_component_json`.
- **Settings** (project settings module): `WEIGHING_SCALE_THRESHOLD_KG`, see Configuration.

### API Design

Under **`/station/api/`** (ADR-002), camelCase JSON, error shape `{"error": {"code", "message"}}`, as in bolts 005–008.

**1. `GET /station/api/sessions/<session_id>/components` (extended, bolt 008)**. Each component gains three blocks. Snapshot values keep their 4-place strings, as before; every value meant for display also has a text form, so the UI does no number formatting:

```json
{
  "sequence": 3,
  "code": "DYE-4471",
  "…": "bolt 008 fields unchanged",
  "target": "94.0000",
  "targetText": "94.0 g",
  "scale": {"scaleId": "scale-3kg", "label": "3 kg precision", "unit": "g", "mode": "automatic"},
  "tolerance": {
    "tolerance": "0.5000",
    "low": "93.5000",
    "high": "94.5000",
    "nearFrom": "84.6000",
    "caption": "TOLERANCE ±0.5 g (93.5 – 94.5)"
  }
}
```

Sodium Sulphate: `"targetText": "24.000 kg"`, `"scale": {"scaleId": "scale-32kg", "label": "32 kg floor", "unit": "kg", "mode": "automatic"}`.

`low`, `high` and `nearFrom` are there for the bar position only (bolt 011), not for deciding the zone.

**2. `GET /station/api/sessions/<session_id>/components/<sequence>/evaluation?net=93.4&unit=g` (new)**:
- A pure query: no state change, so `GET`, no CSRF token and no operator needed (like `GET …/components`).
- Parameters:
  - `net` (required): a plain decimal string as the scale client returns it, `^-?\d{1,6}(\.\d{1,6})?$`. Exponents, `NaN`, `Infinity`, commas and blanks are rejected. Negative is allowed, because a lifted container reads negative; it is `under`.
  - `unit` (required): `g` or `kg`. A reading in the other unit is converted (Decision 1).
- `200`:

```json
{
  "sessionId": 1,
  "sequence": 3,
  "net": "93.4",
  "unit": "g",
  "netText": "93.4 g",
  "zone": "near",
  "withinTolerance": false,
  "stillToWeigh": "0.6",
  "stillToWeighText": "0.6 g",
  "surplus": null,
  "surplusText": null,
  "statusLine": "DISPENSE — 0.6 g REMAINING"
}
```

  - Values are at display resolution (Decision 2): `net` is the value that was evaluated, e.g. `net=94.54` → `"94.5"`, `within`.
  - At 94.6 g: `"zone": "over"`, `"withinTolerance": false`, `"stillToWeigh": "0.0"`, `"surplus": "0.6"`, `"surplusText": "0.6 g"`, `"statusLine": "OVER TOLERANCE — SURPLUS +0.6 g"`.
- Errors:
  - `400 INVALID_REQUEST`: `net` or `unit` missing or invalid;
  - `404 SESSION_NOT_FOUND`, `404 COMPONENT_NOT_FOUND`;
  - `405` for any other method.

**How bolt 011 uses it:** on activating a component it reads `scale.scaleId` and polls that scale only. On each **changed** reading it calls the evaluation endpoint and paints readout, bar colour and status line from the answer. OK is enabled only when `withinTolerance` is true (and the bolt 010 preconditions hold). The server re-checks at confirm in any case.

### Data Model

**No change.** No new model, no migration. The rules read `target_qty`, `tolerance`, `unit` and `display_max` from `SnapshotComponent` (bolt 005). Nothing is stored. Bolt 010 stores scale, target, tolerance min/max and the evaluated weight on the weighing record.

### Configuration

- `WEIGHING_SCALE_THRESHOLD_KG` in the project settings:
  - value = `Decimal(os.environ.get("WEIGHING_SCALE_THRESHOLD_KG", "3"))`;
  - not a finite number > 0 → `ImproperlyConfigured` at startup, with the bad value in the message (fail safe; Decision 3);
  - changed by setting the environment variable before `npm run dev`; no code change (NFR-13).
- No other new settings. The resolution (0.1 g / 0.001 kg) and the 90 % "near" rule are fixed by the requirements and stay constants in `tolerance.py`.

### Security Design

- **No trust in the browser's verdict:** the browser only displays the server's evaluation. Bolt 010's confirm re-reads the scale on the server and evaluates again with the same function (FR-13b).
- **Read-only endpoint:** `GET`, no side effects, no data beyond the recipe values already shown on the station. CSRF does not apply.
- **Input validation:** a strict regex before `Decimal(...)`, so no `InvalidOperation`, no exponent tricks and no huge numbers reach the rules. `session_id` and `sequence` use `<int:…>` converters.
- **Fail safe configuration:** an invalid threshold stops startup instead of silently putting a heavy component on the precision scale.

### NFR Implementation

- **NFR-16 / Decimal:** values are built from strings; quantize with `ROUND_HALF_UP`; a test checks that the rule modules contain no `float(`.
- **NFR-13 / configuration:** threshold from settings + env, read on each call.
- **NFR-1 / responsiveness:** the evaluation is a single indexed lookup plus arithmetic on the local server. The browser calls it only when the reading changes, so a steady weight causes no extra calls.
- **NFR-10 / fidelity:** caption, status lines and number formats are the prototype's wording, with the em dash ("—") and the en dash ("–") as in the prototype.
- **NFR-11 / language:** operator-facing texts are kept together in `tolerance.py` (status lines, caption) and `scale_selection.py` (labels).

### Logging

No log lines for selection or evaluation: they are pure queries asked on every weight change, and logging them would flood the log. A refused evaluation (`404`) is logged at INFO through the existing bolt 008 refusal path. The decisions that matter (confirmation accepted or refused) are logged by bolt 010.

### Design choice for the checkpoint

**A. Where the browser gets the zone** - Recommended: **ask the server for each changed reading** (`GET …/evaluation`). There is one rule in one place; what the operator sees is exactly what confirm will decide. It costs one small local request per weight change. Alternative: send the band to the browser and repeat the zone rule in JavaScript. It has no extra requests, but two copies of a safety rule could drift apart (the Playwright tests would have to guard them).

### External Dependencies

- **`batches.models.SnapshotComponent`** (bolt 005): `target_qty`, `tolerance`, `unit`, `display_max` (read-only).
- **`weighing.identity`** (bolt 008): session/component lookup and `session_components`.
- **Dummy Scale** (training contract): only its scale IDs `scale-3kg` / `scale-32kg` and their units (g / kg, bolt 002 Decision 1). No HTTP call is made by this bolt.
- **Consumers:**
  - bolt 010: `evaluate_reading` at confirm, `component_rules` for the record's scale and tolerance min/max;
  - bolt 011: the extended `GET …/components` and the evaluation endpoint.

### ADR Candidates (Stage 3)

1. **The server is the single source of the weighing rules; the browser asks it to evaluate each changed reading** (choice A). It shapes bolts 010 and 011 and differs from a common "client computes, server re-checks" approach.
2. **One value at display resolution** (Decision 2): a reading is rounded half up once to 0.1 g / 0.001 kg and that value is shown, evaluated and recorded. This is a safety-relevant rounding rule.

The threshold setting (Decision 3) follows directly from NFR-13 and needs no ADR.

### Files (planned for the Implement stage)

- **New**:
  - `src/weighing/scale_selection.py`;
  - `src/weighing/tolerance.py`;
  - `src/weighing/rules.py`.
- **Modified**:
  - the project settings module: `WEIGHING_SCALE_THRESHOLD_KG` with env override and validation;
  - `src/weighing/identity.py`: `ComponentView.rules`;
  - `src/weighing/views.py`, `src/weighing/urls.py`: the extended component JSON and the evaluation endpoint.
- **New tests (Test stage)**:
  - `tests/weighing/test_scale_selection.py`: 3 kg / 3.0001 kg, 3000 g / 3000.1 g, the five seed components, a changed threshold (`override_settings`), labels and "automatic", invalid threshold → `ImproperlyConfigured`;
  - `tests/weighing/test_tolerance.py`: the five boundary weights (zone and verdict), below 90 % → under, caption, still to weigh at 0.0 / 90.0 / 94.0 / 95.0, status lines, surplus, conversion g ↔ kg, rounding at resolution (94.54 → 94.5, 94.55 → 94.6), "24.000 kg" / "94.0 g", Sodium Sulphate band 23.880 – 24.120 kg, no `float(` in the modules;
  - `tests/weighing/test_rules_api.py`: the extended component JSON for Yellow RGB and Sodium Sulphate, the evaluation endpoint for the five weights, validation (`400`), `404`, `405`.
  - Playwright for "OK disabled at 93.4 / 94.6" is in bolt 011, which builds the weigh screen.
- **Unchanged**: the adapters, the JS clients, the station UI, the `batches` app and all `dummy_*` apps.
