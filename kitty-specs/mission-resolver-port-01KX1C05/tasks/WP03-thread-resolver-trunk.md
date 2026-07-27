---
work_package_id: WP03
title: 'Thread the resolver trunk: shell + canonicalizer + sentinel'
dependencies:
- WP02
requirement_refs:
- FR-002
- FR-003
- FR-004
- FR-005
- NFR-001
tracker_refs: []
planning_base_branch: feat/mission-resolver-port-2173
merge_target_branch: feat/mission-resolver-port-2173
branch_strategy: Planning artifacts for this mission were generated on feat/mission-resolver-port-2173. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-resolver-port-2173 unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
- T016
- T017
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "920129"
history:
- at: '2026-07-08T18:06:06+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/resolution.py
create_intent:
- tests/mission_runtime/test_builder_fs_free_identity.py
execution_mode: code_change
owned_files:
- src/mission_runtime/resolution.py
- src/specify_cli/missions/_read_path_resolver.py
- src/specify_cli/doctrine_synthesizer/apply.py
- src/specify_cli/core/vcs/detection.py
- tests/mission_runtime/test_builder_fs_free_identity.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load your agent profile via `/ad-hoc-profile-load` for `python-pedro` (implementer). Then read
`kitty-specs/mission-resolver-port-01KX1C05/spec.md` (FR-002/003/004/005), `plan.md` (IC-02/IC-03),
`data-model.md` (injection seam), and `research.md` (D-01, D-07, D-08, D-09).

## Objective

Make the port the **single walk trunk**: thread an optional `resolver` from the shell callers through the
canonicalizer chain to the free `resolve_mission`, so every read path uses the injected resolver.
Reconcile the `legacy-<slug>` bootstrap sentinel as a documented carve-out. Deliver the FS-free builder
**identity-leg** test — the concrete `#1619` unblock. **This is the trunk WP; without it the port is a
7th parallel path.**

> **Heaviest WP in the mission (post-tasks squad).** 6 concerns over a 1465-LOC god-module. Follow the
> subtask order T012→T013→T014→T015→T016→T017 strictly. T015 (the 2 enumeration adopters, disjoint files)
> is liftable into its own sibling WP if you prefer — do so only if you also update `owned_files`; otherwise
> keep the internal order. Do NOT treat "6 subtasks" as small.

## Critical design rulings (squad)
- **Inject at the CALLERS, not inside the assembler**: `_resolve_mission_slug` (`resolution.py:303`) runs
  *before* `_assemble_core_fragments` (`:1036`) and feeds it. Thread `resolver` through
  `resolve_action_context` (`:1354`), `mission_context_for` (`:827`), `resolve_placement_only` (`:1143`).
  (Line numbers verified against live code; if drifted, grep by name.)
- **Preserve the canonicalizer + topology-aware read**: `_resolve_mission_id`/`_resolve_mission_slug` route
  through `_read_path_resolver` (`resolve_handle_to_read_path`, `primary_feature_dir_for_mission`,
  `_canonicalize_primary_read_handle`) — do NOT bypass them; thread the resolver *into* that chain at the
  `resolve_mission` call (`_read_path_resolver.py:503`). Do NOT fold canonicalization into the blind
  primitive (C-007).
- **`build_execution_context` stays FS-free and takes no resolver**; never put an adapter on the frozen
  `MissionExecutionContext` (C-006).
- **No cache** (C-005).

## Subtasks

### T012 — Thread through the canonicalizer chain
- `_read_path_resolver.py:503` currently calls the free `resolve_mission(handle, repo_root)`. Add an
  optional `resolver` param to the relevant `_read_path_resolver` functions and pass it into that call.
  Keep canonicalization + topology behavior identical.

### T013 — Thread through the shell callers
- `resolution.py`: add `resolver: MissionResolver | None = None` to `resolve_action_context`,
  `mission_context_for`, `resolve_placement_only`, and thread it down to `_resolve_mission_slug` /
  `_resolve_mission_id` and into the canonicalizer. Default None → real `FsMissionResolver` at the walk
  site (already handled by WP02's free-fn default). Do not construct `FsMissionResolver` inside
  `mission_runtime` (would red the ledger) — rely on the free-fn default in `specify_cli.context`.

### T014 — Legacy-`<slug>` bootstrap sentinel carve-out (D-07)
- `_resolve_mission_id` (`resolution.py:948`, def at `:913`) degrades to `legacy-<slug>` for pre-identity/bootstrap
  missions. Keep this as an **explicit, documented pre-identity branch** that does NOT call the
  fail-closed `resolve()`. Add a regression test proving bootstrap/scaffold still mints the sentinel (not
  a raised `MissionNotFoundError`).

### T015 — Adopt the 2 resolve-by-identity consumers
- `doctrine_synthesizer/apply.py:602/788` and `core/vcs/detection.py:169` each walk `kitty-specs/` to find
  a dir matching a `mission_id`/slug. Route them through `all_missions()`/`resolve()` on the resolver
  (surfacing the `vcs` field detection needs). Preserve their exact success/miss behavior.
- **Complexity landmine (Paula):** `apply.py:412 apply_proposals` is already **C901=14** (ceiling 15).
  **Extract a small helper BEFORE adding the resolver-adoption branch**, or your own diff reds `ruff`. Keep
  the touched function ≤15.

### T016 — Free-function caller audit (verify the trunk)
- Confirm each of the 8 free-`resolve_mission` callers now benefits from the trunk (they call the same
  free fn, which delegates to `FsMissionResolver`): `audit/engine.py:87`, `selector_resolution.py:218`,
  `retrospect.py:124`, `agent_retrospect.py:72`, `mission_type.py:1051`, `runtime/show_origin.py:231`,
  `acceptance/__init__.py:910`, `_read_path_resolver.py:503`. Most need **no edit** (documentation only);
  edit via documented leeway only if a caller must inject a specific resolver. (`acceptance/__init__.py`'s
  #2139 read is WP05's — leave that file to WP05.)

### T017 — FS-free builder identity test + verify (NFR-001, scoped)
- New `tests/mission_runtime/test_builder_fs_free_identity.py`: drive the builder's **identity-resolution
  leg** by passing a `FakeMissionResolver` through `resolve_action_context`/the shell, asserting the
  resolved identity with **no `kitty-specs/` tree**. Scope the test + its docstring to the identity leg
  (the assembler's other FS legs — `get_main_repo_root`, `_resolve_coordination_branch`,
  `_resolve_status_surface_dir`, topology — are separate later-phase ports, D-09).
- Verify: `test_layer_rules.py` green (zero new ledger edge); `test_mission_runtime_surface.py` green
  (`build_execution_context` still FS-free, no adapter on the frozen context); no cache; full
  `tests/architectural/` green; `ruff`/`mypy` clean.

## Branch Strategy
Planning branch and merge target: `feat/mission-resolver-port-2173`. Lane worktree per `lanes.json`.

## Definition of Done
- All read paths reach the walk through the resolver; the 8 callers are audited (routed or documented).
- Bootstrap sentinel preserved with a regression test.
- FS-free identity test green; layer/surface/cache/purity all verified; `ruff`/`mypy` clean.

## Risks / reviewer guidance
- **Split-brain check**: reviewer confirms no read path still reaches `_build_index`/`resolve_mission`
  bypassing the threaded resolver (grep the canonicalizer + shell).
- **Sentinel**: confirm bootstrap still works (the load-bearing carve-out).
- **Topology preserved**: confirm coord-vs-primary reads are unchanged (don't regress the placement fixes).
- Run the full arch suite from the **primary checkout**, not a worktree (marker gates vacuous under `.worktrees/`).

## Activity Log

- 2026-07-08T19:48:26Z – claude:sonnet:python-pedro:implementer – shell_pid=203850 – Assigned agent via action command
- 2026-07-08T20:21:23Z – claude:sonnet:python-pedro:implementer – shell_pid=203850 – Trunk threaded: resolver flows shell→canonicalizer(_read_path_resolver:520)→resolve_mission; sentinel preserved; FS-free test 5 passed; layer-rules 23 passed; ruff+mypy clean
- 2026-07-08T20:21:38Z – claude:opus:reviewer-renata:reviewer – shell_pid=297780 – Started review via action command
- 2026-07-08T20:45:18Z – user – shell_pid=297780 – Moved to planned
- 2026-07-08T20:46:21Z – claude:sonnet:python-pedro:implementer – shell_pid=874844 – Started implementation via action command
- 2026-07-08T21:05:34Z – claude:sonnet:python-pedro:implementer – shell_pid=874844 – Cycle 2: synced surface-resolution-audit census (regenerated inventory.md via canonical rekey_inventory.py — 5 added resolver=resolver candidate callsites + 5 ghost rows repointed) + allowlist line pointer 1239->1282 for primary_feature_dir_for_mission; FULL tests/architectural/ green (827 passed, 4 skipped, 0 failed); trunk logic in resolution.py/_read_path_resolver.py UNCHANGED
- 2026-07-08T21:07:34Z – claude:opus:reviewer-renata:reviewer – shell_pid=920129 – Started review via action command
- 2026-07-08T21:14:32Z – user – shell_pid=920129 – Cycle 2 review passed (resolves cycle-1 census-desync rejection): census synced via canonical rekey_inventory.py (--check reports fresh, exit 0), allowlist pointer 1282 matches live primitive def, trunk byte-identical to approved cycle-1 (git diff a2e10385b HEAD on resolution.py + _read_path_resolver.py EMPTY), 3 previously-red arch tests green (19 passed), full tests/architectural/ suite 827 passed/4 skipped/0 failed
