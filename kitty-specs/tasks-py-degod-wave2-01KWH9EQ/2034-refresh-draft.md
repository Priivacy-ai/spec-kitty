# DRAFT — final #2034 refresh comment (FR-010)

> **Status: DRAFT — do NOT post.** The orchestrator posts this to
> [#2034](https://github.com/Priivacy-ai/spec-kitty/issues/2034) at mission
> review. Prepared by WP10/T046, mission `tasks-py-degod-wave2-01KWH9EQ`,
> 2026-07-02. Numbers sourced from the committed census artifact
> (`marker-census.md`, same directory).

---

## Final tasks-domain census (mission `tasks-py-degod-wave2` — FR-009 delivered)

Mission `tasks-py-degod-wave2-01KWH9EQ` closed its domain-matched slice of this
issue. Final numbers, measured on the mission's final tree with the canonical
selection model (`tests/architectural/_gate_coverage.py`):

| Metric | Value |
|--------|-------|
| Tasks-domain glob (FR-009, committed) | `tests/tasks/**` + `tests/specify_cli/cli/commands/agent/test_tasks*` + `tests/architectural/test_tasks_command_surface.py` + `tests/architectural/test_tasks_domain_gate_visibility.py` |
| Test files in domain | **43** (15 + 26 + 2; the mission added 9: byte-freeze suite, 6 seam suites, 2 architectural gates) |
| Tests in domain | **754** |
| Tests selected by ZERO CI gates | **0** |
| Orphan-baseline entries in domain | **0** (of 4 total in `_gate_coverage_baseline.json`) |

### What FR-009 delivered for the tasks domain

1. **Census artifact (evidence)** —
   `kitty-specs/tasks-py-degod-wave2-01KWH9EQ/marker-census.md`: a per-file
   `file | markers | selecting gate(s)` table mapping every domain test file to
   the exact `ci-quality.yml` gate expression(s) that select it (e.g.
   `fast-tests-core-misc -m "fast and not windows_ci"`, core-misc shards
   `-m "not windows_ci and (git_repo or integration or architectural)"`), plus
   the reproducible generation script. Zero unselected — the ~1 invisible file
   anticipated at spec time did not materialize; the pre-plan squad's ground
   truth (domain fully gate-visible on the mission base) held through all 10 WPs.
2. **Standing baseline-growth assertion (permanence)** —
   `tests/architectural/test_tasks_domain_gate_visibility.py`: red if any
   `orphan_files` entry in `_gate_coverage_baseline.json` ever matches the
   FR-009 glob, with a synthetic-violation theater test driving the same check
   function. Absorbing a tasks-domain path via `--update-baseline` is now a CI
   failure, not a judgment call (spec C-006).

### Repo-wide state (unchanged; out of this mission's scope)

- 2026-07-02 re-census: **257/26,612** tests repo-wide are selected by no
  marker gate; no `-m unit` / `-m contract` gate exists.
- **#2283 is the 3-cause structural parent** of this issue: (a) marker-gate
  divergence, (b) fresh-clone venv skew, (c) missing producer-conformance
  sweep. This mission closed **cause (a) for its own domain only** — the
  pattern (committed glob + census artifact + baseline-growth assertion) is
  reusable per-domain, but the repo-wide fix stays with #2283.
- The repo-wide paths remain open:
  **#2296** (Wave-0 tail: 4 orphan test files need a ci-quality.yml
  integration-shard path addition — workflow-scope-gated, i.e. blocked on a
  workflow-permission lane) and
  **#2297** (Wave 0 full: generate the CI suite-map authority from one source —
  the structural fix).

Verdict for this issue: still **deferred-with-followup** upstream — the
tasks-domain slice is done and ratcheted; the repo-wide re-tiering is #2283 /
#2296 / #2297 work.
