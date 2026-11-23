---
stage: design
bolt: 012-weighing-station
created: 2026-11-23T08:54:03Z
---

## Technical Design: weighing-station (overshoot)

This design is based on the approved domain model (`ddd-01-domain-model.md`, APPROVE MODEL 2026-11-23T08:54:03Z), its six recommended decisions, and the STEP 24 training rule (OQ-4):
1. the surplus % is a percentage of the target;
2. the server re-reads the scale at Quit;
3. if the scale cannot be read, Quit ends as a plain `quit`;
4. the discard is stored on the ComponentAttempt;
5. a fixed OvershootRule in code;
6. no new logging for recovery (a).

### Architecture Pattern

**Same layered Django app and plain-Python service layer as bolts 006–010.** No new app and no new endpoint.

- **One new domain module, `weighing/overshoot.py`:** the fixed `OVERSHOOT_RULE` and the `Surplus` value. It is pure and `Decimal` only (ADR-008).
- **Existing code is extended, not copied:**
  - `tolerance.evaluate` gains the surplus percentage;
  - `progression.quit` gains the server re-read;
  - the evaluation and quit JSON gain the overshoot fields.
- **Scale I/O only through `devices.scale.read_weight`, outside the transaction** (ADR-011). The transaction re-checks the open attempt under the session lock before writing.
- **Deliberately absent:** no recalculation code, no override endpoint, no supervisor authentication path, and no write to any target, tolerance or snapshot field.

### Layer Structure

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Presentation   weighing/views.py   evaluation JSON + "overshoot";    │  no new URL
│                                    quit JSON + "ended"; refusal      │
│                                    detail + surplus                  │
├──────────────────────────────────────────────────────────────────────┤
│ Application    weighing/progression.py  quit(): re-read → discard    │
│                weighing/confirmation.py refusal detail + surplus     │
├──────────────────────────────────────────────────────────────────────┤
│ Domain         weighing/overshoot.py (new)  OVERSHOOT_RULE, Surplus  │  pure, Decimal
│                weighing/tolerance.py        evaluate(): percent      │
├──────────────────────────────────────────────────────────────────────┤
│ Infrastructure weighing/models.py  AttemptEnd + overshoot_discarded, │  migration 0005
│                                    end_net / end_surplus / end_unit  │
│                devices/scale.py    read_weight (existing)            │  Dummy Scale
└──────────────────────────────────────────────────────────────────────┘
```

- **`weighing/overshoot.py`** (new):
  - **`OvershootRule`** (frozen dataclass) and its single instance `OVERSHOOT_RULE`:
    - `confirm_allowed = False`;
    - `recalculation = "none"`;
    - `override_available = False`;
    - `override_reason = "Supervisor override is not available in this training build"`;
    - `recovery_text = "Remove material until the weight is back in the band, or press Quit (F4) to discard and re-weigh."`;
    - `decision = "OQ-4, workbook STEP 24, 2026-11-23"`.
  - **`Surplus`** (frozen dataclass):
    - `amount`: at display resolution, as bolt 009's `surplus`;
    - `percent` = `(amount / target * 100).quantize(Decimal("0.1"), ROUND_HALF_UP)`;
    - `unit`;
    - `heading` = `"Surplus +{amount_text} ({percent:+}%) — over tolerance"`, e.g. "Surplus +2.4 g (+2.6%) — over tolerance".
  - **`surplus_of(evaluation, band) -> Surplus | None`**: returns a value only when the zone is `over`.
- **`weighing/tolerance.py`** (extended):
  - `WeightEvaluation` gains `surplus_percent` (Decimal or none) and `overshoot` (Surplus or none).
  - The zone, `surplus` and `status_line` are unchanged ("OVER TOLERANCE — SURPLUS +2.4 g").
- **`weighing/models.py`** (extended):
  - `AttemptEnd` gains `OVERSHOOT_DISCARDED = "overshoot_discarded"`. The value has 19 characters, so the `end_reason` field grows from 16 to 24 characters.
  - `ComponentAttempt` gains `end_net`, `end_surplus` (Decimal 12,4, null) and `end_unit` (char 2, blank).
  - The append-only guard allows these three only **together with** `ended_at` / `end_reason`, and only once.
  - `end(reason, discard=None)` writes them.
- **`weighing/progression.py`** (extended): `quit(session_id, sequence, operator_id)`:
  1. **Checks** (unchanged): operator; session open; the component is the active one.
  2. **Outside a transaction:**
     - `read_weight(attempt.scale_id)`;
     - on `ScaleDisconnected` / `ScaleUnavailable`: no discard (Decision 3);
     - otherwise `rules.evaluate_reading(component, net, unit)`.
  3. **In one transaction, session row locked:**
     - re-check that the attempt is still open (otherwise `COMPONENT_NOT_ACTIVE`);
     - zone `over` → `end(OVERSHOOT_DISCARDED, discard=(net, surplus, unit))`; otherwise `end(QUIT)`;
     - start the new **untared** attempt (unchanged).
  4. **Log:** `OvershootDiscarded` (payload as in the model), or the existing `AttemptQuit`.
  5. **Return** the `SessionProgress` plus `ended`, which describes how the old attempt ended.
- **`weighing/confirmation.py`** (extended): the `OUT_OF_TOLERANCE` refusal `detail` gains `surplus`, `surplusPercent` and `surplusText` when the zone is `over`. The refusal itself is unchanged and stores nothing.
- **`weighing/views.py`** (extended): the serialisers below. No new URL.

### API Design

No new endpoint. Three existing responses gain fields; existing fields keep their names and meaning, so bolt 011's client keeps working.

**1. `GET /station/api/sessions/<id>/components/<seq>/evaluation?net=96.4&unit=g`** gains `surplusPercent` and `overshoot`.

Within, near or under → `"surplusPercent": null, "overshoot": null`. Over:

```json
{
  "zone": "over",
  "withinTolerance": false,
  "surplus": "2.4",
  "surplusText": "2.4 g",
  "surplusPercent": "2.6",
  "statusLine": "OVER TOLERANCE — SURPLUS +2.4 g",
  "overshoot": {
    "heading": "Surplus +2.4 g (+2.6%) — over tolerance",
    "recovery": "Remove material until the weight is back in the band, or press Quit (F4) to discard and re-weigh.",
    "confirmAllowed": false,
    "recalculation": "none",
    "overrideAvailable": false,
    "overrideReason": "Supervisor override is not available in this training build"
  }
}
```

The other fields (`net`, `netText`, `stillToWeigh`, `bar`, …) are unchanged and are not shown above. At 94.6 g: `"surplus": "0.6"`, `"surplusPercent": "0.6"`, heading "Surplus +0.6 g (+0.6%) — over tolerance".

**2. `POST /station/api/sessions/<id>/components/<seq>/quit`** returns the Progress JSON (unchanged) plus `ended`:

```json
"ended": {"attemptId": 12, "reason": "overshoot_discarded", "net": "96.4", "surplus": "2.4", "unit": "g",
          "message": "Overshoot discarded (96.4 g). Empty the container and press Re-tare (F2)."}
```

For a normal quit, `"reason": "quit"`, `net` and `surplus` are `null`, and `message` = "Attempt abandoned. Empty the container and press Re-tare (F2)." Bolt 013 shows `message`. Other endpoints return Progress JSON without `ended`.

**3. `POST …/confirm` refused over tolerance** (unchanged `409 OUT_OF_TOLERANCE`) has a longer `detail`:
`{"net": "96.4", "unit": "g", "zone": "over", "surplus": "2.4", "surplusPercent": "2.6", "surplusText": "2.4 g"}`.

**Not added:** any `override`, `recalculate` or `targets` endpoint. A POST to such a path returns `404` from Django's URL resolver.

### Data Model

Migration `weighing/0005_componentattempt_overshoot_discard` (schema only):
- **`end_reason`:** max length 16 → 24; the choices gain `overshoot_discarded`.
- **New columns:** `end_net` (Decimal 12,4, null), `end_surplus` (Decimal 12,4, null), `end_unit` (char 2, default `""`).
- **CheckConstraint `discard_snapshot_only_on_overshoot_discard`:**
  - `end_reason = 'overshoot_discarded'` requires `end_net`, `end_surplus` and `end_unit` to be set;
  - any other end reason requires all three to be null or blank.
  This is model invariant 3, enforced in the database.
- **Existing rows:** unchanged; the new columns are null or blank. No data migration is needed.
- **No change** to `WeighingRecord`, `WeighingSession` or the snapshot tables. `WeighingResult` stays `within` only.

### Security Design

- **The browser can't create a discard or skip one.**
  - The quit body is still ignored.
  - The server's own re-read of the attempt's scale decides whether the zone is `over` (ADR-008).
  - The stored `end_net` is the evaluated server value at display resolution (ADR-009).
- **No path to confirm over tolerance.** Confirm is unchanged, and no override endpoint, flag or setting exists. `OVERSHOOT_RULE` is a frozen code constant, not an environment variable.
- **Targets are read-only here:** no code in this bolt writes `SnapshotComponent`, the attempt's target or a tolerance. A test compares every component's target and tolerance before and after the overshoot flows.
- **Attributable:** `OvershootDiscarded` carries the current operator (ADR-005). Quit still needs an operator (`403 OPERATOR_REQUIRED`) and CSRF.
- **Fail safe:**
  - A scale failure at Quit never blocks the Quit (FR-13e, Decision 3). It ends as `quit`, because no measured overshoot exists to store.
  - A race (attempt already ended or switched) → `409 COMPONENT_NOT_ACTIVE`, and nothing is written.

### NFR Implementation

- **NFR-4 / NFR-16:** `Decimal` throughout. The percentage is computed from Decimal amounts and the Decimal target, with ROUND_HALF_UP to 0.1. No float anywhere.
- **NFR-5:** the end of the attempt (with its snapshot) and the start of the new attempt are written in one transaction.
- **NFR-12:** the discard snapshot is written once; the attempt stays append-only; there is no delete.
- **Performance:** one extra scale read per Quit (a local Dummy call). It runs outside the transaction, so the SQLite write lock is not held during HTTP.

### External Dependencies

- **`devices.scale`:** `read_weight`, `ScaleDisconnected`, `ScaleUnavailable` (Dummy Scale training contract).
- **`weighing.rules.evaluate_reading` / `tolerance`** (bolt 009), and **`weighing.progression`** (bolt 010).
- **Consumer:** bolt 013 (UI) shows `overshoot.heading`, `overshoot.recovery`, `overrideReason` (with Supervisor override disabled) and the quit `ended.message`. It computes nothing itself.

### ADR Candidates (Stage 3)

1. **ADR-012: the training overshoot rule is fixed in code.** There is no recalculation and no override. An overshoot discard is stored on the attempt, decided by the server's re-read at Quit. This records the STEP 24 business decision (OQ-4) as an architecture constraint for bolts 013, 015 and 016:
   - no override result on records;
   - no adjusted targets in the write-back or on the ticket.
   It also explains how a future approved rule would change it.

### Files (planned for the Implement stage)

- **New**:
  - `src/weighing/overshoot.py`;
  - `src/weighing/migrations/0005_componentattempt_overshoot_discard.py`.
- **Modified**:
  - `src/weighing/tolerance.py`: surplus percent and the overshoot value;
  - `src/weighing/models.py`: `AttemptEnd`, the discard fields, the guard and the constraint;
  - `src/weighing/progression.py`: `quit` with the re-read, `ended`;
  - `src/weighing/confirmation.py`: the refusal detail;
  - `src/weighing/views.py`: the evaluation, quit and refusal JSON.
- **New tests (Test stage)**, against the live Dummy Scale with its training simulate controls:
  - `tests/weighing/test_overshoot.py`:
    - 96.4 g → "OVER TOLERANCE — SURPLUS +2.4 g", surplus 2.4, percent 2.6, heading, rule texts;
    - 94.6 g → +0.6 g (+0.6%);
    - kg: Sodium Sulphate 24.200 kg → +0.200 kg (+0.8%);
    - 94.5 / 94.0 / 93.4 g → no overshoot;
    - percent rounding (ROUND_HALF_UP);
    - Decimal types only.
  - `tests/weighing/test_overshoot_recovery.py`:
    - confirm refused at 96.4 g with the surplus detail and no record;
    - Quit at 96.4 g → `overshoot_discarded` with net, surplus and unit stored, no record, a new untared attempt, `ended.message`;
    - Quit at 94.0 g → plain `quit`;
    - Quit with the scale disconnected → plain `quit`, not blocked;
    - recovery (a): 96.4 g, then 94.0 g → confirm recorded with 94.0 g, `within`;
    - after a discard, Re-tare then 94.2 g → confirm;
    - every target and tolerance is unchanged after all flows;
    - discard fields immutable after the end;
    - the database constraint rejects a snapshot without `overshoot_discarded`;
    - no override or recalculate URL exists (`404`).
  - `tests/weighing/test_overshoot_api.py`: evaluation JSON `overshoot` / `surplusPercent` (null when not over); quit JSON `ended`; `409` refusal detail; `403` without an operator.
- **Unchanged**: the adapters, all JS and templates (bolt 013), `batches`, and all `dummy_*` apps.
