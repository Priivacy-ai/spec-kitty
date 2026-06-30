# Mission-surface-resolution callsite inventory (WP01 / FR-003)

Generated input: `python tests/architectural/surface_resolution_audit/audit.py`
walks `src/specify_cli` and `src/mission_runtime`. The audit tracks:

1. **All resolver/topology-blind calls inside the canonical seam source files**
   (`RESOLVER_SOURCE_STEMS` in `audit.py`).
2. **All raw-bypass path joins** (`KITTY_SPECS_DIR / slug`) anywhere in the
   source trees.
3. **All direct read-SELECTION callsites** (`resolve_mission_read_path`) via
   `discover_selection_callsites()` (FR-006a) — distinct from the raw-join
   scanner because a direct selection call composes no `KITTY_SPECS_DIR` join of
   its own.

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

> **Point-in-time snapshot — line numbers are NOT live-pinned.** This table is a
> reviewer reference captured against one tree state. The convergence mission
> (`01KVN754`) shifted every seam file's line numbers, so the `file:line`
> locators below drift on each edit and are NOT reconciled by any CI gate. The
> live authority is `discover_rows()`, re-run on the current tree by
> `tests/architectural/test_single_mission_surface_resolver.py` (the wired guard).
> Rows are kept for their **dispositions + rationale**, not their exact lines.

| file:line | handle source | sink | disposition | rationale |
| --- | --- | --- | --- | --- |
| mission_runtime/resolution.py:185 | slug | resolve_mission_read_path | routed-through-resolver | `_resolve_mission_slug` -> `resolve_mission_read_path`; slug validated by `assert_safe_path_segment` inside the resolver (NFR-002). Single canonical runtime entry point (FR-030). |
| mission_runtime/resolution.py:233 | repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `_mid8_from_primary_meta` reads primary-checkout `meta.json` to derive mid8. The coord surface carries no `meta.json`. Topology-blind by design (C-GUARD-3a). |
| mission_runtime/resolution.py:547 | primary_root | primary_feature_dir_for_mission | topology-blind-by-design | `_resolve_coordination_branch` anchors `meta.json` read on primary only — reading through the coord-aware resolver would flip topology (C-GUARD-3a split-brain rationale). |
| mission_runtime/resolution.py:579 | primary_root | primary_feature_dir_for_mission | topology-blind-by-design | `_resolve_mission_id` reads `meta.json` from primary; same C-GUARD-3a rationale as :547. |
| mission_runtime/resolution.py:609 | primary_root | resolve_status_surface | routed-through-resolver | `_resolve_status_surface_dir` -> `resolve_status_surface` (the single status-surface authority IC-01). |
| mission_runtime/resolution.py:618 | primary_root | candidate_feature_dir_for_mission | routed-through-resolver | `_resolve_status_surface_dir` fallback when meta absent/malformed; routes through coord-aware resolver. |
| mission_runtime/resolution.py:824 | repo_root | candidate_feature_dir_for_mission | routed-through-resolver | `resolve_placement_only` entry-point handle canonicalization (F-001); coord-aware resolver. |
| specify_cli/coordination/status_transition.py:264 | repo_root | candidate_feature_dir_for_mission | routed-through-resolver | `_canonical_primary_feature_dir` `_fallback()`: routes through coord-aware resolver when lane `.worktrees` path detected. |
| specify_cli/coordination/status_transition.py:273 | repo_root | resolve_status_surface_with_anchor | routed-through-resolver | `_canonical_primary_feature_dir` -> `resolve_status_surface_with_anchor` (single-pass #1737 fix). |
| specify_cli/coordination/status_transition.py:281 | repo_root | candidate_feature_dir_for_mission | routed-through-resolver | `_canonical_primary_feature_dir` malformed-meta fallback; still routes through coord-aware resolver. |
| specify_cli/coordination/surface_resolver.py:518 | mission_slug | raw-path-join | raw-bypass | `_coord_mid8` fail-closed raise payload: `CoordinationWorkspace.worktree_path(...) / KITTY_SPECS_DIR / mission_slug` inside a `StatusReadPathNotFound` constructor. Diagnostic path in a `raise` — no FS open/write. Structural composition inside the resolver module. Tag as bypass to audit the composition; operationally safe (diagnostic only). |
| specify_cli/coordination/surface_resolver.py:523 | mission_slug | raw-path-join | raw-bypass | Same `_coord_mid8` fail-closed raise: `repo_root / KITTY_SPECS_DIR / mission_slug` for `primary_candidate`. Diagnostic path in `raise` — no FS sink. Same rationale as :518. |
| specify_cli/coordination/surface_resolver.py:600 | repo_root | resolve_status_surface_with_anchor | routed-through-resolver | `resolve_status_surface` -> `resolve_status_surface_with_anchor` (thin wrapper, single canonical surface path accessor). |
| specify_cli/coordination/surface_resolver.py:670 | repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `resolve_status_surface_with_anchor` re-anchors config read on canonical primary dir to avoid #1589/#1821 split-brain (FR-003 cascade layer 1). Documented: coord worktree has no `meta.json`. |
| specify_cli/core/mission_creation.py:328 | mission_slug_formatted | raw-path-join | routed-through-resolver | `create_mission`: `mission_slug_formatted = mission_dir_name(mission_slug, mid8=…)` — output of the canonical `mission_dir_name` grammar seam (FR-032/FR-044). Not raw operator input; seam output feeds the join. |
| specify_cli/missions/_read_path_resolver.py:410 | repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `read_primary_meta` (the shared read-side seam primitive, FR-001) composes the primary candidate through the blessed topology-blind constructor to read `meta.json` BEFORE the topology-aware read path resolves; coord worktree carries no `meta.json`. |
| specify_cli/missions/_read_path_resolver.py:497 | repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `resolve_handle_to_read_path` M5 fail-closed branch: composes the primary candidate for the typed `StatusReadPathNotFound` diagnostic when a coord-declared topology has an unprovable identity. |
| specify_cli/missions/_read_path_resolver.py:509 | handle | resolve_mission_read_path | routed-through-resolver | `resolve_handle_to_read_path` (THE single guarded read-side seam, IC-01) -> `resolve_mission_read_path` (the existence-gated topology resolver). This IS the canonical adopted read-side entry point; the guard (`assert_safe_path_segment`) + M5 fail-closed gate run before this call. |
| specify_cli/missions/_read_path_resolver.py:580 | repo_root | resolve_status_surface | routed-through-resolver | `resolve_feature_dir_for_mission`-class helper -> `resolve_status_surface` (the single coord-aware surface authority). |
| specify_cli/missions/_read_path_resolver.py:608 | mission_slug | resolve_mission_read_path | routed-through-resolver | `resolve_surface_dir_or_typed_error` -> `resolve_mission_read_path` via `mid8_from_slug` (C-005: one resolver). |
| specify_cli/missions/_read_path_resolver.py:641 | mission_slug | raw-path-join | topology-blind-by-design | `primary_feature_dir_for_mission`: `get_main_repo_root(repo_root) / KITTY_SPECS_DIR / mission_slug`. This IS the topology-blind primitive definition; lives inside the blessed path-constructor module; `assert_safe_path_segment` called at :640 (NFR-002). Deliberately bypasses coord worktree by design. (Relocated from :511 by the WP01 seam additions — re-keyed by WP05.) |
| specify_cli/missions/_read_path_resolver.py:661 | mission_slug | resolve_mission_read_path | routed-through-resolver | `resolve_feature_dir_for_slug` -> `resolve_mission_read_path` via `mid8_from_slug` (relocated here from the retired `feature_dir_resolver` shim, WP07/FR-007). |
| specify_cli/review/cycle.py:185 | mission_slug | raw-path-join | routed-through-resolver | `resolve_review_cycle_pointer` -> `validate_review_cycle_pointer` -> `_validate_segment` -> `assert_safe_path_segment` validates `parts.mission_slug` at lines 140-141 BEFORE the join at :185. Seam present; classified routed-through-resolver (the seam = `_validate_segment` guard). |
| specify_cli/status/aggregate.py:491 | repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `_find_meta_path` primary lookup: composes the primary candidate through the blessed topology-blind constructor (WP06 fix — replaced the old raw `repo_root / KITTY_SPECS_DIR / mission_slug` self-composition); reads `meta.json` on the primary checkout. |
| specify_cli/status/aggregate.py:502 | repo_root | candidate_feature_dir_for_mission | routed-through-resolver | `_find_meta_path` fallback: routes handle (mid8/ULID/numeric prefix) through coord-aware resolver for non-literal slugs (F-001). |
| specify_cli/status/aggregate.py:516 | repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `_find_meta_path` re-anchor: re-anchors the meta read on the primary checkout under the canonical candidate name via the blessed topology-blind constructor (WP06 fix). |
| specify_cli/status/aggregate.py:716 | self.repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `MissionMetadataUnavailable` diagnostic composes the primary candidate through the blessed topology-blind constructor (WP06 fix — replaced the old raw `self.repo_root / KITTY_SPECS_DIR / self.mission_slug` diagnostic self-composition). |

## Disposition summary

| disposition | count | meaning |
| --- | --- | --- |
| routed-through-resolver | 15 | goes through a canonical blessed resolver (cite it); includes review/cycle.py:185 (validated segments) and mission_creation.py:328 (seam grammar output) |
| topology-blind-by-design | 10 | deliberately primary-only; coord surface carries no meta.json; rationale named in each row. (WP06 routed the aggregate.py primary lookups/diagnostics through `primary_feature_dir_for_mission`; the WP01 read-side seam added two topology-blind primary reads in `read_primary_meta` + the M5 fail-closed branch of `resolve_handle_to_read_path`.) |
| raw-bypass | 2 | composes KITTY_SPECS_DIR/slug path inline without a resolver — the two `_coord_mid8` fail-closed diagnostic payloads (no FS sink, operationally safe) |
| **total** | **27** | seam-internal + raw-bypass rows (point-in-time; the `01KVN754` convergence deleted the two coord-empty-apparatus rows — `_is_coord_empty_condition` + `_canonicalize_or_enrich_coord_empty` — and the live `discover_rows()` guard is the authority) |

**Raw-bypass rows (disposition + status):**
- `specify_cli/coordination/surface_resolver.py:518,523` — `_coord_mid8` fail-closed raise payloads (diagnostic, no FS sink; operationally safe).
- `specify_cli/missions/_read_path_resolver.py:641` — the `primary_feature_dir_for_mission` topology-blind primitive DEFINITION (allowlisted TBYD; `assert_safe_path_segment` at :640).
- `specify_cli/core/mission_creation.py:328` — seam-grammar output (`mission_slug_formatted`); routed-through-resolver (not a raw operator slug).
- `specify_cli/review/cycle.py:185` — `_validate_segment`-pre-validated; routed-through-resolver.

**DRAINED read-CLI raw-joins (FR-007, confirmed by WP05 re-derivation):**
The four read-CLI primary-meta bootstrap raw-joins that the previous inventory
tracked as `raw-bypass` are GONE from `discover_rows()` — migrated onto the
single guarded read-side seam `resolve_handle_to_read_path` by WP02:
- `specify_cli/cli/commands/agent/context.py:72` (#2046) — migrated.
- `specify_cli/cli/commands/agent/mission.py:1327` (#2046) — migrated.
- `specify_cli/cli/commands/agent/mission.py:1378` (#2046, `.is_dir()` probe) — migrated.
- `specify_cli/cli/commands/decision.py:464` — **D-6 consolidation** drain (the
  decision-verify primary-meta bootstrap was folded onto the seam as a
  consequence of the WP02 factory-boundary consolidation; this is a D-6
  consolidation outcome, NOT a #2046 residual). The seam supplies the
  `assert_safe_path_segment` guard each bootstrap previously lacked.

**Disposition changes vs the previous inventory:**
- The four read-CLI `raw-bypass` rows (`context.py:72`, `mission.py:1327`,
  `mission.py:1378`, `decision.py:464`) are GONE — drained by WP02's migration
  onto the seam (FR-007). `discover_rows()` no longer surfaces them; their
  `_ALLOWLISTED_RAW_JOINS` entries were already removed by WP02.
- The topology-blind primitive `primary_feature_dir_for_mission` DEFINITION
  shifted from `_read_path_resolver.py:511` to `:641` (the WP01 seam additions
  pushed it down); the allowlist entry was re-keyed by WP05.
- Two NEW topology-blind primary reads surfaced inside the WP01 seam
  (`_read_path_resolver.py:410` in `read_primary_meta`, `:497` in the M5
  fail-closed branch of `resolve_handle_to_read_path`).
- Seam-internal line numbers across `mission_runtime/resolution.py` and
  `_read_path_resolver.py` shifted with the WP01/WP03 edits; the sink table was
  re-derived against the current tree.

**Note on false negatives:** The audit tracks resolver calls only within the
canonical seam files, not across all discovered callers. The "Routed caller
summary" covers all other callers in aggregate. This is intentional: the bypass
scanner + the read-SELECTION scanner run codebase-wide (ensuring no hidden
raw-bypass or direct selection call exists outside the tracked surfaces), while
the per-callsite detail is reserved for the seam internals where correctness is
most critical.

## Read-SELECTION callsites (FR-006a)

`discover_selection_callsites()` enumerates every direct
`resolve_mission_read_path(...)` call — the read-side SELECTION authority.
Seam-internal calls are auto-blessed; external calls must be allowlisted in
`audit.py::ALLOWLISTED_SELECTION_CALLSITES`.

| file:line | in seam file | disposition |
| --- | --- | --- |
| mission_runtime/resolution.py:185 | yes | seam-internal (canonical runtime entry, RESOLVER_SOURCE_STEMS) |
| specify_cli/missions/_read_path_resolver.py:509 | yes | seam-internal (`resolve_handle_to_read_path`, the guarded seam) |
| specify_cli/missions/_read_path_resolver.py:608 | yes | seam-internal (`resolve_surface_dir_or_typed_error`) |
| specify_cli/missions/_read_path_resolver.py:661 | yes | seam-internal (`resolve_feature_dir_for_slug`) |
| specify_cli/acceptance/__init__.py:619 | no | BLESSED-EXTERNAL — acceptance lenient-fallback (WP03/T013); mid8 via the sanctioned `resolve_declared_mid8` cascade; allowlisted. |

## Routed caller summary

The following files contain only `routed-through-resolver` callsites. All
delegate to a blessed resolver without inline path composition.

| file | resolver(s) used | callsite count |
| --- | --- | --- |
| specify_cli/acceptance/__init__.py | resolve_feature_dir_for_mission, resolve_mission_read_path, primary_feature_dir_for_mission | 4 |
| specify_cli/agent_utils/status.py | resolve_feature_dir_for_mission | 1 |
| specify_cli/cli/commands/agent/context.py | resolve_handle_to_read_path | 1 |
| specify_cli/cli/commands/agent/mission.py | resolve_handle_to_read_path, primary_feature_dir_for_mission | 4 |
| specify_cli/cli/commands/agent/status.py | candidate_feature_dir_for_mission | 1 |
| specify_cli/cli/commands/agent/tasks.py | candidate/resolve_feature_dir_for_mission, primary_feature_dir_for_mission, resolve_feature_dir_for_slug, resolve_handle_to_read_path | 17 |
| specify_cli/cli/commands/agent/workflow.py | candidate/resolve_feature_dir_for_mission, primary_feature_dir_for_mission, resolve_handle_to_read_path | 16 |
| specify_cli/cli/commands/agent_retrospect.py | resolve_status_surface | 1 |
| specify_cli/cli/commands/charter/_widen.py | candidate_feature_dir_for_mission | 1 |
| specify_cli/cli/commands/decision.py | resolve_feature_dir_for_mission, resolve_handle_to_read_path | 2 |
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
| specify_cli/sync/events.py | candidate_feature_dir_for_mission | 1 |
| specify_cli/task_utils/support.py | resolve_feature_dir_for_slug | 1 |
| specify_cli/verify_enhanced.py | resolve_feature_dir_for_mission | 2 |
| specify_cli/widen/state.py | resolve_feature_dir_for_mission | 1 |
| specify_cli/workspace/context.py | resolve_feature_dir_for_slug | 6 |

## Audited-surface list anchor

The stable surface list WP08's guard anchors on is maintained as a separate
machine-readable artifact: `audited-surfaces.md`.
