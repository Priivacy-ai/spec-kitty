# Audited mission-surface-resolution surfaces (WP01 / FR-003)

Machine-produced anchor for WP08's guard. This file lists every surface
classified `routed-through-resolver` or `raw-bypass` in `inventory.md`.
`topology-blind-by-design` surfaces are excluded — they are intentionally
primary-only and not guarded by WP08's resolver-routing enforcement.

WP08's guard should assert:
- every `raw-bypass` surface is converted (by WP06/WP07) to a
  `routed-through-resolver` surface before the mission lands, OR
- the raw-bypass is retained with an explicit inventory annotation explaining
  why the bypass is safe (diagnostic payload, seam primitive definition, etc.).

---

## Canonical resolver surfaces (routed-through-resolver)

These surfaces correctly route through a blessed resolver. WP08's guard should
verify they continue to do so after WP06/WP07 refactoring.

| surface | resolver used | notes |
| --- | --- | --- |
| `mission_runtime/resolution.py:184` | `resolve_mission_read_path` | Single runtime entry point (`_resolve_mission_slug`) |
| `mission_runtime/resolution.py:603` | `resolve_status_surface` | Status-surface dir resolution (`_resolve_status_surface_dir`) |
| `mission_runtime/resolution.py:612` | `candidate_feature_dir_for_mission` | Fallback in `_resolve_status_surface_dir` |
| `mission_runtime/resolution.py:817` | `candidate_feature_dir_for_mission` | Handle canonicalization in `resolve_placement_only` |
| `specify_cli/coordination/status_transition.py:223` | `candidate_feature_dir_for_mission` | `_canonical_primary_feature_dir` lane-worktree fallback |
| `specify_cli/coordination/status_transition.py:232` | `resolve_status_surface_with_anchor` | `_canonical_primary_feature_dir` single-pass resolution |
| `specify_cli/coordination/status_transition.py:240` | `candidate_feature_dir_for_mission` | `_canonical_primary_feature_dir` malformed-meta fallback |
| `specify_cli/coordination/surface_resolver.py:450` | `resolve_status_surface_with_anchor` | `resolve_status_surface` thin wrapper |
| `specify_cli/coordination/surface_resolver.py:484` | `candidate_feature_dir_for_mission` | `resolve_status_surface_with_anchor` single-pass entry |
| `specify_cli/core/mission_creation.py:328` | `mission_dir_name` (grammar seam) | `create_mission` — seam output, not raw slug |
| `specify_cli/missions/_read_path_resolver.py:405` | `resolve_mission_read_path` | `candidate_feature_dir_for_mission` definition |
| `specify_cli/missions/feature_dir_resolver.py:46` | `resolve_mission_read_path` | `resolve_feature_dir_for_slug` shim |
| `specify_cli/review/cycle.py:185` | `_validate_segment` seam | Validated `parts.mission_slug` before join |
| `specify_cli/status/aggregate.py:314` | `resolve_status_surface` | `MissionStatus._resolve_read_dir` |
| `specify_cli/status/aggregate.py:449` | `candidate_feature_dir_for_mission` | `_find_meta_path` handle-aware fallback |

---

## Raw-bypass surfaces (FR-001 targets)

These surfaces bypass the resolver. WP06/WP07 must address them or document
why the bypass is safe (diagnostic-only payloads).

| surface | slug composed | bypass context | severity |
| --- | --- | --- | --- |
| `specify_cli/status/aggregate.py:430` | `mission_slug` | `_find_meta_path` initial primary lookup; coord-topology handle resolution deferred to fallback at :449 | HIGH — functional bypass (S8 residual); WP06 target |
| `specify_cli/coordination/surface_resolver.py:429` | `mission_slug` | `_coord_mid8` fail-closed raise payload (`StatusReadPathNotFound`); diagnostic path only, no FS open/write | LOW — diagnostic; inside resolver module |
| `specify_cli/coordination/surface_resolver.py:434` | `mission_slug` | Same `_coord_mid8` raise: `primary_candidate` diagnostic Path; no FS sink | LOW — diagnostic; inside resolver module |
| `specify_cli/cli/commands/decision.py:464` | `mission_slug` | Pre-resolver primary meta read for `mission_id` derivation; followed by `resolve_mission_read_path` at :476 | MEDIUM — unguarded outside blessed module; WP07 target |
| `specify_cli/status/aggregate.py:668` | `mission_slug` | `MissionMetadataUnavailable` raise payload (`meta_path`); slug pre-validated; diagnostic only | LOW — diagnostic; slug pre-validated |
| `specify_cli/status/aggregate.py:669` | `mission_slug` | `MissionMetadataUnavailable` raise payload (`primary_candidate`); diagnostic only | LOW — diagnostic; slug pre-validated |

---

## Topology-blind-by-design surfaces (NOT guarded by WP08)

These surfaces deliberately target the primary checkout. They are correct and
should NOT be converted to coord-aware resolver calls.

| surface | rationale |
| --- | --- |
| `mission_runtime/resolution.py:218` | `_mid8_from_primary_meta` — coord surface has no `meta.json` |
| `mission_runtime/resolution.py:541` | `_resolve_coordination_branch` — C-GUARD-3a |
| `mission_runtime/resolution.py:573` | `_resolve_mission_id` — C-GUARD-3a |
| `specify_cli/coordination/surface_resolver.py:517` | `resolve_status_surface_with_anchor` config re-anchor — FR-003 cascade layer 1 |
| `specify_cli/missions/_read_path_resolver.py:438` | `primary_feature_dir_for_mission` definition — this IS the topology-blind primitive |
