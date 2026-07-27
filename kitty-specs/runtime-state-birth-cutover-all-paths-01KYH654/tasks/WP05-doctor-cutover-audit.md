---
work_package_id: WP05
title: On-demand doctor cutover audit
dependencies: []
requirement_refs:
- FR-007
planning_base_branch: fix/runtime-state-birth-cutover-all-paths
merge_target_branch: fix/runtime-state-birth-cutover-all-paths
branch_strategy: Planning artifacts for this mission were generated on fix/runtime-state-birth-cutover-all-paths. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/runtime-state-birth-cutover-all-paths unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-runtime-state-birth-cutover-all-paths-01KYH654
base_commit: a949d018cc363dc3d310fbb317e41313144b1a7a
created_at: '2026-07-27T07:57:26.833809+00:00'
subtasks:
- T020
- T021
- T022
- T023
phase: Phase 3 - Observability
history:
- at: '2026-07-27T07:43:31Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/_cutover_doctor.py
create_intent:
- src/specify_cli/cli/commands/_cutover_doctor.py
- tests/specify_cli/cli/commands/test_cutover_doctor.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/doctor.py
- src/specify_cli/cli/commands/_cutover_doctor.py
- tests/specify_cli/cli/commands/test_cutover_doctor.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP05 – On-demand doctor cutover audit

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile in the frontmatter first.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Give operators an on-demand audit of every mission's cut-over status outside CI
(FR-007), matching the existing `doctor` per-subcommand-module convention.

**Done when**: `spec-kitty doctor cutover [--json]` lists each mission's cut-over
status, backed by the canonical `cutover_repo(dry_run=True)`.

## Context & Constraints

- Read [plan.md](../plan.md) IC-05 and [research.md](../research.md) (audit host).
- **Reuse, don't duplicate**: back the audit with `runtime_state_cutover.cutover_repo(repo_root, dry_run=True)` — each `CutoverResult` already carries `flipped`/`would_flip`/`verify`/`error`. Do NOT reimplement corpus walking or verification.
- **Convention**: `cli/commands/doctor.py` is a thin `add_typer` shim delegating to per-subcommand `_<name>_doctor.py` modules (e.g. `_mission_state_doctor.py`). Add `_cutover_doctor.py` the same way. Do NOT shoehorn a corpus-wide audit into the per-feature `status/doctor.py::run_doctor` aggregation.
- Independent WP (no dependency); however the "cut over" definition should be consistent with WP03's shared predicate where sensible — if WP03's `cutover_eligibility` module has landed, prefer it for the verdict; otherwise `cutover_repo(dry_run=True)` is sufficient for the audit.

## Subtasks & Detailed Guidance

### Subtask T020 – Add the doctor cutover subcommand shell
- **Steps**: Add a `cutover` command to the doctor typer in `doctor.py`, delegating to `_cutover_doctor.py`. Keep the shell thin (match the sibling subcommands).
- **Files**: `src/specify_cli/cli/commands/doctor.py`, `src/specify_cli/cli/commands/_cutover_doctor.py` (new).

### Subtask T021 – Back with cutover_repo(dry_run=True); render per-mission status
- **Steps**: In `_cutover_doctor.py`, call `cutover_repo(repo_root, dry_run=True)`, render a per-mission table (slug, cut-over yes/no, reason) and a `--json` form. Exit code non-zero if any mission is un-cut-over is OPTIONAL for an audit — default to informational exit 0 with a clear count, and document it.

### Subtask T022 – Update the CLI-surface census
- **Steps**: Extend the CLI-surface census/expectations for the new `doctor cutover` subcommand.

### Subtask T023 – Red-first: reporting test [P]
- **Steps**: New test with a fixture corpus containing one cut-over and one un-cut-over mission; assert the audit reports each correctly (table + `--json`). Write RED first.
- **Files**: `tests/specify_cli/cli/commands/test_cutover_doctor.py` (new).

## Test Strategy

Red-first. `PWHEADLESS=1 uv run pytest tests/specify_cli/cli/commands/test_cutover_doctor.py -q`; run the CLI-surface census test.

## Risks & Mitigations

- Duplicating corpus/verify logic → reuse `cutover_repo(dry_run=True)`.
- Wrong host (`run_doctor` per-feature aggregation) → use the per-subcommand-module pattern instead.

## Review Guidance

Confirm: thin shell per convention; `cutover_repo(dry_run=True)` reused (no reimplementation); `--json` present; CLI census updated; fixture test covers both cut-over and un-cut-over.

## Activity Log

- 2026-07-27T07:43:31Z – system – Prompt created.
