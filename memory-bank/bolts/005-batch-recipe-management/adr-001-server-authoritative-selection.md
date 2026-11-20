---
bolt: 005-batch-recipe-management
created: 2026-11-20T08:47:02Z
status: accepted
superseded_by: null
---

# ADR-001: Server-authoritative batch selection; the browser reads the Dummy for display

## Context

The user's STEP 12 decision (system-context, Clarification 2026-11-20T05:15:14Z) has the browser call the Dummy APIs directly through one JS client per integration, because workbook STEP 19, 21, 26 and 27 expect the browser's Network tab to show calls such as `GET /api/batches` and `GET /api/batches/B-24187/recipe`. The same decision keeps the WeighingMS server as the authority: it snapshots the selected recipe, re-reads the scale before a confirmation and stores all records.

Bolt 005 is the first bolt where both runtimes touch the same data. Which runtime decides that a batch is open, and which copy of the recipe later weighing uses, has to be fixed now, because bolts 007, 009, 010 and 011 build on it.

Forces: FR-21 (the UI gets data only from the Dummy APIs over HTTP); C-01 and DR-03 (recipes are read-only, a local copy is never authoritative); FR-2 and FR-3d ("nothing opens" on a refusal or retrieval failure); NFR-7 (a failure is never shown as success); NFR-2 (recipe shown ≤ 3 s).

## Decision

1. The **browser displays** the queue and the recipe from the Dummy OrgaTEX through `orgatex-client.js`.
2. On touch or scan, the browser posts `{batchId, method}` to the WeighingMS select endpoint. The **server re-reads** the batch and recipe through its Python OrgaTEX adapter, applies the selection rules and, only if all succeed, stores an immutable recipe snapshot (`BatchSelection`).
3. The browser opens the weigh view **only on the server's `201`**. On a refusal it shows the server's reason and stays on the queue.
4. Weighing (unit 005) works against the **server snapshot**, never against data the browser sends.

## Rationale

- The selection result must be decided where it can be trusted and recorded: browser state can be stale, tampered with or lost on reload, while the server snapshot outlives the page and feeds the weighing records.
- The browser's direct read satisfies FR-21 and produces the Network evidence the workbook asks for.
- Both reads go to the same Dummy, so in normal operation they agree; if they ever disagree (OrgaTEX changed the batch in between), the server's fresh read wins, which is what DR-03 asks for.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Browser-only selection (no server call) | One read; simplest | No authoritative snapshot; weighing would trust browser data; nothing to resume from | Contradicts STEP 12 ("server stays the authority") and C-01 |
| Server-only (server proxies queue and recipe to the UI) | One source; one read | Network tab shows WeighingMS calls, not `GET /api/batches…`; the UI does not get data "from the Dummy APIs" | Contradicts STEP 12 and the workbook's STEP 19 evidence |
| Browser posts the recipe it read; server stores it | One OrgaTEX read | Server would store client-supplied recipe data as truth | Breaks C-01 / DR-03 trust; no server-side validation against OrgaTEX |

## Consequences

### Positive

- One authoritative, immutable recipe per selection for all later weighing, records and resume.
- The Network tab shows the Dummy calls the workbook expects.
- Selection rules (not found, not released, recipe not available, OrgaTEX unavailable) live in one Python service and are tested with Django tests.

### Negative

- Each selection reads OrgaTEX twice (browser and server).
- The UI must handle a server refusal even after its own read succeeded (e.g. OrgaTEX failed in between).

### Risks

- **The browser's displayed recipe and the server snapshot differ** (OrgaTEX changed in between). Mitigation: the weigh view (bolt 011) renders from the selection response, i.e. the server snapshot; the browser's recipe read is for the selection screen and evidence only.
- **Slow OrgaTEX makes selection exceed 3 s.** Mitigation: adapter timeout ends in `503 ORGATEX_UNAVAILABLE`, never in a late success; a timing test guards the normal path.

## Related

- **Stories**: 004-batch-recipe-management/001-view-batch-queue, 002-select-batch, 003-load-read-only-recipe; later 007 UI stories and 005-weighing-station/010-resume-after-reload
- **Standards**: candidate for `system-architecture.md` (runtime split per integration) if that standard is created
- **Previous ADRs**: none
