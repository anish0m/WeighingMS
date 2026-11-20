---
id: 007-dummy-failure-toggles
unit: 001-dummy-integrations
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 002-dummy-integrations
implemented: false
---

# Story: 007-dummy-failure-toggles

## User Story

**As a** trainer
**I want** to switch each Dummy into its failure mode and back
**So that** fail-safe behaviour can be demonstrated and tested (workbook STEP 30)

## Requirements

- DB-4, DB-7, DB-8, DB-9
- Supports FR-1c, FR-3d, FR-17d, FR-20

## Acceptance Criteria

- [ ] **Given** Dummy OrgaTEX set to unavailable, **When** any OrgaTEX endpoint is called, **Then** it returns a 503-style error
- [ ] **Given** Dummy Scale `scale-3kg` set to disconnected, **When** weight/status is read, **Then** status is disconnected and no weight is returned
- [ ] **Given** Dummy Scanner set to unavailable / Dummy Printer set to error, **When** a scan / print is attempted, **Then** an error is returned and nothing is stored
- [ ] **Given** any Dummy in failure mode, **When** it is switched back to ok, **Then** normal responses resume

## UI/UX Impact

- Indirect: status bar and error messages; toggles are exposed in the training panel (007-…-ui/008)

## API Dependencies

- Provides: training-only toggle endpoint per Dummy (shape fixed in Bolt design)

## Test Expectations

- Django API tests for each toggle on/off

## Technical Notes

- Training contract only: not a claim about the real OrgaTEX / device interface (A-01…A-15 stay unresolved).

## Dependencies

### Requires
- 002-dummy-orgatex-batch-endpoints
- 005-dummy-scale-api
- 006-dummy-scanner-and-printer

### Enables
- 002-orgatex-integration/003-write-back-failure-and-retry
- 003-device-integration/005-device-status-and-fail-safe
- 006-ticket-printing/002-reprint-and-print-failure
- 007-assisted-weighing-station-ui/008-training-simulation-panel

## Out of Scope

- None
