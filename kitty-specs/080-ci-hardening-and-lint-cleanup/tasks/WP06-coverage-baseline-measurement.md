---
work_package_id: WP06
title: Measure Per-Module Coverage Baseline
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
requirement_refs:
- FR-006
planning_base_branch: feat/080-ci-hardening-and-lint-cleanup
merge_target_branch: feat/080-ci-hardening-and-lint-cleanup
branch_strategy: Planning artifacts for this feature were generated on feat/080-ci-hardening-and-lint-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/080-ci-hardening-and-lint-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
- T031
history:
- date: '2026-04-09'
  action: created
  actor: claude-sonnet-4-6
authoritative_surface: kitty-specs/080-ci-hardening-and-lint-cleanup/
execution_mode: planning_artifact
owned_files:
- kitty-specs/080-ci-hardening-and-lint-cleanup/coverage-baseline.md
tags: []
---

# WP06 — Measure Per-Module Coverage Baseline

## Objective

Run the full test suite (all markers) per module cluster and produce
`kitty-specs/080-ci-hardening-and-lint-cleanup/coverage-baseline.md` with measured coverage
percentages and calibrated per-module coverage floors.

This artifact is the input to WP09 (per-module CI job split) — the CI jobs will configure
`--fail-under=<floor>` based on the floors recorded here.

## Context

**Why this WP exists:** Per-module coverage floors cannot be set accurately without first
measuring what the current baseline is. Setting floors too high breaks CI; setting them too
low is meaningless. The `max(tier_minimum, measured - 2%)` formula provides floors that are
honest ("do not regress") rather than aspirational ("reach a new target").

**Dependency chain:** WP01–WP05 must be merged first so the baseline is measured against a
clean, passing codebase. Measuring before the lint/type fixes would produce an inaccurate
baseline (some tests may have been failing).

**Tier definitions (from research.md R-02):**

| Tier | Modules | Minimum floor |
|------|---------|--------------|
| Essential (A) | status, lanes, kernel, sync | 75% |
| Normal (B) | next, review, merge, cli, missions, upgrade | 60% |
| Glue (C) | dashboard, release, orchestrator_api, post_merge, core-misc | 40% |

**Floor formula:** `floor = max(tier_minimum, measured_coverage - 2)`

**Doctrine:** `quality-gate-verification` tactic, DIRECTIVE_030.

**This WP starts Batch 2 (sequential after Batch 1).** WP07 and WP08 depend on this WP
completing first.

## Subtask Guidance

### T027 — Measure aggregate coverage for Tier A modules (status, lanes, kernel, sync)

Run coverage measurement for each Tier A module. Use ALL test markers (not just `fast`) to
get the true aggregate coverage:

```bash
# status
pytest tests/status/ \
  --cov=src/specify_cli/status \
  -m 'fast or git_repo or slow or integration or e2e' \
  --cov-report=term-missing -q 2>&1 | tail -8

# lanes
pytest tests/lanes/ \
  --cov=src/specify_cli/lanes \
  -m 'fast or git_repo or slow or integration or e2e' \
  --cov-report=term-missing -q 2>&1 | tail -8

# kernel (note: kernel may live under src/kernel/, not src/specify_cli/kernel/)
pytest tests/kernel/ \
  --cov=src/kernel \
  -m 'fast or git_repo or slow or integration or e2e' \
  --cov-report=term-missing -q 2>&1 | tail -8

# sync
pytest tests/sync/ \
  --cov=src/specify_cli/sync \
  -m 'fast or git_repo or slow or integration or e2e' \
  --cov-report=term-missing -q 2>&1 | tail -8
```

Record the TOTAL coverage percentage for each module (the `TOTAL` line in the coverage report).

**Note on unlabelled tests (from research.md R-03):** `tests/lanes/` has zero marked tests.
Until WP07 adds markers, the `-m 'fast or git_repo ...'` filter will collect ZERO tests for
`lanes/`. For WP06's purposes, run WITHOUT the `-m` filter for `lanes/` and `review/`:
```bash
pytest tests/lanes/ --cov=src/specify_cli/lanes --cov-report=term-missing -q 2>&1 | tail -8
```
Flag this in `coverage-baseline.md` as "measured without marker filter (zero markers exist pre-WP07)".

---

### T028 — Measure aggregate coverage for Tier B modules (next, review, merge, cli, missions, upgrade)

```bash
# next
pytest tests/next/ --cov=src/specify_cli/next \
  -m 'fast or git_repo or slow or integration or e2e' \
  --cov-report=term-missing -q 2>&1 | tail -8

# review (use no marker filter — zero markers until WP07)
pytest tests/review/ --cov=src/specify_cli/review \
  --cov-report=term-missing -q 2>&1 | tail -8

# merge (use no marker filter — mostly unmarked)
pytest tests/merge/ --cov=src/specify_cli/merge \
  --cov-report=term-missing -q 2>&1 | tail -8

# cli (use no marker filter — zero markers)
pytest tests/cli/ --cov=src/specify_cli/cli \
  --cov-report=term-missing -q 2>&1 | tail -8

# missions
pytest tests/missions/ --cov=src/specify_cli/missions \
  -m 'fast or git_repo or slow or integration or e2e' \
  --cov-report=term-missing -q 2>&1 | tail -8

# upgrade
pytest tests/upgrade/ --cov=src/specify_cli/upgrade \
  -m 'fast or git_repo or slow or integration or e2e' \
  --cov-report=term-missing -q 2>&1 | tail -8
```

For any module where the marker-filtered run returns zero tests, fall back to running without
the `-m` filter and note it in `coverage-baseline.md`.

---

### T029 — Measure aggregate coverage for Tier C modules (dashboard, release, orchestrator_api, post_merge, core-misc)

```bash
# dashboard
pytest tests/dashboard/ --cov=src/specify_cli/dashboard \
  -m 'fast or git_repo or slow or integration or e2e' \
  --cov-report=term-missing -q 2>&1 | tail -8

# release
pytest tests/release/ --cov=src/specify_cli/release \
  -m 'fast or git_repo or slow or integration or e2e' \
  --cov-report=term-missing -q 2>&1 | tail -8

# orchestrator_api
pytest tests/orchestrator_api/ --cov=src/specify_cli/orchestrator_api \
  -m 'fast or git_repo or slow or integration or e2e' \
  --cov-report=term-missing -q 2>&1 | tail -8

# post_merge
pytest tests/post_merge/ --cov=src/specify_cli/post_merge \
  -m 'fast or git_repo or slow or integration or e2e' \
  --cov-report=term-missing -q 2>&1 | tail -8

# core-misc: residual modules not in dedicated dirs
# Find what tests exist for policy/, schemas/, validators/, core/, etc.
pytest tests/ \
  --ignore=tests/status --ignore=tests/lanes --ignore=tests/sync \
  --ignore=tests/next --ignore=tests/review --ignore=tests/merge \
  --ignore=tests/cli --ignore=tests/missions --ignore=tests/upgrade \
  --ignore=tests/dashboard --ignore=tests/release --ignore=tests/orchestrator_api \
  --ignore=tests/post_merge \
  --cov=src/specify_cli \
  --cov-report=term-missing -q 2>&1 | tail -10
```

For `core-misc`, the exact test directory structure may differ from the list above —
explore `tests/` to find the residual test directories.

---

### T030 — Apply floor formula and write `coverage-baseline.md`

After collecting all measurements, create the output file:

**File to create:** `kitty-specs/080-ci-hardening-and-lint-cleanup/coverage-baseline.md`

**Format:**
```markdown
# Coverage Baseline — Mission 079

**Date measured:** 2026-04-09
**Branch:** feat/080-ci-hardening-and-lint-cleanup (post WP01–WP05)
**Formula:** floor = max(tier_minimum, measured_coverage - 2)

## Results

| Module | Tier | Tier Min | Measured | Floor | Notes |
|--------|------|----------|----------|-------|-------|
| status | A | 75% | XX% | YY% | |
| lanes  | A | 75% | XX% | YY% | measured without marker filter (WP07 pending) |
| kernel | A | 75% | XX% | YY% | |
| sync   | A | 75% | XX% | YY% | |
| next   | B | 60% | XX% | YY% | |
| review | B | 60% | XX% | YY% | measured without marker filter (WP07 pending) |
| merge  | B | 60% | XX% | YY% | measured without marker filter (WP07 pending) |
| cli    | B | 60% | XX% | YY% | measured without marker filter (WP07 pending) |
| missions | B | 60% | XX% | YY% | |
| upgrade  | B | 60% | XX% | YY% | |
| dashboard       | C | 40% | XX% | YY% | |
| release         | C | 40% | XX% | YY% | |
| orchestrator_api| C | 40% | XX% | YY% | |
| post_merge      | C | 40% | XX% | YY% | |
| core-misc       | C | 40% | XX% | YY% | residual modules |

## WP09 Reference

Copy the Floor column values into the `--fail-under` parameter for each module's
integration-tests job in ci-quality.yml. Use the Floor value, not the Measured value.
```

Replace `XX%` and `YY%` with actual measured and calculated values.

---

### T031 — Verify zero test failures in baseline run; flag any failures before proceeding

Before finalizing `coverage-baseline.md`, confirm that no tests are failing:

```bash
# Run the complete test suite
pytest tests/ -m 'fast or git_repo' -q 2>&1 | tail -10
```

If any tests fail:
1. **Do NOT proceed to WP07 or WP09** — a failing test in the baseline invalidates the
   coverage measurement (coverage is only meaningful for passing code paths).
2. Identify whether the failing test is pre-existing (existed on `main` before this mission)
   or introduced by WP01–WP05.
3. If pre-existing: document in `coverage-baseline.md` under a "Known Failures" section;
   exclude that module from the floor until the failure is fixed.
4. If introduced by WP01–WP05: halt, identify the regression, and fix it before proceeding.

**Commit `coverage-baseline.md`** to the feature branch once all measurements are complete
and any known failures are documented.

## Definition of Done

- [ ] `coverage-baseline.md` exists at `kitty-specs/080-ci-hardening-and-lint-cleanup/coverage-baseline.md`
- [ ] Every module listed in the plan has a measured coverage percentage recorded
- [ ] Floor values are calculated using `max(tier_minimum, measured - 2)`
- [ ] Modules with zero markers (lanes, review, merge, cli) are noted as "measured without marker filter"
- [ ] Zero test failures in the baseline run (or known failures documented with module exclusions)
- [ ] File committed to `feat/080-ci-hardening-and-lint-cleanup`

## Risks

- **Module test directory structure differs:** Some modules may not have a matching
  `tests/<module>/` directory. Use `find tests/` to discover actual paths.
- **Coverage too low for tier minimum:** If measured < tier_minimum, the floor is set to
  tier_minimum. This means WP09's CI job will gate on a floor the module doesn't currently
  meet — that would immediately fail CI. In this case, record the actual measured coverage
  and set the floor to `measured - 2%` regardless of tier minimum, and add a note:
  "below tier minimum — floor set to measured to avoid blocking CI; tighten in follow-up".
- **`core-misc` is ill-defined:** The residual cluster is a catch-all. Measure what you can;
  document what modules it includes.
