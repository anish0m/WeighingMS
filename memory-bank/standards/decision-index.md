---
last_updated: 2026-11-23T04:01:39Z
total_decisions: 7
---

# Decision Index

This index tracks all Architecture Decision Records (ADRs) created during Construction bolts.
Use this to find relevant prior decisions when working on related features.

## How to Use

**For Agents**: Scan the "Read when" fields below to identify decisions relevant to your current task. Before implementing new features, check if existing ADRs constrain or guide your approach. Load the full ADR for matching entries.

**For Humans**: Browse decisions chronologically or search for keywords. Each entry links to the full ADR with complete context, alternatives considered, and consequences.

---

## Decisions

<!-- Entries are appended below in reverse chronological order (newest first) -->

### ADR-007: Identity checks are stored in the `weighing` app as part of the WeighingSession; snapshot-only material rules stay in `batches`
- **Status**: accepted
- **Date**: 2026-11-23
- **Bolt**: 008-batch-recipe-management (batch-recipe-management)
- **Path**: `bolts/008-batch-recipe-management/adr-007-identity-checks-in-weighing-session.md`
- **Summary**: Stories 004 and 005 belong to unit 004 (`batches`), but an identity check only has meaning for one weighing run, which lives in `weighing`. `batches/material.py` keeps the stateless snapshot rules (tare format, header, lot/container faults), `weighing` stores `IdentityCheck` and provides `check_material_ready`, and the dependency stays one-way (`weighing` → `batches`).
- **Read when**: Implementing confirmation (bolt 010 must call `check_material_ready`), building the weigh view's component header or scan step, adding state that belongs to a weighing run, or deciding which app a new model goes in.

### ADR-006: The server verifies the dyestuff scan by re-reading it by `scanId`; a code sent by the browser is never trusted
- **Status**: accepted
- **Date**: 2026-11-23
- **Bolt**: 008-batch-recipe-management (batch-recipe-management)
- **Path**: `bolts/008-batch-recipe-management/adr-006-server-verifies-dyestuff-scan.md`
- **Summary**: Before a component can be confirmed, the dyestuff must be verified by scanning its barcode against the component's code (FR-4, OQ-8, brief FR-09 / BR-10). The browser sends only the `scanId`; the server reads the scanner's latest scan through its adapter, uses it only if the IDs match, and records the comparison with the snapshot code as an append-only `IdentityCheck`.
- **Read when**: Working on the dyestuff scan step, any scanner-driven action, confirmation preconditions, or any endpoint where the browser could supply a value that proves something (codes, weights).

### ADR-005: The current operator is held in the server-side Django session; weighing actions read it only from there
- **Status**: accepted
- **Date**: 2026-11-20
- **Bolt**: 006-weighing-station (weighing-station)
- **Path**: `bolts/006-weighing-station/adr-005-current-operator-in-server-session.md`
- **Summary**: The operator must be chosen before any batch is weighed (story 001 AC 1), shown in the header on every view (AC 2), and every weighing action without one must be refused (AC 3, FR-19a). Choosing an operator (`PUT /station/api/operator`) stores the operator ID in the server-side Django session, and every weighing action resolves the operator only from there through `require_operator()`.
- **Read when**: Adding any weighing action (tare, confirm, override, completion), storing who performed an action, building the header or operator choice in the UI, or working on resume after reload.

### ADR-004: Station identities are seeded Operator / Supervisor entities, not `django.contrib.auth` users
- **Status**: accepted
- **Date**: 2026-11-20
- **Bolt**: 006-weighing-station (weighing-station)
- **Path**: `bolts/006-weighing-station/adr-004-seeded-station-identities.md`
- **Summary**: Every weighing must be attributable to an operator, and a supervisor must authenticate to authorise an override, using the approved training method in OQ-3. The `weighing` app owns two seed-only entities, `Operator` and `Supervisor`, which are not Django `User` rows, and the supervisor PIN is stored only as a Django password hash.
- **Read when**: Working on operator or supervisor identity, the supervisor override (bolt 012), PIN handling, seed data, or any proposal to introduce `django.contrib.auth` users or a login.

### ADR-003: The recipe snapshot is an immutable local cache, enforced in the models
- **Status**: accepted
- **Date**: 2026-11-20
- **Bolt**: 005-batch-recipe-management (batch-recipe-management)
- **Path**: `bolts/005-batch-recipe-management/adr-003-immutable-recipe-snapshot.md`
- **Summary**: WeighingMS needs a local copy of the selected batch's recipe for weighing, records and resume, while recipes stay owned by OrgaTEX (C-01, DR-03). Each selection stores its own snapshot, the models refuse updates and deletes, and every selection reads OrgaTEX fresh.
- **Read when**: Storing or reading recipe/component data, weighing records that reference targets or tolerances, resume after reload, or any code that might change OrgaTEX-owned data.

### ADR-002: WeighingMS's own API lives under `/station/api/`, separate from the Dummy contracts under `/api/`
- **Status**: accepted
- **Date**: 2026-11-20
- **Bolt**: 005-batch-recipe-management (batch-recipe-management)
- **Path**: `bolts/005-batch-recipe-management/adr-002-station-api-namespace.md`
- **Summary**: Bolt 005 adds the first WeighingMS-owned JSON endpoint while all existing endpoints are Dummy training contracts under `/api/`. All WeighingMS-owned JSON endpoints are mounted under `/station/api/`, and their paths never contain a Dummy path segment.
- **Read when**: Adding any WeighingMS URL or JSON endpoint (weighing, confirm, records, write-back or print results), or changing the integration boundary test.

### ADR-001: Server-authoritative batch selection; the browser reads the Dummy for display
- **Status**: accepted
- **Date**: 2026-11-20
- **Bolt**: 005-batch-recipe-management (batch-recipe-management)
- **Path**: `bolts/005-batch-recipe-management/adr-001-server-authoritative-selection.md`
- **Summary**: The STEP 12 decision has the browser call the Dummy APIs directly while the server stays the authority. The browser displays queue and recipe from the Dummy, but a batch opens only when the server has re-read it through its adapter and stored the snapshot, which weighing then uses.
- **Read when**: Building UI flows that read Dummy data and then act on it (batch selection, weigh view, confirm, write-back, print), or deciding which runtime owns a piece of state.
