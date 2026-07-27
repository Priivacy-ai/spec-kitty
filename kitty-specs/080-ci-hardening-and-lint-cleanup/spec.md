# Mission 079: CI Hardening and Lint Cleanup

**Mission type:** software-dev
**Status:** draft
**Target branch:** main
**Architect assessment:** `work/079-alphonso-assessment.md`
**Related issues:** #548 (path-based CI filtering), #549 (per-module CI job split)

---

## Overview

The spec-kitty codebase currently carries three classes of accumulated technical debt that each
raise the cost of every pull request:

1. **Static analysis violations** — ruff style/quality violations and mypy type errors are
   reported by CI on every run but never fixed. They accumulate noise in CI feedback, make the
   lint gate meaningless, and obscure new regressions introduced by contributors.

2. **Monolithic CI test jobs** — `fast-tests-core` and `integration-tests-core` run the entire
   `src/specify_cli/` surface as a single undifferentiated unit. A one-line change to the
   dashboard triggers the merge suite, the sync suite, the review suite, and more. Every
   contributor pays the full cost regardless of what they touched.

3. **Lack of CI path awareness** — CI jobs run unconditionally on every PR, even when only
   documentation files changed. A 21-line ADR commit consumed 4+ minutes of CI time across jobs
   that had zero relevance to the change.

This mission resolves all three problems in dependency order: lint/type correctness first,
then CI structure, then CI path filtering.

---

## Problem Statement

### Lint and Type Violations

The codebase has open ruff and mypy violations that CI reports but does not enforce. This means:

- The lint job is advisory, not authoritative — contributors cannot trust it as a quality gate
- New violations introduced by PRs are masked in a sea of pre-existing noise
- The `dossier` test suite is testing the wrong data shape (mypy reveals schema drift between
  the tests and the current `MissionDossier`/`ArtifactRef` dataclass signatures)
- Several files contain stale `# type: ignore` suppressions that no longer correspond to real
  errors, creating false confidence

### Monolithic Test Jobs

All modules in `src/specify_cli/` are tested as one unit. This produces:

- Slow CI feedback for targeted changes (a reviewer changing one file waits for 12 unrelated modules)
- No path to per-module filtering because there are no per-module targets to filter against
- No per-module coverage floors, so a module with 0% coverage can hide behind a high-coverage neighbor

### Missing Path Awareness

CI runs unconditionally. This produces:

- Full suite execution on documentation-only commits
- No ability to skip the Python test runner for Markdown/ADR changes
- Required checks defined against monolithic jobs — any future split must coordinate with branch
  protection settings to avoid blocking legitimate PRs

---

## Goals

1. Bring the codebase to a clean ruff + mypy baseline so the lint gate is authoritative
2. Split CI test jobs along functional module boundaries so each module has its own fast + integration job pair
3. Add path-aware triggering so documentation-only commits bypass Python test execution
4. Ensure all changes respect internal module dependency ordering (modules that depend on others must not be split in an order that breaks their dependency chain)
5. Coordinate branch protection required-check updates so no PR is blocked during or after the transition

---

## Actors

| Actor | Role |
|-------|------|
| **Contributor** | Developer opening a PR; affected by CI job scope and feedback quality |
| **Reviewer** | Approves PRs; relies on CI gate accuracy to know what was checked |
| **Maintainer** | Manages branch protection rules and required checks |
| **CI system** | Executes jobs; subject to path filter and module split configuration |

---

## User Scenarios

### Scenario A — Contributor opens a code PR touching one module

A contributor changes a file in `src/specify_cli/merge/`. Under the current system, all
12+ module clusters run. After this mission:
- Only the `merge` module's fast + integration jobs run automatically
- The contributor gets focused feedback within the merge module's coverage scope
- If `merge` depends on `review` and `next`, those jobs also run (dependency-ordered triggering)
- Unrelated modules (dashboard, sync, release) are skipped

### Scenario B — Contributor opens a docs-only PR

A contributor adds an ADR or updates `docs/`. Under the current system, the full test suite
runs. After this mission:
- Python test and lint jobs are skipped
- Only markdownlint and commitlint run
- Required checks are satisfied via skip-pass shim jobs so branch protection is not blocked

### Scenario C — Reviewer reads the lint job output

A reviewer looks at the lint CI job for a new PR. Under the current system, the output contains
hundreds of pre-existing violations masking any new ones. After this mission:
- The ruff and mypy reports contain only violations introduced by the PR under review
- The lint gate is authoritative: a clean run means the code is clean

### Scenario D — Contributor adds a new test to an existing module

A contributor adds a test to `tests/review/`. The per-module job for `review` runs. Coverage
for that module is computed independently against a calibrated floor for the review module.

---

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|------------|--------|
| FR-001 | All ruff violations present on `main` at mission start must be resolved: ARG001 in `catalog.py`, SIM108 in `resolver.py`, B009 in `glossary_hook.py`, SIM105 in `_safe_re.py`, E402/UP035/F401 cluster in `acceptance.py` | proposed |
| FR-002 | All mypy errors present on `main` at mission start must be resolved: dossier test schema drift (call-arg mismatches in `test_snapshot.py`), stale `# type: ignore` comments across 8 files, bare generic types in `state_contract.py`, `acceptance_matrix.py`, `doctrine/missions/repository.py`, and migration files, `no-any-return` violations in `version_utils.py`, `upgrade/feature_meta.py`, `policy/audit.py`, and `doctrine/missions/repository.py`, missing return type annotations in `sync/config.py`, type incompatibility in `merge/conflict_resolver.py`, and incompatible assignment in `cli/commands/materialize.py` | proposed |
| FR-003 | The `requests` library type stubs must be added as a development dependency so mypy can type-check `sync/body_transport.py` without errors | proposed |
| FR-004 | The CI workflow must define a dedicated fast-tests job and integration-tests job for each of the following module clusters: `dashboard`, `merge`, `review`, `sync`, `next`, `lanes`, `upgrade`, `missions`, `cli`, `post_merge`, `release`, `orchestrator_api`, and a residual `core-misc` cluster | proposed |
| FR-005 | Each per-module CI job must scope its test invocation only to that module's source and test paths; it must not run tests for other modules | proposed |
| FR-006 | Each per-module CI job must have an independently configured coverage floor appropriate to that module's current coverage level | proposed |
| FR-007 | The CI job DAG must express the verified import-graph dependency ordering between module clusters. The authoritative structure (from research.md R-01) is: `sync` (Tier 0, leaf) → `status` (Tier 1) → `{review, next, lanes, dashboard, upgrade}` (Tier 2) → `{cli, orchestrator_api}` (Tier 3). `merge` is a Tier 0 leaf node with no dependencies on `next` or `review`. All DAG edges must be derived from the verified import graph, not assumed. | proposed |
| FR-008 | The monolithic `fast-tests-core` and `integration-tests-core` jobs must be replaced by the per-module jobs; they must not run alongside the new jobs | proposed |
| FR-009 | The `report` and `quality-gate` jobs must be updated to collect results from all new per-module jobs | proposed |
| FR-010 | A documentation-only PR (changes limited to `*.md`, `architecture/**`, `docs/**`, `kitty-specs/**`) must not trigger Python test jobs, ruff, or mypy | proposed |
| FR-011 | A documentation-only PR must still trigger markdownlint and commitlint | proposed |
| FR-012 | A PR touching only `src/kernel/` must not trigger per-module jobs for other modules | proposed |
| FR-013 | Skip-pass shim jobs must be added for any per-module job that is a required branch-protection check, so that PRs where those jobs are skipped are not blocked | proposed |
| FR-014 | The `orchestrator-boundary.yml` workflow must add a path filter so it only runs when `src/specify_cli/orchestrator_api/**` is touched | proposed |
| FR-015 | The `check-spec-kitty-events-alignment.yml` workflow must add a path filter so it only runs when `src/specify_cli/sync/**`, `pyproject.toml`, or the events package version changes | proposed |
| FR-016 | All test files in per-module test directories must have at least one pytest marker applied (`fast`, `git_repo`, `slow`, `integration`, or `e2e`); unmarked test functions must be catalogued before the CI job split so coverage accounting is accurate | proposed |
| FR-017 | Tests in `tests/next/` and `tests/missions/` currently marked `git_repo` that do not require a real git repository (i.e., they only need filesystem isolation) must be identified; any confirmed shift-left candidate must be re-marked `fast` and refactored to remove the git subprocess dependency | proposed |

### Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|------------|-----------|--------|
| NFR-001 | A documentation-only PR must not spend more than 2 minutes in CI (markdownlint + commitlint only) | ≤ 2 minutes total CI wall-clock time | proposed |
| NFR-002 | A PR touching a single module cluster must complete CI in under 5 minutes from push to all relevant jobs finishing | ≤ 5 minutes for single-module PRs | proposed |
| NFR-003 | After the ruff/mypy cleanup (FR-001/FR-002), the lint job must report zero violations on `main` | 0 ruff violations, 0 mypy errors on `main` | proposed |
| NFR-004 | No existing passing test must be broken by the mypy fixes (dossier schema drift fixes must not change test behavior, only fix the call signatures to match the current data model) | 100% of previously passing tests remain passing | proposed |
| NFR-005 | Per-module coverage floors must be set no lower than 2 percentage points below the actual current coverage for that module; the 2% buffer accounts for natural test-run variance while still functioning as a "do not regress" gate | coverage_floor(module) ≥ current_coverage(module) − 2% | proposed |

### Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | Branch protection required checks must remain satisfied throughout the migration; no PR must be blocked during or after the CI job split | proposed |
| C-002 | The lint fixes (FR-001/FR-002) must be delivered before the CI job split (FR-004/FR-008) so coverage floors are computed against a clean baseline | proposed |
| C-003 | Module dependency order (FR-007) must be determined from runtime code inspection, not assumed; the implementation agent must verify import/call graphs before defining DAG edges | proposed |
| C-004 | Auto-fixable ruff violations must be fixed using the tool's own fix mode, not manual edits, to avoid introducing new issues | proposed |
| C-005 | `# type: ignore` removals must be verified to not re-introduce the original error (each removal must be tested with a mypy run targeting that file) | proposed |
| C-006 | The `requests` stubs (FR-003) must be added only to the development dependency group, not the runtime dependencies | proposed |
| C-007 | The dossier test fixes (FR-002, schema drift) must align to the current production signatures of `MissionDossier` and `ArtifactRef`; they must not modify the production dataclasses themselves | proposed |

---

## Out of Scope

- Bandit security issues (the 1127 Low + 23 Medium issues reported by bandit are tracked via Sonar and managed separately)
- B608 SQL injection false positives in `sync/queue.py` (the parameterized queries are safe; this is annotated separately)
- Full mypy `--strict` compliance across all modules not listed in FR-002 (broader mypy cleanup is a future effort)
- CI performance beyond what the job split and path filtering deliver (no caching strategy changes, no parallelization beyond job DAG)
- Modifying the production behavior of any runtime module (this mission is quality/CI infrastructure only)

---

## Success Criteria

1. After all WPs are merged to `main`, `ruff check src/` reports zero violations
2. After all WPs are merged to `main`, `mypy --strict src/` reports zero errors for all files listed in FR-002
3. A docs-only PR (ADR markdown only) completes CI in under 2 minutes with only markdownlint and commitlint running
4. A PR touching only the `dashboard` module does not trigger the `merge`, `sync`, or `review` test jobs
5. The `merge` test job only starts after both `review` and `next` test jobs have passed
6. All currently passing tests continue to pass after the lint/type fixes are applied
7. The `quality-gate` job passes on a clean `main` after the full migration

---

## Dependencies and Assumptions

### External Dependencies

- GitHub branch protection settings must be updated in tandem with CI job renames (owner coordination required before WP07 merge)
- `dorny/paths-filter` action (or equivalent) available in the GitHub Actions marketplace

### Internal Dependencies (Execution Order)

```
WP01 (ruff auto-fix)  ─┐
WP02 (E402 root cause) ─┤─→ WP06 (CI job split) ─→ WP07 (path filtering)
WP03 (dossier schema)  ─┤
WP04 (stale ignores)   ─┤
WP05 (bare generics)   ─┘
```

WP01–WP05 are independent of each other and can be executed in parallel (separate lanes).
WP06 depends on WP01–WP05 being merged (clean baseline required for coverage floor calibration).
WP07 depends on WP06 (path filters need per-module job targets to be meaningful).

### Assumptions

- A1: Module runtime dependency graph (for FR-007) can be determined by inspecting import relationships in `src/specify_cli/`. The implementation agent for WP06 must verify this before encoding DAG edges.
- A2: Per-module coverage floors can be calibrated at low-but-honest values initially (e.g., the actual current coverage for that module) and tightened in a follow-up mission.
- A3: The `dossier/tests/test_snapshot.py` errors are caused by schema drift in `MissionDossier` and `ArtifactRef` dataclasses, not logic errors in the test scenarios themselves. If inspection reveals the tests are testing deprecated behavior, that is out of scope and must be escalated.
- A4: GitHub treats `paths`-filter skipped jobs as satisfying required checks. If a required check cannot be satisfied by a shim, it must be temporarily removed from branch protection before WP07 merges.
