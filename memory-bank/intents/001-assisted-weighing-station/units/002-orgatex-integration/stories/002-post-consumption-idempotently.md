---
id: 002-post-consumption-idempotently
unit: 002-orgatex-integration
intent: 001-assisted-weighing-station
status: complete
priority: must
created: 2026-11-20T04:51:01.000Z
assigned_bolt: 014-orgatex-integration
implemented: true
---

# Story: 002-post-consumption-idempotently

## User Story

**As a** store / inventory (via WeighingMS)
**I want** actual consumption of a completed batch posted to (Dummy) OrgaTEX exactly once
**So that** actual vs theoretical consumption can be reconciled (BO-04)

## Requirements

- FR-17 (a, c)
- IR-05, IR-08 (brief)

## Acceptance Criteria

- [ ] **Given** B-24187 is complete with 5 confirmed records, **When** write-back is triggered, **Then** one consumption post is sent with per-component actuals and an idempotency key derived from the batch
- [ ] **Given** the post was accepted, **When** write-back is triggered again, **Then** the same key is used and Dummy OrgaTEX still holds one consumption record
- [ ] **Given** Dummy OrgaTEX accepts, **When** the response arrives, **Then** the write-back status becomes CONFIRMED with the acceptance time

## UI/UX Impact

- View 3: "Written to OrgaTEX CONFIRMED hh:mm:ss" (rendered by 007)

## API Dependencies

- Consumes: Dummy OrgaTEX `POST /api/batches/:batchId/consumption`

## Test Expectations

- Django test: one post creates one record; repeat creates none
- Workbook STEP 26 evidence

## Technical Notes

- Brief IR-06 (batch status write-back) is not built

## Dependencies

### Requires
- 001-dummy-integrations/004-dummy-orgatex-consumption-endpoint

### Enables
- 002-orgatex-integration/003-write-back-failure-and-retry
- 005-weighing-station/009-complete-batch

## Out of Scope

- None
