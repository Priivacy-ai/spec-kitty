# Data Model: Close #2160 Coord-Shadows Read/Gate Arm

No new persistent entities — this mission operates on existing runtime/artifact structures. The
relevant entities and their invariants:

## Subtask row
- **Shape**: `- [ ] T### <desc>` / `- [x] T### <desc>` line in a WP's `tasks.md` section.
- **Invariant**: a row counts iff its id matches `T\d{3,}`, it is under the WP's section (first
  `WPnn` token in the heading), and it is not inside a fenced code block.
- **Section boundary (canonical)**: bounded by the heading whose first `WPnn` token is the WP; a
  re-appearing `## WPnn` heading does NOT re-enter a closed section (guard semantic).
- **Consumers**: lane-transition guard (block), dashboard (done/total), rollback (uncheck) — all via
  `core.subtask_rows._walk_wp_section`.

## Primary planning surface
- **Definition**: the partition holding `tasks.md`; resolved by
  `resolve_planning_read_dir(..., kind=MissionArtifactKind.TASKS_INDEX)`.
- **Invariant**: planning-artifact reads resolve here, never the coordination status husk; a missing
  coord-side `tasks.md` must NOT be interpreted as "no subtasks" (no fail-open).

## Claim markers
- **Fields**: `agent`, `shell_pid` in WP frontmatter (read via `task_utils` frontmatter readers).
- **Liveness**: `shell_pid` liveness is decided by `sync/daemon._is_process_alive` (one helper).
- **Invariant**: a live claim is never treated as stale (indicator) nor as a blocking stale claim
  (allocator); a rollback-to-`planned` clears both markers.

## Lane worktree (coord topology)
- **Invariant**: its sparse-checkout excludes coordination status artifacts
  (`status.events.jsonl`, `status.json`); a **recovered** lane must apply the same sparse-checkout as
  a freshly-created one (mirror `coordination_branch is not None` AND resolvable `short_id`).

## State transition touched
- `for_review` gate: `subtasks_complete` must be truthfully derived from the primary `tasks.md` at
  the emit layer; `WP → for_review` is blocked when any `T###` row in the WP section is unchecked and
  neither `--subtasks-complete` nor `--force` is asserted, on every code path.
