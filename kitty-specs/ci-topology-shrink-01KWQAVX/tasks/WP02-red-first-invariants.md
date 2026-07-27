---
work_package_id: WP02
title: 'Red-first invariants: SC-001 worklist, NFR-002 arch-matrix, NFR-003 uniqueness, C-005 coverage-consumer, FR-011 serial, NFR-005 ceiling, FR-013 arch-pole-deserialized, SC-003a shard-universe-bounded'
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-011
- FR-013
- NFR-002
- NFR-003
- NFR-005
- NFR-006
- C-005
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-ci-topology-shrink-01KWQAVX
base_commit: aa998ede7e31927286e78e7819757e03c2f2c604
created_at: '2026-07-04T21:00:00+00:00'
subtasks:
- T004
- T005
- T006
- T016
- T017
phase: Phase 2 - Red-first invariants
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1028132"
history:
- at: '2026-07-04T21:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_ci_topology_worklist.py
- tests/architectural/test_arch_unblind_matrix.py
- tests/architectural/test_same_tier_uniqueness.py
- tests/architectural/test_coverage_consumer_needs.py
- tests/architectural/test_serial_port_preservation.py
- tests/architectural/test_job_count_ceiling.py
- tests/architectural/test_arch_pole_deserialized.py
- tests/architectural/test_shard_universe_bounded.py
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_ci_topology_worklist.py
- tests/architectural/test_arch_unblind_matrix.py
- tests/architectural/test_same_tier_uniqueness.py
- tests/architectural/test_coverage_consumer_needs.py
- tests/architectural/test_serial_port_preservation.py
- tests/architectural/test_job_count_ceiling.py
- tests/architectural/test_arch_pole_deserialized.py
- tests/architectural/test_shard_universe_bounded.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Red-first invariants

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

Author the eight NEW architectural invariants the post-tasks squad demanded — **each authored FAILING against today's topology** so WP03 has a red-to-green target that cannot be faked. NEW test files ONLY; the existing `tests/architectural/` suite is UNTOUCHED (`git diff --stat` must show only the eight new files). Every invariant pins a BEHAVIORAL RELATION over the parsed model (Directive 041 — refactor-stable), never a workflow line number. All eight files are `architectural`-marked so CI selects them.

Consume ONLY the additive relations WP01 added to `_gate_coverage.py` (and the committed census). Do NOT re-derive the bound model here.

## Subtasks & Detailed Guidance

### Subtask T004 [P] – Worklist + arch-unblind matrix
- `test_ci_topology_worklist.py` (**SC-001 / FR-001 / NFR-006**): load the committed `tests/architectural/ci_topology_census.json`, ITERATE `worklist[]`, assert each dir maps to a named src-backed filter group AND a focused shard, and that a touch of `src/specify_cli/<dir>/**` does NOT set `unmatched=true`/`run_all`. The floor `t_loc` comes from the artifact, NOT a literal. RED today: every worklist dir currently trips `unmatched`.
  - **Freshness-guard assertion (NFR-006 seam — closes SC-001 vacuous-pass gaming)**: add a GREEN `architectural`-marked assertion `census.worklist == live_derived_worklist()` that calls WP01's pure re-derivation function (the seam WP01 exposes for this test) and re-derives the worklist from the LIVE tree. A hand-trimmed or stale census then REDS in CI — the freshness check is a pytest-collected assertion, NOT pasted prose in an Activity Log. This is the mechanized replacement for the "pasted live self-check output" anchor.
- `test_arch_unblind_matrix.py` (**SC-002 / NFR-002**): assert the differential-matrix relation selects the arch/adversarial suite over **100%** of `src/specify_cli/*` dirs (0 blind). RED today: 13 arch-blind dirs.

### Subtask T005 [P] – Same-tier uniqueness + coverage-consumer
- `test_same_tier_uniqueness.py` (**NFR-003 / SC-004**): assert no test is selected by >1 fast shard nor by >1 integration shard (over the same-tier relation). Distinct from the existing report-only cross-tier duplicate warning. Assert `_gate_coverage` orphan count stays 0 and total selected unchanged (baseline totals). RED today: authored against the post-split expectation, may need a fault-injection fixture to prove it bites.
- `test_coverage_consumer_needs.py` (**C-005 / FR-006 / FR-007**): assert coverage-emitting jobs ⊆ `sonarcloud.needs` AND critical-path emitters ⊆ `diff-coverage.needs` (and `mutation-testing.needs` where it consumes them). **Assert the NEGATIVE**: the invariant must NOT intersect `slow-tests.needs` (fast-jobs-only — would red on arrival). RED today: the new WP03 jobs do not yet exist / are not yet in the consumer lists.

### Subtask T006 [P] – Serial-port preservation + job-count ceiling
- `test_serial_port_preservation.py` (**FR-011**): assert every shard whose positional roots include daemon/real-port tests (e.g. `tests/sync/test_orphan_sweep.py`, ports 9400-9449) preserves a `-n0` serial pass and uses `--dist loadfile` (never bare `load`) + per-worker HOME isolation. RED today if WP03's split were to drop the serial pass (author against the post-split shape; use a fault-injection negative to prove it bites).
- `test_job_count_ceiling.py` (**NFR-005**): assert `len(quality-gate.needs) ≤ CEILING`. Pin `CEILING` from the plan's composite design (~57 with composites; today ~45). RED-negative discipline: also prove the test would red if the graph exceeded the ceiling (fault-injection).

### Subtask T016 [P] – Arch-pole de-serialization structural gate (FR-013)
- `test_arch_pole_deserialized.py` (**FR-013 / structural**): parse the arch/adversarial job's `needs` set from the bound model and assert it contains **NO fast-lane job** (e.g. `fast-tests-core-misc`). This is the structural gate the squad demanded because `if: always()` + `needs: [fast-tests-core-misc]` is STILL serialized — `always()` ≠ parallel; the job still waits on the fast lane's timeline before starting. Only DROPPING the edge de-serializes it (FR-013). **NATURAL RED today** (the serialization edge is present); flips GREEN when WP03 drops `needs: fast-tests-core-misc`. Pin the BEHAVIORAL relation (parsed `needs` set excludes any fast-lane job), never a workflow line number.

### Subtask T017 [P] – Shard-universe boundedness (SC-003a)
- `test_shard_universe_bounded.py` (**SC-003a / structural**): over the parsed shard-command set, assert that NO single shard collects the full catch-all universe — e.g. the max single-shard selected-test-count is strictly `< total`, OR the shard count is `≥ N` (the pinned shard-count from the composite design). Rationale: same-tier uniqueness (NFR-003) alone does NOT imply the monolith was split — one giant shard trivially satisfies uniqueness. This invariant closes that gap (SC-003a was previously unowned). **NATURAL RED today** (one monolithic `fast-tests-core-misc` shard collects the universe); GREEN post-split. Pin the relation over the parsed shard set, not a line number.

## Implementation Notes

- RED-first is a DoD anchor: run each new file on the planning base and RECORD the failing output. Any invariant that is green pre-WP03 is a defect (vacuous) — re-author with a fault-injection fixture until it bites.
- Pin behavioral relations, not line numbers. Where a relation needs a synthetic universe, keep the synthetic size out of the assertion's meaning (do not hard-code the real census count).

## Campsite cleaning (standing rule; ride the WP's normal review)

New files — write them clean from the start: `ruff --select ALL` exit 0, `mypy` Success, docstrings on every test, no `# noqa` unless individually justified. Do not touch files outside the eight owned.

## Definition of Done (non-fakeable — every anchor is recorded RED evidence)

- **Eight new files exist, `architectural`-marked, reds captured on WP01's tip** (census + `_gate_coverage` additive relations present, WP03 absent) — NOT the bare planning base. This makes the reds genuine topology-reds (edge present / monolith unsplit / dirs arch-blind), not missing-substrate `ImportError`/`FileNotFoundError` errors. Paste the failing output per file in the Activity Log (assertion/`AttributeError` iterating real census/model data — not a placeholder skip).
- **`test_arch_pole_deserialized` (FOLD 1) is a NATURAL red today**: the parsed arch/adversarial `needs` set still contains a fast-lane job (`fast-tests-core-misc`) because `if: always()` ≠ parallel; it flips green only when WP03 drops that edge (FR-013 de-serialized).
- **`test_shard_universe_bounded` (FOLD 3) is a NATURAL red today**: one monolithic shard collects the full catch-all universe; green only post-split (SC-003a).
- **`census.worklist == live_derived_worklist()` assertion is GREEN** in `test_ci_topology_worklist.py` (calls WP01's pure re-derivation function) — a stale/hand-trimmed census reds in CI (NFR-006 freshness-guard is a pytest-collected assertion, not pasted prose; closes the SC-001 vacuous-pass gaming).
- **Zero edits to any pre-existing test file** (`git diff --stat` shows only the eight new files).
- Each invariant proven to BITE: fault-injection red-negative recorded for NFR-003/FR-011/NFR-005 (relations that could pass vacuously). `test_arch_pole_deserialized` and `test_shard_universe_bounded` bite naturally (real topology reds, no fault-injection needed).
- `ruff` + `mypy` clean on the eight files.

## Risks / Reviewer Guidance

- Reject any vacuously-green invariant (passes on today's broken topology) — RED evidence is the gate.
- Reject a coverage-consumer test that intersects `slow-tests.needs` — the C-005 correction is explicit; it must assert the negative.
- Reject any edit to the existing suite — WP02 is new-files-only by contract.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-04T21:00:00Z – system – Prompt created.
- 2026-07-04T22:37:04Z – claude:opus:python-pedro:implementer – shell_pid=991561 – Assigned agent via action command
- 2026-07-05T00:55:00Z – claude:opus:python-pedro:implementer – Loaded python-pedro; applied DIR-041 (tests pin behavioral relations over the WP01 bound model/committed census, never workflow line numbers — every invariant survives a re-shard/rename) and DIR-043 (the 8 tests ARE the structural gate that closes Mode-A/Mode-B/coverage-drop by construction), plus DIR-030 (ruff+mypy clean) and DIR-024 (new-files-only, no edits to the existing suite or `_gate_coverage.py`). Authored 8 new `architectural`-marked files on WP01's tip (census + additive relations present, WP03 absent). Consumed only WP01's additive relations (`live_derived_worklist`, `differential_arch_matrix`, `same_tier_shard_counts`, `WorkflowModel.*`); did NOT re-derive the model.
- 2026-07-05T00:55:30Z – claude:opus:python-pedro:implementer – RED CAPTURED — test_ci_topology_worklist.py (SC-001/FR-001/NFR-006), `2 failed, 4 passed in 36.02s`. Topology-reds (AssertionError iterating the real committed census): `test_every_worklist_dir_routes_to_named_src_backed_group` — 32 worklist dirs whose target group is not a live src-backed dorny group (e.g. `retrospective->'closeout'`, `auth->'auth_audit_git'`, `dossier->'agent_surface'` …); `test_no_worklist_dir_falls_to_unmatched_run_all` — the same 32 dirs still trip `unmatched->run_all` on a confined touch (`['audit','auth','bulk_edit',…,'workspace']`). GREEN freshness guard `test_census_worklist_matches_live_derivation` (`census.worklist == live_derived_worklist()`) PASSES — a stale/hand-trimmed census would red (NFR-006). LOC-floor + shard-declared sanity green (t_loc read from artifact).
- 2026-07-05T00:55:45Z – claude:opus:python-pedro:implementer – RED CAPTURED — test_arch_unblind_matrix.py (SC-002/NFR-002), `2 failed, 1 passed in 23.05s`. Topology-reds over `differential_arch_matrix()`: `test_no_src_dir_is_architecturally_blind` + `test_every_dir_is_arch_selected` — 13 arch-blind dirs `['agent_utils','charter_runtime','cli','dashboard','lanes','merge','missions','post_merge','release','review','runtime','sync','upgrade']`. `test_matrix_spans_every_src_package_dir` green (matrix covers 100% of dirs).
- 2026-07-05T00:56:00Z – claude:opus:python-pedro:implementer – RED CAPTURED — test_same_tier_uniqueness.py (NFR-003/SC-004), `2 failed, 2 passed in 61.28s` (collects the live universe = 28,673 tests). Topology-reds over `same_tier_shard_counts(gates, universe)`: `test_no_test_selected_by_multiple_fast_shards` — 2494 tests in >1 fast shard (sample `tests/docs/test_adr_converter.py::…`); `test_no_test_selected_by_multiple_integration_shards` — 796 tests in >1 integration shard (sample `tests/architectural/test_execution_context_parity.py::…` ×7). GREEN no-drop guard `test_split_preserves_zero_orphans` (orphan_count == 0). FAULT-INJECTION `test_same_tier_relation_bites_on_synthetic_double_run` PASSES — a synthetic test placed in two `fast-tests-*` gates is flagged `count_fast_shards==2`, proving the relation BITES independent of live size.
- 2026-07-05T00:56:15Z – claude:opus:python-pedro:implementer – RED CAPTURED — test_coverage_consumer_needs.py (C-005/FR-006/FR-007), `1 failed, 3 passed in 22.38s`. Topology-red: `test_src_coverage_emitters_are_sonarcloud_consumers` — `mission-loader-coverage` emits `--cov=src/specify_cli/mission_loader` + uploads its XML but is absent from `sonarcloud.needs` (a genuine coverage-consumer drop of the exact C-005 class). GREEN correction `test_coverage_binding_is_not_slow_tests_needs` (emitters ⊄ `slow-tests.needs`, so slow-tests is provably the wrong consumer — asserts the NEGATIVE per the C-005 correction). GREEN phantom-needs guard on `diff-coverage.needs`/`mutation-testing.needs`. NOTE for reviewer/WP03: the strict "critical-path emitters ⊆ diff-coverage.needs" direction is deliberately NOT a hard subset — today diff-coverage draws critical-path coverage from an intentional MIX of fast+integration providers (e.g. `fast-tests-charter` but `integration-tests-status`), so a naive subset would false-red on intentional redundancy (DIR-041). WP03 turns the sonarcloud subset green by adding `mission-loader-coverage` (+ the new composite/arch emitters) to `sonarcloud.needs`.
- 2026-07-05T00:56:30Z – claude:opus:python-pedro:implementer – GREEN + FAULT-INJECTION — test_serial_port_preservation.py (FR-011), `5 passed in 22.20s`. FR-011 is preserved today (live GREEN): the daemon suite `tests/sync/test_orphan_sweep.py` (ports 9400-9449) is `--ignore`d out of every `-n auto` pool (`fast-tests-core-misc` ignores `tests/sync`; `fast-tests-sync` ignores the file) and runs in a dedicated `-n0` serial pass (`fast-tests-sync`), evaluated GLOBALLY across all jobs; no bare `--dist load`. Because it could pass vacuously, 3 FAULT-INJECTION tests PROVE BITE: daemon in a `-n auto` pool → flagged; daemon excluded from parallel with no serial pass anywhere → flagged; bare `--dist load` → flagged. xdist flags are not in the WP01 model, so this parses raw workflow run-text (a new relation, not a re-derivation).
- 2026-07-05T00:56:45Z – claude:opus:python-pedro:implementer – GREEN + FAULT-INJECTION — test_job_count_ceiling.py (NFR-005), `3 passed in 22.13s`. `len(quality-gate.needs) == 45 <= CEILING`. CEILING pinned = 57 from plan.md Complexity Tracking ("~32 dedicated jobs balloon quality-gate.needs (~45 today) past the ceiling; composites cap it (~57)"). Live GREEN (headroom); FAULT-INJECTION `test_ceiling_relation_bites_when_graph_exceeds_it` PASSES — a synthetic graph of `CEILING+1` needs reds the predicate (synthetic size kept out of the assertion's meaning).
- 2026-07-05T00:57:00Z – claude:opus:python-pedro:implementer – NATURAL RED CAPTURED — test_arch_pole_deserialized.py (FR-013), `1 failed, 1 passed in 22.01s`. Topology-red `test_arch_pole_needs_no_fast_lane_job`: the arch-running job `integration-tests-core-misc` (identified via `positive_marker_tokens` ⊇ {architectural}) declares `needs: [changes, fast-tests-core-misc]` — a fast-lane serialization edge. `if: always()` ≠ parallel; only DROPPING the edge de-serializes it (WP03). Behavioral relation over the parsed `needs` set, no line number. Sanity `test_architectural_suite_has_a_running_job` green.
- 2026-07-05T00:57:15Z – claude:opus:python-pedro:implementer – NATURAL RED CAPTURED — test_shard_universe_bounded.py (SC-003a), `1 failed, 1 passed in 58.07s`. Topology-red `test_no_single_shard_collects_the_full_catch_all_universe`: `fast-tests-core-misc` is a single unsharded shard whose selection (11,338 tests) equals its full catch-all universe (`max_single_shard == job_catch_all_universe == 11338`, `shard_count == 1`) — the monolith SC-003a targets; NFR-003 uniqueness alone cannot detect it. `integration-tests-core-misc` (6-shard matrix) passes. GREEN post-split when WP03 matrix-splits the fast core-misc job. Sanity `test_catch_all_jobs_are_present` green.
- 2026-07-05T00:57:30Z – claude:opus:python-pedro:implementer – GATES: `ruff check` (project config: E/F/W/C90/C4/ARG/B/SIM/UP/ASYNC/S/TID251) → All checks passed on all 8 files; `mypy` → Success (8 source files). Every RED is a genuine TOPOLOGY red (AssertionError over real census/model/universe data), NOT a missing-substrate ImportError/FileNotFoundError. Committed 8 code files in lane-b as `419629012` (test files only; `git show --stat` = 8 files, 851 insertions; no edits to the existing suite or `_gate_coverage.py`).
- 2026-07-04T23:12:44Z – claude:opus:python-pedro:implementer – shell_pid=991561 – 8 red-first invariants; reds captured on WP01 tip; freshness assertion green; 3 fault-injections recorded (NFR-003/FR-011/NFR-005)
- 2026-07-04T23:14:29Z – claude:opus:reviewer-renata:reviewer – shell_pid=1028132 – Started review via action command
- 2026-07-04T23:26:11Z – user – shell_pid=1028132 – Review passed (reviewer-renata; applied DIR-041 refactor-stable, DIR-024 locality/scope, DIR-030 gate-quality, non-fakeable-assertion + contract-vs-implementation scrutiny). NO scope violation: WP02 commit 419629012 is the 8 test files ONLY; the _gate_coverage.py+census delta in the lane..mission diff is WP01's commit 8daa01752 carried into lane-b via cross-lane dep propagation (lane-b depends_on lane-a), not a WP02 edit. All 8 reds are GENUINE topology-reds (AssertionError over real census/model/universe) with zero missing-substrate ImportError/FileNotFoundError: worklist 32 unrouted+32 unmatched (freshness guard GREEN), arch_unblind 13 blind dirs, same_tier 2494 fast+796 integration doubles, coverage_consumer mission-loader-coverage absent from sonarcloud.needs (a REAL production C-005 drop), arch_pole integration-tests-core-misc needs fast-tests-core-misc (natural), shard_universe fast-tests-core-misc 11338==11338/shard_count 1 (natural); serial_port + job_count GREEN-today with all fault-injections biting (parallel-daemon/dropped-serial/bare-load; over-ceiling graph; synthetic same-tier double). C-005 RULING: ACCEPT the deliberate narrowing. Both sonarcloud AND diff-coverage ingest coverage via a GLOB (pattern:'*-reports' + find coverage-*.xml), so needs is an ORDERING guarantee; sonarcloud is THE binding Sonar consumer and the strict emitters-subset-sonarcloud.needs IS asserted and reds today, so a forgotten new fast-tests-<D> emitter WILL red the sonarcloud arm. The strict critical-path-subset-diff-coverage.needs is genuinely un-assertable without a DIR-041 false-red (src/doctrine is critical-path, fast-tests-doctrine emits --cov=src/doctrine yet diff-coverage deliberately draws doctrine from integration-tests-doctrine; fast-tests-doctrine absent from diff-coverage.needs today), and mutation-testing is if:false; the phantom-needs guard is the correct safe-direction check. Residual narrow race-drop risk on diff-coverage is covered by the sonarcloud arm (binding authority). NFR-003 is a faithful SC-004 encoding (within-tier uniqueness; cross-tier overlap left legitimate) - correct, not over-strict. ruff (project config) clean + mypy Success; no line-number pins, synthetic sizes kept out of assertion meaning. NIT (non-blocking): ruff --select ALL shows 7 D401 + 1 TC003, stylistic rules not in the project profile.
