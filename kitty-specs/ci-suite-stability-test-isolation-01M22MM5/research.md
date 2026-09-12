# Research — CI Suite Stability & Test-Isolation (#4017 + #4015)

## Decision 1 — #4017 fix = re-assess-under-lock (core) + observe() role-tag (enabler), generic scope
- **Decision**: On the cold/effects path, after acquiring the existing anchor flock (`asset_preparation.py:516-522`), **re-assess** effects against the now-warm home; the loser finds `effects==[]` and returns via the warm fast-path (`bootstrap.py:200-201`). Tag `observe()` entries source-read vs destination-probe and filter destinations at the compare site (`check_assets`). Land both at the **generic** `check_assets`/`ensure_runtime` seam (all owners). Do NOT strip `PreparedAssets.observations`.
- **Rationale**: The flock already serializes; the bug is the post-lock re-check validating a stale plan + non-idempotent apply (`mkdir`/`open("x")` at `:545`/`:617`). Narrowing alone converts `"Global asset input changed"` → `"global_asset_write_failed: File exists"` (post-spec squad BLOCKER). Re-assess is the minimal correct fix; role-tagging removes the conceptual "HOME-is-an-input" error and keeps the race from re-manifesting. Generic scope because all owners race identically on the shared home (HiC-confirmed).
- **Alternatives**: narrowing-only (rejected — converts the crash, doesn't fix it); per-worker-home isolation (rejected — dodge, abandons the shared-home property); geographic strip of observations (rejected — sources share the HOME prefix under test layouts → source-drift undetected; also breaks the fingerprint/cross-family invariants).

## Decision 2 — #4017 operator signal (OPERATOR_SIGNAL_CONTRACT)
- **Decision**: The re-assess/defer outcome emits a human sentence + machine signal on an existing operator-visible surface (CLI/log/exit); the red-first asserts on the emitted signal, not just the machine shape.
- **Rationale**: A deciding path (loser converged to no-op vs winner applied) must be operator-observable, not silently swallowed (epics #3410/#3549).

## Decision 3 — #4015 enabler = shared assert_timing_budget helper
- **Decision**: New `tests/_perf_helpers.py::assert_timing_budget(measured, budget)` whose call-site text is guard-clean (contains a vocabulary token like `budget`), used by vocab-blocked timing tests instead of widening `TIMING_ASSERTION_VOCABULARY` or per-var renames.
- **Rationale**: Uniform across all 9, no vocabulary widening (which risks a functional assert passing the guard), no bespoke renames. Deletion remains an evidence-gated option for low-value pure-timing gates.

## Decision 4 — #4015 split + delete discipline
- **Decision**: 74 mixed → split (functional assert stays per-PR unmarked; timing assert → `@performance` nightly, budget preserved, collected+green); 9 vocab-blocked → helper/rename/delete. DELETE is evidence-gated (flake-rate + AST zero-functional-assert + operator sign-off). Per-split coverage-mapping table makes no-coverage-loss diffable.
- **Rationale**: Keeps functional coverage on the per-PR path, enforces budgets nightly, and makes deletion auditable rather than judgment-only.

## Adversarial Evidence (pre-mission grounding + post-spec squads — dispositions)
Per `contracts/adversarial-evidence-contract.md`. No finding dropped.

### Pre-mission grounding squad
| # | Lens | Finding | Disposition | Landed |
|---|------|---------|-------------|--------|
| G1 | debugger (#4017) | Real TOCTOU race, not test-isolation; flock taken too late; ensure_runtime aborts instead of re-assessing | **accepted** | Decision 1; spec Context + FR-001 |
| G2 | researcher (#4015) | 74+9 lists still accurate in commit 1d59ed2ca6; chore-class; shared-helper recommended | **accepted** | Decision 3/4; C-005 |
| G3 | researcher (flaky census) | Scary flaky gates already off blocking path; residual = #4015; fold, add delete disposition; #4017 separate | **accepted** | folded into #4015 (comment); FR-011 delete disposition |

### Post-spec squad
| # | Lens | Sev | Finding | Disposition | Landed |
|---|------|-----|---------|-------------|--------|
| P1 | architect | **blocker** | Narrow-scope alone converts crash → "File exists" (non-idempotent apply); re-assess-under-lock is mandatory, not optional | **accepted** (reversed operator's narrow-only choice; re-confirmed) | FR-001 core; C-001; Decision 1 |
| P2 | architect | major | check_assets is generic (all owners race) — scope must be decided | **accepted** → HiC = GENERIC | FR-004; plan decision 01M22NKW |
| P3 | architect | major | "asset input" not cleanly source/destination separable — role-tag, don't strip | **accepted** | FR-002; C-002 |
| P4 | architect | minor | re-assess gated to cold path; warm = 1 assess, no lock | **accepted** | FR-005; NFR-002; SC-004 |
| P5 | architect | minor | #4082 uses separate charter_yaml_io recheck (insulated) — pin with regression | **accepted** | FR-007; SC-005 |
| P6 | architect | minor | place fix once (triple-nested recheck); test the real global_assets path | **accepted** | FR-004; SC-006 |
| P7 | renata | high | FR-002(apply-safety) un-gated — no SC proves apply safe | **accepted** | SC-002 deterministic interleave/convergence |
| P8 | renata | high | SC-001 "100% of 40 iters" green-by-luck + e2e nightly-only | **accepted** | SC-002 deterministic structural test (not dice-roll) |
| P9 | renata | high | No requirement that genuine SOURCE drift still caught (over-narrowing) | **accepted** | FR-003; SC-003 |
| P10 | renata | medium | No SC proves relocated budgets run nightly | **accepted** | NFR-004; SC-008 |
| P11 | renata | medium | DELETE boundary subjective — evidence-gate it | **accepted** | FR-011; SC-010 |
| P12 | renata | medium | NFR-003 not verifiable — per-split mapping | **accepted** | FR-013; NFR-003; SC-009 |

All accepted/changed; none deferred-without-rationale, none dropped.

### Post-plan brownfield squad
| # | Lens | Sev | Finding | Disposition | Landed |
|---|------|-----|---------|-------------|--------|
| BP1 | paula | — | Premise correction: #4082 did NOT touch asset_preparation/bootstrap/merge — coordinates + flock diagnosis intact | **accepted (confirms plan)** | no change; noted |
| BP2 | paula | major | `_recheck_command_completion` (managed_skills.py:165, #4082-modified) is a SEPARATE recheck not reached by check_assets | **accepted** | FR-004 verify-or-exclude; WP-A3 |
| BP3 | paula | major | FR-007 must drive the LIVE managed_skills composition interplay, not just dry-run preview | **accepted** | FR-007 rewritten |
| BP4 | paula | low | No open PR/parallel session/foldable on the seam | **accepted (no action)** | — |
| SP1 | planner | major | A1→A2 order erases the FR-006 exact signal ("File exists" after role-tag) | **accepted** | WP-A0 red-first-first; FR-006 rewritten |
| SP2 | planner | major | FR-004/SC-006 generic+triple-nested has no WP owner | **accepted** | WP-A3 |
| SP3 | planner | major | Lane B ~23-WP fan-out disproportionate | **accepted** | group by effort, collapse 1-2-file subsystems |
| SP4 | planner | major | Coverage-mapping has no owner | **accepted** | WP-B1 owns master table; splits append |
| SP5 | planner | medium | tests/_next_shard_map.py cross-lane conflict point | **accepted** | Coordination Points |
| SP6 | planner | medium | Delete sign-off scattered across ~25 WPs | **accepted** | front-loaded to WP-B1 one consolidated sign-off |
All accepted; none dropped.

### Post-tasks brownfield squad (WP-DoD tightenings)
| # | Lens | Sev | Finding | Disposition | Landed |
|---|------|-----|---------|-------------|--------|
| RT1 | renata | high | NFR-003 coverage invariant enforced nowhere (prose only) | **accepted** | WP05 T016a: AST functional-assert baseline + tests/architectural/test_timing_coverage_invariant.py; WP06-09 DoD |
| RT2 | renata | high | NFR-004 nightly-collection fakeable (local -m performance ≠ nightly shard-map) | **accepted** | WP06-09 DoD: prove collected by nightly lane's own selection |
| RT3 | renata | med | FR-007 clause (a) byte-unchanged unassigned | **accepted** | WP03 T011b |
| RT4 | renata | med | WP03 "driven green" satisfiable by skip/xfail | **accepted** | WP03 T008: 2 passed/0 skipped/0 xfailed, no xfail/skipif |
| RT5 | renata | med | red-first not bound to production path / witness | **accepted** | WP01 DoD: organic emission, text pinned to T002 witness |
| RT6 | renata | low-med | warm-path not instrumented | **accepted** | WP03 T011: spy (assess count==1, lock==0) |
| SP1 | planner | high | ~7 timing-test dirs unowned by WP06-09 | **accepted** | WP09 owned_files +agent/post_merge/core/next/release; scope-completeness note; architectural/upgrade as recorded out-of-map |
| SP2 | planner | med | WP01/03/04 new tests/runtime files under shard-map root, no registration note | **accepted** | shard-map note added WP01/03/04 |
| SP3 | planner | med | tests/_next_shard_map.py multi-owner silent-merge hazard | **accepted** | WP05 sole owner; others record filenames in Activity Log |
| SP4 | planner | low | authoritative_surface undersells WP07-09 | **noted** (cosmetic; reporting only) | — |
| SP5 | planner | low | WP05 sign-off gate reviewer-discipline-only | **accepted** | promoted to WP05 DoD (blocking) |
| SP6 | planner | — | dep chain/lanes.json/globs/create_intent confirmed sound | **accepted (no action)** | — |
All accepted/noted; none dropped.
