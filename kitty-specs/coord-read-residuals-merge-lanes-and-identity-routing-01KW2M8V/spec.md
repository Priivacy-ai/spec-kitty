# Mission Specification: Coord-Read Residuals — Merge/Lanes Planning Reads + Identity-Read Routing

**Mission Branch**: `mission/coord-read-residuals-2185-2186`
**Created**: 2026-06-26
**Status**: Draft (revised after post-spec adversarial squad — facts verified sound; fixture-falsifiability, gate-narrative, and ownership revisions folded in)
**Input**: Issues #2185 + #2186 (children of epic #2160, siblings of #2115). The parallel, out-of-loop half of the coord-authority read-routing cleanup — the surfaces the implement-loop mission (`implement-loop-coord-authority-completion-01KW2E7A`) is boundary-forbidden (C-009) from touching.

## Context & Problem

`#2106` (merged 2026-06-24) made planning artifacts — `meta.json` (PRIMARY_METADATA), `lanes.json` (LANE_STATE), `tasks/` (WORK_PACKAGE_TASK) — live **only on the PRIMARY checkout** for every topology. Under coordination (`coord`) topology the materialized `-coord` worktree is a **status-only husk**: it carries no PRIMARY-partition artifacts.

Multiple read sites still resolve those PRIMARY-kind artifacts through **coord-aware** resolvers (`candidate_feature_dir_for_mission`, `resolve_feature_dir_for_mission`), which land on the husk. On a coord-topology mission those reads silently return empty/stale data, raise resolver errors, or fall back to defaults. This Mission routes the two residual classes the implement-loop Mission is forbidden from touching:

- **Lane A (#2185, #2187)** — the **merge / finalize / recovery / lanes / topology / status-display** path reads of `lanes.json`, `tasks/`, and `meta.json` (incl. the `show_kanban_status` `tasks/` read, #2187).
- **Lane B (#2186)** — **identity / telemetry / lifecycle** reads of `meta.json` in the command layer (the `next_cmd` telemetry-drop class and the post-#2115 fallback-dependent identity probes).

The canonical fix already exists and is in production use (introduced by the #2106 gate-read work): route PRIMARY-partition reads through `resolve_planning_read_dir(repo_root, slug, kind=...)` (which folds the handle and resolves PRIMARY topology-blind via `primary_feature_dir_for_mission`), or anchor directly on `primary_feature_dir_for_mission(repo_root, _canonicalize_primary_read_handle(repo_root, slug))`. STATUS-partition reads **must stay coord-aware**.

> **Research correction (binding for this Mission):** the artifact "kind" labels in the issue tables are partly wrong. The actual partition (verified against `mission_runtime.is_primary_artifact_kind`) is restated per-site in the Surface Inventory below. Several sites the issues label `LANE_STATE` actually read `meta.json` (PRIMARY_METADATA); several "pure" sites are **mixed** PRIMARY+STATUS and require a per-leg split. The Mission routes by the *real* kind, not the issue label.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Merge/finalize/recovery works on a coord-topology mission (Priority: P1)

As an operator merging or recovering a **coord-topology** mission, I want the merge/forecast/finalize/recovery/topology code to read `lanes.json`, `tasks/`, and `meta.json` from the PRIMARY checkout, so that forecasts, lane resolution, WP-path lookup, abort teardown, recovery scans, and worktree-topology materialization see real planning data instead of the empty `-coord` husk.

**Why this priority**: Today these paths silently lose lane/WP/identity data or raise resolver errors on coord topology — the merge/recovery surface is where data loss is most destructive (wrong branch, skipped WPs, failed teardown).

**Independent Test**: Reuse the merged sibling's **already-divergent** real `git worktree` coord fixture (`tests/integration/coord_topology_fixture.py`: STATUS-only husk — no `tasks/`/`lanes.json`/`meta.json`; primary has `lanes.json`+`tasks/`+a decoy events file), extended with the FR-009 sentinel-husk-meta variant. Drive the real `_run_lane_based_merge` / `scan_recovery_state` / `materialize_worktree_topology` paths; assert each reads from `primary_feature_dir` and returns the seeded lanes/WPs on a **returned domain value**, and that reverting any read to the coord-aware resolver makes the test fail (the husk has no such artifact). Unit stubs that hand in a primary dir directly are explicitly disallowed (they mask the routing bug).

**Acceptance Scenarios**:
1. **Given** a coord-topology mission whose `-coord` husk has no `lanes.json`, **When** `merge/forecast.py` builds a forecast, **Then** it reads `lanes.json` (and the review-artifact `tasks/` preflight) off PRIMARY and forecasts the real WP set.
2. **Given** the same mission, **When** `_run_lane_based_merge` (executor) runs, **Then** the `lanes.json` / `meta.json` legs resolve PRIMARY while the `status_feature_dir` STATUS leg stays coord-aware.
3. **Given** a recovery scan (`lanes/recovery.py::scan_recovery_state`), **When** it reads lanes (LANE_STATE) and tasks (WORK_PACKAGE_TASK), **Then** those legs resolve PRIMARY while the `status.events.jsonl` leg stays coord-aware.
4. **Given** `_mark_wp_merged_done` (`merge/done_bookkeeping.py`), **When** it resolves the WP markdown path, **Then** it uses `resolve_planning_read_dir(kind=WORK_PACKAGE_TASK)` and the misleading "do not use the read-path resolver" comment is removed; the status-transactional legs are unchanged.

### User Story 2 — Identity/telemetry survives coord topology (Priority: P1)

As a maintainer relying on lifecycle telemetry and mission-type routing, I want `next_cmd.py` identity reads (and the other unguarded command-layer identity probes) to anchor on PRIMARY, so that lifecycle records are written and `get_or_start_run` routes on the real mission type even under coord topology.

**Why this priority**: `next_cmd.py:619` (was `:631` pre-merge) (`get_mission_type` → `get_or_start_run`) is **routing**, not just telemetry — a husk miss starts the run with the wrong/default mission type (runtime-behavioral, not merely observability). `:187`/`:253` silently drop lifecycle records.

**Independent Test**: On a coord topology whose **husk `meta.json` carries a sentinel identity distinct from PRIMARY** (FR-009 — otherwise a husk-landing read returns the same `mission_id` and the test is non-falsifiable), invoke the `next` lifecycle-record and answer-handling paths; assert the lifecycle record is written with the **PRIMARY** `mission_id` (not the sentinel) and `get_mission_type` returns the PRIMARY type (not the husk/default). Reverting the read to the coord-aware resolver must surface the sentinel/default and fail the test.

**Acceptance Scenarios**:
1. **Given** a coord-topology mission, **When** `_pair_previous_lifecycle_record` / `_write_issuance_lifecycle_record` run, **Then** `resolve_mission_identity` reads `meta.json` off PRIMARY and the `started`/`completed` records are written (not silently swallowed).
2. **Given** the same mission, **When** `_handle_answer` resolves mission type, **Then** `get_mission_type` returns the real type and `get_or_start_run` starts the correct run.
3. **Given** any remaining unguarded command-layer identity probe relying on the `implement.py:1018` primary-anchor fallback, **When** that probe runs, **Then** it carries its own PRIMARY anchor and does not depend on the fallback.

### User Story 3 — Residual classes become observable and regression-proof (Priority: P2)

As a maintainer, I want the architectural read gate to *see* the residual read classes the literal vocabulary is blind to, so that the fixes are regression-proof and a future regression (or the eventual removal of the `implement.py:1018` fallback) cannot silently re-introduce the husk-read bug.

**Why this priority**: The existing dir-read scanner matches only `resolver / "tasks"|"*.md"` path-join *literals* (`_PLANNING_DIR_LITERALS`/`_PLANNING_ARTIFACT_LITERALS`). Its vocabulary is **structurally blind** to two shapes this Mission routes: (i) `lanes.json` (LANE_STATE) reads, and (ii) `meta.json` **function-call** reads (`resolve_mission_identity(dir)`/`get_mission_type(dir)`) — even after the implement-loop Mission widens scan *scope* to whole-`src` (scope ≠ vocabulary). Consequently the merge/lanes/core #2185 cluster has **ZERO pins and none can be added**, and the identity class likewise has no detector. So this Mission builds a **single net-new call-shape arm covering BOTH** the `lanes.json` shape (scope `merge/`+`lanes/`+`core/worktree_topology.py`) and the identity shape (scope `cli/commands/` + `agent_utils/status.py`). This is the automated backstop for the #2115 fallback-removal sequencing risk.

**Independent Test**: For **each** shape: add an unguarded read bound off a coord-aware resolver — `read_lanes_json(coord_dir)`/`require_lanes_json(coord_dir)` in a `merge/`/`lanes/`/`core/` module, and `resolve_mission_identity(coord_dir)`/`get_mission_type(coord_dir)` in `cli/commands/` (or `agent_utils/status.py`); assert the arm flags it; route it; assert green. The arm ships with a committed synthetic-AST non-vacuity self-test for **both** shapes (mirroring the existing gate pattern), so its teeth are an automated regression, not a manual ritual.

**Acceptance Scenarios**:
1. **Given** the FR-007 **lanes.json call-shape arm**, **When** a `merge/`/`lanes/`/`core/` site reads `lanes.json` off a coord-aware resolver without a primary fold, **Then** the arm fails (the literal vocabulary could not see this) — and passes once routed.
2. **Given** the FR-007 **identity call-shape arm**, **When** a `cli/commands/` or `agent_utils/status.py` `resolve_mission_identity`/`get_mission_type` resolves off a coord-aware resolver without a primary fold, **Then** the arm fails; the arm carries a synthetic-AST non-vacuity self-test for both shapes.
3. **Lane A:** the only ratchet-visible pin is **#2187** (`show_kanban_status`, a `tasks/` literal); routing it drains exactly that pin. The merge/lanes/core #2185 sites have **no pins** (vocabulary-blind) — their regression coverage is the FR-007 lanes.json arm + the FR-009 divergent-fixture revert-fails test, **not** a pin drain. **Lane B:** no #2186 pin pre-exists either; the arm (FR-007) and the Lane B routing **co-land in this Mission** (gate-unmask-cannot-self-validate: arm + remediation ship together, validated by a pre-merge full-gate dry run).

### Edge Cases

- **Mixed PRIMARY+STATUS single resolver call** (`merge/executor.py`, `merge/done_bookkeeping.py`, `lanes/recovery.py:356`): a single `feature_dir` feeds both a PRIMARY leg and a STATUS leg. Splitting must route only the PRIMARY leg and leave the STATUS leg coord-aware — never collapse both onto PRIMARY (would break C-001 status semantics).
- **Ambiguous / coord-deleted handle**: routing must preserve the structured hard-fail (`MissionSelectorAmbiguous`, #1848) — no silent fallback (C-002).
- **Flat (non-coord) topology**: PRIMARY routing must be a no-op behavioral change (PRIMARY == primary on flat topology); existing flat-topology tests must stay green.
- **Chicken-and-egg in `worktree_allocator._read_coordination_branch`**: it reads `meta.json` (which lives on PRIMARY) via a coord-aware resolver to *discover* coord — route to `resolve_planning_read_dir(kind=PRIMARY_METADATA)`, which is topology-blind and correct.

## Requirements *(mandatory)*

### Surface Inventory *(authoritative — kinds restated from the real partition)*

**Lane A — #2185 + #2187 (merge/lanes/core/status-display; this Mission owns these files):**

| Site | Real kind(s) | Shape | Route |
|------|--------------|-------|-------|
| `merge/forecast.py:153` (+ uncited `:159` review-artifact preflight) | LANE_STATE (+ WORK_PACKAGE_TASK) | pure PRIMARY | `resolve_planning_read_dir(kind=LANE_STATE / WORK_PACKAGE_TASK)` |
| `merge/executor.py:976,981,997,1003` | PRIMARY_METADATA + LANE_STATE; `run.feature_dir` STATUS leg | **mixed** | **route the `:976` legs DIRECTLY, per-leg** (`:981`/`:1003` `resolve_mission_identity` → META; `:997` `require_lanes_json` → LANE_STATE seam) — these live in `_run_lane_based_merge` (def `:947`), a **different function** from the `:887` PRIMARY anchor in `_run_lane_based_merge_locked` (def `:866`); do NOT thread `:887` through. Keep the `run.feature_dir` STATUS leg coord-aware |
| `merge/resolve.py:98` | PRIMARY_METADATA (issue mislabels LANE_STATE) | pure PRIMARY | `kind=PRIMARY_METADATA` |
| `merge/done_bookkeeping.py:237` | WORK_PACKAGE_TASK (issue says meta.json) | **mixed** | WP-path leg → `kind=WORK_PACKAGE_TASK`; remove misleading comment; status-transactional legs unchanged |
| `cli/commands/merge.py:269` | PRIMARY_METADATA (issue mislabels LANE_STATE) | pure PRIMARY | `kind=PRIMARY_METADATA` |
| `lanes/merge.py:68,198` | LANE_STATE | pure PRIMARY | `kind=LANE_STATE` |
| `lanes/recovery.py:356` | LANE_STATE + WORK_PACKAGE_TASK + STATUS | **mixed** | split: lanes/tasks → resolver; events leg coord-aware |
| `lanes/recovery.py:611` | LANE_STATE (issue mislabels WORK_PACKAGE_TASK) | pure PRIMARY | `kind=LANE_STATE` |
| `lanes/recovery.py:664` (`feature_dir` feeding `emit_status_transition_transactional` @ `:686`) | **STATUS** | **KEEP** | **coord-aware — never route**; it is a STATUS-write leg (the C-001/#2155 analog) and must stay on the worktree-local resolver |
| `lanes/worktree_allocator.py:360` | PRIMARY_METADATA (issue mislabels LANE_STATE) | pure PRIMARY | `kind=PRIMARY_METADATA` |
| `core/worktree_topology.py:138,140,141` | PRIMARY_METADATA + LANE_STATE + WORK_PACKAGE_TASK | pure PRIMARY | single swap of `:138` co-resolves all three |
| `agent_utils/status.py:120,126` (`show_kanban_status`) — **#2187** | WORK_PACKAGE_TASK + STATUS | **mixed** | per-leg split: `tasks/` glob (`:126`) → `resolve_planning_read_dir(kind=WORK_PACKAGE_TASK)`; the `read_events(feature_dir)` STATUS leg (`:151`) stays coord-aware (C-001). The `resolve_mission_identity` leg (`:132`) is the #2186 identity class — **ROUTE / PRIMARY_METADATA** (see the Lane B table row + the FR-007 identity arm), distinct from the #2187 `tasks/` drain |

**Lane B — #2186 (identity/telemetry; this Mission owns the command-layer identity class):**

| Site | Read | Impact | Route |
|------|------|--------|-------|
| `cli/commands/next_cmd.py:187,253` | `resolve_mission_identity` (meta.json) — *exact on merged main* | lifecycle record silently swallowed | primary-anchor the identity read |
| `cli/commands/next_cmd.py:619` *(was `:631` pre-merge)* | `get_mission_type` (meta.json) | **routing**: wrong run type started | `resolve_planning_read_dir`/primary fold |
| `cli/commands/agent/workflow.py:1282,2739` *(was `:1274`/`:2732`)* | `resolve_mission_identity` (inline own resolve) | mission_id empty in review-prompt / preflight | clean standalone primary-anchor |
| `cli/commands/agent/workflow.py:1644` *(was `:1636`)* | `get_mission_type` — **shared-variable mixed** (reuses `feature_dir` that also feeds coord-aware review context) | research-branch type miss | needs its **own** primary-anchored variable — NOT a `feature_dir` re-point |
| `implement.py:1394` *(was `:1389`)* | `resolve_mission_identity` — **shared-variable**, correct only via the `:1018` fallback | identity drop once fallback retired | give it its **own** anchor so it survives fallback removal |
| `agent_utils/status.py:132` (`show_kanban_status`) | `resolve_mission_identity` (meta.json) off a coord-aware `feature_dir` | coord husk is STATUS-only post-#2106 → kanban identity raises/wrongs | **ROUTE / PRIMARY_METADATA** — primary-anchor / `resolve_planning_read_dir(kind=PRIMARY_METADATA)`; the #2186 class, in the same function whose `tasks/` leg #2187 already routes |

> **Lane B citations re-resolved against merged `main`** (architect lens, verified): `next_cmd.py` `resolve_mission_identity` legs `:187`/`:253` are still exact; `get_mission_type` moved `:631`→`:619`. `implement.py` `:1389`→`:1394`. `workflow.py` `:1274`→`:1282`, `:1636`→`:1644`, `:2732`→`:2739`. The Lane B citation re-resolution subtask re-confirms before editing (C-SEQ).

> **Squad-verified ownership (architect lens):** the `workflow.py` identity legs are genuinely the out-of-loop #2186 class — the implement-loop Mission disclaims this class (its C-009/C-008) and its ROUTE/KEEP lines (`:2110/2116/2121/2124`, review-cycle `:2610/2647`, KEEP `:1015`) are **line-disjoint** from these identity legs. So they STAY in this Mission. **But:** they live *inside* functions the implement-loop Mission rewrites, so (1) all Lane B line citations MUST be **re-resolved against post-implement-loop-merge `main`** before editing (C-SEQ); and (2) the **plan must emit a definitive per-site ROUTE / KEEP / owned-by-implement-loop table** covering every Lane B site, cross-checked against the implement-loop Mission's actual ROUTE+KEEP list — no "verify later" deferral, no site left in the gap between the two missions (FR-005).

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Route pure-PRIMARY Lane A sites onto `resolve_planning_read_dir(kind=...)` by real kind | US1 | High | Open |
| FR-002 | Per-leg split mixed Lane A sites (`executor`; `done_bookkeeping`; `recovery:356`): for `executor`, the verified-on-merged-`main` framing is `merge/executor.py:976` (`feature_dir = candidate_…`) in `_run_lane_based_merge` (def `:947`) — route the legs **per-leg, directly**: `:981`/`:1003` (`resolve_mission_identity` → PRIMARY_METADATA) + `:997` (`require_lanes_json` → LANE_STATE), **distinct** from the `:887` PRIMARY anchor in `_run_lane_based_merge_locked` (def `:866`) — do **NOT** thread `:887` through; the STATUS leg `status_feature_dir = run.feature_dir` (`:503`/`:560`) stays coord-aware. PRIMARY legs → resolver, STATUS legs stay coord-aware; keep `done_bookkeeping` status-transactional legs on the **primary** (meta-bearing) dir | US1 | High | Open |
| FR-003 | Remove the self-contradicting "do not use the read-path resolver" comment in `done_bookkeeping.py` and route the WP-path leg | US1 | Medium | Open |
| FR-004 | Primary-anchor the `next_cmd.py` identity/type reads (`:187`, `:253`, `:619` — `:619` was `:631` pre-merge) | US2 | High | Open |
| FR-005 | Emit (at plan) a **complete per-site ROUTE/KEEP/owned-by-implement-loop table** for every Lane B site, cross-checked against the implement-loop ROUTE+KEEP list and re-resolved against post-merge `main`; route the genuinely-owned probes — incl. the **shared-variable mixed** sites (`workflow.py:1644`, `implement.py:1394` — were `:1636`/`:1389`) with their **own** primary anchor (not a `feature_dir` re-point) so they survive fallback removal | US2 | High | Open |
| FR-006 | **Honest scope statement:** the implement-loop Mission's whole-`src` dir-read scan *scope* is real, but the ratchet's **literal vocabulary** (`_PLANNING_DIR_LITERALS`/`_PLANNING_ARTIFACT_LITERALS` — `tasks`/`.md` dir-joins) is structurally blind to `lanes.json` (LANE_STATE) and to `meta.json` function-call reads. So widening *scope* does NOT make the merge/lanes/core #2185 reads detectable by the literal vocabulary — and there is no merge/lanes/core #2185 pin to verify-present. Detection for this Mission's PRIMARY reads comes instead from (1) the FR-007 call-shape arm (static) and (2) the FR-009 divergent-fixture revert-fails test (behavioral). State this plainly; do NOT assert "verified covered" against the literal scanner. **Arm-scope asymmetry (state honestly):** the lanes.json arm covers `merge/`+`lanes/`+`core/worktree_topology.py`; the identity arm covers `cli/commands/`+`agent_utils/status.py`. The merge/lanes/core **identity** reads (`merge/resolve.py:103`, `merge/executor.py:981`/`:1003`, `core/worktree_topology.py:139`) are ROUTED but their regression coverage is the **FR-009 revert-fails fixture (behavioral), NOT the identity arm** — do not claim static-arm protection for them | US3 | Medium | Open |
| FR-007 | Build a **call-shape scan arm** that flags PRIMARY reads the literal vocabulary cannot see, covering **both** shapes: (a) **identity** — `resolve_mission_identity(dir)`/`get_mission_type(dir)` (scope `cli/commands/` **+ `agent_utils/status.py`**, so the `show_kanban_status` `:132` identity read is statically gated, not orphaned); and (b) **lanes.json** — `read_lanes_json(dir)`/`require_lanes_json(dir)` (LANE_STATE; scope `merge/`+`lanes/`+`core/worktree_topology.py`, since those modules hold the reads) — whose `dir` is bound off a coord-aware resolver (`resolve_feature_dir_for_mission`/`candidate_feature_dir_for_mission`/`resolve_feature_dir_for_slug`) without a primary fold. Ship a **mandatory synthetic-AST non-vacuity self-test for BOTH shapes** (pre-fix snippet flagged; routed snippet not). Arm + remediation **co-land** (gate-unmask-cannot-self-validate). Identity scope bounded to `cli/commands/` + `agent_utils/status.py`; lanes.json scope bounded to the three module families above — so the arm does not red-CI on out-of-scope strangers (`sync/`, `acceptance/`, `policy/`, `orchestrator_api/` — follow-on). **Arm-scope asymmetry (see FR-006): the merge/lanes/core IDENTITY reads are covered behaviorally by the FR-009 revert-fails fixture, NOT by this identity arm** (which does not scan `merge/`/`lanes/`/`core/`) | US3 | High | Open |
| FR-008 | **Lane A drain reality:** the ONLY ratchet-visible Lane A drain is **#2187** (`agent_utils/status.py::show_kanban_status` — the #2187 `tasks/` drain subtask) — a genuine `tasks/`-literal pin. The merge/lanes/core #2185 sites have **ZERO pins** under the current vocabulary and none can be added; their regression coverage is (1) the **new FR-007 lanes.json call-shape arm** and (2) the **FR-009 divergent-fixture revert-fails test** — NOT a pin drain. Arm + Lane A/Lane B remediation co-land, validated by a pre-merge full-gate dry run | US3 | High | Open |
| FR-009 | Add a coord-topology **merge/recovery/topology + identity integration test** that **reuses the merged sibling's already-divergent fixture** (`tests/integration/coord_topology_fixture.py`: STATUS-only husk — no `tasks/`/`lanes.json`/`meta.json`; primary has `lanes.json`+`tasks/`+a decoy events file, and a resolved primary `mission_id` of **`01KW2E7AFC0000000000000001`** — the reused implement-loop sibling fixture's primary, **NOT** this Mission's `01KW2M8V…`). **ADD a sentinel-husk-meta variant** — a **distinct fixture/parametrization that *writes* a husk `meta.json`**, explicitly **OVERRIDING the base `coord_topology_fixture.py` invariant `assert not (coord_mission_dir / "meta.json").exists()`**: the husk `meta.json` is **present-but-wrong** — it carries `mission_id = 6KERGF2ZNFBPR91YEZMARG99KS` (a 26-char sentinel ULID) ≠ the fixture's actual resolved PRIMARY id, with `lanes.json`+`tasks/` PRIMARY-only — so the identity proof is a **silent-wrong-value** (matching the spec'd bug), not a missing-file. Do NOT retrofit `write_side/topology_fixtures.py::build_coord` (its husk mirrors primary — non-divergent — with ~26 consumers). Divergence is a **HARD test precondition (the triad)**: `assert not (coord_husk / "lanes.json").exists()`, `assert not (coord_husk / "tasks").exists()`, and `assert husk meta mission_id == 6KERGF2ZNFBPR91YEZMARG99KS` **and `!= ctx.mission_id`** (bind to the fixture's actual resolved primary id, not a hard-coded `01KW2M8V…` literal) **before** any routed-path drive. Reverting a routed read to coord-aware FAILS the test **on a returned DOMAIN VALUE** (forecast WP set / materialized worktrees for Lane A; resolved mission type / lifecycle `mission_id` for Lane B) — the fixture's `assert_reads_primary` / `assert_both_legs` (path-equality) are **NOT** acceptable as the terminal (real `git worktree`, no stubs) | US1, US2 | High | Open |
| FR-010 | Record a **before/after canonicalizer census** and the **explicit list of newly-added DIRECT `primary_feature_dir_for_mission(_canonicalize_primary_read_handle(...))` call sites**; set `ROUTED_CANONICALIZER_FLOOR` = after-census − MARGIN. **Honesty clause:** if the routed sites call the `resolve_planning_read_dir` seam (not the primitive directly), the census does NOT move — in that case STATE PLAINLY the floor did not move and adds no new protection; do NOT re-pin the same integer and claim it as a gain | US3 | Medium | Open |
| FR-011 | **Pre-flight (narrowed):** assert the single **#2187** pin (`agent_utils/status.py::show_kanban_status`) is present in `_DIR_READ_KNOWN_RESIDUALS` on the rebased base before draining it (the #2187 drain subtask). The **absence of merge/lanes/core #2185 pins is the EXPECTED permanent state** (vocabulary is structurally blind to `lanes.json`/`meta.json` reads) — it is NEVER a STOP and must not be mis-read as a landing-timing failure. The preflight verifies: sibling routing landed (C-SEQ) + Lane B citations re-resolved + the #2187 pin present | US3 | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No STATUS-read regression | Every STATUS-partition read (`status.events.jsonl`, status surface) remains coord-aware; zero STATUS legs re-routed to PRIMARY (asserted by tests) | Reliability | High | Open |
| NFR-002 | No silent fallback | Ambiguous/coord-deleted handles keep the structured hard-fail (`MissionSelectorAmbiguous`, #1848); no new best-effort swallow | Reliability | High | Open |
| NFR-003 | Flat-topology behavioral parity | On non-coord topology the change is a no-op; existing flat-topology merge/lanes/next tests stay green | Compatibility | High | Open |
| NFR-004 | Integration over stubs | The #2185 acceptance test drives real code against a real `git worktree` coord fixture; unit stubs handing in a primary dir directly are not accepted as proof | Test Integrity | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | STATUS stays coord-aware | STATUS-partition reads must remain on the coord-aware resolver; only PRIMARY-partition legs route | Technical | High | Open |
| C-002 | Resolver consumed, not re-authored | This Mission only *consumes* `resolve_planning_read_dir` / `primary_feature_dir_for_mission` / `_canonicalize_primary_read_handle`; it must not edit resolver internals (mirror implement-loop C-003/C-007) | Technical | High | Open |
| C-003 | Strategy consistency | Identity routing must match the implement-loop Mission's chosen seam model (handle-blind primitive + caller-side canonicalization; no silent fallback) | Technical | High | Open |
| C-009-mirror | Surface exclusivity | This Mission owns ONLY `merge/`, `lanes/`, `core/worktree_topology` (#2185) + the `meta.json` identity-read class incl. `next_cmd.py` (#2186). It must NOT touch the implement-loop ROUTE surface (`tasks.py`, `workflow.py` route legs, `tasks_dependency_graph.py`, `workspace/context.py`, etc.) — the inverse of the implement-loop C-009 | Technical | High | Open |
| C-EXCL-2167 | Legacy reader untouched | The repo-root `scripts/tasks/` pre-3.0 legacy reader is **#2167** — pin-and-cite only; never route or delete | Technical | High | Open |
| C-EXCL-FALLBACK | Do not remove the fallback | This Mission adds guards so the `implement.py:1018` primary-anchor fallback *can* be retired later; it does NOT remove the fallback (separate follow-on) | Technical | High | Open |
| C-SEQ | Landing sequence | Land after the implement-loop Mission's routing + whole-`src` scanner *scope* widening; branch from / rebase onto post-implement-loop-merge main, then re-resolve all Lane B line citations. **No #2185 pin hand-off exists** (the ratchet vocabulary is blind to `lanes.json`/`meta.json` reads, so the merge/lanes/core cluster has zero pins); the only ratchet-visible drain is the **#2187** `tasks/` pin (FR-011 narrowed preflight). Lane B builds its own call-shape arm and routes in-mission. Spec/plan proceed in parallel now; landing serializes after implement-loop | Process | High | Open |

### Key Entities

- **`resolve_planning_read_dir(repo_root, slug, *, kind)`** — kind-aware seam (`missions/_read_path_resolver.py`); PRIMARY kinds fold the handle + resolve topology-blind, STATUS kinds stay coord-aware.
- **`primary_feature_dir_for_mission` + `_canonicalize_primary_read_handle`** — handle-blind PRIMARY primitive + caller-side canonicalizer pairing.
- **`MissionArtifactKind`** — partition authority (`is_primary_artifact_kind`): PRIMARY = PRIMARY_METADATA/LANE_STATE/WORK_PACKAGE_TASK; STATUS = STATUS_STATE/ACCEPTANCE_MATRIX/ISSUE_MATRIX.
- **`_DIR_READ_KNOWN_RESIDUALS` + dir-read scanner** (`tests/architectural/test_gate_read_literal_ban.py`) — the ratchet, vocabulary = `tasks`/`.md` dir-join *literals* only. Structurally blind to `lanes.json` (LANE_STATE) and to `meta.json` function-call reads. The **net-new call-shape arm** (FR-007) adds both the `lanes.json` shape (merge/lanes/core) and the identity shape (cli/commands/); the only literal pin in scope is **#2187** (`show_kanban_status`, drained by the #2187 drain subtask) — the merge/lanes/core #2185 cluster has no pins to drain.
- **Divergent coord fixture** (`tests/integration/coord_topology_fixture.py`) — the merged sibling's already-divergent real `git worktree` topology (STATUS-only husk), reused here + extended with the FR-009 sentinel-husk-meta variant. **Not** `write_side/topology_fixtures.py::build_coord` (non-divergent husk, ~26 consumers — do not retrofit).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** (the #2185 backstop): On the divergent fixture (`tests/integration/coord_topology_fixture.py`: PRIMARY-only `lanes.json`/`tasks/`, husk lacks them; sentinel husk meta ≠ PRIMARY), the merge/recovery/topology integration test is green and **fails** when any routed merge/lanes/core site is reverted to the coord-aware resolver — and the failure is on a **returned DOMAIN VALUE** (the forecast WP set / the materialized worktrees — Lane A outputs; mission type / lifecycle `mission_id` belong to SC-002), **not** a resolved-path equality and **not** the fixture's `assert_reads_primary`/`assert_both_legs` path-equality helpers. This behavioral revert-fails proof — not the pin ratchet — is the #2185 regression backstop.
- **SC-002**: On a coord topology whose husk `meta.json` carries a sentinel identity ≠ PRIMARY, lifecycle records are written with the **PRIMARY** `mission_id` and `get_mission_type` returns the PRIMARY type (Lane B) — reverting to coord-aware surfaces the sentinel/default and fails the test **on the returned domain value (resolved mission type / lifecycle `mission_id`), not the `assert_reads_primary`/`assert_both_legs` path-equality helpers**. Zero silent telemetry/routing drops.
- **SC-003**: 100% of the Surface Inventory sites are routed by their *real* kind; every STATUS leg stays coord-aware (NFR-001) — no over-routing.
- **SC-004** (three real teeth — #2185 closure lives in SC-001): (1) the FR-007 **call-shape arm self-test** flags an injected unguarded probe for **both** shapes — identity (`resolve_mission_identity`/`get_mission_type`) AND `lanes.json` (`read_lanes_json`/`require_lanes_json`) bound off a coord-aware resolver — and passes once routed; (2) the **#2187** `_DIR_READ_KNOWN_RESIDUALS` pin shrinks by **exactly one** (the #2187 drain subtask) — the only ratchet-visible Lane A drain; (3) **FR-010 floor honesty** — the canonicalizer floor is recomputed from the recorded before/after census, and if seam-routing did not move the census this is stated plainly (no re-pinned-integer "gain").
- **SC-005**: `ruff` + `mypy` clean on all touched surfaces; full `tests/architectural/` green (incl. no new un-pinned identity-arm strangers — identity arm scoped to `cli/commands/` + `agent_utils/status.py`); flat-topology parity preserved (NFR-003).

## Traceability

- **Epic (parent, reference-only — never claim/close):** #2160
- **Originating issue:** #2115 (claimed by the implement-loop Mission; closes when it lands)
- **This Mission addresses:** **#2185** (Lane A) + **#2186** (Lane B) + **#2187** (Lane A — `show_kanban_status` `tasks/` residual, same class as #2185)
- **Sibling in-loop Mission (boundary partner):** `implement-loop-coord-authority-completion-01KW2E7A` — C-009 forbids it from these surfaces; this Mission is its inverse
- **Cause:** #2106 (merged) — kind-aware write-surface placement
- **Explicitly excluded:** #2167 (repo-root `scripts/tasks/` legacy reader — pin-and-cite only); removal of the `implement.py:1018` fallback (separate follow-on)
- **Sequencing:** lands after the implement-loop Mission (whole-`src` scanner *scope* widening + re-resolved Lane B citations; **no #2185 pin hand-off** — the cluster is vocabulary-invisible)
