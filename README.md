# WeighingMS — Assisted Dyestuff Weighing Station

An assisted dyestuff and chemical weighing station application built for a textile/RMG dyeing facility (conceptually integrated with SETEX **OrgaTEX MES**). Developed step-by-step using the **specs.md AI-DLC (AI-Driven Development Lifecycle)** methodology for the *AI-DLC Enabled Engineering Capability Assessment*.

---

## Project Overview

In a dyehouse, manual weighing without live feedback or component-level traceability causes shade failures and unattributed rework. **WeighingMS** guides operators through every step of batch chemical preparation:

1. **Select Batch** — Retrieve released batches from the OrgaTEX batch queue (via scan or touch).
2. **Guided Weighing** — Automatically select the appropriate scale (`3 kg` precision scale for $\le 3\text{ kg}$, `32 kg` floor/heavy-duty scale for $> 3\text{ kg}$), track live dispensed weight against target and tolerance bands, handle overshoot scenarios, and enforce component progression.
3. **Confirm & Print** — Record full component-level traceability, post actual consumption back to OrgaTEX, and generate a batch weighing ticket.

> **Note:** External systems (OrgaTEX MES, weighing scales, barcode scanner, and ticket printer) are implemented as **Dummy APIs** for development, testing, and demonstration purposes. The Dummy APIs are **training contracts** defined by this project. They are not the real OrgaTEX, scale, scanner or printer interfaces.

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
- **Python** 3.12 (for the Django backend and Dummy APIs)
- **Node.js** 24 with npm (for the `specs.md` CLI/dashboard and Playwright)

### Running the Application

1. **Install dependencies:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   npm install
   npx playwright install chromium
   ```

2. **Create the database and seed the training scenario** (batch B-24187 with recipe Teal 4C, queued batches B-24188, B-24190 and B-24191, and the two Dummy scales):
   ```bash
   python manage.py migrate
   python manage.py seed_training
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```
   Open http://localhost:8000.
   - **Choose the operator:** pick **R. Karim · Shift A** (operator `OP-01`). The batch queue appears only after an operator is chosen.
   - **Training panel:** the **TRAINING ONLY** panel below the terminal drives the Dummy devices. You can simulate dispensing, set an exact weight, simulate a scan, and switch failure modes.

4. **View the `specs.md` AI-DLC Dashboard:**
   ```bash
   npx specsmd@latest dashboard
   ```

5. **Run Tests:**
   ```bash
   npm test                 # Django test suite (.venv/bin/python manage.py test tests)
   npx playwright test      # E2E; starts its own server on port 8001 with a separate database
   ```

---

## AI-DLC Workflow & Checkpoints

This repository follows the three-phase **specs.md AI-DLC** process without one-shot code generation:

- **Phase 1 — Inception:** Intent capture → Requirements elaboration → UI/UX prototype analysis → System Context → Capability Units → User Stories → Bolt Plan.
- **Phase 2 — Construction:** Step-by-step Bolt execution (`Plan → Human Review → Implement → Test → Human Review`) covering Dummy APIs, batch selection, live weighing, scale switching, tolerance enforcement, overshoot handling, OrgaTEX write-back, and ticket generation.
- **Phase 3 — Operations & Validation:** UI/UX prototype comparison, Playwright E2E and failure-mode testing, final `specs.md` audit, and `FINAL-EVIDENCE.md` verification.