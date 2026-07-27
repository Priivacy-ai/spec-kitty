# Work Packages: CI Topology Shrink & Guard Un-Blinding (ci-topology-shrink-01KWQAVX)

**Inputs**: [spec.md](./spec.md) (authority — FR-001..013, NFR-001..007, C-001..006, SC-001..006) + [plan.md](./plan.md) (IC-01..06, honest WP-shape) + [research.md](./research.md) (census RULE, live worklist, 29.4-min baselines) + [data-model.md](./data-model.md) (bound-model relations).

**Topology**: near-linear DAG forced by **C-003** — `ci-quality.yml` is a shared hot file editable by exactly ONE owning WP, so WPs partition **by FILE**, never by slice. Two single-owner spines: `tests/architectural/_gate_coverage.py` (WP01 extends, READ-ONLY after) and `.github/workflows/ci-quality.yml` (WP03 sole owner). Red-first invariants (WP02) land BEFORE the surgery (WP03) and define green against the fixed workflow. Second-layer (WP04) and verification (WP05) fan out after the surgery; closeout (WP06) joins them.

**Verification doctrine (non-fakeable DoD)**: every DoD anchor is a **green test or a parsed-invariant assertion**, not prose. Every new invariant is authored FAILING against today's topology first (WP02 red evidence), then satisfied by WP03. All census numbers and timings are re-derived live at implement (NFR-006/NFR-001). The 8 #2368 WP04 invariants stay green through every WP (NFR-007); the new relations (NFR-002/003/005, C-005) are additive to the bound model (C-001).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Construction-derived census artifact (`tests/architectural/ci_topology_census.json`) + freshness-guard | WP01 | — |
| T002 | Additive `_gate_coverage.py` parse extensions (differential-matrix + same-tier + arch-job relations) | WP01 | — |
| T003 | WP01 gates (existing consumers green untouched; live self-check counts recorded) | WP01 | — |
| T004 | RED: `test_ci_topology_worklist.py` (SC-001) + `test_arch_unblind_matrix.py` (NFR-002) | WP02 | [P] |
| T005 | RED: `test_same_tier_uniqueness.py` (NFR-003) + `test_coverage_consumer_needs.py` (C-005) | WP02 | [P] |
| T006 | RED: `test_serial_port_preservation.py` (FR-011) + `test_job_count_ceiling.py` (NFR-005) | WP02 | [P] |
| T016 | RED: `test_arch_pole_deserialized.py` (FR-013 — arch `needs` drops the fast-lane job) | WP02 | [P] |
| T017 | RED: `test_shard_universe_bounded.py` (SC-003a — no single shard collects the full universe) | WP02 | [P] |
| T007 | Composite filter groups + `changes.outputs` rows + `unmatched` loop (FR-001/002/010) | WP03 | — |
| T008 | `fast-tests-core-misc` matrix split + `--ignore` mirror + integration `ignore_args` (FR-003/004/012) | WP03 | — |
| T009 | Always-on de-serialized `arch-adversarial` job + coverage `coverage-*.xml` emit (FR-005/006/013) | WP03 | — |
| T010 | Coverage-consumer + `JOB_GROUPS` heredoc + all needs-lists (FR-007/C-005/C-002) | WP03 | — |
| T011 | WP03 gates: WP02 reds → green; all 8 #2368 invariants green | WP03 | — |
| T012 | `ci-windows.yml` static `windows_critical` list for relocated windows-marked files (FR-008) | WP04 | [P] with WP05 |
| T013 | Coverage-topology ownership test + `coverage-*.xml` emit⇒consume proof (FR-006) | WP05 | [P] with WP04 |
| T014 | Post-shrink timings artifact + NFR-001 acceptance observation + C-006 nightly decision | WP05 | — |
| T015 | `_gate_coverage_baseline.json` refresh (totals unchanged) + issue-matrix verdicts + closeout comments | WP06 | — |

## Work Packages

### WP01 — Census + bound-model spine (Priority: P1)

- **Goal**: IC-03 + IC-04 substrate — deliver the NFR-006 **construction-derived** worklist as a committed, test-consumed census artifact with a **freshness-guard**, and extend `_gate_coverage.py` ADDITIVELY with every parsed relation WP02's invariants consume (differential-matrix per dir, same-tier per test, always-on arch-job recognition). Single-owner spine: READ-ONLY after this WP.
- **Independent Test**: WP01 exposes a pure `live_derived_worklist()` function so WP02's `test_ci_topology_worklist.py` asserts `census.worklist == live_derived_worklist()` (the mechanized freshness-guard — a stale census reds in CI, replacing any pasted self-check log); every existing gate-coverage / path-filter / marker-registry consumer test passes UNTOUCHED.
- **Priority**: P1 · **Requirement Refs**: FR-001, NFR-001, NFR-002, NFR-003, NFR-006, C-001 · **Prompt**: `/tasks/WP01-census-and-bound-model-spine.md`

#### Included Subtasks

- [x] T001 Author `tests/architectural/ci_topology_census.json`: committed `t_loc`, `rule`, `worklist[]`, `mapped_dirs[]`, `arch_blind_groups[]`, `timings_baseline` (29.4-min, `source_run_id`) — re-derived live, NOT hand-copied — with a **freshness-guard** (re-derive-from-live == frozen, or the guard reds).
- [x] T002 Extend `tests/architectural/_gate_coverage.py` additively: the differential-matrix relation `{dir → arch_selected}` (NFR-002), the same-tier uniqueness relation `{test → fast_shard_count, integration_shard_count}` (NFR-003), and always-on-arch-job recognition (a group-less `if: always()` suite job) — pure parsing, no assertions.
- [x] T003 Gates: existing consumers green with zero edits; live self-check counts (worklist size, arch-blind count, 8-marker set, needs-map sizes) recorded as WP02/WP03 ground truth.

#### Implementation Notes

- The census RULE (research §1.3): `D ∈ worklist ⟺` direct child of `src/specify_cli/` ∧ `sum(LOC *.py) ≥ T_LOC` ∧ no src-backed dorny group globs it. `T_LOC` is a committed constant in the artifact (recommended 500), NEVER a literal in the test.
- Freshness-guard is the NFR-006 teeth: a stale hand-edited census must red, so the metric measures coverage not the author's constant.

#### Dependencies

- None (starting package).

#### Risks & Mitigations

- Census drifts from live tree → freshness-guard re-derives and asserts equality; pin `T_LOC` in the artifact only.
- Existing parse behavior regressed → additive-only contract; every existing consumer test must pass with zero edits.

---

### WP02 — Red-first invariants (Priority: P1)

- **Goal**: IC-06 + the squad-demanded mechanized gates — author the NEW architectural invariants FAILING against today's topology, so WP03 has a red-to-green target that cannot be faked. NEW test files ONLY; the existing suite is untouched.
- **Independent Test**: Each of the eight new test files is `architectural`-marked (CI-selected) and, with reds captured on **WP01's tip** (census + `_gate_coverage` relations present, WP03 absent) so they are genuine topology-reds not missing-substrate errors, runs RED (recorded failure output); the `census.worklist == live_derived_worklist()` freshness assertion is green; zero edits to any pre-existing test file (`git diff --stat` shows only the eight new files).
- **Priority**: P1 · **Requirement Refs**: FR-001, FR-011, FR-013, NFR-002, NFR-003, NFR-005, NFR-006, C-005 · **Prompt**: `/tasks/WP02-red-first-invariants.md`

#### Included Subtasks

- [x] T004 [P] `test_ci_topology_worklist.py` (SC-001): iterate the committed census `worklist[]`, assert each dir maps to a named src-backed group AND a focused shard, `unmatched`/`run_all` NOT set. **Plus the NFR-006 freshness-guard assertion** `census.worklist == live_derived_worklist()` (calls WP01's pure re-derivation function; GREEN — a stale census reds). `test_arch_unblind_matrix.py` (NFR-002): differential-matrix asserts arch selects 100% of `src/specify_cli/*` dirs (0 blind).
- [x] T005 [P] `test_same_tier_uniqueness.py` (NFR-003): no test selected by >1 fast shard nor >1 integration shard — distinct from the report-only cross-tier duplicate warning. `test_coverage_consumer_needs.py` (C-005): coverage-emitters ⊆ `sonarcloud.needs`; critical-path emitters ⊆ `diff-coverage.needs`; explicitly does NOT intersect `slow-tests.needs`.
- [x] T006 [P] `test_serial_port_preservation.py` (FR-011): every shard touching daemon/real-port tests preserves a `-n0` serial pass and `--dist loadfile`. `test_job_count_ceiling.py` (NFR-005): `len(quality-gate.needs) ≤ ceiling` (ceiling pinned from the composite design).
- [x] T016 [P] `test_arch_pole_deserialized.py` (FR-013 structural gate): parse the arch/adversarial job's `needs` set and assert it contains NO fast-lane job (`fast-tests-core-misc`) — `if: always()` ≠ parallel, so only dropping the edge de-serializes. NATURAL RED today (edge present); green when WP03 drops it.
- [x] T017 [P] `test_shard_universe_bounded.py` (SC-003a): over the parsed shard-command set, assert no single shard collects the full catch-all universe (max single-shard selected-count `< total`, OR shard count `≥ N` from the composite design). Same-tier uniqueness alone does NOT imply the monolith was split. NATURAL RED today (one monolith); green post-split.

#### Implementation Notes

- All invariants pin BEHAVIORAL RELATIONS (a dir routes to a group; the arch job selects every dir), never workflow line numbers — refactor-stable per Directive 041.
- The NFR-005 ceiling constant is pinned here from the plan's composite design (~57 with composites vs ~45 today); WP03 must land under it.

#### Parallel Opportunities

- T004/T005/T006 are separate new files — safe to author concurrently within the WP.

#### Dependencies

- Depends on WP01 (consumes the census artifact + the new `_gate_coverage` relations).

#### Risks & Mitigations

- A vacuously-green invariant (would pass on today's broken topology) → RED evidence is a DoD anchor; any test green pre-WP03 is a defect, re-author.
- Coverage-consumer test wrongly intersects `slow-tests.needs` (fast-jobs-only) → C-005 correction is explicit in the prompt; test asserts the negative.

---

### WP03 — Single-owner `ci-quality.yml` surgery (Priority: P1)

- **Goal**: IC-01 + IC-02 + IC-04 + IC-05 — the SOLE owner of `.github/workflows/ci-quality.yml`. ALL topology edits land here: composite group additions (dedicated + composite per FR-010), `fast-tests-core-misc` matrix subdivision (FR-003), FR-013 arch-pole de-serialization + always-on arch job (Option A, NO filter group), the 5-edit atomic registration per group (FR-002), the `--ignore` mirror + integration `ignore_args` (FR-004/012), `JOB_GROUPS` heredoc, and every consuming needs-list (FR-007). Turns WP02 green.
- **Independent Test**: All eight WP02 invariants flip RED→GREEN (including `test_arch_pole_deserialized` — the arch `needs` drops the fast-lane job, FR-013; and `test_shard_universe_bounded` — no single shard owns the full universe, SC-003a); the 8 #2368 WP04 invariants stay green (`test_src_filter_coverage.py` + `test_workflow_coherence.py` + `test_marker_job_completeness.py`); `_gate_coverage` orphan count stays 0 and total selected unchanged.
- **Priority**: P1 · **Requirement Refs**: FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-009, FR-010, FR-011, FR-012, FR-013, NFR-004, C-002, C-003 · **Prompt**: `/tasks/WP03-single-owner-ci-quality.md`

#### Included Subtasks

- [x] T007 Register each census worklist dir into a composite src-backed filter group (FR-001/010): dorny `filters:` glob + `changes.outputs.<group>` row + `unmatched` enumeration loop entry (the 5-edit pattern surfaces 1-3, FR-002) — keeping FR-010c enumeration and FR-010 boolean invariants green.
- [x] T008 Subdivide `fast-tests-core-misc` into a focused matrix mirroring the integration shards (FR-003); update the `--ignore` mirror in lockstep (FR-012 invariant) and the integration-matrix `ignore_args` for nested `tests/specify_cli/<D>` roots (orchestrator_api, bulk_edit) (FR-004); consolidate the `migration` double-root preserving `and not slow` (FR-012).
- [x] T009 Extract the `architectural` shard into a standalone always-on `arch-adversarial` job: `if: always()` with NO dorny filter output (Option A — leaves `src_backed_groups`/`unmatched` untouched), drop `needs: fast-tests-core-misc` (FR-013 de-serialize), emit `coverage-*.xml` under the glob-consumed name (FR-006); preserve `-n0` serial + `--dist loadfile` + HOME isolation on new shards (FR-011); preserve fail-safe catch-all (FR-009).
- [x] T010 Wire the `JOB_GROUPS` heredoc rows (5-edit surfaces 4-5, FR-002) and register every new job into `quality-gate.needs`, `sonarcloud.needs`, `diff-coverage.needs`, `mutation-testing.needs` (C-005/FR-007) — NEVER `slow-tests.needs`; keep every derived surface asserted-against-parsed-source (C-002).
- [x] T011 Gates: WP02's eight reds → green (incl. `test_arch_pole_deserialized` FR-013 + `test_shard_universe_bounded` SC-003a); the 8 #2368 invariants green; orphan count 0, total selected unchanged; a probe PR per representative slice demonstrates focused routing (SC-006).

#### Implementation Notes

- **C-003 is the topology constraint**: this file is owned by exactly this WP. If per-slice workflow edits ever become unavoidable, FLATTEN the mission to `single_branch` with linearized shared-surface edits — a re-plan decision, NOT a lane split.
- The 5-edit atomic registration (research §4.4) must land per group in one commit or invariants 1/2/5/7 red.
- Un-blind (US2) and wallclock (US3) are the SAME arch-pole move (FR-013) — de-serialization alone moves the arch tail 29.4→12.3 min (meets the ≤13.6-min ceiling); sharding the fast job is the SC-003/NFR-004 failure-isolation win.

#### Dependencies

- Depends on WP02 (its invariants are the red-to-green target).

#### Risks & Mitigations

- Partial (<5) group registration reds FR-010c/FR-011 → the invariants ARE the safety net; land each group atomically.
- Always-on arch job accidentally carries a filter-group `if:` → perturbs `src_backed_groups` and reds FR-010; NFR-002 relation asserts it stays unconditional.
- A new `fast-tests-<group>` forgotten from a coverage consumer → C-005 invariant (WP02) reds by construction.

---

### WP04 — Second-layer Windows surface (Priority: P1)

- **Goal**: Propagate any new/relocated **windows-marked** test file into `ci-windows.yml`'s static `windows_critical` list (`:24-42`) — the ONLY real second-layer surface per the corrected FR-008. Do NOT touch `quality_gate_decision.py`, `drift-detector.yml`, or `release.yml` (they carry no shard/ignore/job→group data).
- **Independent Test**: FR-003c glob-live invariant (`test_every_filter_glob_is_live`, which covers `ci-windows.yml`) stays green — every `windows_critical` entry maps to a live test file, no dead glob; any windows-marked file relocated by WP03's carve is present in the static list.
- **Priority**: P1 · **Requirement Refs**: FR-008 · **Prompt**: `/tasks/WP04-second-layer-windows.md`

#### Included Subtasks

- [x] T012 For each windows-marked test file relocated by WP03's shard carve, update the static `windows_critical` list (`ci-windows.yml:24-42`) in lockstep; assert `test_every_filter_glob_is_live` green (no dead glob) and no split-brain (C-002).

#### Implementation Notes

- FR-008 correction: `quality_gate_decision.py` holds no job→group data; `drift-detector.yml`/`release.yml` carry no shard/ignore names — editing them is out of scope and would be drift.
- If WP03 relocated no windows-marked files, the DoD is the green glob-live invariant plus a recorded no-op justification (still non-fakeable — the invariant proves the list is coherent).

#### Dependencies

- Depends on WP03 (the carve determines which windows-marked files move).

#### Risks & Mitigations

- A relocated windows file dropped from the static list → FR-003c glob-live/coherence invariant reds; update in the same landing.

---

### WP05 — Coverage-topology + timing verification (Priority: P2)

- **Goal**: Prove coverage emit⇒consume by construction (FR-006) with a coverage-ownership test, and record the NFR-001 **acceptance observation** — measure the post-shrink core-misc critical-path lane against the committed 29.4-min baseline (ceiling ≈13.6 min) in a committed timings artifact; confirm no nightly blind spot; make the C-006 nightly-schedule decision iff the measured PR critical path still >15 min.
- **Independent Test**: `tests/release/test_coverage_topology_ownership.py` asserts every new `coverage-<D>.xml`-emitting job is matched by the aggregator's `coverage-*.xml` wildcard consumer (emit⇒consume); the committed `ci_topology_timings_postshrink.json` records measured lane ≤ ceiling with `source_run_id`.
- **Priority**: P2 · **Requirement Refs**: FR-006, NFR-001, C-006 · **Prompt**: `/tasks/WP05-coverage-topology-timing.md`

#### Included Subtasks

- [x] T013 [P] Author `tests/release/test_coverage_topology_ownership.py`: each shard's `coverage-*.xml` name is glob-consumed by the aggregator download (FR-006 emit⇒consume by construction); no emitter's XML is silently dropped.
- [x] T014 Record `tests/release/ci_topology_timings_postshrink.json`: measured post-shrink core-misc critical path vs the WP01 baseline, `source_run_id`, verdict ≤55% AND ≤ next-longest lane (NFR-001). State the C-006 nightly decision: thin nightly-schedule option ONLY if measured PR critical path still >~15 min; else record that the shrink satisfies #1933's intent with escape hatches + nightly `run_all` over-cover intact.

#### Implementation Notes

- NFR-001 is a plan/verify acceptance observation, NOT a standing unit gate — it lives in the committed artifact, not as a flaky timing assertion.
- The timings artifact is a SEPARATE file from WP01's census (owned-file disjointness); WP01 holds the pre-mission baseline, WP05 the post-mission measurement.

#### Parallel Opportunities

- Runs in parallel with WP04 (disjoint files; both depend only on WP03).

#### Dependencies

- Depends on WP03 (the carved shards + de-serialized arch pole are what is measured).

#### Risks & Mitigations

- Measured critical path still >ceiling → the artifact records it honestly and triggers the C-006 nightly-option evaluation; not a silent pass.
- A coverage XML silently dropped → the ownership test reds; complements WP02's C-005 needs-list invariant (needs-list membership vs glob-consumption are two distinct guards).

---

### WP06 — Closeout (Priority: P2)

- **Goal**: Refresh the ratchet baseline (`orphan_test_count`=0 and no previously-collected test disappears — `total_tests` RISES by the newly-added gated tests), set every issue-matrix verdict to a terminal value, post closeout comments, and the #1931 rollup. Coordinate-note: #2072 also re-keys `_gate_coverage_baseline.json` — flag the shared file.
- **Independent Test**: `_gate_coverage_baseline.json` refreshed with `orphan_test_count`=0 and no dropped test (`total_tests` rises by the 8 new WP02 + 1 new WP05 gated files — a DROP or new orphan is the regression), asserted by the orphan ratchet (`test_gate_coverage.py`) staying green; `issue-matrix.md` has zero `unknown`/`in-mission` rows remaining (all terminal); all 8 #2368 invariants + the new relations green on the merged tree (NFR-007 sweep).
- **Priority**: P2 · **Requirement Refs**: NFR-007, C-006 · **Prompt**: `/tasks/WP06-closeout.md`

#### Included Subtasks

- [x] T015 Refresh `tests/architectural/_gate_coverage_baseline.json` (`--update-baseline`; `orphan_test_count` MUST stay 0 and NO previously-collected test may disappear — `total_tests` legitimately RISES by the newly-added gated tests: the 8 new WP02 files + the 1 new WP05 file; a DROP or new orphan is the regression, not a rekey). Set `issue-matrix.md` terminal verdicts (**note: `issue-matrix.md` is under `kitty-specs/` — a planning-artifact/coord edit, NOT an `owned_files` entry, so no ownership violation**). Post closeout comments on #2378 (shard-side), #1933 (group-side, shrink-intent statement), #2383 (arch un-blind); #1931 rollup (terminal at closeout). Append the CHANGELOG entry (root `CHANGELOG.md` is a symlink → `docs/changelog/CHANGELOG.md`). Flag the #2072 shared-baseline coordinate.

#### Implementation Notes

- The baseline refresh must keep `orphan_test_count`=0 and drop no previously-collected test — `total_tests` RISING by the newly-added gated tests is expected and correct; a DROP or a new orphan is the real regression, not a rekey; investigate before committing.
- CHANGELOG edits go through the symlink target `docs/changelog/CHANGELOG.md`.

#### Dependencies

- Depends on WP04 and WP05 (closeout follows second-layer + verification).

#### Risks & Mitigations

- Baseline rekey introduces a new orphan or DROPS a previously-collected test → assert `orphan_test_count`=0 and no-test-disappears as the DoD anchor (a `total_tests` rise from the new gated tests is expected, not a regression).
- #2072 concurrently rekeys the same baseline → flag the coordinate in the closeout comment so a later agent does not clobber.

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP02 → WP03 → {WP04 ∥ WP05} → WP06. Near-linear per C-003 (single-owner `ci-quality.yml`).
- **Parallelization**: WP04 and WP05 run concurrently (disjoint files, both depend only on WP03). Within WP02, the eight invariant files are independently authorable.
- **MVP Scope**: WP01→WP02→WP03 delivers the correctness + wallclock core (Mode-A close + Mode-B un-blind + de-serialization). WP04/WP05/WP06 are propagation, verification, and closeout.

## Dependency notes

`ci-quality.yml` is edited by WP03 ALONE (C-003 — a `lanes` allocator rejects overlapping `owned_files`; per-slice WPs cannot co-own one file). WPs partition by FILE: WP01 owns the bound-model parse + census; WP02 owns the new invariant test files; WP03 owns `ci-quality.yml`; WP04 owns `ci-windows.yml`; WP05 owns the coverage-ownership test + timings artifact; WP06 owns the baseline + issue-matrix + CHANGELOG. Zero owned-file overlap across WPs (verified).

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP01 (census/worklist authority), WP03 (register groups) |
| FR-002 | WP03 |
| FR-003 | WP03 |
| FR-004 | WP03 |
| FR-005 | WP03 |
| FR-006 | WP03 (emit), WP05 (verify) |
| FR-007 | WP03 |
| FR-008 | WP04 |
| FR-009 | WP03 (deliver), WP02/WP05 (assert) |
| FR-010 | WP03 |
| FR-011 | WP02 (invariant), WP03 (deliver) |
| FR-012 | WP03 |
| FR-013 | WP02 (structural gate — arch `needs` drops the fast-lane job), WP03 (deliver) |
| NFR-001 | WP01 (baseline artifact), WP05 (acceptance observation) |
| NFR-002 | WP01 (relation), WP02 (test), WP03 (satisfy) |
| NFR-003 | WP01 (relation), WP02 (test), WP03 (satisfy) |
| NFR-004 | WP02 (test), WP03 (deliver) |
| NFR-005 | WP02 (test), WP03 (satisfy) |
| NFR-006 | WP01 |
| NFR-007 | WP03 (through-green), WP06 (final sweep) |
| C-001 | WP01, WP03 |
| C-002 | WP03 |
| C-003 | WP03 (topology decision) |
| C-004 | All (scope fence) |
| C-005 | WP02 (test), WP03 (satisfy) |
| C-006 | WP05 (decision), WP06 (closeout statement) |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Census artifact + freshness-guard | WP01 | P1 | No |
| T002 | `_gate_coverage.py` additive relations | WP01 | P1 | No |
| T003 | WP01 gates | WP01 | P1 | No |
| T004 | RED worklist + arch-unblind matrix | WP02 | P1 | Yes |
| T005 | RED same-tier + coverage-consumer | WP02 | P1 | Yes |
| T006 | RED serial-port + job-count ceiling | WP02 | P1 | Yes |
| T016 | RED arch-pole de-serialized (FR-013 structural gate) | WP02 | P1 | Yes |
| T017 | RED shard-universe bounded (SC-003a) | WP02 | P1 | Yes |
| T007 | Composite groups + 5-edit surfaces 1-3 | WP03 | P1 | No |
| T008 | Fast matrix split + ignore mirror | WP03 | P1 | No |
| T009 | Always-on de-serialized arch job | WP03 | P1 | No |
| T010 | JOB_GROUPS + needs-lists | WP03 | P1 | No |
| T011 | WP03 gates | WP03 | P1 | No |
| T012 | ci-windows static list | WP04 | P1 | Yes |
| T013 | Coverage-topology ownership test | WP05 | P2 | Yes |
| T014 | Post-shrink timings + C-006 decision | WP05 | P2 | No |
| T015 | Baseline refresh + issue-matrix + closeout | WP06 | P2 | No |
