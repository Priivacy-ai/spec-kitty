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
