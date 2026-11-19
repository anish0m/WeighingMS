# WeighingMS

Course project (Brain Station 23, AI-DLC Engineering Capability Assessment): an assisted dyestuff weighing station for a dyehouse, built strictly through the **specs.md AI-DLC** flow (Inception → Construction → Operations) with human checkpoints. The process artifact trail is graded as much as the working app.

## Where truth lives
- Process: `docs/provided/Workbook for claude.md` (STEP 0–35) + final submission in `docs/WeighingMS Project Instructions.txt`.
- Task plan: `docs/explanation/task_distribution.md`. Work through it in order. Task numbers (T001…) are the reference when the user names a task. After STEP 12, Claude fills its Appendix A (Bolt map) and rewrites Part C with exact Bolt commands.
- Business intent: `docs/provided/brief.md`. UI/interaction: `docs/provided/customize-weighing-station.html`. Course requirement: `docs/provided/Project Requirement.pdf`.
- Ignore `docs/provided/Workbook for Puku.md` (its Step 2.5 is Puku-only).
- NEVER edit anything in `docs/provided/`. The workbook's working copies are `docs/brief.md` and `docs/customize-weighing-station.html` (created in STEP 1).

## Tech stack (approved by the user; do not propose alternatives)
- Python 3.12 + Django + SQLite, virtualenv at `.venv/`: app and Dummy APIs
- Django templates + HTML/CSS + Alpine.js: UI reproducing the HMI prototype
- Django test runner (Python tests in `tests/`) + Playwright E2E (`playwright/`, `playwright.config.js` at root, report in `playwright-report/`)
- Node 24 / npm 11 on this machine: specs.md CLI, dashboard, Playwright
- Target layout (workbook FINAL SUBMISSION): `src/`, `tests/`, `playwright/`, `memory-bank/`, `.specsmd/`, `README.md`, `FINAL-EVIDENCE.md`

## Commands
No build tooling exists yet. It is created during Construction. These are the agreed commands that the Bolts must create. Verify them against `package.json` before quoting them as working:
```
npm run dev              # app at http://localhost:8000 via .venv/bin/python manage.py runserver
npm test                 # Django test suite
npx playwright test      # E2E; --headed for the recorded run
npx specsmd@latest install    # interactive, so the USER runs it (STEP 2)
npx specsmd@latest dashboard  # interactive, so the USER runs it (STEP 4, 32)
```
specs.md agents are slash commands: `/specsmd-master-agent`, `/specsmd-inception-agent`, `/specsmd-construction-agent`, `/specsmd-operations-agent`. They exist only after STEP 2, once Claude Code is restarted.

## Workflow rules
- IMPORTANT: Do one workbook step at a time. When it is done, stop and wait for the user's confirmation. Never skip a step, a checkpoint or a Bolt stage.
- At every AI-DLC gate (Intent, Requirements, System Context, Units, Stories, Bolt plan, each Bolt stage), stop and wait for the user's explicit `APPROVE …` message. Never self-approve.
- In Construction, execute only the next approved Bolt. Never "build the whole app".
- Do only what the workbook, brief and requirement PDF ask. Do not add unrequested features, files or refactors.
- If something is unclear: ask, record, decide, continue. Never invent requirements silently.
- When a workbook prompt is given, use its exact wording. Do not paraphrase it.
- End EVERY reply with a final line `Next step:` followed by what the user should do next (exact command/message to send, or which checkpoint is open).

## Domain rules that are easy to get wrong
- Dummy OrgaTEX / Scale / Scanner / Printer APIs are **training contracts**. Never present them as the real OrgaTEX interface. The brief's open questions (A-01…A-15) stay unresolved.
- The UI must fetch all scenario data from the Dummy APIs. Never put a hard-coded batch or recipe array in templates or JS.
- Scale selection: target ≤ 3 kg → 3 kg precision scale; > 3 kg → 32 kg floor scale. The threshold must be configurable.
- Tolerance is inclusive. Yellow RGB 94.0 g ± 0.5 g: 93.4 cannot confirm, 93.5/94.0/94.5 can, 94.6 cannot. Use `Decimal`, never float, for quantities (brief NFR-16).
- Overshoot is a human decision (STEP 24). Do not copy the prototype's recalculation. Propose options and stop.
- On confirm, record: actualWeight, operator, component, lot, container, tare, scale, timestamp.
- Seed scenario: batch B-24187 / SO-9931 / JET-04 / Teal 4C with five components (Blue RSPL, Red RB, Yellow RGB, Sodium Sulphate, Soda Ash), plus queued B-24188, B-24190, B-24191. Values come from the prototype's `components` array.

## Git
- IMPORTANT: Run read-only git only (`status`, `log`, `diff`, `check-ignore`). Never run `add`, `commit`, `push`, `branch`, `reset`, `checkout`, `stash`, or anything that touches GitHub. The user commits and pushes.
- The user's commit style is `step-NN: <title>`. Earlier commits use `init:` / `chore:`.

## After every completed step
1. Write `docs/explanation/steps/step-NN_<kebab-title>.md` (e.g. `step-04-5_define-the-tech-stack-standard.md`) in the format of `docs/explanation/steps/step-x_title.md`: one `## <filename>` block per changed file, each with `### changes` and `### reason`. Keep it concise.
2. Review the step's output against the workbook and sources, and fix any inaccuracy.
3. Report, then wait for the user to commit, push and confirm. Run `git status --short` first. If the step changed nothing outside `docs/`, say "nothing to commit" and only ask for confirmation.
4. End the report with a compaction recommendation (see below).

## Context compaction (`/compact`)
State survives compaction because it lives on disk: `memory-bank/` holds the artifacts and approvals, `docs/explanation/steps/` holds the change logs, and the task-list checkboxes show progress. So compact only at points where everything important is already written down.
- **Recommend compacting** (say `Recommended: /compact now`) after the user confirms the commit of:
  - STEP 4.5 (bootstrap done)
  - STEP 8 (UI analysis output is long)
  - STEP 12 (Inception complete)
  - each Construction step that ran one or more Bolts (STEP 16–27)
  - STEP 30
- **Recommend skipping it** (say `/compact not needed`) after the small steps: 0–4, 5–7, 9–11, 13–15, 31–35.
- **Never recommend compacting** mid-step, between a Bolt stage and its `APPROVE`, during the STEP 24 overshoot decision, or while an agent is waiting at a checkpoint. Unapproved in-flight reasoning would be lost.
- Always give the exact command to run, with the next task number filled in. Example:
  `/compact STEP 12 done and committed. Next: STEP 13, task T238. Keep: approved tech stack, all APPROVE decisions, Appendix A bolt map location.`
- After compaction, re-read `CLAUDE.md` and the next unchecked tasks in `docs/explanation/task_distribution.md` before acting.

## Evidence
- Put all evidence in `docs/evidence/` under the workbook's file names (e.g. `STEP-02-manifest.txt`, `STEP-08-ui-analysis/`).
- The user captures screenshots and videos (GNOME Print key → `~/Pictures/Screenshots/`, screencast → `~/Videos/Screencasts/*.webm`, converted with `ffmpeg`). Claude only writes text/JSON/MD evidence when the task list says so.

## Gotchas
- IMPORTANT: `docs/` is git-ignored (`/docs` in `.gitignore`) by design, and NO file under `docs/` will ever be on GitHub. The user sometimes removes that line temporarily so they can `@`-mention docs files in chat. Never treat that as a request to commit `docs/`, never suggest committing it, and never edit `.gitignore` for it. Evidence and step notes are submitted outside GitHub.
- The user may save screenshots under GNOME's default name (`Screenshot from <date>.png`). Rename them to the workbook evidence name immediately.
- `/playwright-report/` and `db.sqlite3` are git-ignored. The report must be copied to `docs/evidence/STEP-29-playwright-report/` for submission.
- The project folder was renamed from `AIDLC_EECA` to `WeighingMS`. Use paths relative to the root.
