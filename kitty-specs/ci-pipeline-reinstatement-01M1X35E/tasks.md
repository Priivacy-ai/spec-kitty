# Tasks: CI Pipeline Reinstatement

**Mission**: `ci-pipeline-reinstatement-01M1X35E`
**Planning base / merge target**: `feat/ci-pipeline-reinstatement`

Subtask completion is event-sourced — record with
`spec-kitty agent tasks mark-status Txxx --status done`. The rows below are
reference rows (`Txxx Description (WPxx)`), **not** checkboxes.

**Delivery is cluster-gated**: `FOUNDATION → TOPOLOGY → LEAN-SUITE`. A cluster's
exit gate (a real dispatched pipeline run + the in-repo gates) must be green
before the next cluster's WPs claim. Every TOPOLOGY WP depends on **all**
FOUNDATION WPs; every LEAN-SUITE WP depends on the TOPOLOGY WPs it builds on.

**ATDD red-first (C-011, binding):** every WP's first subtask commits a
failing-first behavior/ATDD test as a **separate first commit** that pins the
WP's observable behavior. For CI-YAML WPs the red-first test is an in-repo test
(`tests/release/` or `tests/architectural/`) asserting the workflow/gate
behavior. The reviewer verifies red-on-base → green-on-final.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Red-first: extend `test_release_ci_ownership.py` pinning the `introduced` set + `ci.yml` neutralized (RED on base) | WP01 | |
| T002 | Tidy-first: campsite the ownership-test module (extract disposition-set helpers, behavior-preserving) | WP01 | |
| T003 | Add `introduced` disposition + rows to `interim-ci-producer.md`; reconcile stale EXPERIMENTAL/public split | WP01 | |
| T004 | Neutralize/retire dead `.github/workflows/ci.yml` (archived-inert EXPERIMENTAL producer) | WP01 | |
| T005 | Ownership test: introduced exact-set + stock-runner + no-`SK_CI_TOKEN` + runs-on-every-workflow-PR + self-mutation | WP01 | |
| T006 | Reconcile `test_private_factory_ci_is_scoped_to_experimental_repo` with `ci.yml` retirement (no orphaned red) | WP01 | |
| T007 | Red-first: self-mutation negative — plant dead-code shard/retired-import → census flags dead + exclusion fires (RED) | WP02 | |
| T008 | Census schema + data artefact `p1_census/census.json` (surface/status/evidence/authorizes) | WP02 | |
| T009 | Census oracle `_p1_census_oracle.py`: importer-graph + retirement-gate resolution → per-surface status | WP02 | |
| T010 | False-negative guard: a drop requires independent evidence (gate-ref / ADR / zero-importer-AND-not-dynamic) | WP02 | |
| T011 | False-positive "known-live is never dead" guard: dynamic-reach importer-0 surfaces refused as dead (planted) | WP02 | |
| T012 | Non-vacuity floor (fails on empty set) + coverage-denominator-exclusion; enforcement allowlists out of scope | WP02 | |
| T013 | Red-first: reproduce #3284 into the triage record; assert base is red (the observable precondition) | WP03 | |
| T014 | Per-red independent-evidence triage: drop-dead-code (census-authorized) vs fix-live-regression, each evidenced | WP03 | |
| T015 | Drop census-authorized dead-import `mission_v1` test files (enumerated) with per-file evidence | WP03 | |
| T016 | Fix any live-regression red at the stable entry point (or record all 23 as census-dead drops with evidence) | WP03 | |
| T017 | Verify base green (0 untracked failures); no third "leave-red" disposition; record run evidence | WP03 | |
| T018 | Red-first: `test_warmup_action.py` pins the composite contract (pinned-rev PR / latest nightly, cache key) (RED) | WP04 | |
| T019 | Author `.github/actions/warmup/action.yml` composite: resolve + editable install once | WP04 | |
| T020 | PR mode: pinned `spec_kitty_events` rev; `actions/cache` keyed on `uv.lock` + resolved rev | WP04 | |
| T021 | Nightly/full mode: latest mainline (upstream-drift signal); mode input threading | WP04 | |
| T022 | Prove #3283 bootstrap-lock elimination: one pre-warm, downstream reuse without re-install (documented) | WP04 | |
| T023 | Red-first: `test_retirement_scrub.py` asserts no group/`--cov` maps to retired/never-restore, census-cross-checked (RED) | WP05 | |
| T024 | Re-derive dorny filter groups against live `src/**` (drop sync/saas/delivery/emit + never-restore) | WP05 | |
| T025 | Re-derive `--cov=<module>` targets against live `src/**`; census-authorized exclusions only | WP05 | |
| T026 | Persist scrub result `ci_retirement_scrub.json` (group→roots, cov targets, census evidence per exclusion) | WP05 | |
| T027 | Assert enforcement allowlists (`test_no_dead_*`/`test_no_retired_subsystems`) stay always-on, untouched | WP05 | |
| T028 | Red-first: re-validate the ~5 active `xfail(strict=True)` landmines (RED capturing current strict-xfail state) | WP06 | |
| T029 | Resolve `test_transition_gate_parity.py` + `test_sc6_planning_placement_e2e.py` strict-xfail (fix or convert) | WP06 | |
| T030 | Resolve `test_egress_consent_boundary.py` + `test_init_integration.py` strict-xfail | WP06 | |
| T031 | Fix env-leaker `tests/agent/test_context_validation_unit.py` (order-independent under any shard order) | WP06 | |
| T032 | Fix env-leaker `tests/docs/test_check_cli_reference_freshness.py` | WP06 | |
| T033 | Extend `tests/conftest.py` env-isolation so shard-order divergence cannot red only in CI | WP06 | |
| T034 | Red-first: rewrite `test_ci_quality_path_filters.py` for two-authority + fail-closed unmatched→run-all (RED) | WP07 | |
| T035 | Tidy-first + author `.github/workflows/ci-router.yml`: dorny `changes` + shift-left front (cheapest first) | WP07 | |
| T036 | Job `if:` gates (group→job); fast always-on gates de-serialized, heavy arch battery code-scoped (NFR-002/FR-008) | WP07 | |
| T037 | Build single importable gate-selection authority `scripts/ci/gate_selection.py` (parses the two authorities) | WP07 | |
| T038 | `test_gate_selection_authority.py`: "which shards/gates does this diff select"; asserted vs the two hand-sources | WP07 | |
| T039 | Fail-closed catch-all: `src/**` unmatched → run-all loud alarm; docs/corpus excluded from unmatched loop | WP07 | |
| T040 | Red-first: `test_module_shard_registry.py` — registry completeness + skew ≤20% on measured, post-scrub basis (RED) | WP08 | |
| T041 | Record a `--durations` run on the scrubbed live basis (run-id captured) → `.github/ci-shard-timings.json` | WP08 | |
| T042 | Derive committed registry `.github/ci-module-registry.yml` (module→roots, `--cov`, tier, shard_count), duration-balanced | WP08 | |
| T043 | De-serialize `integration-tests-next` (`-n auto`) + take the arch pole off the critical path | WP08 | |
| T044 | Assert registry is the single data source (add-module = row) + ≤20-reusable-workflow ceiling | WP08 | |
| T045 | Red-first: `test_module_tests_matrix.py` — matrix realizes every registry row + `workflow_call` contract (RED) | WP09 | |
| T046 | Author `.github/workflows/module-tests.yml` reusable `workflow_call` shard (consumes warmup env, emits artefacts) | WP09 | |
| T047 | Author `.github/workflows/ci-modules.yml` caller matrixing over the registry (bounded ≤20/caller) | WP09 | |
| T048 | Wire per-shard coverage/xunit artefact emission (naming contract; forward-ref WP10) | WP09 | |
| T049 | Mode input threading (pr/full) into the reusable workflow (forward-ref WP11) | WP09 | |
| T050 | Assert shards don't `needs:` each other; each consumes the warmup env once | WP09 | |
| T051 | Red-first: `test_coverage_artefact_contract.py` — `coverage-<tier>-<module>.xml` + `*-reports`, basename-unique, ≤1 `<source>` (RED) | WP10 | [P] |
| T052 | Author `.github/workflows/ci-aggregate.yml`: download `*-reports`, dedup by basename | WP10 | [P] |
| T053 | diff-cover PR gate `--fail-under=90` on changed critical-path lines (NFR-003) | WP10 | [P] |
| T054 | Stale-artefact fallback: partial re-trigger → fall back to most-recent successful run's `*-reports` | WP10 | [P] |
| T055 | Assert dotted `--cov=<module>` + `relative_files=true` preserved (C-005); no single merged `coverage.xml` | WP10 | [P] |
| T056 | Red-first: `test_dual_mode_contract.py` — PR fail-fast vs full `if: always()`, skipped≠green (RED) | WP11 | [P] |
| T057 | Verify mode input threaded through router (WP07) + module-tests (WP09); PR fail-fast, full run-all | WP11 | [P] |
| T058 | `workflow_dispatch` present on every reinstated workflow (SC-010) — asserted in the contract test | WP11 | [P] |
| T059 | Merge-eligibility: short-circuit-skipped successor NOT counted green (required-check set distinguishes) | WP11 | [P] |
| T060 | Dispatched-run evidence doc: a real dispatched run proving host short-circuit/run-all behavior (SC-009) | WP11 | [P] |
| T061 | Red-first: in-repo test — `sonar.yml` is `introduced` in map + fork-safe skip-green + aggregates coverage (RED) | WP12 | [P] |
| T062 | Verify Sonar identity (`Priivacy-ai_spec-kitty`) against the spec-kitty repo BEFORE wiring; record in note | WP12 | [P] |
| T063 | Author `.github/workflows/sonar.yml`: aggregate `*-reports` → SonarSource scan (SHA-pinned), nightly/dispatch | WP12 | [P] |
| T064 | Fork-safe: skip-green without `SONAR_TOKEN`; documented no-rearchitecture path to per-PR | WP12 | [P] |
| T065 | Register `sonar.yml` `introduced` row (lockstep with WP01 schema); reconcile `sonar-project.properties` | WP12 | [P] |
| T066 | Red-first: `test_performance_marker_guard.py` — a `@performance` test with functional assertions is flagged (RED) #3665 | WP13 | [P] |
| T067 | Author `.github/workflows/ci-nightly.yml`: full-mode run-all (`if: always()`) + performance/heavy-e2e cadence #3595 | WP13 | [P] |
| T068 | Interpreter matrix lane above Python 3.12 up to supported ceiling (FR-021, nightly-only) | WP13 | [P] |
| T069 | Assert perf/e2e/interpreter NOT on the per-PR path (SC-011) | WP13 | [P] |
| T070 | Mis-mark guard: functional coverage cannot silently leave the PR path | WP13 | [P] |
| T071 | Register `ci-nightly.yml` `introduced` row (lockstep); closes #3595 / #3665 | WP13 | [P] |
| T072 | Red-first: `test_pycache_sweep.py` — retired-dir `__pycache__` orphans swept, not re-collected (RED) | WP14 | [P] |
| T073 | Author `.github/workflows/packs.yml` built-in lane (regen `--check`, DRG `--check`, manifest, corpus, plugin) | WP14 | [P] |
| T074 | Internal lane (DRG-fragment validity, org-charter activation, packaging-safety negative guard) | WP14 | [P] |
| T075 | `packs/**` trigger independence (Gate-0/Gate-1 lockstep) + corpus exit-5 floor | WP14 | [P] |
| T076 | `__pycache__` sweep step + register `packs.yml` `introduced` row (lockstep) | WP14 | [P] |
| T077 | Red-first: `test_p1_planted_regression.py` — plant dead-code-shard/retired-import → exclusion gate fires (RED) | WP15 | [P] |
| T078 | Planted retired-import negative: `test_no_retired_subsystems` still reds it | WP15 | [P] |
| T079 | Planted dead-symbol negative: `test_no_dead_symbols` still reds it (always-on) | WP15 | [P] |
| T080 | Allowlist-preservation test: enforcement allowlists untouched by P1/P2 demotion | WP15 | [P] |
| T081 | Assert census-dead behavioral test never enters coverage denominator (SC-005/NFR-006) | WP15 | [P] |
| T082 | Red-first: `test_shape_guard_membership.py` — E4 membership machine-checkable, relabel can't move gate status (RED) | WP16 | [P] |
| T083 | Commit `shape_guard_membership.yaml` (test_id → enforcement-allowlist / shape-guard / behavioral) | WP16 | [P] |
| T084 | Demote `test_golden_count_ban.py` cardinality bans off the blocking gate (convert/derive) | WP16 | [P] |
| T085 | Derive twelve-agent parity from source (`test_twelve_agent_parity.py`) + one canonical snapshot + structural invariants | WP16 | [P] |
| T086 | Assert enforcement allowlists NOT in demotion scope (C-007 partition) | WP16 | [P] |
| T087 | Prove a benign symbol-add PR does not red on shape alone (NFR-007); closes #3458 | WP16 | [P] |
| T088 | Red-first: `test_ci_integrity_oracle_nonvacuous.py` — planted-orphan reds oracle + non-vacuity floor (RED) | WP17 | [P] |
| T089 | Rebuild collection-completeness oracle `_ci_integrity_oracle.py` against real on-disk reinstated YAML | WP17 | [P] |
| T090 | Non-vacuity floor: oracle fails if it evaluates nothing (DIR-043) | WP17 | [P] |
| T091 | Fix the zero-producer/inert-slot bare-name false-pass in `_gate_coverage.py` (#2967) | WP17 | [P] |
| T092 | Enumerated must-run gates all wired; two-authority routing internally consistent (SC-004) | WP17 | [P] |
| T093 | Runtime-vs-static boundary: oracle proves wiring only; runtime execution evidenced by each job (SC-004) | WP17 | [P] |
| T094 | Red-first: `test_local_gate_parity.py` — local pre-PR parity selects the SAME gates as CI (one authority) (RED) | WP18 | |
| T095 | Author `scripts/ci/local_gate_parity.py` consuming WP07's `gate_selection.py` (no second parser) | WP18 | |
| T096 | Local command/entrypoint (make target or CLI) invoking the parity check | WP18 | |
| T097 | Assert parity: local selection == CI routing for a sample diff (#2476) | WP18 | |
| T098 | Doc the local pre-PR workflow (quickstart cross-ref) | WP18 | |

## Work Packages

**FOUNDATION cluster — unblocks everything (cluster gate: base-green + deterministic warmup + census oracle live + live-src scrub complete + gov schema + `ci.yml` retired)**

### WP01 — Governance-map `introduced` disposition + dead-`ci.yml` retirement

- **Goal**: Extend the verdict-map schema + enforcer with an `introduced`
  disposition so net-new workflows are representable, and retire the
  archived-inert EXPERIMENTAL `ci.yml` in lockstep with its enforcing fence.
- **Requirements**: FR-012, FR-017, C-001, C-010. **Contract**: `contracts/governance-map-schema.md`.
- **Independent test**: `test_release_ci_ownership.py` asserts the four
  disposition sets (incl. `introduced`) and runs on a workflow-changing PR;
  RED on base, GREEN after.
- **Subtasks**: T001 (red-first), T002 (tidy-first), T003, T004, T005, T006
- **Dependencies**: none
- **Prompt**: `tasks/WP01-governance-map-introduced.md` (~360 lines)

### WP02 — Dead-code census machine oracle (bidirectional guardrail)

- **Goal**: Stand up the dead-code census as an in-repo **machine oracle** with a
  bidirectional guardrail (false-negative independent-evidence + false-positive
  known-live-never-dead), non-vacuous.
- **Requirements**: FR-013 (census), C-006, NFR-006. **Contract**: `contracts/p1-census-oracle.md`.
- **Independent test**: self-mutation negative — a planted dead-code shard /
  retired-import is flagged and the exclusion fires; a planted known-live
  importer-0 surface is refused as dead.
- **Subtasks**: T007 (red-first), T008, T009, T010, T011, T012
- **Dependencies**: none
- **Prompt**: `tasks/WP02-census-oracle.md` (~420 lines)

### WP03 — Base-red triage #3284 (census-authorized, per-red independent evidence)

- **Goal**: Triage the 23 untracked failures + 2 errors (#3284) so the base is
  green before any shard selection is frozen — each red **either** dropped
  (census-authorized dead-code) **or** fixed (live regression), none left red.
- **Requirements**: FR-002, SC-008. **Closes**: #3284.
- **Independent test**: the mission base run reports **0** untracked failures;
  each drop carries individually-reviewable independent evidence.
- **Subtasks**: T013 (red-first), T014, T015, T016, T017
- **Dependencies**: WP02
- **Prompt**: `tasks/WP03-base-red-triage-3284.md` (~380 lines)

### WP04 — Warmup / bootstrap #3283 (pinned-PR / latest-nightly cache composite)

- **Goal**: A shared warmup composite that pre-builds the editable env once as a
  cache-keyed reusable artefact, eliminating the #3283 venv-lock cascade.
- **Requirements**: FR-003. **Closes**: #3283.
- **Independent test**: `test_warmup_action.py` pins the composite contract; a
  clean checkout provisions the env deterministically and downstream reuse skips
  the install.
- **Subtasks**: T018 (red-first), T019, T020, T021, T022
- **Dependencies**: none
- **Prompt**: `tasks/WP04-warmup-bootstrap-3283.md` (~340 lines)

### WP05 — Retirement scrub — re-derive dorny groups + `--cov` against live `src/**`

- **Goal**: Re-derive the dorny filter groups and `--cov` targets against live
  `src/**` so no CI job selects a test over dead/retired code; every exclusion is
  census-authorized (no bare labels).
- **Requirements**: FR-013 (scrub). Uses the WP02 census.
- **Independent test**: `test_retirement_scrub.py` asserts no group/`--cov`
  target maps to a retired subsystem or never-restore surface, cross-checked
  against the census.
- **Subtasks**: T023 (red-first), T024, T025, T026, T027
- **Dependencies**: WP02
- **Prompt**: `tasks/WP05-retirement-scrub.md` (~340 lines)

### WP06 — Fix-before-wiring + early strict-xfail/env-leak hygiene

- **Goal**: Re-validate every active `xfail(strict=True)` landmine and fix the
  confirmed env-leak tests **before** they can enter a gated shard, so CI
  greens/reds reflect real state.
- **Requirements**: FR-015.
- **Independent test**: each named landmine is resolved (fixed or converted) and
  the two env-leakers pass under any shard order.
- **Subtasks**: T028 (red-first), T029, T030, T031, T032, T033
- **Dependencies**: none
- **Prompt**: `tasks/WP06-fix-before-wiring.md` (~360 lines)

**TOPOLOGY cluster — parallelizable after the FOUNDATION gate (cluster gate: full pipeline green on a real PR + wallclock targets + artefact-sharing + dual-mode verified). Every WP below depends on **all** FOUNDATION WPs (WP01–WP06).**

### WP07 — Path router + two-authority + single gate-selection authority

- **Goal**: The dorny two-authority router (fail-closed unmatched→run-all,
  shift-left ladder, fast always-on gates split from the code-scoped heavy arch
  battery) + the **single importable gate-selection authority** parsing the two
  authorities (one source, reused by L3/WP18).
- **Requirements**: FR-004, FR-005, FR-008, FR-016 (authority), NFR-002.
  **Contract**: `contracts/router-two-authority.md`.
- **Independent test**: rewritten `test_ci_quality_path_filters.py` +
  `test_gate_selection_authority.py`; a docs-only PR runs 0 code shards.
- **Subtasks**: T034 (red-first), T035 (tidy-first), T036, T037, T038, T039
- **Dependencies**: WP01, WP02, WP03, WP04, WP05, WP06
- **Prompt**: `tasks/WP07-path-router-two-authority.md` (~440 lines)

### WP08 — Module registry + `--durations` shard-freeze

- **Goal**: Record a `--durations` run on the **scrubbed** live basis and freeze
  the committed module registry (duration-balanced, skew ≤20%), realized as a
  matrix data source (≤20 reusable-workflows/caller ceiling).
- **Requirements**: FR-006, NFR-001, NFR-005.
- **Independent test**: `test_module_shard_registry.py` — registry completeness
  + skew ≤20% on measured durations, post-scrub basis.
- **Subtasks**: T040 (red-first), T041, T042, T043, T044
- **Dependencies**: WP01, WP02, WP03, WP04, WP05, WP06, WP07
- **Prompt**: `tasks/WP08-module-registry-shard-freeze.md` (~360 lines)

### WP09 — Matrix reusable module-tests workflow(s)

- **Goal**: The reusable `workflow_call` shard + its caller matrixing over the
  committed registry — every per-module group contributes to one full run;
  gives the suite a public CI home (FR-001).
- **Requirements**: FR-001, FR-006, FR-008.
- **Independent test**: `test_module_tests_matrix.py` — the matrix realizes
  every registry row; a `src/**` PR executes the module shards.
- **Subtasks**: T045 (red-first), T046, T047, T048, T049, T050
- **Dependencies**: WP01, WP02, WP03, WP04, WP05, WP06, WP08
- **Prompt**: `tasks/WP09-matrix-module-tests.md` (~380 lines)

### WP10 — Artefact contract + aggregation + diff-cover gate + stale fallback

- **Goal**: The coverage/xunit naming contract, the aggregation workflow, the
  diff-cover PR gate (≥90% changed-line), and the stale-artefact fallback.
- **Requirements**: FR-007, FR-009, C-005, NFR-003. **Contract**: `contracts/artefact-naming.md`.
- **Independent test**: `test_coverage_artefact_contract.py` — naming,
  basename-uniqueness, ≤1 `<source>`, dotted `--cov`.
- **Subtasks**: T051 (red-first), T052, T053, T054, T055
- **Dependencies**: WP01, WP02, WP03, WP04, WP05, WP06, WP09
- **Prompt**: `tasks/WP10-artefact-aggregation-diffcover.md` (~360 lines)

### WP11 — Dual-mode + manual dispatch + merge-eligibility (skipped≠green)

- **Goal**: PR fail-fast vs full run-all (`if: always()`), `workflow_dispatch`
  everywhere, and a required-check set where a short-circuit-skipped successor is
  NOT merge-eligible-green — evidenced by a real dispatched run.
- **Requirements**: FR-018, FR-019, NFR-008, SC-009, SC-010.
- **Independent test**: `test_dual_mode_contract.py` + the dispatched-run
  evidence doc.
- **Subtasks**: T056 (red-first), T057, T058, T059, T060
- **Dependencies**: WP01, WP02, WP03, WP04, WP05, WP06, WP07, WP09
- **Prompt**: `tasks/WP11-dual-mode-dispatch-eligibility.md` (~360 lines)

### WP12 — Sonar workflow (net-new, `introduced`)

- **Goal**: A net-new `sonar.yml` aggregating coverage and scanning from the
  spec-kitty repo (nightly/dispatch), fork-safe skip-green, identity verified
  before wiring.
- **Requirements**: FR-010, C-008.
- **Independent test**: an in-repo test asserts `sonar.yml` is `introduced` +
  fork-safe skip + coverage aggregation.
- **Subtasks**: T061 (red-first), T062, T063, T064, T065
- **Dependencies**: WP01, WP02, WP03, WP04, WP05, WP06, WP10
- **Prompt**: `tasks/WP12-sonar-workflow.md` (~340 lines)

### WP13 — Nightly full-mode: expensive cadence + interpreter lane + mis-mark guard

- **Goal**: The full-mode nightly workflow (run-all, performance/heavy-e2e
  cadence, interpreter matrix above 3.12) + a guard flagging mis-marked
  `@performance` functional tests.
- **Requirements**: FR-020, FR-021, SC-011. **Closes**: #3595, #3665.
- **Independent test**: `test_performance_marker_guard.py`; a per-PR run
  executes 0 performance/e2e jobs.
- **Subtasks**: T066 (red-first), T067, T068, T069, T070, T071
- **Dependencies**: WP01, WP02, WP03, WP04, WP05, WP06, WP09
- **Prompt**: `tasks/WP13-nightly-fullmode-interpreter.md` (~380 lines)

### WP14 — Packs workflow (built-in + internal lanes) + retired-dir `__pycache__` sweep

- **Goal**: A dedicated packs workflow (built-in + internal lanes, `packs/**`
  trigger independence, corpus exit-5 floor) + the retired-dir `__pycache__`
  sweep edge case.
- **Requirements**: FR-011.
- **Independent test**: `test_pycache_sweep.py`; a packs-only PR runs the packs
  workflow and no code shards.
- **Subtasks**: T072 (red-first), T073, T074, T075, T076
- **Dependencies**: WP01, WP02, WP03, WP04, WP05, WP06, WP07
- **Prompt**: `tasks/WP14-packs-workflow.md` (~360 lines)

**LEAN-SUITE cluster — hygiene on the live pipeline (cluster gate: P1 negative tests fire + P2 demotion + non-vacuous integrity oracle)**

### WP15 — P1 machine proofs (planted dead-code/retired-import + allowlist preservation)

- **Goal**: The planted-regression negatives proving the exclusion gate actually
  fires (not a prose promise) + the enforcement-allowlist-preservation test.
- **Requirements**: FR-013, C-006, SC-005.
- **Independent test**: `test_p1_planted_regression.py` reds when the exclusion
  gate is removed; the enforcement allowlists still catch a planted regression.
- **Subtasks**: T077 (red-first), T078, T079, T080, T081
- **Dependencies**: WP02, WP05, WP09
- **Prompt**: `tasks/WP15-p1-machine-proofs.md` (~340 lines)

### WP16 — P2 shape-guard demotion + committed membership

- **Goal**: Demote the low-ROI golden-count/compat/twelve-agent shape guards off
  the blocking gate (derive-from-source) + commit the machine-checkable
  allowlist-vs-shape-guard membership list.
- **Requirements**: FR-014, C-007, NFR-007. **Closes**: #3458.
- **Independent test**: `test_shape_guard_membership.py`; a benign symbol-add PR
  no longer reds on shape alone.
- **Subtasks**: T082 (red-first), T083, T084, T085, T086, T087
- **Dependencies**: WP09
- **Prompt**: `tasks/WP16-p2-shape-guard-demotion.md` (~360 lines)

### WP17 — CI-integrity oracle non-vacuity + planted-orphan

- **Goal**: Rebuild the collection-completeness oracle against real on-disk YAML
  with a non-vacuity floor + planted-orphan negative; fix the zero-producer
  bare-name false-pass (#2967).
- **Requirements**: FR-016, SC-004. **Closes**: #2967.
- **Independent test**: `test_ci_integrity_oracle_nonvacuous.py` — a
  planted-orphan test reds the oracle; the oracle fails when it evaluates
  nothing.
- **Subtasks**: T088 (red-first), T089, T090, T091, T092, T093
- **Dependencies**: WP07, WP09
- **Prompt**: `tasks/WP17-integrity-oracle-nonvacuous.md` (~380 lines)

### WP18 — Gate-selection authority local pre-PR parity consumer

- **Goal**: A local pre-PR parity command consuming WP07's single gate-selection
  authority (no second parser), proving local selection == CI routing.
- **Requirements**: FR-016. **Closes**: #2476.
- **Independent test**: `test_local_gate_parity.py` — local selection matches CI
  routing for a sample diff.
- **Subtasks**: T094 (red-first), T095, T096, T097, T098
- **Dependencies**: WP07, WP17
- **Prompt**: `tasks/WP18-local-gate-parity.md` (~320 lines)
