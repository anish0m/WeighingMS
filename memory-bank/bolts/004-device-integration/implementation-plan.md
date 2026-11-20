---
stage: plan
bolt: 004-device-integration
created: 2026-11-20T08:21:09Z
---

## Implementation Plan: device-integration

### Objective

Build the WeighingMS side of the station's devices, following the STEP 12 decision. The browser talks to the Dummy Scale, Scanner and Printer directly, through **one JS client per device**. The server keeps its own **Python adapters** only where it must be the authority:
- the **scale adapter** re-reads the weight before a confirmation;
- the **scanner adapter** checks scanned codes.

Every failure fails safe and is visible (FR-20, NFR-7). The Dummies are **training contracts**, not the real scale, scanner or printer interfaces (A-05, A-10 stay open).

### Stories

- **001-read-live-scale-weight**: FR-9, NFR-1, IR-10
- **002-tare-command**: IR-12; supports FR-7
- **003-scanner-input**: IR-15; supports FR-2, FR-4, FR-20b
- **004-printer-adapter**: IR-16; supports FR-18, FR-20c
- **005-device-status-and-fail-safe**: FR-20a/d, NFR-7, IR-13, IR-18

### 1. What will change?

**New WeighingMS app `devices`** (unit 003). It has no models; all four adapters below are separate modules inside it, so each device stays replaceable on its own (IR-07).

**Server Python adapters**, built on the same pattern as the OrgaTEX adapter: frozen result types, `Decimal`, fail-safe exceptions, and WARNING logs with URL, status and device (IR-09).
- `devices/scale.py`:
  - `read_weight(scale_id)` → `ScaleReading(scale_id, net_weight: Decimal, unit, status, read_at)`
  - `read_status(scale_id)` → `"ready"` or `"disconnected"`
  - `tare(scale_id)` → the zeroed `ScaleReading`
  - On failure it raises one of:
    - `ScaleDisconnected`: the Dummy says `SCALE_DISCONNECTED`;
    - `ScaleUnavailable`: unreachable, timeout, unknown scale, or a malformed body.
  - It reads only the scale it is asked for (story 001 AC 3).
- `devices/scanner.py`:
  - `read_latest_scan()` → `Scan(scan_id, kind, code, scanned_at)` or `None`;
  - `read_new_scan(after_scan_id)` returns a scan only if it is newer, so each code is received **once** (story 003 AC 1);
  - raises `ScannerUnavailable`.
- **No Python printer adapter** (Decision 1). The browser prints, and the server only records the result it reports (STEP 12 decision, bolt 016).

**Browser JS clients** (classic scripts on `window.WeighingMS`, like `orgatex-client.js`):
- **`scale-client.js`:**
  - `readWeight(scaleId)`, `readStatus(scaleId)`, `tare(scaleId)`;
  - `watchWeight(scaleId, onReading, onFailure)` polls `GET /api/scales/:scaleId/weight` **every 200 ms** (5 Hz, NFR-1) without a page reload, and stops cleanly when the active scale changes;
  - weights stay decimal strings.
- **`scanner-client.js`:**
  - `readStatus()`;
  - `watchScans(onScan, onFailure)` polls `GET /api/scanner/scans/latest` and calls `onScan` once per new `scanId`. The scan that was already there when the page loaded is ignored.
- **`printer-client.js`:**
  - `readStatus()`;
  - `printTicket(content, batchId)` → `{ticketId, printedAt}`, or throws a `DeviceError` with kind `error` (`PRINTER_ERROR`).
- **`device-status.js`:**
  - polls the four status endpoints **every 1 s**, so a disconnection shows within 2 s (IR-13, FR-20a);
  - exposes `{scale3kg, scale32kg, scanner, printer}`, each with a state (`ready` / `disconnected` / `unavailable` / `error`) and a `since` time;
  - a failed or unreadable poll is **never** `ready` (FR-20d);
  - the status bar (bolt 007) binds to it.
- A shared `DeviceError` (kind and code) lives in `device-status.js`, which is loaded first.

**Settings** (NFR-13):
- `SCALE_BASE_URL` and `SCANNER_BASE_URL`, default `http://localhost:8000/api`;
- `DEVICE_TIMEOUT_SECONDS`, default `2`, kept below the 2 s detection target.

The JS poll intervals are named constants at the top of each client.

### 2. Which files will be created/modified?

**Created**
- `src/devices/__init__.py`, `src/devices/apps.py`
- `src/devices/http.py`: a small shared GET/POST helper for the device adapters (JSON load with floats rejected, `Decimal` fields, error-body mapping)
- `src/devices/scale.py`, `src/devices/scanner.py`
- `src/devices/static/devices/scale-client.js`, `scanner-client.js`, `printer-client.js`, `device-status.js`
- `tests/devices/__init__.py`, `tests/devices/test_scale_adapter.py`, `tests/devices/test_scanner_adapter.py`

**Modified**
- `src/weighingms/settings.py`: register `devices`; add the three settings
- `tests/architecture/test_integration_boundaries.py`: extend the "single adapter" checks to the device paths

There are no migrations, URLs or templates. The UI first loads these scripts in bolt 007; `orgatex/adapter.py` is not changed.

### 3. Which requirements and stories are being implemented?

| Story | AC | Covered by |
|---|---|---|
| 001 | `scale-3kg` at 90.0 g → 90.0 g `Decimal`, unit g, ready | `scale.read_weight` |
| 001 | new weight available within 200 ms, no reload | `scale-client.watchWeight` at 200 ms |
| 001 | active component on `scale-32kg` → only `scale-32kg` read | adapter and client read only the given `scaleId` |
| 002 | tare → net 0.0 g | `scale.tare`, `scale-client.tare` |
| 002 | disconnected → failure, nothing reported as tared | `ScaleDisconnected`; JS `DeviceError` |
| 003 | B-24187 scanned → received once | `scanner.read_new_scan`, `scanner-client.watchScans` (dedupe by `scanId`) |
| 003 | scanner unavailable → error, no state change | `ScannerUnavailable`; JS `DeviceError` |
| 004 | printer ready → ticket ID returned | `printer-client.printTicket` |
| 004 | printer error → PrinterError | JS `DeviceError` kind `error`, code `PRINTER_ERROR` |
| 005 | all ready → SCALE 3 kg / 32 kg / SCANNER / PRINTER READY | `device-status.js` |
| 005 | `scale-3kg` disconnected → not ready within 2 s, confirmation blocked | 1 s status poll; the server re-read raises `ScaleDisconnected`, which bolt 010's confirm uses |
| 005 | a failure is never shown as ready | every failure path maps to a non-ready state |

**Note on stories 001 and 005:** they say "UI polls through WeighingMS" and "WeighingMS device-status endpoint". They were written before the STEP 12 decision, which made the browser poll the Dummies directly. That is what puts `GET /api/scales/scale-3kg/weight` in the STEP 21 Network tab. The JS clients are the WeighingMS side of that, so no extra server endpoint is added.

### 4. Which APIs are involved?

These are consumed only; the Dummy training contracts are from bolt 002 and nothing changes.

| API | Client |
|---|---|
| `GET /api/scales/:scaleId/weight` | scale adapter + JS |
| `GET /api/scales/:scaleId/status` | scale adapter + JS |
| `POST /api/scales/:scaleId/tare` | scale adapter + JS |
| `GET /api/scanner/status` | JS |
| `GET /api/scanner/scans/latest` | scanner adapter + JS |
| `GET /api/printer/status` | JS |
| `POST /api/tickets` | JS |

The tests also use the training controls `/api/training/scales/:id/simulate`, `/api/training/scanner/scans` and `/api/training/modes/:target`.

### 5. How will this be tested?

**Django tests** (`npm test`) on a `LiveServerTestCase`: real HTTP against the seeded Dummies, with the base URLs pointed at the live server.

- **`tests/devices/test_scale_adapter.py`:**
  - simulate set 90.0 g → `read_weight("scale-3kg")` returns `Decimal("90.0")`, g, ready;
  - `scale-32kg` reads in kg;
  - routing: reading `scale-32kg` requests only `/scales/scale-32kg/weight`, checked by recording the URLs the adapter opens;
  - a new simulated weight is returned on the next read;
  - tare → net 0;
  - disconnected → `read_weight` and `tare` raise `ScaleDisconnected`, with a WARNING log naming the URL, `503` and the scale;
  - `read_status` returns `disconnected`;
  - back to `ok` → reads resume;
  - unknown scale, unreachable host, float or malformed body → `ScaleUnavailable`.
- **`tests/devices/test_scanner_adapter.py`:**
  - no scan → `None`;
  - B-24187 scanned → returned with `kind` `batch`;
  - `read_new_scan(after=that id)` → `None`, so the scan is received once;
  - a later dyestuff scan → returned;
  - unavailable → `ScannerUnavailable` and logged; no scan is stored, which is checked after the toggle;
  - back to `ok` → reads resume.
- **`tests/architecture/test_integration_boundaries.py`** (extended):
  - only `devices/scale.py` knows `/scales` and only `devices/scanner.py` knows `/scanner` among the WeighingMS Python files;
  - only `scale-client.js`, `device-status.js`, `scanner-client.js` and `printer-client.js` know their device paths among the JS files;
  - still no `dummy_*` imports.

**JS clients:** `node --check` during Implement, plus a manual browser-console smoke test. Their behaviour tests are the Playwright tests in bolt 007 (status change on a toggled Dummy) and bolt 011 (readout follows simulate), and the STEP 21 Network evidence. That covers the printer AC as well (Decision 2).

**Gate:** `npm test` (the 96 existing tests plus the new ones) and `npm run lint` pass.

### Dependencies

- Bolt 002 (complete): Dummy Scale, Scanner and Printer endpoints and the training toggles
- Bolt 003 (complete): the adapter pattern and the boundary tests
- No new packages

### Technical Approach

- Thin adapters: HTTP and parsing only, no database and no business rules. Scale **selection** is bolt 009; what a scanned code **means** is bolt 005; ticket **content** is bolt 016.
- Disconnection is reported two ways:
  - a `503 SCALE_DISCONNECTED` on weight or tare;
  - `status: "disconnected"` from `/status`.
- **Fail-safe mapping:**
  - an unknown error, timeout or malformed body is never "ready";
  - a JS poll that throws switches the device to `unavailable` until a later poll succeeds.

### Decisions for the user

1. **Python adapters only for the scale and the scanner, no Python printer adapter.**
   - **Recommended.** The STEP 12 decision has the browser post the ticket (STEP 27 Network evidence) and report the result, so a server-side printer adapter would be unused code.
   - *Alternative:* add `devices/printer.py` too, so story 004 gets Django tests, even though nothing calls it.
2. **JS client behaviour is tested by Playwright in bolts 007 and 011, not in this bolt.**
   - **Recommended.** It follows the approved stack (Django test runner + Playwright, set up in the first UI bolt). This bolt syntax-checks the JS and tests the Python side against real HTTP.
   - *Alternative:* set up Playwright here with a small test page. That pulls the E2E setup forward into a non-UI bolt.

### Acceptance Criteria

- [ ] Scale adapter: `Decimal` reading in the scale's unit, only the requested scale, tare → 0, disconnected → `ScaleDisconnected`, other failures → `ScaleUnavailable`, all failures logged
- [ ] Scanner adapter: latest scan, each scan received once, unavailable → `ScannerUnavailable` with nothing stored
- [ ] JS clients:
  - 200 ms weight polling and 1 s status polling;
  - tare, print and scan watch;
  - every failure → `DeviceError`, never `ready`
- [ ] One module per device knows its paths; no `dummy_*` imports
- [ ] `npm test` and `npm run lint` pass

### Out of scope for this bolt

- Scale selection rule (bolt 009), the confirmation check that uses `ScaleDisconnected` (bolt 010)
- Batch/dyestuff scan meaning (bolts 005, 008), ticket content and print records (bolt 016)
- Status bar and weigh-view rendering (bolts 007, 011); Playwright setup
- Stability flag (IR-11): the Dummy has none (A-05)
