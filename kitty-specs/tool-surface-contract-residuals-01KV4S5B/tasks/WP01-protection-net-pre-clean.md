---
work_package_id: WP01
title: Protection net & dead-code pre-clean
dependencies: []
requirement_refs:
- NFR-001
- FR-008
tracker_refs:
- '1945'
planning_base_branch: feat/tool-surface-contract-residuals
merge_target_branch: feat/tool-surface-contract-residuals
branch_strategy: Planning artifacts for this mission were generated on feat/tool-surface-contract-residuals. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/tool-surface-contract-residuals unless the human explicitly redirects the landing branch.
created_at: '2026-06-15T05:20:00+00:00'
subtasks:
- T001
- T002
- T003
- T004
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "3880629"
history:
- date: '2026-06-15'
  action: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tool_surface/model.py
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/tool_surface/model.py
- tests/specify_cli/tool_surface/test_model.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via the `/ad-hoc-profile-load` skill (profile: **python-pedro**, role: implementer). Adopt its boundaries, governance scope, and initialization declaration for this work package. Then return here.

## Objective

Establish the backward-compat **protection net** and remove the dead `model.SurfaceFinding` duplicate **before** any finding-code work (WP02) begins. This is the FOLD-PRE gate from the plan's pre-tasks scan — it clears the `SurfaceFinding` type-name ambiguity so WP02 has one obvious target.

## Context

- PR #1948's body documented that `tool_surface/model.py::SurfaceFinding` is a dead duplicate superseded by `findings.SurfaceFinding` (the 9-field shape with `to_json()` used by all live reporting). A randy-reducer scan confirmed: **zero live source importers**; the only consumers are stale tests in `tests/specify_cli/tool_surface/test_model.py` instantiating the old 7-field shape.
- The "protection net" = the frozen backward-compat baselines that every later WP must not break: the `doctor skills --json` schema baseline and the `agent config` compat tests. WP01 does **not** edit them — it confirms they exist and are green, so a regression in WP02–WP05 is change-detected.

## Subtasks

### T001 — Verify the protection net is in place (capture evidence)
- Run the frozen baselines and **paste the pytest summary line** (passed/failed counts) into the handoff — self-asserted "green" is insufficient:
  - `pytest tests/specify_cli/cli/commands/test_doctor_skills.py -q`
  - `pytest -k "agent_config_compat" -q`
- These are the *pre-change* baseline. Do NOT edit them (WP03 owns the agent-config tests; WP05 will modify `test_doctor_skills.py` for #1965 determinism — that's expected, not a freeze you enforce here).

### T002 — Delete dead `model.SurfaceFinding`
- Remove the `SurfaceFinding` class from `src/specify_cli/tool_surface/model.py` (the ~11-LOC dead duplicate). Leave `SurfacePlan` and the rest of `model.py` intact (`surface_presence.py` imports `SurfacePlan` from here — keep it).
- Before deleting, re-grep to confirm no live importer: `git grep -n "from specify_cli.tool_surface.model import" | grep SurfaceFinding` and `git grep -n "model.SurfaceFinding"` — expect only `test_model.py`.

### T003 — Drop ONLY the stale `SurfaceFinding` test (surgical, not a gut-job)
- In `tests/specify_cli/tool_surface/test_model.py`, remove ONLY the `SurfaceFinding`-specific test(s) (the 7-field shape: `code/tool_key/surface_kind/severity/path/repair_command/detail`, e.g. `test_surface_finding_*`) and drop `SurfaceFinding` from the shared `from ...model import (...)` line — **without** deleting the file or touching the live tests for `SurfacePlan`, `NativeAgentProfile`, `SurfaceDefinition`.
- **Anti-gut guard:** record the pre/post test count for `test_model.py` (must drop by exactly the number of `SurfaceFinding` tests) and enumerate the surviving test names in the handoff. Deleting the file or weakening assertions to "make it compile" is a rejection.

### T004 — Confirm clean
- `git grep -n "SurfaceFinding" src/ | grep -v "findings.py"` → no `model`-sourced references remain.
- `pytest tests/specify_cli/tool_surface/ -q` green; `ruff check` + `mypy --strict` clean on `model.py` + `test_model.py`.

## Branch Strategy

Planning branch & merge target: **`feat/tool-surface-contract-residuals`** (PR-bound to `main`). Execution worktrees are allocated per computed lane from `lanes.json` at implement time. Commit with explicit `--to-branch feat/tool-surface-contract-residuals` on `safe-commit`; run status transitions from the primary checkout CWD.

## Test Strategy (ATDD)

No new feature behavior — this is a deletion + verification WP. The "test" is: the full `tool_surface` suite stays green after the deletion, and `test_model.py` no longer references the dead class.

## Definition of Done

- `model.SurfaceFinding` gone; zero live references; `findings.SurfaceFinding` is the sole `SurfaceFinding`.
- `test_model.py` compiles and passes; full `tool_surface` suite green; ruff + mypy --strict clean.
- Frozen baselines (doctor-skills, agent-config compat) confirmed green (the protection net for WP02–WP05).

## Risks

- Deleting the class breaks `test_model.py` import unless T003 lands in the same change — do both together.
- Do not touch `findings.py` (WP02 owns it) or the agent-config tests (WP03 owns them).

## Reviewer Guidance

Recommended reviewer: **reviewer-renata** (standard). Verify: zero live importers of `model.SurfaceFinding` remain; the deletion didn't remove `SurfacePlan` or other live `model.py` exports; the protection-net baselines are green. Closes the FOLD-PRE for #1940 (WP02). Issue-matrix: this WP supports the mission-level closure of #1945's children (FR-008) — no single issue closes here.

## Activity Log

- 2026-06-15T05:53:08Z – claude:opus:python-pedro:implementer – shell_pid=3872717 – Assigned agent via action command
- 2026-06-15T05:58:27Z – claude:opus:python-pedro:implementer – shell_pid=3872717 – Ready for review.
- 2026-06-15T05:58:40Z – claude:opus:python-pedro:implementer – shell_pid=3872717 – HANDOFF NOTE: BASELINES (T001): test_doctor_skills.py = 12 passed; agent_config_compat = 5 passed. T002: SurfaceFinding class (lines 62-72, ~11 LOC) deleted from model.py; pre-deletion grep confirmed zero live source importers — only test_model.py referenced it. T003: test_model.py pre-count=5, post-count=4 (dropped exactly 1 test: test_surface_finding_allows_none_path_and_repair). Surviving tests: test_surface_definition_is_hashable, test_surface_instance_absent_has_none_hash, test_surface_plan_accepts_empty_instances, test_native_agent_profile_fields. T004: git grep -n SurfaceFinding src/ | grep -v findings.py = all remaining hits are from ..findings imports (no model-sourced refs); pytest tests/specify_cli/tool_surface/ = 224 passed, 1 pre-existing failure (test_doctor_skills_json_error_schema_stable confirmed pre-existing via git stash check); ruff check = all checks passed; mypy --strict = no issues in 2 source files.
- 2026-06-15T05:59:16Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=3880629 – Started review via action command
- 2026-06-15T06:03:26Z – user – shell_pid=3880629 – Review passed: surgical deletion of model.SurfaceFinding confirmed (11 LOC removed, SurfacePlan/NativeAgentProfile/SurfaceDefinition/SurfaceInstance all intact); test_model.py dropped exactly 1 test (5->4, test_surface_finding_allows_none_path_and_repair), 4 survivors are real assertions; zero model-sourced SurfaceFinding refs in src/ (all remaining hits are from ..findings imports); findings.py untouched; ruff+mypy --strict clean on both touched files; tool_surface suite 224 passed; sole failure test_doctor_skills_json_error_schema_stable confirmed pre-existing (stash check); protection-net baselines green: doctor_skills 12 passed, agent_config_compat 5 passed; no out-of-scope changes; all anti-pattern checklist items PASS or N/A.
