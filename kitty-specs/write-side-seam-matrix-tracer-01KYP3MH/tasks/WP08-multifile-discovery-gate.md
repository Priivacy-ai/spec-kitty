---
work_package_id: WP08
title: Multi-file issue-reference discovery + merge gate
dependencies:
- WP05
- WP03
requirement_refs:
- FR-004
- NFR-005
planning_base_branch: feat/write-side-seam-matrix-tracer
merge_target_branch: feat/write-side-seam-matrix-tracer
branch_strategy: Planning artifacts for this mission were generated on feat/write-side-seam-matrix-tracer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-side-seam-matrix-tracer unless the human explicitly redirects the landing branch.
created_at: '2026-07-29T09:24:15+00:00'
subtasks:
- T028
- T029
- T030
- T031
history:
- at: '2026-07-29T09:24:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tasks/
create_intent:
- src/specify_cli/tasks/issue_reference_discovery.py
- tests/specify_cli/tasks/test_issue_reference_discovery.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/tasks/issue_reference_discovery.py
- src/specify_cli/policy/merge_gates.py
- src/specify_cli/status/doctor.py
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/cli/commands/agent/mission.py
- tests/specify_cli/tasks/test_issue_reference_discovery.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '1738'
---

# Work Package Prompt: WP08 – Multi-file issue-reference discovery + merge gate

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

## Objective

Generalize issue-reference discovery from single-`spec.md` to **all** mission artifacts across the three enforcement sites, and add the missing **merge-time** completeness gate so load-bearing references are never invisible (#1738).

## Context

- Today `detect_issue_references(spec_md_path)` reads `spec.md` **only** (`tasks/issue_matrix.py:51`), and there is no merge-time completeness gate. Enforcement is checked at three sites: `status/doctor.py:374`, `cli/commands/agent/tasks.py:159`, `cli/commands/agent/mission.py:2140`.
- Put the generalized discovery in a **new module** (`tasks/issue_reference_discovery.py`) — do not edit WP05's `issue_matrix.py`. The three enforcement sites repoint to the new module; WP05's single-file function becomes superseded at the call sites.
- Use the **one canonical reference definition** shared with finalization/approval/review — do NOT invent a fourth definition (M7 spirit).

## Subtasks

### T028 — Multi-file discovery module
Create `src/specify_cli/tasks/issue_reference_discovery.py` scanning `spec.md` + `tasks/` + `plan.md` + `research.md` + `analysis-report.md` + `contracts/` for canonical issue references. Deterministic, deduplicated, canonicalized refs (same canonicalization the matrix keys use).

### T029 — Repoint the three enforcement sites
Update `status/doctor.py:374`, `cli/commands/agent/tasks.py:159`, and `cli/commands/agent/mission.py:2140` to consume the new discovery module instead of the single-file scan.

### T030 — Merge-time completeness gate
Add a missing-issue-matrix completeness gate to `src/specify_cli/policy/merge_gates.py`: at merge time, every discovered reference must have a row (fail-closed when references exist). This is a **net-new reader** — `merge_gates` is not a migration target, it gains the reader here.

### T031 — Tests
`tests/specify_cli/tasks/test_issue_reference_discovery.py`: an issue referenced only in `tasks/WP01.md` (or `plan.md`/`contracts/`) is discovered; the merge gate enforces it; the definition matches finalization/approval.

## Branch Strategy

Both planning and merge target are `feat/write-side-seam-matrix-tracer`. Allocate via `/spec-kitty.implement WP08` (depends on WP05, WP03).

## Definition of Done
- Discovery scans all artifacts; three enforcement sites repointed; merge gate enforces completeness.
- `ruff`/`mypy` clean; complexity ≤ 15; tests green.

## Risks / Reviewer guidance
- **One canonical reference definition** — confirm finalization, approval, merge, and review share it (no fourth).
- The merge gate must be fail-closed when references exist and defer to WP09 for the zero-reference `not_applicable` branch.
- **Commit each slice** (discovery module, enforcement repoint, gate) so worktree progress is durable.
