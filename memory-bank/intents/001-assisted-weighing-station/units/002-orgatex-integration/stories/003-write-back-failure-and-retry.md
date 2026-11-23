---
id: 003-write-back-failure-and-retry
unit: 002-orgatex-integration
intent: 001-assisted-weighing-station
status: complete
priority: must
created: 2026-11-20T04:51:01.000Z
assigned_bolt: 014-orgatex-integration
implemented: true
---

# Story: 003-write-back-failure-and-retry

## User Story

**As an** operator
**I want** to see when consumption was not written to OrgaTEX and to retry it
**So that** no completed batch is silently missing from OrgaTEX

## Requirements

- FR-17 (b, d)
- NFR-7
- IR-09 (brief)

## Acceptance Criteria

- [ ] **Given** Dummy OrgaTEX is unavailable, **When** write-back is triggered, **Then** the status is "not written" with the reason, never CONFIRMED, and the weighing records stay in WeighingMS
- [ ] **Given** status is "not written" and OrgaTEX is back, **When** retry is requested, **Then** the post succeeds with the same idempotency key and the status becomes CONFIRMED with time
- [ ] **Given** an ambiguous failure (timeout after the Dummy stored the post), **When** retry is requested, **Then** no duplicate consumption is created

## UI/UX Impact

- View 3: "not written" state and a retry action (rendered by 007)
- Status bar ORGATEX state

## API Dependencies

- Consumes: Dummy OrgaTEX consumption endpoint + failure toggle

## Test Expectations

- Django tests with the Dummy toggled unavailable; retry; duplicate check
- Playwright failure scenario in STEP 30

## Technical Notes

- None

## Dependencies

### Requires
- 002-post-consumption-idempotently
- 001-dummy-integrations/007-dummy-failure-toggles

### Enables
- 007-assisted-weighing-station-ui/007-confirm-and-print-view

## Out of Scope

- None
