---
unit: 002-orgatex-integration
intent: 001-assisted-weighing-station
phase: inception
status: ready
created: 2026-11-20T04:22:15Z
updated: 2026-11-20T04:51:01Z
---

# Unit Brief: OrgaTEX Integration

## Purpose

The single WeighingMS-side adapter for OrgaTEX (brief IR-07). It is the only code that knows the (Dummy) OrgaTEX contract, so replacing the Dummy with the real interface later changes only this Unit.

## Scope

### In Scope
- Client for queue, batch detail and recipe reads; parse quantities as `Decimal`.
- Consumption write-back with an idempotency key, write-back status (pending / confirmed with time / not written) and retry.
- Mapping failures to "OrgaTEX unavailable" / "not written"; logging per IR-09.

### Out of Scope
- Deciding which batch is selectable or how a recipe is shown (004).
- Deciding when a batch is complete (005).
- Batch status write-back (brief IR-06): not built (System Context decision).

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-17 | On completion, post actual consumption per component to Dummy OrgaTEX; show CONFIRMED + time only after acceptance; idempotent retry; failure shows "not written" with retry | Must |

Also supports: FR-1c and FR-3d (unavailable reads, owned by 004), FR-21b (no Dummy model imports), NFR-7.

---

## Domain Concepts

### Key Entities
| Entity | Description | Attributes |
|--------|-------------|------------|
| WriteBack | One consumption posting for a batch | batch_id, idempotency key, status, attempts, confirmed_at, last_error |

### Key Operations
| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| fetch_queue | Released batches | – | batch list or Unavailable |
| fetch_batch / fetch_recipe | Batch detail, recipe | batch_id | data or NotFound / Unavailable |
| post_consumption | Idempotent write-back | batch_id, actuals | confirmed (time) / not written |
| retry_write_back | Re-send with same key | batch_id | confirmed / not written |

---

## Story Summary

- **Total Stories**: 3
- **Must Have**: 3
- **Should Have**: 0
- **Could Have**: 0

### Stories

- [ ] **001-read-batches-and-recipe**: Read queue, batch and recipe through the OrgaTEX adapter - Must - Planned
- [ ] **002-post-consumption-idempotently**: Post actual consumption idempotently - Must - Planned
- [ ] **003-write-back-failure-and-retry**: Write-back failure is visible and retryable - Must - Planned

---

## Dependencies

### Depends On
| Unit | Reason |
|------|--------|
| 001-dummy-integrations | HTTP contract of Dummy OrgaTEX |

### Depended By
| Unit | Reason |
|------|--------|
| 004-batch-recipe-management | Queue, batch and recipe reads |
| 005-weighing-station | Completion triggers write-back |
| 007-assisted-weighing-station-ui | ORGATEX status and write-back status shown |

### External Dependencies
| System | Purpose | Risk |
|--------|---------|------|
| OrgaTEX (real, future) | Batch/recipe master, consumption receiver | High (A-01, A-02 unconfirmed) |

---

## Technical Context

### Suggested Technology
Plain Python adapter module with an HTTP client; base URL from settings.

### Integration Points
| Integration | Type | Protocol |
|-------------|------|----------|
| Dummy OrgaTEX API | API | HTTP JSON |

### Data Storage
| Data | Type | Volume | Retention |
|------|------|--------|-----------|
| Write-back status | SQLite | One per batch | With batch records |

---

## Constraints

- No other module calls OrgaTEX (IR-07).
- Never shows CONFIRMED unless the Dummy accepted the post (NFR-7).

---

## Success Criteria

### Functional
- [ ] Completing B-24187 posts consumption once; a retry creates no second record
- [ ] With Dummy OrgaTEX unavailable, reads report unavailable and write-back stays "not written"

### Non-Functional
- [ ] Failures logged with enough detail to diagnose (IR-09)

### Quality
- [ ] Every approved acceptance criterion has an automated test

---

## Bolt Suggestions

| Bolt | Type | Objective |
|------|------|-----------|
| orgatex-integration-1 | Simple | Read client (queue, batch, recipe) |
| orgatex-integration-2 | Simple | Idempotent write-back + retry (STEP 26) |
