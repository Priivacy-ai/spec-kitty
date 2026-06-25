---
work_package_id: WP04
title: Record-analysis seam (Seam A)
dependencies:
- WP03
requirement_refs:
- FR-003
- FR-004
- FR-006
- NFR-001
tracker_refs: []
planning_base_branch: prog/2056-mission
merge_target_branch: prog/2056-mission
branch_strategy: Planning artifacts for this mission were generated on prog/2056-mission. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2056-mission unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-decompose-mission-god-module-01KVXHF8
base_commit: cc74304cd7f3ac2d26cc05c3904ff69feb19f276
created_at: '2026-06-24T19:52:40.998893+00:00'
subtasks:
- T013
- T014
- T015
- T016
phase: Phase 3 - Command seams
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3228847"
history:
- timestamp: '2026-06-24T19:52:40Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/agent/mission_record_analysis.py
create_intent:
- src/specify_cli/cli/commands/agent/mission_record_analysis.py
- tests/specify_cli/cli/commands/agent/test_mission_record_analysis.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/mission_record_analysis.py
- tests/specify_cli/cli/commands/agent/test_mission_record_analysis.py
tags: []
---

# Work Package Prompt: WP04 – Record-analysis seam (Seam A)

## Do This First

1. Confirm WP03 merged; golden test green.
2. Read research.md §3 Seam A — the lowest-risk command slice (1 command + 2 dedicated helpers).
3. Keep the `commit_for_mission` / `CoordinationWorkspace` imports function-local (lazy) to avoid cycles (NFR-005).

## Objective

Extract `record_analysis` and its two dedicated helpers into `mission_record_analysis.py`, importing the
Seam C/D surfaces extracted in WP02/WP03.

## Implementation

### T013 — Create the seam module
Move `record_analysis`, `_enforce_analysis_report_write_preflight`,
`_resolve_record_analysis_placement_ref` into `mission_record_analysis.py`. Lazy-import
`commit_router.commit_for_mission` and `analysis_report.write_analysis_report`.

### T014 — Register + repoint
Register the `record-analysis` command from the seam (the shim re-export/registration is finalized in WP09;
for now `mission.py` imports the command object from the seam). Documented out-of-map import edit.

### T015 — Tests
Author `test_mission_record_analysis.py`; extend (do not replace) the existing
`test_record_analysis_coord_worktree.py` coverage. Target ≥90% of the seam.

### T016 — Gates
Golden test green; ruff + mypy clean.

## Acceptance

- New seam + test; ≥90% coverage; existing record-analysis tests green; golden green; CC ≤15.

## Out-of-map edits

- `src/specify_cli/cli/commands/agent/mission.py`: import-line edits only.

## Activity Log

- 2026-06-24T21:03:46Z – claude:opus:randy-reducer:implementer – shell_pid=3141470 – Assigned agent via action command
- 2026-06-24T21:25:56Z – claude:opus:randy-reducer:implementer – shell_pid=3141470 – Seam A extracted; record-analysis command relocated + registered on app (CLI surface unchanged); 21 seam tests (90% combined cov) + golden + json_envelope + full agent suite + record/wp05/analysis_report repointed all green; ruff C901 clean; mypy clean on new file. --force: pre-existing status bookkeeping contamination.
- 2026-06-24T21:26:07Z – claude:opus:reviewer-renata:reviewer – shell_pid=3228847 – Started review via action command
- 2026-06-24T21:26:12Z – user – shell_pid=3228847 – Review passed: behavior-preserving Seam A extraction; command registered on app keeps 8-command CLI surface; placement-ref/preflight/git-helper relocated verbatim; patch targets repointed for the move (record_analysis runs in seam); 90% combined coverage; golden+json_envelope+full agent suite green; ruff C901 clean; mypy clean on new file (2 pre-existing findings unchanged); one-way imports (seam→C/D surfaces only). Scope clean. --force: status bookkeeping contamination.
