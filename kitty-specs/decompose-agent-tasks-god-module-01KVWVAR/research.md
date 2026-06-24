# Research — Phase 0: Decompose agent/tasks.py god-module

**Mission**: 01KVWVARJKSH9T2QNHJVE4ZC7Y · **Date**: 2026-06-24 · **Branch**: main (`c3814ec5a`)
**Method**: 3 parallel read-only Explore agents (seam map · coupling/commit-router trace · test-coverage audit) over `src/specify_cli/cli/commands/agent/tasks.py` (4633 LOC) and its collaborators.

---

## TL;DR / Decisions

| # | Decision | Resolution | Evidence |
|---|----------|------------|----------|
| D1 | **Seam set** (FR-003) | 5 extracted seam modules + a thinned command shim. See §2. | seam-map agent |
| D2 | **Verification strategy** (resolves spec C-005) | **Capture golden CLI characterization tests BEFORE refactoring**, then keep the existing 72 unit tests green. Existing coverage is seam/import-heavy but contract-light (only 1 help-text assertion, 2 smoke tests) — function-importing tests would survive a move silently while the CLI contract drifts undetected. | coverage agent §3,§5 |
| D3 | **Residual-size target** (resolves spec NFR-004) | Binding target is **maxCC ≤ 15 for every function** (the real defect driver). LOC target: **tasks.py ≤ ~1200 LOC** residual (from 4633), achieved by extracting ~1800 LOC of helpers into 5 seams AND internally decomposing the 6 mega-functions. A literal "tiny registration shim" is NOT realistic in one mission — the command bodies carry genuine orchestration. | seam-map agent §1,§5 |
| D4 | **Commit-routing scope re-grounding** (FR-006/007/008) | **The issue/PR-2060 premise has drifted — see §3.** There are **3 tails, not 4**; protected-primary now **refuses → feature branch** (the silent-skip-to-coord behavior was already removed in WP02/WP03); and an FR-008-style test already exists. Re-scope to: route the 3 tails through the centralized `commit_for_mission` router and delete the now-redundant bespoke pre-checks. | coupling agent §2 |

---

## 1. The public CLI surface (the frozen contract — C-001/FR-001)

Single typer app `app` (`tasks.py:716`, `name="tasks"`, `no_args_is_help=True`) with **9 commands**:

| Command | Handler | Lines | ~LOC | Complexity |
|---------|---------|-------|------|-----------|
| `move-task` | `move_task()` | 1824–2601 | **778** | EXTREME |
| `mark-status` | `mark_status()` | 2956–3220 | **265** | HIGH |
| `list-tasks` | `list_tasks()` | 3223–3305 | 83 | Low |
| `add-history` | `add_history()` | 3308–3384 | 77 | Low |
| `finalize-tasks` | `finalize_tasks()` | 3387–3604 | **218** | HIGH |
| `map-requirements` | `map_requirements()` | 3607–3988 | **382** | EXTREME |
| `validate-workflow` | `validate_workflow()` | 3991–4082 | 92 | Low |
| `status` | `status()` | 4085–4567 | **483** | EXTREME |
| `list-dependents` | `list_dependents()` | 4570–4632 | 63 | Low |

Plus a non-command helper that is itself a god-function: **`_validate_ready_for_review()` (1377–1724, 348 LOC)** — touches research-artifact validation, worktree state, merge ancestry, and contamination checks. It must be sub-decomposed regardless of which seam it lands in.

**The complexity is concentrated in 6 functions** (`move_task`, `status`, `map_requirements`, `_validate_ready_for_review`, `mark_status`, `finalize_tasks` ≈ 2474 LOC / 53% of the file). File-splitting alone will NOT satisfy maxCC ≤ 15 — these bodies must be internally flattened/extracted too.

## 2. Proposed seams (D1 — resolves FR-003)

Five extracted modules adjacent to `tasks.py`, plus the residual shim. One-way dependency only (seams never import `tasks.py`).

| Seam (proposed file) | Members (approx) | ~LOC | Existing test trust |
|----------------------|------------------|------|---------------------|
| `tasks_outline.py` — tasks.md/manifest parsing, WP-id resolution | `_normalize_task_id_input`, `_match_history_wp_heading`, `_extract_pipe_table_wp_id`, `_resolve_history_wp_id`, `_is_pipe_table_task_row`, `_parse_pipe_table_header`, `_wp_id_exists`, `_resolve_wp_id`, WP regex consts | ~180 | MEDIUM (+30 LOC isolated parser test) |
| `tasks_materialization.py` — frontmatter/file persistence, markdown mutation | `_collect_status_artifacts`, `_persist_inline_subtask_status`, `_materialize_inline_subtask_status`, `_update_pipe_table_status`, `_resolve_checkbox`, `_resolve_pipe_table`, `_persist_review_artifact_override`, `_persist_review_feedback` | ~185 | MEDIUM (+80 LOC error cases) |
| `tasks_finalize_validation.py` — dependency/cycle validation, lane metadata | `_is_backward_transition`, `_lane_targets_for_emit`, `_wp_lane_from_status_events`, `_read_transactional_wp_lane`, + cycle/frontmatter loop extracted from `finalize_tasks` | ~230 | HIGH (no new tests) |
| `tasks_dependency_graph.py` — dependency readiness/gating glue | `_check_dependent_warnings`, `_behind_commits_touch_only_planning_artifacts`, dependent-gating extracted from `move_task` | ~165 | LOW (+50 LOC readiness test) |
| `tasks_parsing_validation.py` — readiness/verdict/issue-matrix validation | `_issue_matrix_*` (7 fns), `_validate_ready_for_review` (sub-split), `_self_review_fallback_option_error`, `_get_latest_review_cycle_verdict`, `_apply_review_status_flags` | ~485 | STRONG (no new tests) |
| **`tasks.py` (residual shim)** — typer app + 9 thinned command bodies + orchestration glue | the 9 `@app.command` handlers, reduced to dispatch/option-unpack/emit | ~800–1200 | LOW (needs golden CLI test) |

**Suggested extraction order** (dependency-aware, lowest-risk first): outline → materialization → finalize-validation → dependency-graph → parsing-validation → final shim-thinning pass.

**Shared module-level state to relocate carefully** (touched by multiple seams): `TASKS_MD_FILENAME`, `SPEC_MD_FILENAME`, `_QUALIFIED_TASK_ID_RE`, `_VALID_VERDICTS`, `_FORWARD_ORDER`, `_RUNTIME_STATE_DENY_LIST`, WP/inline regexes, and the `TaskIdResolutionOutcome/Format` enums + `TaskIdResult` dataclass.

## 3. Commit-routing: the premise has DRIFTED (D4 — critical)

The issue comment (from PR #2060, written against an older `tasks.py`) said: *"the planning-commit tails were NOT migrated to commit_for_mission … 4 sites … silently skip commits on protected primaries rather than routing to the coord worktree."* **The current code tells a different story:**

1. **There are 3 commit tails, not 4:**
   - `move_task()` → `safe_commit(...)` at **`tasks.py:2486`** (WORK_PACKAGE_TASK; uses `resolve_placement_only`)
   - `mark_status()` → `safe_commit(...)` at **`tasks.py:3131`** (TASKS_INDEX; uses `resolve_placement_only`)
   - `map_requirements()` → `safe_commit(...)` at **`tasks.py:3947`** (WORK_PACKAGE_TASK; resolves worktree via `_planning_commit_worktree` imported from `mission.py:3928`)

2. **The tails are already kind-aware** — they call `resolve_placement_only(...)` / `_planning_commit_worktree(...)` with explicit `MissionArtifactKind`, so they are NOT the naive hardcoded `CommitTarget(ref=target_branch)` the comment implies. They were partially migrated by the "write-surface-coherence WP02/WP03" work.

3. **Protected-primary behavior changed:** `commit_for_mission` (`coordination/commit_router.py:98–141`) now **refuses** planning commits to a protected primary and tells the user to use a feature branch (`status="no_op_wrong_surface"`, `commit_router.py:160–178`). The historical "route to coordination worktree" fallback was **removed** (WP02/WP03). So the comment's "should route to coord worktree" remedy is stale.

4. **An FR-008-style regression test already exists:** `tests/specify_cli/cli/commands/test_wp03_bypass_writers_fr008.py:139–206` asserts the refusal diagnostic names the feature-branch remedy and does NOT mention the coord worktree.

**Re-grounded scope for FR-006/007/008** (still valuable, just re-aimed):
- **FR-006 →** Route the 3 tails through the single `commit_for_mission` entry point instead of open-coding `resolve_placement_only`+`safe_commit` (and, for tail 3, the `_planning_commit_worktree` import from `mission.py`). This is the real "centralize the router" win the comment wanted. *Gap:* tail 3 must thread `target_branch=` for the WP09 ff-advance (currently absent at the call site).
- **FR-007 →** Once routed, the bespoke pre-checks become dead: `_skip_target_branch_commit()` (`954–971`), `_protected_branch_status_commit_error()` (`921–932`), their guard conditionals in `move_task` (2448–2470) and `mark_status` (3021–3029), and the `_planning_commit_worktree` import (3928). The `is_protected` reads at `924` and `970` go with them.
- **FR-008 →** Extend the existing test rather than duplicate it: add a `tasks.py`-level regression proving each of the 3 tails routes through `commit_for_mission` (assert router invoked / refusal surfaced), since current tests still patch the direct `safe_commit` path.

> ⚠️ **Behavior-change nuance:** routing through `commit_for_mission` shifts the protected-primary error from a *pre-check message* to a *router result* (`no_op_wrong_surface` diagnostic). The user-visible message text changes. This must be acknowledged (it touches FR-001's "output unchanged" — these are error paths on protected primaries, an intended behavior change under FR-006, not a regression). **Decision point for the user — see questions below.**

## 4. Coupling & circular-import risk

- **dependency_graph** (`core/dependency_graph.py`, 391 LOC) is imported at `tasks.py:53` and called at `1215/1221` (move_task warnings) and `4603/4604` (validate_workflow). It imports only from `status.py`, never from `cli/commands/` → **no cycle; LOW extraction risk.** The two call sites stay in the shim; the seam needn't import it.
- An extracted commit seam would re-import: `git.safe_commit`, `mission_runtime.{CommitTarget,MissionArtifactKind,resolve_placement_only,resolve_topology,routes_through_coordination}`, `core.commit_guard.GuardCapability`, `git.protection_policy.ProtectionPolicy`, `core.paths.*`, `status.{Lane,resolve_lane_alias,feature_status_lock}`, `missions._read_path_resolver`.
- **Enforce one-way imports:** seams must never import back into `tasks.py`. Seam↔seam imports (e.g. materialization↔outline) are fine across separate files.

## 5. Test-coverage baseline (informs D2)

- ~72 core tests across 9 files (notably `test_tasks.py` 1054 LOC, `test_tasks_canonical_cleanup.py` 863 LOC, `test_tasks_helpers.py` 602 LOC).
- **Strong:** parsing-validation helpers, finalize-validation. **Weak:** command-registration contract (1 help assertion), dependency readiness, package-materialization error paths.
- **No golden CLI contract test** pinning command names / flags / exit codes / `--json` envelope. This is the single biggest refactor risk and the reason for D2.
- New test work estimate: **~410 LOC** (golden CLI ~150, protected-primary routing ~100, materialization errors ~80, readiness ~50, isolated parser ~30).

---

## Open questions / risks feeding `/spec-kitty.plan`

1. **R1 (commit-routing behavior change):** Adopting `commit_for_mission` changes the protected-primary error *message text* on the 3 tails. Confirm this intended behavior change is acceptable, and that we update/extend the affected assertions rather than treat them as regressions. *(User decision — surfaced below.)*
2. **R2 (mega-function decomposition):** Hitting maxCC ≤ 15 requires internally decomposing `move_task` (778), `status` (483), `map_requirements` (382), `_validate_ready_for_review` (348), `finalize_tasks` (218), `mark_status` (265) — this is more than file-splitting and is the bulk of the effort. Plan must budget for it.
3. **R3 (scope size):** ~1800 LOC moved + 6 mega-functions decomposed + ~410 LOC new tests + golden-test capture is a large mission. The plan should slice this into independently-mergeable WPs (likely one per seam + one for the commit-routing fix + one for golden-test capture), respecting dependency order.
4. **R4 (`_planning_commit_worktree` shared helper):** tail 3 imports it from `mission.py`. If `commit_for_mission` fully internalizes worktree resolution, confirm `mission.py`'s own use is unaffected (out of scope to change mission.py here).
5. **R5 (golden-test framework):** Decide capture mechanism (inline snapshots vs `pytest-snapshot`) — no snapshot dependency exists in the suite today.
