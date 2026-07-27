---
work_package_id: WP03
title: _resolve_lanes_dir pure extraction (#2052)
dependencies: []
requirement_refs:
- FR-006
- NFR-004
tracker_refs:
- '2052'
- '1993'
planning_base_branch: feat/mission-surface-resolver-safety-net
merge_target_branch: feat/mission-surface-resolver-safety-net
branch_strategy: Planning artifacts for this mission were generated on feat/mission-surface-resolver-safety-net. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-surface-resolver-safety-net unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
phase: Phase 1 - Tidies (parallel)
agent: claude:sonnet:python-pedro:implementer
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/implement.py
create_intent:
- tests/cli/commands/test_resolve_lanes_dir.py
execution_mode: code_change
mission_id: 01KVN754TY9CVJ8G10ERTMPVRH
owned_files:
- src/specify_cli/cli/commands/implement.py
- tests/cli/commands/test_resolve_lanes_dir.py
role: implementer
tags: []
wp_code: WP03
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This profile governs your implementation style, boundaries, and quality standards for this work package.

---

## 🧹 Campsite-Cleaning Directive (#1970) — ACTIVE

While inside `implement.py` around the lanes-dir resolution, remediate adjacent issues in-slice bounded to
this mission's goal. No "out of scope" hand-waving for debt in the touched block.

## Objective

Extract a pure, topology-aware, **zero-mock-testable** `_resolve_lanes_dir(repo_root, mission_slug) -> Path`
seam from the inline assignment in `implement()`. This makes the lanes-dir resolution unit-testable with a
`tmp_path` (no infrastructure mocks), satisfying the residual of #1993 that #2050 left behind.

## Context (verified)

- The behavior is already correct (it reads the coord surface — `implement.py:~1019`,
  `_lanes_feature_dir = _status_feature_dir`). The unmet ask is the **pure extraction** for testability —
  distinct from the existing `lanes/persistence.resolve_lanes_dir` (a different path-join helper). Do NOT
  conflate them.
- Research basis: `research/collapse-reduction-map-randy.md` (section D — confirmed separable, no coupling
  to the resolver chain).

## Subtasks

### T011 — Verify-first
- Read the current inline resolution at `implement.py:~1019`. Confirm what it computes (coord-worktree
  surface preferred; primary fallback for flat/legacy). If the residual is already behaviorally satisfied,
  the WP is **just** the extraction + test (no behavior change) — record that finding.

### T012 — Extract the pure seam
- Add `_resolve_lanes_dir(repo_root: Path, mission_slug: str) -> Path` (pure: no I/O mocks needed beyond a
  `tmp_path` filesystem). It prefers the coord-worktree surface (where `finalize-tasks` writes `lanes.json`)
  and falls back to the primary checkout for flat/legacy topology. Replace the inline assignment with a call
  to it. **No behavior change.**

### T013 — Zero-mock unit test
- `tests/cli/commands/test_resolve_lanes_dir.py`: build a `tmp_path` repo with (a) coord topology and
  (b) flat/legacy topology; assert `_resolve_lanes_dir` returns the coord surface / primary respectively —
  **no `unittest.mock`** (the point is zero-mock testability).

### T014 — Campsite
- Remediate adjacent debt around the extraction site you touch.

## Branch Strategy
Planning base / merge target: `feat/mission-surface-resolver-safety-net`. Independent lane (parallel with
WP02 and the WP01 chain).

## Definition of Done
- `_resolve_lanes_dir` is a pure function; the inline assignment routes through it; **zero behavior change**.
- Zero-mock unit test covers coord + flat topology and passes.
- `ruff` + `mypy` clean. Campsite noted. If the residual was already satisfied, the handoff says so.

## Risks & Reviewer Guidance
- Reviewer: confirm zero behavior change (the inline path and the function compute the same dir) and that
  the test genuinely uses no mocks (a `tmp_path` filesystem only).

## Activity Log
- 2026-06-21T14:42:27Z – system – WP03 prompt generated via /spec-kitty.tasks
