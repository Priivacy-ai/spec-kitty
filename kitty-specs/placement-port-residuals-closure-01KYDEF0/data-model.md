# Data Model — Placement-Port Residuals Closure

This mission persists **no new entities**. The "model" here is the set of
partitions, artifact kinds, gates, and capabilities the fixes must respect.
Captured so the invariants are explicit for /tasks and review.

## Partitions & artifact kinds (existing — `src/mission_runtime/artifacts.py`)

| Artifact kind | Partition | Home resolver | Relevant FR |
|---------------|-----------|---------------|-------------|
| `PRIMARY_METADATA` (`meta.json`, `status_phase`) | PRIMARY | `resolve_artifact_surface(...).path` (directory) | FR-001 |
| `STATUS_STATE` (`status.events.jsonl`) | COORD (under coord topology) | coord ref via port | FR-002, FR-008, FR-011 |
| `TRACER_FILE` (`traces/`) | COORD | `placement_seam(...).read_dir(kind)` | FR-006 |

**Invariant (I-01)**: `resolve_placement_only(kind)` returns a branch `CommitTarget` (a ref); the on-disk directory home comes from `resolve_artifact_surface(...).path`. FR-001 asserts on the directory, not the ref.

**Invariant (I-02)**: `status.events.jsonl` is a COORD artifact under coord topology. No fix may relocate it to PRIMARY (bounds FR-002's read/write decoupling).

## Legacy runtime state (existing — `backfill_runtime_state.py`)

- `LegacyWPRuntime.has_evictable_state()` → true when `shell_pid`/`agent`/`assignee`/`tracker_refs`/`subtasks`/completed `review` present. Drives the FR-002 silent-loss repro.
- `backfill_runtime_state(dir)` currently couples READ (`dir/tasks/*.md`) and WRITE (`append_events_atomic_verified(dir, …)`). FR-002 splits these into a read-dir (PRIMARY) and event write-dir (COORD).

## Architectural gates (test-side invariants this mission reconciles)

| Gate | Invariant | Reconciliation |
|------|-----------|----------------|
| `test_no_write_side_rederivation` | every `CommitTarget`/`safe_commit` ref is seam-derived OR allow-listed | FR-008: allow-list `executor.py` coord-seed (dated rationale) |
| `test_guard_capability_call_sites[MERGE_BOOKKEEPING]` | each non-standard capability authorizes exactly one flow; others assert STANDARD | FR-012: extend `_PROTECTED_FLOW_ALLOWLISTS["MERGE_BOOKKEEPING"]` with `executor.py` |
| `_placement_whole_tree_scan` | every unsanctioned `src/` module scanned; sanctioned via per-file entry or retained prefix | FR-003: `migration/` prefix → per-file entries (keep `mission_runtime/`, `upgrade/migrations/`) |
| `test_no_raw_mission_spec_paths` | constant-based mission-spec path construction stays in constructor files | FR-009: route via constructor OR allow-list `mission_repair.py` |
| `test_mission_cli_golden_contract` | mission CLI exposes exactly the frozen command + flag surface | FR-010: `repair` → `_EXPECTED_COMMANDS`(9) + `_EXPECTED_FLAGS["repair"]`; rename count test |

## State transition touched (status model — unchanged shape)

`status_phase` flip: legacy → snapshot-authority, written once by `_flip_phase`.
FR-001 changes only *where the write target is resolved* (through the port); the
transition itself is unchanged. FR-002 changes only *which leg the seed frontmatter
is read from*. No new lanes, events, or phases are introduced.
