---
unit: 006-ticket-printing
intent: 001-assisted-weighing-station
phase: inception
status: ready
created: 2026-11-20T04:22:15Z
updated: 2026-11-20T04:26:59Z
---

# Unit Brief: Ticket & Printing

## Purpose

Produce the printed evidence of a completed batch: build the weighing ticket from the confirmed records, send it to the (Dummy) printer, provide a preview, mark reprints, and report print failures so the ticket can be printed again.

## Scope

### In Scope
- Ticket content per the prototype: "FCI DYEING — WEIGHING TICKET", batch, order, machine, shade, date/time, operator, per component name/target/actual/unit, "ALL WITHIN TOLERANCE" summary, batch barcode.
- Print, preview, reprint marked "REPRINT", print log.
- Printer failure: nothing marked printed; print again later.

### Out of Scope
- Printer I/O (003); batch completion (005); the Confirm & print screen (007).
- Configurable layout beyond the prototype (label content is unconfirmed, A-04 / Q18).

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-18 | Generate ticket with all listed fields; Dummy Printer stores it; second print "REPRINT"; failure shown and retry later; "Next batch" (F3) returns to queue | Must |

---

## Domain Concepts

### Key Entities
| Entity | Description | Attributes |
|--------|-------------|------------|
| Ticket | Content for one batch | batch, lines, summary, barcode, generated_at |
| PrintJob | One print attempt | ticket, is_reprint, result, printed_at |

### Key Operations
| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| build_ticket | Ticket from records | completed session | Ticket |
| print_ticket | Print or reprint | batch | printed / failed |
| preview | Show ticket | batch | ticket content |

---

## Story Summary

Stories are created at STEP 11 (estimate ~2).

---

## Dependencies

### Depends On
| Unit | Reason |
|------|--------|
| 005-weighing-station | Completed batch and records |
| 003-device-integration | Printer adapter |

### Depended By
| Unit | Reason |
|------|--------|
| 007-assisted-weighing-station-ui | Print ticket / preview on view 3 |

### External Dependencies
| System | Purpose | Risk |
|--------|---------|------|
| Ticket printer (real, future) | Physical ticket | Low (A-04) |

---

## Technical Context

### Suggested Technology
Django app (e.g. `tickets`) with a plain-Python ticket builder.

### Integration Points
| Integration | Type | Protocol |
|-------------|------|----------|
| 003 printer adapter | Python call | – |
| 007 UI | API | HTTP JSON |

### Data Storage
| Data | Type | Volume | Retention |
|------|------|--------|-----------|
| Print jobs | SQLite | Few per batch | Kept |

---

## Constraints

- Printing never changes the completed batch or its records.
- Ticket values come from records (Decimal), not recomputed.

---

## Success Criteria

### Functional
- [ ] Printing B-24187 produces a ticket with all fields and confirmed actuals
- [ ] Second print is marked "REPRINT"; printer error reported, later print succeeds

### Quality
- [ ] Every approved acceptance criterion has an automated test

---

## Bolt Suggestions

| Bolt | Type | Objective |
|------|------|-----------|
| ticket-printing-1 | Simple | Ticket build, print, reprint, failure (STEP 27) |
