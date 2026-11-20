---
id: 010-resume-after-reload
unit: 005-weighing-station
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 010-weighing-station
implemented: false
---

# Story: 010-resume-after-reload

## User Story

**As an** operator
**I want** the batch to reopen where I was after a reload or restart
**So that** confirmed work is never lost or repeated

## Requirements

- NFR-6, NFR-5
- brief NFR-06

## Acceptance Criteria

- [ ] **Given** 2 of 5 components confirmed, **When** the page is reloaded, **Then** B-24187 reopens at the in-progress component with both confirmations kept
- [ ] **Given** the server restarts mid-batch, **When** the station is opened, **Then** the same state is restored from the database

## UI/UX Impact

- View 2 restored state after reload

## API Dependencies

- Provides: WeighingMS weighing-session API for the UI (shape fixed in Bolt design)

## Test Expectations

- Django test: state rebuilt from DB
- Playwright: reload mid-batch

## Technical Notes

- None

## Dependencies

### Requires
- 006-confirm-weighing

### Enables
- None

## Out of Scope

- None
