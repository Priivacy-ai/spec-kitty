# Research: Close #2160 Coord-Shadows Read/Gate Arm

Brownfield remediation mission — the design decisions were made by a 3-lens code squad
(reviewer-renata / paula-patterns / randy-reducer) and hardened by a 2-lens post-spec squad. This
file records the decisions rather than re-deriving them.

## Decision: one canonical subtask-row walk, guard-semantic wins
- **Decision**: Extract `_walk_wp_section` in `core/subtask_rows.py`; the counter's `break`-on-exit
  semantic is canonical; correct the uncheck writer's re-enter behavior to match.
- **Rationale**: the guard (`tasks_shared._check_unchecked_subtasks`) is the authority the lane gate
  blocks on; the dashboard and rollback must agree with it. The two aggregate walks already diverge,
  so "byte-identical to the aggregate" is impossible — a canonical choice is required.
- **Alternatives**: keep both walks (rejected — three parallel copies of the semantic); make the
  writer canonical (rejected — the guard is the gate authority).

## Decision: close the fail-open at the shared emit layer, not per-door
- **Decision**: fix `_infer_subtasks_complete` (row semantics + primary-surface resolution) at all
  four production callers; retire #2511's per-door pre-derivation.
- **Rationale**: randy proved the native `agent status` path still fails open via `aggregate.py:717`
  after #2511's orchestrator-only fix. A shared-layer fix closes the class on every path and reduces
  code (the per-door patch collapses).
- **Alternatives**: keep per-door patches (rejected — leaves the class half-open + duplicates logic).

## Decision: reuse `sync/daemon._is_process_alive`, do not add `os.kill`
- **Decision**: promote/centralize the existing psutil liveness helper; both the indicator and the
  allocator consume it.
- **Rationale**: a cross-platform, edge-hardened helper already exists; adding `os.kill` would be a
  parallel primitive (C-002 violation) and would need to re-solve NFR-004's platform safety.
- **Alternatives**: `os.kill(pid, 0)` (rejected — parallel impl, weaker platform handling).

## Verified-already-done: #1862 analysis-freshness checkbox-insensitivity
- `analysis_report._normalize_tasks_md` (#1764) already strips `[ ]`/`[x]` before hashing, wired to
  both `write_analysis_report` and `check_analysis_report_current`. #1862 is closed
  verified-already-fixed; the mission keeps only a regression guard (FR-009), no new logic.

## Verified-current: the vulnerable vs already-correct surfaces
- **Vulnerable**: the emit-layer `_infer_subtasks_complete` (fail-open + divergent regex) reached by
  `agent status --to for_review` and the orchestrator door.
- **Already correct (do not touch)**: the native `move-task` guard
  (`tasks_shared._check_unchecked_subtasks`) — resolves `TASKS_INDEX` + uses the canonical iterator.
