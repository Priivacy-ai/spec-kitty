---
work_package_id: WP01
title: Local pre-PR parity — lock-parity check + residual runner + docs
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
tracker_refs: []
planning_base_branch: feat/ci-delivery-topology
merge_target_branch: feat/ci-delivery-topology
branch_strategy: Planning artifacts for this mission were generated on feat/ci-delivery-topology. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-delivery-topology unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
agent: "claude"
shell_pid: "2752881"
history:
- 'Created by planner for #2283 Phase-3 tasks phase'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- tests/specify_cli/cli/commands/test_test_env_check.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/_test_env_check.py
- src/specify_cli/cli/commands/review/__init__.py
- src/specify_cli/cli/commands/review/ERROR_CODES.md
- docs/guides/review-gates.md
- tests/specify_cli/cli/commands/test_test_env_check.py
role: implementer
tags: []
task_type: implement
---

# WP01 – Local pre-PR parity: lock-parity check + residual runner + docs

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load` → `python-pedro` (implementer, Sonnet-5). Read `spec.md` (FR-001/002/003, NFR-001/002, C-001/003/004) + `plan.md` (IC-01). Study `_test_env_check.py:21-33` (`assert_pytest_available`), `review/__init__.py:307` (the preflight seam), `review/ERROR_CODES.md` (the `MISSION_REVIEW_*` catalog), `ci-quality.yml:2418` (the residual `-m` selector), `pyproject.toml:52-53` + `uv.lock` (typer/click pins).

## Objective
Make the local pre-PR layer a faithful mirror of CI — WITHOUT touching any workflow, `uv.lock`, or dependency pin (NFR-001).

## Changes
- **T001 — typer/click lock-parity check (FR-001)**: add a function to `_test_env_check.py` that reads the **locked** `typer`/`click` versions from `uv.lock` (parse it — `tomllib`; it's the single source, do NOT hardcode versions) and compares to the installed versions (`importlib.metadata.version`). On divergence, raise a new **`MISSION_REVIEW_ENV_SKEW`** diagnostic (add it to `review/ERROR_CODES.md` following the `MISSION_REVIEW_*` pattern) with remediation `uv sync --frozen --all-extras`. **Warn-loud by default; fail-closed opt-in** (a flag/env — don't brick a legitimately forward-compat `typer>=0.26` dev loop). Wire it into `review/__init__.py:307`, right after `assert_pytest_available`.
- **T002 — local residual runner (FR-002)**: provide a local command/sub-check that runs the CI residual `-m (unit or contract) and not (...)` selection over `tests/`. ⚠️ **Single-source the `-m` expression from the CI selector** (`ci-quality.yml:2418`, or the `_gate_coverage` marker model) — parse/read it live; do NOT hand-copy a divergent string (NFR-002). Do NOT reuse `pre_review_gate.py` (it's absent on-branch — #2438, C-003).
- **T003 — docs + tests (FR-003)**: `docs/guides/review-gates.md` ALREADY documents `--frozen` (`:16-78`) — ADD only (1) the typer/click skew flag + how to resolve, (2) how to run the residual selection locally. Canonical "Mission" terminology. Unit tests in `tests/specify_cli/cli/commands/test_test_env_check.py`: **red-first** the skew check (mock `importlib.metadata.version` to diverge from a fixture `uv.lock` → raises `MISSION_REVIEW_ENV_SKEW`; matching → passes; warn-vs-fail-closed both covered) + the residual selector is read-live (mutate the source selector → the runner's selection changes, proving no hardcode).

## DoD
- Lock-parity check raises `MISSION_REVIEW_ENV_SKEW` on divergence (warn-loud default), wired into the preflight; reads `uv.lock` live.
- Local residual runner single-sources the `-m` from the CI selector (proven by a test).
- `review-gates.md` gains the 2 new items; terminology guard green.
- **NFR-001**: `git diff` touches NO `.github/workflows/`, NO `uv.lock`, NO `pyproject.toml` deps.
- `PWHEADLESS=1 uv run pytest tests/specify_cli/cli/commands/test_test_env_check.py -q` green; `ruff` + `mypy --strict` clean on the changed `.py`; no new suppressions.

## Commit
`git add src/specify_cli/cli/commands/_test_env_check.py src/specify_cli/cli/commands/review/__init__.py src/specify_cli/cli/commands/review/ERROR_CODES.md docs/guides/review-gates.md tests/specify_cli/cli/commands/test_test_env_check.py && git commit -m "feat(review): local pre-PR parity — typer/click lock-parity preflight + residual-selection runner — refs #2283"`

## Report back
The lock-parity check (paste it — show it reads `uv.lock` live) + the `MISSION_REVIEW_ENV_SKEW` code; the residual runner + proof the `-m` is single-sourced (not hardcoded); the red-first skew test (mock diverge → raises); the docs delta; confirmation NFR-001 holds (no workflow/lock/dep change); pytest + ruff + mypy; lane commit SHA. If the CI `-m` selector can't be read live without a hardcoded copy, STOP and report.

## Activity Log

- 2026-07-07T09:41:43Z – claude – shell_pid=2752881 – Assigned agent via action command
