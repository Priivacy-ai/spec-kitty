# Implementation Plan: CI Hardening and Lint Cleanup

**Branch**: `feat/080-ci-hardening-and-lint-cleanup` | **Date**: 2026-04-09
**Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md)
**Mission type**: software-dev

---

## Summary

Bring the spec-kitty codebase to a clean ruff + mypy baseline, replace the monolithic CI test
jobs with dependency-ordered per-module jobs (informed by a measured coverage baseline and
tiered floor policy), and add path-based CI filtering so documentation-only commits do not
trigger the full test suite.

The work is structured in three dependency-ordered execution batches:
- **Batch 1 (parallel):** WP01–WP05 — lint and type fixes on `main`
- **Batch 2 (sequential after Batch 1):** WP06 + WP07 + WP08 — baseline measurement, shift-left, and test marker cataloguing
- **Batch 3 (sequential after Batch 2):** WP09 + WP10 — CI job split and path filtering

---

## Technical Context

**Language/Version:** Python 3.11+ (runtime); Python 3.12 on CI runners
**Primary Dependencies:** pytest, ruff, mypy, typer, rich, ruamel.yaml
**Storage:** Filesystem only (YAML, JSONL, Markdown); no database
**Testing:** pytest with markers: `fast`, `git_repo`, `slow`, `integration`, `e2e`
**Target Platform:** GitHub Actions (ubuntu-24.04 runners); also Linux/macOS local dev
**Performance Goals:** docs-only PRs ≤ 2 min CI; single-module code PRs ≤ 5 min CI
**Constraints:** Branch protection required checks must not be broken at any point during migration (C-001)
**Scale/Scope:** ~87,000 lines of Python source; ~13 module clusters; ~12 workflow files

---

## Charter Check

Charter file: `.kittify/charter/charter.md` (present, v1.1.0)

| Check | Status | Notes |
|-------|--------|-------|
| mypy --strict passes | ❌ (pre-mission) → ✅ (post-WP05) | WP01–WP05 fix all open violations |
| 90%+ coverage for new code | ✅ enforced by per-WP gate | New test code in WP08 must meet charter threshold |
| CLI < 2 seconds | not applicable | No runtime behavior changed |
| Terminology: `--mission` not `--feature` | not applicable | No CLI changes |

**No charter violations introduced by this mission.**

---

## Architectural Assessment (Architect Alphonso)

*Profile: `architect` — analysis mode*

### Module Dependency Graph and CI DAG Ordering

The import-graph analysis (research.md R-01) confirms three execution tiers for the CI DAG:

```
Tier 0 (leaf nodes — run immediately):
  sync ─────────────────────────────────────────────────────┐
  merge ────────────────────────────────────────────────┐   │
  missions ─────────────────────────────────────────┐   │   │
  post_merge / release ─────────────────────────┐   │   │   │
                                                │   │   │   │
Tier 1 (depends on Tier 0):                     │   │   │   │
  status ◄───────────────────────────────────────── ────│───┘
                                                    │   │
Tier 2 (depends on Tier 1):                         │   │
  review ◄── status                                 │   │
  next   ◄── status                                 │   │
  lanes  ◄── status, merge ◄──────────────────────── ───┘
  dashboard ◄── status, sync ◄──────────────────────────┘
  upgrade ◄── status

Tier 3 (orchestrators — depend on Tier 2):
  cli ◄── {everything above}
  orchestrator_api ◄── cli, lanes, merge, status
```

**Key architectural decision:** Alphonso's original assumption ("next and review before merge")
does not hold at the import level — `merge` has no imports from `next` or `review`. The actual
structural ordering is `sync → status → {review, next, lanes}`. The CI DAG must encode this
verified structure, not the intuitive but unverified assumption.

### Coverage Floor Architecture

The three-tier floor model reflects the principle that coverage strictness should be
proportional to the blast radius of a regression:

```
Essential (Tier A) — 75% minimum:
  status, lanes, kernel, sync
  Rationale: used by ≥3 modules; state-machine correctness is non-negotiable

Normal (Tier B) — 60% minimum:
  next, review, merge, cli, missions, upgrade
  Rationale: core workflow logic; bounded failure domain

Glue (Tier C) — 40% minimum:
  dashboard, release, orchestrator_api, post_merge, core-misc
  Rationale: thin adapters; integration tests cover the critical paths
```

Floors are set to `max(tier_minimum, measured_baseline - 2%)` — a "do not regress" gate,
not a "achieve more coverage" mandate. Tightening is out of scope for this mission.

### Shift-Left Assessment

The test pyramid is currently inverted in key modules:
- `tests/next/` has more `git_repo` tests than `fast` tests (5:4 ratio)
- `tests/missions/` has a 7:6 git_repo:fast ratio
- `tests/review/` and `tests/lanes/` have zero marked tests — they are invisible to any
  marker-scoped CI job

This creates two problems:
1. **CI cost:** `git_repo` tests spawn subprocess `git init` + git operations, costing ~30–90s
   per test. Tests that only need filesystem state should not pay this cost.
2. **CI correctness:** Unmarked tests in `review` and `lanes` are not counted in any marker-
   scoped coverage run — they contribute to line coverage but not to the job that reports it.

**Architectural recommendation:** FR-016 (marker cataloguing) is a prerequisite for FR-017
(shift-left) and must complete before WP09 (CI split) to ensure coverage accounting is
correct from the first split run.

### Risk Register (updated from original assessment)

| Risk | Likelihood | Mitigation | Owner WP |
|------|------------|------------|---------|
| Branch protection breaks on job rename | High | Add shim jobs before removing old required checks | WP10 |
| Coverage floors set too high (miscalibration) | Medium | Measure-first + `-2%` buffer; conservative tier minimums | WP06 |
| Dossier test fixes change test behavior | Medium | Inspect production signatures before editing; do not change test scenarios | WP03 |
| Unmarked tests missed in coverage accounting | High | FR-016 cataloguing in WP07 before CI split in WP09 | WP07 |
| `dorny/paths-filter` output name collision | Low | Use namespaced output keys per job group | WP10 |
| CI matrix explosion in `report`/`quality-gate` | Medium | Reusable workflow or job matrix for DAG enumeration | WP09 |

---

## Doctrine References

| Artifact | Type | Applied in |
|----------|------|-----------|
| `DIRECTIVE_030` — Test and Typecheck Quality Gate | Directive | WP01–WP05 acceptance criteria |
| `DIRECTIVE_025` — Boy Scout Rule | Directive | WP02 (E402 cleanup scope) |
| `DIRECTIVE_034` — Test-First Development | Directive | WP08 (shift-left must not reduce coverage) |
| `DIRECTIVE_001` — Architectural Integrity Standard | Directive | WP09 (CI DAG must match architectural boundaries) |
| `test-pyramid-progression` | Tactic | WP09 job ordering; WP08 shift-left criteria |
| `testing-select-appropriate-level` | Tactic | WP08 classification of shift-left candidates |
| `test-boundaries-by-responsibility` | Tactic | WP09 job scoping (each job tests its own boundary) |
| `quality-gate-verification` | Tactic | WP06 floor calibration verification |
| `no-parallel-duplicate-test-runs` | Tactic | WP09 job split (no test must run in two jobs) |

---

## Project Structure

### Documentation (this mission)

```
kitty-specs/080-ci-hardening-and-lint-cleanup/
├── spec.md              # Mission specification
├── plan.md              # This file
├── research.md          # Module graph, tier classification, shift-left findings
├── checklists/
│   └── requirements.md  # Spec quality checklist (all items pass)
└── tasks.md             # Generated by /spec-kitty.tasks (not yet created)
```

### Source Code Touch Points

```
src/
├── charter/
│   ├── catalog.py             # WP01: ARG001 fix
│   └── resolver.py            # WP01: SIM108 fix
├── doctrine/missions/
│   └── glossary_hook.py       # WP01: B009 fix
├── kernel/
│   └── _safe_re.py            # WP01: SIM105 fix
└── specify_cli/
    ├── acceptance.py           # WP02: E402/UP035/F401 root-cause fix
    ├── dossier/tests/
    │   └── test_snapshot.py    # WP03: MissionDossier/ArtifactRef schema drift
    ├── post_merge/stale_assertions.py  # WP04: stale type: ignore (×4)
    ├── tracker/credentials.py  # WP04: stale type: ignore (×1)
    ├── merge/config.py         # WP04: stale type: ignore (×1)
    ├── migration/rebuild_state.py      # WP04: stale type: ignore (×1)
    ├── migration/backfill_identity.py  # WP04: stale type: ignore (×1)
    ├── policy/audit.py         # WP04: stale type: ignore (×1)
    ├── state_contract.py       # WP05: bare dict type-arg
    ├── acceptance_matrix.py    # WP05: bare dict type-arg (×2)
    ├── sync/config.py          # WP05: missing return type annotations
    ├── sync/body_transport.py  # WP05: missing types-requests stub
    ├── merge/conflict_resolver.py      # WP05: sort key type
    ├── migration/backfill_identity.py  # WP05: no-any-return
    ├── migration/backfill_ownership.py # WP05: bare dict type-arg
    ├── version_utils.py        # WP05: no-any-return
    ├── upgrade/feature_meta.py # WP05: no-any-return
    └── cli/commands/materialize.py     # WP05: incompatible assignment

tests/
├── next/          # WP08: shift-left candidates (5 git_repo tests)
├── missions/      # WP08: shift-left candidates (7 git_repo tests)
├── lanes/         # WP07: FR-016 marker cataloguing (0 markers on 12 test files)
└── review/        # WP07: FR-016 marker cataloguing (0 markers on 6 test files)

.github/workflows/
├── ci-quality.yml             # WP09 + WP10: job split + path filtering
├── orchestrator-boundary.yml  # WP10: FR-014 path filter
└── check-spec-kitty-events-alignment.yml  # WP10: FR-015 path filter

pyproject.toml                 # WP05: add types-requests to dev deps
```

---

## Work Packages

### Batch 1 — Lint and Type Fixes (parallel, independent)

---

#### WP01 — Auto-fix Ruff Violations

**Scope:** Fix all auto-fixable ruff violations in the four isolated-file locations.
**Relevant spec FRs:** FR-001
**Doctrine:** DIRECTIVE_030, DIRECTIVE_025

**Files to fix:**
- `src/charter/catalog.py:245` — ARG001: remove or use the `doctrine_root` parameter
- `src/charter/resolver.py:120` — SIM108: collapse if/else to ternary
- `src/doctrine/missions/glossary_hook.py:134` — B009: replace `getattr(module, "X")` with `module.X`
- `src/kernel/_safe_re.py:185` — SIM105: replace try/except/pass with `contextlib.suppress`

**Approach:** Run `ruff check --fix src/charter/catalog.py src/charter/resolver.py src/doctrine/missions/glossary_hook.py src/kernel/_safe_re.py` for auto-fixable rules. Verify each change passes the test suite for that module.

**Acceptance criteria:**
- `ruff check src/charter/catalog.py src/charter/resolver.py src/doctrine/missions/glossary_hook.py src/kernel/_safe_re.py` exits 0
- All tests in the affected modules pass
- DIRECTIVE_030 gate: mypy passes for touched files

---

#### WP02 — Fix acceptance.py Import Ordering

**Scope:** Resolve the E402 cascade in `src/specify_cli/acceptance.py` plus the UP035/F401 cluster caused by the same root issue.
**Relevant spec FRs:** FR-001
**Doctrine:** DIRECTIVE_030, DIRECTIVE_025

**Root cause:** A `logger = logging.getLogger(__name__)` call appears at line 10, before all
other imports. This produces 8 E402 violations on every subsequent import. The correct fix is
to move the logger setup below the imports.

**Files to fix:**
- `src/specify_cli/acceptance.py`: move logger init after imports; remove `MutableMapping`,
  `extract_scalar`, `find_repo_root` (unused); replace `Dict`/`List`/`Set`/`Tuple`/`Iterable`
  with their `collections.abc` or builtin equivalents (UP035)

**Acceptance criteria:**
- `ruff check src/specify_cli/acceptance.py` exits 0
- `mypy src/specify_cli/acceptance.py` exits 0
- All tests exercising `acceptance.py` pass (run `pytest tests/` filtering by acceptance-touching test files)

---

#### WP03 — Fix Dossier Test Schema Drift

**Scope:** Fix `src/specify_cli/dossier/tests/test_snapshot.py` which calls `MissionDossier` and `ArtifactRef` with wrong keyword arguments.
**Relevant spec FRs:** FR-002
**Doctrine:** DIRECTIVE_030, DIRECTIVE_034

**Pre-condition (must verify first):**
Read the current production class signatures:
- `MissionDossier` dataclass in `src/specify_cli/dossier/` — determine current required fields
- `ArtifactRef` dataclass — determine current required fields (`wp_id`, `step_id`, `error_reason` appear required per mypy)

**Risk (Assumption A3):** If the test scenarios test deprecated behavior rather than current
behavior, do not fix them silently — escalate with a comment and flag for the reviewer.

**Acceptance criteria:**
- `mypy src/specify_cli/dossier/tests/test_snapshot.py` exits 0 (zero call-arg and misc errors)
- All tests in `tests/specify_cli/` and the dossier test file pass
- No production dataclass signatures are modified

---

#### WP04 — Remove Stale `# type: ignore` Comments

**Scope:** Remove 8 stale `# type: ignore` suppressions across 6 files.
**Relevant spec FRs:** FR-002
**Doctrine:** DIRECTIVE_030

**Files and lines:**
- `src/specify_cli/post_merge/stale_assertions.py` lines 317, 319, 322, 324
- `src/specify_cli/tracker/credentials.py` line 15
- `src/specify_cli/merge/config.py` line 57
- `src/specify_cli/migration/rebuild_state.py` line 38
- `src/specify_cli/migration/backfill_identity.py` line 36
- `src/specify_cli/policy/audit.py` line 27

**Verification process for each removal (C-005):**
1. Remove the `# type: ignore` comment
2. Run `mypy <file>` — if an error reappears, the original suppression was valid; restore it and document the remaining error in a comment explaining why it persists

**Acceptance criteria:**
- `mypy` for each of the 6 files reports zero `unused-ignore` errors
- No new mypy errors introduced by the removals
- All tests in affected modules pass

---

#### WP05 — Fix Remaining Mypy Violations

**Scope:** Fix bare generic types, `no-any-return` violations, missing return type annotations, incompatible assignments, and add `types-requests` dev dependency.
**Relevant spec FRs:** FR-002, FR-003
**Doctrine:** DIRECTIVE_030

**Grouped by fix type:**

*Bare generics (`dict` → `dict[str, ...]`, etc.):*
- `src/specify_cli/state_contract.py:80`
- `src/specify_cli/acceptance_matrix.py:75,88`
- `src/doctrine/missions/repository.py:56,74`
- `src/specify_cli/migration/backfill_ownership.py:86,151`

*Missing return types:*
- `src/specify_cli/sync/config.py:15,39` — add `-> None`

*`no-any-return` (functions declared to return a specific type but return `Any`):*
- `src/specify_cli/version_utils.py:28`
- `src/specify_cli/upgrade/feature_meta.py:165`
- `src/specify_cli/policy/audit.py:27` (also has a stale ignore — coordinate with WP04 if same WP)
- `src/doctrine/missions/repository.py:31,36,66,71,76`
- `src/specify_cli/migration/backfill_identity.py:36` (coordinate with WP04)

*Type incompatibilities:*
- `src/specify_cli/merge/conflict_resolver.py:172` — sort key callable type
- `src/specify_cli/cli/commands/materialize.py:123` — `Any | None` assigned to `str`
- `src/specify_cli/tracker/credentials.py:17` — `None` assigned to `Module` type

*Missing stubs (C-006: dev deps only):*
- Add `types-requests` to `pyproject.toml` under `[project.optional-dependencies]` `lint` or `test` group (not runtime)

**Acceptance criteria:**
- `mypy --strict src/` reports zero errors for all files listed in FR-002
- All existing tests pass
- `types-requests` is in dev/lint dependencies only

---

### Batch 2 — Baseline Measurement and Test Classification (sequential after Batch 1)

*Batch 2 starts only after all of WP01–WP05 are merged to the feature branch.*

---

#### WP06 — Measure Per-Module Coverage Baseline

**Scope:** Run the full test suite (all markers) per module cluster and record actual coverage percentages. Produce the floor table for WP09.
**Relevant spec FRs:** FR-006
**Doctrine:** `quality-gate-verification`, DIRECTIVE_030

**Process:**
For each module cluster listed in the Tier table (research.md R-02):
```bash
pytest tests/<module>/ \
  --cov=src/specify_cli/<module> \
  -m 'fast or git_repo or slow or integration or e2e' \
  --cov-report=term-missing -q
```

Record results in `kitty-specs/080-ci-hardening-and-lint-cleanup/coverage-baseline.md`.

**Floor formula per module:**
```
floor = max(tier_minimum, measured_coverage - 2)
```

Where tier minimums are:
- Essential (status, lanes, kernel, sync): 75%
- Normal (next, review, merge, cli, missions, upgrade): 60%
- Glue (dashboard, release, orchestrator_api, post_merge, core-misc): 40%

**Output:** `kitty-specs/080-ci-hardening-and-lint-cleanup/coverage-baseline.md` with one row
per module: `| module | tier | measured | floor |`

**Acceptance criteria:**
- All module clusters have a recorded measured coverage percentage
- `coverage-baseline.md` is committed to the feature branch
- No test failures during baseline run (if failures occur, halt and report — do not proceed to WP07/WP08/WP09 with failing tests)

---

#### WP07 — Test Marker Cataloguing (FR-016)

**Scope:** Audit all test files in `tests/lanes/` and `tests/review/` (zero current markers) and any other module directories where a significant number of test functions are unmarked. Add appropriate pytest markers.
**Relevant spec FRs:** FR-016
**Doctrine:** `testing-select-appropriate-level`, `test-pyramid-progression`

**Classification criteria:**
- `fast`: no subprocess, no git, no network, no disk writes outside `tmp_path` — pure logic
- `git_repo`: requires real git repository (subprocess `git init` or worktree)
- `slow`: takes > 30 seconds
- `integration`: requires multiple real components interacting
- `e2e`: exercises the full CLI workflow end-to-end

**Scope:**
1. `tests/lanes/` (12 test files, 0 markers) — classify all test functions
2. `tests/review/` (6 test files, 0 markers) — classify all test functions
3. `tests/merge/` (7 test files, 2 fast, 1 git_repo) — classify unmarked functions
4. `tests/cli/` (3 test files, 0 markers) — classify all

**Acceptance criteria:**
- Zero test functions in the catalogued modules lack at least one pytest marker
- All tests still pass after marker addition (markers are additive, not behavioral)
- `pytest tests/lanes/ tests/review/ tests/merge/ tests/cli/ -m fast` runs without error

---

#### WP08 — Shift-Left Test Migration (FR-017)

**Scope:** Convert `git_repo`-marked tests in `tests/next/` and `tests/missions/` that do not require real git operations to `fast`-marked tests.
**Relevant spec FRs:** FR-017
**Doctrine:** `testing-select-appropriate-level`, `test-pyramid-progression`, DIRECTIVE_034

**Identification criteria for shift-left eligibility:**
A `git_repo` test is a shift-left candidate if:
1. It does not call `subprocess.run`/`subprocess.check_call`/`check_output` with `git` commands
2. It does not use `git worktree`, `git init`, `git commit`, or any git operation that requires a real repo
3. Its assertions are on data structures, rendered content, or file contents — not on git state

**Process:**
1. For each `git_repo` test in `tests/next/` and `tests/missions/`:
   - Check if git operations can be replaced with `tmp_path` + fixture data
   - If yes: refactor to use `tmp_path`, replace `@pytest.mark.git_repo` with `@pytest.mark.fast`
   - If no: document why it must remain git_repo in a comment on the test

2. Verify the converted tests still assert the same outcomes

**Acceptance criteria (DIRECTIVE_034 — test-first):**
- No test coverage decreases after shift-left (run full suite before and after; compare coverage)
- Converted tests run in the `fast` marker tier (confirmed by `pytest -m fast tests/next/ tests/missions/`)
- Each converted test still passes and asserts the same invariant as before
- Any test that cannot be shifted has a comment explaining why

---

### Batch 3 — CI Structure (sequential after Batch 2)

*Batch 3 starts only after WP06 (coverage-baseline.md produced) and WP07 (all tests marked).*

---

#### WP09 — Per-Module CI Job Split (FR-004 to FR-009)

**Scope:** Replace `fast-tests-core` and `integration-tests-core` in `.github/workflows/ci-quality.yml` with per-module job pairs, using the dependency DAG from R-01 and coverage floors from WP06.
**Relevant spec FRs:** FR-004, FR-005, FR-006, FR-007, FR-008, FR-009
**Doctrine:** DIRECTIVE_001, `test-boundaries-by-responsibility`, `no-parallel-duplicate-test-runs`

**Job naming convention:** `fast-tests-<module>` and `integration-tests-<module>`

**DAG encoding in GitHub Actions:**
```yaml
# Tier 0 jobs — no needs:
fast-tests-sync:
fast-tests-merge:
fast-tests-missions:
fast-tests-post_merge:
fast-tests-release:

# Tier 1 — needs Tier 0:
fast-tests-status:
  needs: [fast-tests-sync]

# Tier 2 — needs Tier 1:
fast-tests-review:
  needs: [fast-tests-status]
fast-tests-next:
  needs: [fast-tests-status]
fast-tests-lanes:
  needs: [fast-tests-merge, fast-tests-status]
fast-tests-dashboard:
  needs: [fast-tests-status]
fast-tests-upgrade:
  needs: [fast-tests-status]

# Tier 3 — needs Tier 2:
fast-tests-cli:
  needs: [fast-tests-lanes, fast-tests-next, fast-tests-review, fast-tests-dashboard, fast-tests-upgrade]
fast-tests-orchestrator_api:
  needs: [fast-tests-cli, fast-tests-lanes, fast-tests-merge, fast-tests-status]

# Residual catch-all for unlisted modules:
fast-tests-core-misc:
  # tests/core/, tests/policy/, tests/schemas/, tests/validators/, etc.
```

**Coverage floor application (from WP06 coverage-baseline.md):**
```yaml
- name: Check coverage floor
  run: |
    coverage report --fail-under=<floor_from_baseline>
```

**`report` and `quality-gate` DAG update (FR-009):**
List all new per-module job names explicitly in the `needs:` array of both jobs.

**Acceptance criteria:**
- `fast-tests-core` and `integration-tests-core` jobs no longer exist
- All new per-module jobs run and pass on `main`
- `quality-gate` job passes on `main`
- `DIRECTIVE_030` gate: full suite passes

---

#### WP10 — Path-Based CI Filtering + Branch Protection Shims (FR-010 to FR-015)

**Scope:** Add path-based workflow and job filters; add skip-pass shim jobs; update `orchestrator-boundary.yml` and `check-spec-kitty-events-alignment.yml`.
**Relevant spec FRs:** FR-010, FR-011, FR-012, FR-013, FR-014, FR-015
**Doctrine:** DIRECTIVE_001

**Pre-condition (C-001):** Confirm with the repository owner which jobs are currently listed
as required checks in branch protection before making any changes.

**Step 1 — Add workflow-level `paths:` trigger to `ci-quality.yml`:**
```yaml
on:
  pull_request:
    branches: [main, develop, 2.x]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'pyproject.toml'
      - '.github/workflows/ci-quality.yml'
  push:
    branches: [main, develop, 2.x]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'pyproject.toml'
      - '.github/workflows/ci-quality.yml'
```

**Step 2 — Add `changes` detection job using `dorny/paths-filter`:**
```yaml
changes:
  runs-on: ubuntu-latest
  outputs:
    sync: ${{ steps.filter.outputs.sync }}
    merge: ${{ steps.filter.outputs.merge }}
    # ... all modules
  steps:
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
          # ... etc.
```

**Step 3 — Add `if:` conditions to each per-module job:**
```yaml
fast-tests-sync:
  if: needs.changes.outputs.sync == 'true'
  needs: [changes]
```

**Step 4 — Add skip-pass shim jobs (FR-013):**
For each per-module job that is a required check, add:
```yaml
fast-tests-<module>-shim:
  runs-on: ubuntu-latest
  needs: [changes]
  if: needs.changes.outputs.<module> != 'true'
  steps:
    - run: echo "Skipped — no <module> changes"
```

**Step 5 — Update `orchestrator-boundary.yml` (FR-014):**
Add path filter: `src/specify_cli/orchestrator_api/**`, `src/specify_cli/core/**`

**Step 6 — Update `check-spec-kitty-events-alignment.yml` (FR-015):**
Add path filter: `src/specify_cli/sync/**`, `pyproject.toml`

**Acceptance criteria:**
- A PR touching only `docs/**` does not trigger Python test jobs
- A PR touching only `src/specify_cli/dashboard/` does not trigger `fast-tests-merge` or `fast-tests-sync`
- All required checks remain satisfied (shim jobs or skip-pass pattern active)
- `orchestrator-boundary.yml` does not run on a docs-only PR
- `check-spec-kitty-events-alignment.yml` does not run on a docs-only PR

---

## Execution Batches and Lane Strategy

```
Lane A (parallel):  WP01 → merge
Lane B (parallel):  WP02 → merge
Lane C (parallel):  WP03 → merge
Lane D (parallel):  WP04 → merge
Lane E (parallel):  WP05 → merge

  ↓ (all of Batch 1 merged)

Lane F (sequential): WP06 → WP07 → WP08 → merge

  ↓ (Batch 2 merged, coverage-baseline.md committed)

Lane G (sequential): WP09 → WP10 → merge
```

**Rationale for sequential Batch 2:** WP06 (measurement) must precede WP07 (marker
cataloguing) because marker addition changes which tests run in marker-scoped coverage
commands. WP08 (shift-left) must follow WP07 because some tests being shifted may gain or
lose the `fast` marker during cataloguing.

**Rationale for sequential Batch 3:** WP09 (job split) must precede WP10 (path filtering)
because the path filter's per-module `if:` conditions reference job names that WP09 creates.

---

## Branch Contract (repeated per skill requirement)

- **Current branch at plan start:** `feat/080-ci-hardening-and-lint-cleanup`
- **Planning/base branch:** `feat/080-ci-hardening-and-lint-cleanup`
- **Final merge target for completed changes:** `main`
- `branch_matches_target`: true (we are on the feature branch throughout)

Next step: `/spec-kitty.tasks` — generates work package files and finalizes lane assignments.
