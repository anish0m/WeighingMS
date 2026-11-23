---
bolt: 015-weighing-station
created: 2026-11-23T10:35:24Z
status: accepted
superseded_by: null
---

# ADR-014: Batch history is a read-only API over the stored records: every record of the batch from all its sessions, at `/station/api/batch-history/<batch_id>`, with no reporting

## Context

Story 011 (FR-19 b/c, brief FR-29, BR-19, AC-07) requires that all weighing records of a batch can be retrieved with target, actual, operator, scale, lot, container, tare and timestamp, so Lab/QA can tell a bad recipe from a bad weighing.

The brief's FR-29 also asks for retrieval "by batch, date, operator or dyestuff". OQ-2, however, decided "no further reporting": no reports, no dashboards, no supervisor remote view.

The prototype has no history screen.

Two more constraints:
- ADR-002 keeps WeighingMS paths under `/station/api/`, free of Dummy path segments (`/batches` belongs to Dummy OrgaTEX);
- a batch can have more than one weighing session, because B-24187 stays in the Dummy queue (IR-06 not built, ADR-013).

## Decision

1. **`GET /station/api/batch-history/<batch_id>`** returns `{batchId, records}`.
   - The records are every `WeighingRecord` of the batch, from **all** its sessions, ordered by component sequence, then record time.
   - Each one uses the existing record JSON (bolt 010), which includes the operator's ID, name and shift, plus `sessionId`.
2. **It is a query, not a resource:** an unknown batch, or one with no records, gives 200 with an empty list.
3. **Read-only, with no operator needed** (Lab/QA reads it). Other methods → 405.
4. **No filters, paging, export or UI page.** Retrieval is by batch only (OQ-2).

## Rationale

- **The records already hold every traceability field** (bolt 010, ADR-010), so the history is one query and adds no new storage.
- **All sessions:** an investigation must see everything weighed for the batch. `sessionId` on each record tells the runs apart.
- **`batch-history`, not `batches`:** it keeps the integration-boundary test meaningful (only the OrgaTEX adapter and client know `/batches`).
- **API only:** this meets story 011 and AC-07 without building the reporting that OQ-2 excludes.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Only the completed session's records | Exactly one record per component | Hides earlier runs of the same batch from an investigation | Lab/QA needs every weighing |
| `/station/api/batches/<id>/records` | Reads naturally | Contains the Dummy segment `/batches`; breaks ADR-002 and the boundary test | ADR-002 |
| Filters by date / operator / dyestuff (brief FR-29) | Closer to the brief | Reporting scope that OQ-2 excludes | OQ-2 |
| 404 for an unknown batch | Signals a typo | WeighingMS does not own the batch list; "no records" is a valid answer | It is a query over records |

## Consequences

### Positive

- Story 011 is met with one read-only endpoint and no schema change.
- Bolt 016 (ticket) can reuse the same read for the ticket lines.

### Negative

- No browsing UI: Lab/QA uses the API (or the Django test client, or `curl`).
- Brief FR-29's other retrieval keys are not provided (OQ-2).

### Risks

- **Large batch histories later.** Mitigation: training volume is five records per run; paging can be added when a real need appears.

## Related

- **Stories**: 005-weighing-station/011-retrieve-batch-history
- **Requirements**: FR-19 (b, c), OQ-2; brief FR-29, BR-19, AC-07
- **Previous ADRs**: ADR-002 (station API namespace), ADR-010 (records), ADR-013 (a batch can be weighed again)
