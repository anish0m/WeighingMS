---
unit: 003-device-integration
intent: 001-assisted-weighing-station
phase: inception
status: ready
created: 2026-11-20T04:22:15Z
updated: 2026-11-20T04:51:01Z
---

# Unit Brief: Device Integration (Scale, Scanner, Printer)

## Purpose

WeighingMS-side adapters for the station's devices, one module per device, plus the device status shown in the status bar. Every device failure fails safe and is visible; no failure is ever reported as success.

## Scope

### In Scope
- Scale adapter: net weight, unit and status for a named scale (`scale-3kg`, `scale-32kg`); tare command; disconnection detected within 2 s.
- Live weight feed to the UI at ≥ 5 Hz (NFR-1).
- Scanner adapter: receive batch and dyestuff codes; report unavailable.
- Printer adapter: submit a ticket, return result / preview; report error.
- Device status service: SCALE 3 kg, SCALE 32 kg, SCANNER, PRINTER states.

### Out of Scope
- Which scale a component uses (rule in 005).
- What a scanned code means (004 for batch/dyestuff checks).
- Ticket content (006).
- ORGATEX status (002).

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-9 | Live net weight from the selected scale, updating continuously without reload; value is the Dummy Scale API's | Must |
| FR-20 | Device failures fail safe and are visible: scale disconnected → unavailable + confirm blocked within 2 s; scanner failing → error, nothing changes; printer error → not printed, can print later; never shown as success | Must |

Also supports: NFR-1, NFR-7, NFR-13 (device config), FR-7 (tare command, owned by 005), FR-21b.

---

## Domain Concepts

### Key Entities
| Entity | Description | Attributes |
|--------|-------------|------------|
| ScaleReading | One reading | scale_id, net weight (Decimal), unit, status, read_at |
| DeviceStatus | Current state per device | device, state (ready / disconnected / unavailable / error), since |

### Key Operations
| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| read_weight | Current net weight | scale_id | ScaleReading or Disconnected |
| tare | Zero the net reading | scale_id | ok / failure |
| read_scan | Next scanned code | – | code or Unavailable |
| print | Submit ticket | ticket | printed (id) / PrinterError |
| device_status | All device states | – | list of DeviceStatus |

---

## Story Summary

- **Total Stories**: 5
- **Must Have**: 5
- **Should Have**: 0
- **Could Have**: 0

### Stories

- [ ] **001-read-live-scale-weight**: Read live net weight from a named scale - Must - Planned
- [ ] **002-tare-command**: Send the tare command to the selected scale - Must - Planned
- [ ] **003-scanner-input**: Receive scanned codes from the scanner - Must - Planned
- [ ] **004-printer-adapter**: Send tickets to the printer - Must - Planned
- [ ] **005-device-status-and-fail-safe**: Device status and fail-safe on failure - Must - Planned

---

## Dependencies

### Depends On
| Unit | Reason |
|------|--------|
| 001-dummy-integrations | HTTP contracts of Dummy Scale, Scanner, Printer |

### Depended By
| Unit | Reason |
|------|--------|
| 004-batch-recipe-management | Batch and dyestuff scans |
| 005-weighing-station | Weight, tare, scale status for confirmation |
| 006-ticket-printing | Printer |
| 007-assisted-weighing-station-ui | Live weight, status bar |

### External Dependencies
| System | Purpose | Risk |
|--------|---------|------|
| Real scales (future) | Weight stream | High (A-05) |
| Real scanner (future) | Barcodes | Medium (A-10) |
| Real printer (future) | Tickets | Low (A-04) |

---

## Technical Context

### Suggested Technology
Plain Python adapter modules (`scale`, `scanner`, `printer`) with an HTTP client; device base URLs and scale IDs from settings.

### Integration Points
| Integration | Type | Protocol |
|-------------|------|----------|
| Dummy Scale / Scanner / Printer | API | HTTP JSON |

### Data Storage
| Data | Type | Volume | Retention |
|------|------|--------|-----------|
| None persistent (status is live) | – | – | – |

---

## Constraints

- Weights parsed as `Decimal`, never float.
- One adapter module per device; no Dummy model imports (FR-21b).

---

## Success Criteria

### Functional
- [ ] Reading `scale-3kg` returns the Dummy's weight; tare zeroes it
- [ ] Disconnected scale reported within 2 s; scanner and printer failures reported, never as success

### Non-Functional
- [ ] Weight refresh interval ≤ 200 ms on the UI path

### Quality
- [ ] Every approved acceptance criterion has an automated test

---

## Bolt Suggestions

| Bolt | Type | Objective |
|------|------|-----------|
| device-integration-1 | Simple | Scale adapter + status (STEP 21) |
| device-integration-2 | Simple | Scanner and printer adapters + failure handling |
