# Implementation Plan: Retire Standalone Tasks CLI

**Mission**: retire-standalone-tasks-cli-01KWAMQ3
**Branch contract**: current = base = merge-target = `mission/retire-standalone-tasks-cli` (PR'd upstream to `Priivacy-ai:main`)
**Spec**: [spec.md](./spec.md)
**Status**: Plan (Phase 1 complete)

## Summary

Net-removal mission with one small additive port. Delete the dead, test-only standalone tasks CLI in all three copies, reconcile the ~17 test files that reference it (delete / surgical-split / leave), preserve its one unique capability (acceptance-artifact encoding normalization) as an opt-in `--normalize-encoding` flag on the supported `spec-kitty accept`, and shed the architectural-ratchet entries the deletion unblocks. No product behavior change; coverage is preserved by the real-surface suites.

## Technical Context

- **Language/Version**: Python 3.11+
- **Primary Dependencies**: standard library for the change itself (the `argparse` surface is being *removed*; `typer` already backs `spec-kitty accept`); `pytest`, `ruff`, `mypy` for gates. No new runtime dependencies.
- **Storage / State**: none introduced. Acceptance/status/merge state stays in the canonical `status.events.jsonl` + `meta.json` model.
- **Testing**: `pytest` (parallel `-n auto --dist loadfile`); architectural ratchet meta-tests under `tests/architectural/`; ATDD-first per charter C-011.
- **Target platform**: cross-platform CLI (Linux/macOS/Windows), package `spec-kitty-cli`.
- **Project type**: single Python package (`src/specify_cli/`) + test suite (`tests/`).
- **Performance goals**: n/a (net code removal; no hot-path change).
- **Constraints**: charter C-004 burn-down (ratchet only shrinks), C-007 `__all__` convention, terminology canon (Mission not feature); no production importer of `specify_cli.scripts.tasks.*` may break (spec C-001).

## Charter Check

- **ATDD-First (C-011)**: the only *added* behavior is the `accept --normalize-encoding` flag (FR-005) — written red-first via NFR-004 tests. Deletions are guarded by the suite collecting + passing.
- **Burn-down Policy (C-004)**: this mission *shrinks* four ratchet/allowlist surfaces (FR-007); baselines recomputed to live sizes, never grown.
- **`__all__` Convention (C-007)**: removed modules' `__all__` leave with them; no charter/kernel `__all__` touched.
- **Terminology Canon**: deletion + one flag; verified by `test_no_legacy_terminology`.
- No charter conflicts; no exceptions requested.

## Engineering Alignment

The work is dominated not by the deletions but by **reconciling the test suite**: ~17 test files reference the surface and must be deleted, surgically split, or left, and one shared helper (`tests/utils.py::write_wp`, used by **40 files**) must be repointed to the canonical helper. The standalone CLI is dead at product runtime in all three copies; its product behavior is fully duplicated by the real-surface suites (NFR-002 map), with exactly one unique capability — encoding normalization — preserved by FR-005.

## Phase 0 — Research (resolved)

Full findings in [research.md](./research.md). Key resolutions:

- **FR-008 (consumer migration) → RESOLVED: no migration needed** (decision `01KWANGYM89NRT5KNAHVGX8BF5`). The standalone CLI is not deployed to consumer projects (absent from init/upgrade templates + release packaging); the historical consumer path `.kittify/scripts/tasks/` is already swept by the existing `m_0_10_0_python_only` migration; the packaged `src/specify_cli/scripts/tasks/` leaves the wheel automatically on deletion.
- **Merge-metadata coverage → accepted loss.** `_prepare_merge_metadata`/`_finalize_merge_metadata` (only in the dead CLI) wrap `record_merge`/`finalize_merge`, which have **zero production callers** — the canonical merge path writes WP-done status events, never `meta.json` `merge_history`. Nothing to port; delete `TestMergeToleranceMalformedMeta` only. (Out-of-scope follow-up: `record_merge`/`finalize_merge` become production-dead — future dead-symbol sweep.)
- **FR-005 without-flag behavior already exists.** `collect_feature_summary` reads via `_read_text_strict` → raises `ArtifactEncodingError(AcceptanceError)` whose message already says *"Run with --normalize-encoding to fix automatically"*; `accept.py:318` catches `AcceptanceError` → exit 1, writes nothing. FR-005 only needs to (i) add flag wiring delegating to canonical `normalize_feature_encoding(repo_root, feature) -> list[Path]`, mirroring the standalone control flow at `scripts/tasks/tasks_cli.py:156-205` (no standalone logic carried over, C-003), and (ii) test the three paths.

## Phase 1 — Design

### Surfaces deleted (FR-001/002/003)
- `scripts/tasks/{tasks_cli.py, task_helpers.py, acceptance_support.py}`
- `.kittify/overrides/scripts/tasks/` (3 files)
- `src/specify_cli/scripts/tasks/` (3 files + now-empty package)

### FR-004 / FR-009 — test reconciliation classification
**DELETE** (pure standalone scaffolding): `tests/cross_cutting/misc/test_tasks_cli_commands.py`; `…/test_task_helpers.py`; `tests/specify_cli/scripts/test_task_helpers.py`; `tests/specify_cli/scripts/tasks/test_tasks_cli.py` (+ remove the empty `tests/specify_cli/scripts/` package tree); `tests/specify_cli/test_standalone_tasks_cli_canonical.py`.

**SURGICAL** (keep canonical assertions, drop dead-module ones):
- `tests/utils.py` — **critical path**: repoint `write_wp`'s `from task_helpers import …` (`:109`) → `from specify_cli.task_utils.support import append_activity_log, build_document, set_scalar, split_frontmatter` (behaviorally equivalent — `split_frontmatter`/`build_document`/`append_activity_log` byte-identical; `set_scalar` same output via `re.search`). Used by **40 files**. The `TASKS_DIR` sys.path injection (`:9-13`) + `run_tasks_cli` (`:35-36`) are NOT removed here — they stay until WP04 (see Work-package shape: removing them while DELETE-class files still exist breaks collection).
- `tests/cross_cutting/misc/test_acceptance_support.py` — **SURGICAL, not delete** (post-plan gate finding): 19 tests, **8 drive the real `spec-kitty accept` via `CliRunner`/`cli_app`** (diagnose-JSON skipped/failed checks, no-commit merge-pending non-mutation, matrix/meta/events non-mutation, corrupt-`lanes.json` blocking) — these 6 behaviors are NOT duplicated elsewhere; the `acc.*` calls resolve to canonical `specify_cli.acceptance` through the thin re-export shim. Swap the module-level imports (`import acceptance_support as acc` → `from specify_cli import acceptance as acc`; `import task_helpers as th` → canonical `task_utils.support`), repoint any `run_tasks_cli` seeds to the real CLI / `emit_status_transition`, keep the 8 real-CLI tests + the canonical-engine `acc.*` tests (relocate under `tests/specify_cli/acceptance/` if the cross_cutting path is torn down), and re-home only the `normalize_feature_encoding` + encoding-error assertions onto the FR-005 tests. Delete only any standalone-API-shape-only test.
- `tests/conftest.py` — delete the `ensure_imports` fixture (`:737-741`) in **WP04** (co-located with the DELETE-class files it serves), after confirming no consumers.
- `tests/specify_cli/test_feature_metadata.py` — delete only `TestMergeToleranceMalformedMeta` (`:856-972`); keep canonical `record_merge`/`finalize_merge` tests.
- `tests/specify_cli/acceptance/test_accept_pre30_hard_reject.py` — keep `test_collect_feature_summary_rejects_pre30` + helpers; delete standalone-command imports/tests; **add** a thin real-CLI regression (CliRunner on `_pre30_repo`) pinning `accept.py:305` (exit 1 + "spec-kitty upgrade" + no commit).
- `tests/specify_cli/test_acceptance_regressions.py` — delete T014 + T016 (standalone help + acceptance_support API-alignment); keep canonical regressions.
- `tests/upgrade/test_pre30_guard_wiring.py` — delete the `tasks_cli.*_command` arms; keep canonical `pre30_guard` wiring tests.
- `tests/specify_cli/test_lane_regression_guard.py` — delete `_standalone_task_scripts` + its parametrized test; keep the src-rglob runtime guard.
- `tests/specify_cli/test_codebase_sweep.py` — delete the now-vacuous standalone-scripts sweep test (canonical src sweep remains).

**LEAVE** (assert absence / canonical false-positives — no edit): `tests/cross_cutting/misc/test_template_compliance.py`, `tests/upgrade/test_migration_python_only_unit.py`, `tests/git_ops/test_atomic_status_commits_unit.py`, `tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py`.

**Exit invariant**: after FR-004, `grep -r "specify_cli.scripts.tasks" tests/` returns nothing and the suite collects + passes.

### FR-005 — encoding port (only added behavior)
Add `--normalize-encoding/--no-normalize-encoding` (default off) to `spec-kitty accept` (`cli/commands/accept.py`). On `ArtifactEncodingError` from `collect_feature_summary`: flag off → existing behavior (exit 1; message already references the flag); flag on → call canonical `specify_cli.acceptance.normalize_feature_encoding(repo_root, feature)`, report repaired paths, re-collect, proceed. No standalone code copied (C-003).

### FR-007 — ratchet shed (recompute live per C-002)
- `test_no_dead_symbols.py`: remove the `acceptance_support::*` block (13) + `task_helpers::*` block (21) = 34 entries.
- `test_no_dead_modules.py`: remove the 3 `specify_cli.scripts.tasks.*` `_CATEGORY_3` entries.
- `test_gate_read_literal_ban.py`: remove the `…tasks_cli.py::list_command` residual entry.
- `resolution_gate_allowlist.yaml`: remove the `_prepare_merge_metadata` write-site entry.
- `surface_resolution_audit/{inventory.md,write_candidate_classification.yaml}`: remove stale rows; `test_coord_read_residuals_closeout.py`: comment-only cleanup.
- `_baselines.yaml`: set `test_no_dead_symbols.category_b_grandfathered_legacy` and `test_no_dead_modules.category_3_external_cli_entrypoints` to **post-edit live frozenset sizes** (recompute, do not hand-count). `test_gate_read_literal_ban` / `resolution_gate_allowlist` have no `_baselines.yaml` entry — their shrink is the in-file removal.

### NFR-002 coverage map (summary; full table in research.md)
Lane transitions → `tests/status/*` + `tests/agent/*`; rollback → `test_emit_backward_transition.py`; list/history/status-identity → `test_status_cli.py` + `tests/status/*`; verify/accept-checklist/perform_acceptance → `tests/specify_cli/acceptance/*` + `tests/agent/test_commands.py`; merge teardown/clean-tree/dry-run/squash → `tests/lanes/test_merge*.py` + `test_recovery_post_merge.py`; staging isolation → `test_finalize_coord_staging.py`. **One accepted loss** (merge-metadata malformed-JSON tolerance). **Two gaps closed by FR-005** (`normalize_feature_encoding` + encoding-error behavior gain real-surface tests for the first time).

## Risks

| Risk | Mitigation |
|------|------------|
| `tests/utils.py::write_wp` repoint breaks 40 files | Canonical `task_utils.support` helpers verified byte-equivalent; land the repoint first and run the full suite before other deletions. |
| Baseline numbers hand-miscounted | Recompute `len(frozenset)` live after edits (C-002); ignore the stale inline justification counts. |
| A missed importer fails at collection | FR-004 exit invariant greps `specify_cli.scripts.tasks` to zero across `tests/`; CI `integration-tests-core-misc (architectural)` confirms. |
| SC-5 hard-reject loses command-surface proof | FR-009 adds a thin real-CLI pre-3.0 reject regression (engine-level test already survives). |

## Work-package shape (guidance for /spec-kitty.tasks)
Strictly-linear chain (each gate depends on the prior). **Sequencing constraint (post-plan gate):** the `tests/utils.py` sys.path injection + `run_tasks_cli` are what make the bare module-level imports in the DELETE-class files resolve; they must NOT be removed before those files are deleted, or collection breaks. So:
1. **WP01** — repoint `tests/utils.py::write_wp` import **only** (one-line swap to canonical `task_utils.support`); leave the sys.path injection + `run_tasks_cli` in place; full suite green. Isolates the 40-file blast radius first.
2. **WP02** — FR-005 encoding port on `spec-kitty accept` + NFR-004 tests (red-first).
3. **WP03** — surgical test reconciliation (FR-004/FR-009): repoint/split the behavior-bearing test files (incl. `test_acceptance_support.py` reclassification) so nothing surgical imports the standalone surface, while the modules still exist; suite green.
4. **WP04** — delete the 3 standalone copies (FR-001/002/003) + DELETE-class tests + remove `tests/utils.py` sys.path injection & `run_tasks_cli` & `conftest.py::ensure_imports` (now safe — consumers gone) + pyproject (FR-006) + FR-007 ratchet shed + `_baselines.yaml` live recompute; suite collects + architectural suite green.

(Exact WP slicing is the `/spec-kitty.tasks` author's call; this is guidance, not a binding decomposition.)

## Encoding-authority boundary (post-plan gate — recorded decision)
Two production encoding-repair engines exist and must stay distinct:
- **`spec-kitty validate-encoding --fix`** → `text_sanitization.sanitize_directory` (also drives the dashboard scanner). Proactive cleanup of `**/*.md`; normalizes valid-UTF-8 smart quotes/dashes too (em-dash → `---`, en-dash → `--`).
- **`spec-kitty accept --normalize-encoding`** (FR-005) → `acceptance.normalize_feature_encoding`. Gate-time byte-recovery: only rewrites `PRIMARY_ARTIFACT_FILES` that actually **fail** UTF-8 decode (em-dash → `--`, en-dash → `-`).

FR-005 deliberately delegates to `normalize_feature_encoding` (NOT the `validate-encoding` engine) because `accept`'s need is fail-closed byte-recovery at the acceptance gate, mirroring the retired standalone surface's exact behavior — not proactive whole-tree cleanup. The two maps' divergent dash output is **intentional and recorded here** so a later agent does not "unify" them and silently change `accept`'s repair output. (Note: `normalize_feature_encoding` has zero production callers today — FR-005 gives it its first; "canonical" means it is the canonical home of this logic, not that it is currently wired.)

## Out-of-scope follow-up (tracked)
Once the standalone CLI is gone, `mission_metadata.record_merge`/`finalize_merge` become production-dead (zero callers; only the deleted CLI invoked them). They are invisible to the dead-symbol ratchet because `mission_metadata.py` has no `__all__` — the same test-shielded-dead-symbol pattern this mission targets. Removing them expands blast radius into canonical `mission_metadata.py` (must prove nothing reads `meta.json` `merge_history`), so it is deferred to a **separate tracked follow-up issue** (to be filed at merge per DIR-003), not folded here.
