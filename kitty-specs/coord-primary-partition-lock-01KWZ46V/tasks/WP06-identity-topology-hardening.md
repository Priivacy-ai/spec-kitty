---
work_package_id: WP06
title: 'Identity/topology hardening (#2091, #2250, husk)'
dependencies: []
requirement_refs:
- C-006
- FR-005
- FR-007
- FR-008
- FR-012
- NFR-003
- NFR-004
tracker_refs: []
planning_base_branch: design/coord-primary-partition-lock
merge_target_branch: design/coord-primary-partition-lock
branch_strategy: Planning artifacts for this mission were generated on design/coord-primary-partition-lock. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/coord-primary-partition-lock unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
- T031
- T032
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1424763"
history:
- at: '2026-07-07T20:40:00+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/
create_intent:
- tests/specify_cli/coordination/test_workspace_mid8_guard.py
- tests/specify_cli/coordination/test_coord_topology_states.py
execution_mode: code_change
owned_files:
- src/specify_cli/coordination/workspace.py
- src/specify_cli/coordination/surface_resolver.py
- src/specify_cli/missions/_read_path_resolver.py
- tests/specify_cli/coordination/test_workspace_mid8_guard.py
- tests/specify_cli/coordination/test_coord_topology_states.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` (implementer) via `/ad-hoc-profile-load`. Read `spec.md`, `plan.md` (IC-05),
`research.md` (D3, D8), `data-model.md` (Coordination surface states, M-1, T-2). Parallel — no
dependency. Implement via `spec-kitty agent action implement WP06 --agent claude`.

## Objective

Harden the identity/topology edges: add the missing empty-`mid8` guard at the composition seam
(#2091, red-first), verify + regression-lock the never-created path (#2250), and enforce
stored-topology-not-husk (FR-012). Close #2091 and #2250.

## Subtasks

### T027 — Red-first (#2091)
- Failing test reproducing an empty `mid8` at `CoordinationWorkspace` composition → malformed
  `kitty/mission-<slug>-` → `git worktree add` exit-128 (red against pre-fix `workspace.py`).

### T028 — Empty-mid8 guard (#2091)
- Add a guard at `CoordinationWorkspace` composition (`workspace.py:161-226`, `worktree_path`/`branch_name`/`resolve`): a non-empty `mid8` is required; empty → fail loudly with an actionable error (invariant M-1). Verify the upstream `runtime_bridge.py:223-235` guard remains (belt-and-suspenders).

### T029 — #2250 verify + regression
- Verify the shipped never-created fix; the DELETED-gating (`coordination_branch is not None`) sits at `_read_path_resolver.py` ~`:731-744` (the `:697-706` range is now the FR-006 topology gate — symbol-anchor, post-rebase). Extend `test_coord_never_created.py` (or add `test_coord_topology_states.py`) to lock: a mission that never declared `coordination_branch` does NOT emit `COORDINATION_BRANCH_DELETED`. Distinguish the three states (never-created / `DELETED` / `UNMATERIALIZED`) with correct behavior each (see `data-model.md`).

### T030 — FR-012 husk guard (SUBSUMED — verify + regression only)
- **Squad finding:** `_husk_is_authoritative_surface` (`surface_resolver.py:504`) already gates the husk short-circuit on **stored** topology across both read legs (`resolve_status_surface_with_anchor` + `candidate_feature_dir_for_mission`), shipped by #2062 (pre-merge-base). **Do NOT re-implement — forking the guard is a C-001 violation.** This subtask is now: **verify** the guard holds + **add a flatten-transition regression** (a coord-less stored topology resolves PRIMARY before any husk probe). Same verify-only posture as T029.

### T031 — Close issues
- With T027–T030 green, close #2091 and #2250 (reference the regression tests).

### T032 — Campsite (Sonar)
- `workspace.py`: hoist `'worktree'` (×4). `_read_path_resolver.py`: `'coordination_branch'` (×3) ADJACENT — hoist if in a touched function. `surface_resolver.py` is clean.

## Campsite (Sonar issues in owned files)

| File | Rule | Location | Class | Action |
|------|------|----------|-------|--------|
| `coordination/workspace.py` | S1192 | `'worktree'` ×4 | SAFE | Hoist to constant (small file) |
| `missions/_read_path_resolver.py` | S1192 | `'coordination_branch'` ×3 | ADJACENT | Hoist if in a touched function |
| `coordination/surface_resolver.py` | — | clean | — | — |

## Branch Strategy

Base / merge target `design/coord-primary-partition-lock`. Worktree per computed lane. No dependency —
can run in parallel with WP02–WP05.

## Definition of Done

- Empty-`mid8` composition fails loudly (no exit-128); upstream guard verified.
- never-created ≠ `COORDINATION_BRANCH_DELETED`; three coord states distinguished; flatten reads stored topology, not husk.
- #2091 + #2250 closed with regression tests; `ruff` + `mypy` clean; ≤15 complexity.

## Risks & Reviewer guidance

- The #2091 red test must target the **composition seam** locus specifically (not just the upstream runtime_bridge guard).
- FR-012 must not weaken a legitimate materialized-coord read — verify the husk guard only rejects a coord-less stored topology's stale worktree.

## Activity Log

- 2026-07-07T21:58:03Z – claude:opus:python-pedro:implementer – shell_pid=1303270 – Assigned agent via action command
- 2026-07-07T22:01:22Z – user – shell_pid=1303270 – Moved to planned
- 2026-07-07T22:01:37Z – claude:sonnet:python-pedro:implementer – shell_pid=1309735 – Started implementation via action command
- 2026-07-07T22:29:56Z – claude:sonnet:python-pedro:implementer – shell_pid=1309735 – Ready for review; ruff diff-scoped exit 0; mypy --strict full-project clean for touched files (18 pre-existing unrelated errors unchanged); 1561 tests green across coordination/missions/status suites; #2091+#2250 closed on GitHub with verification notes
- 2026-07-07T22:31:11Z – claude:opus:reviewer-renata:reviewer – shell_pid=1424763 – Started review via action command
- 2026-07-07T22:36:15Z – user – shell_pid=1424763 – Review passed: #2091 empty-mid8 guard at CoordinationWorkspace composition seam (worktree_path/branch_name; resolve/teardown/is_present inherit); red-first empirically reproduced (guard neutralized -> git worktree add exit-128 on kitty/mission-<slug>-). #2250 three coord states locked distinctly no-mock (never-created->primary/no DELETED; UNMATERIALIZED->primary; DELETED->hard-fail). FR-012 husk guard _husk_is_authoritative_surface BYTE-IDENTICAL to base (verify-only, no C-001 fork) + new flatten-transition regression. surface_resolver _coord_mid8 caller fix correct (diagnostic-only direct compose, no seam raise). Sonar: '_GIT_WORKTREE' hoisted (4x). ruff exit 0; 270 coordination tests green; zero NEW mypy errors (3 pre-existing Returning-Any identical to base). No dead code, no silent returns, no --feature aliases, all files owned.
