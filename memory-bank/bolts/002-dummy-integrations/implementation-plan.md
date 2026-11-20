---
stage: plan
bolt: 002-dummy-integrations
created: 2026-11-20T06:44:05Z
---

## Implementation Plan: dummy-integrations

### Objective

Complete the Dummy layer: the Dummy Scale API (read, tare, training simulate controls), the Dummy Scanner and Dummy Printer, and a training failure toggle for every Dummy. These are training contracts defined by this project, **not** the real scale, scanner, printer or OrgaTEX interfaces (A-01…A-15 stay unresolved).

### Stories

- **005-dummy-scale-api**: DB-5, DB-6, DB-7 (supports FR-7, FR-8, FR-9, FR-12, FR-14)
- **006-dummy-scanner-and-printer**: DB-8, DB-9 (supports FR-2, FR-4, FR-18)
- **007-dummy-failure-toggles**: DB-4, DB-7, DB-8, DB-9 (supports FR-1c, FR-3d, FR-17d, FR-20)

### Deliverables

**`src/dummy_scale/`** (models exist from bolt 001)
- `services.py`: read, tare, simulate (dispense / overshoot / reset / set), mode switch; Decimal only
- `views.py`, `urls.py`: contract endpoints and training endpoints
- `models.py`: status choices extended with `disconnected`; migration `0002`

**`src/dummy_scanner/`** (new app)
- `models.py`: `DummyScan` (kind `batch`/`dyestuff`, code, scanned_at), `DummyScannerState` (mode `ok`/`unavailable`)
- `services.py`, `views.py`, `urls.py`, migration `0001`

**`src/dummy_printer/`** (new app)
- `models.py`: `DummyTicket` (content, batch_id, printed_at), `DummyPrinterState` (mode `ok`/`error`)
- `services.py`, `views.py`, `urls.py`, migration `0001`

**`src/dummy_orgatex/`** (extend bolt 001)
- `models.py`: `DummyOrgatexState` (mode `ok`/`unavailable`); migration `0002`
- `views.py`: every OrgaTEX endpoint returns `503 ORGATEX_UNAVAILABLE` while unavailable
- `services.py`: seeding also resets the scanner, printer and OrgaTEX mode (all `ok`, no scans, no tickets)
- `seed_data.py`: scale units (see Decision 1)

**`src/weighingms/`**: register the two new apps; mount their URLs under `/api/`

**Tests** in `tests/dummy_scale/`, `tests/dummy_scanner/`, `tests/dummy_printer/`, `tests/dummy_orgatex/`

### API contract (training contract; camelCase JSON, quantities as decimal strings, errors `{"error": {"code", "message"}}`)

Contract endpoints (what WeighingMS and the browser use):
- `GET /api/scales` → `{"scales": [{scaleId, name, capacity, unit, status}]}`
- `GET /api/scales/:scaleId/status` → `{scaleId, status}` (`ready` / `disconnected`), 200 in both cases
- `GET /api/scales/:scaleId/weight` → `{scaleId, netWeight, unit, status, readAt}`; disconnected → `503 SCALE_DISCONNECTED`, no weight
- `POST /api/scales/:scaleId/tare` → net weight 0, returns the reading; disconnected → 503
- `GET /api/scanner/status` → `{status}` (`ready` / `unavailable`)
- `GET /api/scanner/scans/latest` → `{scan: {scanId, kind, code, scannedAt} | null}`; unavailable → `503 SCANNER_UNAVAILABLE`
- `GET /api/printer/status` → `{status}` (`ready` / `error`)
- `POST /api/tickets` body `{content, batchId?}` → `201 {ticketId, content, batchId, printedAt}`; printer error → `503 PRINTER_ERROR`, nothing stored; empty content → 400
- `GET /api/tickets/:ticketId` → the stored ticket; unknown → 404 `TICKET_NOT_FOUND`
- Unknown scale anywhere → 404 `SCALE_NOT_FOUND`

Training-only endpoints, all under `/api/training/` so they are clearly separate from the contract (used by tests and the training panel, story 007-ui/008):
- `POST /api/training/scales/:scaleId/simulate` body:
  - `{action: "dispense", target, tolerance, unit}` → weight = target + 0.4·tolerance (94.0 ± 0.5 → 94.2)
  - `{action: "overshoot", target, tolerance, unit}` → target + 4.8·tolerance (→ 96.4)
  - `{action: "reset"}` → 0
  - `{action: "set", weight, unit}` → exact weight (e.g. 93.4)
  - `unit` must equal the scale's unit (no conversion); values must be decimal strings; disconnected → 503
- `POST /api/training/scanner/scans` body `{kind, code}` → 201 stored scan; unavailable → 503, nothing stored
- `GET /api/training/modes` and `PUT /api/training/modes/:target` body `{mode}`:
  - `orgatex`: `ok` / `unavailable`
  - `scale-3kg`, `scale-32kg`: `ok` / `disconnected`
  - `scanner`: `ok` / `unavailable`
  - `printer`: `ok` / `error`
  - invalid target or mode → 400; `GET /api/training/modes` lists all current modes

Each mode is stored in its own Dummy app (DB-10). The `/api/training/modes` view lives in `src/weighingms/training.py` and only dispatches to each Dummy app's `get_mode` / `set_mode` service; there is no shared table.

### Dependencies

- Bolt 001 (complete): `dummy_scale` model, `seed_training`, Dummy OrgaTEX endpoints
- No new packages

### Technical Approach

- Same pattern as bolt 001: thin views → `services.py` → domain exceptions mapped to HTTP errors.
- Simulate formulas follow the prototype buttons ("Simulate dispense" = target + 0.4·tol, "Simulate overshoot" = target + 4.8·tol), computed in `Decimal`.
- Endpoints that change state are CSRF-exempt (the browser calls the Dummies directly, STEP 12 decision).
- `seed_training` remains the single reset: batches, recipe, scales (ready, 0), all modes `ok`, scans and tickets cleared.

### Decisions for the user

1. **Scale units.** Bolt 001 seeded both scales in `kg`. The stories expect the 3 kg scale to read `94.2 g`, as in the prototype (precision-scale components are in g, floor-scale components in kg). **Recommended:** `scale-3kg` reports in `g` (capacity `3000` g), `scale-32kg` stays in `kg` (capacity `32` kg). This changes one seed value and one bolt-001 test (capacity 3 kg → 3000 g). Alternative: keep both in kg and send `0.0942` kg for Yellow RGB, which the UI would convert.
2. **Scanner and printer status endpoints** (`GET /api/scanner/status`, `GET /api/printer/status`) are added so the status bar (FR-20, bolt 004) has a source. They are small and read-only.

### Acceptance Criteria

- [ ] `GET /api/scales` lists `scale-3kg` (precision) and `scale-32kg` (floor)
- [ ] weight/status return net weight (decimal string), unit and `ready`/`disconnected`
- [ ] tare sets net weight to 0
- [ ] For 94.0 g ± 0.5 g: dispense → 94.2, overshoot → 96.4, reset → 0.0, set 93.4 → 93.4 (g)
- [ ] A submitted batch or dyestuff scan is returned as the latest scan
- [ ] `POST /api/tickets` stores the ticket and returns an ID; `GET /api/tickets/:id` returns the same content
- [ ] OrgaTEX unavailable → every OrgaTEX endpoint 503; scale disconnected → status `disconnected`, no weight; scanner unavailable / printer error → error and nothing stored
- [ ] Switching any Dummy back to `ok` resumes normal responses
- [ ] `npm test` (bolt 001's 31 tests + new ones) and `npm run lint` pass

### Test Plan

Django test runner (`npm test`):
- `tests/dummy_scale/test_scale_api.py`: list, status, weight, tare, unknown scale 404, string quantities
- `tests/dummy_scale/test_simulate.py`: dispense 94.2, overshoot 96.4, reset 0, set 93.4/93.5/94.0/94.5/94.6, kg case (Sodium Sulphate 24.000 ± 0.120 → 24.048), unit mismatch 400, float value 400
- `tests/dummy_scanner/test_scanner_api.py`: batch scan and dyestuff scan become the latest, no scan → `null`, invalid kind 400
- `tests/dummy_printer/test_printer_api.py`: store + read back, unknown ticket 404, empty content 400
- `tests/training/test_modes.py`: each toggle on → failure response and nothing stored; off → normal; invalid target/mode 400; `seed_training` resets all modes to `ok`

Manual (STEP 16 evidence): `npm run dev`, then `curl -s http://localhost:8000/api/scales | jq`.

### Out of scope for this bolt

- WeighingMS-side clients and adapters (bolts 003, 004), device status aggregation and fail-safe (bolt 004)
- Ticket content and layout (bolt 016); the training panel UI (bolt 011)
- Any tolerance or scale-selection rule (bolts 009+)
