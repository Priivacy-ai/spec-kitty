# Contract: Authoritative Commit Surface

**Revised post-squad (2026-09-03).** The decision all commit-bearing loci consume.
**Home: `src/specify_cli/coordination/surface_authority.py`** — a pure module importable by
both `cli.commands.agent.*` and `coordination.*` with no cycle (`coordination/` must not
import `cli/`). Two pure functions:

## 1. `coord_topology_reachable` (used by create-time, WP-A)

```
coord_topology_reachable(pr_bound: bool, primary_protected: bool, current_is_primary: bool) -> bool
```
Rule 5 (topology selection): coordination routing is reachable **iff**
`pr_bound and (primary_protected or current_is_primary)`.
- `primary_protected` = `ProtectionPolicy.resolve(repo_root).is_protected(primary_target)` — protection of the **primary target branch**, NOT the current checkout.
- This is an **insertion into the `pr_bound` arm** of `_resolve_default_topology_phase` (`mission_create.py:391`), not a rewrite: the `None`-guard arm (`:393-394`) and the non-pr-bound `current==primary → COORD` arm (`:399-401`) are preserved.
- Tripwire: `tests/specify_cli/cli/commands/agent/test_mission_create.py:455` (`test_create_pr_bound_on_non_primary_branch_still_defaults_to_coord`, target=`main` protected) MUST stay green — it confirms keying on target-protection, not checkout. `--pr-bound --start-branch <unprotected-target>` → `SINGLE_BRANCH`.

## 2. `resolve_surface_authority` (used by commit-bearing commands + commit_router, WP-B/WP-C)

```
resolve_surface_authority(
    topology, primary_target, primary_protected, current_branch, artifact_kind
) -> SurfaceVerdict

SurfaceVerdict:
    surface: "primary" | "coordination"
    ref: str
    non_committable: None
        | RouteToCoord            # coord-kind under coord+protected: commit lands on coord; the
                                  #   redundant direct-to-protected-primary commit is suppressed → exit 0
        | Refuse(remedy: str)     # primary-kind on a protected primary with no coord route → exit 1 + remedy
        | NoOp(reason: str)       # genuine no-op only → exit 0, typed (no_op_already_committed | no_op_no_changes)
```

### Rules (authoritative — kind-aware)

1. **Coordination/lifecycle-kind under COORD/LANES_WITH_COORD, primary protected** → `surface=coordination`, `ref=kitty/mission-<slug>-<mid8>`; the direct primary commit is **suppressed (RouteToCoord, exit 0)** — the coord commit is authoritative. *(This is exactly today's correct `move-task` skip, per `_skip_target_branch_commit`'s documented invariant: it "suppresses a commit the protection policy would refuse anyway"; the coord status transition is authoritative.)*
2. **Coordination-kind on an UNPROTECTED primary** → `use_coord` is false (`placement.ref == primary_target`); commit lands on **primary** directly. Coord routing is inert (this is why DD-2 declines to mint coord here).
3. **Primary/planning-kind on a protected primary** → `Refuse(remedy="--start-branch <feature-branch> or SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS=1")`, exit 1. *(Matches shipped spec-commit / #2739 and today's `map-requirements`.)*
4. **Primary-kind on an unprotected branch** → `surface=primary`, commit directly.
5. **Genuine no-op** (nothing staged / already committed) → `NoOp(reason)`, exit 0 — the ONLY exit-0 "nothing committed" besides RouteToCoord. A **wrong-surface** situation is a `Refuse`, never a `NoOp`. Note the router today labels wrong-surface `no_op_wrong_surface` (`commit_router.py`/`write_seam.py`): the helper MUST map that to **Refuse**, not treat the `no_op_` prefix as exit-0.
6. `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS=1` folds into `primary_protected=False` (rule 3 degrades to rule 4). Stated, not implicit.

### Key reframing (why exit codes legitimately differ)
The three task commands are **not** required to share an exit code. They must share the **rule**: same `{artifact_kind, topology, primary_protected}` → same verdict. `move-task` (lifecycle-kind) yields RouteToCoord/exit-0; `map-requirements` (planning-kind) yields Refuse/exit-1 — both correct because their kinds differ. The #2300 defect is that each command **hardcodes** its verdict instead of consulting rule 1–6, and `mark-status` drifted off any commit path entirely.

## Consumers (corrected)
- `mission_create._resolve_default_topology_phase` → `coord_topology_reachable` (rule 5 only). Does NOT consume `resolve_surface_authority` (no `artifact_kind` at create time).
- `commit_router._commit_partition_group` → align its existing `use_coord`/refuse logic to `resolve_surface_authority` (rules 1–5) + the DD-3 fail-loud guards.
- `tasks_move_task` (lifecycle-kind) + `tasks_map_requirements` (planning-kind) → consume `resolve_surface_authority` via their shell helpers (`_skip_target_branch_commit` / `_protected_branch_status_commit_error` collapse into it).
- `tasks_mark_status` → **NOT a consumer**: event-log-only since #2816 (`_ms_commit` is dead — compat-shim + unit-test only). Freeze as no-commit; do not re-add a commit path.

## Behavior-change ledger (characterize-then-diff, NFR-001) — corrected

| command / kind | context | before | after |
|---|---|---|---|
| move-task (lifecycle) | coord + protected primary | skip primary commit, exit 0 (coord authoritative) | **unchanged** (RouteToCoord, exit 0) — now via shared rule, not hardcoded |
| map-requirements (planning) | coord + protected primary | refuse, exit 1 | **unchanged verdict** (Refuse, exit 1) — via shared rule; remedy unified |
| mark-status | coord + protected primary | event-log-only, no commit, exit 0 | **unchanged** (frozen no-commit) |
| move-task / map-requirements | genuine no-op, unprotected | exit 0 | **unchanged** (NoOp reason, exit 0) — NEW golden rows to lock |
| spec-commit | genuine no-op (`unchanged`) | exit 0 + reason (#2739) | **unchanged** — regression guard row |
| any commit-bearing | wrong-surface (`no_op_wrong_surface`) | exit 1 | **unchanged** (Refuse) — assert not collapsed to exit-0 |

"Identical" = for the same `{artifact_kind, topology, primary_protected}`, identical verdict + shared `reason` code + shared remedy constant (command-name substring may vary). Each row frozen in a golden test before the change and re-frozen after; JSON-mode exit codes asserted (not only human-readable output).

## Invariants (see data-model.md)
INV-1 authority coherence · INV-2 topology honesty · INV-3 no silent misroute (all `commit_router` primary-fallback sites fail loud) · INV-4 shared-rule consultation (kind-aware, not exit-code-uniform).
