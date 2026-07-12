# Phase 0 Research — CI Test-Topology Performance

Resolves the technical unknowns surfaced by the spec + post-spec squad. Format: Decision / Rationale / Alternatives.

## R1 — Runner core count on `ubuntu-latest` (gates the interim budget)
- **Decision**: Treat `ubuntu-latest` as **≥4 cores** for the NFR-001 interim (~18 min) but make the number **contingent** on the FR-001 `--durations` run; if the standard runner is 2-core, restate the interim as ~35 min and lean on the `next` shard matrix (FR-002) for the ≤7 min target.
- **Rationale**: `-n auto` scales with `os.cpu_count()`; `test-suite-acceleration-plan.md` records ~5 min (2-core) / ~2–3 min (4-core) uncertainty. The durations run produces ground truth before the shard table is authored.
- **Alternatives**: hardcode a worker count (`-n 4`) — rejected: brittle across runner classes; `-n auto` is the repo convention.

## R2 — Registering `next` in the coverage-preservation authority
- **Decision**: Wire `integration-tests-next`'s `-m next_shard_N` legs into `tests/architectural/_gate_coverage.py::same_tier_shard_counts` (exactly-one-shard-per-test over the parsed YAML) + the orphan ratchet (0-drop) + `test_required_selection_structures_present` (every `next_shard_N` present as a required matrix leg; extend `_REQUIRED_CORE_MISC_SHARDS`). Keep the marker-partition guard only as a *secondary* assignment check.
- **Rationale**: the squad proved the marker-partition guard proves assignment, not execution — it is false-green on skipped/cancelled/OOM legs. `_gate_coverage` already parses the workflow and models selection, which is the enforceable substrate.
- **Alternatives**: clone `test_arch_shard_marker_completeness.py` for `next` — rejected (false-green blind spot; also a D-044/C-003 clone).

## R3 — Coverage preservation across a *re-scope* (not just a shard)
- **Decision**: For path-narrowing WPs (slow-tests, integration-tests-* sweep), commit a **frozen baseline of pre-change collected node-ids per job** (`pytest --collect-only -q`) and have the guard fail on any symmetric-difference vs the post-change collection under the same `(paths − ignores, -m …)`.
- **Rationale**: partition-completeness over the *current* collection cannot detect a dir silently dropped by a narrowed filter; only a diff against the pre-change set can.
- **Alternatives**: trust `@slow`-location membership — rejected (location ≠ selection; `--ignore` can deselect a carrier inside a listed dir).

## R4 — Real-port family enumeration
- **Decision**: Commit `tests/_real_port_suites.py` listing the fixed-range `find_free_port_in_range` consumers (`test_orphan_sweep.py`, `test_daemon_orphan_classification.py`, `test_daemon_cleanup_boundary.py`, `test_issue_1071_singleton_reconfirmation.py`); generalize `test_serial_port_preservation.py` to assert none appear under `-n auto`. Ephemeral `bind(("127.0.0.1", 0))` binders are explicitly parallel-safe and excluded.
- **Rationale**: architect lens confirmed the existing guard hardcodes only `orphan_sweep`; FR-006's sweep of `integration-tests-sync` would scatter the rest.
- **Alternatives**: keep the single-file guard — rejected (the hidden family regresses on the first `-n auto` sweep).

## R5 — Feeding the Playwright / UI-e2e coverage into Sonar
- **Decision**: Two-track. (a) **Python** — add `--cov=src/specify_cli/dashboard --cov-append` (or the merged run's coverage) to the `ui-e2e.yml` `pytest tests/ui/` step and combine into `coverage.xml` so server-side dashboard code exercised by the e2e is credited. (b) **JS** — investigate Playwright/istanbul JS coverage → lcov → `sonar.javascript.lcov.reportPaths`; if export is impractical in CI time budget, fall back to `sonar.coverage.exclusions=**/static/**` (WP-J) and document the JS-coverage deferral.
- **Rationale**: `dashboard.js` (~720 lines, 0%) is exercised by Playwright but invisible to Sonar; the run carries no `--cov` at all today.
- **Alternatives**: only exclude static — rejected as the sole fix (loses real Python e2e credit); only wire JS — rejected (Python e2e credit is the cheaper, higher-value half).

## R6 — `--dist loadfile` single-file floor
- **Decision**: Balance the `next` shards on measured per-*file* durations (loadfile pins a file to one worker), and split any pathological single file (as in `fast-tests-cli`'s `test_charter_activate_commands.py`) so no file-chain exceeds the leg budget. Re-verify collection-equivalence per the ratchet after any file split.
- **Rationale**: sharding cannot beat the slowest single file under `loadfile`; the floor must be measured, not assumed.
- **Alternatives**: `--dist load` — prohibited (C-001: breaks file-scoped fixtures).
