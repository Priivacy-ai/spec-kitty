# Mission-surface-resolution callsite inventory (WP01 / FR-003)

Generated input: `python tests/architectural/surface_resolution_audit/audit.py`
walks `src/specify_cli` and `src/mission_runtime`. The audit tracks:

1. **All resolver/topology-blind calls inside the canonical seam source files**
   (`RESOLVER_SOURCE_STEMS` in `audit.py`).
2. **All raw-bypass path joins** (`KITTY_SPECS_DIR / slug`) anywhere in the
   source trees.

Dispositions are human-verified against the cited source — see `RULESET.md`
for the full vocabulary and false-negative classes.

**Scope note:** The 144 downstream callers that legitimately call
`resolve_feature_dir_for_mission` / `candidate_feature_dir_for_mission` /
`resolve_feature_dir_for_slug` outside the seam files are summarized in the
"Routed caller summary" section below. They are classified
`routed-through-resolver` by definition and are not tracked row-by-row because
the matcher's job is to prevent bypass under-counting, not to enumerate every
blessed call.

## Sink table

| file:line | handle source | sink | disposition | rationale |
| --- | --- | --- | --- | --- |
| mission_runtime/resolution.py:184 | slug | resolve_mission_read_path | routed-through-resolver | `_resolve_mission_slug` → `resolve_mission_read_path`; slug validated by `assert_safe_path_segment` inside the resolver (NFR-002). Single canonical runtime entry point (FR-030). |
| mission_runtime/resolution.py:218 | repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `_mid8_from_primary_meta` reads primary-checkout `meta.json` to derive mid8. The coord surface carries no `meta.json`. Topology-blind by design (C-GUARD-3a). |
| mission_runtime/resolution.py:541 | primary_root | primary_feature_dir_for_mission | topology-blind-by-design | `_resolve_coordination_branch` anchors `meta.json` read on primary only — reading through the coord-aware resolver would flip topology (C-GUARD-3a split-brain rationale). |
| mission_runtime/resolution.py:573 | primary_root | primary_feature_dir_for_mission | topology-blind-by-design | `_resolve_mission_id` reads `meta.json` from primary; same C-GUARD-3a rationale as :541. |
| mission_runtime/resolution.py:603 | primary_root | resolve_status_surface | routed-through-resolver | `_resolve_status_surface_dir` → `resolve_status_surface` (the single status-surface authority IC-01). |
| mission_runtime/resolution.py:612 | primary_root | candidate_feature_dir_for_mission | routed-through-resolver | `_resolve_status_surface_dir` fallback when meta absent/malformed; routes through coord-aware resolver. |
| mission_runtime/resolution.py:817 | repo_root | candidate_feature_dir_for_mission | routed-through-resolver | `resolve_placement_only` entry-point handle canonicalization (F-001); coord-aware resolver. |
| specify_cli/cli/commands/decision.py:464 | mission_slug | raw-path-join | raw-bypass | `cmd_verify`: `repo_root / KITTY_SPECS_DIR / mission_slug` to read primary-checkout `meta.json` for `mission_id` derivation BEFORE calling `resolve_mission_read_path` at :476. Unguarded raw join outside the blessed path-constructor module. FR-001 target (WP07 follow-up). |
| specify_cli/coordination/status_transition.py:223 | repo_root | candidate_feature_dir_for_mission | routed-through-resolver | `_canonical_primary_feature_dir` `_fallback()`: routes through coord-aware resolver when lane `.worktrees` path detected. |
| specify_cli/coordination/status_transition.py:232 | repo_root | resolve_status_surface_with_anchor | routed-through-resolver | `_canonical_primary_feature_dir` → `resolve_status_surface_with_anchor` (single-pass #1737 fix). |
| specify_cli/coordination/status_transition.py:240 | repo_root | candidate_feature_dir_for_mission | routed-through-resolver | `_canonical_primary_feature_dir` malformed-meta fallback; still routes through coord-aware resolver. |
| specify_cli/coordination/surface_resolver.py:429 | mission_slug | raw-path-join | raw-bypass | `_coord_mid8` fail-closed raise payload: `CoordinationWorkspace.worktree_path(...) / KITTY_SPECS_DIR / mission_slug` inside a `StatusReadPathNotFound` constructor. Diagnostic path in a `raise` — no FS open/write. Structural composition inside the resolver module. Tag as bypass to audit the composition; operationally safe (diagnostic only). |
| specify_cli/coordination/surface_resolver.py:434 | mission_slug | raw-path-join | raw-bypass | Same `_coord_mid8` fail-closed raise: `repo_root / KITTY_SPECS_DIR / mission_slug` for `primary_candidate`. Diagnostic path in `raise` — no FS sink. Same rationale as :429. |
| specify_cli/coordination/surface_resolver.py:450 | repo_root | resolve_status_surface_with_anchor | routed-through-resolver | `resolve_status_surface` → `resolve_status_surface_with_anchor` (thin wrapper, single canonical surface path accessor). |
| specify_cli/coordination/surface_resolver.py:484 | repo_root | candidate_feature_dir_for_mission | routed-through-resolver | `resolve_status_surface_with_anchor` → `candidate_feature_dir_for_mission` (the single-pass resolution, FR-036). |
| specify_cli/coordination/surface_resolver.py:517 | repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `resolve_status_surface_with_anchor` re-anchors config read on canonical primary dir to avoid #1589/#1821 split-brain (FR-003 cascade layer 1). Documented: coord worktree has no `meta.json`. |
| specify_cli/core/mission_creation.py:328 | mission_slug_formatted | raw-path-join | routed-through-resolver | `create_mission`: `mission_slug_formatted = mission_dir_name(mission_slug, mid8=…)` — output of the canonical `mission_dir_name` grammar seam (FR-032/FR-044). Not raw operator input; seam output feeds the join. |
| specify_cli/missions/_read_path_resolver.py:405 | mission_slug | resolve_mission_read_path | routed-through-resolver | `candidate_feature_dir_for_mission` → `resolve_mission_read_path` (C-005: one resolver). This IS the canonical coord-aware entry point. |
| specify_cli/missions/_read_path_resolver.py:438 | mission_slug | raw-path-join | topology-blind-by-design | `primary_feature_dir_for_mission`: `get_main_repo_root(repo_root) / KITTY_SPECS_DIR / mission_slug`. This IS the topology-blind primitive definition; lives inside the blessed path-constructor module; `assert_safe_path_segment` called at :437 (NFR-002). Deliberately bypasses coord worktree by design. |
| specify_cli/missions/feature_dir_resolver.py:46 | mission_slug | resolve_mission_read_path | routed-through-resolver | `resolve_feature_dir_for_slug` → `resolve_mission_read_path` via `mid8_from_slug`. Shim module re-exporting the canonical resolver (C-004). |
| specify_cli/review/cycle.py:185 | mission_slug | raw-path-join | routed-through-resolver | `resolve_review_cycle_pointer` → `validate_review_cycle_pointer` → `_validate_segment` → `assert_safe_path_segment` validates `parts.mission_slug` at lines 140-141 BEFORE the join at :185. Seam present; classified routed-through-resolver (the seam = `_validate_segment` guard). |
| specify_cli/status/aggregate.py:314 | repo_root | resolve_status_surface | routed-through-resolver | `MissionStatus._resolve_read_dir` → `resolve_status_surface` (the single coord-aware surface authority, FR-005/#1821). |
| specify_cli/status/aggregate.py:430 | mission_slug | raw-path-join | raw-bypass | `_find_meta_path` initial path: `repo_root / KITTY_SPECS_DIR / mission_slug` for primary-checkout meta lookup. No resolver on first attempt; handle-aware fallback at :449. S8 #1589 residual — the raw join is the first attempt, coord-aware handle resolution is the fallback. FR-001 target (WP06). |
| specify_cli/status/aggregate.py:449 | repo_root | candidate_feature_dir_for_mission | routed-through-resolver | `_find_meta_path` fallback: routes handle (mid8/ULID/numeric prefix) through coord-aware resolver for non-literal slugs (F-001). |
| specify_cli/status/aggregate.py:668 | mission_slug | raw-path-join | raw-bypass | `MissionMetadataUnavailable` raise payload: `self.repo_root / KITTY_SPECS_DIR / self.mission_slug / "meta.json"`. Composed only for a diagnostic path in a `raise`; slug pre-validated at `_validate_mission_slug` (line 228). No FS open/write. Tagged raw-bypass to audit the composition; operationally safe. |
| specify_cli/status/aggregate.py:669 | mission_slug | raw-path-join | raw-bypass | Same `MissionMetadataUnavailable` raise payload: `primary_candidate=self.repo_root / KITTY_SPECS_DIR / self.mission_slug`. Diagnostic only; slug pre-validated. |

## Disposition summary

| disposition | count | meaning |
| --- | --- | --- |
| routed-through-resolver | 15 | goes through a canonical blessed resolver (cite it); includes review/cycle.py:185 (validated segments) and mission_creation.py:328 (seam grammar output) |
| topology-blind-by-design | 5 | deliberately primary-only; coord surface carries no meta.json; rationale named in each row |
| raw-bypass | 6 | composes KITTY_SPECS_DIR/slug path inline without a resolver — FR-001 targets |
| **total** | **26** | 26 AST-discovered rows (seam-internal + raw-bypass scope) |

**Raw-bypass targets for WP06/WP07:**
- `specify_cli/status/aggregate.py:430` — `_find_meta_path` initial primary lookup (S8 residual, WP06)
- `specify_cli/status/aggregate.py:668,669` — `MissionMetadataUnavailable` diagnostic payloads (operationally safe, tagged for completeness)
- `specify_cli/coordination/surface_resolver.py:429,434` — `_coord_mid8` fail-closed raise payloads (diagnostic, no FS sink)
- `specify_cli/cli/commands/decision.py:464` — pre-resolver primary meta read (WP07 follow-up)

**Note on false negatives:** The audit tracks resolver calls only within the
six canonical seam files, not across all 168 discovered callers. The "Routed
caller summary" covers all other callers in aggregate. This is intentional:
the bypass scanner runs codebase-wide (ensuring no hidden raw-bypass exists
outside the tracked files), while the per-callsite detail is reserved for the
seam internals where correctness is most critical.

## Routed caller summary

The following files contain only `routed-through-resolver` callsites. All
delegate to a blessed resolver without inline path composition.

| file | resolver(s) used | callsite count |
| --- | --- | --- |
| specify_cli/acceptance/__init__.py | resolve_feature_dir_for_mission, resolve_mission_read_path, primary_feature_dir_for_mission | 4 |
| specify_cli/agent_utils/status.py | resolve_feature_dir_for_mission | 1 |
| specify_cli/cli/commands/agent/context.py | resolve_mission_read_path | 1 |
| specify_cli/cli/commands/agent/mission.py | resolve_mission_read_path, primary_feature_dir_for_mission | 4 |
| specify_cli/cli/commands/agent/status.py | candidate_feature_dir_for_mission | 1 |
| specify_cli/cli/commands/agent/tasks.py | candidate/resolve_feature_dir_for_mission, primary_feature_dir_for_mission, resolve_feature_dir_for_slug, resolve_mission_read_path | 17 |
| specify_cli/cli/commands/agent/workflow.py | candidate/resolve_feature_dir_for_mission, primary_feature_dir_for_mission, resolve_mission_read_path | 16 |
| specify_cli/cli/commands/agent_retrospect.py | resolve_status_surface | 1 |
| specify_cli/cli/commands/charter/_widen.py | candidate_feature_dir_for_mission | 1 |
| specify_cli/cli/commands/decision.py (non-bypass lines) | resolve_feature_dir_for_mission, resolve_mission_read_path | 2 |
| specify_cli/cli/commands/doctor.py | resolve_feature_dir_for_mission | 1 |
| specify_cli/cli/commands/implement.py | primary_feature_dir_for_mission, resolve_feature_dir_for_mission, candidate_feature_dir_for_mission | 6 |
| specify_cli/cli/commands/materialize.py | resolve_feature_dir_for_slug | 1 |
| specify_cli/cli/commands/merge.py | candidate/primary/resolve_feature_dir_for_mission, resolve_status_surface | 11 |
| specify_cli/cli/commands/mission_type.py | resolve/candidate/primary_feature_dir_for_mission | 4 |
| specify_cli/cli/commands/next_cmd.py | resolve_feature_dir_for_mission, candidate_feature_dir_for_mission | 5 |
| specify_cli/cli/commands/research.py | resolve_feature_dir_for_slug | 1 |
| specify_cli/cli/commands/retrospect.py | resolve_status_surface, candidate_feature_dir_for_mission | 3 |
| specify_cli/cli/commands/validate_encoding.py | resolve_feature_dir_for_slug | 1 |
| specify_cli/cli/commands/validate_tasks.py | resolve_feature_dir_for_slug | 1 |
| specify_cli/cli/commands/verify.py | candidate_feature_dir_for_mission | 1 |
| specify_cli/core/git_ops.py | candidate_feature_dir_for_mission | 1 |
| specify_cli/core/paths.py | candidate_feature_dir_for_mission | 1 |
| specify_cli/core/worktree_topology.py | candidate_feature_dir_for_mission | 1 |
| specify_cli/decisions/emit.py | resolve_feature_dir_for_mission | 1 |
| specify_cli/decisions/service.py | resolve_feature_dir_for_mission | 2 |
| specify_cli/doctrine_synthesizer/apply.py | resolve_feature_dir_for_mission | 3 |
| specify_cli/dossier/api.py | candidate_feature_dir_for_mission | 3 |
| specify_cli/lanes/merge.py | resolve_feature_dir_for_mission | 2 |
| specify_cli/lanes/recovery.py | candidate/resolve_feature_dir_for_mission | 3 |
| specify_cli/lanes/worktree_allocator.py | candidate_feature_dir_for_mission | 1 |
| specify_cli/manifest.py | resolve/candidate_feature_dir_for_mission | 2 |
| specify_cli/mission_loader/command.py | candidate_feature_dir_for_mission | 1 |
| specify_cli/missions/plan/plan_interview.py | resolve_feature_dir_for_mission | 1 |
| specify_cli/missions/plan/specify_interview.py | resolve_feature_dir_for_mission | 1 |
| specify_cli/orchestrator_api/commands.py | primary_feature_dir_for_mission, resolve_mission_read_path | 3 |
| specify_cli/post_merge/retrospective_terminus.py | resolve_feature_dir_for_slug | 1 |
| specify_cli/retrospective/gate.py | resolve_status_surface | 1 |
| specify_cli/retrospective/lifecycle_events.py | resolve_feature_dir_for_mission | 3 |
| specify_cli/retrospective/summary.py | candidate_feature_dir_for_mission | 1 |
| specify_cli/retrospective/writer.py | resolve_feature_dir_for_slug | 1 |
| specify_cli/scripts/tasks/task_helpers.py | resolve_feature_dir_for_mission | 1 |
| specify_cli/scripts/tasks/tasks_cli.py | resolve_feature_dir_for_mission | 3 |
| specify_cli/sync/events.py | candidate_feature_dir_for_mission | 1 |
| specify_cli/task_utils/support.py | resolve_feature_dir_for_slug | 1 |
| specify_cli/verify_enhanced.py | resolve_feature_dir_for_mission | 2 |
| specify_cli/widen/state.py | resolve_feature_dir_for_mission | 1 |
| specify_cli/workspace/context.py | resolve_feature_dir_for_slug | 6 |

## Audited-surface list anchor

The stable surface list WP08's guard anchors on is maintained as a separate
machine-readable artifact: `audited-surfaces.md`.
