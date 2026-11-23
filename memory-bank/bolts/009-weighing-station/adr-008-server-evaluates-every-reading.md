---
bolt: 009-weighing-station
created: 2026-11-23T04:51:03Z
status: accepted
superseded_by: null
---

# ADR-008: The server is the single source of the weighing rules; the browser asks it to evaluate each changed reading

## Context

The weigh screen shows a live readout that changes several times a second (NFR-1). For every reading the operator needs:
- the zone (under / near / within / over);
- how much is still to weigh;
- the status line;
- whether OK may be pressed.

The tolerance rule is a safety control. An out-of-tolerance weighing must never reach production (BO-01, FR-12, FR-13b). The rule must be refused server-side, "not only by the disabled button".

In the STEP 12 architecture, the browser polls the Dummy Scale directly (`GET /api/scales/<scaleId>/weight`, training contract), and the WeighingMS server is the authority (ADR-001). It re-reads the scale before a confirmation (bolt 004). This raises a question: who decides the zone that the operator *sees* while dispensing?

A common pattern is "the client computes, the server re-checks": the band is sent to the browser and a JavaScript copy of the rule paints the screen. That pattern means two implementations of the same safety rule, in two languages. JavaScript numbers are binary floats, and the rule must be Decimal (NFR-16).

## Decision

1. The weighing rules exist **once**, as pure Decimal functions in `weighing/scale_selection.py`, `weighing/tolerance.py` and `weighing/rules.py`.
2. `GET /station/api/sessions/<id>/components` gives the browser, per component:
   - the selected scale (`scaleId`, label, unit, `mode: "automatic"`);
   - the target and its text;
   - the band (`low`, `high`, `nearFrom`) and the caption.
   The band values are for **drawing the bar only**.
3. For each **changed** reading, the browser calls `GET /station/api/sessions/<id>/components/<seq>/evaluation?net=…&unit=…`. It paints the readout colour, the bar colour, still to weigh and the status line from the answer. OK is enabled only when `withinTolerance` is true and bolt 010's preconditions hold.
4. The browser contains **no zone or tolerance logic**.
5. At confirm (bolt 010), the server re-reads the scale itself and calls the same `evaluate_reading`. It refuses unless the result is within tolerance.

## Rationale

- One rule in one place: what the operator sees is exactly what confirm will decide. The five boundary weights (93.4 / 93.5 / 94.0 / 94.5 / 94.6 g) are proven once, in Django tests, in Decimal.
- No float arithmetic in the browser for a tolerance decision.
- The cost is small: the server is local to the station, the request is a single lookup plus arithmetic, and it is made only when the reading changes.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Band sent to the browser; JS computes the zone; server re-checks at confirm | No extra requests; instant colour change | Two copies of a safety rule in two languages; JS floats; drift is caught only by end-to-end tests | The rule must be single and Decimal |
| The server polls the scale and pushes evaluations (SSE / WebSocket) | Browser does nothing but display | New push channel and background polling per session; STEP 12 put the scale polling in the browser | More infrastructure than the station needs; contradicts the STEP 12 decision |
| Server evaluates only at confirm; screen shows the raw weight only | Simplest | No zone colours, no status line, no "near" warning: the prototype and FR-12 require them | Fails FR-12 and NFR-10 |

## Consequences

### Positive

- Zone, status line and OK state on screen always agree with the server's confirm decision.
- Bolt 011's UI stays thin: it displays server answers.
- Changing a rule (e.g. the overshoot handling decided at STEP 24) changes one module.

### Negative

- One extra local request per changed reading. In the Network tab, `…/evaluation` calls appear next to the scale polling.
- The screen colour lags the readout by one local round trip.

### Risks

- **The server is slow or unreachable, so the zone doesn't update.** Mitigation: the UI keeps OK disabled until a fresh evaluation for the current reading says `withinTolerance`. Confirm re-checks on the server anyway, so a stale screen can never record a weighing.
- **Too many requests while the weight changes fast.** Mitigation: evaluate only changed readings, and at most one request in flight (the latest reading wins). This is a bolt 011 implementation rule.

## Related

- **Stories**: 005-weighing-station/002-select-scale-automatically, 004-target-and-remaining, 005-evaluate-inclusive-tolerance; later 006-confirm-weighing (bolt 010), 007-assisted-weighing-station-ui/004-weigh-view-live-readout-and-tolerance (bolt 011)
- **Standards**: coding-standards (business rules in services; Decimal only)
- **Previous ADRs**: ADR-001 (server authority), ADR-002 (`/station/api/`), ADR-003 (snapshot supplies target and tolerance), ADR-007 (material gate, combined with this verdict at confirm); ADR-009 (the value that is evaluated)
