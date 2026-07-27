---
work_package_id: WP01
title: Fix repair_lane_mismatch frontmatter corruption (#2921)
dependencies: []
requirement_refs:
- FR-007
planning_base_branch: fix/read-side-placement-seam-migration
merge_target_branch: fix/read-side-placement-seam-migration
branch_strategy: Planning artifacts for this mission were generated on fix/read-side-placement-seam-migration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/read-side-placement-seam-migration unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-read-side-placement-seam-migration-01KYHP67
base_commit: 8ec371983fd3c7f70367b90f393121556678b60a
created_at: '2026-07-27T12:28:03.665676+00:00'
subtasks:
- T001
- T002
- T003
phase: Phase 1 - Bugfix
history:
- at: '2026-07-27T12:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/task_metadata_validation.py
create_intent:
- tests/specify_cli/test_repair_lane_mismatch.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/task_metadata_validation.py
- tests/specify_cli/test_repair_lane_mismatch.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Fix repair_lane_mismatch frontmatter corruption (#2921)

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` to load `python-pedro` (role implementer, agent claude) before anything else.

## Objective
`repair_lane_mismatch` corrupts frontmatter: `task_metadata_validation.py:127` binds the 3rd element of `parse_frontmatter` (which is the raw frontmatter TEXT, per `template/renderer.py:23-53`) to `padding`, then `:178` feeds it into `build_document(fm, body, padding)` whose 3rd arg must be trailing whitespace (`task_utils/support.py:215`) → the closing `---` is glued to a duplicated stale frontmatter block spliced into the body. Fix it.

## Subtasks
### T001 — Red-first repro
Write `tests/specify_cli/test_repair_lane_mismatch.py`: create a WP file under a lane dir (e.g. `tasks/for_review/WP01.md`) whose frontmatter `lane` mismatches the dir (`lane: planned`) + a body. Call the PRE-EXISTING entry point `repair_lane_mismatch(task_file, dry_run=False)`; assert it currently produces duplicated frontmatter / broken fence (RED).
### T002 — Minimal fix
- `:127` → `frontmatter, body, _ = parse_frontmatter(content)` (stop mislabeling raw text as padding).
- `:178` → `new_content = build_document(frontmatter_yaml, body, "\n")`.
Do NOT swap to `split_frontmatter` (it returns a string, not the mutable dict the module needs to set `frontmatter["lane"]`).
### T003 — Round-trip assertion
Green the test: repaired file has exactly one frontmatter block, `lane` corrected, clean `\n---\n` fence, body present + NOT duplicated, and `validate_task_metadata(task_file) == []`.

## Gates (FOREGROUND, `uv run`)
`PWHEADLESS=1 uv run pytest tests/specify_cli/test_repair_lane_mismatch.py -q`; `uv run ruff check`; `uv run mypy src/specify_cli/task_metadata_validation.py`.

## DoD / Review
Red-first shown; fix is the two minimal edits; round-trip clean; independent of #2922 (no placement coupling). Finish: commit, `mark-status T001 T002 T003 --status done`, `move-task WP01 --to for_review`.
