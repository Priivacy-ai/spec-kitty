# Pre-Planning Ledger — write-side-seam-matrix-tracer

**Created**: 2026-07-29 · **Base**: main `39f462a4f` (PRE-#3060-merge) · **Status**: pre-planning, PARKED until #3060 lands
**Squad**: 3 profile-loaded opus lenses via charter seam — paula-patterns (campsite/code-state), architect-alphonso (design viability), planner-priti (related-issue precision). Read-only.

This ledger is the durable output of the pre-planning squad. The spec (`spec.md`) is intentionally left `Draft`; the "Spec corrections" section below is the change-list to apply **at resume, before `/plan`**, once #3060 has merged.

---

## HEADLINE — this is an ADOPTION mission, not a construction mission

The write primitive, the lane→coord materialization authority, and both matrix writers **already exist on current main**. Only the tracer-finding writer is genuinely must-build. The work is routing existing writers/call-sites through the existing seam — mirroring how #3060 migrated the *read* side.

**The metric that frames the whole mission:** ~80 seam-routed `read_dir` call sites vs **~3** seam-routed `write_target` consumers. FR-004 = close that asymmetry (census-and-route), not build a resolver.

---

## Extend-points that ALREADY EXIST (cite these; do NOT rebuild)

| Concern | Existing surface | Citation |
|---|---|---|
| Write-side seam primitive | `PlacementSeam.write_target(kind)` → `resolve_placement_only(root, slug, kind=)` (kind-aware, CWD-invariant) | `src/mission_runtime/resolution.py:1395`, `:1228` |
| Lane-origin → coord routing (FR-003 mirror) | `_resolve_write_target(...)` → `resolve_write_target_or_degrade` → `resolve_placement_only` | `src/specify_cli/coordination/status_transition.py:640` |
| Coord materialization authority | `commit_for_mission` (`_group_files_by_partition`, `_materialise_coord_worktree`) | `src/specify_cli/coordination/commit_router.py:127`, `:405`, `:577` |
| Acceptance-matrix writer | `write_acceptance_matrix(feature_dir, matrix)`; **computed** verdict `overall_verdict` (+`VERDICT_PASS_PENDING_CONSOLIDATION`); negative-invariant machinery (#2743) | `src/specify_cli/acceptance/matrix.py:259`, `:191`, `:55`, `:461/:420/:556`, grep-absence `:619` |
| Issue-matrix scanner (single-file = #1738) | `detect_issue_references(spec_md_path)` reads `spec.md` ONLY; `scaffold_issue_matrix` (idempotent) | `src/specify_cli/tasks/issue_matrix.py:51`, `:65`, `:75` |
| File→kind classifier (consult, don't re-hardcode literals) | `_MISSION_FILE_KIND_BY_BASENAME` / `kind_for_mission_file` | `src/mission_runtime/artifacts.py:195` |
| Governing ADRs | partition + **C-006 rejects a parallel write resolver** (`2026-06-24-1`); `target_branch` from `meta.json` primary anchor (`2026-06-24-2`); surface vocab — "COORD is not conditioned on topology" (`2026-07-23-1`); post-consolidation deferral (`2026-07-23-2`) | `docs/adr/3.x/` |

**#3060 boundary is clean:** its diff is read-side only (`primary_feature_dir_for_mission` → seam delegation; internal callers to the `_compose_primary_feature_dir` leaf to dodge the Ledger-M16 recursion). Nothing in the write projection, matrix writers, lane allocator, or tracer path changes. **The rebase risk is conceptual drift, not merge conflict.**

---

## MUST-BUILD (the one genuine construction)

- **FR-003 tracer-finding writer.** `TRACER_FILE` classification exists (`artifacts.py:181`, `"traces"` map `:230`) but there is **only a reader** (`retrospective/generator.py:268/:282`, live literal `"traces"`). Agents currently append into the mission dir directly — on a lane that means the lane worktree's `kitty-specs/`, committed on the lane branch (the #2980/#2549 barrier). Build the routed writer that lands `traces/` on COORD via `commit_for_mission`.

---

## LANDMINES / structural risks

1. **FR-005 is a git-topology change, not routing.** The coordination branch is minted at `mission create` off `target_branch` **before** spec/plan/tasks exist (`core/mission_creation.py:61-66`, `:446`); planning artifacts (`_PRIMARY_ARTIFACT_KINDS`) land on `target_branch` afterward. So a lane branched off the coord tip has **no common ancestor containing planning artifacts** with the consolidation base — confirmed = the #2993 P0. Blast radius: `lanes/worktree_allocator.py:215/:227`, `lanes/auto_rebase.py`, `merge/executor.py`, `merge/ordering.py`, dependent-lane invariant **#1684**. → **own WP, own ADR, explicit merge/ancestor tests.** Different risk class than the P2 writer FRs.
2. **FR-004 = census-and-route, guard the recursion.** ~12 direct-caller bypasses of `resolve_placement_only` across 8 modules (census: `docs/architecture/artifact-placement-seam.md`). Live seam-write consumers are only ~3 (`core/mission_creation.py:190`, `cli/commands/agent/mission_record_analysis.py:122`, `cli/commands/agent/workflow.py:568`); direct bypasses incl. `coordination/status_transition.py:300`, `git/bookkeeping_commit.py:196`, `events/decision_log.py:136`. Guard the **Ledger-M16** recursion (public boundary → seam, internal callers → leaf).
3. **Both matrix writers take a caller-resolved `feature_dir` and bypass the seam.** Both kinds are COORD (`artifacts.py:174-175`; `commit_router.py:705-717`). A verdict command that writes to a caller-supplied dir strands the COORD artifact on the wrong partition — the identical failure class #3060 just closed on the read side. FR-001/002 must thread them through `write_target(ACCEPTANCE_MATRIX/ISSUE_MATRIX)`.
4. **Verdict is a COMPUTED property.** The command materializes + routes; it must **not** re-author verdict semantics or create a second hand-stored source of truth that drifts from `overall_verdict` (#2743 negative-invariant integrity).

---

## ONE-SEAM DISCIPLINE (Paula's whack-a-field guard)

All four write concerns (acceptance verdict, issue verdict, tracer routing, generic write) are the **same missing adoption**. A plan that gives FR-001/002/003 each a bespoke "compute path + commit" reproduces the pre-#3060 read-side leak **three times**. Insist on: **(a) one write-surface resolution (`write_target`), (b) one materialization authority (`commit_for_mission`), (c) parameterized scanner/writer cores with thin per-kind wrappers.** Reject any WP slice that gives the writers independent compute-and-commit paths.

---

## COLLISIONS & DEPENDENCIES

- **#2663 (OPEN, tech-debt) — pull into FR-004.** The write-partition split (`_partition_files_for_commit`, verbatim implement-claim arm committing the whole batch to coord instead of partitioning) is *already isolated* — the exact write twin FR-004 unifies. Stopgap shipped PR #2662. Leaving it unnamed invites a duplicate partition impl + a C-001 seam-bypass allow-list.
- **#3033 (P0, OPEN) — scope decision required.** Post-merge writes against a deleted `target_branch` must **succeed** (governing `2026-07-23-2`), but FR-004 routes *all* writes through the seam and the spec frames a missing surface as "return error." Not in C-006. Fold, or make it explicit out-of-scope **with a guard**, before FR-004 lands — else FR-004 inherits a P0.
- **#3055 (OPEN) — routing PREREQUISITE, not merely a deferred gate.** The coord-authority gate (`tests/architectural/test_resolution_authority_gates.py`) does not yet recognize the seam idiom for COORD writes; `decisions/emit.py:71` is allow-listed pending it. Routing tracer/matrix COORD writes will hit the **same gate** and can be **blocked** until #3055's idiom-teaching lands.
- **FR-002 source-of-truth tension (#1738 vs #1746/#1742).** The multi-file scanner (#1738) and the machine-authored `mission-card.json` `closes_issues` path (Mission Clarity Layer epic #1746 / gate #1742) are two canonical sources for the same data. Reconcile: scanner is **interim-authoritative** with a seam for a mission-card source; add a `relates`/`at_tension_with` link to #1742.
- **#2966 (P2, OPEN)** — "port `status/emit.py` to `write_target`" overlaps FR-004 status routing; C-003 (route-only, don't rebuild the engine) keeps it consistent; coordinate to avoid double-work.
- **#2960 (OPEN)** — `agent:""` annotation silently blanks attribution (reducer guards `is not None`); relevant to FR-003's "attributed findings" promise → in-mission campsite.
- **#3035 (OPEN)** — gate-side twin of FR-002's no-ref no-op edge (gate still demands `issue-matrix.md`); close the edge on both sides or note as adjacent.

---

## SPEC CORRECTIONS to apply at resume (before `/plan`)

1. **Reframe FR-004** (Context prose + FR-004 row): "**extend** `write_target`/`commit_for_mission`; census-and-route the ~12 write bypasses (mirror #3060's read migration)" — NOT "build the write twin." Cite ADR `2026-06-24-1` **C-006** (no parallel write resolver).
2. **Fix the prereq/traceability line** (~L139): "#3060 closes **#2886**; **#3014 already resolved independently** (empty `closedBy`); #3055 deferred." (#3014 was NOT closed by #3060.)
3. **Fix the Assumptions merge-driver line** (~L161): replace "the union merge driver" with the **four dedicated drivers** (`spec-kitty-traces` / `-issue-matrix` / `-acceptance-matrix` / `-event-log`); note FR-006 depends on `spec-kitty-acceptance-matrix` being **row-aware** (confirm, don't assume).
4. **Re-weight FR-005**: its anchor **#2993 is a P0**; mark FR-005 as an ADR-gated structural lane-base change in its own WP/lane (see Landmine 1).
5. **Add #3033 to C-006 scope decision** (fold vs out-of-scope+guard).
6. **Promote #3055** in the spec from "deferred gate" to **routing prerequisite** for FR-001/FR-003 COORD writes.
7. **Add FR-002 source-of-truth reconcile note** vs #1746/#1742.
8. **Extend the traceability table**: #2663 → FR-004 core; #2960 → FR-003 campsite; #3035 → FR-002 adjacent.
9. **FR-001 note**: `write_acceptance_matrix` exists; the command *fronts + routes* it and keeps the computed verdict authoritative.
10. **Verify `traces/` vs `ln/` naming via `Read`** (the scout's grep output was redacted by the environment — a display artifact; live literal is `"traces"`).

---

## RESUME DECISIONS — RESOLVED 2026-07-29 (operator, post-#3060-merge)

- **A — FR-005 home → BUNDLE into core mission.** Kept in the single core mission (one lane), but marked ADR-gated (C-007) and reviewed as its own WP with explicit merge/ancestor tests.
- **B — #3033 → OUT-OF-SCOPE + graceful guard.** FR-009 now degrades gracefully on a deleted `target_branch`; the real post-merge write mode is fast-follow #3033 (C-006).
- **C — FR-002 issue source-of-truth → DEFERRED to its own slice.** The issue-matrix verdict command + multi-file reference discovery (#2583/#1738) move to the WP-metadata authority slice (#2093 WP-metadata authority split, #2400 metadata & profile authority sub-epic) — it is its own technical problem domain tied to the reader surface and open P0s. This mission keeps issue-matrix **placement-routing only** (FR-002 narrowed). Gate twin #3035 travels with the deferred slice.
- **D — #3055 → FOLDED into this mission.** New FR-010 teaches the coord-authority gate the write-side seam idiom (routing `decisions/emit.py` off the allow-list), unblocking FR-001/FR-003 COORD routing.

**Spec corrected accordingly** (2026-07-29): FR-004 reframed to census-and-route (not "build twin"); #3014 prereq fixed; four-dedicated-merge-drivers replaces the union-driver assumption; FR-005 re-weighted P0/ADR-gated; C-007 added; #2663 folded into FR-004; FR-010 added; issue-matrix narrowed. #3060 confirmed MERGED (`e6806f184`) and rebased; `write_target`/`write_acceptance_matrix` intact, `primary_feature_dir_for_mission` gone — all extend-points verified against the merged base.
