# Mission Specification: Assertive Test Suite Sanitation

**Mission Branch**: `pr/assertive-test-suite-sanitation`  
**Created**: 2026-08-10  
**Status**: Approved for planning  
**Input**: Maintainer directive to remove slow, permanently failing, flaky, non-structural, and other tests that do not realistically stand a chance of catching a bug.

## Intent Summary

Spec Kitty maintainers need a smaller, faster, and trustworthy test suite. A test earns permanent residence only when it constrains a live observable contract or a durable architectural invariant and a relevant controlled fault makes it fail for the intended reason. Permanently skipped tests, placeholders, advisory checks that cannot fail, dominated duplicates, obsolete compatibility checks, synthetic self-assertions, spent mission scaffolds, and positive code-shape or prose pinning are retired aggressively.

The primary actor is a maintainer changing production behavior. The successful outcome is fast, credible feedback that fails on a real regression and stays green through behavior-preserving refactors. The main exception is a current issue-pinned product defect: preserve one honest, blocking, live-entry-point reproduction when it truly exercises the defect; delete skipped or duplicate copies. The invariant is that no deletion may remove the only causal guard for a live contract.

This is a `software-dev` mission. It is not a bulk rename or terminology replacement.

## User Scenarios & Testing

### User Story 1 — Trust Every Retained Test (Priority: P1)

As a maintainer, I want every retained test to fail under a relevant product or architecture regression so that green results provide real confidence.

**Why this priority**: False-green tests are more dangerous than missing tests because they consume time while implying protection that does not exist.

**Independent Test**: Require every retained candidate unit to reference node-level proof or a named family proof. A family is valid only when members exercise the same production path and oracle while varying an explicitly recorded boundary; the controlled fault must reach the product action and fail the intended oracle rather than collection, import, or setup.

**Acceptance Scenarios**:

1. **Given** a test that reaches a live public behavior and has a distinct observable oracle, **when** the guarded behavior is broken, **then** the test fails for that broken behavior and receives a `KEEP` verdict.
2. **Given** an architectural guard over a live corpus, **when** a plausible production change violates a named current authority and observable invariant, **then** the guard fails and its corpus-floor check proves the scan is non-vacuous; merely planting the scanner's searched literal is insufficient.
3. **Given** a test that remains green after its alleged implementation is removed or faulted, **when** its evidence is reviewed, **then** it receives a `DELETE` or `FIX_TEST` verdict rather than protection by name or marker.

---

### User Story 2 — Remove Zero-Signal Test Weight (Priority: P1)

As a maintainer, I want inert and dominated tests removed so that collection, execution, and refactoring cost track the amount of actual defect protection.

**Why this priority**: The current suite collects 37,444 nodes in roughly 94–110 seconds before assertions and contains confirmed permanent skips, exact duplicates, historical mission checks, and never-fail advisory tests.

**Independent Test**: Run the complete candidate census, apply the disposition rubric, and compare node count, test lines, collection time, and CI-route cost before and after while preserving causal coverage.

**Acceptance Scenarios**:

1. **Given** an unconditional skip or placeholder with no executed assertion, **when** its contract is not being repaired in this mission, **then** the test body is removed and any still-valid requirement remains in its tracker issue or authoritative document.
2. **Given** two tests with the same contract and causal bite, **when** one is slower, shallower, or synthetic, **then** the stronger live-path test survives and the dominated duplicate is removed.
3. **Given** a test that validates historical WP reports, deleted branches, exact prose, magic counts, symbol placement, or mission-local scaffolding, **when** no current live contract depends on that shape, **then** the test is removed.
4. **Given** an obsolete positive-shape architectural test, **when** a still-valid negative invariant is embedded in it, **then** the negative invariant is retained or rehomed and the obsolete existence/shape assertions are removed.

---

### User Story 3 — Classify Red and Flaky Signal Honestly (Priority: P1)

As a maintainer, I want failing and nondeterministic tests classified by causal evidence so that the suite never green-washes product defects or preserves broken harnesses indefinitely.

**Why this priority**: A red test may be a valuable P0 reproduction, a stale contract, an infrastructure failure, or a true flake. Treating all red tests alike destroys signal.

**Independent Test**: Compare candidate behavior on the planning base and mission branch, repeat suspected flakes under isolated and CI-parallel conditions, and verify each red candidate has a terminal disposition.

**Acceptance Scenarios**:

1. **Given** a deterministic, current, live-entry-point reproduction of an accepted P0 product defect, **when** it is evaluated under the accepted red-main ADR, **then** exactly one issue-linked blocking reproduction remains honestly red until the product is fixed; release authority and known-red accounting remain explicit.
2. **Given** a permanently skipped copy of an open defect, **when** it cannot execute in blocking CI, **then** the inert test is removed rather than retained as documentation.
3. **Given** a correctness test with mixed outcomes under repeated identical runs, **when** nondeterminism is reproduced, **then** the root cause is fixed or the test is removed if it has no unique contract; it is never retried to green.
4. **Given** an environment or bootstrap failure before the product action, **when** outcomes are classified, **then** the harness is repaired and unrelated tests are not blamed.

---

### User Story 4 — Keep CI Routes Proportional (Priority: P2)

As a CI operator, I want narrow test classes routed without whole-suite collection and stale infrastructure bottlenecks so that wall-clock cost is proportional to executed signal.

**Why this priority**: Whole-tree marker discovery currently pays roughly 100 seconds of collection even for a single regression file, and the shared test-venv bootstrap can cascade thousands of setup errors.

**Independent Test**: Exercise the changed CI selectors and shared test environment from a clean checkout, then compare collection and execution timing to the baseline.

**Acceptance Scenarios**:

1. **Given** a CI class with a stable small manifest, **when** the job starts, **then** it collects only the owned paths rather than all 37,000+ nodes.
2. **Given** parallel workers that need a shared test environment, **when** one worker performs a valid slow install, **then** waiting workers do not convert it into thousands of unrelated setup errors.
3. **Given** a deleted or moved test, **when** marker and shard topology is validated, **then** no required contract becomes unrouted or silently skipped.

---

### User Story 5 — Audit Every Decision (Priority: P2)

As a reviewer, I want a machine-readable disposition ledger and before/after evidence so that each deletion can be challenged without reconstructing the audit.

**Why this priority**: Assertive deletion is safe only when caller, authority, routing, causal bite, overlap, and outcome evidence remain inspectable.

**Independent Test**: Sample every verdict class and trace the candidate from inventory through evidence to the retained test, tracker issue, or deletion diff.

**Acceptance Scenarios**:

1. **Given** any deleted candidate, **when** a reviewer inspects its ledger row, **then** the row identifies its prior path/node, test class, contract or lack thereof, evidence, verdict, and surviving guard or issue.
2. **Given** any temporary exemption, **when** the ledger is validated, **then** it has an owner, issue, expiry date, and terminal outcome; expired entries fail validation.
3. **Given** the aggregate mission diff, **when** hard gates run, **then** contract, architectural, cross-repository E2E, and issue-matrix results are recorded.

### Edge Cases

- A slow test is the only live boundary check for a critical contract: retain it until an equivalent cheaper live-path test proves the same fault sensitivity.
- A duplicate has one unique boundary or platform case: remove only dominated cases, not the unique oracle.
- A structural guard has no current violations: retain it only when it scans a nonzero live corpus and a planted violation demonstrates bite.
- A test points at an open issue but skips in every supported environment: remove the inert test; keep the issue and, if justified, one executable honest reproduction.
- A migration or compatibility test is old: age alone is not evidence of obsolescence; the supported-version policy must show the input is retired.
- A base failure is environmental or setup-related: preserve raw evidence, replay the minimal harness-only repair identically on disposable base and HEAD worktrees, and rerun before assigning a product/test verdict.
- A deleted test changes coverage percentage without losing unique causal protection: report the metric but do not use line coverage alone as a veto.
- A test is expensive only during collection: attribute collection, setup, and call cost separately.

## Requirements

### Functional Requirements

| ID | Title | Requirement | Priority | Status |
|----|-------|-------------|----------|--------|
| FR-001 | Complete candidate census | Reconcile every discovered test-like file/function and every collected source test function, coherent parameter family, and mechanically proven duplicate cluster. Include ignored paths, collection errors, deselected suites, quarantines, placeholders, and zero-node files; record markers, CI route or absence, outcome state, skip/xfail/quarantine reason, duration phase, referenced issue/contract, source target, and duplicate-group membership. Expand to node-level records wherever parameters differ in path, oracle, outcome, marker, route, cost class, or disposition. | High | Approved |
| FR-002 | Disposition rubric | Assign each candidate a disposition: `KEEP`, `CONSOLIDATE`, `FIX_TEST`, `FIX_PRODUCT`, `DELETE`, or narrowly time-bounded `TEMPORARY`. `FIX_TEST` and `FIX_PRODUCT` are nonterminal until repaired and reclassified; `CONSOLIDATE` is terminal only after survivor/removals are recorded. `TEMPORARY` is a one-time, non-renewable HiC-approved exception only for an irreplaceable environmental/platform guard; it is forbidden for permanent skips, placeholders, missing-ref tests, advisory-never-fail checks, deterministic correctness failures, and threshold tests. | High | Approved |
| FR-003 | Causal survival proof | Every deletion/consolidation/temporary candidate and every survivor materially changed or cited to justify deletion requires node-level or valid family evidence. A surviving guard must show a plausible production fault, incompatible consumed contract shape, or known-bad live entry point reaches Act and makes the intended oracle fail. Faults must violate a named current authority; collection/import/setup failures and scanner-self-tests do not count. Unchanged tests outside selected candidate classes remain represented by the global machine census without hand-authored causal narratives. | High | Approved |
| FR-004 | Zero-signal retirement | Delete unconditional placeholders, never-fail advisory tests, missing-ref tests, non-executed skips, and synthetic tests that cannot observe production behavior. | High | Approved |
| FR-005 | Duplicate consolidation | Consolidate exact and semantic duplicates, retaining the cheapest test with the deepest live path and every genuinely unique boundary oracle. | High | Approved |
| FR-006 | Scaffold retirement | Delete spent WP/mission acceptance scaffolds, historical-report validators, and current-code-to-current-code comparisons with no distinct oracle. Delete migration parity checks only when a named authoritative compatibility matrix proves both the production migration path and every supported consumer/input are retired. | High | Approved |
| FR-007 | Structural-test adjudication | Delete positive shape/prose/token/count pinning that lacks a current authority; require surviving architectural guards to prove live-corpus floor, failure under a plausible production change that violates a named authority, and a two-sided oracle. A planted searched literal alone is not causal proof. | High | Approved |
| FR-008 | Contract-test adjudication | Require each surviving contract test to name a still-consumed public contract and demonstrate sensitivity to an incompatible shape or behavior. | High | Approved |
| FR-009 | Honest regression lane | For each accepted open P0, preserve exactly one executable live-entry-point reproduction in the blocking regression lane under `docs/adr/3.x/2026-07-17-1-red-main-is-honest-ci-is-release-authority.md`. It remains honestly red until fixed, then proves red-to-green through the same entry point. It may be retired only when the issue is formally closed, downgraded, or adjudicated invalid and never skips, xfails, quarantines, or retries. | High | Approved |
| FR-010 | Red/flaky classification | Attribute red candidates against the planning base. Suspected deterministic correctness flakes run 20 isolated and 10 CI-parallel repetitions across five recorded `PYTHONHASHSEED` values and applicable platform runners: any mixed outcome is a confirmed flake; all-green is `NOT_REPRODUCED`, never proof of non-flakiness. Record commands, environment, seeds, worker topology, and outcomes. | High | Approved |
| FR-011 | Permanent-skip elimination | Adjudicate every unconditional skip and permanent xfail. No `KEEP` verdict may leave a test permanently non-executing. | High | Approved |
| FR-012 | Proportional CI routing | Replace whole-tree marker collection for stable narrow classes with explicit owned paths/manifests and validate that required tests remain routed. | Medium | Approved |
| FR-013 | Bootstrap reliability | Resolve #3283 so a valid shared test-environment build cannot time out sibling workers and cascade unrelated setup errors. Preserve the raw pre-fix infrastructure failure, then replay the minimal bootstrap fix identically in disposable base and HEAD worktrees before outcome and timing comparisons. | High | Approved |
| FR-014 | Disposition ledger | Produce a machine-readable global census plus deep ledger rows for every deletion, consolidation, temporary exception, nonterminal fix, and materially changed or deletion-justifying survivor. Rows include candidate identity, scope/family basis, class-specific evidence, verdict, action, survivor, issue, owner, and expiry. Every ledgered `KEEP` references node-level or valid family proof; every outcome divergence expands to node-level rows. | High | Approved |
| FR-015 | Before/after report | Record base and final node count, test LOC, collection/setup/call time, CI-route cost, duplicate groups, skip states, known-red set, and causal/mutation evidence. | Medium | Approved |
| FR-016 | Source residue cleanup | Remove test-only production symbols or dead surfaces only when caller/authority searches prove they have no live consumer and surviving behavior contracts remain protected. | Medium | Approved |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Complete inert-state coverage | 100% of source functions, coherent parameter families, or mechanically proven clusters containing unconditional skips, permanent xfails, quarantines, placeholders, missing-ref skips, or advisory-never-fail behavior receive a terminal ledger verdict; divergent members expand to node level. | Completeness | High | Approved |
| NFR-002 | Deletion evidence coverage | 100% of deletions satisfy the minimum evidence profile for their class: inert states require source/collection/route plus skip/issue/authority proof; duplicates require equivalence, survivor, and unique-boundary comparison; structural/contract guards require current authority/consumer and causal probe; slow tests require phase timing plus causal/survivor proof; flakes require the fixed matrix; dead symbols require caller/authority proof. No deletion relies only on age, name, marker, directory, or runtime. | Reliability | High | Approved |
| NFR-003 | Hard-gate preservation | Contract and architectural hard gates must pass unconditionally. Cross-repository E2E must pass unless the mission-review workflow accepts a schema-valid `mission-exception.md` for an environmental dependency; code defects never qualify. | Reliability | High | Approved |
| NFR-004 | Known-red preservation | Define the known-red set as exact nodeid+outcome records from the immutable planning base after the minimal #3283 fix is replayed and each red is adjudicated. Live product defects remain identical unless fixed red-to-green; stale, obsolete, or non-causal reds may be removed only as explicit ledger deltas. Raw pre-fix infrastructure results remain separate. | Integrity | High | Approved |
| NFR-005 | Repeatable timing | Performance comparisons use at least three clean runs under identical command, environment, worker count, and cache policy; report median and maximum separately. | Performance | Medium | Approved |
| NFR-006 | Material cost reduction | Freeze base workload commands and route universe before deletion. Across identical runner, cache, worker, and install policies, report summed compute cost and critical-path wall-clock separately, mapping renamed or removed routes explicitly and attributing deletion, routing, and bootstrap savings separately. Whole-suite collection median and fixed-route aggregate cost target at least 15% reduction; a miss remains a criterion miss unless the maintainer-in-charge explicitly waives it after causal-preservation review. | Performance | High | Approved |
| NFR-007 | No causal coverage regression | Unique live-contract and plausible-authority-violating fault coverage must not decrease across changed clusters. Focused mutation/fault probes preserve all non-equivalent kills owned by deleted tests; every materially changed or deletion-justifying `KEEP` has node or valid family proof over the same path, oracle, and boundary. | Quality | High | Approved |
| NFR-008 | Stable full-suite start | From a fresh clone, the documented parallel suite must begin executing test bodies without lock-timeout cascades in three consecutive runs. | Reliability | High | Approved |
| NFR-009 | Bounded temporary states | A temporary exemption is allowed once, only for an irreplaceable environmental/platform guard, with explicit HiC approval, owner, issue, terminal action, and expiry within 30 days. It cannot renew and cannot cover FR-004/FR-011 inert classes, correctness failures, or timing thresholds; zero expired exemptions may remain. | Governance | Medium | Approved |
| NFR-010 | Cross-platform safety | Deletions must preserve tests that uniquely guard Linux, macOS, Windows, or Python 3.11+ behavior; platform-specific removal requires equivalent platform evidence. | Compatibility | High | Approved |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No green-washing | No retry-to-green, assertion weakening, blanket skip, xfail, or quarantine may be introduced to make the suite pass. | Governance | High | Approved |
| C-002 | No deletion quota | Deletion count is an outcome, not a target. Evidence decides disposition; numerical quotas must not override a unique live contract. | Scope | High | Approved |
| C-003 | No marker immunity | `contract`, `architectural`, `regression`, `slow`, and directory names are claims requiring evidence, not automatic keep/delete decisions. | Quality | High | Approved |
| C-004 | Product fixes are exceptional | Do not change product behavior merely to make stale tests green. Changes outside tests/evidence/workflows are limited to #3283/#2645 test-harness reliability/performance and proven removal of test-only dead symbols/surfaces. | Scope | High | Approved |
| C-005 | Current authority wins | Active specs, ADRs, public contracts, supported-version policy, and live entry points determine intent; historical mission artifacts do not. | Architecture | High | Approved |
| C-006 | Test deletions remain reviewable | Partition changes by coherent test class/surface with non-overlapping file ownership and independent review. | Workflow | High | Approved |
| C-007 | Issue traceability | Referenced issues #1931, #2309, #2316, #2342, #2645, #2782, #3184, #3283, and #3284 must have explicit issue-matrix verdicts before merge. | Tracking | High | Approved |
| C-008 | PR-only delivery | All changes land through a pull request targeting `main`; the operator performs the protected-branch merge. | Workflow | High | Approved |
| C-009 | Honest-red authority | Accepted P0 reproductions follow the red-main ADR: one live blocking red is retained and accounted separately from release authority. No other correctness failure may be normalized, retried, skipped, xfailed, or quarantined. | Governance | High | Approved |

### Key Entities

- **Test Candidate**: A collected node or coherent parameterized family being evaluated; includes path, marker, route, state, cost, and alleged contract.
- **Contract Claim**: The live behavior, public shape, security boundary, platform rule, or architectural invariant a test claims to protect.
- **Evidence Bundle**: Caller and authority search, CI routing, base attribution, causal/fault probe, overlap analysis, and timing evidence supporting a verdict.
- **Disposition Record**: The durable ledger row connecting a candidate to a terminal verdict, action, surviving guard or issue, reviewer, and optional expiry.
- **Surviving Guard**: The retained test or external hard gate that continues to detect the candidate's unique defect hypothesis.

## Non-Goals

- No broad product-feature work or fixes for #2309, #2316, #2342, or #2782; inert pytest bodies may be deleted while those product decisions remain issue-tracked.
- No mechanical cleanup of the unrelated Sonar pytest-rule census in #2972.
- No blanket deletion of contract, architectural, migration, compatibility, regression, or platform suites.
- No replacement of live integration/contract coverage with cheaper mocked unit tests that do not exercise the same boundary.
- No claim that line coverage equality alone proves safe deletion.
- No release, deployment, or merge to protected `main` by an agent.

## Assumptions

- The immutable inventory baseline is commit `28ae75ea998c898aba57364db7a06d2088bd2af2`. Outcome and timing baselines replay only the minimal #3283 harness fix in a disposable worktree, apply that identical patch to HEAD, and keep raw pre-fix infrastructure results separate.
- The suite currently contains approximately 37,444 collected nodes, 2,432 `test_*.py` files, and 833,936 Python test lines. Refreshed planning found 173 docstring-normalized strict AST-body groups/365 members across 131 files; earlier projections found 171 normalized groups/357 functions and 75 stricter groups/162 functions. WP01 will version both algorithms and establish deterministic canonical manifests after #3283 recovery.
- CI and issue state may change during the mission; the final report uses the current target-branch base and records any drift.
- Tracker issues are authoritative for unresolved product defects; pytest is not an issue backlog.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Every inert-state candidate class in NFR-001 has 100% terminal disposition coverage and zero permanent `KEEP` results that remain non-executing.
- **SC-002**: Every deletion satisfies its class-specific evidence profile, every materially changed or deletion-justifying `KEEP` has node-level or valid family causal proof, and review finds zero deleted unique live-contract or plausible-authority-violating fault guards.
- **SC-003**: Frozen whole-suite collection median and fixed-route summed compute cost and critical-path wall-clock each improve by at least 15% across three equivalent runs. Any miss is reported as a criterion miss unless explicitly waived by the maintainer-in-charge; it never overrides causal-preservation gates.
- **SC-004**: Contract, architectural, cross-repository E2E, marker-routing, and platform-sensitive gates preserve or strengthen their causal bite.
- **SC-005**: A fresh-clone parallel run starts normally three times without the #3283 lock-timeout cascade.
- **SC-006**: Final PR contains a machine-readable disposition ledger, before/after report, issue matrix with terminal verdicts, and independently approved WPs.

## Referenced Issues

- #1931 — umbrella test-suite friction epic.
- #2309 — permanently skipped daemon-reaper contract tests.
- #2316 — permanently skipped upgrade contract tests.
- #2342 — quarantined timing threshold without stable protection.
- #2645 — pathological whole-tree collection scanner cost.
- #2782 — issue-pinned regression test that can self-skip.
- #3184 — completed regression files left in the wrong suite location.
- #3283 — shared test-environment lock timeout discovered during mission baseline.
- #3284 — 23 additional pre-existing full-suite failures and two errors discovered after bootstrap prewarm.
