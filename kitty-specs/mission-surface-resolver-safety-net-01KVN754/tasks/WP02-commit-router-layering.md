---
work_package_id: WP02
title: commit_router inverted-layering fix (#2061)
dependencies: []
requirement_refs:
- FR-007
- NFR-004
tracker_refs:
- '2061'
planning_base_branch: feat/mission-surface-resolver-safety-net
merge_target_branch: feat/mission-surface-resolver-safety-net
branch_strategy: Planning artifacts for this mission were generated on feat/mission-surface-resolver-safety-net. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-surface-resolver-safety-net unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
phase: Phase 1 - Tidies (parallel)
agent: claude:sonnet:python-pedro:implementer
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/commit_router.py
create_intent:
- tests/coordination/test_commit_router_layering.py
execution_mode: code_change
mission_id: 01KVN754TY9CVJ8G10ERTMPVRH
owned_files:
- src/specify_cli/coordination/commit_router.py
- tests/coordination/test_commit_router_layering.py
role: implementer
tags: []
wp_code: WP02
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This profile governs your implementation style, boundaries, and quality standards for this work package.

---

## 🧹 Campsite-Cleaning Directive (#1970) — ACTIVE

While inside `commit_router.py`, remediate adjacent issues in-slice (stale comments, dead imports, type/lint
nits) bounded to this mission's goal. No "pre-existing, out of scope" hand-waving for issues in the touched
surface.

## Objective

Remove the only `coordination/ → cli/` reach-in in the codebase. `commit_router.py:293` imports (callsites at :303/:308)
`path_is_under_worktrees` from `cli/commands/merge.py`, which merely re-wraps the same-package primitive
`coordination/surface_resolver.is_under_worktrees_segment`. Import the primitive directly.

## Context (verified)

- `commit_router.py:293` `from specify_cli.cli.commands.merge import path_is_under_worktrees`; used at
  `:303` and `:308`.
- `cli/commands/merge.py:188` `path_is_under_worktrees` is `return is_under_worktrees_segment(path)` — a
  byte-identical delegate.
- `is_under_worktrees_segment` is exported from `coordination/surface_resolver.py:289` (same package).
- This is fully independent of the read-path/coord chain — runs in parallel.

## Subtasks

### T008 — Swap the import + call sites
- Replace the `cli.commands.merge` import with
  `from specify_cli.coordination.surface_resolver import is_under_worktrees_segment`; update the two call
  sites (`:303`, `:308`) to call `is_under_worktrees_segment` with the same argument. Semantics are identical.

### T009 — Test the byte-identical behavior + no reach-in
- Add `tests/coordination/test_commit_router_layering.py`: (a) a focused test that the staging path under
  `.worktrees/` is classified identically before/after (use a `tmp_path` shaped path); (b) an
  import-direction assertion that `coordination/commit_router.py` has **zero** `from specify_cli.cli`
  imports (AST or source scan). Make it non-fakeable (the assertion fails if the reach-in returns).

### T010 — Campsite
- Remediate adjacent debt in `commit_router.py` you touch.

## Branch Strategy
Planning base / merge target: `feat/mission-surface-resolver-safety-net`. Independent lane (parallel with
WP03 and the WP01 chain).

## Definition of Done
- Zero `coordination/ → cli/` imports in `commit_router.py` (test-enforced); behavior byte-identical.
- `ruff` + `mypy` clean. Campsite noted.

## Risks & Reviewer Guidance
- Reviewer: confirm the call-site semantics are identical (the merge wrapper added nothing) and the
  import-direction test actually fails if someone re-adds the `cli` import.

## Activity Log
- 2026-06-21T14:42:27Z – system – WP02 prompt generated via /spec-kitty.tasks
