---
work_package_id: WP03
title: Unify resolver primitives (tidy-BEFORE)
dependencies:
- WP02
requirement_refs:
- FR-009
tracker_refs: []
planning_base_branch: feat/single-mission-surface-resolver
merge_target_branch: feat/single-mission-surface-resolver
branch_strategy: Planning artifacts for this mission were generated on feat/single-mission-surface-resolver. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-mission-surface-resolver unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T013
agent: claude
history:
- at: '2026-06-19T17:06:54Z'
  actor: claude
  note: WP authored from plan IC-01 (FR-009/T1, T4, T5).
agent_profile: python-pedro
authoritative_surface: src/specify_cli/missions/
create_intent: []
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/specify_cli/missions/_read_path_resolver.py
- tests/specify_cli/missions/test_read_path_resolver_validation.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `python-pedro`; acknowledge its initialization declaration.

## Objective

The tidy-BEFORE that clears the path for the equivalence matrix: unify the **two divergent `primary_feature_dir_for_mission`** (FR-009/T1), single-source the composition grammar (T5), and extract the shared **resolve-dir-or-typed-error delegator** (T4) — all in `_read_path_resolver.py` as the canonical primitive home. (IC-01)

## Context (code-verified by the boy-scout squad)
- `_read_path_resolver.py:~410` `primary_feature_dir_for_mission` → uses the slug **raw**.
- `missions/feature_dir_resolver.py:~23` → **composes the mid8 suffix** (the divergent twin; retired in WP07).
- Decision (research D2): the **mid8-composing form wins** (it locates backfilled/`<slug>-<mid8>` dirs; raw mislocates them). `_compose_mission_dir` is the single grammar (T5).
- The duplicated resolve-dir wrappers in `aggregate._resolve_read_dir` and `mission_runtime/resolution.py` have differing fallback targets + exception sets — extract ONE delegator here; WP04/WP05 re-point to it.

## Subtasks

### T009 — Unify `primary_feature_dir_for_mission` (FR-009/T1)
- Make `_read_path_resolver.primary_feature_dir_for_mission` the ONE definition, composing `<slug>[-mid8]` via `_compose_mission_dir`. (The `feature_dir_resolver.py` twin keeps re-exporting THIS one until WP07 retires it — do not delete that file here; just make it re-export.) **Behavior decision recorded**: mid8-composing form; verify it locates bare-slug, `<slug>-<mid8>`, and backfilled dirs.

### T010 — Single composition grammar (T5)
- Confirm `_compose_mission_dir` is the sole `<slug>[-mid8]` composer; route `compose_meta_json_path` + the unified primary through it. No second composition path.

### T011 — Shared resolve-dir-or-typed-error delegator (T4)
- Extract one helper (in `_read_path_resolver.py`) that wraps `resolve_status_surface` → returns dir OR raises the canonical typed error, with ONE reconciled fallback policy + exception set. Document the reconciliation (the two old wrappers differed — name the chosen union). WP04 (`aggregate`) and WP05 (`resolution.py`) will re-point to it.

### T012 — Per-caller-class regression tests
- Tests proving the unified `primary_feature_dir_for_mission` resolves correctly for bare-slug, `<slug>-<mid8>`, and backfilled-name missions (the divergence classes). Mutation: revert to raw-slug → the `<slug>-<mid8>` test FAILS.

### T013 — Gates
- `ruff` + `mypy --strict` clean; run `tests/specify_cli/missions/`; confirm the WP02 equivalence matrix's `<slug>-<mid8>` cells now turn green (remove their xfail or note WP02 will).

## Branch Strategy
Planning/base + merge target: `feat/single-mission-surface-resolver`. Worktree per lane. Depends on **WP02** (verify against the gate).

## Definition of Done
- [ ] Exactly ONE `primary_feature_dir_for_mission` definition (mid8-composing); the twin re-exports it (retired in WP07).
- [ ] Single composition grammar (`_compose_mission_dir`); no second path.
- [ ] Shared resolve-dir-or-typed-error delegator extracted with a reconciled fallback/exception policy (documented).
- [ ] Per-caller-class tests pass, mutation-verified; equivalence mid8-handle cells green.
- [ ] ruff + mypy --strict clean.

## Risks / Reviewer guidance
- **Risk**: the canonical-form pick is a behavior change — the per-caller-class tests must prove the mid8-composing form doesn't break bare-slug callers. NOT a blind merge.
- **Reviewer**: confirm the delegator's reconciled fallback set is documented (the two old wrappers differed); confirm the `<slug>-<mid8>` test would fail under the raw-slug form.
