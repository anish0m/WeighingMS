---
id: 007-confirm-and-print-view
unit: 007-assisted-weighing-station-ui
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: null
implemented: false
---

# Story: 007-confirm-and-print-view

## User Story

**As an** operator
**I want** a completion screen with the summary, the OrgaTEX status and the ticket
**So that** I can print, check the write-back and move to the next batch

## Requirements

- FR-16, FR-17, FR-18 (rendering)
- NFR-9, NFR-10

## Acceptance Criteria

- [ ] **Given** B-24187 is complete, **When** view 3 opens, **Then** "Batch B-24187 weighed", Components weighed 5 of 5, All within tolerance YES, Total dispensed, Elapsed, Operator are shown from the API
- [ ] **Given** write-back confirmed / not written, **When** view 3 renders, **Then** "Written to OrgaTEX CONFIRMED hh:mm:ss" / "not written" with a Retry action
- [ ] **Given** view 3, **When** Print ticket F1 / Next batch F3 is used, **Then** the ticket prints and the preview shows / the queue (view 1) opens

## UI/UX Impact

- View 3 in full, including ticket preview
- Matches the prototype `docs/customize-weighing-station.html` (labels, layout, colours, units) for the STEP 28 comparison

## API Dependencies

- Consumes: WeighingMS completion (005), write-back status/retry (002), print/preview (006)

## Test Expectations

- Playwright STEP 26–27: summary values, CONFIRMED, print and next batch

## Technical Notes

- None

## Dependencies

### Requires
- 005-weighing-station/009-complete-batch
- 002-orgatex-integration/003-write-back-failure-and-retry
- 006-ticket-printing/002-reprint-and-print-failure

### Enables
- 007-assisted-weighing-station-ui/009-no-hard-coded-scenario-data

## Out of Scope

- None
