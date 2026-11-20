---
bolt: 006-weighing-station
created: 2026-11-20T09:20:12Z
status: accepted
superseded_by: null
---

# ADR-004: Station identities are seeded Operator / Supervisor entities, not `django.contrib.auth` users

## Context

Every weighing must be attributable to an operator (FR-19, brief FR-34, BR-14). A supervisor must authenticate to authorise an override (NFR-4, brief FR-35/36). The brief leaves the method open (A-09, Q37). The approved training answer (OQ-3) is:

- the operator is **chosen from a seeded list, with no password** (seed: R. Karim · Shift A);
- the supervisor gives a **seeded ID + PIN** and a reason, which is recorded.

The tech-stack standard names Django's `django.contrib.auth` as the "default candidate" if identification is needed. NFR-4 also requires that roles share no credentials.

## Decision

1. The `weighing` app owns two seed-only entities:
   - `Operator` (`operator_id`, `name`, `shift`, `active`);
   - `Supervisor` (`supervisor_id`, `name`, `pin_hash`, `active`).
   They are not Django `User` rows, have no login, and are not registered in the Django admin.
2. The data migration `weighing/0002_seed_identities` seeds the training identities:
   - `OP-01` R. Karim · Shift A;
   - `SUP-01` "Training Supervisor" with PIN `2468`.
   Both are marked as training data. The app has no create, edit or delete path for identities.
3. The supervisor PIN is stored only as a hash made with Django's password hasher (`make_password`, PBKDF2) and checked with `check_password`. A wrong ID and a wrong PIN give the same refusal ("Supervisor ID or PIN incorrect"). The PIN is never logged or returned.
4. Only the hashing utilities `django.contrib.auth.hashers` are used from `contrib.auth`.

## Rationale

- OQ-3 asks for a **choice without a password** for operators. A `contrib.auth` user always has a password and a login flow, which the requirements don't ask for and which the prototype doesn't show.
- **Separate tables** make "no shared credentials between roles" (NFR-4) structural: an operator ID can never pass supervisor verification.
- Seeding through a migration matches the data-stack standard: seed data loaded through Django, never hard-coded in the UI. It also gives the test database the same identities.
- Using Django's hasher avoids inventing any cryptography.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| `django.contrib.auth` users + groups "operator" / "supervisor" | Standard Django; admin UI; permission system | Passwords and login for operators (against OQ-3); one credential model for both roles; adds auth/admin surface nobody asked for | Doesn't match OQ-3; more than required |
| Hard-coded identities in settings or code | No tables | The PIN sits in the code; records can't reference an identity row | Insecure; not traceable |
| A Dummy "directory" API | Looks like a real FCI directory | Invents an integration the brief doesn't define (A-09 is open); a training contract presented as real | Out of scope; misleading |

## Consequences

### Positive

- The operator flow matches OQ-3 and the prototype exactly: pick a name, and the header shows it.
- Supervisor verification is ready for bolt 012's override without further design.
- Weighing records can hold a foreign key to the operator row (FR-19b).

### Negative

- This departs from the tech-stack's default candidate. Anyone expecting Django users will find none.
- New identities need a new migration (acceptable for a seeded training station).

### Risks

- **The training PIN `2468` is published in the repository and the README.** Mitigation: it is documented as training data only. A real deployment replaces this with the FCI directory (A-09), which is a new decision.
- **No lockout after repeated wrong PINs.** Mitigation: out of scope for training; failed attempts are logged at WARNING.

## Related

- **Stories**: 005-weighing-station/001-identify-operator; later 005-weighing-station/007-handle-overshoot (override) and 006-confirm-weighing (operator on the record)
- **Standards**: `tech-stack.md` "Authentication" could note this ADR as the chosen approach.
- **Previous ADRs**: ADR-002 (endpoints under `/station/api/`)
