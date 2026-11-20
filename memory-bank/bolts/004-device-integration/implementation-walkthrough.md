---
stage: implement
bolt: 004-device-integration
created: 2026-11-20T08:28:06Z
---

## Implementation Walkthrough: device-integration

### Summary

WeighingMS can now reach the station's devices, one module per device:
- **Server Python adapters**, only where the server is the authority:
  - **scale** (`read_weight`, `read_status`, `tare`) for re-reading the weight before a confirmation;
  - **scanner** (`read_latest_scan`, `read_new_scan`) for checking scanned codes.
- **Browser JS clients** for the live UI:
  - **scale** (polled at 5 Hz, plus tare);
  - **scanner** (each new scan delivered once);
  - **printer** (print a ticket);
  - **device status**, which feeds the status bar and is polled every 1 s.

Every failure is reported as disconnected, unavailable or error, and never as ready or success. All of these call the Dummy training contracts, not the real devices.

### Structure Overview

New WeighingMS app `devices` (unit 003), with no models.
- **`http.py`** is the shared plumbing for the Python adapters. It sends the request, rejects floats, logs failures and raises `DeviceCallFailed`.
- **`scale.py` and `scanner.py`** each own their paths and result types, and map failures to their own fail-safe exceptions.
- **`device-status.js`** is loaded first. It holds the shared `DeviceError`, the request helper and the status aggregator. Each client file owns its own paths.

### Completed Work

- [x] `src/devices/__init__.py`, `src/devices/apps.py` - New app "Device integrations"
- [x] `src/devices/http.py` - Shared device HTTP plumbing:
  - `call()` and the field parsers (`field`, `decimal_field`, `datetime_field`, `choice_field`);
  - floats are rejected while parsing;
  - every failure is logged at WARNING with device, method, URL, HTTP status and error code (IR-09).
- [x] `src/devices/scale.py` - Scale adapter:
  - `ScaleReading` (`Decimal` net weight, unit, status, `read_at`);
  - `ScaleDisconnected` for `503 SCALE_DISCONNECTED`;
  - `ScaleUnavailable` for everything else, including an unknown scale and a response for another scale.
- [x] `src/devices/scanner.py` - Scanner adapter:
  - `Scan` (`scan_id`, kind `batch`/`dyestuff`, code, `scanned_at`);
  - `read_new_scan(after_scan_id)` so each scan arrives once;
  - `ScannerUnavailable`.
- [x] `src/devices/static/devices/device-status.js`:
  - `DeviceError`, with kind `disconnected` / `unavailable` / `error` / `rejected`;
  - `requestJson`;
  - `createDeviceStatus(onChange)` covers SCALE 3 kg, SCALE 32 kg, SCANNER and PRINTER, each with a state and a `since` time, polled every 1000 ms.
- [x] `src/devices/static/devices/scale-client.js` - `readWeight`, `readStatus`, `tare`, and `watchWeight(scaleId, onReading, onFailure)`, which polls one scale every 200 ms until `stop()`
- [x] `src/devices/static/devices/scanner-client.js` - `readStatus`, `readLatestScan`, and `watchScans(onScan, onFailure)`, which calls `onScan` once per new `scanId` and ignores the scan already present when watching starts
- [x] `src/devices/static/devices/printer-client.js` - `readStatus`, and `printTicket(content, batchId)`, which resolves only when the printer returns a ticket ID
- [x] `src/weighingms/settings.py` - Registers `devices`; adds `SCALE_BASE_URL`, `SCANNER_BASE_URL` (default `http://localhost:8000/api`) and `DEVICE_TIMEOUT_SECONDS` (default 2)

### Key Decisions

- **No Python printer adapter; JS behaviour is tested with Playwright in bolts 007 and 011.** Both were approved with the plan.
- **Disconnected is separate from unavailable.** Only the Dummy's explicit `SCALE_DISCONNECTED` is "disconnected". An unreachable host, a timeout, an unknown scale or a malformed body is "unavailable". Neither is ever ready.
- **The device status never starts as `ready`:**
  - every device starts as `unavailable` until its first successful poll;
  - a thrown error or an unexpected status value maps to a non-ready state.
- **Polls don't overlap:**
  - the weight poll schedules its next tick after the previous one finishes, keeping a 200 ms cadence;
  - the status aggregator skips a tick while a poll is still running.
- **Scans already present when watching starts are ignored.** An old scan from before the page loaded therefore can't select a batch.

### Deviations from Plan

- **`device-status.js` knows no device paths.** The plan listed it among the JS files that know the paths. It asks each client for its status instead, so the scale, scanner and printer paths each live in exactly one JS file. The Test-stage boundary check will assert this.
- **Added `DeviceError` kind `rejected`** for a 400 response, for example an empty ticket. A 400 is invalid input, not a broken device. The status bar never shows `rejected`; it shows unavailable.

### Dependencies Added

None.

### Developer Notes

- **Checks:**
  - `manage.py check` is clean and `makemigrations --check` finds no changes;
  - `npm run lint` passes and the existing 96 tests pass;
  - `node --check` passes on all 4 JS files.
- **Python smoke test against the dev server:**
  - simulate 90.0 g → `read_weight("scale-3kg")` returns `90.0000 g ready`;
  - `scale-32kg` reads in kg; tare → `0.0000`;
  - a scanned B-24187 is returned once, then `read_new_scan(id)` → `None`;
  - `scale-9kg` → Unavailable (`404 SCALE_NOT_FOUND`);
  - disconnected → `read_weight` and `tare` raise `ScaleDisconnected` and `read_status` returns `disconnected`;
  - scanner off → `ScannerUnavailable`.
- **JS smoke test in Node 24, fetch prefixed with the dev server URL:**
  - status shows `SCALE 3 kg=disconnected, SCANNER=unavailable, PRINTER=error`, then all `ready` after restoring;
  - tare → `disconnected SCALE_DISCONNECTED`; print with the printer in error → `error PRINTER_ERROR`;
  - print with the printer ok → ticket ID;
  - `watchScans` ignored the existing scan and delivered `DYE-4471` once;
  - `watchWeight("scale-32kg")` made 6 polls in about 1.15 s (≈ 5 Hz) and followed the simulated `24.0480 kg`.
- After the smoke tests, the dev database was re-seeded: all modes `ok`, no scans, no tickets.
