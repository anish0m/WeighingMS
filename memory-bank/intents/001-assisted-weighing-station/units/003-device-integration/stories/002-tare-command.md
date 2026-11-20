---
id: 002-tare-command
unit: 003-device-integration
intent: 001-assisted-weighing-station
status: ready
priority: must
created: 2026-11-20T04:51:01Z
assigned_bolt: 004-device-integration
implemented: false
---

# Story: 002-tare-command

## User Story

**As an** operator
**I want** to zero the scale with the container on it
**So that** the reading is net of the container

## Requirements

- Supports FR-7 (owned by 005)
- IR-12 (brief)

## Acceptance Criteria

- [ ] **Given** a container on `scale-3kg`, **When** the tare command is sent, **Then** the Dummy net weight becomes 0.0 g
- [ ] **Given** the scale is disconnected, **When** tare is sent, **Then** a failure is returned and nothing is reported as tared

## UI/UX Impact

- View 2: Re-tare F2 result (rendered by 007)

## API Dependencies

- Consumes: Dummy Scale `POST /api/scales/:scaleId/tare`

## Test Expectations

- Django tests: tare success and failure

## Technical Notes

- None

## Dependencies

### Requires
- 001-dummy-integrations/005-dummy-scale-api

### Enables
- 005-weighing-station/003-tare-retare-and-quit

## Out of Scope

- None
