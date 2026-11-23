---
unit: 005-weighing-station
intent: 001-assisted-weighing-station
created: 2026-11-20T09:02:10Z
last_updated: 2026-11-23T10:39:21Z
---

# Construction Log: weighing-station

## Original Plan

**From Inception**: 5 bolts planned
**Planned Date**: 2026-11-20T05:15:14Z

| Bolt ID | Stories | Type |
|---------|---------|------|
| 006-weighing-station | 001-identify-operator | ddd-construction-bolt |
| 009-weighing-station | 002-select-scale-automatically, 004-target-and-remaining, 005-evaluate-inclusive-tolerance | ddd-construction-bolt |
| 010-weighing-station | 003-tare-retare-and-quit, 006-confirm-weighing, 008-progress-components, 010-resume-after-reload | ddd-construction-bolt |
| 012-weighing-station | 007-handle-overshoot | ddd-construction-bolt |
| 015-weighing-station | 009-complete-batch, 011-retrieve-batch-history | ddd-construction-bolt |

## Replanning History

| Date | Action | Change | Reason | Approved |
|------|--------|--------|--------|----------|

## Current Bolt Structure

| Bolt ID | Stories | Status | Changed |
|---------|---------|--------|---------|
| 006-weighing-station | 001 | ✅ completed | - |
| 009-weighing-station | 002, 004, 005 | ✅ completed | - |
| 010-weighing-station | 003, 006, 008, 010 | ✅ completed | - |
| 012-weighing-station | 007 | ✅ completed | - |
| 015-weighing-station | 009, 011 | ⏳ in-progress | - |

## Execution History

| Date | Bolt | Event | Details |
|------|------|-------|---------|
| 2026-11-20T09:02:10Z | 006-weighing-station | started | Stage 1: Domain Model |
| 2026-11-20T09:16:48Z | 006-weighing-station | stage-complete | Domain Model → Technical Design (APPROVE MODEL; recommended decisions: own Operator/Supervisor entities with hashed PIN, current operator in the server-side Django session, seed OP-01 R. Karim · Shift A + SUP-01 training supervisor, existing open session returned) |
| 2026-11-20T09:19:44Z | 006-weighing-station | stage-complete | Technical Design → ADR Analysis (APPROVE DESIGN; app `weighing`, `/station/api/operators`, `/operator`, `/sessions`; one open session per batch; seed migration) |
| 2026-11-20T09:23:09Z | 006-weighing-station | stage-complete | ADR Analysis → Implement (APPROVE ADR; ADR-004 seeded station identities, ADR-005 current operator in server session; both accepted) |
| 2026-11-20T09:27:17Z | 006-weighing-station | stage-complete | Implement → Test (APPROVE IMPLEMENTATION; app `weighing`, seed migration, sessions app + middleware enabled) |
| 2026-11-20T09:30:26Z | 006-weighing-station | completed | All 5 stages done (APPROVE TESTS); 227/227 tests pass; story 001 complete; unit stays open for bolts 009, 010, 012, 015 |
| 2026-11-23T04:44:23Z | 009-weighing-station | started | Stage 1: Domain Model |
| 2026-11-23T04:45:57Z | 009-weighing-station | stage-complete | Domain Model → Technical Design (APPROVE MODEL; recommended decisions: reading converted to the component unit, one value at display resolution shown/evaluated/recorded, threshold setting `WEIGHING_SCALE_THRESHOLD_KG` with env override, tolerance verdict only (bolt 010 combines), over status shows surplus amount only) |
| 2026-11-23T04:49:12Z | 009-weighing-station | stage-complete | Technical Design → ADR Analysis (APPROVE DESIGN; no model/migration; `scale_selection.py`, `tolerance.py`, `rules.py`; `GET …/components` extended with target/scale/tolerance; new `GET …/components/<seq>/evaluation`; choice A: server evaluates each changed reading) |
| 2026-11-23T04:53:56Z | 009-weighing-station | stage-complete | ADR Analysis → Implement (APPROVE ADR; ADR-008 server is the single source of the weighing rules, ADR-009 one value at display resolution; both accepted) |
| 2026-11-23T04:59:35Z | 009-weighing-station | stage-complete | Implement → Test (APPROVE IMPLEMENTATION; `tolerance.py`, `scale_selection.py`, `rules.py`, setting `WEIGHING_SCALE_THRESHOLD_KG`, extended `GET …/components`, new `GET …/evaluation`; no migration) |
| 2026-11-23T05:03:33Z | 009-weighing-station | completed | All 5 stages done (APPROVE TESTS); 360/360 Django tests, 19/19 Playwright; stories 002, 004, 005 complete; unit stays open for bolts 010, 012, 015 |
| 2026-11-23T05:09:30Z | 010-weighing-station | started | Stage 1: Domain Model |
| 2026-11-23T05:11:30Z | 010-weighing-station | stage-complete | Domain Model → Technical Design (APPROVE MODEL; recommended decisions: server tares via adapter, quit starts an untared attempt, record tare from snapshot, next component activated in the confirm transaction with tare after commit, resume the most recently active open session, record operator = current station operator) |
| 2026-11-23T05:13:08Z | 010-weighing-station | stage-complete | Technical Design → ADR Analysis (APPROVE DESIGN; `progression.py`, `confirmation.py`; models `ComponentAttempt`, `WeighingRecord` (migration 0004); 6 endpoints incl. `GET /current-session`; scale I/O outside the transaction, re-check under lock) |
| 2026-11-23T05:27:05Z | 010-weighing-station | stage-complete | ADR Analysis → Implement (APPROVE ADR; ADR-010 stored append-only attempts, derived component state; ADR-011 scale I/O outside the transaction, re-check under lock; both accepted) |
| 2026-11-23T05:42:35Z | 010-weighing-station | stage-complete | Implement → Test (APPROVE IMPLEMENTATION; `progression.py`, `confirmation.py`, models `ComponentAttempt` / `WeighingRecord` + migration 0004, 6 endpoints) |
| 2026-11-23T05:47:57Z | 010-weighing-station | completed | All 5 stages done (APPROVE TESTS); 430/430 Django tests, 19/19 Playwright; stories 003, 006, 008, 010 complete; unit stays open for bolts 012, 015 |
| 2026-11-23T08:52:26Z | 012-weighing-station | started | Stage 1: Domain Model (OQ-4 decided at STEP 24: overweight stays unconfirmed, defined recovery action, no recalculation, no override) |
| 2026-11-23T08:54:03Z | 012-weighing-station | stage-complete | Domain Model → Technical Design (APPROVE MODEL; recommended decisions: surplus % of target, server re-reads scale at Quit, unreadable scale → plain quit, discard stored on ComponentAttempt (`overshoot_discarded` + end_net/end_surplus/end_unit), fixed OvershootRule in code, no new logging for recovery (a)) |
| 2026-11-23T08:55:58Z | 012-weighing-station | stage-complete | Technical Design → ADR Analysis (APPROVE DESIGN; new `overshoot.py` (OVERSHOOT_RULE, Surplus); quit re-reads the scale outside the transaction; evaluation `overshoot` / `surplusPercent`, quit `ended`, refusal detail surplus; migration 0005 with discard snapshot + check constraint; no new endpoint) |
| 2026-11-23T08:57:03Z | 012-weighing-station | stage-complete | ADR Analysis → Implement (APPROVE ADR; ADR-012 training overshoot rule fixed in code, no recalculation / override, discard on the attempt; accepted and indexed) |
| 2026-11-23T09:01:19Z | 012-weighing-station | stage-complete | Implement → Test (APPROVE IMPLEMENTATION; `overshoot.py`, discard on ComponentAttempt + migration 0005, quit re-read, evaluation `overshoot` / `surplusPercent`, quit `ended`, refusal detail surplus; surplus % computed in `overshoot.surplus_of` to avoid a circular import) |
| 2026-11-23T09:29:26Z | 012-weighing-station | completed | All 5 stages done (APPROVE TESTS); 475/475 Django tests (26 new), Playwright 49/50 (existing training-panel toggle race from bolt 011, fix assigned to bolt 013); story 007 complete; unit stays open for bolt 015 |
| 2026-11-23T10:22:15Z | 015-weighing-station | started | Stage 1: Domain Model |
| 2026-11-23T10:24:09Z | 015-weighing-station | stage-complete | Domain Model → Technical Design (APPROVE MODEL; completion in the last confirm's transaction, pending WriteBack created with it, elapsed session start → completion "M min S s", history = all records of the batch, API only) |
| 2026-11-23T10:35:24Z | 015-weighing-station | stage-complete | Technical Design → ADR Analysis (APPROVE DESIGN; new `completion.py` / `history.py`, completion + pending WriteBack in the last confirm's transaction, confirm JSON `completion`, `GET sessions/<id>/summary`, `GET batch-history/<batch_id>`, no migration) |
| 2026-11-23T10:39:21Z | 015-weighing-station | stage-complete | ADR Analysis → Implement (APPROVE ADR ALL, APPROVE ADR; ADR-013 completion in the last confirmation with the pending write-back, ADR-014 batch-history read; accepted and indexed) |

## Execution Summary

| Metric | Value |
|--------|-------|
| Original bolts planned | 5 |
| Current bolt count | 5 |
| Bolts completed | 4 |
| Bolts in progress | 1 |
| Bolts remaining | 1 |
| Replanning events | 0 |

## Notes

- Dummy APIs are training contracts, not the real OrgaTEX / device interfaces.
- OQ-4 (overshoot rule) was decided at workbook STEP 24 (2026-11-23T08:50:18Z) before bolt 012 started.
- 2026-11-20T09:30:26Z: bolt 006 complete. ADR-004 (seeded station identities) and ADR-005 (current operator in the server session) accepted and indexed. The sessions app and `SessionMiddleware` were enabled. Story 001's on-screen header is verified by Playwright in bolt 007.
- 2026-11-23T05:03:33Z: bolt 009 complete. ADR-008 (server is the single source of the weighing rules) and ADR-009 (one value at display resolution) accepted and indexed. Setting `WEIGHING_SCALE_THRESHOLD_KG` (default 3, env override). Bolt 010's confirm must call `rules.evaluate_reading` on the server's own scale re-read, store the evaluated net as actualWeight, and call `check_material_ready` (ADR-007). Story 005's Playwright check (OK disabled at 93.4 / 94.6) is in bolt 011.
- 2026-11-23T05:47:57Z: bolt 010 complete. ADR-010 (stored append-only attempts, derived component state) and ADR-011 (scale I/O outside the transaction, re-check under lock) accepted and indexed. Endpoints: `GET /current-session`, `GET …/progress`, `POST …/components/<seq>/activate|tare|quit|confirm`. After a confirm the first pending component in recipe order becomes active. Bolt 011 wires F1/F2/F4, the rail and resume; bolt 012 builds overshoot on `OUT_OF_TOLERANCE`.
- 2026-11-23T09:29:26Z: bolt 012 complete. ADR-012 (training overshoot rule fixed in code: no recalculation, no override, overshoot discard on the attempt) accepted and indexed. Migration 0005. Evaluation JSON gains `surplusPercent` / `overshoot`; quit JSON gains `ended`; the 409 `OUT_OF_TOLERANCE` detail gains the surplus. Bolt 013 shows these server texts and also fixes the training-panel failure-switch race found in the Playwright regression run (APPROVE TESTS, option 1).
