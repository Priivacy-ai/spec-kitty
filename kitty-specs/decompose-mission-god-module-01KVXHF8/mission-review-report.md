# Mission Review Report — decompose-mission-god-module-01KVXHF8 (#2056)

**Reviewer:** post-merge independent audit (adversarial, evidence-based)
**Date:** 2026-06-25
**Baseline:** `origin/main` @ `c3814ec5a`
**Merged diff audited:** `origin/main..main` (squash `bc6cf3e07` + closeout `c518f20bd`)
**Verdict:** **PASS WITH NOTES**

---

## 0. Branch-topology finding (procedural, not a code defect)

The mission was **squash-merged into local `main`** (`bc6cf3e07`), and the closeout
commit (`c518f20bd`) sits on `main`. The decomposed code — the 363-LOC `mission.py`
shim and all 9 seam modules — lives on **`main`**.

`prog/2056-mission` (the branch the task brief named) is the **pre-decomposition
lane-integration branch**: its `mission.py` is still 4125 LOC and it contains NONE
of the seam modules. Auditing `origin/main..prog/2056-mission` would have reviewed
the wrong tree. The audit and all Part 1b gate fixes were therefore performed
against `main`, where the merged result actually is. **Part 1b fixes are committed
on `main`** (committing them on `prog/2056-mission` is impossible — the test files
reference seam modules that branch does not have).

---

## 1. FR trace (FR-001..007) — would each test fail if its impl were deleted?

| FR | Requirement | Test → Impl | Genuine? | Verdict |
|----|-------------|-------------|----------|---------|
| **FR-001** | Frozen 8-command CLI surface | `test_mission_cli_golden_contract.py` (16 passed) — CliRunner asserts `app --help` lists all 8 subcommands; each subcommand `--help` lists exact flags; success+error JSON envelopes. 28 subcommand-name assertions. | Yes — deleting a command registration drops it from `--help`, failing the golden. | **PASS** |
| **FR-002** | #2056 pointer comment + seam map | `mission.py:1-28` — SHIM pointer references #2056 + full WP02–WP08 seam map. | Yes (manual). | **PASS** |
| **FR-003** | 4-cluster seam split | 9 seam modules present + imported by shim (verified each has 1–4 refs; zero dead seams). 8 `app.command(...)` registrations each delegate to a seam fn. | Yes — orphan/import gates + golden. | **PASS** |
| **FR-004** | Per-seam focused tests ≥90% | 10 new per-seam/per-phase test files; pure parsers/resolvers get DIRECT unit tests (closes the Seam-C indirect-only gap). | Yes — tests call seam helpers directly. | **PASS** |
| **FR-005** | 3 mega-fns → ≤15-CC phase helpers | `finalize_tasks` 1227→~181 LOC; mission_finalize 40 private helpers, setup_plan 20, create 8. `ruff --select C901` exit 0 on all. INV-6 `_assert_no_write_in_validate_only` + 3 focused tests. | Yes — INV-6 raises-test fails if assertion deleted. | **PASS** |
| **FR-006** | Shim re-exports ~100 names | `test_mission_shim_reexports.py` (parametrized over full surveyed set). All edges resolve (`locate_project_root`, `_find_feature_directory`, `_show_branch_context`, `CommitToBranchResult`, `app`, 8 cmds, lifecycle/tasks imports). | Yes — dropping a re-export fails the gate at the shim. | **PASS** |
| **FR-007** | RELOCATE planning-commit residue → commit_router; repoint tasks.py | `_planning_commit_worktree`/`_resolve_planning_placement` defined in commit_router; `_stage_finalize_artifacts_in_coord_worktree` reconciled to alias of `_stage_artifacts_in_coord_worktree` (NOT forked); tasks.py imports both from commit_router; shim re-exports. `test_commit_router_planning_residue.py` (11 tests). | Yes — AST import-source check + INV-8 guard. | **PASS** |

No synthetic/false-positive tests found. The INV-6 negative test and FR-007 AST
import-source assertions are genuine (verified by inspection).

## 2. Critical cross-file check — tasks.py post-relocation (HIGHEST-RISK ITEM)

**CONFIRMED WORKING.** `tasks.py`'s two function-local imports of
`_planning_commit_worktree` / `_resolve_planning_placement` were correctly repointed
from `agent.mission` to `coordination.commit_router` (diff verified). Both relocated
symbols resolve from commit_router. The cross-file suite
(`-k "tasks or map_requirements or commit_router or write_surface"`) ran
**904 passed** on the planning-commit path (the lone failure was a test-isolation
flake, root-fixed — see §7).

- **INV-8 holds:** `commit_router.py` has **no** `cli.commands` imports (only
  `specify_cli.mission_metadata` + `specify_cli.missions._read_path_resolver`,
  both lower layers). `test_commit_router_has_no_cli_imports` passes.
- **Reconciliation, not fork:** `_stage_finalize_artifacts_in_coord_worktree`
  is `= _stage_artifacts_in_coord_worktree` (commit_router.py:539) — the
  near-duplicate collapsed into the canonical helper; no second copy.

## 3. INV-6 (validate-only zero-mutation) — PRESERVED

`_assert_no_write_in_validate_only` (mission_finalize.py:810) asserts the write
queue is empty under `--validate-only`; called in `finalize_tasks` (1570); 3
focused tests (pass-empty, raises-when-queued, noop-when-not-validate-only).

## 4. record_analysis shim gap — CLOSED

`test_protected_primary_spec_commit.py[record_analysis]` +
`test_wp06_sc2_paused_mission_blockers.py` → **5 passed**.
`_resolve_record_analysis_placement_ref` + `_enforce_analysis_report_write_preflight`
re-exported via shim.

## 5. Gates

| Gate | Result |
|------|--------|
| `pytest tests/specify_cli/cli/commands/agent` | **561 passed, 2 xfailed** |
| golden contract | **16 passed** |
| `ruff check` (mission.py + seams + commit_router) | **exit 0** |
| `ruff --select C901` (≤15) | **exit 0** |
| `tests/architectural/` (full) | **481 passed, 0 failed** after Part 1b fixes (was 7 failed) |
| `mypy --strict` (touched files) | 2 errors — see NOTE-1 (advisory gate) |

## 6. Issue-matrix & dead-code

- #2056 = `fixed`; #2058 = `deferred-with-followup` (#2058); #1623 =
  `deferred-with-followup` (#1623). All verdicts terminal.
- Every new seam module imported by the shim — **no dead seams**.
- acceptance-matrix.json overall_verdict `pass`, all 7 FR criteria `pass`.

## 7. Part 1b — mission-introduced CI-gate regressions FIXED (committed on `main`)

All 7 `tests/architectural/` failures were confirmed mission-introduced (all 7 PASS
on `origin/main` baseline). Fixed via each gate's intended mechanism — **no
suppressions, no gate-weakening**:

1. **`test_pytest_marker_convention`** — 9 new seam test files lacked module-level
   `pytestmark`. Added `[pytest.mark.unit, pytest.mark.fast]`.
2. **`test_gate_coverage::test_no_new_orphan_surfaces`** — 11 files selected by zero
   CI gates (`unit` is not a gate-selected marker). Added gate-selected markers:
   `fast` for the 10 `cli/commands/agent/` files (path-gated `fast` job),
   `git_repo` for `test_commit_router_planning_residue.py` (coordination integration
   gate selects `git_repo or integration`). The tests now actually run in CI.
3. **`test_untrusted_path_containment`** (2 tests) — the `mission_slug` path-join
   sink relocated `mission.py:317` → `mission_finalize.py:200`. Updated inventory.md
   row file:line + deferred-list entry (disposition unchanged: routed-through-seam
   TODO → #2037).
4. **`test_status_module_boundary`** — `mission_finalize.py` imported
   `status.bootstrap` / `status.wp_metadata` submodules directly. Routed through the
   `specify_cli.status` package facade (exported `BootstrapResult` + `_Builder` in
   `status/__init__.py`); import is now `from specify_cli.status import ...`.
5. **`test_topology_resolution_boundary`** — the UX-only worktree-navigation-hint
   predicate relocated `mission.py` → `mission_create.py`. Updated the existing
   allowlist entry's path (same documented non-routing predicate).
6. **`test_no_raw_mission_spec_paths`** — the decomposition introduced the literal
   `kitty_specs` identifier in source (new comments + a new fn
   `_validate_owned_files_not_in_kitty_specs`). Renamed the fn to
   `_validate_owned_files_not_in_mission_specs` (matching the existing
   `_invalid_mission_specs_owned_files` convention) and reworded 3 comments to
   describe the runtime-built alias without the raw literal — restoring origin/main's
   "no raw literal in source" convention.

Plus a **flakiness root-fix** (not architectural, but mission-introduced):
`test_mission_re_exports_relocated_symbols` used an `is`-identity assertion that
flaked when `tests/coordination/test_commit_router.py` `importlib.reload`s
commit_router. Replaced with a `__module__`-based relocation invariant (immune to
reload churn); verified the polluter + residue test now pass together (45 passed).

`test_tid251_enforcement.py` "No module named ruff" did NOT appear — ruff is
installed in the review venv; that test passed.

## NOTES (non-blocking)

- **NOTE-1 (HIGH) — mypy --strict not clean (SC-6/NFR-003 partial gap).** The
  full-package `mypy --strict src/specify_cli` rose from **15 errors (baseline)** to
  ~**27 (merged)**; the decomposition added ~11 `redundant-cast` + 1 `arg-type`
  error in `mission_finalize.py`/`mission_setup_plan.py`. After the §7.4 facade
  routing, only **2** strict errors remain on the touched files:
  `mission_parsing.py:137 no-any-return` (PRE-EXISTING — same fn was dirty as
  `mission.py:4125` on baseline) and `mission_finalize.py:834 arg-type` (a
  `dict[str,object]` invariance mismatch in the owned-files validator —
  mission-introduced). **CI's mypy job is advisory (not a hard gate)** and the
  baseline was already dirty, so this is not a CI-gate regression — but the spec
  promised mypy-strict-clean, so it is a fidelity gap worth a follow-up.
- **NOTE-2 (procedural) — branch topology.** See §0. The PR-ready branch is `main`
  in the clone, not `prog/2056-mission`.

## Conclusion

The decomposition is faithful to all 7 FRs: the CLI surface is frozen
(golden green), the 4 seams + per-family lifecycle modules are extracted with the
shim re-exporting every patch target, the 3 mega-functions are decomposed under the
C901 ceiling, INV-6 is preserved, and the planning-commit residue is relocated (not
deleted) into commit_router with tasks.py correctly repointed and INV-8 intact. The
only fidelity gap is mypy-strict (advisory, partially pre-existing). All
mission-introduced CI-gate (architectural) regressions are fixed at root.

**Verdict: PASS WITH NOTES.**
