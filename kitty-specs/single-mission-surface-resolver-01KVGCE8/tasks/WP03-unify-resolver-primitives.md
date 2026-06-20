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
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1822542"
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

## ⚠️ Corrected premise (squad-verified, 2026-06-19) — direction was REVERSED
The plan's "mid8-composing form wins" directive is **dangerous and must NOT be followed as written**. Code ground truth:
- `_read_path_resolver.py:410` `primary_feature_dir_for_mission` → **raw slug, BY DESIGN**. Its docstring states it is "deliberately topology-blind … does NOT route through `resolve_mission_read_path`" and is used by primary-anchored readers (`finalize-tasks` merge-target, mission **01KTRC04 FR-003**). It carries the `assert_safe_path_segment` traversal guard and is the form exported in `__all__`.
- It is **called by `mission_runtime/resolution.py:202-218` `_mid8_from_primary_meta`** to read the primary `meta.json` and *derive* the mid8 — so composing mid8 *inside* this function would be **circular** (you need the dir to read the mid8 you'd need to build the dir).
- `missions/feature_dir_resolver.py:23` is the **mid8-composing twin** (`compose_meta_json_path(...).parent`) — that file is the C-004 shim retired in **WP07**.
- So the canonical raw-slug form is correct and load-bearing; the divergence is a **same-named function with a different intent**, not a bug to blind-merge.

## Context (code-verified)
- The fix is **disambiguation, not a merge onto mid8**: keep `_read_path_resolver.primary_feature_dir_for_mission` raw-slug/topology-blind; make the `feature_dir_resolver.py` twin **re-export THIS canonical raw-slug one** (eliminating the shadowing divergence) — do NOT delete that file here (WP07 retires it).
- Audit the shim's callers: any caller that actually needed mid8-composition wanted the **topology-aware resolved dir** and must route to `resolve_feature_dir_for_slug`/`resolve_mission_read_path` (or `compose_meta_json_path`) explicitly — NOT to a mid8-fied `primary_feature_dir`. Record the per-caller decision (re-pointed vs preserved).
- `_compose_mission_dir`/`compose_meta_json_path` remains the single `<slug>[-mid8]` grammar (T5) for the **topology/resolved** path; the raw-slug primary anchor is intentionally outside it.
- The duplicated resolve-dir wrappers in `aggregate._resolve_read_dir` and `mission_runtime/resolution.py` have differing fallback targets + exception sets — extract ONE delegator here; WP04/WP05 re-point to it.

## Subtasks

### T009 — Disambiguate `primary_feature_dir_for_mission` (FR-009/T1) — do NOT blind-merge
- FIRST confirm (rg the callers) the two same-named defs have **different intent**: canonical (`_read_path_resolver.py:410`) = raw-slug topology-blind primary anchor; shim (`feature_dir_resolver.py:23`) = mid8-composing. Make the shim **re-export the canonical raw-slug one** so the name resolves identically everywhere. Preserve the topology-blind raw-slug contract (do not introduce mid8 composition into the primary anchor — it would break `_mid8_from_primary_meta` and the 01KTRC04 finalize-tasks read). If a shim caller genuinely needed mid8 resolution, re-point THAT caller to the topology-aware resolver and record it.

### T010 — Single composition grammar (T5)
- Confirm `_compose_mission_dir`/`compose_meta_json_path` is the sole `<slug>[-mid8]` composer for the **topology-aware/resolved** path. The raw-slug primary anchor is intentionally separate; document why (topology-blind by design). No accidental second composition path.

### T011 — Shared resolve-dir-or-typed-error delegator (T4)
- Extract one helper (in `_read_path_resolver.py`) that wraps `resolve_status_surface` → returns dir OR raises the canonical typed error, with ONE reconciled fallback policy + exception set. Document the reconciliation (the two old wrappers differed — name the chosen union). WP04 (`aggregate`) and WP05 (`resolution.py`) will re-point to it.

### T012 — Per-caller-class regression tests (incl. the topology-blind contract)
- Tests proving (a) the shim's name now resolves to the canonical raw-slug form; (b) **every pre-existing caller of the raw-slug `primary_feature_dir_for_mission` still reads its primary-anchored `meta.json`** after the change — specifically `_mid8_from_primary_meta` (`resolution.py:202`) and the `finalize-tasks` merge-target read (01KTRC04 FR-003). Mutation: introduce mid8-composition into the primary anchor → these primary-anchored reads FAIL (proves the topology-blind contract is load-bearing).

### T013 — Gates
- `ruff` + `mypy --strict` clean; run `tests/specify_cli/missions/` + `tests/mission_runtime/`; confirm the WP02 equivalence matrix's `<slug>-<mid8>` cells now agree (remove their xfail or note WP02 will). No regression in the 01KTRC04 finalize-tasks path.

## Branch Strategy
Planning/base + merge target: `feat/single-mission-surface-resolver`. Worktree per lane. Depends on **WP02** (verify against the gate).

## Definition of Done
- [ ] Exactly ONE `primary_feature_dir_for_mission` definition (**canonical raw-slug, topology-blind**); the `feature_dir_resolver.py` twin re-exports it (retired in WP07). No mid8 composition introduced into the primary anchor.
- [ ] Single composition grammar (`_compose_mission_dir`/`compose_meta_json_path`) for the topology-aware/resolved path; the raw-slug primary anchor intentionally separate (documented).
- [ ] Shared resolve-dir-or-typed-error delegator extracted with a reconciled fallback/exception policy (documented).
- [ ] Per-caller-class tests pass incl. the topology-blind contract regression (`_mid8_from_primary_meta`, finalize-tasks); mutation-verified.
- [ ] ruff + mypy --strict clean.

## Risks / Reviewer guidance
- **Risk (root-cause regression)**: blind-merging onto the mid8-composing form would break the deliberate topology-blind primary anchor (01KTRC04 FR-003) and make `_mid8_from_primary_meta` circular — reintroducing the very split-brain this mission kills. The fix is **disambiguation** (shim re-exports the raw-slug canonical), not a merge.
- **Reviewer**: confirm the primary anchor is still raw-slug; confirm the mutation test (inject mid8 composition → primary-anchored reads fail) bites; confirm the delegator's reconciled fallback set is documented (the two old wrappers differed).

## Activity Log

- 2026-06-19T18:06:25Z – claude:opus:python-pedro:implementer – shell_pid=1551247 – Assigned agent via action command
- 2026-06-20T09:05:08Z – claude:opus:python-pedro:implementer – shell_pid=1551247 – Disambiguation (raw-slug canonical, shim re-exports) + T4 delegator (0550e8d0c); 37 tests pass; equivalence gate 6pass/7xfail/0XPASS; ruff+mypy clean. NOTE: implementer API-died pre-commit, orchestrator verified+completed (lint fixes + commit). coord-fresh/bare + coord-behind/bare xfails NOT closed by WP03 (they're resolve_mission_read_path mid8-blindness, closed at the WP06 collapse) — flagged for WP06 re-attribution.
- 2026-06-20T09:05:28Z – claude:opus:reviewer-renata:reviewer – shell_pid=1822542 – Started review via action command
- 2026-06-20T09:11:16Z – user – shell_pid=1822542 – reviewer-renata APPROVED: raw-slug direction verified, mutation test bites (injected forbidden mid8-merge → RED), delegator policy sound, 180/180 tests, gate 0-XPASS, ruff+mypy clean. coord-fresh/bare re-attribution agreed (WP06 follow-up).
