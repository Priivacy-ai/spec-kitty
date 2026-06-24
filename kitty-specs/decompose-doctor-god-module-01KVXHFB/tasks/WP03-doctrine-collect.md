---
work_package_id: WP03
title: _doctrine_collect collector-seam completion
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-004
- FR-006
tracker_refs:
- '2059'
planning_base_branch: prog/2059-doctor
merge_target_branch: prog/2059-doctor
branch_strategy: Planning artifacts for this mission were generated on prog/2059-doctor. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2059-doctor unless the human explicitly redirects the landing branch.
created_at: '2026-06-24T19:54:56+00:00'
subtasks:
- T007
- T008
- T009
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3107150"
history:
- date: '2026-06-24'
  action: created
  actor: claude
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/_doctrine_collect.py
create_intent:
- src/specify_cli/cli/commands/_doctrine_collect.py
- tests/specify_cli/cli/commands/test_doctrine_collect.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/_doctrine_collect.py
- tests/specify_cli/cli/commands/test_doctrine_collect.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via the `/ad-hoc-profile-load` skill (profile: **randy-reducer**, role: implementer). Adopt its boundaries, governance scope, and initialization declaration for this work package. Then return here.

## Objective

Complete the doctrine-health seam #1623 left behind: move the doctrine-health DATA COLLECTORS (Cluster J) out of `doctor.py` into a new `_doctrine_collect.py`, beside the existing `_doctrine_health.py` (MODEL) and `_profile_health_render.py` (RENDER). This finishes the MODEL/RENDER/COLLECT triad. **Do NOT re-extract `_doctrine_health.py`/`_profile_health_render.py`** — they are already done.

## Context

- #1623 explicitly scoped its move to render-only and left the collectors in `doctor.py` (research §3).
- Collectors to move (Cluster J): `_resolve_pack_version`, `_count_pack_artifacts`, `_summarize_org_charter`, `_collect_profile_health`, `_attach_pack_health`, `_build_pack_entries`, `_collect_doctrine_collisions`, `_collect_org_layer_data`, `_resolve_artifact_source`, `_read_project_selections`, `_read_org_required`, `_build_selection_block`, and the `_ORG_ARTIFACT_DIRS` constant.
- Test-facing symbols among these that 58 test files import from `doctor`: `_collect_profile_health`, `_collect_org_layer_data`, `_build_pack_entries`, `_count_pack_artifacts`, `_resolve_pack_version` (FR-006 re-export).
- The byte-pinned doctrine-selections snapshot test (`test_doctor_doctrine_selections_snapshot.py`) must stay green.

## Subtasks

### T007 — Create `_doctrine_collect.py`
- Move the Cluster J collectors + `_ORG_ARTIFACT_DIRS` into `_doctrine_collect.py`. Import `console`/guards/constants from `_doctor_shared`; import the MODEL types from `_doctrine_health` and RENDER helpers from `_profile_health_render` as needed (one-way: collect → model/render/shared). No import of `doctor.py`.

### T008 — Delegate + re-export in `doctor.py`
- The `doctrine` command body in `doctor.py` calls the collectors from `_doctrine_collect`.
- Re-export the test-facing collector symbols from `doctor` (mirror the `_profile_health_render` `from ._x import _y as _y` precedent): `_collect_profile_health`, `_collect_org_layer_data`, `_build_pack_entries`, `_count_pack_artifacts`, `_resolve_pack_version` (and any others the doctor test files import — grep to confirm).

### T009 — Focused tests + snapshots
- `test_doctrine_collect.py`: exercise each collector branch directly (pack version resolution, artifact counting, profile-health collection, collision/org-layer assembly, selection-block build). ≥90% coverage.
- Re-run the byte-pinned doctrine snapshot + WP01 golden — both green.

## Branch Strategy

Planning branch & merge target: **`prog/2059-doctor`** (PR-bound to `main`). Worktrees per `lanes.json`. Commit with `--to-branch prog/2059-doctor`; transitions from the primary checkout CWD.

## Test Strategy (ATDD)

RED collector unit tests before the move; GREEN after. Doctrine snapshot + golden stay green.

## Out-of-map edits

- `src/specify_cli/cli/commands/doctor.py` — delegate the `doctrine` body + add the re-export block. Owned by WP11; sequential chain → no concurrent writer.

## Definition of Done

- Collectors live in `_doctrine_collect.py`; the doctrine MODEL/RENDER/COLLECT triad is complete; `_doctrine_health.py`/`_profile_health_render.py` untouched.
- Test-facing collector symbols re-export from `doctor`; the 58 test files' imports resolve.
- `_doctrine_collect` ≥90% covered; doctrine snapshot + golden green; ruff + mypy --strict clean, zero new suppressions.

## Risks

- Moving a collector without re-exporting breaks the doctor test imports (FR-006).
- Re-extracting MODEL/RENDER (already done) is out of scope — touch only the collectors.

## Reviewer Guidance

Recommended reviewer: standard. Verify only collectors moved (not MODEL/RENDER), re-exports resolve, the byte-pinned doctrine snapshot is green, ≥90% collector coverage, one-way imports.

## Activity Log

- 2026-06-24T19:54:56Z – claude – planning – WP created (deps WP02; completes #1623 seam).
- 2026-06-24T20:43:54Z – claude:opus:randy-reducer:implementer – shell_pid=3046407 – Assigned agent via action command
- 2026-06-24T20:56:12Z – claude:opus:randy-reducer:implementer – shell_pid=3046407 – Collectors extracted to _doctrine_collect; #1623 triad complete; 92% cov; snapshot+golden green; ruff/mypy clean
- 2026-06-24T20:56:20Z – claude:opus:reviewer-renata:reviewer – shell_pid=3107150 – Started review via action command
- 2026-06-24T20:56:24Z – user – shell_pid=3107150 – Only collectors moved (MODEL/RENDER untouched); collect->model/render/shared one-way (AST-verified, no doctor import); 5 test-facing symbols re-export from doctor; byte-pinned doctrine snapshot green; 92% collector coverage; ruff/mypy --strict clean; behavior-preserving
