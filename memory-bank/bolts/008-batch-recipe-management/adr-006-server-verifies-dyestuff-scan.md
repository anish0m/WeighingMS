---
bolt: 008-batch-recipe-management
created: 2026-11-23T03:57:31Z
status: accepted
superseded_by: null
---

# ADR-006: The server verifies the dyestuff scan by re-reading it by `scanId`; a code sent by the browser is never trusted

## Context

Before a component can be confirmed, the dyestuff must be verified by scanning its barcode against the component's code (FR-4, OQ-8, brief FR-09 / BR-10). A wrong dyestuff must never be confirmed, so this check is a safety control.

In the STEP 12 architecture, the browser watches the Dummy Scanner directly through `scanner-client.js`, and the WeighingMS server stays the authority (ADR-001). The bolt 004 plan gave the server a scanner adapter precisely so that "the scanner adapter checks scanned codes".

Batch selection (ADR-001, bolt 007) works differently: the browser posts the batch code it scanned, and the server decides by re-reading OrgaTEX. That is safe for a selection, because a forged batch code can only open a real, released batch. For identity, a forged code would *be* the proof, so the same pattern would let any request mark a component verified.

## Decision

1. The browser sends only the **`scanId`** of a new dyestuff scan: `POST /station/api/sessions/<id>/components/<seq>/identity` with `{"scanId": …}`. A code in the body is ignored.
2. The server reads the scanner's **latest scan** through `devices.scanner.read_latest_scan()` and uses it only if its `scan_id` equals the requested `scanId`:
   - no scan or another scan → `409 SCAN_NOT_CURRENT`;
   - kind `batch` → `409 NOT_A_DYESTUFF_SCAN`;
   - scanner unavailable → `503 SCANNER_UNAVAILABLE`.
   In each of these cases nothing is stored.
3. The server compares the **scanner's** code with the **snapshot** component's code (exact match after trimming), and records an `IdentityCheck` with the expected code, scanned code, `scan_id`, result, operator (ADR-005) and time. A mismatch is recorded as `wrong_dyestuff`; it is a `201` result with "Wrong dyestuff", not a request error.
4. A `scan_id` is recorded at most once per session; re-sending it returns the first check (`200`).
5. The **latest** check of a component decides its identity status, and confirmation (bolt 010) is allowed only if that status is `verified` (`check_material_ready`).

## Rationale

- The code that verifies identity comes from the device, not from the client, so a bug or a crafted request cannot verify a dyestuff that was never scanned. A forged request can at most re-submit a real, current scan.
- "Latest scan only" stops an old scan from being reused for a later component or after the operator has picked up another container.
- It matches the rest of the architecture: the server also re-reads the scale before a confirmation, rather than trusting a weight from the browser.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| The browser posts the scanned code (as batch selection does) | Simplest; no scanner read on the server | The client supplies the proof of identity; a typo or crafted request can verify | A safety check must not trust the client |
| The server polls the scanner itself and verifies without a browser request | No browser involvement at all | A background poller per session; harder to tie a scan to the component on screen | More moving parts than the station needs |
| The browser posts the code and the server re-reads to compare both | Double check | Two sources for one fact; the browser's value adds nothing | The server read alone is sufficient |

## Consequences

### Positive

- Identity verification is decided entirely on the server and is attributable (operator, time, scan ID).
- Wrong scans are kept, so mismatches stay traceable (BR-10).
- The Dummy Scanner training controls can drive the Django tests end to end.

### Negative

- A verify call costs one scanner read; it fails with `503` if the scanner is down, even if the browser has just seen the scan.
- If a second scan happens between the browser seeing a scan and the server reading it, the first is refused with "Scan again".

### Risks

- **A busy scanner produces scans faster than the browser posts them.** Mitigation: the operator scans one container at a time; "Scan again" is shown and the operator rescans. The station has one scanner (NFR-3).
- **The Dummy Scanner contract differs from the real scanner (A-10, keyboard-wedge or serial).** Mitigation: only the adapter knows the contract; this decision depends only on "a scan has an ID, a kind and a code".

## Related

- **Stories**: 004-batch-recipe-management/004-verify-dyestuff-identity; later 005-weighing-station/006-confirm-weighing (bolt 010), 007-assisted-weighing-station-ui/003-weigh-view-recipe-rail-and-header (bolt 011)
- **Standards**: coding-standards (business rules in services)
- **Previous ADRs**: ADR-001 (server authority), ADR-002 (`/station/api/`), ADR-003 (snapshot is the expected code's source), ADR-005 (operator from the server session)
