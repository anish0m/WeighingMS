# Data Stack

## Overview
Database and data persistence decisions for this project.

WeighingMS persists everything in one local SQLite database, accessed through the Django ORM. This covers WeighingMS-owned records (weighing records, sessions, audit) and the training-time state of the Dummy integrations (dummy OrgaTEX batches/recipes/consumption, scale readings, printed tickets).

Status: **Approved** by the user on 2026-11-19 (STEP 4.5, `APPROVE DATA STACK`).

## Database
**SQLite** (Django default backend). The file is `db.sqlite3`, which is git-ignored.

Rationale:
- The brief scopes V1 to one station at one site (A-11). Data volume is a handful of batches with a few components each, well within SQLite's range.
- No database server to install or run, so the app and its Dummy APIs work fully offline (BR-16, NFR-03) and tests get a fresh database automatically.
- SQLite supports durable transactional writes, which serves "a confirmed weighing survives immediate power loss" (NFR-05) at training scale.

## ORM / Database Client
**Django ORM**, with Django migrations for all schema changes.

Rationale:
- It is integrated with the approved Django framework: models, migrations, the test-database lifecycle and admin come built in.
- Quantities use `models.DecimalField` (brief data model: `decimal(12,4)`, i.e. `max_digits=12, decimal_places=4`) and map to Python `Decimal`, never `float` (NFR-16).
- Timestamps use timezone-aware `DateTimeField` (`USE_TZ = True`), stored in UTC.
- Schema changes go only through `makemigrations` and `migrate`. Never edit the database by hand.

## Decision Relationships
- SQLite + Django ORM keep persistence inside the single Django process chosen in the tech stack. There is no external service.
- The Dummy integrations store their own state in the same database but in their own Django app(s) and tables, separate from WeighingMS domain tables. This preserves the integration boundary (IR-07), so a real OrgaTEX or scale integration would replace the dummy app without touching the domain data.
- Training seed data (batch B-24187 and the queued batches, taken from the prototype) is loaded through Django, not hard-coded in UI code. The exact loading mechanism is decided in the seed-data Bolt.
