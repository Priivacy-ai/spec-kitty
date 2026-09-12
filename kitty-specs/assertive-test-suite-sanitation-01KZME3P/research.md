# Research: Assertive Test Suite Sanitation

## Evidence Baseline

Inventory commit: `28ae75ea998c898aba57364db7a06d2088bd2af2`.

| Observation | Evidence | Planning consequence |
|-------------|----------|----------------------|
| 37,444 nodes collect in 94.26s; a marker-only probe was ~109.63s | local `pytest --collect-only` probes | collection is a first-class cost; narrow routes must name paths |
| 2,432 `test_*.py` files and 833,936 Python test lines | repository census | source discovery must precede collection reconciliation |
| 173 strict AST-body groups / 365 members across 131 files after docstring normalization; earlier projections found 171 normalized groups / 357 functions and 75 stricter groups / 162 functions | Multiple AST-normalization projections | fingerprints are candidates, not automatic deletes; WP01 records algorithm/version and owns canonical reconciliation |
| First fresh parallel run cascaded setup errors before Act | repeated lock-timeout logs; #3283 | repair/replay harness before outcome attribution |
| Mutation CI is hard-disabled | `.github/workflows/ci-quality.yml` | changed clusters need focused local mutation/fault evidence |
| Only one file currently bears the regression marker | `tests/regression/test_issue_2782_sync_strict_json_ingress_skip.py` | whole-tree marker collection is disproportionate and the sole guard can self-skip |
| Timing docs remain pending and shard routing uses test-count proxies | `docs/plans/testing/ci-job-timings.md` | freeze new measured baseline; do not trust annotations alone |

## Candidate Classes and Initial Evidence

These are mandatory adjudication inputs, not pre-authorized bulk deletions.

| Class | Concrete candidates | Initial hypothesis |
|-------|---------------------|--------------------|
| Permanent skips/placeholders | `tests/sync/test_daemon_singleton_reaper_consolidation.py`; `tests/sync/test_client_integration.py`; `tests/readiness/test_upgrade_ux.py` | delete inert bodies; tracker remains authority; preserve at most one executable diagnostic per accepted P0 |
| Invalid quarantine/threshold | `tests/retrospective/test_summary_tolerance.py` | threshold is not irreducible Tier-3 flake; prove owned statistical gate or delete |
| Never-fail advisory | `tests/architectural/test_retired_contracts_absent.py` | `record_property` findings cannot block; delete or convert only if a live invariant exists |
| Missing authority/ref | `tests/architectural/test_verdict_name_truthfulness.py` | deleted-branch checks are historical scaffolding |
| Historical mission/report checks | `tests/release/test_diff_coverage_policy.py`; `test_wp05_write_target_drain.py`; `test_no_parity_scaffold.py` | delete after current-authority and caller proof |
| Positive shape/prose/count pinning | `test_batch_drain_retired_3167.py`; duplicate glossary/lint guards; exact prose docs tests | delete assertions that cannot observe behavior; retain proven negative invariant only |
| Semantic duplicates | runtime `home` vs kernel paths; git-ops legacy vs unit suites; dashboard glossary/lint; lane template guards | keep canonical live seam plus unique platform/import boundaries |
| False-green P0 route | issue #2782 regression test | retain exactly one live blocking red under the red-main ADR; it cannot self-skip |
| Whole-tree marker routes | quarantine and regression jobs | replace with explicit owned path/manifest and route-validation evidence |

## Research Decisions

### R1 — A test must earn residence causally

**Decision**: retain only when a plausible mutation, incompatible consumed contract, or known-bad live entry reaches Act and fails the intended oracle. For an architectural rule, the fault must represent a realistic prohibited production change under a named current authority.

**Rejected**: coverage percentage, marker, directory, age, runtime, or planted searched literal as sufficient proof. Each is a proxy that can preserve false signal.

### R2 — Group evidence without hiding divergence

**Decision**: family/cluster evidence is allowed only for identical production path and oracle plus an explicit parameter boundary. Different outcome, marker, CI route, cost class, platform, or disposition forces node expansion.

**Rejected**: 37,444 hand-authored node narratives; they would consume the mission without adding causal evidence. Also rejected file-level verdicts that can hide one unique boundary.

### R3 — Discover outside pytest

**Decision**: AST/source discovery yields test-like functions and classes, then collection data reconciles them. Ignored, errored, deselected, quarantined, and zero-node sources stay visible.

**Rejected**: `pytest --collect-only` as the inventory source; it cannot report what it never collects.

### R4 — Fix bootstrap before judging product tests

**Decision**: record raw #3283 failures and implement this state machine in the cache directory: `ABSENT → BUILDING(owner_pid, process_start_token, heartbeat, temp_path) → VALIDATED → PUBLISHED`. A claimant briefly locks state, records a same-filesystem unique temp path, then releases the lock while building and heartbeats every five seconds. Waiters poll without holding the lock; a live/fresh owner continues, while a dead owner or heartbeat older than the recorded lease limit is reclaimed under lock and its temp path cleaned. The builder validates the temp Python, source-version marker, and editable import, reacquires the lock, proves lease ownership, removes only an invalid final, and renames the validated temp directory to the absent final path on the same filesystem. Publication is never in-place. Crash-mid-build, invalid-final, slow-live-owner, dead-owner, and two-simultaneous-start faults are required on supported OSes. Persist the exact replay patch artifact and apply it unchanged to disposable base and HEAD worktrees.

**Rejected**: merely lengthening a timeout with no dead-creator handling; it trades deterministic failure for longer hangs. Also rejected manual prewarm, building directly into the published path, and holding one fixed-duration lock across installation.

### R5 — Accepted P0 red follows current authority

**Decision**: under the accepted red-main ADR, an accepted unresolved P0 owns exactly one live blocking red reproduction, accounted separately from release authority. After a fix, the same reproduction proves red-to-green. Skips, xfails, quarantine, and retries are forbidden.

**Rejected**: duplicate permanent reds and false-green self-skipping regression jobs. Superseding the red-main ADR is outside this mission.

### R6 — Compatibility authority outranks age

**Decision**: migration/compatibility tests survive until a named support matrix proves the production path and every supported input/consumer are retired.

**Rejected**: deleting “old” migrations because their originating mission is complete.

### R7 — Timing is a fixed experiment

**Decision**: record exact command, runner/OS, worker count, cache policy, environment, route set, collection/setup/call phases, and three cold repetitions. Report median/max, summed compute, and critical path. Map deleted/renamed routes rather than dropping them from the denominator.

**Rejected**: comparing GitHub job durations across unlike runner classes, top-50 durations only, or route subsets selected after the change.

### R8 — Mutation is focused, not ceremonial

**Decision**: run focused `mutmut` or deterministic fault injection against the changed source cluster and survivor. Record unique non-equivalent kills and classify uncovered/surviving mutants.

**Rejected**: enabling a repository-wide mutation job as mission scope or claiming a global score from generated/boilerplate code.

## Flake Decision Matrix

For suspected deterministic correctness flakes:

1. Run 20 isolated repetitions.
2. Run 10 repetitions with the CI worker topology.
3. Span five recorded `PYTHONHASHSEED` values.
4. Add applicable OS runners only when the contract is platform-specific.
5. Any mixed outcome is `CONFIRMED_FLAKE`; all-green is `NOT_REPRODUCED`.
6. A single stable red is classified through base/HEAD attribution, never labeled flaky.

Quarantine is allowed only for irreducible Tier-3 environmental dependencies with owner, issue, and expiry no later than 30 days. Correctness and timing-threshold tests never use quarantine.

## Issue Matrix Intent

| Issue | Mission handling |
|-------|------------------|
| #1931 | umbrella; assign/comment; this mission delivers measured reduction |
| #2309 | remove ten inert skipped bodies unless a live executable reproduction is repaired separately |
| #2316 | remove two inert skipped bodies; no product fix in mission |
| #2342 | adjudicate invalid timing quarantine |
| #2645 | measure collection scanner cost; change only if evidence assigns ownership to this mission |
| #2782 | ensure exactly one live blocking reproduction while unresolved under the red-main ADR; it cannot self-skip |
| #3184 | reconcile completed regression files and route ownership |
| #3283 | red-first harness repair and three clean-start proofs |
| #3284 | classify 23 additional base failures and two errors; delete only stale/non-causal rows proven by this mission and leave live product fixes tracked |

## Planning Verdict

Proceed. Current suite has confirmed zero-signal weight and invalid routing, while the evidence rules prevent indiscriminate deletion. No unresolved planning question remains.
