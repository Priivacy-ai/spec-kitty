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

---

## POST-SPEC GROUNDING ADDENDUM — 2026-07-29 (paula / architect / priti, opus, on merged HEAD)

Second squad grounded every corrected claim against `feat/write-side-seam-matrix-tracer` @ merged base. Facts are file:line on HEAD; the spec was re-expanded a second time from these.

### Grounded facts that changed the spec
- **FR-007 (was FR-004) TRUE bypass set ≠ the "~12 `resolve_placement_only` callers".** Those 12 are the seam's own engine (`commit_router` ×4, `write_target_degrade`, `status_transition:300` = FR-006 mirror) — the census doc itself says none is a defect. The real adoption targets: caller-resolved-`feature_dir` writers (`write_acceptance_matrix` callers `gates_core.py:492`, `post_consolidation.py:275`, `accept.py`, `backfill_provenance.py:109`), the tracer must-build, the 4 coord-authority-gate write sites (`decisions/emit.py:71`, `widen/state.py:63`, `agent_tasks_ports.py:322`, `lanes/recovery.py:765`), #2663 (`implement.py::_partition_files_for_commit`), and the `status/emit.py` write (#2966 slice).
- **FR-008 merge-driver "row-aware" REFUTED.** `spec-kitty-acceptance-matrix`/`-issue-matrix` = whole-file `_write_more_filled_side` (`merge_driver.py:333/347/357`); only `-traces`/`-event-log` union. → operator chose to BUILD row-aware drivers on a structured schema (FR-002/FR-008).
- **FR-010 is interlocking ratchet surgery, not a one-liner.** Routing `decisions/emit.py` off the allow-list drops the write census 4→3 (trips `COORD_AUTHORITY_WRITE_FLOOR=4`), staleness twin-guard reds the allow-list entry, `test_coord_authority_by_design_modules_classified_write` hard-asserts emit.py present, and `coord_authority_baseline:4` must re-pin. Move A (route emit.py off = STRENGTHENING) + conditional Move B (widen gate by def-use + alias-bite non-vacuity test). NOT a blocker for the new `write_target`-routed writers (gate scans only `resolve_feature_dir_for_mission`).
- **FR-001 confirmed clean**: `overall_verdict` computed `@property`, `from_dict` excludes it (can't drift). Plus #2318 comment: `_evaluate_acceptance_matrix()` only writes on negative-invariants → stale `pending` after all-pass accept → FR-001 persist-on-accept + regression.
- **FR-009 lane-base = ONE ADR** (amends `2026-04-03-1`). MUST pin the base to a **recorded finalize-tasks SHA** (`lanes.json`/`meta.json`), never "current tip of target_branch" (moving-tip trap), and decide whether the base carries coord-status lineage (`auto_rebase._refuse_preexisting_lane_status_deletions:460-488` reasons over coord status in the merge-base). No consolidation abort path (`2026-07-23-2`). `merge/ordering.py` is a pure frontmatter topo-sort — NOT ancestor-dependent, untouched.
- **FR-011 zero-write condition**: the existing degrade path (`status_transition._resolve_write_target:640` → `get_feature_target_branch`) falls back to *writing* `main` — resurrects a closed defect + forecloses #3033's `CONSOLIDATED` decision. FR-011 must be a structured **zero-write refusal** that discloses #3033.
- **C-007 narrowed**: exactly ONE new ADR (FR-009); FR-007 + FR-010 are `contracts/` citation docs, not ADRs.
- **Defer-home fix**: issue-matrix domain re-homed #2400 → **#1746** (where #1738 lives); `at_tension_with #1742`. State: all core tickets OPEN; #3035 was samuelgoff's (now folded + reassigned, coordinated); new adjacents #2465 (read-axis, coordinate) / #3065.

### SCOPE EXPANSION — 2026-07-29 (operator, post-grounding)
Operator pulled the full issue-matrix cluster back into core and chose the structured path:
- **FR-006 answer → BUILD row-aware driver + STRUCTURED matrix schema** (issue-matrix markdown → JSON/YAML + per-item statuses + rendered md view + migrate all readers). FR-002/FR-008.
- **#2966 → FOLD status/emit.py route into FR-007** (route-only, C-003).
- **#1738 (multi-file discovery + merge gate) + #3035 (zero-ref not_applicable) + #2318 comment (persist-on-accept) → IN CORE.** Reverses the earlier issue-matrix deferral; only mission-card source #1742/#1740 stays `at_tension_with`.
- **#3035 reassigned** samuelgoff → operator, with a crediting coordination comment (their work reused downstream).
Spec re-expanded to 12 FRs + C-008 (structured-migration completeness). Commit: (this commit).

### RECOMMENDED WP/LANE SHAPE (for /plan — architect)
- **Lane A (P0, ADR-first):** WP author FR-009 ADR → retarget lane base + merge/ancestor tests. Files: `lanes/`, `merge/`. Must land before Lane C's SC-003 regression is meaningful. No consolidation abort path.
- **Lane B (enabler / routing prereq):** route `decisions/emit.py` off allow-list (+ conditional gate-predicate widen + non-vacuity test). FR-010. **Blocks Lane C.**
- **Lane C (writer adoption + matrix tooling, ONE seam):** WP parameterized write-seam core → acceptance command+persist (FR-001) → structured matrix schema + reader migration (FR-002/C-008) → issue verdict command (FR-003) → multi-file discovery + merge gate (FR-004) → zero-ref not_applicable (FR-005) → tracer writer (FR-006) → census-route incl. #2663 + status/emit.py (FR-007) → row-aware driver (FR-008); FR-011/FR-012 cross-cutting. **Reject any WP giving writers independent compute-and-commit paths** (re-leaks the pre-#3060 defect). Disjoint file scopes from Lane A. Gated by Lane B.

---

## POST-PLAN SQUAD FINDINGS + REMEDIATION PLAN — 2026-07-29 (paula/architect/priti, opus)

Verdict: **NOT ready for /tasks until the remediations below land.** Coverage is complete (zero FR holes); the gaps are one internal contradiction, two migration split-brain BLOCKERs, IC sizing, one sequencing edge, and merge-driver rigor. Remediation is authored here for turnkey execution (post-compact).

### BLOCKERS (must fix in plan/contracts before /tasks)
- **B1 (architect) — gate-site contradiction.** IC-02/coord-authority-gate.md route ONLY `decisions/emit.py` (floor 4→3, three by-design sites remain) but IC-03/FR-007/write-seam-adoption.md list ALL FOUR gate sites as "bypasses to route." The other three (`widen/state.py:63`, `agent_tasks_ports.py:322`, `lanes/recovery.py:765`) are **by-design sanctioned coord writes** — the `>=4` floor counts them to prove non-vacuity (`test_resolution_authority_gates.py:704-723/1661-1716`). Routing all four → census 0 → gate vacuous (forbidden by 2026-06-26-1). **FIX:** only `emit.py` is routed this mission; the three stay on the kind-blind resolver as by-design authority (floor→3). Correct write-seam-adoption.md line 11 (drop the three from the bypass set); add a non-vacuity invariant (census may not drop below the re-pinned floor).
- **B2 (paula F1) — basename→kind linchpin.** `artifacts.py:200 _MISSION_FILE_KIND_BY_BASENAME["issue-matrix.md"]` is the recognition seam (`kind_for_mission_file` → auto_rebase:227, commit_router, coherence). If the writer emits `.json` but the map only knows `.md`, `kind_for_mission_file(".json")` → None → not staged to coord / not row-merged / treated as primary residue (split-brain; vacuously green in kind-constructing unit tests). **FIX:** first red-first WP of IC-05a: add `"issue-matrix.json" → ISSUE_MATRIX` (keep `.md` for failover), with positive+negative recognition assertions.
- **B3 (paula F2) — finalize scaffold authors `.md` on PRIMARY.** `mission_finalize.py:355 _scaffold_issue_matrix_if_present` → `tasks/issue_matrix.py:94` scaffolds `issue-matrix.md` on the planning dir for EVERY new mission before any structured write → FR-013 migrate-on-write never fires greenfield → permanent split-brain on the wrong partition. **FIX:** migrate the finalize scaffold to author `issue-matrix.json` via `write_target(ISSUE_MATRIX)` (COORD); IC-05a owns `mission_finalize.py` + the scaffold write path.

### MAJORS (fold into plan/contracts same pass)
- **M1 (architect) — Lane B over-blocks Lane C.** Per D-6, `write_target`-routed writers are gate-invisible → IC-04/05/07 have NO real dep on Lane B. Only the `emit.py` gate-route slice touches the gate. **FIX:** IC-04/05/06/07 depend on the IC-03 **core**; IC-03's emit.py slice is the only Lane-B-gated part. Don't serialize the gate-invisible writers behind Lane B.
- **M2 (architect) — FR-009 coord-status-lineage × FR-007.** Planning artifacts live on PRIMARY `target_branch`; matrix/tracer/status are COORD (2026-06-24-1 §5). A lane based on the primary planning SHA doesn't share ancestry with the coord surface where SC-003 writes live — but once FR-007 routes those writes OFF the lane onto coord, part of the coord-lineage question is moot. **FIX:** IC-01 ADR must resolve coord-status-lineage explicitly in light of §5 + FR-007 routing; disentangle FR-009 ancestry (primary) vs FR-008 row-aware merge (coord) durability ownership (SC-003 bundles both).
- **M3 (priti) — split IC-05 → IC-05a (schema+canonical writer+basename map+finalize scaffold) / IC-05b (reader migration C-008 blast-radius) / IC-05c (migration sub-module FR-013 incl. the shared reader).** Split IC-06 → IC-06a (verdict cmd FR-003) / IC-06b (multi-file discovery + 3 enforcement sites + merge gate FR-004) / IC-06c (zero-ref not_applicable FR-005).
- **M4 (priti) — add hard edge IC-08 → IC-01** for the SC-003 durability regression (else false-green before Lane A lands); or split IC-08 into (driver-unit, base-independent) + (durability-integration, gated on IC-01+IC-08-unit).
- **M5 (priti) — third contracts/ doc: merge-driver algorithm** (3-way base-aware %O/%A/%B, row-key canonicalization by criterion_id/issue_ref, delete-vs-stale disambiguation). Currently only 2 contracts budgeted.
- **M6 (paula F4) — driver registration is 3 sites.** IC-08 must also update `cli/commands/init.py:73,194` (new-repo `.gitattributes` pattern) + author a NEW forward migration repointing `**/issue-matrix.md` → `issue-matrix.json` (do NOT mutate historical `m_3_2_6`). Else upgraded repos bind a driver to a filename that no longer exists → FR-008 clobber-protection silently absent.
- **M7 (paula F5) — one canonical reader.** The markdown parser `validate_issue_matrix` (`review/_issue_matrix.py:194`) is shared by doctor/review/finalize-lint/move-task. IC-05c's migration sub-module MUST host the single canonical `load_issue_matrix()→rows` (failover-read inside); all read sites call it. Else whack-a-field across 5 sites.
- **M8 (paula F3) — doctrine/skills consumers.** Update `spec-kitty-mission-review/SKILL.md:581/695`, `spec-kitty-implement-review/SKILL.md:499`, `mission-wrap-up-sequence.procedure.yaml:19/50`, `spec-kitty-core.glossary-pack.yaml:679/690/693` (incl. `ISSUE_MATRIX_SCHEMA_DRIFT`/mission-review gate def), `planning-and-tracking.styleguide.yaml:18` from `.md`→`.json`; run `test_no_legacy_terminology.py`. Add as an IC-05b sub-scope.

### MINORS
- **m1 (priti) — home FR-002's acceptance-schema half** explicitly in IC-04 (currently implicit).
- **m2 (paula F6) — fix C-008 consumer list.** Real live consumers = doctor, post-merge review, move-task/approval blocker, finalize lint, `kind_for_mission_file` recognition (auto_rebase/commit_router/coherence), merge-driver+registration (merge.py/init.py/migration), doctrine skills. DROP "dashboard" and "gates" from *migration* scope (dashboard reads nothing today = net-new build; merge_gates gains a reader via FR-004). → **ESCALATION E2.**
- **m3 (paula F7) — ~10 `.md`-shaped test files** are migration fallout; judge each (re-pin `.json` / migrate / delete obsolete markdown-parser tests). Name as explicit IC-05b fallout (not ad-hoc).
- **m4 (architect) — plan.md line 36 citation:** FR-010 implements `2026-06-26-1-single-authority-seam-and-call-site-gate`, NOT `2026-06-24-1`. Fix.
- **m5 (architect) — ADR hygiene:** `2026-06-26-1-single-authority-seam...` is status **Proposed** (de-facto shipped); two ADRs share date `2026-06-26-1` → cite by SLUG not bare date; either ratify to Accepted in this mission or contracts acknowledge "Proposed-but-shipped."
- **m6 (architect) — Move B (if triggered) = ADR amendment** of 2026-06-26-1, not a contract-only predicate-widen.
- **m7 (priti) — add #2274 to IC-01 blast radius** (lane-hygiene guard compares kitty-specs by commit-history not content → false-positive after the FR-009 planning-rebase). Coordinate #2273/#2626/#2570 (FR-009/FR-006 adjacent), #2555/#2228 (FR-006/FR-008 adjacent).

### ESCALATIONS TO HiC (need operator decision)
- **E1 — #2970** (5 BLOCKER S2083 path-injection findings in `merge_driver.py`, the exact file IC-08 rewrites). FOLD the security fix into IC-08 (Sonar attack-vector-campsite doctrine — you're rewriting the file) vs COORDINATE-only. Recommend FOLD.
- **E2 — Dashboard net-new-build.** The dashboard reads NO matrix today; "dashboard parses JSON directly" (operator decision) is a net-new build, not a migration. DROP dashboard from this mission's migration scope + file a follow-up for a JSON dashboard panel, vs INCLUDE a net-new dashboard panel here (scope growth). Recommend DROP + follow-up.

### CONFIRMED SOUND (no action)
FR-011 zero-write refusal ✓; FR-009 recorded-SHA + no-consolidation-abort + amends 2026-04-03-1 ✓; Lane A "before IC-08 regression" ordering ✓; write-seam-adoption/coord-authority-gate correctly citation-docs-not-ADRs ✓; FR→IC coverage complete (zero holes) ✓.
