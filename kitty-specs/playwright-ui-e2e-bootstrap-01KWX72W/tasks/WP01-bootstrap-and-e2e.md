---
work_package_id: WP01
title: Framework bootstrap + synthetic fixture + the kanban→modal e2e
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-006
tracker_refs: []
planning_base_branch: feat/playwright-ui-e2e-bootstrap
merge_target_branch: feat/playwright-ui-e2e-bootstrap
branch_strategy: Planning artifacts for this mission were generated on feat/playwright-ui-e2e-bootstrap. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/playwright-ui-e2e-bootstrap unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
agent: "claude"
shell_pid: "2150133"
history:
- 'Created by planner for #1008 tasks phase'
agent_profile: frontend-freddy
authoritative_surface: tests/ui/
create_intent:
- tests/ui/conftest.py
- tests/ui/test_dashboard_wp_modal.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- pyproject.toml
- tests/ui/conftest.py
- tests/ui/test_dashboard_wp_modal.py
role: implementer
tags: []
task_type: implement
---

# WP01 – Framework bootstrap + synthetic fixture + the kanban→modal e2e

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load` → `frontend-freddy` (browser-side implementer, Sonnet-5). Read `spec.md` (FR-001/002/003/006, C-001/002/003) + `plan.md` (IC-01). **Never claim the frontend works without Playwright proof — this WP makes that real.**

## Objective
Install `pytest-playwright` + build a hermetic synthetic-mission fixture + the ONE e2e that clicks a WP card and asserts the modal renders the canonical agent identity + prompt — non-vacuous against the #970 regression.

## Changes
- **T001 — bootstrap (FR-001)**: add `pytest-playwright` as a **dev/test dependency** in `pyproject.toml` (respect `test_pyproject_shape.py` + shared-package-boundary gates; version bump + CHANGELOG only if `__init__.py` changes — it should NOT). Chromium via `playwright install chromium` at test/CI time (cached), **never committed**. Minimal Playwright config (headless).
- **T002 — synthetic fixture + in-thread boot (FR-003)** in `tests/ui/conftest.py`:
  - Materialize a temp project root with synthetic mission(s)/WP(s) whose frontmatter uses the **dict** form `agent: {tool: "...", model: "..."}` + `agent_profile: "..."` + `role: "..."` — the form `dashboard/scanner.py::_process_wp_file` (`:851-869`) decomposes into DOM keys `agent`/`model`/`agent_profile`/`role`. ⚠️ Do NOT use the dominant colon-string `agent: 'tool:model:profile:role'` — the scanner does NOT split it (blank `model` → vacuous/blank test).
  - Boot the dashboard **in-thread** via `start_dashboard(project_dir=<temp root>, port=find_free_port(), background_process=False)` (`dashboard/server.py:110`). ⚠️ NOT `cli/commands/dashboard.py` / `ensure_dashboard_running` (a detached-child singleton that kills siblings on the shared port range → xdist flake). Tear it down with the pytest process.
- **T003 — the e2e (FR-002)** in `tests/ui/test_dashboard_wp_modal.py`: navigate to the booted URL → wait for the kanban → **assert `#prompt-modal` is HIDDEN** → **click a WP card** → wait for the modal → assert — **SCOPED to the modal container (`#prompt-modal` / `.agent-identity-section` / `#modal-prompt-meta`), NOT page-global and NOT `.card .badge`** — that the modal renders `agent`/`model`/`agent_profile`/`role` (populated, matching the fixture) + `prompt_markdown`. ⚠️ `agent`/`agent_profile`/`role` ALSO render as card badges (`dashboard.js:514-516`) before the click, so a page-global `get_by_text` is FAKEABLE (only `model` is modal-exclusive) — scope every assertion to the modal locator. Explicit Playwright waits (no `sleep`).
- **T004 — non-vacuity (FR-006, RENDER-path)**: prove the guard bites the **modal render** — temporarily delete the identity block in `showPromptModal` (`dashboard.js:628-631`) with the **fixture data left INTACT** → the modal-scoped assertion **fails cleanly**; revert → green. A throwaway demonstration (paste both as evidence, NOT committed). ⚠️ Do NOT prove via blanking the scanner/fixture data — that reds the always-visible card badge too and proves nothing about the modal render. (No "detail-not-fetched" mode exists — the modal reuses the card's `task` object.)

## DoD
- `pytest-playwright` dev dep + Chromium cached (not committed); no `__init__.py` change (no version bump needed).
- Fixture uses the dict-form frontmatter; boots in-thread on an ephemeral port, headless, hermetic.
- `PWHEADLESS=1 uv run pytest tests/ui/ -q` green; the modal assertions are **scoped to the modal container** (not page-global / card-badge) + check `#prompt-modal` hidden pre-click.
- Non-vacuity (**render-path**): deleting the `showPromptModal` identity block (data intact) reds the modal-scoped test; revert → green (paste both) — NOT a scanner/data-blank.
- `ruff` + `mypy --strict` clean on the new files; no new suppressions; **no COMMITTED dashboard source change** (the T004 render-path mutation is a reverted throwaway, not committed).

## Report back
The dep addition (pyproject diff); the fixture (dict-form frontmatter + in-thread `start_dashboard` boot — paste both); the e2e's click + canonical-field assertions; the #970 non-vacuity proof (red + green); pytest counts; ruff+mypy; lane commit SHA. If the in-thread `start_dashboard` seam can't be driven hermetically, STOP and report (do NOT fall back to the CLI singleton).

## Activity Log

- 2026-07-07T03:24:21Z – claude – shell_pid=2150133 – Assigned agent via action command
- 2026-07-07T04:05:20Z – claude – shell_pid=2150133 – Moved to for_review
- 2026-07-07T04:06:24Z – user – shell_pid=2150133 – Moved to approved
