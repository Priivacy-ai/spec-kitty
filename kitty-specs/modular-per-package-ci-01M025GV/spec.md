# Mission Specification: Modular per-package CI + automated asset/prompt regeneration

**Mission Branch**: `mission/modular-per-package-ci`
**Created**: 2026-08-15
**Status**: Draft
**Tracker**: [Priivacy-ai/spec-kitty#3447](https://github.com/Priivacy-ai/spec-kitty/issues/3447) (motivating symptom: [#3379](https://github.com/Priivacy-ai/spec-kitty/issues/3379))
**Input**: Modularize CI so `kernel`/`doctrine`/`packs` each build as their own reusable workflow feeding one aggregated Sonar run, and add automated source-driven regeneration of the generated command/skill fixtures with a self-service fix.

> Phase-0 research (`research.md`) settled the two load-bearing decisions and corrected three scope
> assumptions in the issue. This spec is written against those settled decisions. Key corrections carried
> here: the drifting assets are **committed test fixtures** (144 command baselines + 24 skill snapshots), not
> the untracked `.claude/commands/`; per-package `pyproject.toml`s are **dormant** (this is a test-partition +
> workflow-structure split, not per-wheel builds); Sonar does **not** decorate PRs today (single-run
> aggregation + `diff-coverage` PR gate is the invariant to preserve).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Kernel builds as its own precursor workflow, coverage still aggregates (Priority: P1)

As a **maintainer**, I want the `kernel` module extracted into a self-contained, independently-runnable
reusable workflow (`on: workflow_call`) invoked as an ordered job inside `ci-quality`, so that the module has
its own build boundary while its `coverage-kernel.xml` still aggregates into the single run consumed by
`diff-coverage` and the nightly Sonar scan.

**Why this priority**: This is the architectural proof-of-concept for the whole `(a)` mechanism. `kernel` is
the smallest, cleanest package (`needs:[changes]` only, single non-sharded job, own 90% floor). Proving
coverage-into-aggregation end-to-end de-risks doctrine + packs.

**Independent Test**: Extract `.github/workflows/module-kernel.yml`, replace the `kernel-tests` body in
`ci-quality.yml` with a `uses:` caller keeping the same job id + gate, open a PR touching `src/kernel`, and
confirm `coverage-kernel.xml` appears in `diff-coverage`'s discovered set and the module job runs — in one run.

**Acceptance Scenarios**:
1. **Given** a PR that changes `src/kernel`, **When** ci-quality runs, **Then** the kernel steps execute inside
   the caller's run via the reusable workflow and `kernel-test-reports` / `coverage-kernel.xml` are produced.
2. **Given** the extracted workflow, **When** `diff-coverage` and the nightly `sonarcloud` jobs run, **Then**
   they discover `coverage-kernel.xml` unchanged (glob discovery) and total coverage is not reduced vs baseline.
3. **Given** branch protection pins `quality-gate`, **When** the `uses:` refactor changes inner check names,
   **Then** the required check still resolves and merge is not blocked.

---

### User Story 2 — Self-service regeneration of generated fixtures (Priority: P1)

As a **contributor** who edited a source prompt under `packs/built-in/missions/mission-steps/**`, I want a
single command that regenerates the committed command baselines and skill snapshots, so I can fix the drift
myself instead of a maintainer regenerating by hand.

**Why this priority**: This is the primary DevEx win and directly closes #3379. It is independently valuable
even before the CI automation lands.

**Independent Test**: Run `spec-kitty regen` after a source-prompt edit; the 144 command fixtures + 24 skill
snapshots update byte-identically to what a `PYTEST_UPDATE_SNAPSHOTS=1` pytest run produces; `spec-kitty regen
--check` then exits 0.

**Acceptance Scenarios**:
1. **Given** an edited source prompt, **When** I run `spec-kitty regen`, **Then** all affected fixtures are
   rewritten and the drift gates pass.
2. **Given** stale fixtures, **When** I run `spec-kitty regen --check`, **Then** it exits non-zero and prints
   the offending `<agent>/<command>` paths, a unified diff, and the literal remediation line `Run: spec-kitty regen`.
3. **Given** fresh fixtures, **When** I run `spec-kitty regen --check --json`, **Then** it exits 0 and emits
   structured JSON reporting no drift.

---

### User Story 3 — Doctrine and packs modularized the same way (Priority: P2)

As a **maintainer**, I want `doctrine` (its fast + integration legs, `src/doctrine` + `src/charter`) and
`packs` (the `fast-tests-corpus` group) extracted into their own reusable workflows, so all three modules share
the same module-owned build boundary and precursor pattern.

**Why this priority**: Generalizes the proven POC. Depends on US1's mechanism being validated.

**Independent Test**: Extract `module-doctrine.yml` and `module-packs.yml`, wire as `uses:` jobs, run full
ci-quality, confirm all module `coverage-*.xml` aggregate and CI is green.

**Acceptance Scenarios**:
1. **Given** the doctrine reusable workflow, **When** ci-quality runs, **Then** `coverage-fast-doctrine.xml`
   and `coverage-integration-doctrine.xml` are produced and aggregated, preserving artifact names.
2. **Given** the packs reusable workflow (lifted `fast-tests-corpus`), **When** ci-quality runs, **Then**
   `coverage-fast-corpus.xml` is produced and aggregated.
3. **Given** all three modules extracted, **When** the architectural CI-model guards run, **Then** they
   tolerate `uses:` caller jobs and pass.

---

### User Story 4 — Trust-tiered CI regeneration automation (Priority: P2)

As a **maintainer**, I want CI to keep the generated fixtures fresh automatically on trusted events and to fail
loudly-but-followably on untrusted ones, so drift never reaches a late gate failure.

**Why this priority**: Automates US2's fix. Depends on the `regen` tool existing.

**Independent Test**: Push to a same-repo branch with stale fixtures → workflow auto-commits the regen; open a
fork PR with stale fixtures → check-only failure with the remediation command; apply the `regen` label →
privileged run pushes the regen commit into the fork branch.

**Acceptance Scenarios**:
1. **Given** a same-repo push or `workflow_dispatch` with drift, **When** the regen workflow runs, **Then** it
   commits the regenerated fixtures back to the branch (bot identity, `contents: write`).
2. **Given** a fork PR with drift, **When** the regen workflow runs, **Then** it runs `spec-kitty regen
   --check` only, fails with the exact command + diff, and does not attempt to push.
3. **Given** a maintainer applies the `regen` label to a fork PR, **When** the privileged workflow runs, **Then**
   it regenerates and pushes into the fork branch via the least-privilege maintainer PAT, executing only
   base-repo tooling over PR data (`pull_request_target` trusted-tooling pattern).

---

### User Story 5 — Narrow the drift gate to end the churn (Priority: P2)

As a **maintainer**, I want the twelve-agent and command_renderer gates narrowed from the 144+24 byte grid to
structural invariants + one canonical snapshot, so a one-line source edit stops fanning out to ~14 fixture
failures even before regen is run.

**Why this priority**: Permanently reduces churn (the maintainer TODOs in the gate tests already propose this).
Complementary to regen; sequenced after the tool exists so behavior is proven equivalent first.

**Independent Test**: Edit one source prompt; confirm the narrowed gate flags at most one canonical snapshot +
the structural invariants, not the full per-(agent,command) grid.

**Acceptance Scenarios**:
1. **Given** the narrowed gates, **When** a source prompt changes, **Then** at most one canonical snapshot needs
   regeneration plus structural-invariant assertions (agent count, per-agent cardinality, arg-placeholder
   presence, path resolution) still hold.
2. **Given** the narrowing, **When** the full compliance suite runs, **Then** no drift-detection coverage is
   lost (a genuinely wrong render is still caught by the canonical snapshot + invariants).

---

### User Story 6 — Baselines re-homed to the module partition (Priority: P3)

As a **maintainer**, I want the completeness baselines that assume the current test partition relocated to match
the module-owned split, so every relocated test still resolves to exactly one CI home.

**Why this priority**: Follows mechanically from the module split; the last consolidation step.

**Independent Test**: After relocation, `test_marker_job_completeness.py` and the collection-completeness oracle
pass; golden-count assertions and path filters point at the new homes.

**Acceptance Scenarios**:
1. **Given** relocated fixtures/tests, **When** the marker/collection completeness oracles run, **Then** every
   relocated test resolves to exactly one CI gate (no double-marker CI-home trap).
2. **Given** the module partition, **When** the golden-count and path-filter assertions run, **Then** they
   reference the module-owned homes and pass.

### Edge Cases

- **Fork PR with a maintainer PAT absent/expired**: labeled run must fail closed with a clear message, never
  silently no-op or leak the token.
- **A module workflow ever gets sharded** (e.g. doctrine): `${{ matrix.shard }}` suffix must keep
  `coverage-*.xml` names unique so aggregation never collides.
- **`unmatched` fail-closed catch-all**: a `src/**` change matching no named path group must still force the
  module jobs to run (preserve current fail-closed behavior).
- **Version-pin drift**: if a future change bumps one render version, the shared constant must move both the
  fixtures and `regen` together — a divergence must fail a test, not silently mismatch.
- **Coverage filename rename**: any rename of a `coverage-*.xml` or `<slug>-reports` artifact silently drops it
  from aggregation — guard with an assertion that the aggregated set matches the module inventory.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Kernel reusable workflow (`module-kernel.yml`, `on: workflow_call`) invoked as ordered `uses:` job in ci-quality, same job id + gate | US1 | High | Open |
| FR-002 | Kernel `coverage-kernel.xml` / `kernel-test-reports` aggregate into the single run's `diff-coverage` + `sonarcloud` with names unchanged | US1 | High | Open |
| FR-003 | `spec-kitty regen` write-mode regenerates the 144 command baselines + 24 skill snapshots from source templates, reusing `render_command_template()` + `command_renderer.render().to_skill_md()` | US2 | High | Open |
| FR-004 | `spec-kitty regen --check [--json]` renders to memory/tempdir, byte-diffs vs committed fixtures, exits non-zero on drift with offending paths + unified diff + `Run: spec-kitty regen` | US2 | High | Open |
| FR-005 | Shared version-pin constant(s) imported by both the fixture tests and `regen` (single source of truth replacing the divergent `3.1.2a3` / `3.0.0` pins) | US2 | High | Open |
| FR-006 | Doctrine reusable workflow (fast + integration legs; `src/doctrine` + `src/charter`), coverage names preserved | US3 | Medium | Open |
| FR-007 | Packs reusable workflow (lift `fast-tests-corpus`), `coverage-fast-corpus.xml` preserved | US3 | Medium | Open |
| FR-008 | Architectural CI-model guards updated to tolerate `uses:` caller jobs (job-graph, path-filter, coverage-root, release-ownership parsers) | US3 | Medium | Open |
| FR-009 | Regen CI workflow auto-commits regenerated fixtures on same-repo push / `workflow_dispatch` (bot identity, `contents: write`, same-repo guard) | US4 | Medium | Open |
| FR-010 | Regen CI runs check-only on fork PRs, failing with the followable remediation message | US4 | Medium | Open |
| FR-011 | `regen`-label privileged workflow pushes regen commits into the fork branch via least-privilege maintainer PAT, `pull_request_target` trusted-tooling pattern | US4 | Medium | Open |
| FR-012 | Narrow twelve-agent + command_renderer gates to structural invariants + one canonical snapshot | US5 | Medium | Open |
| FR-013 | Re-home baselines (golden counts, CI path filters, marker/shard maps) to the module-owned partition; every relocated test resolves to exactly one CI home | US6 | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No coverage regression | The count of `coverage-*.xml` files aggregated by `diff-coverage` + `sonarcloud` after the refactor is >= the pre-refactor count; no module coverage is dropped | Reliability | High | Open |
| NFR-002 | Wall-clock neutral | Module extraction adds no serial cross-run gate; total ci-quality wall-clock stays within ~5% of the pre-refactor baseline (reusable workflows run same-run) | Performance | Medium | Open |
| NFR-003 | PAT-push security | The labeled PAT-push workflow never executes PR-supplied code, uses a least-privilege PAT, and records a security-review sign-off before it is enabled | Security | High | Open |
| NFR-004 | One-command fix | A source-prompt edit is resolvable by exactly one documented command (`spec-kitty regen`); the check-only failure names it verbatim | DevEx | High | Open |
| NFR-005 | Regen fidelity | `spec-kitty regen` output is byte-identical to a `PYTEST_UPDATE_SNAPSHOTS=1` pytest run for every one of the 168 fixtures | Correctness | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No red merge-blocking gate | No new merge-blocking gate lands red (red-main policy, ADR 2026-07-17-1); new gates land green or non-blocking | Technical | High | Open |
| C-002 | Shared Package Boundary | No build gate requires wheel publication; per-package `pyproject.toml`s stay dormant; this is a test-partition + workflow split (ADR 2026-04-25-1, wheel cutover governed by ADR 2026-08-02-1) | Technical | High | Open |
| C-003 | Fork token read-only | Fork PR `GITHUB_TOKEN` is read-only; no commit-back to forks except via the explicit label→PAT path | Technical | High | Open |
| C-004 | Preserve artifact names | `coverage-*.xml` and `<slug>-reports` names are preserved (aggregators discover by glob, not by job name) | Technical | High | Open |
| C-005 | Required check stability | `quality-gate` remains the pinned required check; `uses:`-induced inner check-name changes must not break branch protection | Technical | High | Open |
| C-006 | Canonical sources | Reuse existing render entrypoints; model `regen` on `spec-kitty doctrine regenerate-graph --check`; no improvised render logic (DIRECTIVE_044) | Technical | High | Open |
| C-007 | Sonar scope unchanged | Preserve single-run coverage aggregation + `diff-coverage` PR gate; add no new Sonar PR decoration | Technical | Medium | Open |
| C-008 | ATDD / red-first | Each implementation WP lands a failing-first test proving the behaviour, RED on the planning base, GREEN on the WP's final commit (charter C-011) | Process | High | Open |
| C-009 | spec-internal deferred | `spec-internal` is not in-tree; it is out of scope and not scaffolded this mission | Business | Low | Open |

### Key Entities

- **Module**: an independently-owned CI unit (`kernel`, `doctrine`, `packs`) with source/test/coverage roots.
- **Module Workflow**: a `module-<id>.yml` (`on: workflow_call`) invoked as an ordered `uses:` job in ci-quality.
- **Coverage Artifact**: per-run `<slug>-reports` holding `coverage-*.xml`, glob-discovered by the aggregators.
- **Fixture Set**: the 144 command baselines + 24 skill snapshots rendered from source `prompt.md` templates.
- **Regen Tool**: `spec-kitty regen [--check] [--json]` (write / check modes).
- **Regen Workflow**: trust-tiered CI (same-repo auto-commit / fork check-only / label→PAT-push).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The kernel POC merges with `module-kernel.yml` (`on: workflow_call`) invoked from ci-quality, and
  `coverage-kernel.xml` is demonstrably present in `diff-coverage`'s discovered set and the nightly Sonar scan —
  produced in a single run.
- **SC-002**: `spec-kitty regen` regenerates all 168 fixtures byte-identically to a `PYTEST_UPDATE_SNAPSHOTS=1`
  pytest run (regression-proven, NFR-005).
- **SC-003**: An edited source prompt + `spec-kitty regen` yields a green gate; the same edit without regen
  fails `--check` with the exact remediation command in the message.
- **SC-004**: All three modules run as reusable workflows, full ci-quality is green, no coverage regression
  (NFR-001), and the architectural CI-model guards pass.
- **SC-005**: After gate narrowing, a one-line source-prompt edit requires regenerating at most one canonical
  snapshot instead of ~14 fixture files (measurable churn reduction).
- **SC-006**: A fork PR with drift fails check-only with the followable message; a `regen`-labeled run pushes
  the regen commit into the fork branch (after the NFR-003 security sign-off).
