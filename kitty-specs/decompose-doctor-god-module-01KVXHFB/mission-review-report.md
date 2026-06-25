# Mission Review Report — decompose-doctor-god-module-01KVXHFB (#2059)

**Reviewer:** post-merge independent auditor (adversarial, evidence-based)
**Branch:** `prog/2059-doctor` (squash-merge `3917c43d3`) · **Baseline:** `origin/main` (`c3814ec5a`)
**Date:** 2026-06-25

## Verdict: PASS WITH NOTES

The decomposition is faithful to the spec, behavior-preserving, and gate-clean.
Five CI-gate regressions of the #2058-hygiene class (orphan `__all__` symbols,
missing test pytestmarks, stale path inventory) were introduced by the mission
and have been **fixed in this review** using each gate's intended mechanism
(no suppressions, no gate-weakening). The remaining note is a non-blocking
SC-002 LOC-target overshoot and an environmental perf-budget flake.

---

## FR trace (FR-001..FR-007)

| FR | Claim | Evidence | Would-the-test-fail-if-impl-deleted? | Verdict |
|----|-------|----------|--------------------------------------|---------|
| FR-001 | Frozen 16-subcommand CLI surface | `test_doctor_cli_surface_golden.py` (38 tests) pins names by set-equality, param arity, `--help` snapshots, and the 3 load-bearing names. `d.app.registered_commands == 16` live. | YES — deletes/renames flip set-equality + arity asserts. | adequate |
| FR-002 | `#2059` pointer comment preserved | `doctor.py:1-14` carries the ORCHESTRATION SHIM block + `issues/2059` URL; `test_doctor_shim_reexports::test_pointer_comment_references_issue_2059`. | YES. | adequate |
| FR-003 | 9 siblings extracted + doctrine seam completed | 9 new modules present (`_doctor_shared`, `_doctrine_collect`, `_identity_audit`, `_command_surface_doctor`, `_mission_state_doctor`, `_coordination_doctor`, `_sparse_checkout_doctor`, `_workspace_husk_doctor`, `_daemon_doctor`). `_doctrine_health.py`/`_profile_health_render.py` untouched (collectors moved into `_doctrine_collect`). Byte-pinned doctrine-selections snapshot green. | YES — collector tests + snapshot exercise the moved code. | adequate |
| FR-004 | Per-sibling focused tests ≥90% | Acceptance matrix records per-sibling coverage 90–100%; 268 focused tests in the 11 new files run green under `-m fast`. | YES — focused per-helper tests call extracted helpers directly. | adequate |
| FR-005 | 6 mega-functions decomposed ≤15 CC | `ruff check --select C901 src/specify_cli/cli/commands/` → All checks passed. `mission_state` `# noqa: C901` dropped (NI-002 confirmed absent). | YES — C901 gate fails on any >15-CC relocation. | adequate |
| FR-006 | 11 private symbols + `app` re-exported; names preserved | `test_doctor_shim_reexports.py` parametrizes every contracted symbol; resolves from `specify_cli.cli.commands.doctor`. Subcommand-name strings owned by `@app.command` shells (compat/safety + argv fast-paths unaffected). | YES — import resolution test fails if a re-export is dropped. | adequate |
| FR-007 | H1 single console home + H2 function-local merge import | H1: single `Console()` lives in `_profile_health_render.py`, re-exported via `_doctor_shared`; every sibling imports `console` from `_doctor_shared` (no per-module `Console()` in the doctor cluster — `_auth_doctor.py` is out of scope). H2: `from specify_cli.cli.commands.merge import path_is_under_worktrees` is indented inside `_check_tracked_worktrees_content` (`_coordination_doctor.py:131`). `import doctor; import merge` runs clean. | YES — `test_doctor_shared` single-Console identity + `test_coordination_doctor` AST not-module-level + import-cycle regression. | adequate |

**All seven FRs are backed by tests that would fail if the implementation were
deleted.** No synthetic/false-positive tests identified. The golden harness
(WP01-first) is genuine characterization, not a tautology.

## H1 / H2 re-verification (grep)

- H1: `Console()` instantiated exactly once in the doctor cluster
  (`_profile_health_render.py:51`); `_doctor_shared` re-exports it; `doctor.py`
  + every `_*_doctor` sibling import `console` from `_doctor_shared`. Confirmed.
- H2: merge import is function-local (`_coordination_doctor.py:131`, indented).
  No module-level `from ...merge` in `_coordination_doctor.py` (NI-001 confirmed
  absent). Confirmed.

## Subcommand-name preservation

`app` exposes 16 commands; the 3 load-bearing names (`skills`,
`restart-daemon`, `sparse-checkout`) are owned by the `@app.command` shells in
`doctor.py`. `tests/cli_gate/test_doctor_modes.py` + `test_safe_commands.py`
green (in the 457-pass doctor+cli_gate run). compat/safety_modes + `__init__.py`
argv fast-paths unaffected.

## Behavior-preserving / dead-code check

- Moves not rewrites: diff is relocation + thin-shell delegation + decomposition
  helpers; logic preserved. Byte-pinned doctrine snapshot + 457-test doctor suite
  green confirm output stability (NFR-004).
- Dead-code: after the `__all__` prune (see below), every sibling is imported
  from `doctor.py` and the symbol-level dead-code gate passes — no orphan public
  symbols, no orphan modules.

## Gate results (run in clone)

| Gate | Result |
|------|--------|
| `pytest tests/specify_cli -k doctor` | 427 passed; 1 env flake (perf budget, see notes) |
| Golden CLI surface + shim/shared/coordination contract tests | 110 passed |
| `ruff check` doctor.py + all `_*` siblings (incl. C901≤15) | All checks passed (exit 0) |
| `mypy --strict` doctor.py + 9 new siblings | Success: no issues in 10 files |
| `pytest tests/architectural/` (after fixes) | **481 passed, 0 failed** |
| doctor suite + `tests/cli_gate/` (perf flake deselected) | 457 passed |

## Issue-matrix gate

`issue-matrix.md`: #1623 verdict = **fixed** (terminal). Evidence cites WP03
moving the doctrine-health COLLECTORS to `_doctrine_collect.py`, completing the
MODEL/RENDER/COLLECT triad; byte-pinned doctrine-selections snapshot green. All
verdicts terminal. Gate satisfied.

---

## CI-gate regressions introduced by the mission (FIXED in this review)

All fixed via each gate's intended mechanism — no suppressions, no
gate-weakening:

1. **Symbol-level dead-code gate** (`test_no_dead_symbols::test_no_public_symbol_in_all_is_unimported`):
   the 9 siblings listed ~40 intra-module private helpers in `__all__` that no
   other `src/` file imports (functionally dead under the gate's runtime
   semantics). **Fix:** pruned each sibling's `__all__` to its true cross-module
   public contract (the `run_*` entrypoints + the FR-006 test-facing symbols
   `doctor.py` re-exports). This is the gate's sanctioned "remove the name from
   `__all__`" remedy — preferred over allowlisting (the allowlist is a shrink-only
   ratchet whose baseline test would have tripped on ~40 new entries). All
   contracted re-exports still resolve; ruff/mypy clean.

2. **pytest-marker convention** (`test_pytest_marker_convention`): the 11 new
   seam test files carried no module-level `pytestmark`. **Fix:** added
   `pytestmark = [pytest.mark.fast]` to each (they are sub-second pure-logic
   module tests; `fast` is gate-selected by `fast-tests-cli`).

3. **Gate-coverage orphan surface** (`test_gate_coverage::test_no_new_orphan_surfaces`):
   the same 11 files were selected by zero CI gates. **Fix:** the `fast` marker
   (above) places them in the `fast-tests-cli` selection — they now actually run
   in CI rather than being baselined as never-running.

4. **Stale untrusted-path / short-id inventory**
   (`test_no_worktree_name_guess::test_shortid_allow_list_entries_are_real` +
   `::test_two_doctor_sites_produce_distinct_composite_keys`): the two
   `mission_id[:8]` diagnostic-tolerance sites moved from `doctor.py` into
   `_coordination_doctor.py` (same functions, byte-identical lines). The
   composite keys are unchanged, but the gate's file-path stale-detection map and
   the distinct-keys test hard-coded `doctor.py`. **Fix:** repointed
   `_SHORTID_ALLOWED_SITES_FILES` + the distinct-keys test + the baseline
   composition comment to `_coordination_doctor.py`. The narrow allow-list
   entries are not widened; the `[:8]` baseline raw count (7) is unchanged.

Post-fix: `tests/architectural/` = 481 passed, 0 failed. No suppression added.

## Notes (non-blocking)

- **SC-002 LOC target:** doctor.py is **1060 LOC** vs the "target ≤~400 LOC"
  in SC-002. SC-002 says "target ~400"; the file is a legitimate thin shim
  (16 `@app.command` shells with full typer flag/help signatures + the
  re-export block) — the residual LOC is unavoidable typer boilerplate, not
  retained logic. Reduction 3434→1060 (-69%) meets the de-godding intent.
  Treat as an advisory miss, not a contract failure.
- **Environmental perf flake:** `test_doctor_ops.py::test_sweep_enumeration_perf_1k_files`
  fails on this machine (0.55–0.82s vs 0.5s budget). The test and the swept
  implementation are **byte-identical to origin/main** (zero diff) — this is a
  machine-speed budget flake, not a mission regression. Per the flakiness
  policy, tune the budget at the root if it recurs on CI; do not retry-to-green.
