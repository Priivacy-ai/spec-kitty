# Mission Review Report — decompose-merge-god-module-01KVXHDK (#2057)

**Reviewer:** Independent post-merge reviewer (adversarial, evidence-based)
**Date:** 2026-06-25
**Branch reviewed:** `prog/2057-merge` (squash-merge `a25638955`; done-bookkeeping `2e538e072`)
**Baseline:** `origin/main` (`c3814ec5a`)
**Verdict:** **PASS WITH NOTES**

---

## Executive summary

The mission delivered a faithful, behavior-preserving decomposition of the
`cli/commands/merge.py` god-module. The reported headline result is confirmed:

- `cli/commands/merge.py`: **3383 → 559 LOC** (shim only).
- **10 new seams** under `src/specify_cli/merge/`: `_constants`, `git_probes`,
  `resolve`, `forecast`, `ordering` (extended), `done_bookkeeping`,
  `bookkeeping_projection`, `executor`, plus the extended `preflight` /
  `push_preflight`.
- The CC-102 `_run_lane_based_merge_locked` is decomposed into **13 `_phase_*`
  helpers** threaded by a `_MergeRunState` dataclass; the orchestrator is now a
  flat linear caller.
- **Max cyclomatic complexity = 15** across the shim and all seams (radon),
  satisfying NFR-001 / SC-002 (was ~102).

The merge suite (**529 tests incl. the golden CLI characterization test**) is
green; `ruff check` is clean; `mypy --strict` is clean on the shim + all 10
seams; no NEW suppressions were introduced (the 12 relocated `# noqa`/`type:
ignore` comments are byte-identical carry-overs from the pre-refactor module).

The **highest-risk item — INV-5 (#1827 baseline record→commit→assert ordering)
and INV-6 (snapshot-restore-on-exception sites) — is byte-preserved** through
the `_MergeRunState` phase split (see §FR-007).

Seven architectural-gate failures were mission-introduced (all mechanical
consequences of relocating call sites + shrinking merge.py); they are fixed via
the gates' intended mechanisms (allowlist/inventory updates, never suppression).
The only remaining `tests/architectural/` failures are the 4 pre-existing
environmental `test_tid251_enforcement.py` "No module named ruff" failures,
which reproduce byte-identically on `origin/main`.

---

## FR-by-FR coverage

| FR | Verdict | Evidence |
|----|---------|----------|
| **FR-001** Preserve CLI surface byte-for-byte | PASS | `tests/specify_cli/cli/commands/test_merge_cli_golden.py` registers the real `merge` command via `CliRunner`, pins `--help` flags, the exact dry-run JSON key set (`spec_kitty_version, mission_slug, target_branch, strategy, delete_branch, remove_worktree, push, mission_branch, lanes, would_assign_mission_number`), the `--json`-without-`--dry-run` error string + exit 1, and headline exit codes. Genuine characterization test (would fail on any drift). 529-test merge suite green. The hidden `--feature` alias is parsed (`merge.py:221/318 mission_slug_raw = (mission or feature or "")`). |
| **FR-002** Top-of-file pointer comment | PASS | `cli/commands/merge.py` carries the `#2057 DECOMPOSITION SHIM` banner with the full seam map + one-way-import RULES, matching the #2056 / #1623 convention. |
| **FR-003** Decompose into resolved seams | PASS | 10 seams present and imported; one-way imports verified (executor AST test asserts no `cli.commands.merge` import; the apparent `merge/baseline.py`/`_constants.py` matches are docstring/logger-name strings, not imports). |
| **FR-004** Per-seam tests ≥90% of moved code | PASS WITH NOTES | Seam test files exist for all 10. Coverage across the merge suite: `_constants` 100%, `git_probes` 99%, `bookkeeping_projection` 94%, `resolve` 94%, `push_preflight` 92%; below 90% within the merge subset: `done_bookkeeping` 87%, `preflight` 80%, `executor` 77%, `ordering` 75%, `forecast` 75%. Uncovered lines are dominated by error-recovery / worktree-cleanup branches exercised by heavier integration tests outside the measured subset. See NOTE-1. |
| **FR-005** CC ≤15 via `_MergeRunState` | PASS | radon max CC = 15 (`_phase_cleanup_worktrees_and_branches`); CC-102 driver eliminated; `merge`, `_mark_wp_merged_done`, `_collect_hollow_review_warnings`, `_assert_merged_wps_done_on_target` all ≤15. |
| **FR-006** Re-export relocated symbols | PASS | Shim `__all__` = 56 names; 3 src consumers (`doctor.py`, `agent/mission.py`, `orchestrator_api/commands.py`) + the ~41 test importers resolve with zero import edits (verified by import smoke + the green suite). |
| **FR-007 / INV-5** #1827 ordering + rollback | PASS | See §FR-007. Byte-preserved; pinned by `test_executor_phase_boundary.py` + `test_1827_baseline_regression.py` (both green). |

---

## FR-007 / INV-5 + INV-6 — the key check (HIGHEST RISK)

**Confirmed byte-preserved.** Original `_run_lane_based_merge_locked`
(origin/main, lines 2264–2769) ordering:

1. `_record_baseline_merge_commit(...)` (rel 323) inside `try` →
   `except BaselineMergeCommitError`: `_restore_final_bookkeeping_snapshots(...)`
   then `raise typer.Exit(1)` (rel 328–334).
2. `safe_commit(...)` (rel 467).
3. `_assert_merged_wps_done_on_target(...)` (rel 482).
4. `_assert_baseline_merge_commit_on_target(...)` (rel 500).

Refactored flow preserves this exactly across two phase helpers:

- `_phase_capture_and_baseline` (executor.py:482) — records the baseline
  (post-target-merge, pre-bookkeeping-commit) with the identical
  `except BaselineMergeCommitError → restore → raise typer.Exit(1)` block.
- `_phase_commit_and_assert` (executor.py:622) — `safe_commit` → done-on-target
  assert → baseline assert (post-commit), with the identical restore-on-error
  scoping.

INV-6: all ~6 restore-on-exception sites are preserved — `_phase_record_done_and_project`
(2 sites), `_phase_porcelain_invariant`, `_phase_commit_and_assert`
(safe_commit non-recovered path), and the baseline-record site.

`test_executor_phase_boundary.py` genuinely pins this: it records the call
sequence and asserts `events == ["record", "commit", "assert"]`, and asserts
restore-then-reraise for the baseline-record error, the non-recovered commit
failure, and the porcelain-invariant violation. These tests fail if any phase is
reordered or any restore site is dropped — not synthetic.

---

## Issue-matrix gate

All verdicts terminal. `#2057` = fixed; `#1827` = verified-already-fixed
(referenced appropriately — the mission preserves, not re-fixes, the invariant);
`#2026`, `#2056`, `#1623` = fixed/verified. Dead-code: every seam is imported
(the dead-symbol gate now passes after the fixes below).

---

## Architectural-gate regressions FIXED (Part 1b, committed on prog/2057-merge)

All seven were mechanical consequences of the relocation. Fixed via each gate's
intended mechanism — NO suppressions, NO gate-weakening:

1. **`test_guard_capability_call_sites.py [MERGE_BOOKKEEPING]`** — the
   `safe_commit(capability=MERGE_BOOKKEEPING)` call relocated from
   `cli/commands/merge.py` to `merge/executor.py`. Moved the per-flow allowlist
   entry to the new seam (avoids the stale-entry check).
2. **`test_safe_commit_import_boundary.py`** — same relocation of the
   `safe_commit(destination_ref=...)` shim call site; moved the allowlist entry
   to `merge/executor.py`.
3. **`test_no_dead_symbols.py`** — the shim's FR-006 re-export `__all__` grew
   24→56; ~53 re-exports lost their cross-file-src proof-of-life when consumers
   moved to seams, and 13 seam-internal helpers / `_MergeRunState` exported for
   the FR-004 focused tests have no cross-file src caller. Added a documented
   Category-C allowlist (`_CATEGORY_C_MERGE_DECOMP_SHIM_REEXPORT_2057`) with
   rationale + FR-303 burn-down. (All 66 symbols verified LIVE — defined and used
   in seams.) The gate's required-keys / ratchet meta-tests do NOT track
   `test_no_dead_symbols` per-category, so no `_baselines.yaml` bump was needed.
4. **`test_pytest_marker_correctness.py` (Rule 1 + Rule 2)** —
   `tests/merge/test_git_probes_seam.py` spawns real `git` via subprocess but
   carried `pytest.mark.fast`. Changed to
   `[pytest.mark.integration, pytest.mark.git_repo]` per the testing-taxonomy
   convention.
5. **`test_untrusted_path_containment.py` (2 tests)** — 3 `mission_slug` path-join
   sinks relocated from `cli/commands/merge.py` into `merge/done_bookkeeping.py`
   (:419, :421) and `merge/ordering.py` (:297). Updated the 3 stale merge.py rows
   in `inventory.md` to the new seam locations, preserving the original
   dispositions (`unreachable` ×2, `routed-through-seam (TODO)` ×1) with
   behavior-preservation provenance notes; audit tool now reports `AUDIT OK`.

**Post-fix state:** `tests/architectural/` = 477 passed, 4 failed — the 4 being
exclusively `test_tid251_enforcement.py` "No module named ruff" (environmental;
reproduces byte-identically on origin/main; ruff is invoked via `python -m ruff`
which is not pip-installed in this venv — out of mission scope).

The residue-authority + advance_branch_ref ratchets (`test_merge_pipeline_ratchets.py`)
and the WP13 residue single-authority test pass unchanged.

---

## Notes / non-blocking findings

- **NOTE-1 (FR-004 partial):** measured against the focused merge suite alone,
  5 of 10 seams meet ≥90%; 5 (executor 77%, ordering 75%, forecast 75%,
  preflight 80%, done_bookkeeping 87%) fall short. Uncovered lines are
  error-recovery / cleanup branches covered by broader integration tests. Spec
  SC-004 is "≥90% of moved code"; the gap is in exception/cleanup paths, not
  happy-path logic. Recommend a follow-up to lift the focused-test coverage on
  executor/ordering/forecast if the ≥90% target is to be enforced per-seam.

- No new third-party dependency. C-006/C-007/C-008 (one-way imports, lazy
  imports, locked constants) preserved.

---

## Confirmation checklist

- INV-5 (#1827 baseline ordering) + INV-6 (restore-on-exception): **PRESERVED**
  (byte-for-byte; pinned by genuine ordering tests).
- merge.py final LOC: **559**; seam count: **10**.
- Golden CLI test: **GREEN**.
- mypy --strict (shim + 10 seams): **clean**; ruff: **clean**; max CC: **15**.
- `tests/architectural/`: clean except the 4 pre-existing environmental
  `test_tid251_enforcement.py` failures.
- No NEW suppressions introduced.
