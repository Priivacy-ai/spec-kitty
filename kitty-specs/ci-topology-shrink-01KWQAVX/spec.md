# Mission Specification: CI Topology Shrink & Guard Un-Blinding

**Mission**: `ci-topology-shrink-01KWQAVX` (mission_id `01KWQAVXZGH1G36HB9QKWMYXGD`)
**Created**: 2026-07-04
**Status**: Draft (post-spec squad revision 1)
**Input**: User description: "spec a remediation mission for Slice C — CI-topology shrink (#2378 shard-side + #1933 group-side, sequenced as siblings). it is hurting us, hard."
**Closes**: #2378 (shard-side split) · #1933 (group-side shrink) · #2383 (arch un-blind, P1) — all under epic #1931.
**Out of scope**: #2283 factors (b)/(c) · #2077 CT7 · #2071 audit · the marker→job model itself (#2034/#2368 substrate — consumed, not rebuilt).

## Context & Problem (why "hurting us, hard")

`.github/workflows/ci-quality.yml` routes CI via three coupled authorities (dorny filter block, the `core_misc` catch-all group, and the FR-010 fail-closed `unmatched→run_all` alarm), all modeled by `tests/architectural/_gate_coverage.py` and pinned by the 8 invariants the #2368 CI suite-map mission bound. Live ground truth (pre-spec 3-lens squad + post-spec 3-lens squad, 2026-07-04):

- **Wallclock:** `fast-tests-core-misc` is a single **unsharded 16.9-min** job; `integration-tests-core-misc` (holding the `architectural`/`adversarial` shard, ~12.2 min) declares `needs: [changes, fast-tests-core-misc]` — so the arch shard is **serialized after** the fast job → a **~29-min critical path = ~85% of the 34-min pipeline, 33% of all CI compute**.
- **Mode A — ~37 UNMAPPED src dirs (68.5k LOC):** `auth`, `migration`, `tracker`, `dossier`, `retrospective`, `compat`, `orchestrator_api`, `bulk_edit`, `tasks`, `doctor`, etc. are in **no** named filter group → every touch trips `unmatched→run_all` (the *entire* pipeline reruns).
- **Mode B — 13 MAPPED-but-ARCH-BLIND dirs (120k LOC, incl. `cli` 58k, `sync` 17.7k, `upgrade` 15.9k, `merge` 6.3k):** `tests/architectural` + `tests/adversarial` run **only** via the `{core_misc, execution_context, acceptance}` groups, so an isolated change to `cli/`, `sync/`, `merge/`, `upgrade/` merges green with the dead-module / stale-symbol / terminology / status-boundary gates **never firing**. This is the root cause of the orphan-coverage bugs whack-a-moled all session (#2370 `m_3_2_4`, acceptance/state, #2379 migration).
- **Failure isolation is near-zero**; the suite is 0-orphan **today only because** the whole-tree catch-all sweeps mask everything.

**Load-bearing design fact (all 3 post-spec lenses):** un-blinding (pillar 2) and the wallclock cut (pillar 3) collide on **the arch pole** — un-blinding runs the 12.2-min arch/adversarial suite on 100% of PRs, and its `needs: fast-tests-core-misc` serialization means sharding only the fast job cannot reach the wallclock ceiling. Both are solved by the **same** move: de-serialize + shard/bound the arch suite (FR-013), realized as an **always-on arch job that adds no filter group** (so it cannot perturb the parsed-relation invariants).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Focused CI for a single-area change (Priority: P1)

A spec-kitty developer changes one source area (e.g. `src/specify_cli/auth/**`) and CI runs **only** that area's focused shard(s) plus the always-on gates — instead of re-running the entire pipeline because the dir was unmapped and tripped the fail-closed catch-all.

**Why this priority**: The acute everyday pain (Mode A) and the foundational half — the named groups it delivers are the substrate the split (US3) and un-blind (US2) build on.

**Independent Test**: For each dir in the **construction-derived worklist** (FR-001), a path-filter fixture test asserts a PR touching only that dir routes to its named group + focused shard and does **not** set `unmatched=true`/`run_all`.

**Acceptance Scenarios**:

1. **Given** `auth/**` is in a named filter group wired to a focused shard, **When** a PR touches only `src/specify_cli/auth/**`, **Then** the `changes` job routes to that group, only the auth shard(s) + always-on gates run, and `run_all` is **not** triggered.
2. **Given** a worklist dir with tests split across two roots (e.g. `migration` → `tests/migration` + `tests/specify_cli/migration`), **When** its shard/composite is carved, **Then** both roots are consolidated into one home and the `@slow` perf test remains excluded (runs only in `slow-tests`), with no same-tier double-run (FR-012, NFR-003).
3. **Given** a src path still unmapped (a future dir), **When** it is touched, **Then** the fail-closed catch-all still forces coverage (fail-safe preserved, FR-009).

---

### User Story 2 - Architectural guards never silently skip (Priority: P1)

A change confined to a previously arch-blind package (`cli/`, `sync/`, `upgrade/`, `merge/`, …) can **no longer** merge green with the architectural + adversarial suite skipped. The dead-module, stale-symbol, terminology, and status-boundary gates run on **every** source change.

**Why this priority**: The correctness root cause of the session's recurring orphan-coverage bugs (Mode B, 120k LOC blind) — the single highest-correctness-leverage change. A wallclock win that still lets real defects merge silently would be a hollow victory.

**Independent Test**: A differential-matrix architectural test asserts arch/adversarial selection over **100%** of `src/specify_cli/*` dirs (0 blind). For each formerly-blind dir, a fixture asserts a touch selects the arch+adversarial suite.

**Acceptance Scenarios**:

1. **Given** `cli/**` was arch-blind, **When** a PR touches only `src/specify_cli/cli/**`, **Then** the arch+adversarial suite is selected and the dead-module / stale-symbol / terminology / status-boundary gates execute.
2. **Given** a PR introducing a new dead module or a legacy-terminology regression in a formerly-blind dir, **When** CI runs, **Then** the relevant architectural gate fails the PR (not silently skipped).

---

### User Story 3 - Core-misc is no longer the pipeline long pole (Priority: P2)

The 16.9-min unsharded `fast-tests-core-misc` monolith is subdivided into a matrix of focused shards **and** the serialized 12.2-min arch pole is de-coupled/sharded, so the core-misc critical path is no longer the pipeline's long pole and a red result names the specific slice that broke.

**Why this priority**: The wallclock + failure-isolation win. P2 because it rides on the named-group substrate from US1 and the arch-pole treatment shared with US2.

**Independent Test**: (a) a **structural** invariant asserts no single shard collects the full catch-all universe (parsed shard-command set); (b) an **acceptance observation** at plan/verify time measures the core-misc critical-path lane against a committed baseline (NFR-001). Assert a deliberately-failed shard names its slice.

**Acceptance Scenarios**:

1. **Given** the fast job is matrix-sharded and the arch suite is de-serialized (FR-013), **When** `run_all` executes, **Then** the core-misc critical-path lane is ≤ the numeric ceiling (NFR-001) and no single shard collects the whole catch-all universe.
2. **Given** a test fails in one carved slice, **When** CI reports, **Then** the failing job names that slice (not an opaque grab-bag).

---

### Edge Cases

- **Windows split-brain**: a carved test file also in `ci-windows.yml`'s static `windows_critical` list (`:24-42`) — update that list in the same commit or FR-003c reds. (This is the **only** real second-layer surface — see FR-008.)
- **Real-port / daemon serial**: `tests/sync/test_orphan_sweep.py` binds ports 9400-9449 and runs `-n0` serially — any slice containing daemon/real-port tests must preserve the serial pass (FR-011, NFR pins it).
- **`dossier` latent gap**: `tests/dossier` is `core_misc`-globbed but in no integration matrix shard — carving it *fixes* a real hole.
- **Nested test roots**: `tests/specify_cli/<D>` slices (`orchestrator_api`, `bulk_edit`) need the integration matrix `ignore_args` updated by hand (not covered by FR-012's whole-tree check).
- **`src/runtime`**: already grouped (`next` group; `integration-tests-next` ~13.5m) — WP01's routing table must confirm mapped/excluded, not re-promote.
- **`doctrine` ambiguity**: `src/doctrine/*` (templates, already grouped) vs `src/specify_cli/doctrine` (unmapped code dir); a `fast-tests-doctrine` job already exists — WP01 routing table disambiguates so a "promote doctrine" step doesn't collide.
- **Dir with no test cone**: mapped to a group but no tests — must not orphan or produce a vacuous shard.
- **Job-count explosion**: promoting ~15 dirs to dedicated jobs balloons `quality-gate.needs` — composite groups cap it (FR-010, measurable ceiling).
- **Coverage drop**: a new `fast-tests-<D>` forgotten from a coverage-consumer's `needs` silently drops its coverage XML — closed by construction (C-005).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Promote every dir in the **construction-derived worklist** to a named src-backed filter group (**dedicated OR composite per FR-010**) so none falls to `unmatched→run_all`. The worklist is a committed, test-consumed census artifact (see NFR-006), NOT a hand list. | US1 | High | Open |
| FR-002 | Register each new group across ALL bound-model surfaces atomically (the 5-edit pattern): dorny filter glob, `changes.outputs` row, `unmatched` enumeration loop, ≥1 test-job `if:`, and the `JOB_GROUPS` heredoc table — no surface hand-added beside the model. | US1 | High | Open |
| FR-003 | Subdivide `fast-tests-core-misc` into a matrix of focused shards (mirroring `integration-tests-core-misc`); each shard owns coherent, non-overlapping test roots. | US3 | High | Open |
| FR-004 | Update the `fast-tests-core-misc` `--ignore` mirror list in lockstep with every shard carve (FR-012 invariant), and the integration-matrix `ignore_args` for nested `tests/specify_cli/<D>` slices. | US3 | High | Open |
| FR-005 | Make `tests/architectural` + `tests/adversarial` run on 100% of src changes (un-blind the 13 Mode-B dirs). **Preferred mechanism (Option A):** an always-on arch job that adds **no filter group** (enters only `quality-gate.needs` + coverage-consumer `needs`), leaving `src_backed_groups`/`compute_unmatched` untouched. | US2 | High | Open |
| FR-006 | Each new shard emits its own coverage XML under a **glob-consumed naming convention** (`coverage-<D>.xml` matched by the aggregator's wildcard download) so emit ⇒ consume by construction. | US3 | Medium | Open |
| FR-007 | Register every new test job in ALL consuming needs-lists: `quality-gate`, `sonarcloud`, `diff-coverage`, `mutation-testing` (and `slow-tests` only for jobs it actually depends on — it lists fast jobs only). | US3 | High | Open |
| FR-008 | Propagate new/relocated **windows-marked test files** to `ci-windows.yml`'s static `windows_critical` list (`:24-42`) — the sole real second-layer surface. (`quality_gate_decision.py` holds no job→group data; `drift-detector.yml`/`release.yml` carry no shard/ignore names — do NOT edit them.) | US1 | High | Open |
| FR-009 | Preserve fail-safe selection: carve-outs only NARROW; an unmapped or newly-added src path still triggers coverage; nightly `run_all` still over-covers (no new blind spot); `ci:full`/`ready-for-ci`/`workflow_dispatch` escape hatches remain intact. | US1 | High | Open |
| FR-010 | Use composite groups (e.g. `agent_surface` = orchestrator_api+tracker+dossier; `lifecycle` = migration+doctor+bulk_edit) to cap job-count under the measurable ceiling in NFR-005. | US1 | Medium | Open |
| FR-011 | Preserve real-port serial `-n0` passes, `--dist loadfile` (never bare `load`), and per-worker HOME isolation on every new shard. | US3 | High | Open |
| FR-012 | The `migration` home (dedicated shard or composite) consolidates `tests/migration` + `tests/specify_cli/migration` and preserves the `and not slow` exclusion (the `@slow` perf test runs only in `slow-tests`) — phrased shard-agnostically. | US1 | High | Open |
| FR-013 | **De-serialize + bound the arch pole.** The arch/adversarial suite must run **in parallel** with the fast lane (drop the `integration-tests-core-misc needs: fast-tests-core-misc` serialization for the arch shard) and be sharded/bounded so its tail lands ≤ the NFR-001 ceiling on every PR — the same object as FR-005's always-on un-blind. | US2, US3 | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Core-misc critical path (absolute) | Record the ~29-min baseline (16.9m fast + 12.2m arch, serialized) in a **committed timings artifact** at plan time; the post-mission core-misc critical-path lane must be **≤ 55% of that baseline AND ≤ the next-longest independent lane**. This is a plan/verify **acceptance observation**, not a standing unit gate. | Performance | High | Open |
| NFR-002 | Architectural coverage completeness | Architectural + adversarial guards execute on **100%** of `src/specify_cli/*` dirs (13 blind → **0**), asserted by a **new** differential-matrix relation in the bound model (`filter_groups + job_gating_groups + gates` → arch-selected per dir) — scope the `_gate_coverage` extension explicitly. | Correctness | High | Open |
| NFR-003 | Same-tier selection uniqueness | No test is selected by **>1 fast shard**, nor by **>1 integration shard** — a mechanized invariant distinct from the existing *report-only* cross-tier duplicate warning. Total `run_all` selected-test count unchanged; `_gate_coverage` orphan count stays **0** (baseline 28,573). | Reliability | High | Open |
| NFR-004 | Feedback isolation | A single-area PR runs only its focused shard(s) + always-on gates (incl. the bounded arch job) and no full-matrix run; a failing shard names its slice. | Usability | Medium | Open |
| NFR-005 | Job-count ceiling | Post-mission `len(quality-gate.needs)` ≤ a pinned ceiling (set at plan time from the composite design), asserted by a test — composites must keep the graph under it. | Maintainability | Medium | Open |
| NFR-006 | Worklist is construction-derived | The FR-001 worklist is computed, not hand-picked: a committed census (e.g. every `src/specify_cli/*` dir with ≥ N LOC lacking a named group) that the SC-001 test iterates — so the metric measures coverage, not the implementer's constant. | Correctness | High | Open |
| NFR-007 | Invariant integrity | All 8 #2368 WP04 architectural invariants remain green through every WP; the new invariants (NFR-002/003/005, C-005) are additive to the bound model. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Consume, don't rebuild the substrate | Do not rebuild the marker→job model or the fail-closed catch-all (#2034/#2368) — extend the bound `_gate_coverage` model additively. | Technical | High | Open |
| C-002 | No split-brain derived surfaces | Every derived surface (catch-all OR-list, JOB_GROUPS heredoc, ci-windows static list) is asserted-against-parsed-source or the build rejects (Decision 8). | Technical | High | Open |
| C-003 | Shared-hot-file merge strategy | `ci-quality.yml` is edited by a **single owning WP** (workflow edits are NOT split per-slice), because per-slice WPs editing one file cannot be owned-file-disjoint and a `lanes` allocator rejects that. WPs partition by FILE (workflow / bound-model / tests / ci-windows), not by slice. If per-slice workflow edits become necessary, **flatten to `single_branch`** with linearized shared-surface edits (docs-consolidation pattern). Topology is a plan-time decision. | Technical | High | Open |
| C-004 | Scope fence | Keep #2283 factors (b)/(c), #2077 CT7, #2071 audit, new markers, gate rewrites, and WIP-title semantics OUT of scope. | Business | High | Open |
| C-005 | Coverage-consumer integrity by construction | New invariant: **coverage-emitting jobs ⊆ `sonarcloud.needs`** and **critical-path emitters ⊆ `diff-coverage.needs`** (and `mutation-testing.needs` where it consumes them). Do NOT intersect `slow-tests.needs` — it lists only fast jobs and would red on arrival. | Technical | High | Open |
| C-006 | Nightly-move deferred | #1933's literal nightly-scheduled-full-suite is OUT (shrink interpretation only); offer a thin nightly-schedule option in-mission ONLY if the committed plan-time timings show the post-shrink PR critical path still > ~15 min. Closeout must state the shrink satisfies #1933's *intent* (fast, targeted PR CI) with escape hatches + nightly `run_all` over-cover intact. | Technical | Medium | Open |

### Key Entities

- **Worklist census artifact**: a committed, test-consumed enumeration of the src dirs the mission must map (construction-derived, NFR-006) — the authority SC-001 iterates.
- **Filter group** (dorny): named path→group mapping; src-backed groups join the `unmatched` enumeration.
- **Shard job** (`fast-tests-<D>` / matrix entry / the always-on arch job): a CI job running a coherent slice under a fixed marker expression; emits `coverage-<D>.xml`.
- **Bound model** (`_gate_coverage.py` + `_gate_coverage_baseline.json`): the parsed authority; the 8 existing + new invariants live here.
- **Needs-list**: a job's `needs:` set; coverage integrity (C-005) binds the coverage-consumer subset by construction.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: **0** dirs in the construction-derived worklist (NFR-006) fall to `unmatched→run_all` — a mechanized test iterates the committed census and asserts each maps to a named group AND a focused shard (not `run_all`).
- **SC-002**: Architectural + adversarial guards run on **100%** of `src/specify_cli/*` dirs (13 blind → 0), proven by the differential-matrix relation (NFR-002) that fails if any dir is arch-blind.
- **SC-003**: No single shard collects the full catch-all universe (structural invariant over the parsed shard-command set) AND the core-misc critical-path lane meets NFR-001's absolute ceiling (acceptance observation vs committed baseline).
- **SC-004**: `_gate_coverage` orphan count remains **0**, total `run_all` selected-test count is unchanged, and the same-tier uniqueness invariant (NFR-003) is green — no drop, no double-run.
- **SC-005**: All 8 #2368 WP04 invariants remain green AND the new coverage-consumer invariant (C-005), the job-count ceiling (NFR-005), and the serial-port preservation invariant (FR-011) are green.
- **SC-006**: For each carve-out dir, a path-filter fixture demonstrates a single-area PR triggers only its focused shard(s) + always-on gates (incl. the bounded arch job) — not a full-matrix run.
