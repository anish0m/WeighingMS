---
stage: implement
bolt: 003-orgatex-integration
created: 2026-11-20T07:51:58Z
---

## Implementation Walkthrough: orgatex-integration

### Summary

WeighingMS now reads OrgaTEX through exactly one module per runtime:
- **Server:** the Python adapter `orgatex/adapter.py` returns typed, immutable batch, queue and recipe objects with `Decimal` quantities.
- **Browser:** the JS client `orgatex-client.js` calls the same paths with `fetch`.

Both report a missing batch or recipe as "not found". Anything else that goes wrong is reported as "unavailable" and is never passed off as data. Both call the Dummy OrgaTEX training contract, not the real OrgaTEX interface.

### Structure Overview

The new WeighingMS app `orgatex` is unit 002's home; bolt 014 will add the write-back here.
- The adapter only does HTTP and parsing. It has no database access and no business rules.
- The base URL and timeout come from settings and can be overridden by environment variables.
- Static files:
  - The JS client is a static file of the same app, served at `/static/orgatex/orgatex-client.js`.
  - It exposes `window.WeighingMS.orgatex` for the Alpine.js views in bolt 007.

### Completed Work

- [x] `src/orgatex/__init__.py`, `src/orgatex/apps.py` - New app "OrgaTEX integration"
- [x] `src/orgatex/adapter.py` - Covers:
  - `fetch_queue`, `fetch_batch`, `fetch_recipe`;
  - frozen dataclasses `Queue`, `Batch`, `Recipe`, `RecipeComponent`;
  - `OrgatexNotFound(code, message)` and `OrgatexUnavailable(reason)`;
  - strict response parsing: decimal strings only, required fields, the batch ID must match the request;
  - IR-09 logging.
- [x] `src/orgatex/static/orgatex/orgatex-client.js` - Browser client: `fetchQueue`, `fetchBatch`, `fetchRecipe`, and `OrgatexError` with kind `not-found` or `unavailable`
- [x] `src/weighingms/settings.py` - Registers `orgatex`; adds `ORGATEX_BASE_URL` (default `http://localhost:8000/api`) and `ORGATEX_TIMEOUT_SECONDS` (default 5)

### Key Decisions

- **Malformed response → `OrgatexUnavailable`** (approved). It is logged as "malformed response" with the reason.
- **What counts as NotFound:** only a 404 that carries the contract's error body.
  - A bare 404, for example from a wrong base URL, counts as Unavailable. This way a misconfiguration never looks like "batch not found".
- **Log levels:**
  - NotFound is a normal business answer and is logged at INFO.
  - Every Unavailable cause is logged at WARNING: HTTP status and error code, network error, or malformed body. Each log line has the URL and batch ID (IR-09).
- **Floats are rejected while parsing the JSON** (`parse_float` raises). A quantity therefore can never pass through a float.
- **The recipe or batch must belong to the requested batch ID.** A mismatch is treated as malformed. This guards the later recipe snapshot.
- **Results use tuples** instead of lists, so a snapshot cannot be changed after it is read.

### Deviations from Plan

None.

### Dependencies Added

None. The adapter uses the standard library `urllib.request`.

### Developer Notes

- Verified during Implement:
  - `manage.py check` is clean and `makemigrations --check` finds no changes;
  - `npm run lint` passes;
  - the existing 71 tests pass;
  - `node --check` passes on the JS client;
  - the dev server serves `/static/orgatex/orgatex-client.js` (200, `text/javascript`).
- Smoke-checked against the running dev server:
  - the queue returns 4 batches with `received_at`;
  - B-24187's details;
  - the Teal 4C recipe with `Decimal` values;
  - B-99999 → NotFound `BATCH_NOT_FOUND`;
  - B-24188's recipe → NotFound `RECIPE_NOT_AVAILABLE`;
  - Dummy toggled unavailable → `OrgatexUnavailable` "HTTP 503 ORGATEX_UNAVAILABLE", with a WARNING log; then switched back to `ok`;
  - base URL on a closed port → Unavailable "Connection refused".
- The JS client keeps `/api` and `/batches` as separate strings. The Test-stage boundary check therefore looks for the `/batches` path.
