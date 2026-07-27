# Phase 1 Contracts: Implement-Loop Friction Quick-Wins II

These are behavioral contracts (not HTTP APIs — this is an internal CLI mission). Each names the
observable input→output the fix must satisfy and the regression that pins it.

## C-A1 — Allocator uncommitted-artifact check (FR-001)

- **Given** `resolve_planning_artifact_staging` sees a `WP##.md` whose only porcelain diff vs the
  placement ref is `{shell_pid, shell_pid_created_at, base_branch, base_commit, planning_base_branch}`
  **Then** that file is dropped from the "uncommitted planning artifact" set (no block).
- **Given** the same file also has any other line changed **Then** it still counts (block preserved).
- **Pin**: `tests/specify_cli/cli/commands/test_implement_vcs_lock_claim.py` sibling + a sequential
  N-lane allocation test asserting 0 inter-allocation commits.

## C-A2 — Analysis-report freshness (FR-002)

- **Given** a pipe-table `tasks.md` whose only change is a status cell `[ ]`↔`[D]`/`[P]`/`[x]`
  **Then** `check_analysis_report_current` returns current (no `stale_analysis_report`).
- **Given** a substantive row-text change **Then** it returns stale.
- **Pin**: pipe-table sibling of `test_analysis_report_survives_subtask_checkbox_churn`.

## C-B1 — Pre-review gate interpreter + verdict (FR-003/004, C-004)

- **Given** `sys.executable -m pytest` fails (`No module named pytest`) but `uv run pytest` is green
  **Then** `run_scoped_tests_at_head` runs via `uv run` and returns a real `pass`/`fail` (not `no_coverage`).
- **Given** `uv` absent **Then** falls back to `sys.executable` without crashing.
- **Given** concurrent scoped runs **Then** they serialize (advisory lock); no false timeout `no_coverage`.
- **Given** the lock is contended **Then** lock-acquire uses its OWN timeout + fallback-to-run, decoupled
  from the 300s subprocess timeout (a lock-wait must never be charged against the run timeout).
- **Pin**: a regression under a pytest-lacking interpreter (monkeypatch `sys.executable` + fake `uv`);
  a concurrent-invocation test; a lock-wait-does-not-trip-run-timeout test. (Update the two existing
  real-subprocess tests that currently mask this.)

## C-B2 — Sub-agent long-gate contract (FR-005)

- **Contract**: a dispatched implement/review sub-agent polls the synchronous gate to completion; to
  skip, it uses `--skip-pre-review-gate` or the honored disable env; the orchestrator must not assume a
  silent hand-back. Documented in the implement-review skill/doctrine.
- **Pin**: skill/doc assertion (no product-code test).

## C-C1 — Manifest `output_path` portability (FR-006/NFR-004)

- **Given** an in-tree profile entry serialized **Then** the on-disk JSON `output_path` is repo-relative
  (no leading `/`, no home dir).
- **Given** a legacy absolute-path manifest loaded under a different `project_root` **Then** the
  reconstructed live `output_path` still `.exists()`-resolves (no migration).
- **Given** an out-of-tree entry **Then** it serializes absolute (fallback), like `source_path`.
- **Invariant**: in-memory `output_path` and the internal manifest key stay ABSOLUTE (`get_hash`/`.exists()`
  unaffected); only the on-disk JSON is relative.
- **Pin**: in-tree-relative-serialization test + absolute→relative tolerance test + a keying-invariant
  test (relative-store round-trip does not break `get_hash`) in
  `tests/specify_cli/tool_surface/profiles/test_manifest.py`.

## C-C2 — Issue-matrix schema-drift error (FR-007)

- **Given** a matrix whose mandatory column header is non-canonical **Then** the approval blocker leads
  with the schema-drift detail naming the offending/normalized column, and does not list all referenced
  issues as "Missing rows".
- **Pin**: malformed-column test in `test_tasks_parsing_validation.py`.

## C-C3 — Bulk-edit inference (FR-008)

- **Given** a spec with `refactor`+`update`+`change`+single `rename` on a non-bulk change **Then**
  `triggered is False`.
- **Given** "rename all occurrences …" / "rename … across the codebase" **Then** `triggered is True`.
- **Given** a **single-HIGH-phrase** bulk spec (score 3, no MEDIUM) **Then** `triggered is True` — this is
  the true-positive at risk from dropping the low-weight `+1` at `INFERENCE_THRESHOLD=4`; if it cannot
  pass at the current threshold, adopt the HIGH/scale co-occurrence fallback instead of lowering detection.
- **Pin**: all three cases in `tests/specify_cli/bulk_edit/test_inference.py`.

## C-D1 — setup-plan scaffold result (FR-009)

- **Given** a freshly-scaffolded plan with no populated content **Then** `result` is the new
  non-error state (`scaffolded`/`awaiting_content`), not `blocked` (via a net-new pristine predicate).
- **Given** a populated-but-insufficient plan **Then** `result == blocked`.
- **Given** a substantive committed plan **Then** `result == success` and it advances.
- **Invariant**: the specify side is already `scaffold_only: success` (no change); consumers of the new
  state — source prompts + the `next` engine result-switch (`engine.py:287-292`) — must not fall through
  on `scaffolded`.
- **Pin**: `test_mission_setup_plan_phases.py`; a `next`-engine test that the new state is handled;
  confirm source prompt templates + agent-copy regeneration.

## C-E1 — move-task coord-lane staging (FR-010/C-002)

- **Given** untracked planning artifacts on primary + a coord-topology lane **When** `move-task --to
  for_review` **Then** staging resolves via the authority path (`commit_router`/`resolve_planning_artifact_staging`)
  with no manual `git restore` dance and the lane branch never commits `kitty-specs/`.
- **Invariant (DUAL pin)**: (a) STATUS_STATE ref/event byte-identical pre/post vs merged #168, AND
  (b) zero `kitty-specs/` entries committed on the lane branch. NO `commit_guard.block_mission_specs`
  exemption; do NOT touch `_mt_resolve_status_placement_ref`/`_collect_status_artifacts`/`_primary_bundle_status_artifacts`.
- **Pin**: a coord-topology move-task regression asserting BOTH (a) and (b); an arch/unit guard that the
  IC-07 diff does not touch the three status-bundling symbols.
