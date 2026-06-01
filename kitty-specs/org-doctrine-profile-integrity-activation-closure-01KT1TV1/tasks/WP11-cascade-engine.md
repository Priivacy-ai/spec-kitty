---
work_package_id: WP11
title: Cascade engine (scope + shared-reference safety)
dependencies:
- WP02
- WP03
- WP10
requirement_refs:
- FR-013
- FR-014
- FR-015
- FR-016
tracker_refs: []
planning_base_branch: mission/org-doctrine-profile-integrity-activation-closure
merge_target_branch: mission/org-doctrine-profile-integrity-activation-closure
branch_strategy: Planning artifacts for this mission were generated on mission/org-doctrine-profile-integrity-activation-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/org-doctrine-profile-integrity-activation-closure unless the human explicitly redirects the landing branch.
subtasks:
- T048
- T049
- T050
- T051
- T052
agent: claude
history:
- at: '2026-06-01T16:49:18Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/charter/cascade.py
execution_mode: code_change
mission_slug: org-doctrine-profile-integrity-activation-closure-01KT1TV1
owned_files:
- src/charter/cascade.py
- tests/charter/test_cascade.py
role: implementer
tags: []
---

# WP11 — Cascade engine (scope + shared-reference safety)

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Implement scoped cascade activation and shared-reference-safe cascade deactivation as pure graph logic over the merged DRG — no per-kind special cases (FR-013/014/015/016, C-005). Provide a `CascadeScope` value object so `--cascade all` is an explicit shorthand and absence never means all.

## Context

- Spec FR-013..016, C-005; research R-005, R-011-D (no shared-ref analysis exists; DRG needs `edges_to` reverse reachability — provided by WP02).
- Data model §6 (I-AC2/AC3). Contract C3.2, C3.3, C3.4.

### Code map

- `src/doctrine/drg/query.py` — `walk_edges`, `resolve_transitive_refs` (forward refs by relation set), `edges_to` (WP02, reverse).
- `src/charter/drg.py` — `filter_graph_by_activation` (post-WP03, charter aggregation).
- `src/charter/activation_engine.py` (WP10) — cascade targets surface through `ActivationPlan.cascade_targets`.

## Branch Strategy

- Planning/base + merge target: `mission/org-doctrine-profile-integrity-activation-closure`. Depends on WP02 (edges_to), WP03 (merged DRG), WP10 (engine).

## Subtasks

### T048 — `CascadeScope` value object

**Steps**: In `src/charter/cascade.py`, define `CascadeScope` — either `ALL` (explicit all-kind shorthand) or an explicit frozenset of `ArtifactKind`. Parsing from the CLI string (`"all"` vs `"agent-profile,tactic"`) lives here (CLI passes the raw string; WP12 calls this). `None`/absent means no cascade.

**Validation**: - [ ] `"all"` → ALL; `"agent-profile,tactic"` → {AGENT_PROFILE, TACTIC}; absent → no cascade.

### T049 — Cascade activation by scope (FR-014)

**Steps**: `cascade_activation_targets(graph, source_urn, scope) -> dict[kind, list[id]]` using `walk_edges`/`resolve_transitive_refs` forward, filtered to the scope's kinds. Report activated vs skipped-by-scope.

**Validation**: - [ ] only scoped kinds returned; `all` returns every referenced kind.

### T050 — No-cascade warning (FR-013)

**Steps**: `referenced_but_not_cascaded(graph, source_urn) -> list[<ref>]` returning referenced artifacts (by kind) for the warning when `--cascade` is absent, plus a recovery hint string.

**Validation**: - [ ] returns the skipped reference kinds for a referencing artifact.

### T051 — Shared-reference-safe deactivation (FR-015/016/C-005)

**Steps**: `deactivation_plan(graph, target_urn, scope, *, active_urns) -> {deactivate: [...], skipped_shared: [(urn, referencing_active_urn)]}`. A cascade candidate is **exclusive** iff unreachable from all other still-activated sources after removing `target_urn` (use `edges_to`/forward closure from remaining active sources). Shared candidates are skipped with the still-referencing active artifact named. Pure graph logic — no per-kind branches.

**Validation**: - [ ] exclusively-referenced deactivated; shared skipped with referencing artifact; no shared artifact removed (C-005).

### T052 — Tests

**Steps**: `tests/charter/test_cascade.py` — scoped activation, `all` shorthand, no-cascade warning, exclusive vs shared deactivation with explicit skip reporting; a diamond-reference graph for the shared case.

**Validation**: - [ ] green; ruff/mypy clean.

## Definition of Done

- [ ] `CascadeScope`; scoped activation; no-cascade warning; shared-safe deactivation via reverse reachability; all pure graph logic. CC-2 pass.

## Risks

- Reverse-reachability correctness is the crux of C-005 — test the diamond/shared case explicitly; a wrong implementation silently removes shared artifacts.
- Keep it kind-agnostic (FR-016): branch on graph reachability, never on `kind ==`.

## Reviewer Guidance (reviewer-renata)

- Confirm shared-reference detection is reverse-reachability over the merged DRG, not a heuristic.
- Confirm no per-kind special-casing.
- Confirm `all` is explicit and absence ≠ all.
