---
id: 004-device-integration
unit: 003-device-integration
intent: 001-assisted-weighing-station
type: simple-construction-bolt
status: planned
stories:
  - 001-read-live-scale-weight
  - 002-tare-command
  - 003-scanner-input
  - 004-printer-adapter
  - 005-device-status-and-fail-safe
created: 2026-11-20T05:15:14Z
started: null
completed: null
current_stage: null
stages_completed: []

# Bolt Dependencies (for execution ordering)
requires_bolts: [002-dummy-integrations]
enables_bolts: [005-batch-recipe-management, 007-assisted-weighing-station-ui, 010-weighing-station, 011-assisted-weighing-station-ui, 016-ticket-printing]
requires_units: []  # unit ordering is enforced through requires_bolts (see body)
blocks: true

# Complexity Assessment (aggregate of included stories)
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
workbook_step: "STEP 19"
---

# Bolt: 004-device-integration

## Overview

Device access: browser-side Scale/Scanner/Printer clients, server-side Scale adapter, device status and fail-safe. Serves workbook STEP 19.

## Objective

Device access: browser-side Scale/Scanner/Printer clients, server-side Scale adapter, device status and fail-safe.

## Stories Included

- **001-read-live-scale-weight**: the weight on the selected scale to update continuously while I dispense (Must)
- **002-tare-command**: to zero the scale with the container on it (Must)
- **003-scanner-input**: my batch card and dyestuff barcode scans to reach the station (Must)
- **004-printer-adapter**: to submit a ticket to the printer and know whether it printed (Must)
- **005-device-status-and-fail-safe**: to see the state of every device and be stopped when one fails (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [ ] **1. Plan**: Pending → implementation-plan.md
- [ ] **2. Implement**: Pending → source code + implementation-walkthrough.md
- [ ] **3. Test**: Pending → tests + test-walkthrough.md

## Expected Outcome

- Browser JS clients, one per device: scale (`GET /api/scales/:scaleId/weight` polled ≥ 5 Hz, `/status`, `POST /tare`), scanner, printer (`POST /api/tickets`)
- Server Python Scale adapter (re-reads the weight for server-side confirmation checks)
- Device status service for SCALE 3 kg / SCALE 32 kg / SCANNER / PRINTER; disconnection detected ≤ 2 s; failures never shown as success

## Test Expectations

- Django tests: Decimal parsing, scale routing, tare, disconnected/unavailable/error
- Workbook STEP 21 Network evidence `GET /api/scales/scale-3kg/weight`

## Dependencies

### Requires
- 002-dummy-integrations

### Unit Dependencies (cross-unit, satisfied through the bolts above)
- 001-dummy-integrations

### Enables
- 005-batch-recipe-management
- 007-assisted-weighing-station-ui
- 010-weighing-station
- 011-assisted-weighing-station-ui
- 016-ticket-printing

## Success Criteria

- [ ] All stories implemented
- [ ] All acceptance criteria met
- [ ] Tests passing (`npm test`; Playwright where listed)
- [ ] Code reviewed

## Notes

- Dummy APIs are training contracts, not the real OrgaTEX / device interfaces.
- Architecture (STEP 12 decision): the browser calls the Dummy APIs directly through one JS client per integration; the WeighingMS server stays the authority (re-reads the scale for confirmation, stores records, supplies write-back payload/key and ticket content).
