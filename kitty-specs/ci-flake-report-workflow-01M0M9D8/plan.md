# Implementation Plan: CI Flake-Report Workflow

**Branch**: `kitty/mission-ci-flake-report-workflow-01M0M9D8` | **Date**: 2026-08-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/ci-flake-report-workflow-01M0M9D8/spec.md` (v2, post-spec-squad)

## Summary

Deliver two partitioned capabilities:

- **A — Flake-Report measurement**: a stdlib+`gh` Python tool (`scripts/ci/flake_report.py`) that enumerates a target workflow's runs, classifies completed failures (`perf_timing_flake` / `infra_flake` / `real` / `needs_review`), mines per-test durations, and produces an **incremental** report (half-open completion-time cursor, 30-day first/lost-baseline fallback) emitted as artifacts by a **weekly + on-demand** workflow (`.github/workflows/ci-flake-report.yml`). Non-gating, artifacts-only.
- **B — Draft/ready CI execution mode**: extend `ci-quality.yml` so **draft** PRs fail-fast (canceller job stops the chain on first failure), **ready** PRs run **full *relevant* signal** (diff-touched chains run to completion via `if: always()`/relevance; untouched domains stay path-filtered out), a **red-first re-run** runs previously-failed nodeids first on the next push, and the merge-gate contract is preserved (gate reads `needs.<job>.result`; no `continue-on-error` on gating jobs; guard tests stay green).

Capability A ships independently; Capability B is a separate WP partition landing in the same PR.

## Technical Context

**Language/Version**: Python 3.11+ (repo standard).
**Primary Dependencies**: standard library only + `gh` CLI (no new PyPI deps — NFR-001). GitHub Actions for the workflows.
**Storage**: workflow artifacts (`state.json` delta baseline, findings bundle); a committed golden fixture under the mission dir.
**Testing**: `pytest` (unit tests for pure functions; a fixture-backed NFR-003 fidelity test; architectural guard tests for Capability B).
**Target Platform**: GitHub Actions runners (`blacksmith-4vcpu-ubuntu-2404`), `gh` authed via `GITHUB_TOKEN`.
**Project Type**: single (tooling + CI config).
**Performance Goals**: weekly job < 15 min (NFR-002) via FR-008 caps (≤200 classified failures, ≤50 duration-mined runs, `--log-failed`/selective `gh api`).
**Constraints**: `ruff` + `mypy --strict` clean, complexity ≤ 15; deterministic output (NFR-004); non-gating flake workflow (C-002); merge-gate preserved (C-003).
**Scale/Scope**: ~100–170 CI runs/week in the enumeration window; ~60 jobs/run.

## Charter / Constitution Check

*GATE: re-checked after design.*

- **Single canonical authority / unification not parity**: Capability B extends the *existing* draft/ready machinery in `ci-quality.yml` (`ready_for_review` trigger, `quality_gate_decision.py`, path-filtered `changes` job) rather than adding a parallel model. ✅
- **Canonical sources**: reuse `scripts/check_nfr_003_latency.py`/`scripts/benchmarks/*` idioms (stdlib `statistics`, JSON output) and existing scheduled-workflow idioms (`docs-freshness.yml`, `drift-detector.yml`). ✅
- **ATDD-first / tiered rigour**: pure-core functions get direct unit tests; NFR-003 fidelity is fixture-backed; Capability B guarded by `test_suite_jobs_gate_blocking.py` / `test_ci_quality_path_filters.py`. ✅
- **Git/workflow discipline**: no direct push to origin/main; consolidate to a PR branch off `upstream/main`; operator merges. ✅
- **Terminology**: no `feature*` aliases introduced; "Mission" canon respected. ✅

## Project Structure

### Documentation (this mission)

```
kitty-specs/ci-flake-report-workflow-01M0M9D8/
├── spec.md                  # v2 (committed)
├── plan.md                  # this file
├── data-model.md            # artifact + state schemas, signature-table contract
├──  tests/ci/fixtures/flake_report/  # FR-017 golden reference (frozen runs/logs + expected)
├── checklists/requirements.md
└── tasks/                   # WP files (tasks phase)
```

### Source Code (repository root)

```
scripts/ci/
└── flake_report.py          # Capability A tool (enumerate/classify/mine/delta/render)
tests/ci/
├── test_flake_report_core.py    # pure-function unit tests (taxonomy, formula, delta, aggregation)
└── test_flake_report_fidelity.py# NFR-003 against fixtures/ golden set
.github/workflows/
├── ci-flake-report.yml      # Capability A workflow (weekly + dispatch, artifacts)
└── ci-quality.yml           # Capability B edits (draft canceller, relevant-signal, red-first)
scripts/ci/quality_gate_decision.py  # Capability B: gate reads needs.<job>.result (edit if needed)
docs/development/ (+ CONTRIBUTING/runbook)  # FR-013 draft/ready contract
```

## Architecture & Data Flow

### Capability A — flake_report.py (pure core ⟂ IO shell)

```
gh (subprocess)  ─┐
                  ├─► enumerate_runs() ──► [Run]  (FR-001 taxonomy filter)
prior state.json ─┘                         │
                                            ├─► classify_failures() ──► [Classification]  (FR-002 signature table)
                                            ├─► mine_durations()   ──► [DurationAgg]      (FR-003, capped FR-008)
                                            ├─► compute_delta(prev) ──► headline + delta   (FR-004 half-open cursor)
                                            └─► render() ──► metrics.json / durations.json / report.md / state.json
```

- **Pure core** (`flake_report.py`, WP01, unit-testable, no IO): `classify_one(nodeids, log_text, job_names) -> (bucket, reason)`; `false_red_rate(counts)`; `aggregate_durations(samples)`; `resolve_window(prev_state, now)`; `advance_cursor(runs)`.
- **IO shell + CLI + render** (`flake_report_cli.py`, WP02, imports the core): `run_gh(args)`, `list_runs`, `failed_log`, `run_log_durations`, `load_state`, `write_bundle`, `render_markdown(model)`, `main()`.
- **Determinism** (NFR-004): enumeration pins `--limit`, sorts in-script; `state.json` records the run-id set (FR-015); output ordering stable.

### Capability B — ci-quality.yml seam (per architect-alphonso findings)

- **Draft fail-fast (FR-009)**: new **canceller** job, `needs:` the early suites, `if: failure() && github.event.pull_request.draft`, `permissions: actions: write`, calls `gh api .../runs/${{ github.run_id }}/cancel`. Added to `NON_BLOCKING_ALLOWLIST` (FR-016) so it never gates and the decision script's tripwire stays green. Race with in-flight jobs is accepted (spec Edge Cases).
- **Ready full-relevant-signal (FR-010)**: on `draft == false`, the diff-relevant chained suites carry `if: always() && <relevant>` so a failed upstream doesn't skip its relevant downstream; the existing `changes`/path-filter gates untouched domains out (full signal = full *relevant* signal). Chains that are pure resource-ordering become `always()`-guarded; logical prerequisites stay.
- **Merge-gate preserved (FR-011/C-003)**: the aggregate gate job reads `needs.<job>.result == 'success'` (real outcomes), never job conclusion masked by `continue-on-error`; **no `continue-on-error` on gating jobs**.
- **Red-first re-run (FR-018)**: persist the failing nodeids of a run as a keyed artifact/cache (`flake-lastfailed-<pr>`); on `synchronize`, a prioritized recheck step runs those nodeids first (`pytest <nodeids>` ahead of the full relevant suite); missing/renamed nodeids skip harmlessly. Pairs with the draft canceller for fastest red.
- **Ready-transition (FR-012)**: `ready_for_review` already in triggers; ensure the full-relevant run re-emits every required-check context so a draft's cancelled checks resolve.

## Key Design Decisions

1. **Signatures keyed on nodeids, not message substrings** (reviewer/architect): resilient to message drift; `needs_review` is the honest fallback, surfaced with a coverage % (FR-015).
2. **Half-open completion-time cursor + in-progress low-water mark** (FR-004): the only correct way to avoid both permanent-skip of straddling runs and double-count of re-runs; cursor never regresses even under manual `workflow_dispatch` backfill.
3. **Committed golden fixture** (FR-017): makes NFR-003 reproducible after the ~90-day `gh` retention window (C-006) ages out the live source.
4. **Canceller as non-gating allowlisted job**: keeps the merge-gate contract intact; the cancel is an ergonomics optimization, never a gate.
5. **Full signal = full *relevant* signal**: preserve path-filtering; do not run untouched-domain suites (operator steer).

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Canceller races/partially cancels; or trips gate invariant tests | Merge-gate breakage | Allowlist + `needs.<job>.result` gate; run `test_suite_jobs_gate_blocking.py`/`test_ci_quality_path_filters.py` in the WP (FR-016) |
| `continue-on-error` greens a required job | Silent un-gating | FR-011: forbid on gating jobs; gate reads real step outcomes; targeted test |
| Log-scraping brittleness / `--durations` absent in a suite | Wrong classification / zero samples | nodeid-keyed signatures; disclose suites lacking `--durations` (C-005); coverage metric |
| Weekly job unbounded on log download | NFR-002 miss | FR-008 caps + `--log-failed`/selective `gh api`; drop-logging |
| Artifact lineage lost (rename/retention) | Silent 30-day rescan | Stable artifact name, `retention-days: 90`, schema-validate `state.json`, label lost-baseline (FR-007) |
| Capability B only testable on a live PR | Weak acceptance | Static workflow-structure assertions + sandbox PR (SC-004) |

## Parallel Work Organization (seed for /tasks)

Dependency graph (→ = depends on):

- **WP01 — Flake-report pure core + unit tests** (Capability A): taxonomy (FR-001), classification + false-red formula (FR-002), duration aggregation (FR-003), delta/cursor (FR-004/005), coverage/input-set (FR-015). Pure functions + `test_flake_report_core.py`.
- **WP02 — gh IO shell, CLI, rendering, caps, fixture + fidelity test** → WP01: `run_gh`/enumeration/log-mining, `report.md` render, caps (FR-008), golden fixture (FR-017), `test_flake_report_fidelity.py` (NFR-003).
- **WP03 — Flake-report workflow** → WP02: `ci-flake-report.yml` weekly+dispatch, prior-artifact retrieval, retention, auth (FR-006/007/014, C-002/C-004).
- **WP04 — Draft canceller + ready relevant-signal + gate preservation** (Capability B): `ci-quality.yml` + `quality_gate_decision.py` edits (FR-009/010/011/012/016); guard tests green.
- **WP05 — Red-first re-run** → WP04 (same file): persist last-failed nodeids + prioritized recheck (FR-018).
- **WP06 — Runbook + changelog** → WP04/05: draft/ready contract + green-before-RFR (FR-013/SC-006); CHANGELOG.

WP01→WP02→WP03 is the Capability-A chain. WP04→WP05→WP06 is the Capability-B chain (same-file edits serialized to avoid conflicts). The two chains are independent and land in one consolidated PR.

## Phase Outputs

- Phase 0 (research): folded inline — architect-alphonso's `ci-quality.yml` findings + the squad metrics are the research basis.
- Phase 1 (design): [data-model.md](./data-model.md) (artifact/state schemas + signature-table contract).
- Phase 2 (tasks): `/spec-kitty.tasks` → WP files.
