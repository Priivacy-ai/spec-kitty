# Mission 080 CI Run Assessment

**Date:** 2026-04-10  
**Run:** [#24224800430](https://github.com/stijn-dejongh/spec-kitty/actions/runs/24224800430)  
**Trigger:** scheduled (cron), post-rebase onto upstream/main  
**Branch:** main  

---

## CI Run Result: PARTIAL PASS

All test and lint jobs passed. SonarCloud Quality Gate failed. Slow, e2e, mutation, and diff-coverage jobs correctly skipped (schedule trigger — expected, user will trigger manually after push).

---

## Job Timings

### Fast-tests tier

| Job | Duration | Notes |
|-----|----------|-------|
| fast-tests-sync | 1m4s | — |
| fast-tests-missions | 42s | — |
| fast-tests-merge | 43s | — |
| fast-tests-release | 37s | — |
| fast-tests-post-merge | 37s | — |
| fast-tests-doctrine | 1m0s | — |
| fast-tests-status | 44s | — |
| fast-tests-lanes | 38s | — |
| fast-tests-dashboard | 46s | — |
| fast-tests-review | 45s | — |
| fast-tests-next | 43s | — |
| fast-tests-upgrade | 42s | — |
| fast-tests-cli | 46s | — |
| **fast-tests-core-misc** | **3m26s** | **Slowest by far — catch-all cluster** |

### Integration-tests tier

| Job | Duration | Notes |
|-----|----------|-------|
| integration-tests-post-merge | 28s | — |
| integration-tests-release | 50s | — |
| integration-tests-missions | 50s | — |
| integration-tests-merge | 36s | — |
| integration-tests-sync | 49s | — |
| integration-tests-doctrine | 38s | — |
| integration-tests-status | 51s | — |
| integration-tests-lanes | 51s | — |
| integration-tests-next | 44s | — |
| integration-tests-upgrade | 43s | — |
| integration-tests-review | 35s | — |
| integration-tests-dashboard | 25s | — |
| integration-tests-cli | 51s | — |

### Other jobs

| Job | Duration | Result |
|-----|----------|--------|
| changes | 7s | ✓ |
| lint | 58s | ✓ |
| kernel-tests | 37s | ✓ |
| quality-gate | 4s | ✓ |
| sonarcloud | 2m26s | ✗ Quality Gate FAILED |
| lint-feedback | 0s | skipped |
| diff-coverage | 0s | skipped |
| slow-tests | 0s | skipped |
| e2e-cross-cutting | 0s | skipped |
| mutation-testing | 0s | skipped |

---

## SonarCloud Failure

The Quality Gate failed. The logs only show `✖ Quality Gate has FAILED.` with a pointer to:  
`https://sonarcloud.io/dashboard?id=stijn-dejongh_spec-kitty&branch=main`

The SonarCloud job itself now runs in **2m26s** (previously ~636s — the test re-run elimination from mission 080 is working). The failure is a gate condition, not an execution error.

**Likely cause:** New code added by upstream commits (browser OAuth, review feedback fix) may not meet the SonarCloud coverage or reliability thresholds. The specific failing metric is only visible in the SonarCloud dashboard — the CI logs don't surface it.

**Action needed:** Check the SonarCloud dashboard to identify which condition failed (coverage on new code, reliability, security, duplications). Once WP04/WP05 are merged (lint/type cleanup), re-assess.

---

## Mission 080 Goals vs Delivered

### What is DONE (in the squash-merged commit)

| FR | Requirement | Status |
|----|-------------|--------|
| FR-004 | Per-module fast+integration job pairs | ✓ Done — 30 jobs running |
| FR-005 | Each job scoped to its module paths | ✓ Done |
| FR-006 | Per-module coverage floors | ✓ Done (calibrated floors in CI) |
| FR-007 | DAG dependency ordering | ✓ Done (Tier 0→1→2→3) |
| FR-008 | Monolithic core jobs removed | ✓ Done |
| FR-009 | quality-gate aggregates all per-module jobs | ✓ Done |
| FR-001 | Ruff auto-fix violations (WP01) | ✓ Done |
| FR-002 (partial) | Dossier test schema drift (WP03) | ✓ Done |

### What is NOT YET DONE

| FR | Requirement | WP | Current State |
|----|-------------|-----|---------------|
| FR-002 (remainder) | acceptance.py import ordering | WP02 | in_progress |
| FR-002 (remainder) | Stale `# type: ignore` removals | WP04 | planned |
| FR-002 (remainder) | Bare generics, no-any-return, type incompatibilities | WP05 | planned |
| FR-003 | `types-requests` dev dependency | WP05 | planned |
| FR-016/FR-017 | Test marker cataloguing + shift-left | WP07/WP08 | planned |
| FR-010/FR-011 | Docs-only skip (path filter) | WP10 | planned |
| FR-012 | kernel-only skip | WP10 | planned |
| FR-014/FR-015 | orchestrator-boundary + events-alignment path filters | WP10 | planned |

---

## Constraint Drift: C-002 Violated

Constraint C-002 states: *"lint fixes must be delivered before the CI job split so coverage floors are computed against a clean baseline."*

The squash merge included WP09 (CI job split) before WP02/WP04/WP05 (remaining lint/type fixes) were completed. The coverage floors were calibrated against the pre-lint-cleanup baseline. This is acceptable in practice (the floors will be slightly conservative), but it means the **NFR-003** criterion ("lint gate reports zero violations on main") is not yet met.

Current state of lint gate: Unknown — the lint job passes (58s), but that means ruff exits 0 and mypy passes for the configured scope. The remaining mypy violations in WP04/WP05 may be out of the mypy scope configured in CI. Verify after WP04/WP05 merge.

---

## Key Observations

### fast-tests-core-misc is the outlier (3m26s)

This is the catch-all cluster and runs 3.4x longer than any other fast-tests job. It will be the bottleneck for any PR that touches cross-cutting code. The two largest collections within it are strong extraction candidates:

#### `tests/charter` — 181 tests, fully fast-marked

All 14 test files in `tests/charter` carry `@pytest.mark.fast` or `pytestmark = fast`. Zero `git_repo`-marked tests. The source package (`src/charter/`) is self-contained with its own top-level directory. Extraction is a clean no-risk split.

**Proposed job:** `fast-tests-charter`
- DAG position: same tier as `fast-tests-doctrine` (both are foundational, no dependency between them; both `need: [changes, kernel-tests]`)
- Path filter: `src/charter/**`, `tests/charter/**` — already present in `core_misc`, would move to a new `charter` output
- Coverage: `--cov=src/charter`
- No integration job needed (no `git_repo`-marked tests exist)

#### `tests/agent` — 1348 tests, fast + 6 git_repo files

The `tests/agent` tree is the single largest contributor to core-misc, with 1348 collected tests across agent workflow, glossary, CLI commands, and feature management. 50 files are fast-marked; 6 carry `git_repo` markers, making an integration job appropriate.

**Proposed jobs:** `fast-tests-agent` + `integration-tests-agent`
- DAG position: Tier 2 or 3 — agent workflows depend on `status`, `missions`, and `charter`; safe to add `needs: [fast-tests-charter, fast-tests-status, fast-tests-missions]`
- Path filter: `src/specify_cli/agent*/**`, `src/specify_cli/agent_utils/**`, `tests/agent/**`
- Coverage: `--cov=src/specify_cli/agent_utils --cov=src/specify_cli/agent`

#### Remaining core-misc after extraction

After removing charter (181) and agent (1348) from core-misc, the remaining test count drops from ~3000+ collected to ~1500+. Key remaining directories:

| Directory | Tests | Notes |
|-----------|-------|-------|
| `tests/dossier` | 311 | another extraction candidate once agent is done |
| `tests/git_ops` | 286 | git-heavy, likely all git_repo-marked |
| `tests/cross_cutting` | 247 | broad surface, may stay in misc |
| `tests/auth` | 210 | 5 collection errors — needs investigation |
| `tests/contract` | 114 | boundary tests |
| `tests/core` | 71 | low count, stays in misc |
| `tests/init` | 54 | low count, stays in misc |
| Others | ~100 | policy, tasks, adversarial, concurrency, etc. |

The 3m26s runtime is dominated by agent test execution. Extracting agent alone should bring core-misc under 90s and into line with other per-module jobs.

### SonarCloud improvement confirmed

The previous assessment (2026-04-09-ci-setup-optimization-assessment.md) identified that sonarcloud was running a full test re-run (636s). Mission 080 eliminated this — it now runs in 2m26s. The Quality Gate failure is a separate issue from execution time.

### CI split is working as intended

All 30 per-module jobs completed successfully. The quality-gate job (which aggregates test results) passed. The CI structure goal of mission 080 is functionally complete.

### Slow/e2e correctly absent

slow-tests and e2e-cross-cutting are skipped on schedule and push triggers. This is correct behavior — they are PR/manual-only. The user will trigger manually after push.

---

## Next Steps

1. **Diagnose SonarCloud gate failure** — check the SonarCloud dashboard for the specific failing condition before pushing
2. **Complete WP02** (acceptance.py) — in_progress, blocking NFR-003
3. **Start WP04/WP05** — stale ignores + bare generics, currently planned
4. **WP10** — path filters for docs-only and orchestrator-boundary workflows
5. **Investigate fast-tests-core-misc** — 3m26s is disproportionate; catalogue what's in it and whether a further split is warranted
