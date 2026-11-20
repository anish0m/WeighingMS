# Global Story Index

## Overview
- **Total stories**: 42
- **Generated**: 42
- **Last updated**: 2026-11-20T04:56:11Z

> Stories approved 2026-11-20T04:56:11Z (`APPROVE STORIES`, workbook STEP 11); status `ready`.

---

## Stories by Intent

### 001-assisted-weighing-station


#### 001-dummy-integrations (7)

- [x] **001-seed-training-scenario** (001-dummy-integrations): Seed the prototype training scenario - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/001-dummy-integrations/stories/001-seed-training-scenario.md` · DB-1, DB-2, DB-5, DB-10; OQ-5 (only B-24187 has a recipe); OQ-6 (B-24187 starts with all 5 components pending); OQ-7 (lot/container from seed)
- [x] **002-dummy-orgatex-batch-endpoints** (001-dummy-integrations): Dummy OrgaTEX serves batch queue and batch details - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/001-dummy-integrations/stories/002-dummy-orgatex-batch-endpoints.md` · DB-1, DB-10; Supports FR-1, FR-2, FR-21
- [x] **003-dummy-orgatex-recipe-endpoint** (001-dummy-integrations): Dummy OrgaTEX serves a batch's recipe - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/001-dummy-integrations/stories/003-dummy-orgatex-recipe-endpoint.md` · DB-2; OQ-5; Supports FR-3, FR-5, FR-6, FR-7, FR-10, FR-12
- [x] **004-dummy-orgatex-consumption-endpoint** (001-dummy-integrations): Dummy OrgaTEX accepts consumption write-back - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/001-dummy-integrations/stories/004-dummy-orgatex-consumption-endpoint.md` · DB-3; Supports FR-17
- [x] **005-dummy-scale-api** (001-dummy-integrations): Dummy Scale API with tare and simulate controls - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/001-dummy-integrations/stories/005-dummy-scale-api.md` · DB-5, DB-6, DB-7; Supports FR-7, FR-8, FR-9, FR-12, FR-14
- [x] **006-dummy-scanner-and-printer** (001-dummy-integrations): Dummy Scanner and Dummy Printer - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/001-dummy-integrations/stories/006-dummy-scanner-and-printer.md` · DB-8, DB-9; Supports FR-2, FR-4, FR-18
- [x] **007-dummy-failure-toggles** (001-dummy-integrations): Training failure toggles for every Dummy - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/001-dummy-integrations/stories/007-dummy-failure-toggles.md` · DB-4, DB-7, DB-8, DB-9; Supports FR-1c, FR-3d, FR-17d, FR-20

#### 002-orgatex-integration (3)

- [x] **001-read-batches-and-recipe** (002-orgatex-integration): Read queue, batch and recipe through the OrgaTEX adapter - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/002-orgatex-integration/stories/001-read-batches-and-recipe.md` · IR-07, IR-09 (brief); Supports FR-1, FR-2, FR-3, FR-21b; NFR-7
- [x] **002-post-consumption-idempotently** (002-orgatex-integration): Post actual consumption idempotently - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/002-orgatex-integration/stories/002-post-consumption-idempotently.md` · FR-17 (a, c); IR-05, IR-08 (brief)
- [x] **003-write-back-failure-and-retry** (002-orgatex-integration): Write-back failure is visible and retryable - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/002-orgatex-integration/stories/003-write-back-failure-and-retry.md` · FR-17 (b, d); NFR-7; IR-09 (brief)

#### 003-device-integration (5)

- [x] **001-read-live-scale-weight** (003-device-integration): Read live net weight from a named scale - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/003-device-integration/stories/001-read-live-scale-weight.md` · FR-9; NFR-1 (≤ 200 ms); IR-10 (brief)
- [x] **002-tare-command** (003-device-integration): Send the tare command to the selected scale - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/003-device-integration/stories/002-tare-command.md` · Supports FR-7 (owned by 005); IR-12 (brief)
- [x] **003-scanner-input** (003-device-integration): Receive scanned codes from the scanner - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/003-device-integration/stories/003-scanner-input.md` · Supports FR-2, FR-4; FR-20 (b); IR-15 (brief)
- [x] **004-printer-adapter** (003-device-integration): Send tickets to the printer - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/003-device-integration/stories/004-printer-adapter.md` · Supports FR-18; FR-20 (c); IR-16 (brief)
- [x] **005-device-status-and-fail-safe** (003-device-integration): Device status and fail-safe on failure - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/003-device-integration/stories/005-device-status-and-fail-safe.md` · FR-20 (a, d); NFR-7; IR-13, IR-18 (brief)

#### 004-batch-recipe-management (5)

- [x] **001-view-batch-queue** (004-batch-recipe-management): See the batch queue released for the station - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/004-batch-recipe-management/stories/001-view-batch-queue.md` · FR-1; brief FR-01, BR-01, IR-01
- [x] **002-select-batch** (004-batch-recipe-management): Select a batch by scan or touch - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/004-batch-recipe-management/stories/002-select-batch.md` · FR-2; OQ-5; brief FR-02–FR-04, BR-02, BR-03, AC-01
- [x] **003-load-read-only-recipe** (004-batch-recipe-management): Load the batch's recipe read-only - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/004-batch-recipe-management/stories/003-load-read-only-recipe.md` · FR-3; NFR-2 (≤ 3 s); C-01; brief FR-05, FR-06, BR-04, IR-02
- [x] **004-verify-dyestuff-identity** (004-batch-recipe-management): Verify the dyestuff by scanning it - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/004-batch-recipe-management/stories/004-verify-dyestuff-identity.md` · FR-4; OQ-8; brief FR-09, BR-10, IR-15
- [x] **005-show-lot-and-container** (004-batch-recipe-management): Show lot, container and tare of the active component - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/004-batch-recipe-management/stories/005-show-lot-and-container.md` · FR-5, FR-6; OQ-7; brief FR-10, BR-11

#### 005-weighing-station (11)

- [x] **001-identify-operator** (005-weighing-station): Identify the operator at session start - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/005-weighing-station/stories/001-identify-operator.md` · FR-19 (a); OQ-3; brief FR-34, BR-14
- [x] **002-select-scale-automatically** (005-weighing-station): Select the scale automatically from the target - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/005-weighing-station/stories/002-select-scale-automatically.md` · FR-8; NFR-13; brief FR-07, BR-05, AC-02, A-06
- [x] **003-tare-retare-and-quit** (005-weighing-station): Tare, re-tare and quit a component attempt - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/005-weighing-station/stories/003-tare-retare-and-quit.md` · FR-7; FR-13 (e); brief FR-11, IR-12
- [x] **004-target-and-remaining** (005-weighing-station): Show target and remaining quantity - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/005-weighing-station/stories/004-target-and-remaining.md` · FR-10, FR-11; brief FR-14
- [x] **005-evaluate-inclusive-tolerance** (005-weighing-station): Evaluate the weight against the inclusive tolerance - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/005-weighing-station/stories/005-evaluate-inclusive-tolerance.md` · FR-12; brief FR-15–FR-17, BR-07, BR-09, A-07
- [x] **006-confirm-weighing** (005-weighing-station): Confirm a weighing and record it - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/005-weighing-station/stories/006-confirm-weighing.md` · FR-13 (a–d); NFR-5, NFR-12; brief FR-18, FR-19, FR-25, DR-02, AC-04
- [x] **007-handle-overshoot** (005-weighing-station): Handle overshoot (rule decided at STEP 24) - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/005-weighing-station/stories/007-handle-overshoot.md` · FR-14; OQ-4 (open); NFR-4; brief FR-20–FR-24, BR-08, BR-13, AC-05, AC-06, A-08
- [x] **008-progress-components** (005-weighing-station): Progress through components in recipe order - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/005-weighing-station/stories/008-progress-components.md` · FR-15; brief FR-06, §6.2
- [x] **009-complete-batch** (005-weighing-station): Complete the batch and trigger write-back - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/005-weighing-station/stories/009-complete-batch.md` · FR-16; brief §6.2, FR-25
- [x] **010-resume-after-reload** (005-weighing-station): Resume an in-progress batch after reload - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/005-weighing-station/stories/010-resume-after-reload.md` · NFR-6, NFR-5; brief NFR-06
- [x] **011-retrieve-batch-history** (005-weighing-station): Retrieve a batch's weighing records - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/005-weighing-station/stories/011-retrieve-batch-history.md` · FR-19 (b, c); brief FR-29, BR-19, AC-07

#### 006-ticket-printing (2)

- [x] **001-print-weighing-ticket** (006-ticket-printing): Print the weighing ticket for a completed batch - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/006-ticket-printing/stories/001-print-weighing-ticket.md` · FR-18 (a, b); brief FR-27, BR-15, IR-16, AC-10, A-04
- [x] **002-reprint-and-print-failure** (006-ticket-printing): Reprint and handle printer failure - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/006-ticket-printing/stories/002-reprint-and-print-failure.md` · FR-18 (c, d); FR-20 (c); brief FR-28

#### 007-assisted-weighing-station-ui (9)

- [x] **001-terminal-shell-and-status-bar** (007-assisted-weighing-station-ui): Terminal shell: header, clock and device status bar - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/007-assisted-weighing-station-ui/stories/001-terminal-shell-and-status-bar.md` · FR-20 (rendering); FR-19 (header operator); NFR-8, NFR-10, NFR-11
- [x] **002-select-batch-view** (007-assisted-weighing-station-ui): View 1: Select batch - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/007-assisted-weighing-station-ui/stories/002-select-batch-view.md` · FR-1, FR-2 (rendering); FR-21; NFR-8, NFR-10
- [x] **003-weigh-view-recipe-rail-and-header** (007-assisted-weighing-station-ui): View 2: recipe rail, component header and dyestuff scan step - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/007-assisted-weighing-station-ui/stories/003-weigh-view-recipe-rail-and-header.md` · FR-3, FR-4, FR-5, FR-6, FR-15 (rendering); NFR-8, NFR-10
- [x] **004-weigh-view-live-readout-and-tolerance** (007-assisted-weighing-station-ui): View 2: live readout, progress bar and tolerance band - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/007-assisted-weighing-station-ui/stories/004-weigh-view-live-readout-and-tolerance.md` · FR-8, FR-9, FR-10, FR-11, FR-12 (rendering); NFR-1, NFR-10
- [x] **005-weigh-view-actions-and-function-keys** (007-assisted-weighing-station-ui): View 2: Confirm, Re-tare, Quit and function keys - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/007-assisted-weighing-station-ui/stories/005-weigh-view-actions-and-function-keys.md` · FR-7, FR-13 (rendering); NFR-8, NFR-9
- [x] **006-weigh-view-surplus-panel-and-override** (007-assisted-weighing-station-ui): View 2: surplus panel and supervisor override - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/007-assisted-weighing-station-ui/stories/006-weigh-view-surplus-panel-and-override.md` · FR-14 (rendering); OQ-4; NFR-4
- [x] **007-confirm-and-print-view** (007-assisted-weighing-station-ui): View 3: Confirm & print - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/007-assisted-weighing-station-ui/stories/007-confirm-and-print-view.md` · FR-16, FR-17, FR-18 (rendering); NFR-9, NFR-10
- [x] **008-training-simulation-panel** (007-assisted-weighing-station-ui): Training panel: simulate scale and failures - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/007-assisted-weighing-station-ui/stories/008-training-simulation-panel.md` · DB-6, DB-4, DB-7, DB-8, DB-9; Prototype "How to run this in the meeting" controls
- [x] **009-no-hard-coded-scenario-data** (007-assisted-weighing-station-ui): All UI data comes from the APIs - Must - ✅ GENERATED  
  `intents/001-assisted-weighing-station/units/007-assisted-weighing-station-ui/stories/009-no-hard-coded-scenario-data.md` · FR-21 (a, b); IR-07 (brief)


---

## Stories by Status

- **Planned**: 0
- **Generated**: 42
- **In Progress**: 0
- **Completed**: 0
