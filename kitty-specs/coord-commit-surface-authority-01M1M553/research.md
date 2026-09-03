# Research: Coord Commit-Surface Authority

**Mission**: coord-commit-surface-authority-01M1M553
**Phase**: 0 (research) · **Date**: 2026-09-03
**Method**: (a) code trace of the three loci on `fix/coord-commit-surface-authority` (@ `545e8e302f` base); (b) black-box reproduction in two isolated temp git repos (protected `main` primary and unprotected `trunk` primary) using the installed `spec-kitty` 3.2.6rc3/rc4.

---

## D-001 — The authoritative-surface decision is fragmented across three unconnected code paths

**Decision**: Treat "which surface owns a mission's commits, and what happens when a command can't commit there" as **one rule** and introduce a single helper the three loci consult. Today no such helper exists.

**Evidence** (code trace):

1. **Create-time topology** — `_resolve_default_topology_phase` (`src/specify_cli/cli/commands/agent/mission_create.py:373-401`). Topology is chosen from exactly two inputs: the `pr_bound` flag and `current_branch == primary_branch`. **Protection status and `--start-branch` are never consulted.** The load-bearing line:
   ```python
   391  if pr_bound:
   392      return MissionTopology.COORD   # short-circuits BEFORE the primary-branch test
   ```
   → any `--pr-bound` mission gets `topology: coord` unconditionally, even when `--start-branch` has moved the checkout onto an unprotected feature branch. This is the **root cause of #2533**. The `SINGLE_BRANCH` (flat) arm at line 401 is reachable only for non-pr-bound missions off the primary.

2. **Commit-time routing** — `_commit_partition_group` (`src/specify_cli/coordination/commit_router.py:257`), `use_coord` derivation at `:288-292`:
   ```python
   289  use_coord = (routes_through_coordination(resolve_topology(...)) and placement.ref != primary_target)
   ```
   Coord worktree PATH (`.worktrees/<slug>-<mid8>-coord`) and BRANCH (`kitty/mission-<slug>-<mid8>`) are derived per-mission from `(mission_slug, mid8)` read from *that mission's own* `meta.json` (`CoordinationWorkspace.resolve`, `coordination/workspace.py:204-228`; `_resolve_mid8`, `commit_router.py:722-741`).

3. **CLI skip-vs-refuse** — split helpers in `.../agent/tasks_shared.py`: `_skip_target_branch_commit` (`:353-373`, skip arm) and `_protected_branch_status_commit_error` (`:317-330`, refuse arm). Only `move-task` composes the skip pre-gate. `tasks_transition_core.decide_transition` is **move-task-only** by its own docstring; `mark-status` and `map-requirements` are "coreless".

**No function takes `{topology, protected-primary, start/current-branch}` and returns both the authoritative surface and the skip-or-refuse verdict.** That helper is the mission's central deliverable (FR-001/FR-002).

---

## D-002 — B16-clause-2 (concurrent-coord write cross-contamination) does NOT reproduce; it folds into #2533

**Decision**: **Document-out User Story 2 / FR-006 as a standalone defect.** The originally-reported behavior (a write reported `success:true/committed:false`, `placement_ref` = a coord branch that lacks the path and holds a *different* mission's commits) does not reproduce on the current build. Fold its residue into the #2533 work.

**Evidence** (two-repo black-box repro):

*Protected `main` primary* — coord spec-commit of `status.events.jsonl` in each of two concurrent coord missions:
- `result: error`, `success: false`, `committed: false`, `placement_ref: main`, exit 1.
- Message names the real remedy (`--start-branch <feature-branch>` / check out a feature branch). **No false success.** The #2739 clause-1 fix holds.

*Unprotected `trunk` primary* — same two-mission setup, coord spec-commit in each:
- `result: success`, `committed: true`, `placement_ref: trunk`, verifiable — the write **landed** (on the primary; `use_coord` is false because `placement.ref == primary_target == trunk`).
- Resulting linear `trunk`: `sk init → Add meta AA → Add meta BB → coord write AA → coord write BB`. **All mission meta and coordination commits landed on `trunk`, correctly attributed.**
- The two coord branches are **stranded labels**: `kitty/...-aa` → `sk init` (empty of AA's dir); `kitty/...-bb` → the `Add meta AA` commit (so it *appears* to "hold AA's commit"). This appearance is a labelling artifact of stranded coord branches on a shared primary — **not a misrouted write.**

**Code corroboration**: coord worktree/branch are strictly per-mission keyed (`slug+mid8` from the mission's own `meta.json`); no path resolves a sibling mission's coord surface from ambient state (`commit_router.py` + `workspace.py`). The only residual wrong-surface hazard is `_resolve_mid8 → None` (missing/short `meta.json`) silently falling back to the primary checkout (`commit_router.py:700-701`) — a **different**, non-concurrency hazard worth a guard, but not B16-c2.

**Conclusion**: the "cross-contamination" appearance and the #2533 stranded-coord-branch defect are **one root cause**: redundant coord topology minted on a surface where coord routing is inert, leaving coord branches as stranded labels. Fixing create-time topology selection (D-001 #1) removes both.

---

## D-003 — #2300 is a shared-rule-consultation gap, NOT an exit-code-uniformity problem (CORRECTED post-squad)

**Decision**: Unify by making the commit-bearing commands consult one **kind-aware** helper (`coordination/surface_authority.resolve_surface_authority`) via their shell helpers. Do **not** touch `tasks_transition_core.py` (it is move-task-coupled by its own contract). Freeze current behavior first (characterize-then-diff, JSON-mode exit codes).

**Evidence** (code trace + source adjudication):
- **move-task → RouteToCoord (exit 0) — CORRECT, not a defect.** `_skip_target_branch_commit` (`tasks_shared.py:353-373`) is documented as: under coord + protected primary the WP-file's status transition is committed to the **coordination branch (authoritative)** and the redundant direct-to-protected-primary commit is *suppressed* ("suppresses a commit the protection policy would refuse anyway"). This is coord deferral, **not a silent drop**. Forcing it to refuse-exit-1 would regress a working coord flow (NFR-004).
- **map-requirements → Refuse, exit 1 — CORRECT for a planning-kind artifact** on a protected primary (`tasks_map_requirements.py:199-206`).
- **mark-status → event-log-only, no commit (since #2816).** ADJUDICATED FROM SOURCE: `_do_mark_status` runs `validate→resolve→apply→history→dossier→output` and **never calls `_ms_commit`**; `_ms_commit` (`tasks_mark_status.py:216-246`) is dead in the flow — reachable only via the `tasks.py:814` compat re-export and two direct unit tests. The earlier "WARN, exit 0 (swallowed)" classification was **wrong**. Making mark-status refuse-exit-1 would *re-add* a commit path #2816 deliberately removed.

**Reframing:** move-task (lifecycle-kind → RouteToCoord) and map-requirements (planning-kind → Refuse) are BOTH correct — their exit codes differ because their **artifact kinds** differ. The #2300 defect is that each command **hardcodes** its verdict instead of consulting a shared rule, and mark-status drifted off any commit path. Fix = shared-rule consultation (kind-aware), NOT exit-code uniformity. `mark-status` is frozen no-commit, not rewritten.

---

## D-004 — DD-3 must cover ALL silent primary-fallback sites (post-squad)

`commit_router` has multiple silent `return repo_root, files` fallbacks, not one: `_materialise_coord_worktree` mid8-None (`:700-701`) **and** its `except Exception` (`:705-711`), plus `_resolve_commit_worktree_for_kind` mid8-None (`:939-940`) **and** its `except Exception` (`:950-954`). To close the defect class (DIR-043) and satisfy INV-3, WP-C must make all of these fail loud (coord-routed) or consciously document any exclusion. The module docstring advertises these as "C-004 strangler safety" — removing one without the others is an inconsistency.

---

## Open questions → feed into plan/tasks

- **OQ-1 (design, blocking)**: unify toward **skip-exit-0** or **refuse-exit-1** when a command cannot commit to the authoritative surface? Recommendation to settle in plan: **refuse-exit-1 with a real remedy** for protected-primary planning artifacts (matches the shipped spec-commit behavior and NFR-002 "no silent skip of a requested write"), reserving skip-0 for genuine no-ops with a typed `reason`.
- **OQ-2 (design)**: should `--pr-bound --start-branch <unprotected>` yield `SINGLE_BRANCH` (no coord), or keep coord but make the coord branch authoritative and populated? Repro favors **SINGLE_BRANCH** (coord is inert on an unprotected feature branch → pure overhead + stranding).
- **OQ-3 (guard)**: add a fail-loud guard for `_resolve_mid8 → None` instead of the silent primary fallback (`commit_router.py:700-701`).
- **OQ-4 (scope)**: mark-status drift (warn-0) — is silent-warn acceptable, or must it join the unified refuse/skip rule? Likely yes (join), else the "unify three commands" goal is unmet.

## Scope adjustment from research

- **User Story 2 / FR-006 (B16-c2 write cross-contamination)**: **DROPPED** as a standalone WP (D-002). Its root cause is absorbed by the #2533 create-time topology fix; add a regression assertion that concurrent coord missions on a shared primary produce no stranded/mislabelled coord branch once topology selection is fixed.
- Net WP shape (post-squad): **WP-0** foundation — `coordination/surface_authority.py` (pure `coord_topology_reachable` + `resolve_surface_authority`) + golden harness freezing current arms · **WP-A** create-time topology (#2533, DD-2 target-protection keying, freeze `test_mission_create.py:455`, absorbs B16-c2 appearance) · **WP-B** #2300 shared-rule consultation for move-task + map-requirements (mark-status frozen no-commit) · **WP-C** DD-3 fail-loud on ALL commit_router fallback sites + align refuse to helper. WP-0 first; A/B/C parallel after. Helper homed in `coordination/` (not `cli`) to avoid a coordination→cli layering inversion.
