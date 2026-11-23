---
bolt: 009-weighing-station
created: 2026-11-23T04:51:03Z
status: accepted
superseded_by: null
---

# ADR-009: A reading is taken once at display resolution; that one value is shown, evaluated and recorded

## Context

The weigh screen shows weights with **1 decimal in g and 3 decimals in kg** (FR-10b): "94.0 g", "24.000 kg". The tolerance band is inclusive: Yellow RGB 94.0 ± 0.5 g accepts 93.5–94.5 and refuses 93.4 and 94.6 (FR-12).

A scale reading can carry more digits than the screen shows. The Dummy Scale returns Decimal strings set by the trainer, and a real scale's resolution is open (A-05). If the display rounds but the rule does not, the operator can see a value that contradicts the verdict:
- 94.54 g would be shown as "94.5 g" (inside the band) but judged as over, with OK disabled;
- 93.46 g would be shown as "93.5 g" but judged as near.

A reading can also arrive in another unit than the component. This happens when a component in g is above the threshold and lands on `scale-32kg`, which reports kg (model Decision 1).

## Decision

1. A reading is first converted **exactly** to the component's unit (× / ÷ 1000 in Decimal).
2. It is then rounded **once**, half up, to the display resolution: **0.1 g** or **0.001 kg** (`tolerance.at_resolution`).
3. That single value is the weight used everywhere:
   - **shown** ("Weighed now", `netText`);
   - **evaluated** (zone, still to weigh, surplus, within tolerance);
   - **recorded** as `actualWeight` by bolt 010's confirm.
4. The resolution and the rounding mode are constants in `weighing/tolerance.py`, not settings. They follow from FR-10b, and changing them must be a reviewed code change.

Examples (Yellow RGB 94.0 ± 0.5 g):
- 94.54 → 94.5 → within;
- 94.55 → 94.6 → over;
- 93.45 → 93.5 → within;
- 93.44 → 93.4 → near.

## Rationale

- What the operator sees, what is judged and what is stored are the same number. A record can always be explained from the screen.
- The display resolution is the precision the station claims to weigh with. Rounding to it is how a weighing indicator presents a weight.
- Round half up is the convention operators expect from a readout. The boundary cases are fixed by tests.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Evaluate the raw reading; round only for display | No rounding in the rule | Screen and verdict can disagree (94.54 shows "94.5 g", OK disabled); the stored value differs from the shown one | Confusing and not explainable from the screen |
| Refuse readings with more digits than the resolution | Never rounds | A real scale with finer resolution could never confirm; the operator can't fix it | Blocks normal operation |
| Round half to even (banker's rounding) | Common in finance | 94.55 → 94.6 but 94.45 → 94.4: surprising on a weighing display | Not what operators expect |
| Truncate (round down) | Never over-reports | 94.59 shows "94.5 g" and is accepted although it is 0.09 g over the band | Accepts real over-tolerance weights |

## Consequences

### Positive

- No screen / verdict / record mismatch at the band edges.
- One function (`at_resolution`) defines the weight for bolts 009, 010 and 011.

### Negative

- A reading up to half a display step outside the band can count as within (e.g. 94.54 g). This is inherent to the display resolution the requirements fix.

### Risks

- **A real scale with a coarser or finer resolution (A-05).** Mitigation: the resolution is one constant per unit; changing it is a reviewed change with the boundary tests updated.
- **Bolt 010 records the raw reading instead of the evaluated value.** Mitigation: bolt 010 takes `actualWeight` from the `WeightEvaluation`, and its tests check that the record equals the evaluated value.

## Related

- **Stories**: 005-weighing-station/004-target-and-remaining, 005-evaluate-inclusive-tolerance; later 006-confirm-weighing (bolt 010)
- **Standards**: coding-standards (Decimal from strings, never float)
- **Previous ADRs**: ADR-008 (the server evaluates every reading)
