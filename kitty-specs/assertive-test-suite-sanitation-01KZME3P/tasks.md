# Work Packages: Assertive Test Suite Sanitation

**Mission**: `assertive-test-suite-sanitation-01KZME3P`  
**Planning/merge branch**: `pr/assertive-test-suite-sanitation`  
**Protected PR base**: `main`  
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

## Execution Shape

WP01 establishes reproducible census/evidence. WP02 repairs #3283 and the #2645 whole-tree collection scanner. WP03 and WP06 depend on the healthy harness. Duplicate families split across WP04/WP11/WP12; coherent structural authority families split across WP05/WP09/WP10/WP13/WP14/WP15. WP07 integrates all deletion handoffs and the architectural shard map, then folds the approved topology into proportional CI. WP08 generates aggregate proof and closure artifacts. Each adjudication WP owns one ledger shard; only WP08 writes the aggregate.

WP01 is also a discovery gate. Every mechanically discovered inert, duplicate, or structural candidate must map to an exact downstream owner. If the generated candidate manifest contains an unowned path or group, stop before dispatching its adjudication class, amend `owned_files`/dependencies/tasks, rerun `finalize-tasks`, and record the replan. “Out of scope” is not a terminal sanitation verdict.

Before claiming a WP, verify each frontmatter `tracker_refs` issue is assigned to `robertDouglass` and contains the mission reference; tracker drift blocks claim under DIR-012/DIR-013.

After analyze passes and planning artifacts are committed, push `pr/assertive-test-suite-sanitation` and open a draft PR targeting protected `main` before implementation claims. This makes real Linux/Windows PR workflows reachable without adding a permanent dispatch. WP02 records local macOS plus exact platform selectors; WP08 requires the integrated commit's actual PR job URLs/results before closure.

## Subtask Index

| Subtask | Description | WP | Parallel |
|---------|-------------|----|----------|
| T001 | Implement mission-local AST/ignore discovery and pytest collection-hook snapshot | WP01 | No |
| T002 | Capture immutable base census and reconcile discovered/collected/zero-node units | WP01 | No |
| T003 | Freeze workload DAG, route universe, environment identity, and raw #3283 evidence | WP01 | Yes |
| T004 | Validate deep-shard schema, grouping divergence, class profiles, and temporary rules | WP01 | No |
| T005 | Prove auditor determinism and fail-closed behavior with temporary fixtures | WP01 | No |
| T006 | Commit compact raw artifacts/hashes and foundation evidence summary | WP01 | No |
| T007 | Add red concurrency tests for slow live builder and two fresh starters | WP02 | No |
| T008 | Add dead-owner, crash-mid-build, invalid-final, and PID-reuse tests | WP02 | Yes |
| T009 | Implement lease/heartbeat/temp-build/validation/atomic-publish state machine | WP02 | No |
| T010 | Prove macOS/Linux/Windows publication semantics and no half-built consumer | WP02 | No |
| T011 | Persist exact replay patch and run identical base/HEAD harness comparison | WP02 | No |
| T012 | Record three consecutive fresh-start results and WP02 disposition shard | WP02 | No |
| T050 | Cache/share the whole-tree wall-clock assertion scan and prove proportional collection | WP02 | No |
| T013 | Census every unconditional skip, permanent xfail, quarantine, placeholder, and flaky marker | WP03 | No |
| T014 | Delete ten #2309 daemon-reaper skipped bodies and two #2316 upgrade skipped bodies | WP03 | Yes |
| T015 | Delete live-server placeholder and obsolete missing-ref/advisory skipped tests | WP03 | Yes |
| T016 | Adjudicate #2342 quarantine and root-cause/delete lingering flaky marker | WP03 | Yes |
| T017 | Preserve one live blocking #2782 red reproduction with no self-skip | WP03 | No |
| T018 | Complete class-specific inert-state shard with terminal verdicts | WP03 | No |
| T019 | Run focused and repeated state/marker validation with zero new masking | WP03 | No |
| T020 | Prove runtime/kernel home-path duplication and preserve unique Windows/import contracts | WP04 | Yes |
| T021 | Prove legacy/unit git-ops duplication and retain canonical live seam | WP04 | Yes |
| T022 | Consolidate duplicate dashboard glossary and lint handler suites | WP04 | Yes |
| T023 | Consolidate duplicate lane/template guards while preserving one negative invariant | WP04 | Yes |
| T024 | Run survivor causal/fault probes and focused mutation comparisons | WP04 | No |
| T025 | Record removed members, survivors, costs, and unique boundaries in WP04 shard | WP04 | No |
| T026 | Adjudicate never-fail retired-contract advisory and historical report validators | WP05 | Yes |
| T027 | Remove name/token/count/prose/self-presence scaffolds with no current authority | WP05 | Yes |
| T028 | Re-evaluate auth transport and batch-drain positive-shape guards against current ADRs | WP05 | Yes |
| T029 | Preserve/rehome only plausible-authority-violating negative invariants | WP05 | No |
| T030 | Emit cohort-A structural handoff; defer central shard-map integration to WP07 | WP05 | No |
| T031 | Record structural causal probes, dead-symbol caller proof, and WP05 verdicts | WP05 | No |
| T032 | Reproduce and classify every #3284 base failure/error under repaired harness | WP06 | No |
| T033 | Adjudicate doctrine reachability/count pins and charter compact-size threshold | WP06 | Yes |
| T034 | Adjudicate ANSI console and mission-template-resolution assertions | WP06 | Yes |
| T035 | Adjudicate timing, daemon, safe-commit, sync teardown, and E2E portability failures | WP06 | Yes |
| T036 | Run fixed flake matrix for nondeterministic candidates; no retry-to-green | WP06 | No |
| T037 | Record owned known-red deltas and exact unresolved handoffs for downstream terminalization | WP06 | No |
| T038 | Complete WP06 shard and focused regression validation | WP06 | No |
| T039 | Replace whole-tree regression/quarantine marker discovery with explicit owned selectors | WP07 | No |
| T040 | Model one owner plus documented coverage/platform/hard-gate overlaps | WP07 | No |
| T041 | Update architectural workflow contracts without weakening red-main authority | WP07 | No |
| T042 | Execute route-manifest selection and three-run fixed-route timing comparison | WP07 | No |
| T043 | Record summed compute, critical path, mapping, and WP07 disposition evidence | WP07 | No |
| T051 | Machine-screen structural cohort B and bind every file to current authority | WP09 | No |
| T052 | Delete spent cohort-B shape/prose/count/history guards | WP09 | Yes |
| T053 | Fault-probe retained cohort-B negative invariants and anti-vacuity | WP09 | No |
| T054 | Run focused cohort-B collection/contract validation and record terminal verdicts | WP09 | No |
| T055 | Emit cohort-B shard-map handoff and raw evidence | WP09 | No |
| T056 | Machine-screen structural cohort C and bind every file to current authority | WP10 | No |
| T057 | Delete spent cohort-C shape/prose/count/history guards | WP10 | Yes |
| T058 | Fault-probe retained cohort-C negative invariants and anti-vacuity | WP10 | No |
| T059 | Run focused cohort-C collection/contract validation and record terminal verdicts | WP10 | No |
| T060 | Emit cohort-C shard-map handoff and raw evidence | WP10 | No |
| T061 | Census doctrine/resolver structural family | WP13 | No |
| T062 | Delete spent doctrine/resolver shape and prose guards | WP13 | Yes |
| T063 | Prove every doctrine/resolver survivor or valid family | WP13 | No |
| T064 | Validate focused family and record terminal ledger | WP13 | No |
| T065 | Emit doctrine/resolver map handoff | WP13 | No |
| T066 | Census runtime/coordination structural family | WP14 | No |
| T067 | Delete spent runtime/coordination structural guards | WP14 | Yes |
| T068 | Prove every runtime/coordination survivor or valid family | WP14 | No |
| T069 | Validate focused family and record terminal ledger | WP14 | No |
| T070 | Emit runtime/coordination map handoff | WP14 | No |
| T071 | Census packaging/CLI/artifact structural family | WP15 | No |
| T072 | Delete spent packaging/CLI shape guards | WP15 | Yes |
| T073 | Prove every packaging/CLI survivor or valid family | WP15 | No |
| T074 | Validate focused family and record terminal ledger | WP15 | No |
| T075 | Emit packaging/CLI map handoff | WP15 | No |
| T076 | Reconcile every Specify CLI duplicate member/group | WP11 | No |
| T077 | Consolidate CLI/compatibility duplicate families | WP11 | Yes |
| T078 | Consolidate dashboard/lane duplicate families | WP11 | Yes |
| T079 | Run causal/mutation and focused validation | WP11 | No |
| T080 | Record WP11 ledger and deletion handoff | WP11 | No |
| T081 | Reconcile every sync/status/upgrade duplicate member/group | WP12 | No |
| T082 | Consolidate status/sync duplicate families | WP12 | Yes |
| T083 | Consolidate supported upgrade duplicate families | WP12 | Yes |
| T084 | Run causal/platform/version validation | WP12 | No |
| T085 | Record WP12 ledger and deletion handoff | WP12 | No |
| T044 | Generate canonical aggregate ledger and HEAD census from WP shards | WP08 | No |
| T045 | Generate before/after report, live known-red delta, causal/mutation matrix, and issue matrix | WP08 | No |
| T046 | Run full parallel suite, orphan sweep, ruff, mypy, and route/platform gates | WP08 | No |
| T047 | Run contract, architectural, and sibling cross-repository E2E hard gates | WP08 | No |
| T048 | Update durable test docs/changelog and generated workflow evidence | WP08 | No |
| T049 | Validate all success criteria, temporary states, tracker verdicts, and PR readiness | WP08 | No |

---

## WP01: Reproducible Census and Evidence Foundation (P1)

**Prompt**: `tasks/WP01-census-evidence-foundation.md`  
**Independent test**: two clean snapshots of the same tree are byte-identical after timestamp normalization; injected zero-node, ignored, errored, and divergent-parameter fixtures are all reconciled or fail closed.

### Included Subtasks

- [ ] T001 Implement mission-local AST/ignore discovery and pytest collection-hook snapshot (WP01)
- [ ] T002 Capture immutable base census and reconcile discovered/collected/zero-node units (WP01)
- [ ] T003 Freeze workload DAG, route universe, environment identity, and raw #3283 evidence (WP01)
- [ ] T004 Validate deep-shard schema, grouping divergence, class profiles, and temporary rules (WP01)
- [ ] T005 Prove auditor determinism and fail-closed behavior with temporary fixtures (WP01)
- [ ] T006 Commit compact raw artifacts/hashes and foundation evidence summary (WP01)

**Dependencies**: none.  
**Parallel opportunities**: T003 may proceed while census hooks are completed.  
**Risks**: collection recursion and giant evidence churn; use an in-process plugin, stable ordering, compact records, and no hand-authored unchanged-KEEP narratives.  
**Estimated prompt**: ~300 lines.

## WP02: Shared Test-Venv Bootstrap Reliability (P1)

**Prompt**: `tasks/WP02-test-venv-bootstrap.md`  
**Independent test**: slow live, dead, crashed, invalid, and simultaneous builders always publish one validated environment; no waiter observes a half-build; three fresh starts avoid #3283.

### Included Subtasks

- [ ] T007 Add red concurrency tests for slow live builder and two fresh starters (WP02)
- [ ] T008 Add dead-owner, crash-mid-build, invalid-final, and PID-reuse tests (WP02)
- [ ] T009 Implement lease/heartbeat/temp-build/validation/atomic-publish state machine (WP02)
- [ ] T010 Prove macOS/Linux/Windows publication semantics and no half-built consumer (WP02)
- [ ] T011 Persist exact replay patch and run identical base/HEAD harness comparison (WP02)
- [ ] T012 Record three consecutive fresh-start results and WP02 disposition shard (WP02)
- [ ] T050 Cache/share the whole-tree wall-clock assertion scan and prove proportional collection (WP02)

**Dependencies**: WP01.  
**Risks**: deadlock, stale-owner theft, unsafe directory replacement, divergent replay patch.  
**Estimated prompt**: ~330 lines.

## WP03: Inert, Skipped, Quarantined, and Flaky States (P1)

**Prompt**: `tasks/WP03-inert-test-states.md`  
**Independent test**: repaired-base and HEAD matrices cover every inert state; permanent non-executing `KEEP` count is zero; #2782 remains exactly one live blocking red; no new masking marker exists.

### Included Subtasks

- [ ] T013 Census every unconditional skip, permanent xfail, quarantine, placeholder, and flaky marker (WP03)
- [ ] T014 Delete ten #2309 daemon-reaper skipped bodies and two #2316 upgrade skipped bodies (WP03)
- [ ] T015 Delete live-server placeholder and obsolete missing-ref/advisory skipped tests (WP03)
- [ ] T016 Adjudicate #2342 quarantine and root-cause/delete lingering flaky marker (WP03)
- [ ] T017 Preserve one live blocking #2782 red reproduction with no self-skip (WP03)
- [ ] T018 Complete class-specific inert-state shard with terminal verdicts (WP03)
- [ ] T019 Run focused and repeated state/marker validation with zero new masking (WP03)

**Dependencies**: WP01, WP02.  
**Parallel opportunities**: T014–T016 touch separate files.  
**Risks**: deleting the only P0 repro or treating conditional platform skips as permanent.  
**Estimated prompt**: ~350 lines.

## WP04: Duplicate and Compatibility-Shim Consolidation (P1)

**Prompt**: `tasks/WP04-duplicate-consolidation.md`  
**Independent test**: every mechanically discovered exact group and every promoted semantic group has a terminal verdict; deleted members contribute no unique non-equivalent mutant, platform boundary, public import contract, or live path beyond the named survivor.

### Included Subtasks

- [ ] T020 Prove runtime/kernel home-path duplication and preserve unique Windows/import contracts (WP04)
- [ ] T021 Prove legacy/unit git-ops duplication and retain canonical live seam (WP04)
- [ ] T022 Consolidate duplicate dashboard glossary and lint handler suites (WP04)
- [ ] T023 Consolidate duplicate lane/template guards while preserving one negative invariant (WP04)
- [ ] T024 Run survivor causal/fault probes and focused mutation comparisons (WP04)
- [ ] T025 Record removed members, survivors, costs, and unique boundaries in WP04 shard (WP04)

**Dependencies**: WP01.  
**Parallel opportunities**: T020–T023 are independent surfaces.  
**Risks**: syntactic duplicates can guard distinct compatibility imports.  
**Estimated prompt**: ~330 lines.

## WP05: Structural and Spent-Scaffold Retirement (P1)

**Prompt**: `tasks/WP05-structural-scaffold-retirement.md`  
**Independent test**: every surviving structural guard scans a live nonzero corpus and fails under a plausible current-authority violation; removed guards pin only stale shape/prose/history or never fail.

### Included Subtasks

- [ ] T026 Adjudicate never-fail retired-contract advisory and historical report validators (WP05)
- [ ] T027 Remove name/token/count/prose/self-presence scaffolds with no current authority (WP05)
- [ ] T028 Re-evaluate auth transport and batch-drain positive-shape guards against current ADRs (WP05)
- [ ] T029 Preserve/rehome only plausible-authority-violating negative invariants (WP05)
- [ ] T030 Emit cohort-A structural handoff; defer central shard-map integration to WP07 (WP05)
- [ ] T031 Record structural causal probes, dead-symbol caller proof, and WP05 verdicts (WP05)

**Dependencies**: WP01.  
**Parallel opportunities**: T026–T028 begin independently; T029–T030 integrate.  
**Risks**: useful negative invariant embedded beside obsolete positive shape.  
**Estimated prompt**: ~350 lines.

## WP06: Pre-existing Red and Error Adjudication (P1)

**Prompt**: `tasks/WP06-baseline-red-adjudication.md`  
**Independent test**: all WP06-owned #3284 nodes receive reproducible terminal classifications; exact downstream-owned handoffs are machine-readable; only accepted P0 reproductions may remain red; base-green/HEAD-red count is zero.

### Included Subtasks

- [ ] T032 Reproduce and classify every #3284 base failure/error under repaired harness (WP06)
- [ ] T033 Adjudicate doctrine reachability/count pins and charter compact-size threshold (WP06)
- [ ] T034 Adjudicate ANSI console and mission-template-resolution assertions (WP06)
- [ ] T035 Adjudicate timing, daemon, safe-commit, sync teardown, and E2E portability failures (WP06)
- [ ] T036 Run fixed flake matrix for nondeterministic candidates; no retry-to-green (WP06)
- [ ] T037 Record owned known-red deltas and exact unresolved handoffs for downstream terminalization (WP06)
- [ ] T038 Complete WP06 shard and focused regression validation (WP06)

**Dependencies**: WP01, WP02.  
**Parallel opportunities**: T033–T035 are separate clusters.  
**Risks**: confusing shared-fixture contamination with obsolete tests; product behavior fixes are out of scope.  
**Estimated prompt**: ~380 lines.

## WP07: Proportional CI Route Ownership (P2)

**Prompt**: `tasks/WP07-proportional-ci-routing.md`  
**Independent test**: changed narrow classes have exactly one owner route, documented secondary overlap, stable selection, and three-run cost comparison without whole-tree marker discovery.

### Included Subtasks

- [ ] T039 Replace whole-tree regression/quarantine marker discovery with explicit owned selectors (WP07)
- [ ] T040 Model one owner plus documented coverage/platform/hard-gate overlaps (WP07)
- [ ] T041 Update architectural workflow contracts without weakening red-main authority (WP07)
- [ ] T042 Execute route-manifest selection and three-run fixed-route timing comparison (WP07)
- [ ] T043 Record summed compute, critical path, mapping, and WP07 disposition evidence (WP07)

**Dependencies**: WP03, WP04, WP05, WP06, WP09, WP10, WP11, WP12, WP13, WP14, WP15.
**Risks**: stranded tests, manufactured savings, or accidental quality-gate policy change.  
**Estimated prompt**: ~300 lines.

## WP09: CI Gate and Route Structural Sanitation (P1)

**Prompt**: `tasks/WP09-structural-cohort-b.md`  
**Independent test**: every assigned cohort-B file has a terminal structural verdict; every survivor reaches and fails its intended oracle under a plausible current-authority violation.

### Included Subtasks

- [ ] T051 Machine-screen structural cohort B and bind every file to current authority (WP09)
- [ ] T052 Delete spent cohort-B shape/prose/count/history guards (WP09)
- [ ] T053 Fault-probe retained cohort-B negative invariants and anti-vacuity (WP09)
- [ ] T054 Run focused cohort-B collection/contract validation and record terminal verdicts (WP09)
- [ ] T055 Emit cohort-B shard-map handoff and raw evidence (WP09)

**Dependencies**: WP01.  
**Risks**: a structural file can mix a useful invariant with spent scaffolding; split or rehome the useful oracle before deletion.  
**Estimated prompt**: ~330 lines.

## WP10: Boundary and Safety Structural Sanitation (P1)

**Prompt**: `tasks/WP10-structural-cohort-c.md`  
**Independent test**: every assigned cohort-C file has a terminal structural verdict; every survivor reaches and fails its intended oracle under a plausible current-authority violation.

### Included Subtasks

- [ ] T056 Machine-screen structural cohort C and bind every file to current authority (WP10)
- [ ] T057 Delete spent cohort-C shape/prose/count/history guards (WP10)
- [ ] T058 Fault-probe retained cohort-C negative invariants and anti-vacuity (WP10)
- [ ] T059 Run focused cohort-C collection/contract validation and record terminal verdicts (WP10)
- [ ] T060 Emit cohort-C shard-map handoff and raw evidence (WP10)

**Dependencies**: WP01.  
**Risks**: CI/governance files have stronger authorities; hand off route-owned paths rather than weakening or duplicating ownership.  
**Estimated prompt**: ~330 lines.

## WP11: Specify CLI Duplicate Consolidation (P1)

**Prompt**: `tasks/WP11-specify-duplicates.md`
**Independent test**: every owned strict/normalized duplicate member is terminally mapped; deletions lose no unique CLI/compatibility/live-route boundary.

### Included Subtasks

- [ ] T076 Reconcile every Specify CLI duplicate member/group (WP11)
- [ ] T077 Consolidate CLI/compatibility duplicate families (WP11)
- [ ] T078 Consolidate dashboard/lane duplicate families (WP11)
- [ ] T079 Run causal/mutation and focused validation (WP11)
- [ ] T080 Record WP11 ledger and deletion handoff (WP11)

**Dependencies**: WP01.
**Risks**: same bodies can traverse distinct compatibility or CLI seams.
**Estimated prompt**: ~220 lines.

## WP12: Sync, Status, and Upgrade Duplicate Consolidation (P1)

**Prompt**: `tasks/WP12-sync-upgrade-duplicates.md`
**Independent test**: every owned duplicate family is terminally mapped with unique persistence/network/version/platform boundaries preserved.

### Included Subtasks

- [ ] T081 Reconcile every sync/status/upgrade duplicate member/group (WP12)
- [ ] T082 Consolidate status/sync duplicate families (WP12)
- [ ] T083 Consolidate supported upgrade duplicate families (WP12)
- [ ] T084 Run causal/platform/version validation (WP12)
- [ ] T085 Record WP12 ledger and deletion handoff (WP12)

**Dependencies**: WP01.
**Risks**: same bodies across migration versions or teardown seams can be distinct.
**Estimated prompt**: ~190 lines.

## WP13: Doctrine and Resolver Structural Sanitation (P1)

**Prompt**: `tasks/WP13-doctrine-structural.md`
**Independent test**: every assigned doctrine/resolver guard is terminal and every survivor/family fails its intended oracle under a current authority violation.

### Included Subtasks

- [ ] T061 Census doctrine/resolver structural family (WP13)
- [ ] T062 Delete spent doctrine/resolver shape and prose guards (WP13)
- [ ] T063 Prove every doctrine/resolver survivor or valid family (WP13)
- [ ] T064 Validate focused family and record terminal ledger (WP13)
- [ ] T065 Emit doctrine/resolver map handoff (WP13)

**Dependencies**: WP01.
**Risks**: similar resolver scanners can enforce different authority doors.
**Estimated prompt**: ~200 lines.

## WP14: Runtime Coordination Structural Sanitation (P1)

**Prompt**: `tasks/WP14-runtime-structural.md`
**Independent test**: every runtime/status/mission/worktree guard is terminal and every survivor/family has two-sided operational fault bite.

### Included Subtasks

- [ ] T066 Census runtime/coordination structural family (WP14)
- [ ] T067 Delete spent runtime/coordination structural guards (WP14)
- [ ] T068 Prove every runtime/coordination survivor or valid family (WP14)
- [ ] T069 Validate focused family and record terminal ledger (WP14)
- [ ] T070 Emit runtime/coordination map handoff (WP14)

**Dependencies**: WP01.
**Risks**: historical mission/status wording can resemble live operational invariants.
**Estimated prompt**: ~180 lines.

## WP15: Packaging and CLI Structural Sanitation (P1)

**Prompt**: `tasks/WP15-packaging-structural.md`
**Independent test**: all packaging/CLI/artifact scanners, including nested enrolment inventory, are terminal and every survivor/family has two-sided consumed-contract bite.

### Included Subtasks

- [ ] T071 Census packaging/CLI/artifact structural family (WP15)
- [ ] T072 Delete spent packaging/CLI shape guards (WP15)
- [ ] T073 Prove every packaging/CLI survivor or valid family (WP15)
- [ ] T074 Validate focused family and record terminal ledger (WP15)
- [ ] T075 Emit packaging/CLI map handoff (WP15)

**Dependencies**: WP01.
**Risks**: packaging text/shape may or may not be a consumed compatibility contract.
**Estimated prompt**: ~170 lines.

## WP08: Aggregate Evidence and Mission Closure (P1)

**Prompt**: `tasks/WP08-aggregate-closure.md`  
**Independent test**: generated aggregate validates; hard gates pass; known-red/issue matrices are exact; final report can be regenerated from shards/raw artifacts; all success criteria have evidence.

### Included Subtasks

- [ ] T044 Generate canonical aggregate ledger and HEAD census from WP shards (WP08)
- [ ] T045 Generate before/after report, live known-red delta, causal/mutation matrix, and issue matrix (WP08)
- [ ] T046 Run full parallel suite, orphan sweep, ruff, mypy, and route/platform gates (WP08)
- [ ] T047 Run contract, architectural, and sibling cross-repository E2E hard gates (WP08)
- [ ] T048 Update durable test docs/changelog and generated workflow evidence (WP08)
- [ ] T049 Validate all success criteria, temporary states, tracker verdicts, and PR readiness (WP08)

**Dependencies**: WP02, WP03, WP04, WP05, WP06, WP07, WP09, WP10, WP11, WP12, WP13, WP14, WP15.
**Risks**: aggregate prose drifting from canonical evidence; report generation and checksums prevent dual authority.  
**Estimated prompt**: ~330 lines.
