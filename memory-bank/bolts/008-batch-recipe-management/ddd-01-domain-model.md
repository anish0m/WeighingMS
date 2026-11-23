---
stage: model
bolt: 008-batch-recipe-management
created: 2026-11-23T03:52:11Z
---

## Static Model: batch-recipe-management (material identity)

### Bounded Context

**Batch & Recipe**, material-identity part. Bolt 005 decided *which* batch is weighed and stored its read-only recipe snapshot (ADR-003). This bolt decides **whether the material in front of the operator is the right one, and from which lot and container it comes**:

- the dyestuff identity check (FR-4, OQ-8, brief FR-09 / BR-10 / IR-15);
- the lot, container and tare of each component (FR-5, FR-6, OQ-7, brief FR-10 / BR-11).

- **Owned here**:
  - the **IdentityCheck**: the result of scanning a material code against a component;
  - the **ComponentHeader**: the line "name · code · LOT · CONTAINER · TARE" built from the snapshot;
  - the **material readiness rule**: "may this component be confirmed, as far as material identity is concerned?"
- **Not owned here**:
  - lot, container and tare *values*. They come from the Dummy OrgaTEX seed per component (OQ-7) and are already stored in `SnapshotComponent` by bolt 005. The operator never enters them;
  - which component is *active*, confirmation itself, weighing records, applying the tare to the reading (unit 005: bolts 009, 010);
  - reading the scanner over HTTP (unit 003 scanner adapter, the anti-corruption layer);
  - the "Scan dyestuff" step on the screen (unit 007, bolt 011).
- **Training contract:** scans come from the **Dummy Scanner** (`scanId`, `kind` `batch`/`dyestuff`, `code`, `scannedAt`), not from a real scanner interface. A-10 stays open.
- **Runtime split (STEP 12 decision, bolt 004 plan):** the browser watches the scanner and shows the result, but the **server checks scanned codes**. The server re-reads the scan through its own scanner adapter (Decision 2), just as it re-reads the scale before a confirmation.

### Entities

- **IdentityCheck** (entity, identity `check_id`): `session` (WeighingSession, by id), `component_sequence`, `expected_code` (MaterialCode), `scan_id`, `scanned_code` (MaterialCode), `result` (IdentityResult), `operator` (OperatorRef), `checked_at`.
  - Belongs to one WeighingSession and one component of that session's recipe snapshot.
  - `expected_code` is copied from the snapshot component, never from the browser.
  - `scanned_code` is the code the **scanner** reported for `scan_id`, never a typed or browser-supplied code.
  - `result` = `verified` if `scanned_code` equals `expected_code` exactly (after trimming), else `wrong_dyestuff`.
  - Recorded for **every** scan, including wrong ones, so mismatches stay traceable (BR-10).
  - Needs an identified operator (FR-19a, bolt 006 `require_operator`).
  - Immutable once recorded; never updated or deleted.
  - A scan (`scan_id`) is used at most once per session. Re-submitting the same scan does not create a second check; it returns the first one.
- **SnapshotComponent** (existing, bolt 005, read-only): already carries `lot`, `container`, `tare` (Quantity). No new fields. This bolt only *reads* them.

### Value Objects

- **MaterialCode** (existing): `value` (e.g. `DYE-4471`, `AUX-0101`). Compared exactly, case-sensitive, after trimming.
- **IdentityResult** (enumeration): `verified` | `wrong_dyestuff`.
- **IdentityStatus** (derived, per session component): `unverified` | `verified` | `wrong_dyestuff`. It is the result of the **latest** IdentityCheck for that component, or `unverified` if there is none (Decision 3).
- **LotId**: `value` (e.g. `2026-0387`). Non-empty after trimming, otherwise "missing".
- **ContainerId**: `value` (e.g. `C-12`, `D-03`). Non-empty after trimming, otherwise "missing".
- **Quantity** (existing): `amount` (Decimal), `unit` (`g` | `kg`). Tare uses it.
- **ComponentHeader**: `name`, `code`, `lot`, `container`, `tare` (Quantity). Text form:
  `"{name} · {code} · LOT {lot} · CONTAINER {container} · TARE {tare}"`.
  - The tare is written in the component's unit: grams without decimals when whole (`214 g`), kilograms with three decimals (`1.850 kg`). Decimal only, no float.
  - Yellow RGB → "Remazol Yellow RGB · DYE-4471 · LOT 2026-0387 · CONTAINER C-12 · TARE 214 g" (story 005 AC 1).
  - Sodium Sulphate → "… · CONTAINER D-03 · TARE 1.850 kg" (story 005 AC 3).
  - A missing lot or container is shown as "—", never invented.
- **MaterialRefusal** (RefusalReason enumeration), with the message shown to the operator:
  - `WRONG_DYESTUFF` → "Wrong dyestuff". The latest scan for this component did not match (story 004 AC 2).
  - `IDENTITY_NOT_VERIFIED` → "Scan the dyestuff first". No scan yet for this component (story 004 AC 3).
  - `LOT_MISSING` → "Lot missing for this component". The snapshot has no lot (story 005 AC 2, FR-5c).
  - `CONTAINER_MISSING` → "Container missing for this component". The snapshot has no container (Decision 4).
  - `NOT_A_DYESTUFF_SCAN` → "Scan a dyestuff code". The scan's kind is `batch`; nothing is recorded.
  - `SCAN_NOT_CURRENT` → "Scan again". The scan the browser named is no longer the scanner's latest scan, or the scanner has no scan; nothing is recorded.
  - `SCANNER_UNAVAILABLE` → "Scanner unavailable". The server could not read the scanner; nothing is recorded (fail safe, FR-20).
  - `COMPONENT_NOT_FOUND` → "Component not found". The sequence is not in the session's recipe.
  - Reused from bolt 006: `OPERATOR_REQUIRED`.

### Aggregates

- **WeighingSession** (root, unit 005, bolt 006): IdentityChecks become **members** of the session, because identity only means something for this batch's run and this component. Invariants added by this bolt:
  1. An IdentityCheck's `component_sequence` exists in the session's recipe snapshot.
  2. `expected_code` equals that snapshot component's code.
  3. Each `scan_id` is recorded at most once per session.
  4. Checks are append-only.
- **BatchSelection** (root, bolt 005): unchanged and immutable. The ComponentHeader is a read model derived from it.

### Domain Events

Recorded as log entries (no event bus in this build):

- **DyestuffVerified**: Trigger: a scan matched the component code - Payload: `session_id`, `batch_id`, `component_sequence`, `code`, `scan_id`, `operator_id`, `checked_at`.
- **WrongDyestuffScanned**: Trigger: a scan did not match - Payload: `session_id`, `batch_id`, `component_sequence`, `expected_code`, `scanned_code`, `scan_id`, `operator_id`, `checked_at`.
- **IdentityCheckRefused**: Trigger: a scan could not be checked (not a dyestuff scan, not current, scanner unavailable, component not found, no operator) - Payload: `session_id`, `component_sequence`, `reason`, `at`.

### Domain Services

- **IdentityVerificationService**: Operations: `verify(session, component_sequence, scan_id) → IdentityCheck | MaterialRefusal` - Dependencies: scanner adapter (`read_latest_scan`), `require_operator` (bolt 006), IdentityCheckRepository. Steps:
  1. Require an operator; otherwise `OPERATOR_REQUIRED`.
  2. Find the component in the session's snapshot; otherwise `COMPONENT_NOT_FOUND`.
  3. If `scan_id` is already recorded for this session, return that check unchanged.
  4. Read the latest scan through the scanner adapter. Unavailable → `SCANNER_UNAVAILABLE`; no scan, or a different `scan_id` → `SCAN_NOT_CURRENT`; kind `batch` → `NOT_A_DYESTUFF_SCAN`.
  5. Compare codes, record the IdentityCheck, emit DyestuffVerified or WrongDyestuffScanned.
  A `wrong_dyestuff` result is a recorded outcome, not an error: the operator sees "Wrong dyestuff".
- **MaterialReadinessPolicy**: Operations: `check(session, component_sequence) → ok | MaterialRefusal` - Dependencies: IdentityCheckRepository, the snapshot (pure rule otherwise). Order of checks: `LOT_MISSING`, `CONTAINER_MISSING`, then the identity status (`unverified` → `IDENTITY_NOT_VERIFIED`, `wrong_dyestuff` → `WRONG_DYESTUFF`). Unit 005's confirmation (bolt 010) **must** call it and refuse on any refusal (Decision 1).
- **ComponentHeaderBuilder**: Operations: `build(snapshot_component) → ComponentHeader` - Dependencies: none.

### Repository Interfaces

- **IdentityCheckRepository**: Entity: IdentityCheck - Methods:
  - `add(check)`;
  - `for_scan(session_id, scan_id) → IdentityCheck | None`;
  - `latest_for(session_id, component_sequence) → IdentityCheck | None`;
  - `all_for(session_id) → IdentityCheck[]`, for the session view and resume (bolt 010);
  - no `update` or `delete`.
- **BatchSelectionRepository** (existing): read-only use, to reach the snapshot component.

### Ubiquitous Language

- **Dyestuff scan**: scanning the barcode on the dyestuff (or auxiliary) container with the station scanner.
- **Identity check**: comparing that scanned code with the active component's code.
- **Verified**: the latest scan for the component matched its code.
- **Wrong dyestuff**: the latest scan for the component did not match. Confirmation stays blocked.
- **Lot**: the production lot of the material being consumed (e.g. 2026-0387). It comes from OrgaTEX and is kept on the record.
- **Container**: the physical container the material is weighed into (e.g. C-12, D-03). It comes from OrgaTEX and is kept on the record.
- **Tare**: the container's empty weight (e.g. 214 g, 1.850 kg). Shown here; applied to the reading in unit 005.
- **Component header**: the line under the component name on the weigh screen with code, lot, container and tare.
- **Material readiness**: lot present, container present and identity verified. All three are needed before a component may be confirmed.

### Story Coverage

- **004-verify-dyestuff-identity**:
  - AC 1 (DYE-4471 scanned for Yellow RGB → verified): IdentityVerificationService, IdentityCheck `verified`, DyestuffVerified.
  - AC 2 (another code → "Wrong dyestuff", confirmation blocked): IdentityCheck `wrong_dyestuff`, WrongDyestuffScanned, MaterialReadinessPolicy → `WRONG_DYESTUFF`.
  - AC 3 (not verified → confirmation refused): MaterialReadinessPolicy → `IDENTITY_NOT_VERIFIED`.
- **005-show-lot-and-container**:
  - AC 1 (Yellow RGB header): ComponentHeader text form.
  - AC 2 (no lot → confirmation refused): MaterialReadinessPolicy → `LOT_MISSING`.
  - AC 3 (Sodium Sulphate: D-03, 1.850 kg): ComponentHeader, kg with three decimals.

### Decisions for the Human Checkpoint

1. **"Confirmation is refused" before confirmation exists** - Recommended: **this bolt provides `MaterialReadinessPolicy` and tests it directly; bolt 010's confirm calls it** and turns every refusal into a refused confirmation. The story ACs are tested here at the policy level, and again end-to-end in bolt 010. Alternative: move both "refused" ACs to bolt 010 (this would leave stories 004 and 005 incomplete when this bolt closes).
2. **Who reads the scanned code** - Recommended: **the server reads it.** The browser sees a new dyestuff scan and asks the server to verify *that* `scanId`. The server re-reads the latest scan through its scanner adapter and compares the scanner's code, so a typed or forged code can never verify (bolt 004 plan: "the scanner adapter checks scanned codes"). Alternative: the browser posts the code it received, as batch selection does in bolt 007 (simpler, but the server then trusts the browser for a safety check).
3. **A wrong scan after a correct one** - Recommended: **the latest check counts.** A wrong scan after a verified one blocks confirmation again until the right code is scanned (fail safe: the operator may have swapped containers). Alternative: once verified, it stays verified for the component.
4. **Missing container** - Recommended: **refuse confirmation with `CONTAINER_MISSING` too**, because FR-6b requires every record to store the container ID. The stories only name the lot, so this is the one rule beyond the ACs. Alternative: refuse only a missing lot, as the story ACs state, and leave the container to bolt 010.
5. **Auxiliaries (Sodium Sulphate, Soda Ash)** - Recommended: **every component needs an identity scan**, auxiliaries included (codes `AUX-…`, scanned as kind `dyestuff` in the training contract). FR-4 is "component identification", and the header shows a code for every component. Alternative: scan only `DYE-…` components (needs a rule on how to tell them apart, which the brief does not give).
