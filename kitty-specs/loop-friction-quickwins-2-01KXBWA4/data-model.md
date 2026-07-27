# Phase 1 Data Model: Implement-Loop Friction Quick-Wins II

This mission mutates behavior around existing artifacts rather than introducing new schemas. The
"entities" are the artifacts the guards read/write and the invariants each fix must preserve.

## E-01 — WP runtime frontmatter (in `tasks/WP##.md`)

- **Fields**: `shell_pid`, `shell_pid_created_at`, `base_branch`, `base_commit`, `planning_base_branch`.
- **Nature**: dynamic runtime state written by a claim; NOT operator-authored planning content.
- **Invariant (FR-001)**: a WP file whose only diff vs the placement ref is these fields must not
  block the allocator's uncommitted-artifact check; any *other* diff still blocks. (#2093 lineage.)

## E-02 — Analysis-report freshness hash inputs

- **Inputs**: normalized digest of `spec.md`, `plan.md`, `tasks.md` (+ charter).
- **Invariant (FR-002)**: status-cell churn (`[ ]`↔`[x]`/`[X]`/`[D]`/`[P]`) — bullet OR pipe-table —
  is normalized out of the `tasks.md` digest; a change to substantive row text still changes it.

## E-03 — Pre-review gate verdict

- **States**: `pass` / `fail` / `no_coverage` (inconclusive) / timeout→`no_coverage`.
- **Interpreter**: resolved via `uv run` (project venv) with `sys.executable` fallback.
- **Invariant (FR-003/004)**: when `uv run pytest` is green, the verdict is a real pass/fail — never
  `no_coverage` due to a missing-pytest interpreter or a contention-driven false timeout. Gate still
  enforces by default (skip only via the shipped `--skip-pre-review-gate` / disable env).

## E-04 — `agent_profiles_manifest.json` entry

- **Fields**: `id`, `file_hash`, `source_hash`, `source_path` (already repo-relative), `projection_version`,
  `output_path` (**target of this mission**).
- **On-disk invariant (FR-006/NFR-004)**: `output_path` for an in-tree entry is stored repo-root-relative
  (POSIX), out-of-tree falls back absolute; the reader reconstructs an absolute live Path from either
  form. In-memory `output_path` and the internal manifest key stay absolute.

## E-05 — Issue-matrix approval blocker message

- **Shape**: a human-facing blocker string; carries `ISSUE_MATRIX_SCHEMA_DRIFT` diagnostics with a
  `detail` (found/normalized columns).
- **Invariant (FR-007)**: when a mandatory column is malformed, the message leads with the schema-drift
  detail (offending/normalized column); "Missing rows: …" appears only when rows actually parsed.

## E-06 — Bulk-edit inference score

- **Fields**: `triggered: bool`, `matched_phrases: list`, weighted keyword sum vs `INFERENCE_THRESHOLD`.
- **Invariant (FR-008)**: `LOW_WEIGHT_KEYWORDS` contribute to `matched_phrases` (display) but not to the
  `triggered` sum; a genuine bulk edit ("rename all occurrences", "rename … across the codebase") still
  yields `triggered = True`.

## E-07 — setup-plan/setup-specify result

- **States**: `success` / `blocked` / (**new**) `scaffolded`/`awaiting_content`.
- **Invariant (FR-009)**: first happy-path scaffold write yields the new non-error state; a
  populated-but-insufficient artifact still yields `blocked`; a substantive committed artifact yields
  `success`. Slash-command templates that branch on `result` handle the new state.

## E-08 — move-task planning-artifact staging (coord topology)

- **Surfaces**: `commit_guard.block_mission_specs` (lane-branch `kitty-specs/` protection), the staging
  resolver in `tasks_move_task`.
- **Invariant (FR-010/C-002)**: staging routes through the established authority path; the lane branch
  is never asked to commit `kitty-specs/`; STATUS_STATE placement semantics are byte-for-byte unchanged
  vs merged #168.
