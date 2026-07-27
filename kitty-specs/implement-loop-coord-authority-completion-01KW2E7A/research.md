# Research — implement-loop-coord-authority-completion-01KW2E7A

## FR-008 residual-discovery sweep

**Author:** architect-alphonso (directives applied: 001 architectural-integrity / PRIMARY-vs-STATUS
partition boundary; 003 decision-documentation / every verdict carries rationale; 031 context-aware
design / bounded-context partition is the binding constraint; 041 tests-as-scaffold / the
`_DIR_READ_KNOWN_RESIDUALS` pin must reflect real residuals, not mask them).

**Method:** full census of every call site of the four coord-aware resolvers in `src/specify_cli/`
(`candidate_feature_dir_for_mission`, `resolve_feature_dir_for_mission`, `resolve_feature_dir_for_slug`,
`resolve_handle_to_read_path`). 111 actual invocations (excludes defs / imports / docstring mentions).
Each site's resolved dir was traced to the artifact it reads/writes and triaged against the partition
authority in `src/mission_runtime/artifacts.py`.

### Load-bearing facts that settle several verdicts

- **`lanes.json` (LANE_STATE) is PRIMARY-partition** (`artifacts.py:99` — "LANE_STATE (lanes.json,
  finalize output) travels with tasks.md → PRIMARY"). Therefore **every `lanes.json` read off a
  coord-aware resolver is a coord-topology bug**, on par with a `tasks/` read. This reclassifies a
  large cluster in `merge/`, `lanes/`, `workspace/`, `core/worktree_topology.py`.
- **`meta.json` (PRIMARY_METADATA) is PRIMARY-partition**, but the guarded resolvers internally
  canonicalize to the primary dir for identity, so most bare `resolver(...)/"meta.json"` reads are
  lower-risk identity probes — flagged, ticket-if-out-of-loop, not core ROUTE.
- **review-cycle sub-artifacts under `tasks/WP*/` are an intentional coord-aware matched read/write
  pair (C-008)** — they STAY coordination-aware. This is what makes the pinned `implement` / `review`
  functions MIXED-READ (some legs route, the review-cycle leg keeps).
- The current arch-gate scanner walks **only `cli/commands/` (+`acceptance/`)** and matches **only the
  two-hop form** `d = resolver(...); d / "tasks"` — it is structurally blind to (a) the inline form
  `resolver(...) / "tasks"` (FR-007) and (b) every read surface outside `cli/commands/`.

### Verdict tally

| Verdict | Count |
|---|---|
| ROUTE (in-loop PRIMARY read — true residual) | 31 sites / ~18 functions |
| MIXED-READ (per-leg split, C-001 — highest risk) | 5 functions |
| TICKET-AND-PIN (out-of-loop PRIMARY read) | 18 sites |
| KEEP (STATUS read / identity-existence probe / write / C-008 coord pair) | ~57 sites |
| AMBIGUOUS | 0 (2 low-confidence noted inline) |

Currently pinned in `_DIR_READ_KNOWN_RESIDUALS`: 6 functions — `tasks.py::finalize_tasks`,
`tasks.py::status`, `workflow.py::_preview_claimable_wp_for_mission`,
`workflow.py::_resolve_review_context`, `workflow.py::implement`, `workflow.py::review`. (Note
`merge.py::_mark_wp_merged_done` was unpinned when it relocated to `merge/done_bookkeeping.py`, which
is outside the scan scope — so the 7th residual is now gate-invisible.)

---

### ROUTE — in-loop PRIMARY-kind reads (the true in-scope residual set)

| file:line | function | artifact | shape | gate-visible? | rationale |
|---|---|---|---|---|---|
| cli/commands/agent/tasks.py:2276 | `finalize_tasks` | tasks.md / `tasks/` | two-hop | pinned | finalize reads WP tasks on PRIMARY surface |
| cli/commands/agent/tasks.py:2108 | `list_tasks` | `tasks/` | **inline** | **blind** | `agent tasks list`, same defect as `status` (spec-named) |
| cli/commands/agent/tasks.py:3415 | `list_dependents` | `tasks/` via `build_dependency_graph` | two-hop | **blind** (join inside helper) | dependency graph reads WP tasks |
| cli/commands/agent/tasks.py:247 | `_map_requirements_feature_dir` | WP-task frontmatter | inline | blind | maps requirements from PRIMARY WP tasks |
| cli/commands/agent/tasks_dependency_graph.py:118 | `_check_dependent_warnings` | `tasks/` via `build_dependency_graph` | two-hop | **blind** (join inside helper) | dependency-warning scan reads WP tasks |
| cli/commands/agent/tasks_parsing_validation.py:935 | `_validate_ready_for_review` | meta.json + research.md | two-hop | blind | research.md is PRIMARY-kind |
| cli/commands/agent/workflow.py:1067 | `_preview_claimable_wp_for_mission` | `tasks/` | two-hop | pinned | claimable preview reads WP tasks |
| cli/commands/agent/workflow.py:1932 | `_resolve_review_context` | **lanes.json (PRIMARY)** | two-hop | pinned | LANE_STATE is PRIMARY — coord husk lacks lanes.json |
| cli/commands/agent/workflow.py:2110/2115/2116/2121/2124 | `_find_first_for_review_wp` | `tasks/` | **inline** | **blind** | review auto-find when no WP arg (spec-named) |
| merge/done_bookkeeping.py:237 | `_mark_wp_merged_done` | `tasks/WP*.md` | inline | **blind (outside scan)** | 7th residual; var misnamed `primary_feature_dir`, assigned coord-aware resolver |
| merge/forecast.py:153 | `run_dry_run_forecast` | lanes.json (PRIMARY) | inline | blind | merge dry-run reads lane state |
| merge/forecast.py:159 | `run_dry_run_forecast` | WP review artifacts | inline | blind | merge forecast WP-task read (review-cycle leg may KEEP — confirm C-008) |
| merge/executor.py:976 | `execute_merge_with_recovery_state` | lanes.json (PRIMARY) | inline | blind | merge executor reads lane state |
| lanes/merge.py:68 | `_resolve_lane_manifest` | lanes.json (PRIMARY) | inline | blind | lane manifest load |
| lanes/merge.py:198 | `merge_mission_to_target` | lanes.json (PRIMARY) | inline | blind | mission merge reads lane state |
| lanes/recovery.py:611 | `recover_context` | lanes.json (PRIMARY) | two-hop | blind | recovery reconstructs lane context |
| core/worktree_topology.py:138 | `materialize_worktree_topology` | lanes.json (PRIMARY) | inline | blind | topology materialization (implement entry) reads lane state |
| context/resolver.py:163 | `resolve_context` | meta.json + tasks/WP*.md | two-hop | blind | WP execution-context resolution for implement |
| workspace/context.py:470/666/714/752/790/853 | `_resolve_matching_context` / `build_normalized_wp_index` / `get_wp` / `get_lane` / `resolve_wp_execution_context` | `tasks/` + lanes.json (PRIMARY) | inline | blind (coord-aware twin `resolve_feature_dir_for_slug`) | reached by status/implement/review (spec-named) |
| task_utils/support.py:309 | `ensure_task_integrity_for_feature` | `tasks/` | inline | blind | task-integrity for implement loop (low-confidence on loop-membership) |

### MIXED-READ — same resolved dir feeds BOTH a PRIMARY and a STATUS leg (C-001 — must split per-leg)

| file:line(s) | function | PRIMARY leg (ROUTE) | STATUS / coord leg (KEEP) | gate-visible? |
|---|---|---|---|---|
| cli/commands/agent/tasks.py:2966 | `status` | `tasks/` glob (~:3008) | `read_events` status.events.jsonl (~:2997) | pinned |
| cli/commands/agent/workflow.py:1275/1387/1582 | `implement` | WP `tasks/` reads | meta identity + dossier + review-cycle feedback (C-008 coord) | pinned |
| cli/commands/agent/workflow.py:2476/2610/2647 | `review` | spec/tasks + baseline-tests | review-cycle sub-artifact (C-008 coord) | pinned |
| cli/commands/validate_encoding.py:80 | `validate_encoding_cmd` | spec.md/data-model.md | analysis-report* | out-of-loop |
| decisions/service.py:144 | `_mission_dir` | meta.json | status.events.jsonl | out-of-loop |

> The two out-of-loop MIXED sites still need a per-leg split, but the split routes to PRIMARY only on
> the PRIMARY leg; they are NOT in-loop, so they are TICKET-AND-PIN-class (ticket, don't fix here).

### TICKET-AND-PIN — out-of-loop PRIMARY-kind reads (pin in `_DIR_READ_KNOWN_RESIDUALS` w/ tracking issue, no silent skip)

| file:line | function | artifact | rationale (out-of-loop surface) |
|---|---|---|---|
| manifest.py:259 / :264 | `get_feature_status` | *.md (primary + worktree) | manifest inspection |
| scripts/tasks/tasks_cli.py:215 / :319 / :624 | `_check_format` / `list_command` / `ensure_directory` | `tasks/` | legacy task CLI script |
| cli/commands/validate_tasks.py:113 | `validate_tasks_cmd` | `tasks/` | validate command |
| acceptance/__init__.py:1225 | `compute_acceptance_matrix` | `tasks/` | accept-gate (acceptance/ fenced separately) |
| cli/commands/_identity_audit.py:55 / :280 | `_scope_to_mission` / `_collect_topology_rows` | meta/topology | identity-audit command |
| cli/commands/charter/_widen.py:52 | `_get_mission_id` | meta.json | charter widen (decision phase) |
| decisions/emit.py:71 ; decisions/service.py:117 | `_mission_dir` / `_resolve_mission_id` | meta.json | decisions service (identity) |
| doctrine_synthesizer/apply.py:152 / :737 | `_feature_dir` / `apply` | meta.json | doctrine synthesizer (identity) |
| verify_enhanced.py:89 / :206 | `run_enhanced_verify` | meta.json | enhanced-verify command (identity) |
| missions/plan/plan_interview.py:56 ; missions/plan/specify_interview.py:56 | `_get_mission_id` | meta.json | spec/plan interview (planning phase) |
| cli/commands/mission_type.py:570 | `delete_cmd` | meta.json + lanes.json | mission teardown |

> Most TICKET rows are `meta.json` **identity probes** (PRIMARY_METADATA). Low-risk because the guarded
> resolvers canonicalize to the primary dir for identity, but a bare `resolver(...)/"meta.json"` against
> a *materialized* coord husk can still miss — so they remain tracked residuals, not silent skips.

### KEEP — correct as-is (representative; ~57 sites total)

- **STATUS reads (coord-correct):** tasks.py:603/1085/1322/2114/2848 (status.events / read_events),
  workflow.py:323 (`_canonical_status_feature_dir`), retrospect.py:110/1016, agent_utils/status.py:120,
  materialize.py:71 (status views), lanes/recovery.py:356/664, doctrine_synthesizer/apply.py:810.
- **Guarded STATUS seam (`resolve_handle_to_read_path`):** acceptance/__init__.py:764,
  orchestrator_api/commands.py:281, decision.py:470 (decisions/index.json), agent/context.py:75,
  agent/mission_feature_resolution.py:194 — the sanctioned IC-01 entry points.
- **C-008 review-cycle matched read/write pair:** review/cycle.py:193 (read pointer) / :272 (write).
- **Identity / existence-check probes (no artifact read):** workflow.py:1015, tasks.py:455/2974,
  status.py:73, decision.py:114, mission_type.py:416, next_cmd.py:360, verify.py:32,
  merge/resolve.py:63/98, merge.py:269, lanes/worktree_allocator.py:360, sync/events.py:120,
  status/aggregate.py:538, coordination/surface_resolver.py:634,
  coordination/status_transition.py:264/281, next_cmd.py:187/253/581/631, mission_type.py:241.
- **Transient / write targets:** dossier/api.py:227/397/435 (`.kittify` snapshots),
  widen/state.py:63 (widen-pending.jsonl), mission_loader/command.py:159 (scaffold write).

---

### Completeness verdict: the spec's named ~6-lane surface is STILL UNDERSIZED

The spec names the `cli/commands/` core (`tasks status`/`list`, `implement`, `review`,
`_find_first_for_review_wp`, `_preview_claimable_wp_for_mission`, `finalize_tasks`), `workspace/context.py`,
and the 7th `merge/done_bookkeeping.py::_mark_wp_merged_done`. The sweep confirms all of those AND
surfaces **a coherent additional in-loop cluster the named set omits**, driven mostly by the
`lanes.json`-is-PRIMARY fact:

- **merge/lanes lane-state cluster (all gate-invisible — outside scan, inline):**
  `merge/forecast.py:153/159`, `merge/executor.py:976`, `lanes/merge.py:68/198`,
  `lanes/recovery.py:611`, `core/worktree_topology.py:138`. These read PRIMARY `lanes.json` off
  coord-aware resolvers — the same defect class as `_mark_wp_merged_done`, on the merge tail of the loop.
- **dependency-graph cluster:** `tasks.py:3415`, `tasks_dependency_graph.py:118`,
  `tasks_parsing_validation.py:935` — PRIMARY `tasks/`/research reads where the join lives inside
  `build_dependency_graph`, so the two-hop scanner is blind even within scan scope.
- **context-resolution cluster:** `context/resolver.py:163`, `task_utils/support.py:309`,
  `tasks.py:247` — PRIMARY WP-task reads on the implement/review execution-context path.
- **MIXED per-leg risk:** the pinned `implement`/`review`/`status` are not single-verdict; they each
  carry a PRIMARY leg that must route AND a STATUS / review-cycle (C-008) leg that must KEEP. Routing
  them wholesale would break the coord-aware review-cycle pair — they require C-001 per-leg surgery.

**Recommendation:** widen the arch-gate scan to all of `src/specify_cli/` AND add an inline-shape arm
(FR-007) before/with routing, or the merge/lanes cluster will land green-but-broken. Treat the ROUTE
table above (≈18 functions, not 6) as the real in-scope set; pin the TICKET table with tracking issues;
split the 3 in-loop MIXED functions per-leg.

---

## FR-008 sweep — fan-out verification + adjudication (4 independent cluster passes)

The solo sweep above was re-verified by 4 parallel profile-loaded agents, one per
module cluster (core / merge+lanes / workspace+ctx / out-of-loop), classifying FRESH.
Result: **corroborated and sharpened**, with one consequential divergence adjudicated
from source.

### Adjudicated divergence — `meta.json` reads off coord-aware resolvers
- alphonso (merge/lanes) classified `meta.json` reads as ROUTE (PRIMARY_METADATA partition).
- debbie/priti classified them KEEP ("identity mirrored on both surfaces").
- paula cited `implement.py:1020` that the coord husk has **no** `meta.json`.
- **Live probe (this mission's coord branch) + authoritative code comment
  `implement.py:1020-1028` settle it:** planning artifacts incl. `meta.json` live
  **ONLY on PRIMARY**; the coord worktree carries STATUS only. So debbie's "mirrored"
  premise is FALSE and alphonso's "coord is a full non-sparse checkout" is FALSE.
- **Adjudication:** `meta.json` identity reads are a **distinct identity-read class**,
  NOT this mission's planning-read scope. Most already use the `implement.py:1018`
  primary-anchor fallback (guarded-degraded); the unguarded best-effort ones
  (`next_cmd.py:187/253/631` silently drop telemetry on coord-topology) → **separate
  identity-read-routing ticket**, not in-scope ROUTE here. This keeps the mission's
  authority = WORK_PACKAGE_TASK + LANE_STATE + WP-frontmatter planning reads.

### Final reconciled in-scope ROUTE set (planning reads on the loop)
- **tasks/ (WORK_PACKAGE_TASK):** `tasks.py:247/249, 2108, 2276(leg), 2966(leg)`;
  `workflow.py:1067, 1932(leg), 2476(leg)` + `tasks_dependency_graph.py:118`;
  `workspace/context.py:666`; `task_utils/support.py:309`;
  `merge/done_bookkeeping.py:237`; `core/worktree_topology.py:141`.
- **lanes.json (LANE_STATE — confirmed PRIMARY, the big new cluster):**
  `workflow.py:1932(leg)`; `merge/forecast.py:153`, `merge/executor.py:997`,
  `lanes/merge.py:68/198`, `lanes/recovery.py:611` + `:356(leg)`,
  `core/worktree_topology.py:140`; `workspace/context.py:752/790/853`.
- **WP-frontmatter / research.md:** `tasks_parsing_validation.py:935`,
  `context/resolver.py:163`, `validate_tasks.py:113(leg)`, `workspace/context.py:470(leg)`.

### MIXED-READ (per-leg split; several need a signature change, not a one-liner)
`tasks.py:2276/2966/2108`, `workflow.py:2476`+`tasks_dependency_graph.py:118`,
`lanes/recovery.py:356`, `merge/executor.py:976`, `core/worktree_topology.py:138`,
`workspace/context.py:470`, `validate_tasks.py:113`, `validate_encoding.py:80`,
`scripts/tasks/tasks_cli.py:319`. Review-cycle sub-artifacts stay coord (C-008).

### TICKET-AND-PIN (out-of-loop PRIMARY reads — pin + tracking issue, no silent skip)
HIGH: `agent_utils/status.py:120` (show_kanban tasks/ read). Others (LOW): `widen/state.py:63`,
`tasks.py:3415` (list-dependents), `scripts/tasks/tasks_cli.py:215`, `manifest.py:259/264`,
`verify_enhanced.py:89/206`, `doctrine_synthesizer/apply.py`, `dossier/api.py`,
`acceptance/__init__.py:1225`, `_identity_audit.py`. Plus the **deliberately-deferred**
`workflow.py:2121/2124` (comment-documented worktree-local anchor) → pin, keep its note.
Separate ticket: the `next_cmd.py` identity-read class.

### Bottom line on sizing
Fan-out confirms the in-scope ROUTE surface is **~20 functions across 4 module clusters
+ gate hardening + out-of-loop triage** — roughly 3× the spec's originally-named 6.
The biggest confirmed addition beyond the post-spec decision is the **merge/+lanes
`lanes.json` cluster** (genuine same-class coord-topology bug on the merge path).

---

## Post-plan brownfield checks (2026-06-26)

### Foldable-issue / tracker hygiene (priti)
- **CLAIM** #2115/#2140/#2183 (all OPEN, correctly claimed). **REFERENCE-only** epics #2160/#2017/#1716/#1878/#2173/#1619 (all OPEN, not claimed — C-006 holds).
- **#2116** (tasks.py coord-skip consolidation) — REFERENCE only; adjacent (touches tasks.py) but a router-contract change → would balloon past C-009. Do not fold.
- **#2167** (retire pre-3.0 scripts/tasks/ legacy reader) — the correct existing ticket to CITE in the `scripts/tasks/tasks_cli.py:215/319/624` pins (FR-008). Do not fold.
- **#2100** (load_meta API consolidation), **#2057** (merge.py decompose), **#2091** (next mid8 git bug), **#2158** (dead-symbol gate parser) — LEAVE (no scope overlap / C-009 forbidden).
- **FR-015 → 2 NEW tickets** (no pre-existing): (a) sibling mission for the merge/+lanes/+core/worktree_topology `lanes.json` cluster; (b) identity-read-routing for the `meta.json` reads off coord.

### Deprecation + split-brain + sizing (randy)
- **No dying shim touched.** The 3.3.0-removed `src/specify_cli/next/` shim is NOT in scope. DoD: IC-02 edits must stay OUT of the `workflow.py:539-617` legacy-fallback block and the `feedback://` deprecation paths (`:1782/1867`).
- **IC-08 dead-symbol removal SAFE** — `FEATURE_CONTEXT_UNRESOLVED_CODE` has zero importers (only its def); the ~15 other hits are the bare string `"FEATURE_CONTEXT_UNRESOLVED"` error code (untouched).
- **Split-brain: STABLE, no new split-brain** — this mission EXTENDS adoption of the canonical seam (already at ~12 sites), introduces no competing resolver. 3 thin `_planning_read_dir` wrappers already exist (mission_feature_resolution:69, orchestrator_api:324, acceptance:787) — reuse, do NOT add a 4th (NFR-004). Routing reads to PRIMARY *converges* (writers already write PRIMARY).
- **Sizing:** IC-01 (gate hardening) and IC-02 (cli/agent reads) are the HEAVIEST (both likely >10 subtasks). Recommend /tasks re-slice: IC-01 → scanner-arm vs floor-recompute; IC-02 → IC-02a tasks.py / IC-02b workflow.py+discovery.py.
- **Behavior-preservation DoDs (WP09-trap class):**
  1. `runtime/next/discovery.py::preview_claimable_wp(feature_dir)` is a single-arg MIXED read (tasks/ PRIMARY + status events COORD from one dir) — **split the signature** into planning_dir + status_dir; RED-first assert tasks-from-PRIMARY AND lanes-from-COORD, selection_reason unchanged on flat.
  2. `build_dependency_graph(feature_dir)` is a shared seam (10 callers, 6 in-loop) — route by passing the planning dir at the IN-LOOP callers; **do NOT change the function signature** (would re-point out-of-loop callers merge/ordering:95, policy/merge_gates:238 — TICKET-class).
  3. MIXED status/implement/review: only PRIMARY legs route; C-008 review-cycle read/write pair STAYS coord (assert post-route).
  4. lanes.json legs (workflow:1932, context.py:752/790/853): confirm `require_lanes_json`/`resolve_lanes_dir` fail-closed semantics + the `:714` not-found path still resolve.

---

## Post-tasks anti-laziness squad (2026-06-26) — convergent findings + remediation

4 profiles (renata/alphonso/pedro/debbie), profile-loaded, read-only. Verdict: structure
strong, but verification obligations under-specified at corner-cutting points + one
structural gap. Remediations applied to the WP prompts:

### HIGH (fixed in WP prompts)
- **C-008 unpinnable residual (debbie root-cause).** `workflow.py::implement`/`::review`
  retain coord-legs for review-cycle sub-artifacts (`tasks/<wp_slug>/…`, C-008). The
  dir-read scanner is function-granular, so those functions stay FLAGGED → their pins
  can't be removed (RED) yet aren't routable. WP06's "zero in-loop residuals" was false.
  **Fix:** WP02 adds a `tasks/<wp_slug>/` sub-path exclusion (so C-008 sub-artifact reads
  don't trip the PRIMARY-kind discriminator) + a "C-008 permanent-coord" pin category;
  WP06's claim reworded to "zero routable in-loop residuals; C-008 sub-artifact reads stay
  coord (permanent)".
- **WP04 discovery.py ripple (pedro).** `preview_claimable_wp` has a 2nd prod caller
  (`runtime/next/runtime_bridge.py:3078`) + 11 calls in `tests/next/test_next_claimable_payload.py`.
  **Fix:** `status_dir: Path | None = None` (default = planning_dir) → backward-compatible,
  ripple vanishes. T019 "remove discovery pins" was vacuous (discovery.py is outside the
  src/specify_cli scan scope) → reworded to "remove workflow pins".
- **WP04/WP03-06 RED-first tautology (renata).** Stashing a new signature reds via
  TypeError, not the divergence. **Fix:** RED must drive the PRE-EXISTING public entry point
  (`_preview_claimable_wp_for_mission`/`review`/`tasks status`) on the COORD fixture, with a
  documented husk-path assertion failure (not import/signature error, not flat-topology).
- **WP08 wrong layer + stale-premise (renata+pedro).** Calling `is_committed` directly pins
  path-handling, not the #2140 caller-resolution vector; the docstring is already correct
  (rewriting to "primary for all topologies" contradicts C-004). **Fix:** drive the caller
  (`setup_plan`/`_planning_read_dir(spec)`) on the coord fixture; keep the path-derived
  docstring framing, update only the caller-level note.

### MEDIUM (fixed)
- WP07 floor: add a tightness bound `live − margin <= floor < live` (margin a named const);
  assert `len(permanent_allowlist) == 3` exactly + the 4 named fold entries removed / 3
  raw-param sanctions kept.
- WP02 self-test: MANDATE capturing the pre-T004 RED output; add a coverage assertion that
  every real inline site in this sweep is flagged before any WP unpins it.
- WP01 asserter: `assert_status_from_coord` must assert resolved-path == coord path (or seed
  a primary-status decoy) so a wrong-leg read fails loudly, not just "status readable".
- FR-009: require an explicit 1:1 pin↔route↔test map; WP06 cross-checks removals vs tests.

### Lane structure (alphonso — non-blocking, noted)
`lanes.json` placed WP03–06 in 4 separate lanes (a/c/d/e/f), not the "one lane" tasks.md
prose claims (the shared mutation is invisible to the allocator — only WP02 declares the
ratchet file). Serial chain → zero concurrency yet cross-lane merge surface on the pin
literal. Accepted as-is (pin-removal blocks are disjoint; #1684 propagation is FIXED) WITH
a mandated pre-merge `spec-kitty merge --dry-run` conflict forecast on the ratchet file
(added to tasks.md close-out). Lane-collapse deferred (would require re-finalize).

### Confirmed sound
Line refs accurate (≤5-line drift); the seam exposes all named kinds; mixed-reads genuine;
no double-assigned sites; FR-014 fixture buildable un-stubbed; WP09 dead-symbol zero importers.

---

CORRECTION (WP06 review): validate_tasks.py:113 is single-leg PRIMARY (frontmatter-vs-subdir), NOT a MIXED read — paula's cluster classification was wrong; no status-events leg exists in scan_all_tasks_for_mismatches.
