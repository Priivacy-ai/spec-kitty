---
work_package_id: WP02
title: gh IO shell, CLI, markdown render, caps, golden fixture + fidelity test
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-008
- FR-014
- FR-017
- NFR-001
- NFR-002
- NFR-003
- C-001
- C-005
planning_base_branch: qa/test-hardening
merge_target_branch: qa/test-hardening
branch_strategy: Planning artifacts for this mission were generated on qa/test-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into qa/test-hardening unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
history: []
agent_profile: python-pedro
authoritative_surface: scripts/ci/
create_intent:
- scripts/ci/flake_report_cli.py
- tests/ci/test_flake_report_fidelity.py
- tests/ci/fixtures/flake_report/runs.json
- tests/ci/fixtures/flake_report/expected.json
- tests/ci/fixtures/flake_report/logs/
execution_mode: code_change
owned_files:
- scripts/ci/flake_report_cli.py
- tests/ci/test_flake_report_fidelity.py
- tests/ci/fixtures/flake_report/runs.json
- tests/ci/fixtures/flake_report/expected.json
- tests/ci/fixtures/flake_report/logs/
tags: []
tracker_refs: []
---

# WP02 — gh IO shell, CLI, render, caps, golden fixture

**Capability A** · profile: python-pedro · deps: WP01 · refs: FR-006, FR-008, FR-014, FR-017, NFR-001, NFR-002, NFR-003, C-001, C-005

## Objective

Create `scripts/ci/flake_report_cli.py` — the IO shell + CLI + markdown rendering — which **imports the pure core** from WP01's `scripts/ci/flake_report.py` (do NOT edit `flake_report.py`; it is WP01's owned file). Plus the committed golden fixture (with `logs/`) and the fidelity test. This makes the tool runnable and NFR-003-verifiable.

## Subtasks

- **T006 — gh IO shell (in `flake_report_cli.py`).** Thin, mockable wrappers importing the WP01 core: `run_gh(args)`, `list_runs(workflow, since, limit)` (pins `--limit`, sorts in-script), `failed_log(run_id)` via `--log-failed`, `run_log_durations(run_id)` grepping `\d+\.\d+s (call|setup|teardown) tests/…`. Auth via ambient `GITHUB_TOKEN` (no local unset path). Target workflow defaults to `ci-quality.yml`, `--workflow` overridable (FR-014).
- **T007 — Caps + drop-logging (FR-008/NFR-002/C-005).** Cap ≤200 classified failures, ≤50 most-recent duration-mined runs, per-fetch timeout; record `caps_applied.dropped`; disclose `suites_without_durations`.
- **T008 — Bundle + render (FR-006/C-001/NFR-004).** `load_state`, `write_bundle` → `metrics.json`/`durations.json`/`report.md`/`state.json` per data-model schemas; deterministic `render_markdown(model)` (headline table, buckets+false-red, delta-vs-prev, long-poles, coverage/caveats, lineage) — lives here in the CLI module, importing core helpers. `main()` CLI (`--workflow`, `--since`, `--state`, `--out`). **No repo commit / no docs writes** (C-001 enforced here).
- **T009 — Golden fixture + fidelity test (FR-017/NFR-003).** Freeze the reference window under `tests/ci/fixtures/flake_report/`: `runs.json` (trimmed `gh run list` JSON) + `logs/<run_id>.log` (trimmed `--log-failed`/durations excerpts — **required**: the classifier's inputs come from log text, so the fixture cannot omit logs) + `expected.json` (expected buckets, false_red_rate≈0.586, per-test medians). `tests/ci/test_flake_report_fidelity.py` feeds `runs.json`+`logs/` through the pure core, asserts within ±2pp (rate) / ±10% (median), that unmatched → needs_review, and one **markdown-determinism** assertion (same input → byte-identical `report.md` sans timestamps, NFR-004).

## Notes

- Clean pure/IO seam: the fidelity test drives the WP01 core with fixture data (no live `gh`). Prefer `--log-failed`/selective `gh api` over full-run-log zips (byte budget → NFR-002).
- Mark unit-ish tests `fast`. `ruff`/`mypy --strict` clean; complexity ≤ 15; hoist repeated literals (S1192).

## Done when

`flake_report_cli.py` runs end-to-end against the fixture producing all four artifacts (importing the WP01 core, not editing it); fidelity + markdown-determinism tests green; caps + disclosures present.
