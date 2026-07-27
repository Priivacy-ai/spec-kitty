---
work_package_id: WP04
title: aggregate.py consolidation (glob + thin adapter)
dependencies:
- WP02
- WP03
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: feat/single-mission-surface-resolver
merge_target_branch: feat/single-mission-surface-resolver
branch_strategy: Planning artifacts for this mission were generated on feat/single-mission-surface-resolver. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-mission-surface-resolver unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1913082"
history:
- at: '2026-06-19T17:06:54Z'
  actor: claude
  note: WP authored from plan IC-03 (FR-008/T2) + IC-06 T3.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/
create_intent:
- tests/status/test_aggregate_surface_resolution.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/specify_cli/status/aggregate.py
- tests/status/test_aggregate_surface_resolution.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load `python-pedro`; acknowledge its initialization declaration.

## Objective
Consolidate all `status/aggregate.py` surface-resolution work: kill the silent-first-match `glob` mid8 path (FR-008/T2) and make `_resolve_read_dir` a thin adapter over the canonical resolver/delegator (T3, part of FR-007). One module, one WP (file-ownership). (IC-03 + IC-06)

## Context
- `aggregate.py:~473` `_find_meta_path`: `for c in sorted(specs_dir.glob(f"{mission_slug}-*/meta.json"))` — silent first-match, the opposite of the `MISSION_AMBIGUOUS_SELECTOR` contract (S8 ambiguity).
- `aggregate.py:~336` `_resolve_read_dir`: re-gates `is_under_worktrees_segment(...) and not .exists() → primary_candidate`, overriding the canonical resolver for the unmaterialized-coord case (a divergence source).

## Subtasks
### T014 — Kill the silent glob (FR-008/T2)
- Route mid8 disambiguation through the one canonical handle resolver (`_canonicalize_handle`/`resolve_mission`); ambiguous → `MISSION_AMBIGUOUS_SELECTOR`, never silent-pick.
### T015 — Thin-adapter `_resolve_read_dir` (T3)
- Re-point to the WP03 shared delegator; remove the duplicate unmaterialized-coord re-gate so aggregate no longer overrides the canonical resolver. (This deletes a duplicate → gated on WP02 equivalence-green for aggregate's input classes, C-004.)
### T016 — Negative tests (+ the create→first-write contract)
- Ambiguous-mid8 → `MISSION_AMBIGUOUS_SELECTOR` (mutation: restore the glob → test fails). Coord-fresh/coord-empty resolution matches the canonical resolver. **CRITICAL distinct cell**: the **no-coord create→first-write** window (primary has the spec, no `coordination_branch`; `aggregate.py:327` preserves this on `FileNotFoundError`) MUST still resolve **PRIMARY** (not a hard-fail) after the re-gate is removed — mutation-verified. Do not conflate it with the coord-empty hard-fail (FR-006/WP06): coord-empty = materialized-but-empty coord → hard-fail; no-coord create-window = primary. Both must be asserted separately.
### T017 — Gates
- `ruff` + `mypy --strict` clean; run `tests/status/`; the WP02 equivalence matrix's aggregate cells turn green.

## Branch Strategy
Planning/base + merge target: `feat/single-mission-surface-resolver`. Worktree per lane. Depends **WP02** (gate) + **WP03** (delegator/primitives).

## Definition of Done
- [ ] Silent glob removed; mid8 routed through the canonical handle resolver (ambiguous → typed error), mutation-verified.
- [ ] `_resolve_read_dir` is a thin adapter over the WP03 delegator; the duplicate re-gate is gone.
- [ ] no-coord create→first-write window still resolves PRIMARY (not hard-fail), asserted as a distinct cell from coord-empty, mutation-verified.
- [ ] aggregate's equivalence cells green (WP02); no regression in `tests/status/`.
- [ ] ruff + mypy --strict clean.

## Risks / Reviewer guidance
- **Risk**: removing the re-gate changes coord-fresh/coord-empty behavior — must match the canonical resolver (proven by the WP02 matrix). Do not delete it before those cells are green.
- **Reviewer**: confirm the ambiguous-mid8 negative test is mutation-killing; confirm no second mid8 path remains in aggregate.

## Activity Log

- 2026-06-20T09:11:47Z – claude:opus:python-pedro:implementer – shell_pid=1836415 – Assigned agent via action command
- 2026-06-20T09:54:33Z – claude:opus:python-pedro:implementer – shell_pid=1836415 – aggregate consolidation (73ebdc290): silent-glob+ambiguity-suppression removed (FR-008 real fix), _resolve_read_dir thin-adapter over WP03 delegator, create-window re-gate KEPT (live-evidence: not a duplicate, delegator defers create-window authority to call site). 4 mutation kills, 9 tests, equivalence 0-XPASS, ruff+mypy clean, tests/status 698 pass. Reviewer: validate the re-gate-kept deviation.
- 2026-06-20T09:54:39Z – claude:opus:reviewer-renata:reviewer – shell_pid=1913082 – Started review via action command
- 2026-06-20T10:03:00Z – user – shell_pid=1913082 – reviewer-renata APPROVED: FR-008 silent-glob+suppression removal real & mutation-killing; KEPT re-gate ruled CORRECT deviation (WP03 docstring defers create-window authority to call site; mutation-proven load-bearing); thin-adapter genuine; equivalence 0-XPASS; 698 pass; ruff+mypy clean. untrusted_path_audit undercount = WP03 debt (pre-merge fix).
