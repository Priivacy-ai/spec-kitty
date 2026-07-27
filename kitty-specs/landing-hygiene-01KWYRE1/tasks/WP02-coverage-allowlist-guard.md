---
work_package_id: WP02
title: Coverage-allowlist determination + existence guard
dependencies: []
requirement_refs:
- FR-003
- FR-004
tracker_refs: []
planning_base_branch: fix/landing-hygiene
merge_target_branch: fix/landing-hygiene
branch_strategy: Planning artifacts for this mission were generated on fix/landing-hygiene. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/landing-hygiene unless the human explicitly redirects the landing branch.
subtasks:
- T003
- T004
agent: "reviewer-renata"
shell_pid: "3786039"
history:
- Created for mission landing-hygiene-01KWYRE1
agent_profile: python-pedro
authoritative_surface: .github/workflows/
create_intent: []
execution_mode: code_change
owned_files:
- .github/workflows/ci-quality.yml
- tests/release/test_diff_coverage_policy.py
- tests/architectural/test_ci_quality_path_filters.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load your assigned profile (`python-pedro`) via `/ad-hoc-profile-load` before reading anything else.

## Objective
Correct the phantom `src/specify_cli/core/mission_detection.py` entry in the `diff-coverage` `--include` critical-path allowlist (it never existed) — with a recorded determination, across BOTH authorities — and add a guard so it can't silently rot again (#2443). **FR-003, FR-004, NFR-001.**

## Context (grounded)
- `.github/workflows/ci-quality.yml:2709` lists `'src/specify_cli/core/mission_detection.py'` in the `critical_paths=( … )` array consumed by `--include` (:2741). That file **never existed** in git history.
- The lost logic is **branch-based mission-slug detection**, **defined** at `src/specify_cli/lanes/branch_naming.py::parse_mission_slug_from_branch` (:778) — `core/vcs/detection.py:158` only imports/consumes it, and `branch_naming.py` is itself absent from the allowlist. NOT `acceptance/__init__.py::detect_mission_slug` (no detection).
- **Two authorities** hardcode the entry: (1) `ci-quality.yml` `--include`; (2) `tests/release/test_diff_coverage_policy.py:275` (its own `critical_path_modules` copy, asserted at :286–287). Editing (1) reds (2) unless updated in lockstep — precedent for lockstep edits is in that file at lines 279–282.
- **Canonical parser to reuse**: `tests/architectural/_gate_coverage.py::_diff_cover_critical_paths()` (:442) — iterated by `test_workflow_coherence.py:231` + `test_ci_quality_path_filters.py:205`.

## Guidance
**T003 — determination + lockstep correction (FR-003)**: the **defining** file is `src/specify_cli/lanes/branch_naming.py` (`parse_mission_slug_from_branch`; `core/vcs/detection.py` is a consumer). Decide whether `branch_naming.py` is genuinely critical-path.
- If yes → **add** `src/specify_cli/lanes/branch_naming.py` (replacing the phantom) in both authorities.
- If an already-listed critical path genuinely covers it → **remove** the phantom entry from BOTH authorities **and record in the PR body the specific already-listed path that covers `branch_naming.py`** (objective — name it). **Bare removal without that named-path proof is forbidden.**
- Either way: `ci-quality.yml` `--include` AND `tests/release/test_diff_coverage_policy.py`'s hardcoded copy change in the SAME commit (lines 279–282 precedent; inline rationale comment).
**T004 — existence guard, glob-aware (FR-004)**: add a test **reusing** `_diff_cover_critical_paths(ci_quality.yml)` that, per entry: a **glob** (contains `*`) → `Path.glob` it and assert **≥1 match** (this also catches a vacuous glob matching zero files — the `src/specify_cli/next/*` precedent); a **literal** → assert `.exists()`. Land it in `tests/architectural/test_ci_quality_path_filters.py`. **Red-first: the failure must name `mission_detection.py` specifically** (not red on unexpanded globs), pass after T003. No hand-rolled second parser (charter).

## Definition of Done
- Both authorities corrected in lockstep; PR records the determination; the guard reds pre-fix, greens post-fix.
- `PWHEADLESS=1 uv run pytest tests/architectural/test_ci_quality_path_filters.py tests/architectural/test_workflow_coherence.py tests/release/test_diff_coverage_policy.py -q` green.
- No hand-rolled second parser; `ruff`+`mypy` clean; no suppression; no weakening of critical-path enforcement.

## Reviewer guidance
Confirm both authorities changed in one commit (no split-brain), the determination is recorded + honest (not a bare removal of real coverage), the guard reuses `_diff_cover_critical_paths`, and it genuinely goes red pre-fix.

## Activity Log

- 2026-07-07T18:21:07Z – python-pedro – shell_pid=3725737 – Assigned agent via action command
- 2026-07-07T18:36:07Z – python-pedro – shell_pid=3725737 – Ready for review: repointed phantom diff-coverage critical path to src/specify_cli/lanes/branch_naming.py in both authorities (ci-quality.yml + test_diff_coverage_policy.py); added glob-aware existence guard reusing _diff_cover_critical_paths; red-first proof named mission_detection.py; DoD gates green (34 passed/2 skipped), ruff+mypy clean.
- 2026-07-07T18:37:25Z – reviewer-renata – shell_pid=3786039 – Started review via action command
