---
bolt: 006-weighing-station
created: 2026-11-20T09:20:12Z
status: accepted
superseded_by: null
---

# ADR-005: The current operator is held in the server-side Django session; weighing actions read it only from there

## Context

The operator must be chosen before any batch is weighed (story 001 AC 1), shown in the header on every view (AC 2), and every weighing action without one must be refused (AC 3, FR-19a).

The STEP 12 architecture has the browser call the Dummy APIs directly, while the WeighingMS server stays the authority (ADR-001). Later actions (tare, confirm, override, completion) must all record *who* acted (FR-19b). The current operator must survive a page reload, because a batch has to resume after a reload (NFR-6, story 010). The station is a single station (NFR-3).

## Decision

1. Choosing an operator (`PUT /station/api/operator`) stores the operator ID in the **server-side Django session**, under the key `weighing.operator_id`. Clearing it (`DELETE`) removes it, and `GET` returns it, or `null`.
2. Every weighing action resolves the operator **only from the session**, through the single guard `require_operator()`:
   - an operator ID in a request body is ignored;
   - with no operator → `403 OPERATOR_REQUIRED`, and nothing is stored;
   - the guard re-reads the operator row, so an operator who is no longer active counts as no operator.
3. A WeighingSession stores the operator who started it, and it never changes. Later records store the operator returned by `require_operator()` at the time of the action.

## Rationale

- Keeping "who is acting" on the server stops the browser, whether through a bug or a crafted request, from attributing a weighing to someone else. This applies ADR-001's "server is the authority" to identity.
- One guard means every later bolt gets the AC 3 refusal by calling one function, not by re-implementing a check.
- The Django session cookie survives a reload with no extra work, which NFR-6 relies on.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| A single database row "station operator" | Survives a server restart; same for every browser | Any browser opening the app acts as that operator; a global mutable row | Weaker attribution; the session already covers reload |
| Operator ID sent by the browser on each request (localStorage) | Stateless server | The client decides who acted; easy to forge or desync | Violates server authority (ADR-001) |
| `contrib.auth` login session | Standard | Needs `User` rows and passwords | Rejected by ADR-004 |

## Consequences

### Positive

- Attribution is decided on the server for every action. The AC 3 refusal is uniform and testable.
- The header and the operator choice (bolt 007) use one small contract: `GET`, `PUT` or `DELETE /operator`.

### Negative

- Every write endpoint needs the session and its cookie, so the tests use Django's test client (which keeps cookies), and Playwright works through the real browser.
- If the session expires or the cookies are cleared, the operator has to choose again. An open weighing session stays intact.

### Risks

- **The sessions app or middleware isn't enabled.** Mitigation: the Implement stage verifies `django.contrib.sessions` and `SessionMiddleware`; the tests cover choose → header → start.
- **Two browsers on the same station could hold different operators.** Mitigation: one station terminal is the intended setup (NFR-3), and each session records its own operator, so attribution stays correct.

## Related

- **Stories**: 005-weighing-station/001-identify-operator; later 006-confirm-weighing, 007-handle-overshoot, 009-complete-batch, 010-resume-after-reload; 007-assisted-weighing-station-ui (header, operator choice)
- **Standards**: none
- **Previous ADRs**: ADR-001 (server authority), ADR-002 (`/station/api/`), ADR-004 (seeded identities)
