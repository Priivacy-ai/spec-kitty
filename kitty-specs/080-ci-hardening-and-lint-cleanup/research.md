# Research: CI Hardening and Lint Cleanup (Mission 079)

**Date:** 2026-04-09
**Status:** Complete — all spec assumptions verified, no NEEDS CLARIFICATION markers remain

---

## R-01: Module Dependency Graph

**Decision:** The CI job DAG for the per-module split (FR-007) is derived from Python import
analysis of `src/specify_cli/`. The graph below is the ground truth for job ordering.

**Method:** `ast.parse` over every `.py` file in each module directory, collecting
`from specify_cli.<module> import ...` references.

**Findings:**

```
Tier 0 — no intra-specify_cli dependencies:
  sync         (leaf: no deps)
  merge        (leaf: no deps)
  missions     (leaf: no deps)
  post_merge   (leaf: no deps)
  release      (leaf: no deps)

Tier 1 — depends on Tier 0:
  status       ← sync

Tier 2 — depends on Tier 1:
  review       ← status
  next         ← status, charter
  lanes        ← merge, status
  dashboard    ← status, sync
  upgrade      ← status

Tier 3 — orchestrators (depend on many Tier 2):
  cli          ← charter, dashboard, lanes, merge, next, post_merge,
                  release, review, status, sync, upgrade
  orchestrator_api ← cli, lanes, merge, status
```

**Note on Alphonso's assessment:** Alphonso stated "next and review before merge" as an
assumed dependency. The import graph shows `merge` has no imports from `next` or `review` at
the code level. The semantic dependency (merge conceptually follows review) does not require
CI ordering. The actual ordering constraint is `sync → status → {review, next, lanes, dashboard, upgrade}`.

**Rationale:** Import-graph ordering ensures that if a dependency module is broken, the CI
system signals failure at the lowest possible tier before running dependent jobs.

**Alternatives considered:**
- Runtime call-graph analysis (more complete but requires instrumentation; import graph is sufficient for CI ordering)
- Manual specification (error-prone; import graph is deterministic and can be regenerated)

---

## R-02: Module Tier Classification for Coverage Floors

**Decision:** Three-tier classification determines coverage floor targets. Floors are set to
the actual measured baseline at the time WP06 runs, subject to tier minimums.

**Tier definitions:**

| Tier | Description | Minimum floor | Rationale |
|------|-------------|--------------|-----------|
| **Essential** (A) | State machines and foundational contracts used by ≥3 other modules | 75% | Failures propagate widely; regressions are high-cost |
| **Normal** (B) | Core feature modules with bounded scope | 60% | Meaningful coverage without over-constraining early-stage modules |
| **Glue** (C) | Adapters, facades, thin CLI wrappers | 40% | High integration coverage; unit coverage less critical |

**Module classification:**

| Module | Tier | Rationale |
|--------|------|-----------|
| `status` | A — Essential | Used by review, next, lanes, dashboard, upgrade, cli (6 dependents); state machine is critical |
| `lanes` | A — Essential | Encodes the core WP lifecycle transitions; used by cli and orchestrator_api |
| `kernel` | A — Essential | Foundational utilities (atomic writes, safe_re); used across all packages |
| `sync` | A — Essential | Event persistence backbone; corruptions are irreversible |
| `next` | B — Normal | Mission runtime loop; complex logic, bounded scope |
| `review` | B — Normal | Review workflow; complex state interactions |
| `merge` | B — Normal | Merge execution; high-risk but well-bounded |
| `cli` | B — Normal | CLI command layer; integration-heavy |
| `missions` | B — Normal | Mission template system; template-heavy |
| `upgrade` | B — Normal | Migration logic; data integrity sensitive |
| `dashboard` | C — Glue | REST API facade over status/sync |
| `release` | C — Glue | Release packaging; thin wrapper |
| `orchestrator_api` | C — Glue | External API adapter; integration-tested via e2e |
| `post_merge` | C — Glue | Static AST analysis helper; narrow scope |
| `core-misc` | C — Glue | Residual utilities, validators, shims |

**Floor calibration process (WP06):**
1. Run `pytest --cov=src/specify_cli/<module> tests/<module>/ -m 'fast or git_repo or slow or integration or e2e'`
   for each module cluster (all tiers, aggregate coverage)
2. Record actual coverage percentage per module
3. Set floor to `max(tier_minimum, actual_coverage - 2%)` — the `-2%` buffer accounts for
   natural test-run variance while not locking in a floor above what already exists

**Rationale:** A floor set to actual coverage is a "do not regress" gate, not a "add more
tests" gate. Tightening is a follow-up mission concern.

---

## R-03: Test Tier Distribution and Shift-Left Opportunities

**Decision:** A shift-left WP (WP08) is warranted. The `tests/next/` and `tests/missions/`
directories have a disproportionate ratio of `git_repo` tests relative to `fast` tests.

**Current observed distribution (sampled):**

| Module | fast | git_repo | slow/integ | unlabeled (test files) |
|--------|------|----------|-----------|----------------------|
| sync | 49 | 2 | 0 | 59 files |
| upgrade | 28 | 3 | 1 | 36 files |
| next | 4 | 5 | 0 | 7 files |
| missions | 6 | 7 | 0 | 20 files |
| test_dashboard | 7 | 0 | 0 | 9 files |
| merge | 2 | 1 | 0 | 7 files |
| review | 0 | 0 | 0 | 6 files |
| lanes | 0 | 0 | 0 | 12 files |
| cli | 0 | 0 | 0 | 3 files |
| release | 5 | 1 | 0 | 3 files |
| post_merge | 0 | 0 | 0 | 1 file |

**Observations:**
- `review` and `lanes` have zero marked tests despite 12 and 6 test files respectively.
  All tests in these modules are unmarked — they will not run in any marker-scoped CI job
  until FR-016 (marker cataloguing) is done.
- `next` has more `git_repo` tests than `fast` tests — a 5:4 ratio despite `next` containing
  decision logic that should be unit-testable.
- `missions` has a 7:6 git_repo-to-fast ratio. Template loading and rendering logic is
  often unit-testable without a real git repo.
- `merge` has only 3 fast/git_repo marked tests across 7 test files — likely heavily unlabelled.

**Shift-left candidates (FR-017 scope):**
- `tests/next/` — tests that assert on decision outcomes (not git state) can use `tmp_path` + YAML files instead of `git init`
- `tests/missions/` — tests that assert on rendered template content can mock the filesystem instead of real git worktrees
- `tests/lanes/` and `tests/review/` — must be classified first (FR-016) before shift-left is possible

**Doctrine reference:** Tactic `test-pyramid-progression` — "Run tests bottom-up through
pyramid layers to get fast feedback." Current unlabelled and git_repo-heavy tests violate
this principle by forcing `git init` overhead on logic that does not require it.

**Rationale:** Shifting 3–5 git_repo tests to fast per module reduces per-module CI time by
~30–90 seconds per test (git subprocess overhead) and lowers the barrier to running the
suite locally.

---

## R-04: CI Path Filter Mechanism

**Decision:** Use a two-layer approach:
1. **Workflow-level `paths:` trigger** on `ci-quality.yml` for the coarse docs-vs-code split
2. **`dorny/paths-filter@v3` action** at the job level for per-module gating within code PRs

**Rationale:**
- Workflow-level `paths:` is simpler and more reliable for the "skip everything" case (pure docs)
- `dorny/paths-filter` is the established standard for per-job conditional execution; it is
  already referenced in issue #548 and is widely used in the GitHub Actions ecosystem
- A hybrid approach avoids the fragility of a single coarse filter while keeping the docs-only
  case cheap

**Branch protection implication (C-001):**
When a job is skipped at the workflow trigger level (`paths:` filter), GitHub marks the check
as "skipped" which satisfies required status checks. When a job is skipped at the job level
via `if: needs.changes.outputs.module == 'false'`, GitHub also treats it as passing for
required checks — but only if the job definition includes an `if:` condition at the top level
(not nested inside a step). Skip-pass shim jobs are still recommended for safety.

**Alternatives considered:**
- Pure `paths:` at workflow level only (loses per-module granularity within code PRs)
- `tj-actions/changed-files` (viable but less commonly used in this context than dorny)
- Manual `git diff` in a setup step (fragile, harder to maintain)

---

## R-05: Existing CI Lint Job Structure

**Finding:** The current `lint` job in `ci-quality.yml` already uses commit-range-aware
markdown and ruff/mypy execution (runs only on changed files within the PR range). The
`ruff` and `mypy` steps produce artifacts uploaded as `lint-failure-details`.

**Implication for WP01–WP05:** Once violations are fixed on `main`, the lint job will report
clean on subsequent PRs. The job does not need structural changes in this mission — it already
has the right shape. WP01–WP05 are purely source code fixes.

**Finding:** The `lint` job already has the infrastructure to post PR feedback comments via
the `lint-feedback` job. This job currently posts ruff and mypy failures as PR comments,
which is the right UX. No changes needed to that flow.

---

## R-06: Doctrine Artifacts

The following doctrine artifacts are directly applicable to this mission and must be referenced
in WP acceptance criteria:

| Artifact | Type | Relevance |
|----------|------|-----------|
| `DIRECTIVE_030` — Test and Typecheck Quality Gate | Directive | Mandates that ruff/mypy must pass before handoff; directly governs WP01–WP05 |
| `DIRECTIVE_025` — Boy Scout Rule | Directive | Governs WP02 (E402 cleanup goes beyond the minimum required fix) |
| `DIRECTIVE_034` — Test-First Development | Directive | Governs WP08 (shift-left refactors must not break existing test coverage) |
| `DIRECTIVE_001` — Architectural Integrity Standard | Directive | Governs CI DAG design in WP07 (structure must match architectural boundaries) |
| `test-pyramid-progression` | Tactic | Test execution order for per-module jobs; bottom tier first |
| `testing-select-appropriate-level` | Tactic | Criteria for classifying shift-left candidates (WP08) |
| `test-boundaries-by-responsibility` | Tactic | Per-module job scoping (each job tests its own boundary, not its dependencies) |
| `quality-gate-verification` | Tactic | Post-WP validation: coverage floor checks before merge |
| `no-parallel-duplicate-test-runs` | Tactic | Ensure that after the split, no test runs twice across jobs |

---

## R-07: Charter Compliance Check

Charter requirements and how this mission satisfies them:

| Requirement | Mission handling |
|-------------|-----------------|
| mypy --strict must pass | WP01–WP05 bring `main` to zero mypy errors (NFR-003) |
| 90%+ coverage for new code | New CI code (workflow YAML) has no coverage gate; new Python test code in WP08 must meet the charter threshold |
| CLI operations < 2 seconds | No runtime behavior changed; not applicable |
| Terminology canon: `--mission` not `--feature` | No CLI changes in this mission; not applicable |

**No charter violations identified.**
