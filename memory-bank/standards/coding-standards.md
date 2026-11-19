# Coding Standards

## Overview
Code style and quality standards for this project.

These rules apply to all AI-generated and human-written code in WeighingMS (Python/Django, Django templates, Alpine.js, Playwright tests). They build on `standards/tech-stack.md` and `standards/data-stack.md`.

Status: **Approved** by the user on 2026-11-19 (STEP 4.5, `APPROVE CODING STANDARDS`).

## Code Formatting
- **Python**: **Ruff formatter** (Black-compatible) with default settings: 4-space indent, double quotes, line length 88. Ruff is a dev dependency in `requirements.txt` and is configured in `pyproject.toml`.
- **JavaScript (Alpine.js, Playwright)**: 2-space indent, single quotes, semicolons. No formatter tooling; keep the files small and consistent by hand.
- **Templates/CSS**: 2-space indent. CSS custom properties (tokens) follow the prototype's names (`--hmi-bg`, `--ok`, `--warn`, `--over`, …).

## Linting Rules
- **Python**: **Ruff** (`ruff check`) with default rules plus import sorting (`I`). Before each Bolt's Test stage, `ruff check` and `ruff format --check` must pass.
- No `print()` in application code. Use logging.
- No commented-out code and no unused imports.
- Type hints on public functions in domain/services modules. Not required in Django views, tests or migrations.

## Naming Conventions
| Element | Convention | Example |
|---------|------------|---------|
| Python variables/functions | snake_case | `evaluate_tolerance`, `actual_qty` |
| Python classes / Django models | PascalCase | `WeighingRecord`, `ScaleReading` |
| Constants | UPPER_SNAKE | `PRECISION_SCALE_MAX_KG` |
| Python modules | snake_case | `tolerance.py` |
| Django apps | short lowercase | `weighing`, `dummy_orgatex` |
| API URL paths | lowercase, plural nouns, kebab-case | `/api/batches/<batch_id>/recipe` |
| JSON keys | camelCase | `targetQty`, `actualWeight` |
| JS variables/functions | camelCase | `currentWeight`, `confirmComponent` |
| Templates | snake_case `.html` | `weigh.html` |
| Tests | `test_<behaviour>` | `test_below_tolerance_cannot_confirm` |

- Domain terms follow the brief's glossary: Batch, Recipe, Component, Tare, Tolerance, Surplus, Override, Lot, Precision scale, Floor scale.
- Boolean names read as questions: `is_within_tolerance`, `can_confirm`.

## File & Folder Organization
- **Django project and apps under `src/`**, split by responsibility (the final app list comes from the approved Units):
  - WeighingMS domain apps hold business rules (tolerance, scale selection, progression, records).
  - Dummy integration apps (`dummy_*`) hold only training-contract endpoints and their state.
- Business rules live in plain Python service modules (e.g. `services.py`), not in views or templates. Views stay thin: parse request → call service → return response.
- WeighingMS code reaches external systems (Dummy OrgaTEX, Scale, Scanner, Printer) **only through one client/adapter module per integration** that calls the HTTP API. It never imports dummy app models directly (IR-07).
- Static assets (Alpine.js, CSS, JS) live in the app's `static/`. Templates live in the app's `templates/<app>/`.
- **Tests**: Python tests in top-level `tests/` mirroring the app names (`tests/weighing/test_tolerance.py`). E2E tests in `playwright/`.

## Testing Strategy
- **Unit tests** (Django `SimpleTestCase`/`TestCase`): every business rule, especially tolerance boundaries (e.g. 93.4 / 93.5 / 94.0 / 94.5 / 94.6 g for 94.0 ± 0.5 g), scale selection at and around 3 kg, component progression and batch completion.
- **API tests** (Django test client): every Dummy API endpoint, covering the success response plus the defined failure behaviour (unavailable, not found, invalid input).
- **E2E tests** (Playwright): the full workbook scenario (select B-24187 → five components → write-back → ticket) and the failure scenarios. E2E runs against the real Dummy APIs, with no mocks.
- **Mocks**: only at integration boundaries in unit tests, never for domain logic.
- **Structure**: Arrange–Act–Assert. Each test checks one behaviour, and its name states that behaviour.
- **Coverage**: no percentage target. Every approved acceptance criterion must have at least one automated test.
- **Gate**: a Bolt's Test stage passes only when `npm test` passes completely (plus `npx playwright test` once E2E exists).

## Error Handling Patterns
- Quantities are always `decimal.Decimal`, built from strings (`Decimal("94.0")`), never from floats. Weights arriving from JSON are parsed as strings or decimals. Comparisons happen in `Decimal`.
- API errors return a proper HTTP status with the JSON body `{"error": {"code": "SCALE_UNAVAILABLE", "message": "..."}}`. Never return `200` for a failure.
- Integration failures (scale, scanner, printer, OrgaTEX) must fail **safe**: confirmation is blocked or the action is reported as not done. They are never silently treated as success.
- Validate input at the boundary (views/serializers) and raise domain exceptions from services. Views map those exceptions to HTTP errors.
- Never catch a bare `except:`. Catch specific exceptions.

## Logging Standards
- Use Python's `logging` with a module logger (`logger = logging.getLogger(__name__)`).
- Integration calls log failures at `WARNING`/`ERROR` with the endpoint, status and batch/component ID, enough to diagnose without OrgaTEX-side access (IR-09).
- Confirmations, overrides and write-backs log at `INFO`. Never log secrets.
