---
work_package_id: WP02
title: CI wiring + CLAUDE.md/docs
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-005
tracker_refs: []
planning_base_branch: feat/playwright-ui-e2e-bootstrap
merge_target_branch: feat/playwright-ui-e2e-bootstrap
branch_strategy: Planning artifacts for this mission were generated on feat/playwright-ui-e2e-bootstrap. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/playwright-ui-e2e-bootstrap unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
agent: "claude"
shell_pid: "2227798"
history:
- 'Created by planner for #1008 tasks phase'
agent_profile: frontend-freddy
authoritative_surface: .github/workflows/
create_intent:
- .github/workflows/ui-e2e.yml
- docs/development/ui-e2e.md
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- .github/workflows/ui-e2e.yml
- CLAUDE.md
- docs/development/ui-e2e.md
- docs/development/3-2-page-inventory.yaml
role: implementer
tags: []
task_type: implement
---

# WP02 – CI wiring + CLAUDE.md/docs

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load` → `frontend-freddy` (Sonnet-5). Read `spec.md` (FR-004, FR-005, NFR-001) + `plan.md` (IC-02). **Depends on WP01** (the runnable `tests/ui/` test) — that must be approved/done first.

## Objective
Run WP01's e2e headless in CI (browser cached) as a scoped merge-gate job, and make the `CLAUDE.md` "Playwright proof" rule real + document how to extend.

## Changes
- **T005 — CI job (FR-004/FR-005/NFR-001)**: a **new scoped workflow** `.github/workflows/ui-e2e.yml` (or a job in the existing CI) that: installs the browser (`playwright install --with-deps chromium`, cached), runs `PWHEADLESS=1 uv run pytest tests/ui/ -q` **headless**, and **participates in the merge gate** (a red e2e blocks). Keep it bounded — ONE test, its own job, not a dependency bloating every unrelated shard. If the repo's aggregator/quality-gate needs the job registered to stay consistent, do that (mirror an existing scoped job).
- **T006 — make the rule real + docs (FR-005)**:
  - `CLAUDE.md`: change the aspirational "Never claim the frontend works without Playwright proof" note so it **links the runnable test path** (`tests/ui/test_dashboard_wp_modal.py`) — an agent can now run/extend it.
  - `docs/development/ui-e2e.md` (new): how to boot the synthetic fixture + write another e2e (copy-template). Register it in `docs/development/3-2-page-inventory.yaml` (regenerate, don't hand-edit: `PYTHONPATH=. uv run python scripts/docs/inventory_lockfile.py --write /tmp/inv.yaml && cp /tmp/inv.yaml docs/development/3-2-page-inventory.yaml`) + add `description:` frontmatter (50–180 chars).

## DoD
- The CI job runs `tests/ui/` headless with a cached browser + is wired into the merge gate; bounded (one test).
- `CLAUDE.md` links the real test path; `docs/development/ui-e2e.md` exists, inventory-registered, with `description` frontmatter.
- Docs gates green locally: `PYTHONPATH=. uv run python scripts/docs/inventory_lockfile.py --strict` + `description_length_check.py --strict`; `ruff`/`mypy` unaffected; no new suppressions.
- Terminology guard green (`pytest tests/architectural/test_no_legacy_terminology.py`) — the new doc is user-facing prose.

## Report back
The CI job (`if:`/trigger, browser-cache step, merge-gate wiring — paste the yaml); the `CLAUDE.md` edit (the rule → the path); the new doc + its inventory registration + `description`; docs-gate + terminology-guard output; lane commit SHA. If the docs-inventory or quality-gate registration can't be satisfied cleanly, STOP and report.

## Activity Log

- 2026-07-07T04:06:54Z – claude – shell_pid=2227798 – Assigned agent via action command
