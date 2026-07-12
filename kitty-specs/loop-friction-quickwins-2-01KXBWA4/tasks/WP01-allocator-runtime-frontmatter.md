---
work_package_id: WP01
title: Allocator + move-task no-op-stable against runtime frontmatter
dependencies: []
requirement_refs:
- FR-001
- NFR-001
- NFR-005
tracker_refs:
- '2570'
- '2093'
planning_base_branch: feat/loop-friction-quickwins-2
merge_target_branch: feat/loop-friction-quickwins-2
branch_strategy: Planning artifacts for this mission were generated on feat/loop-friction-quickwins-2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/loop-friction-quickwins-2 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-loop-friction-quickwins-2-01KXBWA4
base_commit: 7d30f5538ea37f21d008380919fe49ff6e6ae05b
created_at: '2026-07-12T21:31:11.647753+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Guards self-stable
agent: "claude"
shell_pid: '1477088'
shell_pid_created_at: '1783891867.36'
history:
- at: '2026-07-12T19:30:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (post-plan-squad 7-concern decomposition, IC-01)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- tests/specify_cli/cli/commands/test_implement_runtime_frontmatter_claim.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/implement_cores.py
- src/specify_cli/frontmatter.py
- tests/specify_cli/cli/commands/test_implement_runtime_frontmatter_claim.py
- tests/agent/test_orchestrator_lane_allocation.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 — Allocator + move-task no-op-stable against runtime frontmatter

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, boundaries, and initialization declaration for the whole WP.

## Objectives & Success Criteria

Make the allocator's uncommitted-planning-artifact check ignore the runtime WP frontmatter the claim
itself just wrote, so N lanes batch-allocate with **zero** inter-allocation commits — while any change to
the WP body or a non-runtime field still blocks. Ship the canonical helper WP07 reuses.

- **SC**: sequential N-lane allocation with `auto_commit=False` needs 0 manual commits between lanes (NFR-001).
- **SC (true-positive, NFR-005)**: a WP whose markdown body (or a non-runtime frontmatter key) changed still blocks.
- **SC**: byte-identical behavior when `auto_commit=True`.

## Context & Constraints

The bug (#2570.1): `spec-kitty implement WP##` writes `shell_pid`/`shell_pid_created_at` (and workspace
creation writes `base_branch`/`base_commit`/`planning_base_branch`) into `tasks/WP##.md`, then the NEXT
lane's claim sees that uncommitted runtime frontmatter as a dirty planning artifact and refuses.

**Canonical prior art to mirror**: `_drop_vcs_lock_only_meta` / `_is_vcs_lock_only_meta_diff` in
`src/specify_cli/cli/commands/implement_cores.py` (~207–283), wired into `resolve_planning_artifact_staging`
(~334–384, two call sites ~363/368). It drops a `meta.json` whose only diff is the vcs-lock fields, gated
on `auto_commit=False`, scoped strictly to an enumerated field set. Do the exact structural analogue for
`WP##.md` runtime fields.

**KEEP invariants (do not violate):**
- **K-1/NFR-005**: remove the false positive only. A markdown **body** change, or any non-runtime
  frontmatter key change, MUST still block. The helper parses frontmatter AND asserts the body is
  byte-unchanged.
- **K-8**: the runtime field set comes from the ONE canonical source `frontmatter.py::WP_FIELD_ORDER`
  (~49) — do NOT hardcode a fresh tuple (avoid a divergent definition; WP07 reuses the same source).
- No `# noqa`/`# type: ignore`; ruff + mypy clean; complexity ≤15.

Charter: `.kittify/charter/charter.md`. Plan: `kitty-specs/loop-friction-quickwins-2-01KXBWA4/plan.md`
(IC-01). Research: `research.md` (R-01 + Post-Squad Refinements). Contract: `contracts/behavioral-contracts.md` (C-A1).

## Branch Strategy

- **Strategy**: branch per computed lane from `lanes.json`; merge back into the planning base.
- **Planning base branch**: feat/loop-friction-quickwins-2
- **Merge target branch**: feat/loop-friction-quickwins-2

## Subtasks & Detailed Guidance

### Subtask T001 — Canonical runtime-field source

- **Purpose**: One authority for the runtime frontmatter field names so WP01 and WP07 agree.
- **Steps**: In `frontmatter.py`, expose (or reuse if present) a named constant/accessor listing the runtime
  fields: `shell_pid`, `shell_pid_created_at`, `base_branch`, `base_commit`, `planning_base_branch`.
  Derive it from `WP_FIELD_ORDER` (or add a `WP_RUNTIME_FIELDS` frozenset alongside it with a comment
  pointing at both consumers). Do not duplicate the list inline elsewhere.
- **Files**: `src/specify_cli/frontmatter.py`.

### Subtask T002 — `_drop_runtime_frontmatter_only_wp` + wiring

- **Purpose**: Drop a `WP##.md` from the uncommitted-artifact set when its only diff is runtime fields.
- **Steps**: In `implement_cores.py`, add `_drop_runtime_frontmatter_only_wp` mirroring
  `_drop_vcs_lock_only_meta`: (1) only for a path whose name matches `WP##.md`; (2) split frontmatter via
  `frontmatter.py` helpers, compare the current vs placement-ref frontmatter, and drop ONLY if every
  differing key is in the T001 runtime set AND the markdown **body is byte-identical**; (3) gate on
  `auto_commit=False`. Wire it into `resolve_planning_artifact_staging` beside the existing
  `_drop_vcs_lock_only_meta` calls.
- **Files**: `src/specify_cli/cli/commands/implement_cores.py` (and `implement.py` only if the call site lives there).
- **Notes**: keep the diff-comparison a pure function for direct unit testing.

### Subtask T003 — Red-first: runtime-only dropped + N-lane 0-commit

- **Purpose**: Prove the fix.
- **Steps**: New `tests/specify_cli/cli/commands/test_implement_runtime_frontmatter_claim.py`: a WP file
  whose only diff vs the placement ref is each runtime field → helper drops it (no block). Extend
  `tests/agent/test_orchestrator_lane_allocation.py` with a sequential N-lane allocation asserting 0
  inter-allocation commits are required.
- **Files**: the two test files.

### Subtask T004 — Red-first: true-positive preserved + no-op on auto_commit=True

- **Purpose**: Prove the guard still fires.
- **Steps**: In the new test file: (a) a WP with a changed markdown body (plus a runtime-field change) still
  blocks; (b) a changed non-runtime frontmatter key still blocks; (c) with `auto_commit=True` the staging
  result is byte-identical to today (helper is a no-op).
- **Files**: the new test file.

## Definition of Done

- `_drop_runtime_frontmatter_only_wp` implemented + wired; runtime field set sourced from `WP_FIELD_ORDER`.
- All four tests pass; body-change and non-runtime-change true-positives proven; `auto_commit=True` no-op proven.
- `PWHEADLESS=1 uv run pytest tests/specify_cli/cli/commands/test_implement_runtime_frontmatter_claim.py tests/agent/test_orchestrator_lane_allocation.py -q` green; `ruff` + `mypy` clean.

## Risks & Reviewer Guidance

- **Risk**: over-broad drop (missing the body-unchanged assertion) would let a real edit slip — reviewer must
  confirm T004's body-change case fails without the assertion.
- **Reviewer**: verify the field set is the canonical `WP_FIELD_ORDER`-derived constant, not an inline tuple.

## Activity Log

- 2026-07-12T22:02:05Z – claude – shell_pid=1477088 – reviewer-renata: REQUEST-CHANGES (noqa) → fixed (YAMLError); core design/NFR-005/SSOT all APPROVE
- 2026-07-12T22:02:20Z – claude – shell_pid=1477088 – reviewer-renata APPROVE (post-fix)
