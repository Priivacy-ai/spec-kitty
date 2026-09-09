# Mission Specification: CI Pipeline Reinstatement

**Mission Branch**: `feat/ci-pipeline-reinstatement`
**Created**: 2026-09-07
**Status**: Draft
**Input**: Reinstate the CI pipeline (and SonarCloud/SonarQube) from the post-Convergence husk as a lean, well-crafted set of multiple artefact-sharing GitHub Actions workflows — full-tree modular, path-scoped, shift-left/fail-early, wallclock-optimized, with a separate packs workflow, giving the test suite a public stock-runner CI home again.

> **Research basis.** This spec is grounded in two research squads staged (gitignored) at `work/ci-reinstatement/` — the CI grounding set (`00-CONSOLIDATED-GROUNDING-BRIEF.md`, `PARAMOUNT-constraints.md`) and the test-friction corroboration set (`test-friction/00-CONSOLIDATED-TEST-FRICTION-BRIEF.md`), which frames the "test suite friction" epic **#1931**. Cited ticket numbers refer to `Priivacy-ai/spec-kitty` issues.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The test suite has a public CI home again (Priority: P1)

Today, on the public/contributor tree, **no tests run in CI at all**: `ci.yml` is fenced to the private EXPERIMENTAL repository and `ci-quality.yml` runs only lint/build/install. The architectural battery, terminology guard, coverage, corpus, and even the CI-ownership governance test have no public CI home. This story restores a stock-runner CI that actually exercises the suite on a pull request.

**Why this priority**: Without it there is no regression protection on the tree contributors and the promotion repo publish from — the single largest silent quality-posture gap from the Convergence. Everything else builds on it.

**Independent Test**: Open a PR touching a `src/**` module; confirm CI executes the relevant test shards on stock runners and reports a real pass/fail — where today zero tests execute.

**Acceptance Scenarios**:

1. **Given** a PR that changes a live `src/**` module, **When** CI runs on the spec-kitty repository, **Then** the module's test shard plus the always-on architectural + terminology gates execute on stock runners and gate the PR.
2. **Given** a PR opened from a contributor fork, **When** CI runs, **Then** secret-dependent jobs skip-green (advisory) and secret-free test/lint/arch jobs still execute and gate.
3. **Given** the reinstated workflows, **When** they run, **Then** none uses a Blacksmith runner and none references `SK_CI_TOKEN` on a public job.

---

### User Story 2 - A trustworthy green: clean base + reliable bootstrap (Priority: P1)

The suite is only *structurally* clean today; a full run on `main` shows **23 untracked failures + 2 errors (#3284)**, and the canonical `pytest -n auto` cannot even bootstrap on a fresh checkout (venv-lock timeout, **#3283**). A green gate built on that base would be a lie.

**Why this priority**: A shard topology cannot be frozen on a red base, and a warmup/bootstrap that fails non-deterministically poisons every job. This is a precondition gate, not an enhancement.

**Independent Test**: On a clean checkout, the shared warmup stage provisions the environment deterministically; a full run reports **0 untracked failures** (each prior red classified drop-dead-code-test vs fix-live-regression).

**Acceptance Scenarios**:

1. **Given** the #3284 base reds, **When** the mission triages them, **Then** each is classified as either a dead-code test (dropped, per P1) or a live regression (fixed), and the base run is green before any shard selection is frozen.
2. **Given** a pristine checkout, **When** the shared warmup / test-env-creation stage runs, **Then** it resolves the latest `spec_kitty_events` mainline, pre-builds the editable environment once, and publishes it as a reusable artefact — and downstream shards consume it without re-running the install (resolving #3283).

---

### User Story 3 - Fast, path-scoped feedback (docs/packs PRs don't pay for the full run) (Priority: P2)

A change-detection stage routes which jobs run so a docs-only or packs-only PR is not taxed with the whole test suite, and the cheapest gates fail first.

**Why this priority**: Wallclock and low-ROI-run avoidance are core to "lean." A docs typo should not trigger a 30-minute run.

**Independent Test**: A docs-only PR runs only docs + always-on gates; a packs-only PR runs only the packs workflow; neither runs the code test shards.

**Acceptance Scenarios**:

1. **Given** a PR touching only `docs/**`, **When** CI routes it, **Then** only the docs checks and always-on gates run; the code test shards are skipped.
2. **Given** a PR touching only `packs/**`, **When** CI routes it, **Then** only the packs workflow runs; the code test shards are skipped.
3. **Given** a `src/**` change matched by no filter group, **When** CI routes it, **Then** the router fails closed and runs the full pipeline (loud unmatched→run-all alarm), never a silent skip.
4. **Given** the pipeline, **When** it schedules jobs, **Then** static/lint/regen/terminology/arch-import gates run and can fail the PR before any expensive test shard starts.

---

### User Story 4 - Full-tree modular topology with artefact sharing + optimized wallclock (Priority: P2)

Every per-module test group runs as its own reusable workflow contributing to one full run; each stores reusable artefacts (warmed env, coverage, wheels) others consume. The heavy serial poles are de-serialized.

**Why this priority**: Delivers the operator's full-tree-modularization scope and the ~90%-of-the-win scheduling gains (de-serialize `integration-tests-next` 69→≤7 min; take the arch pole off the ~29-min critical path).

**Independent Test**: The critical-path wallclock is measured below target; each shard publishes a uniquely-named coverage artefact that the aggregator consumes without re-running tests.

**Acceptance Scenarios**:

1. **Given** the modular workflows, **When** the full pipeline runs, **Then** each per-module group is its own reusable workflow and their coverage artefacts aggregate into one run.
2. **Given** `integration-tests-next`, **When** it runs, **Then** it executes in parallel (`-n auto`) rather than fully serial, and the architectural pole runs always-on and de-serialized (adding no filter group).
3. **Given** each test shard, **When** it finishes, **Then** it uploads a uniquely-named coverage report under the shared artefact-naming contract, consumed downstream by the diff-coverage gate.

---

### User Story 5 - Code-quality scanning restored (Priority: P2)

SonarCloud/SonarQube scanning — fully removed at Convergence — is restored as a net-new workflow that aggregates the coverage artefacts and runs the scan from the spec-kitty repository.

**Why this priority**: Restores the quality/coverage posture (complexity, duplication, new-code coverage) the CLAUDE.md "Sonar Expectations" section describes but which has no CI behind it today.

**Independent Test**: A scheduled run produces a fresh Sonar report from aggregated coverage; on a fork without the token the job skips-green.

**Acceptance Scenarios**:

1. **Given** the reinstated coverage shards, **When** the Sonar workflow runs nightly/dispatch, **Then** it aggregates their coverage artefacts and produces a fresh analysis from the spec-kitty repository.
2. **Given** a context without `SONAR_TOKEN`, **When** the Sonar job runs, **Then** it skips-green (advisory) rather than hard-failing.
3. **Given** the pipeline matures to an efficient wallclock, **When** the operator elects, **Then** Sonar can be promoted from nightly to per-PR without re-architecting the artefact flow.

---

### User Story 6 - Separate packs workflow (built-in + internal) (Priority: P2)

A dedicated workflow validates the doctrine packs, independent from the code CI, so a packs-only change does not drag in the code suite and vice-versa.

**Why this priority**: Packs (`packs/built-in` public + `packs/internal` maintainer-only) have distinct checks (regen drift, DRG integrity, manifest freshness, corpus suite, plugin validate; and for internal: DRG-fragment validity, org-charter activation, packaging-safety negative guard) and their own trigger scope.

**Independent Test**: A packs-only PR runs the packs workflow (both lanes as applicable) and not the code shards; a src-only PR does not run the packs workflow.

**Acceptance Scenarios**:

1. **Given** a change under `packs/built-in/**`, **When** CI routes it, **Then** the built-in lane runs (regen `--check`, DRG `regenerate-graph --check`, pack-manifest freshness, corpus suite, plugin validate).
2. **Given** a change under `packs/internal/**`, **When** CI routes it, **Then** the internal lane runs (DRG-fragment validity, org-charter activation, packaging-safety negative guard) and the internal pack is proven to never ship in the wheel.
3. **Given** the packs workflow, **When** it triggers, **Then** its `on.paths` (Gate-0) and change-filter (Gate-1) stay in lockstep (or it runs on every PR with Gate-0 dropped), and the `-m corpus` exit-5 floor fires loudly if zero corpus tests are selected.

---

### User Story 7 - A lean suite: no dead-code tests, no low-ROI shape guards (Priority: P3)

The reinstated CI wires only trustworthy, live-signal tests. Dead-code tests and low-ROI shape guards are excluded/demoted; the enforcement allowlists that catch real defects stay always-on.

**Why this priority**: This is what makes the suite "well-crafted" rather than merely present — the operator's two paramount directives (P1, P2).

**Independent Test**: A reviewer can confirm no CI job selects a test over a retired/dead surface; a planted dead-code/retired-surface regression is still caught by the enforcement allowlists; shape guards no longer red a benign PR.

**Acceptance Scenarios**:

1. **Given** the dorny filter groups and `--cov` targets, **When** they are re-derived against live `src/**`, **Then** no group or job maps to a retired subsystem (sync/saas/delivery/emit) or a `never-restore` surface, and no shard selects a census-flagged dead-code behavioral test (e.g. the 12 mission_v1 dead-import files).
2. **Given** a planted change that reintroduces a retired import or a dead symbol, **When** CI runs, **Then** the dead-symbol / retired-subsystem enforcement allowlists red the PR (these stay always-on — they are not shape guards).
3. **Given** a benign PR (e.g. adding a symbol), **When** CI runs, **Then** low-ROI shape guards (golden-count/`len==N`, export-count, node-id baselines, byte-frozen copies) do not block it — they are demoted/converted/removed from the blocking gate.
4. **Given** the fix-before-wiring items, **When** a shard is assembled, **Then** every active `xfail(strict=True)` landmine is re-validated and the confirmed env-leak tests are fixed before they enter a gated shard.

---

### User Story 8 - Governance-safe reinstatement (map + integrity oracle) (Priority: P3)

Every workflow the mission de-defers is reconciled with the governance verdict map and its enforcing test, and the CI-integrity oracles are rebuilt against the real reinstated YAML so no test is silently selected by zero gates.

**Why this priority**: The verdict map is enforced; a de-defer that skips it reds the ownership test, and a vacuous collection oracle lets orphan holes return silently.

**Independent Test**: The ownership test passes for every restored workflow and runs on a workflow-changing PR (not only on a release tag); the collection-completeness oracle evaluates the real reinstated workflows.

**Acceptance Scenarios**:

1. **Given** a de-deferred workflow, **When** it is restored, **Then** `docs/convergence/interim-ci-producer.md` and `tests/release/test_release_ci_ownership.py` are updated in the same change, and that ownership test runs on every workflow-changing PR.
2. **Given** the reinstated multi-workflow topology, **When** the integrity oracle runs, **Then** it evaluates the real on-disk workflows and fails if any test is selected by zero gates (the two-authority path-filter model holds; `test_ci_quality_path_filters.py` is updated in lockstep with the filter reintroduction).

### User Story 9 - Two run modes: churn-guarded PR mode + full-signal nightly (Priority: P2)

The pipeline runs in two modes with deliberately different failure behavior. **PR mode is churn-guarded**: a red predecessor stops its dependent successors from running, so a broken PR does not burn compute on the rest of the matrix while the failure is unaddressed. **Full mode (nightly + manual "run full")** runs every job regardless of intermediate failures, producing full-spectrum signal so a single remediation pass can address every failure at once. Expensive **performance and heavy e2e tests run only on the nightly cadence (and on manual dispatch), never on the per-PR path**. Every workflow is manually dispatchable.

**Why this priority**: This is what keeps the reinstated CI *lean in practice* — PR mode minimizes churn and cost while a failure stands; nightly gives the complete picture for a full remediation. Manual dispatch makes every workflow independently runnable for debugging and on-demand full runs.

**Independent Test**: A PR with a failing early gate shows its dependent successor shards skipped (not run); a nightly/manual full run with multiple failures executes every job and reports the complete failure set; a PR shows performance/heavy-e2e jobs not executed; each workflow can be triggered from the Actions "Run workflow" control.

**Acceptance Scenarios**:

1. **Given** a PR whose early gate (or a predecessor shard) fails, **When** CI runs in PR mode, **Then** the dependent successor jobs/shards do not run (fail-fast short-circuit), so the PR does not run the full matrix while the failure stands.
2. **Given** the nightly schedule or a manual "run full" dispatch, **When** CI runs in full mode, **Then** every job runs regardless of other jobs failing (no short-circuit), and the run reports the complete set of failures for a single remediation pass.
3. **Given** a per-PR run, **When** it is routed, **Then** performance tests and heavy/expensive e2e tests are **not** executed; they run on the nightly cadence and on manual dispatch only.
4. **Given** any reinstated workflow, **When** a maintainer opens the Actions tab, **Then** the workflow exposes a manual `workflow_dispatch` trigger and can be run on demand.

### Edge Cases

- A PR touches a retired test directory that lingers only as `__pycache__` orphans → the router must not re-collect it; the orphans should be swept.
- A nightly full run hits several independent failures → it must run every job to completion and surface all of them (no early abort), so remediation is planned against the full failure set, not the first red.
- A maintainer manually dispatches a single per-module workflow while a dependency's status is unknown → manual dispatch runs that workflow standalone (full-mode semantics), independent of predecessor state.
- A shard split differs from `make test-fast`'s directory order → order-dependent env-leak tests must not red only in CI (fixed before wiring).
- A previous-run partial re-trigger leaves some coverage artefacts stale → the aggregator/Sonar must fall back to the most-recent successful run's artefacts.
- The Sonar project identity (`Priivacy-ai_spec-kitty`) may be stale post client-inversion → verified against the spec-kitty repository before the scan is wired to gate anything.
- A `packs/` template SOURCE edit also trips `regen-assets` → the packs workflow surfaces the regen diff with the exact remediation command.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Public CI home for the suite | As a maintainer, I want the full test suite to run on a PR to the spec-kitty repository on stock runners so that the public/promotion tree has real regression protection (today zero tests run there). | High | Open |
| FR-002 | Base-red triage precondition | As a maintainer, I want the 23 untracked base failures + 2 errors (#3284) triaged and each classified drop-dead-code-test — authorized ONLY by dead-code-census evidence, never a bare label — vs fix-live-regression, so that shard selection is frozen only on a green base and P1 cannot become a loophole to bury a live regression. | High | Open |
| FR-003 | Shared warmup / test-env-creation stage | As a CI author, I want a warmup stage that pre-builds the environment once as a reusable cached artefact so that downstream shards reuse it and the #3283 bootstrap lock is eliminated — resolving a **pinned `spec_kitty_events` rev in PR mode** (deterministic, cache-hit, charter pinned-rev aligned) and the **latest mainline in nightly/full mode** (to catch upstream drift early). | High | Open |
| FR-004 | Path-scoped change router | As a contributor, I want a change-detection stage that routes which jobs run (docs-only/packs-only PRs skip the code suite) with a fail-closed unmatched→run-all so that low-ROI runs are avoided without silent skips. | High | Open |
| FR-005 | Shift-left / fail-early ordering | As a contributor, I want the cheapest static/lint/regen/terminology/arch-import gates to run and fail first, and test tiers ordered cheap→expensive, so that a broken PR fails fast and cheap; shards within a tier run concurrently (not wallclock-serialized), while cross-tier stop-on-red behavior is mode-specific (see FR-019). | High | Open |
| FR-006 | Full-tree modular workflows | As a CI author, I want every per-module test group as its own reusable workflow contributing to one full run so that the pipeline is modular and each part is independently maintainable. | High | Open |
| FR-007 | Artefact-sharing contract | As a CI author, I want each shard to publish uniquely-named coverage/xunit artefacts under a preserved naming contract, consumed downstream by the aggregator and Sonar without re-running tests, so that workflows reuse each other's outputs. | High | Open |
| FR-008 | De-serialized heavy poles | As a maintainer, I want `integration-tests-next` parallelized and the architectural work split so the **fast always-on gates** (terminology, layer-rule/import) run unconditionally and de-serialized (adding no filter group) while the **heavy architectural battery is code-scoped** (so a docs-only PR pays for neither), so that the critical-path wallclock drops sharply with no signal loss and without contradicting docs-only leanness (NFR-002). | High | Open |
| FR-009 | Coverage aggregation + diff-cover PR gate | As a maintainer, I want per-shard coverage aggregated and a diff-coverage gate enforcing changed-line coverage so that new code stays covered. | Medium | Open |
| FR-010 | Sonar scanning workflow (net-new) | As a maintainer, I want a net-new Sonar workflow that aggregates coverage and runs from the spec-kitty repository, nightly/dispatch initially and promotable to per-PR, fork-safe when unconfigured. | Medium | Open |
| FR-011 | Separate packs workflow (built-in + internal lanes) | As a maintainer, I want a dedicated packs workflow with a built-in lane (regen/DRG/manifest/corpus/plugin) and an internal lane (DRG-fragment/org-charter/packaging-safety), triggered by packs paths and independent from the code CI. | Medium | Open |
| FR-012 | Governance-map reconciliation | As a governance owner, I want every de-deferred workflow to update `docs/convergence/interim-ci-producer.md` and `tests/release/test_release_ci_ownership.py` in lockstep, with that ownership test running on every workflow-changing PR — and, because the enforcer today asserts a **closed set** of pre-fork paths with only a `restore\|defer\|never-restore` vocabulary, I want the map schema + test **extended with an `introduced` disposition (and set)** so net-new workflows (Sonar, new `module-*.yml`) with no pre-fork ancestor are representable rather than un-modellable — so that the map never drifts from reality. | High | Open |
| FR-013 | Retirement scrub (P1) | As the operator, I want dorny groups and `--cov` targets re-derived against live `src/**` so that no CI job selects a test over dead/retired code or a `never-restore` surface; the **dead-code census is the machine oracle** that authorizes each exclusion (no bare labels), a **planted dead-code-shard / retired-import negative test** proves the exclusion gate actually fires (not a prose promise), and the dead-symbol/retired-subsystem enforcement allowlists remain always-on. | High | Open |
| FR-014 | Shape-guard demotion (P2) | As the operator, I want low-ROI whitelist/golden-count/frozen-baseline shape guards demoted/converted/removed from the blocking gate (e.g. derive twelve-agent parity from source), while the enforcement allowlists are left untouched (#3458). | Medium | Open |
| FR-015 | Fix-before-wiring hygiene | As a CI author, I want every active `xfail(strict=True)` landmine re-validated and the confirmed env-leak tests fixed before their tests enter a gated shard so that CI greens/reds reflect real state, not scaffold drift. | Medium | Open |
| FR-016 | CI-integrity oracle rebuild | As a maintainer, I want the collection-completeness / two-authority path-filter oracle rebuilt against the **real on-disk reinstated YAML** (and the corpus exit-5 floor re-established) so that no test is silently selected by zero gates; the rebuilt oracle MUST carry a **non-vacuity floor + a planted-orphan negative test** (it fails when it evaluates nothing, closing the currently-vacuous oracle), fix the zero-producer/inert-slot bare-name false-pass, and expose a **single importable gate-selection authority** reused by both CI and local pre-PR parity (one authority, not a second) (#2967, #2476). | Medium | Open |
| FR-017 | Reinstated CI is the primary producer (EXPERIMENTAL archived) | As a programme owner, I want the reinstated CI to assume the primary/sole CI role now that the EXPERIMENTAL repo is **archived** and its Blacksmith `ci.yml` producer is **inert** (archived repos run no Actions) — the nightly/full run provides the comprehensive whole-tree arch + terminology + coverage signal Blacksmith formerly produced — and I want the dead EXPERIMENTAL-fenced `ci.yml` neutralized/retired **in lockstep with its enforcing seam `test_private_factory_ci_is_scoped_to_experimental_repo`** (which hard-asserts the fence), so no workflow targets an archived repo and no orphaned test reds. | High | Open |
| FR-018 | Manual dispatch on every workflow | As a maintainer, I want every reinstated workflow to expose a `workflow_dispatch` trigger so that any workflow can be run on demand (debugging, on-demand full runs, re-runs). | High | Open |
| FR-019 | Dual-mode failure behavior (PR fail-fast vs full run-all) | As a maintainer, I want PR mode to short-circuit — a red predecessor stops its dependent successors — while full mode (nightly + manual "run full") runs every job regardless of failures, so that PR runs avoid churn/cost while a failure stands and nightly runs yield full-spectrum signal for a single remediation pass. A successor **skipped** because its predecessor red MUST NOT count as a pass for merge-eligibility (skipped ≠ green): the required-check set distinguishes short-circuit-skipped from passed, so a short-circuited PR is never mergeable on a masked failure. | High | Open |
| FR-020 | Expensive-test cadence (nightly, not per-PR) | As a maintainer, I want performance tests and heavy/expensive e2e tests to run on the nightly cadence and on manual dispatch only — never on the per-PR blocking path — via a dedicated performance-test workflow, plus a guard flagging `@pytest.mark.performance` tests that carry non-timing (functional) assertions so functional coverage cannot silently leave the PR path (#3595, #3665). | High | Open |
| FR-021 | Interpreter matrix (nightly) | As a maintainer, I want a nightly pytest lane running above Python 3.12 (up to the supported ceiling) so that interpreter-divergence defects are visible instead of escaping CI, kept off the per-PR path to protect latency. The nightly lane is in-mission; the full above-3.12 burn-down is a **linked follow-up** (deferred child #3189), not an in-mission claim. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Critical-path wallclock | The per-PR blocking path completes in ≤ 15 minutes on stock runners for a full `src`-triggering PR (from a historical ~29–34 min critical path); `integration-tests-next` ≤ 7 minutes (from 69.2 min). Thresholds are validated against a recorded baseline run (run-id captured), not asserted. | Performance | High | Open |
| NFR-002 | Low-ROI-run avoidance | A docs-only PR runs 0 code test shards; a packs-only PR runs 0 code test shards; each runs only its scoped checks plus the **fast** always-on gates (terminology/layer-rule). The heavy architectural battery is code-scoped and does NOT run on a docs-only PR. | Performance | High | Open |
| NFR-003 | Changed-line coverage gate | Diff-coverage enforces ≥ 90% on changed critical-path lines as a PR gate. | Reliability | Medium | Open |
| NFR-004 | Fork-safe degradation | 100% of jobs requiring a secret absent in the fork/PR context skip-green (advisory) rather than hard-fail; enforcement re-arms in the canonical repo context. | Reliability | High | Open |
| NFR-005 | Duration-balanced shards | Shard boundaries are derived from a measured `--durations` run against live `src/**`, with inter-shard wallclock skew ≤ 20%. | Performance | Medium | Open |
| NFR-006 | Green integrity | A green CI run guarantees (a) no test was selected by zero gates and (b) no dead-code test contributed to the run or the coverage denominator — **both machine-enforced**: the non-vacuous integrity oracle for zero-gate orphans, and the dead-code census for denominator exclusion. Not a reviewer scrub. | Reliability | High | Open |
| NFR-007 | Shape-guard churn reduction | Zero low-ROI shape guards (golden-count/export-count/node-id/byte-frozen) remain on the PR-blocking path; benign symbol additions do not red CI on shape alone. | Maintainability | Medium | Open |
| NFR-008 | PR-mode churn/compute avoidance | In PR mode, once a predecessor job/shard reds, its dependent successors do not consume runner compute (short-circuit); a PR with an early failure runs strictly fewer jobs than a full run. Nightly/manual full mode runs 100% of jobs regardless of failures. | Performance | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Governance lockstep | Every de-defer updates `docs/convergence/interim-ci-producer.md` AND `tests/release/test_release_ci_ownership.py` in the same change; the closed `restore\|defer\|never-restore` schema is extended with an `introduced` disposition so net-new workflows (Sonar, new `module-*.yml`) are representable rather than un-modellable. | Technical | High | Open |
| C-002 | Stock runners, no private token | Restored workflows use stock runners only (no Blacksmith runners) and carry no `SK_CI_TOKEN` on public jobs (both are test-asserted). | Technical | High | Open |
| C-003 | No retired/never-restore surfaces | No `never-restore` workflow is reinstated and no sync/saas/delivery/emit gate is wired; retirement remains arch-enforced. | Technical | High | Open |
| C-009 | Every workflow manually dispatchable | Every reinstated workflow declares a `workflow_dispatch` trigger; the "run full" manual mode is available on demand independent of the nightly schedule. | Technical | High | Open |
| C-010 | EXPERIMENTAL/Blacksmith is archived-inert | The EXPERIMENTAL repo is archived and its Blacksmith `ci.yml` producer runs no Actions; the mission must not assume any live Blacksmith backstop, must neutralize/retire the dead EXPERIMENTAL repo-identity fence, and the reinstated CI carries the full-signal role (whole-tree arch/terminology/coverage in nightly/full mode). | Technical | High | Open |
| C-004 | PR-only, never push to main | Workflows are validated via PR + `workflow_dispatch`; `spec-kitty merge` consolidates local `main` only; publication is via a PR targeting `main`. | Technical | High | Open |
| C-005 | Artefact naming contract preserved | Coverage/xunit artefacts preserve the `coverage-<tier>-<module>.xml` + `*-reports` naming, `relative_files=true`, and dotted `--cov=<module>` form so aggregators resolve them. | Technical | Medium | Open |
| C-006 | P1 — no dead-code tests; keep enforcement allowlists | No CI job runs a test over dead/retired code, where "dead code" is defined by the **machine dead-code census** (not a per-reviewer judgment call); the dead-symbol/retired-subsystem enforcement allowlists (`test_no_dead_symbols`/`test_no_dead_modules`/`test_no_retired_subsystems`) stay always-on and a planted-regression negative test proves they still fire. | Technical | High | Open |
| C-007 | P2 — shape guards off the blocking gate | Whitelist/golden-count/frozen-baseline shape guards are demoted/converted/removed from the blocking gate; the enforcement-allowlist-vs-shape-guard partition is a **committed, machine-checkable membership list** (not a per-PR judgment call), so relabeling cannot game it in either direction; the enforcement allowlists are NOT in scope of this demotion. | Technical | High | Open |
| C-008 | Sonar runs from the spec-kitty repo | Sonar analysis runs from the spec-kitty repository (current target), nightly/dispatch initially; its project identity is verified before it is wired to gate anything. | Technical | Medium | Open |

### Key Entities

- **Workflow**: a GitHub Actions workflow file; either a shift-left front, a reusable per-module test workflow, the aggregation/gate workflow, the Sonar workflow, or the packs workflow.
- **Change router**: the path-filter stage mapping changed paths → filter groups → which jobs run; fail-closed on unmatched `src/**`.
- **Warmup env artefact**: the pre-built, dependency-resolved environment (pinned `spec_kitty_events` rev in PR mode, latest mainline in nightly/full) published/cached once and reused by downstream jobs.
- **Coverage/xunit artefact**: uniquely-named per-shard reports under the preserved naming contract, consumed by the diff-cover gate and Sonar.
- **Governance verdict map**: `docs/convergence/interim-ci-producer.md`, enforced by `tests/release/test_release_ci_ownership.py` — the restore/defer/never-restore authority.
- **Enforcement allowlist**: dead-symbol / retired-subsystem gates that quote dead surfaces as banned strings (highest-value tests; always-on) — distinct from a shape guard.
- **Shape guard**: a whitelist/golden-count/frozen-baseline test asserting the shape of the code/suite rather than behavior (low-ROI; demote).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A PR to the spec-kitty repository that changes a `src/**` module executes the relevant test shards + always-on gates in CI (baseline today: **0 tests run** on the public tree).
- **SC-002**: A docs-only PR and a packs-only PR each complete CI without running any code test shard.
- **SC-003**: The per-PR blocking path completes in ≤ 15 minutes; `integration-tests-next` in ≤ 7 minutes.
- **SC-004**: The set of must-run-on-every-`src`-change gates is **enumerated** in the topology; the non-vacuous integrity oracle fails any topology where an enumerated gate is unwired or a test is selected by zero gates. (Each gate's *runtime* execution is evidenced by its own job result, not inferred from the static oracle.)
- **SC-005**: **Zero** CI jobs select a test over a census-flagged dead/retired surface (machine-verified, not a reviewer eyeball), and a planted retired-import/dead-symbol regression is still caught by the always-on enforcement allowlists.
- **SC-006**: Low-ROI shape guards no longer block PRs (benign symbol additions pass), while the enforcement allowlists continue to catch real defects.
- **SC-007**: A fresh code-quality (Sonar) report is produced (nightly) from aggregated coverage, with a documented, no-rearchitecture path to per-PR.
- **SC-008**: Before shard selection is frozen, every prior base failure is **either dropped (census-authorized dead-code test) or fixed (live regression)** — none is tracked-and-left-red — and the canonical suite bootstraps deterministically on a clean checkout.
- **SC-009**: In PR mode, a run whose early gate fails executes strictly fewer jobs than a full run (dependent successors are skipped); a nightly/manual full run with ≥2 failures still executes 100% of its jobs and reports every failure.
- **SC-010**: 100% of reinstated workflows can be triggered manually from the Actions "Run workflow" control (`workflow_dispatch` present).
- **SC-011**: A per-PR run executes 0 performance/heavy-e2e jobs; those jobs execute on the nightly schedule and on manual dispatch.

## Assumptions

- **Sonar deployment (confirmed with operator):** Sonar runs from the spec-kitty repository (current target), **nightly/dispatch initially**, promoted to per-PR only if the pipeline becomes efficient enough; `SONAR_TOKEN` lives on that repository and jobs skip-green where it is absent. The existing SonarCloud project identity (`Priivacy-ai_spec-kitty` / `priivacy-ai`) is treated as a **verify-before-wiring** task, not an assumption of validity, given the post-Convergence client-repo inversion.
- **Dependency resolution (confirmed with operator):** the shared warmup / test-env-creation stage folds dependency resolution + editable install into a single pre-warm that emits a reusable cached environment artefact — resolving a **pinned `spec_kitty_events` rev in PR mode** (deterministic, charter pinned-rev aligned) and **latest mainline in nightly/full** (upstream-drift signal). Dissolves the earlier "#830 phase / public `uv sync`" question into a design step (and resolves #3283).
- **Scope (confirmed with operator):** full-tree modularization — every per-module test group becomes its own reusable workflow — **retained as the target but delivered in phased WP clusters gated by hard cluster gates** (Foundation → Topology → Lean-suite), so the ~40-workflow surface lands in gated stages, not one big-bang (post-spec squad reconciliation of the full-tree ROI concern).
- **Leanness split (grounded):** ~90% of the wallclock win is scheduling/tiering (de-serialization, shard rebalancing, `git_repo` fixture-tier consolidation), ~10% is pruning.
- **Governance spine:** the mission is a `defer`→`restore` reconciliation of the enforced verdict map; Sonar is net-new (needs a new row). Because the EXPERIMENTAL repo is archived, the verdict map's "private EXPERIMENTAL vs public promotion" split is itself stale and is expected to be reconciled as part of the governance-map update (the reinstated CI is the primary producer, not a shift-left layer beneath Blacksmith).
- **Run modes (operator-confirmed):** two modes — PR (fail-fast, red predecessor short-circuits successors, no performance/heavy-e2e) and full (nightly + manual "run full", run-all-regardless, full spectrum incl. performance/e2e). Every workflow is manually dispatchable.
- **EXPERIMENTAL archived (operator-confirmed, crucial):** `spec-kitty/EXPERIMENTAL-spec-kitty` is archived; its Blacksmith producer is inert. There is no live CI anywhere until this mission lands, and the reinstated CI must carry the full merge-gate-grade signal itself (in nightly/full mode).

## Tracked Tickets (issue-matrix scope)

The mission **claims and will resolve** the following `Priivacy-ai/spec-kitty` tickets (each enters the mission issue matrix and requires an in-mission verdict at approval):

| Ticket | Maps to | Claim |
|---|---|---|
| #3284 — main full suite: 23 untracked failures + 2 errors | FR-002 | co-assigned (with Robert), linked |
| #3283 — shared test-venv lock bootstrap timeout | FR-003 | co-assigned (with Robert), linked |
| #3595 — dedicated performance-test CI workflow | FR-020 | assigned, linked |
| #3665 — guard mis-marked `@pytest.mark.performance` functional tests | FR-020 | assigned, linked |
| #3458 — golden-count gate low-ROI toll | FR-014 | assigned, linked |
| #2967 — zero-producer lint bare-name false-pass | FR-016 | assigned, linked |
| #2476 — local pre-PR arch-pole parity / gate-selection authority | FR-016 | assigned, linked |

**Parent epic (contributes to, does not close):** #1931 — "Test suite friction" (all the above are already children of it).
**Linked follow-up (NOT an in-mission claim, per operator):** #3189 — full above-3.12 interpreter burn-down. FR-021 lands the nightly lane in-mission; the complete burn-down remains a deferred child of #1931 and is not in this mission's issue-matrix verdict scope.
**Context reference (not owned):** #830 — programme release phase (cited only where the mission dissolved the public-dependency question; matrix verdict = context/deferred).

## Resolved Investigations

- **EXPERIMENTAL repo archived → Blacksmith is inert; reinstated CI is the primary producer (operator-confirmed).** The `spec-kitty/EXPERIMENTAL-spec-kitty` repository is **archived**, so its Blacksmith `ci.yml` producer runs no Actions and provides **no live CI backstop anywhere**. This supersedes the earlier "coexist / de-dup" framing: there is no second live producer to conflict with, and the "one producer per repo" concern is moot. Consequence (FR-017 / C-010): the reinstated CI on the spec-kitty repository (current target) is the **sole/primary** CI and must itself carry the full-signal role — the whole-tree architectural + terminology + coverage signal — via the nightly/full mode, and the dead EXPERIMENTAL-fenced `ci.yml` should be neutralized/retired.
- **Blacksmith `bin/ci-run.sh` behavior (directly audited, now historical).** For the record: `bin/ci-run.sh` selected `make test-full` (whole-tree pytest incl. `tests/architectural/` → arch gates + terminology, but **no coverage**). This confirms coverage was never in CI and is net-new, and documents the signal the reinstated nightly/full run must reproduce now that Blacksmith is inert.

_No open `[NEEDS CLARIFICATION]` decisions remain; the operator-facing facts were either confirmed in the discovery exchange or resolved by the probe above._

## Review Provenance

- **Post-spec adversarial squad (2026-09-07, advisory point-cut per charter SO#1):** 4 profile-loaded
  lenses — architect-alphonso (topology), reviewer-renata (fakeable-assertion), planner-priti
  (scope/sequencing), debugger-debbie (live-evidence). Unanimous verdict **ready-with-fixes** (no
  re-scope). Convergent finding: P1/P2 must be **machine-enforced oracles**, not prose + reviewer
  scrub — folded into FR-002/013/016, C-006/007, NFR-006, SC-004/005/008. Structural BLOCKER (map
  schema closed-set) folded into FR-012/C-001; FR-008↔NFR-002 arch-pole contradiction reconciled;
  FR-017 `ci.yml`-retirement lockstep target named; FR-019 merge-eligibility invariant pinned.
  Two items carried to `/spec-kitty.plan` (scope/sequencing) and two surfaced as operator decisions
  (full-tree ROI; warmup latest-mainline vs pinned-rev). Synthesis: `work/`-staged squad findings.
