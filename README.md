# WeighingMS — Assisted Dyestuff Weighing Station

An assisted dyestuff and chemical weighing station application built for a textile/RMG dyeing facility (conceptually integrated with SETEX **OrgaTEX MES**). Developed step-by-step using the **specs.md AI-DLC (AI-Driven Development Lifecycle)** methodology for the *AI-DLC Enabled Engineering Capability Assessment*.

---

## Project Overview

In a dyehouse, manual weighing without live feedback or component-level traceability causes shade failures and unattributed rework. **WeighingMS** guides operators through every step of batch chemical preparation:

1. **Select Batch** — Retrieve released batches from the OrgaTEX batch queue (via scan or touch).
2. **Guided Weighing** — Automatically select the appropriate scale (`3 kg` precision scale for $\le 3\text{ kg}$, `32 kg` floor/heavy-duty scale for $> 3\text{ kg}$), track live dispensed weight against target and tolerance bands, handle overshoot scenarios, and enforce component progression.
3. **Confirm & Print** — Record full component-level traceability, post actual consumption back to OrgaTEX, and generate a batch weighing ticket.

> **Note:** External systems (OrgaTEX MES, weighing scales, barcode scanner, and ticket printer) are implemented as **Dummy APIs** for development, testing, and demonstration purposes.

---

## Tech Stack

- **Methodology & Spec Framework:** `specs.md` (AI-DLC flow with `memory-bank/` artifacts and human validation checkpoints)
- **Backend & Dummy APIs:** Python + Django (SQLite database)
- **Frontend:** HTML / CSS + Alpine.js (reproducing the industrial HMI operator terminal experience)
- **Testing:** Django test suite + Playwright (end-to-end workflow & failure scenario verification)

---

## Repository Structure

```text
weighingms/
├── .specsmd/                 # specs.md framework configuration & AI-DLC agents
├── memory-bank/              # AI-DLC lifecycle artifacts (standards, intents, units, bolts, operations)
├── src/                      # Application source code (Django backend, Dummy APIs, Alpine.js UI)
├── tests/                    # Unit & API integration tests
├── playwright/               # End-to-end Playwright test suite
├── FINAL-EVIDENCE.md         # Final requirement-to-evidence traceability matrix
└── README.md                 # Project documentation
```

*(Local source specifications under `docs/` and local environment/build artifacts are excluded from version control via `.gitignore`.)*

---

## Getting Started

### Prerequisites
- **Node.js** 18+ (for `specs.md` CLI/dashboard and Playwright)
- **Python** 3.10+ (for Django backend and Dummy APIs)

### Running the Application

1. **Install dependencies** (once scaffolded during Construction):
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   npm install
   ```

2. **Run database migrations & start the development server:**
   ```bash
   python manage.py migrate
   npm run dev
   ```

3. **View the `specs.md` AI-DLC Dashboard:**
   ```bash
   npx specsmd@latest dashboard
   ```

4. **Run Tests:**
   ```bash
   python manage.py test
   npx playwright test
   ```

---

## AI-DLC Workflow & Checkpoints

This repository follows the three-phase **specs.md AI-DLC** process without one-shot code generation:

- **Phase 1 — Inception:** Intent capture → Requirements elaboration → UI/UX prototype analysis → System Context → Capability Units → User Stories → Bolt Plan.
- **Phase 2 — Construction:** Step-by-step Bolt execution (`Plan → Human Review → Implement → Test → Human Review`) covering Dummy APIs, batch selection, live weighing, scale switching, tolerance enforcement, overshoot handling, OrgaTEX write-back, and ticket generation.
- **Phase 3 — Operations & Validation:** UI/UX prototype comparison, Playwright E2E and failure-mode testing, final `specs.md` audit, and `FINAL-EVIDENCE.md` verification.