# Tracer: Design Decisions

**Mission**: tasks-py-degod-wave2-01KWH9EQ
**Created**: 2026-07-02 (seeded at planning per `mission-tracer-files` procedure)
**Lifecycle**: seed at planning → append during implement → assess at close

## Seed decisions (from spec)

1. **Dedicated `tasks_command_adapters.py`** for the port-seam adapter classes rather than
   folding into `agent_tasks_ports.py` — breaks the ports ↔ command-modules import-cycle
   risk (debrief risk note). Deviation requires a recorded no-cycle argument.
2. **Honest LOC ceiling over target-hitting**: ≤1400 is a Wave 1 planning estimate; the
   gate records the real achievable number with rationale if higher (spec FR-004/NFR-004).
3. **Render seam indent parameterization** (or an indented-envelope capability) collapses
   `_StatusRender` instead of keeping a subclass override — one production adapter per
   port (#2173 / C-004).
4. **#2300 divergence frozen**: skip-vs-refuse behavior preserved verbatim (C-001);
   characterized by the golden harness, reconciled only in #2300's own mission.
5. **Boyscout bounded to the tasks domain** (charter standing order 2: domain-matched
   folds only); repo-wide #2034 fix stays upstream.

## Post-spec squad decisions (2026-07-02)

6. **Seam bridge = lazy parent-module attribute routing** (`_tasks.<attr>`), the proven
   `mission.py` template mechanism — NOT bare module-level re-exports, which do not
   preserve patch interception (squad CRITICAL, alphonso+renata convergent).
7. **Byte-freeze suite before routing**: the shape-checked harness JSON legs cannot carry
   the byte-identity claim; 13 byte-exact characterization cases are committed BEFORE the
   render-seam change (squad CRITICAL, renata).
8. **LOC ceiling = min(achieved, 1400)**, >1400 escalates to the operator — closes the
   self-certification hole (renata).
9. **Ratchet re-point ≠ fixture adjustment**: the coord-harness branch-coverage ratchet is
   re-pointed per relocation WP; deletion/floor-lowering forbidden (FR-012).
10. **Shared-helpers module added** (FR-003) — the ~30 cross-family helpers were the
    decomposition blind spot (priti).

## New decisions (append during implement)

_(none yet)_

## Implement-loop decisions (2026-07-02)

11. **Ratchet map is MULTI-HOME** (`{floored_name: ((module, qualname), ...)}` — entry
    orchestrator + its Wave-1 pure cores), superseding parity-contract Layer 3's
    single-home literal. WP05 discovered all three floors were vacuously calibrated
    pre-rewrite (thin wrappers ≈ 0 arcs + the `else 100.0` arm); the reviewer's decisive
    experiment: the single-home form FALSE-REDS (map_requirements 45.9 < 48, status
    45.8 < 46), so the cores are calibration-necessary. WP06/WP07 re-points ADD the
    relocated family module to the entry-home tuple, keeping the core homes.


## WP09 close-out (2026-07-02)

12. **tasks_ports.py shim disposition (FR-008): DELETED** — the importer census
    (`grep -rn "cli.commands.agent.tasks_ports" src/ tests/`) found ZERO importers
    of the shim path; every consumer already imports the canonical
    `specify_cli.agent_tasks_ports` directly, so the "re-point-and-delete" arm was
    degenerate (nothing to re-point). Evidence reproduced in the disposition
    commit (8514ee77c) message; #2289 fence respected — only the shim touched.
13. **AST dumps-gate allowlist is NOT empty at ship time** — gate-contracts.md
    predicted 0 sites; that held for the mission's remit (`tasks*.py` ships at 0,
    asserted), but the whole-directory glob (the anti-move-next-door scope)
    swept in 9 PRE-EXISTING non-tasks siblings (~28 inline dumps sites:
    status.py, mission_finalize.py, mission_accept_merge.py, context.py,
    config.py, mission_parsing.py, release.py, tests.py, workflow.py) that
    belong to the #2289–#2293 unshim surface. Rewriting them was out of
    ownership; enrolled via the contract's own exception mechanism
    (repo-relative paths, shrink-only count ratchet + stale-entry eviction +
    a no-tasks-family-entry assertion). Follow-on burn-down belongs to the
    unshim cluster.
14. **Final ceiling 1206 (min(1206, 1400))** — the sweep relocated the 12
    straggler helpers (6 → move_task, 4 → status_cmd, 1 → map_requirements,
    1 → mark_status) as explicit `as` re-export seams; tasks.py's final def
    census is EXACTLY the 9 `@app.command` wrappers. Standing
    `assert _CEILING <= 1400` mission-cap backstop landed.
15. **Mission-introduced arch-gate drift adjudicated at WP09, not absorbed** —
    4 gates RED on the lane but GREEN on degod-follow-ups (cross-base verified
    in a detached worktree): 2 dead-symbol allowlist burn-downs (wave-2 seam
    bridge gave the symbols live src/ callers) and the coord-authority
    write-census 9 → 7 (WP04's render-seam unification removed the `dumps`
    write-indicator from list_tasks/validate_workflow, re-classifying their
    kind-blind probes as reads) — allowlist drained, baseline+floor lowered
    shrink-only with the margin gate satisfied.


## degod-follow-ups close-out (PR #2308, 2026-07-03)

16. **Coord-router constructor-DI collapse (pre-merge squad MEDIUM, architect
    lens)** — the three near-triplicated `RealCoordCommitRouter` subclasses in
    `tasks_command_adapters.py` (`_MoveTaskCoordRouter`, `_MapReqCoordRouter`,
    `_MarkStatusCoordRouter`) existed ONLY to (a) re-resolve `commit_for_mission`
    / `emit_status_transition_transactional` through the `tasks` namespace so the
    legacy `@patch("...agent.tasks.<sym>")` seams intercept, and (b) thread
    `target_branch` (MapReq only) — bending the one-adapter-per-port rule (C-004)
    the module documents. **Fix (squad's recommendation):** collapse into the
    base `RealCoordCommitRouter` via **constructor DI**. The base gained
    `commit_fn` / `emit_fn` seam-callable params (default to the module-bound
    `agent_tasks_ports` seams → base production behaviour byte-identical) and a
    `thread_target_branch: bool` flag SEPARATE from the `target_branch` value
    (deriving the flag from `target_branch is not None` would collapse the two
    byte-distinct call shapes — MapReq always passed the kwarg, MoveTask/MarkStatus
    never did). A single `tasks_command_adapters.seam_coord_router(*,
    thread_target_branch, target_branch, route_emit)` factory injects two
    module-level wrappers (`_seam_commit_for_mission` /
    `_seam_emit_status_transition_transactional`) that do the lazy
    `from ...agent import tasks as _tasks` import at CALL time — so a `@patch`
    applied AFTER construction still intercepts (late binding preserved by
    call-time resolution, exactly as the deleted subclass bodies did). C-001
    divergence preserved exactly: move_task = `route_emit=True` (both seams
    routed), map_requirements = `thread_target_branch=True` (commit-seam routed +
    ff-advance), mark_status = plain (commit-seam routed, target-branch-less).
    tasks.py's three-symbol re-export block collapsed to one `seam_coord_router`
    re-export → 1206 → 1205 lines; `_CEILING` ratcheted 1206 → 1205 in the same
    change. **Next-degod guidance now IMPLEMENTED here:** future port families that
    only differ in seam-namespace routing or a single threaded arg should reach
    for constructor DI + a shared seam factory, never a per-family subclass.

17. **LOC ceiling gate REMOVED (operator ruling, 2026-07-03)**: raw file-size
    tests are Sonar's job (quality gate / S104); a hard-coded pytest ceiling is
    tests-as-friction (every legitimate edit → test edit). The gate served its
    purpose as the mission's ratchet-down instrument (4569→1205, per-WP
    same-commit lowering) and retires WITH the mission. What remains: the
    semantic AST dumps gate (suite-owned) + the registration-shim header
    guidance in tasks.py + Sonar. Supersedes FR-011's standing-gate clause
    post-accept; gate-contracts.md Gate 2 marked retired.

18. **Refactor-stable test doctrine applied (operator ruling, 2026-07-03)**:
    "if arch/acceptance tests need to change on every cleanup/refactor, they
    are not good tests." The two positive literal-presence scans in
    test_context_worktree_routing.py (routed-seam literals; selector-resolver
    literal) were DELETED — not re-pinned again — with surviving-coverage
    proof: the negative AST no-inline-compose invariant (extended over the
    relocated modules), the behavioral --feature-rejection contract tests,
    and the seam interception batteries. The negative mid8-dedup scan was
    strengthened (parametrized over all routed files). Positive literal scans
    red on every wave; negative/behavioral forms red only when the defect
    class returns.
