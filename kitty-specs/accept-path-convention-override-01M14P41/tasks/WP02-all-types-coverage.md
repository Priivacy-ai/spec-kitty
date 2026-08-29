---
work_package_id: WP02
title: All-four-types + Go coverage [TEST-ONLY]
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-005
- NFR-004b
planning_base_branch: fix/accept-path-convention-override
merge_target_branch: fix/accept-path-convention-override
branch_strategy: Planning artifacts for this mission were generated on fix/accept-path-convention-override. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/accept-path-convention-override unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
history: []
agent_profile: implementer-ivan
authoritative_surface: tests/specify_cli/
create_intent:
- tests/specify_cli/acceptance/test_path_conventions_all_types.py
- tests/specify_cli/test_validate_mission_paths_single_caller.py
execution_mode: code_change
owned_files:
- tests/specify_cli/acceptance/test_path_conventions_all_types.py
- tests/specify_cli/test_validate_mission_paths_single_caller.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your profile before anything else: `/ad-hoc-profile-load implementer-ivan`. Apply its initialization,
boundaries, and directives, then proceed.

## Objective

Prove the by-construction breadth of WP01's override (all four mission types + Go `internal/`) and lock the
single-seam invariant. **STRICTLY TEST-ONLY** — this WP writes no source; any seam defect found routes back
to WP01 (do not edit `validators/paths.py`, `summary_core.py`, or `config/`).

Read `spec.md` US2, `contracts/precedence-contract.md`, `quickstart.md` test-map first.

## Branch Strategy

Base/merge: `fix/accept-path-convention-override`. Depends on WP01 (its reader + seam must exist). Runs in
parallel with WP03. Enter via `spec-kitty agent action implement WP02 --agent claude`.

## Guidance per subtask

### T008 — Other mission types honor the override (FR-004, US2-1)
`tests/specify_cli/acceptance/test_path_conventions_all_types.py`: for a research (and plan/documentation)
mission, assert the **resolved** `required_paths[key] == override value` at the seam — NOT merely that
"accept passed" (a type whose declared dirs happen to exist would pass green without the override being
honored; asserting the resolved value discriminates). Exercise through `evaluate_path_conventions`. Read a
real `mission.yaml` to source the per-type defaults rather than hardcoding assumptions.

### T009 — Go `internal/` layout (FR-005)
Same file: a repo with `internal/` (no `src/`) + override `{workspace: internal/}` accepts; colocated
tests (no `tests/` dir) handled via an override or the existing lenient path — assert the honest accept,
no fabricated dir.

### T010 — Artifact-routed-key rejection + `path_prefix` composition (US1-4, US2-3)
- Overriding `deliverables` is rejected/ignored (C-010) — assert routing is NOT flipped (the mission-surface
  artifact check still fires).
- For a research mission (which applies `path_prefix`), assert override × `path_prefix` composes in the
  documented order (or, if they don't co-occur for a key, assert that with the reason). Pin the behavior.

### T011 — Single-caller invariant (NFR-004b)
`tests/specify_cli/test_validate_mission_paths_single_caller.py` (**NOT** under `tests/architectural/` —
that would trip the shard-orphan + golden-count cascade). Assert via AST/grep that `validate_mission_paths`
has exactly one production caller (`evaluate_path_conventions`). Use a set/equality assertion, not `len()==N`.

## Definition of Done
- All four mission types + Go covered; artifact-routed-key rejection + `path_prefix` composition pinned;
  single-caller guard green and placed outside `tests/architectural/`.
- No source file touched (test-only); `ruff` clean; new-dir tests use frozenset/dict-equality.

## Reviewer guidance
Confirm: zero source edits; the single-caller test is outside `tests/architectural/`; `deliverables`
rejection is asserted (not silently routing); real `mission.yaml` values are read, not assumed.
