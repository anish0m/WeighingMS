---
unit: 007-assisted-weighing-station-ui
intent: 001-assisted-weighing-station
phase: inception
status: ready
unit_type: frontend
default_bolt_type: simple-construction-bolt
created: 2026-11-20T04:22:15Z
updated: 2026-11-20T04:51:01Z
---

# Unit Brief: Operator Terminal UI

## Purpose

Reproduce the functional experience of `docs/customize-weighing-station.html` as the operator terminal, presenting the backend Units' behaviour faithfully. It holds no business rules and no scenario data.

## Scope

### In Scope
- Header (station, batch/order/machine, operator) and device status bar (SCALE 3 kg / SCALE 32 kg / SCANNER / PRINTER / ORGATEX).
- View 1 Select batch: queue, scan prompt, touch rows, received time, error messages.
- View 2 Weigh: recipe rail with counter, component header (name, code, lot, container, tare), dyestuff scan step, live readout, progress bar with tolerance band and target line, Target / Weighed now / Still to weigh, tolerance caption, zone colours, scale indicator "automatic", status line, surplus panel, buttons OK · Confirm (F1), Re-tare (F2), Supervisor override, Quit (F4).
- View 3 Confirm & print: summary, write-back status and retry, ticket preview, Print ticket (F1), Next batch (F3).
- Live weight polling (≤ 200 ms), touch targets ≥ 15 mm, English text.
- Playwright E2E tests.

### Out of Scope
- Any rule (tolerance, scale choice, progression, overshoot): rendered from 005's API, never computed in JS.
- Hard-coded batches, recipes or components in templates or JS.

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-21 | UI obtains batches, recipes, components, tolerances, weights, print results only via APIs over HTTP; no arrays in templates/JS; domain code imports no Dummy models | Must |

Renders the user-facing part of FR-1…FR-20 (owned by 002–006). Owns NFR-8 touch targets, NFR-9 F-keys, NFR-10 prototype fidelity, NFR-11 English; shares NFR-1 (render).

---

## Domain Concepts

### Key Entities
None (presentation only). View state: current view, active component, latest reading, device status.

### Key Operations
| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| Render view 1/2/3 | Server templates + Alpine.js | API data | Screens |
| Poll weight / status | Live refresh | API | Updated readout |
| Send actions | Select, scan, tare, confirm, quit, override, print, next | user input / F-keys | API calls |

---

## Story Summary

- **Total Stories**: 9
- **Must Have**: 9
- **Should Have**: 0
- **Could Have**: 0

### Stories

- [ ] **001-terminal-shell-and-status-bar**: Terminal shell: header, clock and device status bar - Must - Planned
- [ ] **002-select-batch-view**: View 1: Select batch - Must - Planned
- [ ] **003-weigh-view-recipe-rail-and-header**: View 2: recipe rail, component header and dyestuff scan step - Must - Planned
- [ ] **004-weigh-view-live-readout-and-tolerance**: View 2: live readout, progress bar and tolerance band - Must - Planned
- [ ] **005-weigh-view-actions-and-function-keys**: View 2: Confirm, Re-tare, Quit and function keys - Must - Planned
- [ ] **006-weigh-view-surplus-panel-and-override**: View 2: surplus panel and supervisor override - Must - Planned
- [ ] **007-confirm-and-print-view**: View 3: Confirm & print - Must - Planned
- [ ] **008-training-simulation-panel**: Training panel: simulate scale and failures - Must - Planned
- [ ] **009-no-hard-coded-scenario-data**: All UI data comes from the APIs - Must - Planned

---

## Dependencies

### Depends On
| Unit | Reason |
|------|--------|
| 003-device-integration | Live weight, status bar |
| 004-batch-recipe-management | Queue, selection, recipe rail, identity |
| 005-weighing-station | Weigh and completion state, actions |
| 006-ticket-printing | Print and preview |

### Depended By
None.

### External Dependencies
None (Alpine.js served locally).

---

## Technical Context

### Suggested Technology
Django templates + HTML/CSS + Alpine.js (local static file), per approved tech stack; Playwright for E2E.

### Integration Points
| Integration | Type | Protocol |
|-------------|------|----------|
| WeighingMS APIs (004, 005, 006, 003 status) | API | HTTP JSON |

### Data Storage
None.

---

## Constraints

- Visual and interaction fidelity to the prototype (STEP 28 comparison).
- Do not copy prototype shortcuts: float arithmetic, hard-coded surplus panel, `components` array.

---

## Success Criteria

### Functional
- [ ] All three views work end to end against the APIs with seed B-24187
- [ ] F1/F2/F4 on view 2 and F1/F3 on view 3 work

### Non-Functional
- [ ] Weight display refresh ≤ 200 ms; primary buttons ≥ 57 px

### Quality
- [ ] Playwright E2E covers the five-component flow and failure messages

---

## Bolt Suggestions

| Bolt | Type | Objective |
|------|------|-----------|
| ui-1 | Simple | Shell, header, status bar, view 1 (STEP 19) |
| ui-2 | Simple | View 2 Weigh (STEP 20–24) |
| ui-3 | Simple | View 3 Confirm & print (STEP 26–28) |
