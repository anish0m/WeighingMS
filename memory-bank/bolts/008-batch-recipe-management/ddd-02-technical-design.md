---
stage: design
bolt: 008-batch-recipe-management
created: 2026-11-23T03:54:07Z
---

## Technical Design: batch-recipe-management (material identity)

This design is based on the approved domain model (`ddd-01-domain-model.md`, APPROVE MODEL 2026-11-23T03:54:07Z) and its five recommended decisions:
1. `MaterialReadinessPolicy` is tested here and must be called by bolt 010's confirm;
2. the server re-reads the scan by `scanId` through its scanner adapter;
3. the latest check counts;
4. a missing container is refused too;
5. every component needs an identity scan, auxiliaries included.

### Architecture Pattern

**Layered Django apps with a plain-Python service layer**, as in bolts 005 and 006 (coding standards: business rules in service modules, thin views). No new app.

The work is split by **what each part depends on**, so no import cycle appears between the apps (`weighing` already imports `batches`; `batches` must never import `weighing`):

- **`batches`** (unit 004, recipe snapshot) gets the parts that need only the snapshot:
  - `ComponentHeader` and its text form;
  - the lot and container checks (`LOT_MISSING`, `CONTAINER_MISSING`).
- **`weighing`** (WeighingSession aggregate, ADR candidate 1) gets the parts that need the session:
  - the `IdentityCheck` model (a member of the session aggregate, domain model);
  - `verify_identity` (needs the session, the operator and the scanner adapter);
  - `check_material_ready`, which combines the `batches` lot/container checks with the identity status. This is the function bolt 010's confirm calls.
- **Scanner:** `weighing` calls `devices.scanner.read_latest_scan()` (bolt 004). It knows no Dummy path and imports no `dummy_*` module (boundary tests).

Layering rules (unchanged): views → services → models; services never see a request; the current operator is passed in as a value read from the Django session (ADR-005).

### Layer Structure

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Presentation   weighing/views.py, weighing/urls.py                   │  2 new JSON endpoints
├──────────────────────────────────────────────────────────────────────┤
│ Application    weighing/identity.py                                  │  verify_identity, session_components,
│                                                                      │  check_material_ready
├──────────────────────────────────────────────────────────────────────┤
│ Domain         batches/material.py   ComponentHeader, format_tare,   │  pure rules on the snapshot
│                                      lot/container refusals          │
│                weighing/identity.py  IdentityResult, IdentityStatus, │
│                                      MaterialRefusal codes, events   │
├──────────────────────────────────────────────────────────────────────┤
│ Infrastructure weighing/models.py    IdentityCheck (ORM = repository)│  SQLite
│                devices/scanner.py    read_latest_scan (existing)     │  Dummy Scanner (training contract)
└──────────────────────────────────────────────────────────────────────┘
```

- **`batches/material.py`** (new, pure Python, no database writes):
  - `format_tare(amount: Decimal, unit) -> str`:
    - `g`: no decimals when the value is whole (`214.0000` → `214 g`); otherwise trailing zeros are removed (`214.5000` → `214.5 g`);
    - `kg`: three decimals (`1.8500` → `1.850 kg`);
    - Decimal operations only (`quantize`, `normalize`); never `float`.
  - `ComponentHeader` (frozen dataclass: `name`, `code`, `lot`, `container`, `tare`, `unit`) with `text` →
    `"Remazol Yellow RGB · DYE-4471 · LOT 2026-0387 · CONTAINER C-12 · TARE 214 g"`. A blank lot or container is written as `—`.
  - `header_for(component: SnapshotComponent) -> ComponentHeader`.
  - `MaterialFault` enum (value = message): `LOT_MISSING` "Lot missing for this component", `CONTAINER_MISSING` "Container missing for this component".
  - `material_faults(component) -> list[MaterialFault]`: lot first, then container. Blank or whitespace-only counts as missing.
- **`weighing/models.py`** (extended):
  - `IdentityResult` (TextChoices `verified` / `wrong_dyestuff`).
  - `IdentityCheck` (below). `save()` refuses an update of an existing row and `delete()` is refused, like `WeighingSession` (append-only, invariant 4).
- **`weighing/identity.py`** (new, the identity services; keeps `services.py` from growing):
  - `IdentityStatus` (`unverified` / `verified` / `wrong_dyestuff`).
  - New `RefusalReason` members in `weighing/services.py` (value = message, `.code` = name, as before):
    - `SESSION_NOT_FOUND` "Weighing session not found" (the view already returns this code; it becomes a reason);
    - `COMPONENT_NOT_FOUND` "Component not found";
    - `NOT_A_DYESTUFF_SCAN` "Scan a dyestuff code";
    - `SCAN_NOT_CURRENT` "Scan again";
    - `SCANNER_UNAVAILABLE` "Scanner unavailable";
    - `IDENTITY_NOT_VERIFIED` "Scan the dyestuff first";
    - `WRONG_DYESTUFF` "Wrong dyestuff";
    - `LOT_MISSING`, `CONTAINER_MISSING`, with the `MaterialFault` messages.
  - `verify_identity(session_id, sequence, scan_id, operator_id) -> (IdentityCheck, created: bool)`, in one `transaction.atomic()`:
    1. `require_operator(operator_id, action="verify identity")`;
    2. load the session, or `SESSION_NOT_FOUND`; find the snapshot component by `sequence`, or `COMPONENT_NOT_FOUND`;
    3. if `(session, scan_id)` is already recorded → return it with `created=False`. **It is not re-checked against the requested sequence**: a scan belongs to the component it was first checked for;
    4. `read_latest_scan()`: `ScannerUnavailable` → `SCANNER_UNAVAILABLE`; `None` or `scan.scan_id != scan_id` → `SCAN_NOT_CURRENT`; `scan.kind == "batch"` → `NOT_A_DYESTUFF_SCAN`;
    5. `result = verified if scan.code.strip() == component.code.strip() else wrong_dyestuff`; save; log the event; return with `created=True`.
    Every refusal raises `WeighingRefused` and stores nothing.
  - `identity_status(session, sequence) -> (IdentityStatus, IdentityCheck | None)`: the latest check by `checked_at`, then `id` (Decision 3).
  - `check_material_ready(session, sequence) -> None` or raise `WeighingRefused`. Order: `LOT_MISSING`, `CONTAINER_MISSING`, `IDENTITY_NOT_VERIFIED`, `WRONG_DYESTUFF`. **The contract for bolt 010:** confirm calls this before it records anything.
  - `session_components(session_id) -> list[ComponentView]`: for each snapshot component in sequence, the header plus identity status and readiness. Read-only.
- **`weighing/views.py`** (extended): the two views below; refusal → HTTP mapping extends `REFUSAL_STATUS`.

### API Design

Both endpoints are under **`/station/api/`** (ADR-002), camelCase JSON, error shape `{"error": {"code", "message"}}`. Quantities are decimal strings with 4 places, as in bolt 005; the formatted text is given separately so the UI does no number formatting.

- **`GET /station/api/sessions/<session_id>/components`**:
  - `200` `{"sessionId": 1, "batchId": "B-24187", "components": [Component JSON, …]}`, in recipe sequence.
  - `404 SESSION_NOT_FOUND`.
  - Read-only, so no operator is required (the header and rail are shown to anyone at the station, as `GET /sessions/<id>` is).
- **`POST /station/api/sessions/<session_id>/components/<sequence>/identity`**:
  - Request `{"scanId": 17}`. Only the scan ID; the code is never taken from the browser (Decision 2). The operator comes from the server session.
  - `201` IdentityCheck JSON: a new check. This includes **`wrong_dyestuff`**: it is a recorded result, not a failed request. The body's `message` is "Wrong dyestuff" and the UI shows it.
  - `200` IdentityCheck JSON: this scan was already recorded for the session (idempotent re-send).
  - Errors:
    - `400 INVALID_REQUEST`: the body is not a JSON object; `scanId` is missing or not a positive integer (a boolean is rejected);
    - `403 OPERATOR_REQUIRED`;
    - `404 SESSION_NOT_FOUND`, `404 COMPONENT_NOT_FOUND`;
    - `409 NOT_A_DYESTUFF_SCAN`, `409 SCAN_NOT_CURRENT`: understood, but the scan can't be used;
    - `503 SCANNER_UNAVAILABLE`;
    - `405` any other method.

**Component JSON**:

```json
{
  "sequence": 3,
  "code": "DYE-4471",
  "name": "Remazol Yellow RGB",
  "lot": "2026-0387",
  "container": "C-12",
  "tare": "214.0000",
  "unit": "g",
  "tareText": "214 g",
  "header": "Remazol Yellow RGB · DYE-4471 · LOT 2026-0387 · CONTAINER C-12 · TARE 214 g",
  "identity": {"status": "verified", "scannedCode": "DYE-4471", "checkedAt": "2026-11-23T04:10:00Z"},
  "materialReady": true,
  "materialRefusal": null
}
```

- `identity` is `{"status": "unverified", "scannedCode": null, "checkedAt": null}` when there is no check.
- `materialRefusal` is `{"code": "IDENTITY_NOT_VERIFIED", "message": "Scan the dyestuff first"}` (or the first fault in the order above) when `materialReady` is false.
- Target, tolerance and scale are **not** added here; they are bolt 009 (no duplicated responsibility).

**IdentityCheck JSON**:

```json
{
  "checkId": 4,
  "sessionId": 1,
  "sequence": 3,
  "scanId": 17,
  "expectedCode": "DYE-4471",
  "scannedCode": "DYE-4472",
  "result": "wrong_dyestuff",
  "message": "Wrong dyestuff",
  "operator": {"operatorId": "OP-01", "name": "R. Karim", "shift": "A", "display": "R. Karim · Shift A"},
  "checkedAt": "2026-11-23T04:09:30Z"
}
```

`message` is "Dyestuff verified" for `verified`.

### Data Model

Migration `weighing/0003_identitycheck` (schema only, no data). Timestamps are timezone-aware UTC.

- **`weighing_identitycheck`**:
  - Columns:
    - `id` (auto PK, the `checkId`);
    - `session` (FK → `WeighingSession`, `PROTECT`, `related_name="identity_checks"`);
    - `component_sequence` (positive small integer);
    - `expected_code` (char 32), copied from the snapshot component;
    - `scan_id` (positive integer), the Dummy Scanner's `scanId`;
    - `scanned_code` (char 64), the scanner's code;
    - `result` (char 16, choices);
    - `operator` (FK → `Operator`, `PROTECT`);
    - `checked_at` (default now).
  - Constraint: `UniqueConstraint(fields=("session", "scan_id"), name="one_check_per_scan_per_session")` (invariant 3).
  - Index: `(session, component_sequence, checked_at)` for "latest check for this component".
  - Invariants 1 and 2 (the sequence exists, the expected code equals the snapshot's) are enforced by `verify_identity`, the only writer.
- **No change** to `batches` tables: lot, container and tare already exist on `SnapshotComponent` (bolt 005).

### Security Design

- **The scanned code is never taken from the client** (Decision 2). The browser sends only a `scanId`; the server reads the code from the scanner and accepts it only if that scan is the scanner's latest. A forged request can at most re-submit a real, current scan.
- **Attributable:** every check stores the operator from the server session (ADR-005); no operator → `403`, nothing stored.
- **Append-only:** checks can't be updated or deleted (model guards, `PROTECT` FKs); not registered in the admin.
- **CSRF** stays on the `POST` (bolt 007 sends `X-CSRFToken`).
- **Input validation** at the view boundary: `session_id` and `sequence` come from `<int:…>` URL converters; `scanId` is a positive integer.
- **Fail safe (FR-20):** scanner unavailable → `503`, nothing stored, identity status unchanged, confirmation still blocked.

### NFR Implementation

- **FR-4 / BR-10:** confirmation can only pass `check_material_ready` with a matching, latest scan.
- **FR-5c / FR-6b:** missing lot or container → refused before confirmation (bolt 010 copies lot and container onto the record).
- **NFR-16 (Decimal):** tare stays `Decimal` from the snapshot to `format_tare`; JSON carries strings.
- **NFR-6 (resume) groundwork:** checks are stored, so after a reload `GET …/components` shows the same identity status.
- **NFR-7 (failure visible):** `SCANNER_UNAVAILABLE` has its own code and message.
- **Performance:** a few rows per session; one scanner read per verify (the adapter's timeout bounds it).

### Logging (IR-09, coding standards)

Logger `weighing.identity`:

- `INFO` "DyestuffVerified": session, batch, sequence, code, scan ID, operator ID.
- `WARNING` "WrongDyestuffScanned": session, batch, sequence, expected code, scanned code, scan ID, operator ID.
- `INFO` "IdentityCheckRefused": session, sequence, reason code (via the existing "WeighingActionRefused" path where it applies).

### External Dependencies

- **`devices.scanner`** (bolt 004): `read_latest_scan()` → `Scan(scan_id, kind, code, scanned_at)` or `None`; raises `ScannerUnavailable`. Reads the **Dummy Scanner** training contract (`GET /api/scanner/scans/latest`).
- **`batches.models`** (bolt 005): `BatchSelection`, `SnapshotComponent` (read-only).
- **`weighing.services`** (bolt 006): `require_operator`, `RefusalReason`, `WeighingRefused`.
- **UI (bolt 011)**, the consumer: the "Scan dyestuff" step watches scans with `scanner-client.js`; on a new `dyestuff` scan it `POST`s `{scanId}` for the active component and shows `message`. The header line is `header` from `GET …/components`.
- **Bolt 010**, the consumer: confirm calls `check_material_ready` first.

### ADR Candidates (Stage 3)

1. **Identity checks are stored in the `weighing` app, as members of the WeighingSession aggregate, although stories 004/005 belong to unit 004.** `batches` keeps only snapshot-based rules, so the dependency stays one-way (`weighing` → `batches`).
2. **Server-side re-read of the scan by `scanId`** instead of trusting a browser-supplied code. This differs from batch selection (bolt 007 posts the batch code), so it is worth recording why.

### Files (planned for the Implement stage)

- **New**:
  - `src/batches/material.py`;
  - `src/weighing/identity.py`;
  - `src/weighing/migrations/0003_identitycheck.py`.
- **Modified**:
  - `src/weighing/models.py`: `IdentityResult`, `IdentityCheck`;
  - `src/weighing/services.py`: the new `RefusalReason` members;
  - `src/weighing/views.py`, `src/weighing/urls.py`: the two endpoints and their status mapping.
- **New tests (Test stage)**:
  - `tests/batches/test_material.py`: tare formatting (214 g, 1.850 kg, non-whole grams), header text for Yellow RGB and Sodium Sulphate, blank lot/container → faults and `—`;
  - `tests/weighing/test_identity_check.py`: match, mismatch, latest check counts, same scan twice, batch scan, stale scan, no scan, scanner unavailable (Dummy toggle), no operator, unknown component, append-only, `check_material_ready` order (lot, container, unverified, wrong);
  - `tests/weighing/test_identity_api.py`: both endpoints, status codes, validation, CSRF, `405`.
  - The architecture boundary tests cover the new modules automatically.
- **Unchanged**: the adapters, the JS clients, the station UI, and all `dummy_*` apps.
