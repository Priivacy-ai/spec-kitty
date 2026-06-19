# Audited surfaces (WP04 guard anchor)

Stable list of `src/specify_cli` modules that contain an untrusted-segment →
filesystem-sink call site (per `inventory.md`). WP04's architectural guard
anchors on this list so that any **new** untrusted→FS sink introduced in a
module here (or a new module added to it) is forced through the canonical seam
or an explicit disposition.

This file is intentionally machine-parseable: the list below is the
authoritative set; the `audit.py` discovery set must remain a subset of these
modules (plus the inventory-only `mission_metadata.py` FR-009 surface).

**Note (WP02/WP03 update):** Surfaces that were `routed-through-seam (TODO)`
and have been fully fixed by WP02/WP03 (i.e. no sinks remain in the
AST-discovered set) are removed from this file. The two-section split
(TODO vs already-safe) is maintained for the remaining surfaces.

## Surfaces with `routed-through-seam (TODO)` rows (deferred or in-progress)

- `src/specify_cli/cli/commands/agent/mission.py`    # CLI-arg, candidate list only
- `src/specify_cli/cli/commands/agent/tasks.py`      # CLI-arg, .exists() probe
- `src/specify_cli/cli/commands/decision.py`         # CLI-arg, load_meta read
- `src/specify_cli/cli/commands/merge.py`            # CLI-arg, .read_text()
- `src/specify_cli/mission_metadata.py`              # FR-009 meta.json write-path (WP02)
- `src/specify_cli/status/views.py`                  # _stale_check_slug → meta read (WP02)

## Surfaces already routed-through-seam (regression-guard targets)

- `src/specify_cli/missions/_read_path_resolver.py`
- `src/specify_cli/review/cycle.py`
- `src/specify_cli/status/aggregate.py`
- `src/specify_cli/status/lifecycle.py`
- `src/specify_cli/status/progress.py`
- `src/specify_cli/status/store.py`

## Surfaces with only trusted-source / unreachable rows (no fix; keep dispositioned)

- `src/specify_cli/audit/engine.py`            # trusted-source (mission index)
- `src/specify_cli/cli/commands/agent/workflow.py`    # trusted-source (wp.path.stem)
- `src/specify_cli/coordination/surface_resolver.py`  # unreachable (raise payload)
- `src/specify_cli/migration/mission_state.py`        # trusted-source (SHA-256 run_id) + WP03-fixed mission_slug
- `src/specify_cli/post_merge/review_artifact_consistency.py`  # unreachable (existence probe)
- `src/specify_cli/review/arbiter.py`          # unreachable (existence+glob probes after WP03 fix)
- `src/specify_cli/review/baseline.py`         # trusted-source (wp file stem)

## Canonical seams WP04 must require new sinks to use

- `assert_safe_path_segment` / `safe_mission_slug`  — `src/specify_cli/core/paths.py`
- `ensure_within_any` / `ensure_within_directory` / `write_text_within_directory`
  — `src/specify_cli/core/utils.py`
- Boundary delegators: `MissionStatus._validate_mission_slug`
  (`status/aggregate.py`), `_validate_segment` (`review/cycle.py`),
  `MissionIdResolver._is_safe_slug` (`status/store.py`),
  `reducer.safe_mission_slug` (`status/reducer.py`).
