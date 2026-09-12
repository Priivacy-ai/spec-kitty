---
work_package_id: WP03
title: next cold-start performance benchmark + seeded baseline
dependencies:
- WP01
- WP02
requirement_refs:
- FR-003
- FR-006
planning_base_branch: perf/next-latency-durable-fix
merge_target_branch: perf/next-latency-durable-fix
branch_strategy: Planning artifacts for this mission were generated on perf/next-latency-durable-fix. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into perf/next-latency-durable-fix unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
phase: Phase 2 - Guard
history:
- timestamp: '2026-08-28T18:24:17Z'
  agent: system
  action: Prompt generated via tasks phase authoring
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/next/
create_intent:
- tests/specify_cli/next/test_next_cold_start_performance.py
execution_mode: code_change
model: ''
owned_files:
- tests/specify_cli/next/test_next_cold_start_performance.py
- tests/performance/baselines/Linux-CPython-3.11-64bit/**
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match.

---

## Objective

Guard the recovered `next` cold-start latency with a **statistical, off-PR** benchmark on the
existing performance pipeline, and seed a committed baseline reflecting the POST-fix latency
(WP01 + WP02 already landed in this WP's base). This is the replacement for the retired blocking
gate (removed in WP04).

## Context

- Depends on WP01 + WP02 — the baseline must reflect post-fix latency (FR-006). Ensure this WP's
  execution base includes both dependency lanes before measuring.
- Pipeline: `.github/workflows/performance.yml` (ADR `2026-08-22-1`) already has a `next` domain leg
  (`:99`, `paths: tests/next tests/runtime tests/specify_cli/next`) — NO workflow edit needed.
  Env-gated `SPEC_KITTY_RUN_PERFORMANCE=1`; compares against committed baselines with
  `--benchmark-compare-fail=median:50%`.
- Exemplar shape: `tests/review/test_verdict_save_performance.py`
  (`@pytest.mark.performance` + `@pytest.mark.benchmark(group=…)` + `benchmark.pedantic(...)`).
- Decision D4 in `research.md`: **subprocess-based** benchmark (cold-start = fresh process); an
  in-process `benchmark.pedantic` measures the wrong thing.
- Baselines dir: `tests/performance/baselines/Linux-CPython-3.11-64bit/` (only `0001_seed.json` today).

## Subtasks

T011 Add `tests/specify_cli/next/test_next_cold_start_performance.py`: a `@pytest.mark.performance` + `@pytest.mark.benchmark(group="next")` test that measures `spec-kitty next` cold-start via `benchmark.pedantic(lambda: subprocess.run([sys.executable, "-m", "specify_cli", "next", "--agent", "test", "--mission", "clean-install-fixture-01KQ22XX", "--json"], cwd=<fixture>, check=True, capture_output=True), rounds=5, warmup_rounds=1, iterations=1)`. Declare `pytestmark` (performance marker). Assert the subprocess returns 0. (WP03)

T012 Verify collection semantics: the test is SKIPPED on a normal run (no `SPEC_KITTY_RUN_PERFORMANCE`) and COLLECTED under `SPEC_KITTY_RUN_PERFORMANCE=1` in the `next` domain paths — matching `performance.yml`. Confirm it needs no workflow edit. (WP03)

T013 Seed the committed baseline reflecting POST-fix latency. FIRST guard against seeding a PRE-fix baseline (this WP branches from the mission base, not its dependency lanes — MEMORY: dependent WP needs manual dep-lane merge): confirm WP01 + WP02 are actually present in this worktree before measuring — merge the WP01/WP02 lane branches in if needed, and run `PYTHONPATH=src pytest tests/specify_cli/next/test_next_import_footprint.py tests/charter_runtime/test_freshness_cache.py -q` GREEN as the presence proof. THEN run `SPEC_KITTY_RUN_PERFORMANCE=1 PYTHONPATH=src pytest tests/specify_cli/next -m performance --benchmark-save=next --benchmark-storage=file://tests/performance/baselines` and commit the resulting `next` baseline JSON under `tests/performance/baselines/Linux-CPython-3.11-64bit/`. Note in the file/PR that CI-runner absolute numbers differ from local warm-FS; the relative-delta compare is what guards. (WP03)

T014 Document (in the test docstring) that the first CI run with no matching baseline is a pass (pytest-benchmark exit 4, handled by `performance.yml`), and that baseline refresh goes through the workflow_dispatch `update_baseline` path (the pipeline never auto-commits baselines). (WP03)

## Branch Strategy

Planning branch and final merge target: `perf/next-latency-durable-fix`. This WP depends on WP01
and WP02; its execution base must include both. Merge back into `perf/next-latency-durable-fix`.

## Definition of Done (observable in this diff)

- `test_next_cold_start_performance.py` exists, is `performance`-marked and subprocess-based, and passes under `SPEC_KITTY_RUN_PERFORMANCE=1`.
- It is not collected on a normal PR run (env-gated off).
- A committed `next` baseline JSON exists under `tests/performance/baselines/Linux-CPython-3.11-64bit/` reflecting post-fix latency.
- No `.github/workflows/` edit required (the leg already exists).

## Risks / Reviewer guidance

- Pinned `rounds`/`iterations=1` is mandatory — pytest-benchmark auto-calibration on a ~1s subprocess balloons CI time.
- Reviewer: confirm the benchmark is subprocess-based (not in-process), the marker is declared, and the seeded baseline is the post-fix measurement (not a pre-fix or fabricated number).
- New test file → the marker-convention gate applies; run `tests/architectural/test_pytest_marker_convention.py` (and the marker baseline) locally.
