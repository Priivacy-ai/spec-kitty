---
work_package_id: WP09
title: Per-Module CI Job Split and Path Filter
dependencies:
- WP06
- WP07
- WP08
requirement_refs:
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- FR-012
- FR-013
planning_base_branch: feat/079-ci-hardening-and-lint-cleanup
merge_target_branch: feat/079-ci-hardening-and-lint-cleanup
branch_strategy: Planning artifacts for this feature were generated on feat/079-ci-hardening-and-lint-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/079-ci-hardening-and-lint-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T042
- T043
- T044
- T045
- T046
- T047
- T048
- T049
- T050
history:
- date: '2026-04-09'
  action: created
  actor: claude-sonnet-4-6
authoritative_surface: .github/workflows/ci-quality.yml
execution_mode: code_change
owned_files:
- .github/workflows/ci-quality.yml
tags: []
---

# WP09 — Per-Module CI Job Split and Path Filter

## Objective

Replace the monolithic `fast-tests-core` and `integration-tests-core` jobs in
`.github/workflows/ci-quality.yml` with per-module job pairs organised in the verified
import-graph DAG. Add workflow-level path filtering for docs-only skip. Add per-module
`if:` path conditions via `dorny/paths-filter`. Add skip-pass shim jobs for branch
protection required checks.

After this WP, every module in the system has its own dedicated CI job pair, the DAG
encodes verified import dependencies, and docs-only PRs skip Python test execution entirely.

## Context

**Why this WP exists:** The monolithic test jobs mean a 1-line change to `dashboard.py`
triggers the entire suite. FR-004–FR-009 mandate per-module job pairs with accurate
dependency ordering.

**DAG from research.md R-01 (import-verified):**
```
Tier 0 (no intra-specify_cli deps): sync, merge, missions, post_merge, release
Tier 1 (depends on Tier 0):        status ← sync
Tier 2 (depends on Tier 1):        review ← status
                                    next ← status
                                    lanes ← merge, status
                                    dashboard ← status, sync
                                    upgrade ← status
Tier 3 (orchestrators):             cli ← [all Tier 2]
                                    orchestrator_api ← cli, lanes, merge, status
```

**CRITICAL architectural note:** Alphonso's original "next/review before merge" assumption
was INCORRECT per import analysis. `merge` has no imports from `next` or `review`.
`merge` is a Tier 0 module (leaf). The DAG above is the verified ground truth.

**Doctrine:** DIRECTIVE_001 (architectural integrity — CI DAG must match architectural
boundaries), `test-boundaries-by-responsibility`, `no-parallel-duplicate-test-runs`.

**This WP is part of Batch 3 (sequential after Batch 2).**

## Subtask Guidance

### T042 — Add workflow-level `paths:` trigger for docs-only skip

**File:** `.github/workflows/ci-quality.yml`

Read the current `on:` section of the workflow. Modify it to add `paths:` filters so the
entire workflow is skipped for documentation-only changes:

```yaml
on:
  pull_request:
    branches: [main, develop, "2.x"]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'pyproject.toml'
      - '.github/workflows/ci-quality.yml'
  push:
    branches: [main, develop, "2.x"]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'pyproject.toml'
      - '.github/workflows/ci-quality.yml'
```

This satisfies FR-010 (docs-only PR does not trigger Python test jobs) and NFR-001 (≤2 min
for docs-only PRs).

**Important:** After adding this filter, markdownlint and commitlint must still run on
docs-only PRs. Check whether those jobs live in a SEPARATE workflow file (e.g.,
`docs-quality.yml`). If they are in `ci-quality.yml` as well, you must NOT filter them with
the `paths:` block — move them to a separate workflow first, or restructure the `on:` block
to use `paths-ignore:` for those jobs only.

---

### T043 — Add `changes` detection job using `dorny/paths-filter`

**File:** `.github/workflows/ci-quality.yml`

Add a new job at the top of the jobs section:

```yaml
jobs:
  changes:
    runs-on: ubuntu-latest
    outputs:
      sync: ${{ steps.filter.outputs.sync }}
      merge: ${{ steps.filter.outputs.merge }}
      missions: ${{ steps.filter.outputs.missions }}
      post_merge: ${{ steps.filter.outputs.post_merge }}
      release: ${{ steps.filter.outputs.release }}
      status: ${{ steps.filter.outputs.status }}
      review: ${{ steps.filter.outputs.review }}
      next: ${{ steps.filter.outputs.next }}
      lanes: ${{ steps.filter.outputs.lanes }}
      dashboard: ${{ steps.filter.outputs.dashboard }}
      upgrade: ${{ steps.filter.outputs.upgrade }}
      cli: ${{ steps.filter.outputs.cli }}
      orchestrator_api: ${{ steps.filter.outputs.orchestrator_api }}
      core_misc: ${{ steps.filter.outputs.core_misc }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            sync:
              - 'src/specify_cli/sync/**'
              - 'tests/sync/**'
            merge:
              - 'src/specify_cli/merge/**'
              - 'tests/merge/**'
            missions:
              - 'src/specify_cli/missions/**'
              - 'tests/missions/**'
            post_merge:
              - 'src/specify_cli/post_merge/**'
              - 'tests/post_merge/**'
            release:
              - 'src/specify_cli/release/**'
              - 'tests/release/**'
            status:
              - 'src/specify_cli/status/**'
              - 'tests/status/**'
            review:
              - 'src/specify_cli/review/**'
              - 'tests/review/**'
            next:
              - 'src/specify_cli/next/**'
              - 'tests/next/**'
            lanes:
              - 'src/specify_cli/lanes/**'
              - 'tests/lanes/**'
            dashboard:
              - 'src/specify_cli/dashboard/**'
              - 'tests/dashboard/**'
            upgrade:
              - 'src/specify_cli/upgrade/**'
              - 'tests/upgrade/**'
            cli:
              - 'src/specify_cli/cli/**'
              - 'tests/cli/**'
            orchestrator_api:
              - 'src/specify_cli/orchestrator_api/**'
              - 'tests/orchestrator_api/**'
            core_misc:
              - 'src/charter/**'
              - 'src/kernel/**'
              - 'src/doctrine/**'
              - 'tests/charter/**'
              - 'tests/kernel/**'
              - 'tests/doctrine/**'
              - 'tests/policy/**'
```

---

### T044 — Define Tier 0 `fast-tests` jobs (sync, merge, missions, post_merge, release)

**Tier 0 jobs have no `needs:` from other per-module jobs.** They depend only on `changes`.

Template for each Tier 0 job:
```yaml
fast-tests-sync:
  needs: [changes]
  if: needs.changes.outputs.sync == 'true'
  runs-on: ubuntu-24.04
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.12'
    - run: pip install -e ".[dev]"
    - name: Run fast tests — sync
      run: pytest tests/sync/ -m fast -q --tb=short
```

Create this template for: `sync`, `merge`, `missions`, `post_merge`, `release`.

Adjust the `tests/<module>/` path and `--cov=src/specify_cli/<module>` for each module.

Note: `merge` is Tier 0 (leaf node) per the verified import graph. It does NOT need
`fast-tests-review` or `fast-tests-next` to complete first.

---

### T045 — Define Tier 1 `fast-tests-status` job

**Tier 1:** `status` depends on `sync`.

```yaml
fast-tests-status:
  needs: [changes, fast-tests-sync]
  if: |
    always() &&
    (needs.changes.outputs.status == 'true' || needs.changes.outputs.sync == 'true') &&
    needs.fast-tests-sync.result != 'failure'
  runs-on: ubuntu-24.04
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.12'
    - run: pip install -e ".[dev]"
    - name: Run fast tests — status
      run: pytest tests/status/ -m fast -q --tb=short
```

The `always() && ... != 'failure'` pattern ensures the job runs even if upstream was skipped
(due to path filter) but fails if upstream actually failed.

---

### T046 — Define Tier 2 `fast-tests` jobs (review, next, lanes, dashboard, upgrade)

**Tier 2 jobs need Tier 1 (`fast-tests-status`) to complete, and for `lanes`, also Tier 0 `fast-tests-merge`.**

```yaml
fast-tests-review:
  needs: [changes, fast-tests-status]
  if: |
    always() &&
    (needs.changes.outputs.review == 'true' || needs.changes.outputs.status == 'true') &&
    needs.fast-tests-status.result != 'failure'
  ...

fast-tests-next:
  needs: [changes, fast-tests-status]
  if: |
    always() &&
    (needs.changes.outputs.next == 'true' || needs.changes.outputs.status == 'true') &&
    needs.fast-tests-status.result != 'failure'
  ...

fast-tests-lanes:
  needs: [changes, fast-tests-status, fast-tests-merge]
  if: |
    always() &&
    (needs.changes.outputs.lanes == 'true' || needs.changes.outputs.status == 'true' || needs.changes.outputs.merge == 'true') &&
    needs.fast-tests-status.result != 'failure' &&
    needs.fast-tests-merge.result != 'failure'
  ...

fast-tests-dashboard:
  needs: [changes, fast-tests-status]
  ...

fast-tests-upgrade:
  needs: [changes, fast-tests-status]
  ...
```

Repeat the full steps block for each Tier 2 job (or use a reusable workflow to reduce
repetition if the team is comfortable with that).

---

### T047 — Define Tier 3 `fast-tests` jobs (cli, orchestrator_api, core-misc)

**Tier 3: cli depends on all Tier 2; orchestrator_api depends on cli, lanes, merge, status.**

```yaml
fast-tests-cli:
  needs: [changes, fast-tests-lanes, fast-tests-next, fast-tests-review, fast-tests-dashboard, fast-tests-upgrade]
  if: |
    always() &&
    needs.changes.outputs.cli == 'true' &&
    needs.fast-tests-lanes.result != 'failure' &&
    needs.fast-tests-next.result != 'failure' &&
    needs.fast-tests-review.result != 'failure' &&
    needs.fast-tests-dashboard.result != 'failure' &&
    needs.fast-tests-upgrade.result != 'failure'
  ...

fast-tests-orchestrator_api:
  needs: [changes, fast-tests-cli, fast-tests-lanes, fast-tests-merge, fast-tests-status]
  ...

fast-tests-core-misc:
  needs: [changes]
  if: needs.changes.outputs.core_misc == 'true'
  ...
  # tests: tests/charter/, tests/kernel/, tests/doctrine/, tests/policy/
```

---

### T048 — Add `integration-tests-<module>` job pairs with coverage floors

For each module, add a paired `integration-tests-<module>` job. These run `git_repo` and
`integration` marked tests, and apply the coverage floor from `coverage-baseline.md`.

**Template:**
```yaml
integration-tests-sync:
  needs: [changes, fast-tests-sync]
  if: |
    always() &&
    needs.changes.outputs.sync == 'true' &&
    needs.fast-tests-sync.result == 'success'
  runs-on: ubuntu-24.04
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.12'
    - run: pip install -e ".[dev]"
    - name: Run integration tests — sync
      run: |
        pytest tests/sync/ -m 'git_repo or integration or slow' -q --tb=short \
          --cov=src/specify_cli/sync --cov-fail-under=<FLOOR_FROM_BASELINE>
```

Replace `<FLOOR_FROM_BASELINE>` with the `Floor` column value from `coverage-baseline.md`
for each module. You must read `coverage-baseline.md` before writing this task.

Integration-tests jobs should only run if `fast-tests-<module>` passed (not skipped, not
failed). Use `result == 'success'` not `result != 'failure'`.

---

### T049 — Remove old monolithic jobs; update `report` and `quality-gate`

**Remove:**
- `fast-tests-core` job
- `integration-tests-core` job

**Update `report` job:**
Replace the `needs:` list with all new per-module job names:
```yaml
report:
  needs:
    - fast-tests-sync
    - fast-tests-merge
    - fast-tests-missions
    - fast-tests-post_merge
    - fast-tests-release
    - fast-tests-status
    - fast-tests-review
    - fast-tests-next
    - fast-tests-lanes
    - fast-tests-dashboard
    - fast-tests-upgrade
    - fast-tests-cli
    - fast-tests-orchestrator_api
    - fast-tests-core-misc
    - integration-tests-sync
    - integration-tests-merge
    # ... all integration-tests jobs
  if: always()
```

Same update for `quality-gate`.

---

### T050 — Add skip-pass shim jobs for required branch-protection check jobs

For each job that is currently a required branch-protection check, add a shim job that
passes when the module's path filter condition is false:

```yaml
fast-tests-sync-skip:
  needs: [changes]
  if: needs.changes.outputs.sync != 'true'
  runs-on: ubuntu-latest
  steps:
    - run: echo "Skipped — no sync changes detected"
```

**Pre-condition:** Before writing shim jobs, confirm with the repository owner which job
names are in the branch protection required checks list. Only those jobs need shims.

If you cannot confirm the list before implementation: add shim jobs for ALL per-module jobs
as a safe default — a shim that passes on a skip is harmless, and failing to add one for a
required check blocks all PRs.

**Commit** the changes once the workflow YAML is syntactically valid and all subtasks above
are complete. Use:
```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci-quality.yml'))"
```
to verify YAML syntax before committing.

## Definition of Done

- [ ] `ci-quality.yml` has workflow-level `paths:` trigger filtering out docs-only changes
- [ ] `changes` job with `dorny/paths-filter` defines per-module output variables
- [ ] All 13+ module clusters have a `fast-tests-<module>` job with correct DAG `needs:`
- [ ] All 13+ module clusters have an `integration-tests-<module>` job with `--cov-fail-under=<floor>`
- [ ] `fast-tests-core` and `integration-tests-core` are removed
- [ ] `report` and `quality-gate` jobs list all new per-module job names in `needs:`
- [ ] Skip-pass shim jobs added for all required-check jobs
- [ ] YAML parses without error
- [ ] **NFR-002 validated:** Open a draft PR touching only `src/specify_cli/dashboard/` (or any single module); confirm all relevant CI jobs complete within 5 minutes from push to `quality-gate` passing
- [ ] Changes committed to `feat/079-ci-hardening-and-lint-cleanup`

## Risks

- **DAG `if:` condition complexity:** GitHub Actions `if:` expressions with `always()` and
  multiple `needs.X.result` checks are error-prone. Test the YAML locally with
  `act` or by opening a draft PR before merging.
- **`dorny/paths-filter` output key naming:** Output keys cannot contain `/` or `-` — use
  `_` for modules with dashes (e.g., `post_merge` not `post-merge`).
- **Branch protection breaks:** If a required check is renamed or removed without a shim,
  all PRs are immediately blocked. Add shim jobs conservatively (all modules) if uncertain.
- **CI matrix explosion in `report`/`quality-gate`:** `needs:` arrays with 25+ jobs are
  valid in GitHub Actions but may be slow to resolve. This is acceptable for now.

## Reviewer Guidance

Read the `ci-quality.yml` diff carefully against the DAG diagram in the plan. Verify that:
(a) `merge` is Tier 0 (no dependency on `review` or `next`),
(b) `status` depends on `sync` only,
(c) `lanes` depends on `merge` AND `status`.
Any other dependency encoding is a violation of the verified import graph.
