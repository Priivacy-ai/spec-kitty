# Research — Degod tasks.py (Wave 1)

Phase 0 output. Most decisions were settled by two pre-plan squads (sizing/arch/parity, then
coherence/doctrine/program-alignment) against the current code; recorded here as the design
rationale. No open NEEDS CLARIFICATION.

## D1 — Golden-characterization-first (behavior-preserving safety net)
- **Decision**: Freeze the full observable `agent tasks` contract with a golden CLI-characterization harness **before** any extraction; every WP must keep it byte-identical (pure parity).
- **Rationale**: DIRECTIVE_041 (tests-as-scaffold, observable-contract). The refactor's safety rests entirely on this. The existing `test_tasks_cli_contract.py` (#2058/#2114) exists but *by its docstring* punts the coord skip-exit-0 arm and covers no mutating command — so the harness must be **extended with a coord-topology + protected-branch fixture** that drives `move_task`/`mark_status`/`map_requirements` and freezes their exit codes, polymorphic `--json` keys, and side effects.
- **Alternatives rejected**: relying on the existing helper tests (`test_move_task_guard.py`, #1618) — they pin the *helper structure* the refactor dissolves, so they'd break on extraction rather than protect it.

## D2 — Stratified port set; coord WRITE is a TWO-CAPABILITY port (post-squad correction)
- **Decision**: `FsReader` (coord READ) and `CoordCommitRouter` (coord WRITE) are program-reference ports Wave 2 reuses; `GitOps` and `Render` are **mission-local scaffolding**, not reference ports. The WRITE port exposes **two capability methods over two structurally disjoint real seams** — `commit_status(event, *, capability)` over `emit_status_transition_transactional` (keyed `GuardCapability`, self-atomic via `BookkeepingTransaction`) and `commit_artifact(paths, message, *, kind, policy)` over `commit_for_mission` (keyed `MissionArtifactKind` + `ProtectionPolicy`) — **not** a single `commit()` that fuses them.
- **Rationale (corrected against live Wave-2 seams)**: the three Wave-2 consumers use **disjoint halves** — `implement.py` uses only the emit leg (`emit_status_transition_transactional`, zero `commit_for_mission`); `acceptance/__init__.py` uses only the artifact-commit leg (routes `commit_for_mission` on protected primaries, direct `run_git commit` otherwise, `write_meta` — i.e. it **is a writer**, event-less); `move_task` uses both. A single fused `commit()` whose consumers each touch one half is a mis-cut capability that Wave 2 re-cuts — the exact C-006/D2 failure. **The earlier "acceptance does zero writes" premise was factually inverted**; the real proof of CoordRead≠CoordWrite is *capability-disjointness* (acceptance uses `commit_artifact` without `commit_status`), which is precisely why the WRITE port needs two methods. `#2173` already adjudicated GitOps + Render as DROP.
- **Atomicity note (INV-2 restated)**: the #2160 atomicity is a property **inside** `emit_status_transition_transactional` (`BookkeepingTransaction.acquire`), not of port packaging. A co-equal `commit_status` method routing through it is equally atomic — so there is **no** "peer StatusEmit reintroduces split-brain" hazard, and that spurious fear must not force a fused single `commit()`.
- **Alternatives rejected**: 5 co-equal reference ports (mis-shapes the program); a single fused `commit()` (mis-cut — Wave 2 re-cuts it); a unified coord read+write port (violates C-001).

## D3 — #2072 composite-key re-key is a HARD PREDECESSOR
- **Decision**: #2072 Obligation-A (migrate the tasks.py `coord_authority` census entries to composite-key: qualname+token, line-independent) must **land before the first body extraction**, not run "in parallel".
- **Rationale**: DIRECTIVE_041 stable-anchoring. Body-thinning shifts every line in tasks.py; file:line-keyed census entries would force a manual re-key on every WP (the exact friction #2072 removes). Under composite-key the entries survive the rewire untouched.
- **Alternatives rejected**: parallel #2072 (re-key thrash per WP); file:line re-key inside this mission (fights the shrink-only ratchet).

## D4 — Pure parity; the cross-command unification is deferred (#2300)
- **Decision**: This mission preserves all current behavior. The real skip-vs-refuse inconsistency (`move_task` skips-exit-0; `mark_status`/`map_requirements` refuse-exit-1 on coord+protected) is NOT reconciled here.
- **Rationale**: Reconciling it changes ≥1 command's observable behavior → contradicts the pure-parity guarantee that makes the golden test a clean safety net. Deferred to #2300 (characterize-then-intentionally-diff).
- **Alternatives rejected**: unify inside the degod (self-contradictory: FR-004-unify vs NFR-001-parity — flagged by the squad).

## D5 — Inject at the orchestrator boundary, not the Typer command
- **Decision**: The port is a `*, ports=None` keyword param on an extracted `_do_<command>(...)` helper; the `@app.command` stays a thin shell that reads its options and delegates.
- **Rationale**: Typer introspects every parameter of a decorated command; a Protocol-typed `port=` becomes an unwanted `--port` flag / registration failure. The `#2056` template sidesteps this the same way.
- **Alternatives rejected**: `port=` on the command signature (Typer collision); a module-global port (untestable, hidden state).

## D6 — 9 strictly-linear work packages (post-tasks squad resize)
- **Decision**: golden harness → ports (+FR-010 proof) → 3 cores (move_task, mapping, status) → move_task rewire → **core-backed rewire (map_requirements+status)** → **coreless rewire (mark_status+finalize_tasks, +non-import gate)** → render+shim+census.
- **Rationale**: the pre-plan sizing squad lifted 6→8; the post-tasks squad then split the overloaded 4-body rewire WP into a core-backed slice (WP07) and a coreless slice (WP08) — leaving render+shim+census as WP09. Strictly linear per the #2056 template (each WP builds on the prior; shared `tasks.py` rewire surface forbids parallelism).

## D7 — ATDD-for-refactor: the per-core unit test is the red-first artifact
- **Decision**: For the pure-parity extraction WPs, the failing-first (charter C-011) artifact is the **per-core unit test** (RED against the not-yet-extracted core), not a CLI-boundary test (the golden harness stays green throughout).
- **Rationale**: Pure-parity WPs deliver no new user-observable behavior, so nothing goes red at the CLI. The genuine red-first is the unit test of the core being created.

## D8 — FR-010 pre30 read-authority unification: byte-identical ONLY with pinned kinds + a proof artifact
- **Decision**: Migrate the 3 kind-blind `resolve_feature_dir_for_mission` reads (resolver calls at `move_task:1138`, `finalize_tasks:2373`, `list_dependents:3568`) to kind-aware `resolve_planning_read_dir`, **pinning the exact `MissionArtifactKind` per site** (the in-file exemplars diverge — the migrated `add_history` guard uses `TASKS_INDEX`, the finalize/list_dependents *other* reads use `WORK_PACKAGE_TASK` — so the kind is a real per-site decision, not a default).
- **Rationale**: DIRECTIVE_044 unification of a **real** coord-read split-brain: on a coord topology `resolve_feature_dir_for_mission` returns the `-coord` husk while `resolve_planning_read_dir` returns the primary read dir — **they differ by construction**. So "same on-disk dir" is NOT free; it holds only for the correct kind. Because WP01 builds a coord fixture, a wrong kind is the single most likely parity break in the mission.
- **Guardrail**: ship a **dir-equivalence proof artifact** as a WP02 deliverable — a targeted test asserting, for each in-scope kind on the coord fixture, `resolve_feature_dir_for_mission == resolve_planning_read_dir(kind=…)` for the pre30 guard — **before** any WP06/WP08 rewire. Not a WP06 runtime "stop if it shifts."

## D10 — Factual re-census against live tasks.py (squad-verified; anchors are indicative)
- **Decision**: Treat all cited line anchors as indicative and **re-census at WP-start**. Squad-verified facts: `tasks.py` = 3617 LOC; 9 subcommands / 53 params (both TRUE); bodies move_task 831/19, status 488, map_requirements 426, mark_status 280, finalize_tasks **172** (not "mega"); `json.dumps` = **13** (not 17) at lines 442/480/493/2035/2235/2726/2751/2765/2854/2926/3022/3264/3605; floors `COORD_AUTHORITY_WRITE_FLOOR=12` (12 live entries → at floor), `CANONICALIZER_FLOOR=45`, `ROUTED_CANONICALIZER_FLOOR=38` (all TRUE); refuse raises at `mark_status:1952` / `map_requirements:2629`; skip arm `skip_target_branch_commit` fall-through at 1083→1648/1783 (no `typer.Exit(0)` in file). **#2072 HAS landed** (allowlist composite-keyed) → WP03 not blocked.
- **Rationale**: FR-011/NFR-005 drain + the shim/render gates require truthful counts; a gate pinned to a phantom "17" fails on the true starting count. Rename the contract's `CommitResult` (collides with `git/commit_helpers.py:424`) to `CommitStatusResult`/`CommitArtifactResult`. Fix stale `coord_authority_baseline: 13`→12.

## D9 — FR-011 census: drain + shrink-only floor (not re-key)
- **Decision**: As bodies thin, resolve sites that lose their write indicators reclassify WRITE→READ and **drain** from the census; `COORD_AUTHORITY_WRITE_FLOOR`/`CANONICALIZER_FLOOR` lower shrink-only.
- **Rationale**: DIRECTIVE_043 shrink-only ratchet. With #2072 composite-keying first (D3), there is no file:line to re-key — the honest move is drain + floor-lower. WP08 + mission-merge run the full arch cross-base sweep (`post-merge-arch-gate-adjudication`).
