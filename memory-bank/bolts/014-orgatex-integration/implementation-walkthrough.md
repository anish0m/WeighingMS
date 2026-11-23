---
stage: implement
bolt: 014-orgatex-integration
created: 2026-11-23T10:30:00Z
---

## Implementation Walkthrough: orgatex-integration (consumption write-back)

### Summary

A fully weighed batch's actual consumption can now be written back to Dummy OrgaTEX, and the result is stored as a visible status:
- the server supplies the body and the idempotency key;
- the browser's OrgaTEX client posts it and reports back;
- the server sets CONFIRMED only after its own adapter has found the key in OrgaTEX.

A failure becomes "not written" with a reason. A retry reuses the same row and key.

### Structure Overview

The OrgaTEX unit (`orgatex` app) owns:
- the `WriteBack` entity;
- the key and body rules;
- the check against OrgaTEX.

The weighing unit (`weighing` app) owns:
- the precondition (every component recorded);
- the lines taken from the stored records;
- the three station endpoints.

The dependency runs `weighing` → `orgatex` only. In the browser, the OrgaTEX client is still the only JS file that knows the Dummy path. The station client chains start → post → report.

### Completed Work

- [x] `src/orgatex/models.py` - **new.** `WriteBack` and `WriteBackStatus` (pending / confirmed / not written):
  - one row per weighing session, with a unique key;
  - stores the attempts, OrgaTEX's acceptance time, the last error and the operator;
  - a database check allows a confirmation time only on a confirmed row.
- [x] `src/orgatex/migrations/0001_initial.py` - **new.** Creates the write-back table.
- [x] `src/orgatex/adapter.py` - new read `fetch_consumptions`:
  - returns the consumptions OrgaTEX holds for a batch as typed, immutable results (quantities as `Decimal`), or the existing not-found / unavailable errors;
  - the ISO-time parsing is now a shared helper, also used by the queue read.
- [x] `src/orgatex/write_back.py` - **new.**
  - the key `WMS-<batchId>-S<sessionId>` and the contract body;
  - start / retry (attempt count; a confirmed write-back stays confirmed);
  - the check that decides confirmed or not written from OrgaTEX's own data. OrgaTEX is read outside the short transaction that writes the status;
  - logging: INFO on start and confirm, WARNING on "not written" and on a failed check (IR-09).
- [x] `src/weighing/consumption.py` - **new.**
  - starting requires an operator and every component recorded, and builds the lines from the stored records at display resolution;
  - the report requires an operator and a started write-back;
  - the status read is read-only. Records are never changed.
- [x] `src/weighing/services.py` - two new refusal reasons: `BATCH_NOT_COMPLETE` and `WRITE_BACK_NOT_STARTED`.
- [x] `src/weighing/views.py` and `src/weighing/urls.py` - new endpoints under `/station/api/sessions/<id>/`:
  - `write-back` (GET status, POST start or retry);
  - `write-back/result` (POST the browser's report: `posted` as a boolean, an optional `reason`);
  - both refusals map to HTTP 409.
- [x] `src/orgatex/static/orgatex/orgatex-client.js` - `postConsumption`:
  - 200 / 201 → the Dummy's JSON;
  - 503, a network error or a malformed answer → "unavailable";
  - any other contract error → "rejected".
- [x] `src/station/static/station/station-client.js` - `writeBackStatus` and `writeBack(sessionId)`:
  - start; skip the post if already confirmed; post through the OrgaTEX client;
  - report back and resolve to the server's status.

### Key Decisions

- **The server decides CONFIRMED (approved Decision 1):** the browser's report only triggers the server's read. A report of "posted" that OrgaTEX does not hold becomes "not written". A report of "not posted" for a post that OrgaTEX did store (timeout) becomes "confirmed".
- **Key `WMS-<batchId>-S<sessionId>` (approved Decision 2):** it is stable across retries, so the Dummy's idempotency stops a second record.
- **`WriteBack` in `orgatex`, endpoints in `weighing` (approved Decision 3):** session and operator are stored as plain values, with no foreign keys back into `weighing`.
- **Reason text:**
  - the browser's reason is used when it gave one, trimmed to 200 characters;
  - otherwise "OrgaTEX did not store the consumption" (if posted) or "OrgaTEX unavailable";
  - if the server's own read fails, the reason is always "OrgaTEX unavailable".
- **The status read (GET) needs no operator,** like the existing progress read. Start and report need one (ADR-005).

### Deviations from Plan

- **None in behaviour.**
- The start response also carries `batchId`, so the browser knows which OrgaTEX path to post to without its own state.
- The status JSON includes `operatorId` (FR-19: a write-back is attributable to the operator).

### Dependencies Added

- None.

### Developer Notes

- **Dev database:** migration `orgatex/0001` was applied with `migrate`. This only adds the empty write-back table; no data was reset.
- **Regression after the change:** lint clean, Django 475/475. The integration-boundary test still passes: `orgatex` imports no Dummy, and the Dummy path appears only in the adapter and the OrgaTEX client.
- **Bolt 015** adds batch completion; once a batch is complete, the browser runs `writeBack` (which calls start). **Bolt 017** renders the status ("Written to OrgaTEX CONFIRMED hh:mm:ss" / not written + Retry).
