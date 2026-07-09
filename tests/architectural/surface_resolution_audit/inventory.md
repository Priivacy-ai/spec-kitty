# Mission-surface-resolution callsite inventory (WP01 / FR-003; IC-03 re-key FR-004)

Generated input: `python tests/architectural/surface_resolution_audit/audit.py`
walks `src/specify_cli` and `src/mission_runtime`. The audit tracks:

1. **All resolver/topology-blind calls inside the canonical seam source files**
   (`RESOLVER_SOURCE_STEMS` in `audit.py`).
2. **All raw-bypass path joins** (`KITTY_SPECS_DIR / slug`) anywhere in the
   source trees.
3. **All direct read-SELECTION callsites** (`resolve_mission_read_path`) via
   `discover_selection_callsites()` (FR-006a).

## Design-P: drift-proof identity + freshen procedure (IC-03)

> **Row identity is the `(rel_path, enclosing_qualname, token)` composite** derived
> by `composite_key_from_file` — NOT the `file:line` locator. The `line` in each
> locator is a NON-authoritative jump-to convenience and is **never compared**;
> a blank/comment-line insertion above a callsite shifts the line but keeps the
> composite identical, so the audit stays GREEN (the #2306 failure class is fixed).
> The `qualname` and `token` columns carry the frozen comparand; both are stored
> backtick-wrapped for readability and the audit parser strips the backticks.
>
> **Both tripwire directions are gated** (per audit, IC-02/03):
> - **Undercount** — every DISCOVERED callsite must match an inventory row by
>   composite identity, else RED.
> - **Overcount / ghost** — every inventory row (minus `[inventory-only]`-tagged
>   rows) must match a LIVE discovered callsite, else RED. A `[inventory-only]`
>   tag in the notes/rationale exempts a row that documents an intentionally
>   removed sink; each tagged row must cite the removing change. Zero rows are
>   tagged at conversion time.
>
> **Freshen procedure** (after a legitimate seam edit shifts these callsites):
> re-run the recorded converter
> `python tests/architectural/surface_resolution_audit/rekey_inventory.py`, which
> re-derives every `qualname`/`token` from live source (tokens are tool-derived,
> never hand-typed) and rewrites the two gated tables below.

**Scope note:** the many downstream callers that legitimately call
`resolve_feature_dir_for_mission` / `candidate_feature_dir_for_mission` /
`resolve_feature_dir_for_slug` outside the seam files are summarized in the
"Routed caller summary" section (aggregate, not gated row-by-row) — the matcher's
job is to make bypass under-counting and ghost over-documentation impossible, not
to enumerate every blessed call.

## Sink table

| file:line | qualname | token | handle source | sink | disposition | rationale |
| --- | --- | --- | --- | --- | --- | --- |
| mission_runtime/resolution.py:417 | `_mid8_from_primary_meta` | `primary_dir = primary_feature_dir_for_mission (` | repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `_mid8_from_primary_meta` composes/reads the PRIMARY checkout through the blessed topology-blind `primary_feature_dir_for_mission` constructor (the coord surface carries no `meta.json`; C-GUARD-3a split-brain rationale). |
| mission_runtime/resolution.py:746 | `_resolve_coordination_branch` | `primary_dir = primary_feature_dir_for_mission (` | primary_root | primary_feature_dir_for_mission | topology-blind-by-design | `_resolve_coordination_branch` composes/reads the PRIMARY checkout through the blessed topology-blind `primary_feature_dir_for_mission` constructor (the coord surface carries no `meta.json`; C-GUARD-3a split-brain rationale). |
| mission_runtime/resolution.py:792 | `_resolve_topology` | `primary_dir = primary_feature_dir_for_mission (` | primary_root | primary_feature_dir_for_mission | topology-blind-by-design | `_resolve_topology` composes/reads the PRIMARY checkout through the blessed topology-blind `primary_feature_dir_for_mission` constructor (the coord surface carries no `meta.json`; C-GUARD-3a split-brain rationale). |
| mission_runtime/resolution.py:840 | `resolve_topology` | `candidate_dir = candidate_feature_dir_for_mission (` | repo_root | candidate_feature_dir_for_mission | routed-through-resolver | `resolve_topology` delegates to `candidate_feature_dir_for_mission` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| mission_runtime/resolution.py:891 | `mission_context_for` | `candidate_dir = candidate_feature_dir_for_mission (` | primary_root | candidate_feature_dir_for_mission | routed-through-resolver | `mission_context_for` delegates to `candidate_feature_dir_for_mission` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| mission_runtime/resolution.py:986 | `_resolve_mission_id` | `primary_dir = primary_feature_dir_for_mission (` | primary_root | primary_feature_dir_for_mission | topology-blind-by-design | `_resolve_mission_id` composes/reads the PRIMARY checkout through the blessed topology-blind `primary_feature_dir_for_mission` constructor (the coord surface carries no `meta.json`; C-GUARD-3a split-brain rationale). |
| mission_runtime/resolution.py:1037 | `_resolve_status_surface_dir` | `surface = resolve_status_surface ( primary_root , mission_slug , topology )` | primary_root | resolve_status_surface | routed-through-resolver | `_resolve_status_surface_dir` delegates to `resolve_status_surface` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| mission_runtime/resolution.py:1046 | `_resolve_status_surface_dir` | `fallback_dir : Path = candidate_feature_dir_for_mission (` | primary_root | candidate_feature_dir_for_mission | routed-through-resolver | `_resolve_status_surface_dir` delegates to `candidate_feature_dir_for_mission` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| mission_runtime/resolution.py:1300 | `resolve_placement_only` | `candidate_dir = candidate_feature_dir_for_mission (` | repo_root | candidate_feature_dir_for_mission | routed-through-resolver | `resolve_placement_only` delegates to `candidate_feature_dir_for_mission` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| specify_cli/coordination/status_transition.py:268 | `_canonical_primary_feature_dir._fallback` | `anchor : Path = candidate_feature_dir_for_mission ( repo_root , mission_slug )` | repo_root | candidate_feature_dir_for_mission | routed-through-resolver | `_canonical_primary_feature_dir._fallback` delegates to `candidate_feature_dir_for_mission` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| specify_cli/coordination/status_transition.py:277 | `_canonical_primary_feature_dir` | `resolved = resolve_status_surface_with_anchor ( repo_root , mission_slug )` | repo_root | resolve_status_surface_with_anchor | routed-through-resolver | `_canonical_primary_feature_dir` delegates to `resolve_status_surface_with_anchor` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| specify_cli/coordination/status_transition.py:285 | `_canonical_primary_feature_dir` | `malformed_anchor : Path = candidate_feature_dir_for_mission ( repo_root , mission_slug )` | repo_root | candidate_feature_dir_for_mission | routed-through-resolver | `_canonical_primary_feature_dir` delegates to `candidate_feature_dir_for_mission` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| specify_cli/coordination/surface_resolver.py:499 | `_coord_mid8` | `coord_candidate = repo_root` | mission_slug | raw-path-join | raw-bypass | `_coord_mid8` composes KITTY_SPECS_DIR/slug inline ONLY for a fail-closed `StatusReadPathNotFound` diagnostic `raise` payload — the path is never opened (no FS sink; operationally safe). |
| specify_cli/coordination/surface_resolver.py:504 | `_coord_mid8` | `primary_candidate = repo_root / KITTY_SPECS_DIR / mission_slug ,` | mission_slug | raw-path-join | raw-bypass | `_coord_mid8` composes KITTY_SPECS_DIR/slug inline ONLY for a fail-closed `StatusReadPathNotFound` diagnostic `raise` payload — the path is never opened (no FS sink; operationally safe). |
| specify_cli/coordination/surface_resolver.py:598 | `resolve_status_surface` | `return resolve_status_surface_with_anchor (` | repo_root | resolve_status_surface_with_anchor | routed-through-resolver | `resolve_status_surface` delegates to `resolve_status_surface_with_anchor` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| specify_cli/coordination/surface_resolver.py:639 | `resolve_status_surface_with_anchor` | `feature_dir : Path = candidate_feature_dir_for_mission ( repo_root , mission_slug )` | repo_root | candidate_feature_dir_for_mission | routed-through-resolver | `resolve_status_surface_with_anchor` delegates to `candidate_feature_dir_for_mission` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| specify_cli/coordination/surface_resolver.py:703 | `resolve_status_surface_with_anchor` | `primary_dir : Path = primary_feature_dir_for_mission (` | repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `resolve_status_surface_with_anchor` composes/reads the PRIMARY checkout through the blessed topology-blind `primary_feature_dir_for_mission` constructor (the coord surface carries no `meta.json`; C-GUARD-3a split-brain rationale). |
| specify_cli/core/mission_creation.py:342 | `create_mission_core` | `feature_dir = resolved_root / KITTY_SPECS_DIR / mission_slug_formatted` | mission_slug_formatted | raw-path-join | routed-through-resolver | `create_mission_core` joins `mission_slug_formatted`, the OUTPUT of the canonical `mission_dir_name` grammar seam (FR-032/FR-044) — not a raw operator slug; create-time-canonical (the dir is being created here). |
| specify_cli/missions/_read_path_resolver.py:461 | `_canonicalize_bare_modern_handle` | `literal_primary = primary_feature_dir_for_mission ( repo_root , handle )` | repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `_canonicalize_bare_modern_handle` composes/reads the PRIMARY checkout through the blessed topology-blind `primary_feature_dir_for_mission` constructor (the coord surface carries no `meta.json`; C-GUARD-3a split-brain rationale). |
| specify_cli/missions/_read_path_resolver.py:842 | `read_primary_meta` | `primary_dir = primary_feature_dir_for_mission ( repo_root , handle )` | repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `read_primary_meta` composes/reads the PRIMARY checkout through the blessed topology-blind `primary_feature_dir_for_mission` constructor (the coord surface carries no `meta.json`; C-GUARD-3a split-brain rationale). |
| specify_cli/missions/_read_path_resolver.py:979 | `resolve_handle_to_read_path` | `primary_meta , primary_feature_dir_for_mission ( repo_root , handle )` | repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `resolve_handle_to_read_path` composes/reads the PRIMARY checkout through the blessed topology-blind `primary_feature_dir_for_mission` constructor (the coord surface carries no `meta.json`; C-GUARD-3a split-brain rationale). |
| specify_cli/missions/_read_path_resolver.py:1001 | `resolve_handle_to_read_path` | `primary_candidate = primary_feature_dir_for_mission ( repo_root , handle )` | repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `resolve_handle_to_read_path` composes/reads the PRIMARY checkout through the blessed topology-blind `primary_feature_dir_for_mission` constructor (the coord surface carries no `meta.json`; C-GUARD-3a split-brain rationale). |
| specify_cli/missions/_read_path_resolver.py:1052 | `resolve_handle_to_read_path` | `primary_candidate = primary_feature_dir_for_mission ( repo_root , handle ) ,` | repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `resolve_handle_to_read_path` composes/reads the PRIMARY checkout through the blessed topology-blind `primary_feature_dir_for_mission` constructor (the coord surface carries no `meta.json`; C-GUARD-3a split-brain rationale). |
| specify_cli/missions/_read_path_resolver.py:1139 | `resolve_surface_dir_or_typed_error` | `surface : Path = resolve_status_surface ( repo_root , mission_slug )` | repo_root | resolve_status_surface | routed-through-resolver | `resolve_surface_dir_or_typed_error` delegates to `resolve_status_surface` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| specify_cli/missions/_read_path_resolver.py:1250 | `_stored_topology_best_effort` | `primary_dir = primary_feature_dir_for_mission ( repo_root , canonical_handle )` | repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `_stored_topology_best_effort` composes/reads the PRIMARY checkout through the blessed topology-blind `primary_feature_dir_for_mission` constructor (the coord surface carries no `meta.json`; C-GUARD-3a split-brain rationale). |
| specify_cli/missions/_read_path_resolver.py:1282 | `primary_feature_dir_for_mission` | `primary_dir : Path = get_main_repo_root ( repo_root ) / KITTY_SPECS_DIR / mission_slug` | mission_slug | raw-path-join | topology-blind-by-design | `primary_feature_dir_for_mission` IS the topology-blind primitive definition (`primary_feature_dir_for_mission`); `assert_safe_path_segment` guards the slug just above the join (NFR-002); deliberately primary-only. |
| specify_cli/missions/_read_path_resolver.py:1427 | `resolve_planning_read_dir` | `return primary_feature_dir_for_mission ( repo_root , canonical )` | repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `resolve_planning_read_dir` composes/reads the PRIMARY checkout through the blessed topology-blind `primary_feature_dir_for_mission` constructor (the coord surface carries no `meta.json`; C-GUARD-3a split-brain rationale). |
| specify_cli/missions/_read_path_resolver.py:1429 | `resolve_planning_read_dir` | `return candidate_feature_dir_for_mission ( repo_root , mission_slug , resolver = resolver )` | repo_root | candidate_feature_dir_for_mission | routed-through-resolver | `resolve_planning_read_dir` delegates to `candidate_feature_dir_for_mission` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| specify_cli/status/aggregate.py:505 | `MissionStatus._find_meta_path` | `primary_dir = primary_feature_dir_for_mission (` | repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `MissionStatus._find_meta_path` composes/reads the PRIMARY checkout through the blessed topology-blind `primary_feature_dir_for_mission` constructor (the coord surface carries no `meta.json`; C-GUARD-3a split-brain rationale). |
| specify_cli/status/aggregate.py:528 | `MissionStatus._find_meta_path` | `composed_primary = primary_feature_dir_for_mission ( repo_root , bare_dir_name )` | repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `MissionStatus._find_meta_path` composes/reads the PRIMARY checkout through the blessed topology-blind `primary_feature_dir_for_mission` constructor (the coord surface carries no `meta.json`; C-GUARD-3a split-brain rationale). |
| specify_cli/status/aggregate.py:533 | `MissionStatus._find_meta_path` | `candidate_dir = candidate_feature_dir_for_mission ( repo_root , mission_slug )` | repo_root | candidate_feature_dir_for_mission | routed-through-resolver | `MissionStatus._find_meta_path` delegates to `candidate_feature_dir_for_mission` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| specify_cli/status/aggregate.py:549 | `MissionStatus._find_meta_path` | `canonical_primary = primary_feature_dir_for_mission (` | repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `MissionStatus._find_meta_path` composes/reads the PRIMARY checkout through the blessed topology-blind `primary_feature_dir_for_mission` constructor (the coord surface carries no `meta.json`; C-GUARD-3a split-brain rationale). |
| specify_cli/status/aggregate.py:751 | `MissionStatus.save` | `diag_primary = primary_feature_dir_for_mission (` | self.repo_root | primary_feature_dir_for_mission | topology-blind-by-design | `MissionStatus.save` composes/reads the PRIMARY checkout through the blessed topology-blind `primary_feature_dir_for_mission` constructor (the coord surface carries no `meta.json`; C-GUARD-3a split-brain rationale). |

## Disposition summary

| disposition | count | meaning |
| --- | --- | --- |
| routed-through-resolver | 14 | goes through a canonical blessed resolver (cite it) |
| topology-blind-by-design | 17 | deliberately primary-only; coord surface carries no meta.json (C-GUARD-3a) |
| raw-bypass | 2 | composes KITTY_SPECS_DIR/slug inline for a fail-closed diagnostic `raise` payload (no FS sink) |
| **total** | **33** | all AST-discovered ResolutionRow callsites |

## Read-SELECTION callsites (FR-006a)

`discover_selection_callsites()` enumerates every direct
`resolve_mission_read_path(...)` call — the read-side SELECTION authority.
Seam-internal calls are auto-blessed; external calls must be allowlisted in
`audit.py::ALLOWLISTED_SELECTION_CALLSITES`. The table is cross-checked by the
SAME composite undercount/overcount seams as the sink table. On the collapsed
tree all 3 direct selection callsites are seam-internal (zero external).

| file:line | qualname | token | in seam file | disposition | notes |
| --- | --- | --- | --- | --- | --- |
| specify_cli/missions/_read_path_resolver.py:1062 | `resolve_handle_to_read_path` | `return _resolve_mission_read_path (` | yes | seam-internal (auto-blessed) | direct `_resolve_mission_read_path` inside `resolve_handle_to_read_path` — the seam definition. |
| specify_cli/missions/_read_path_resolver.py:1205 | `candidate_feature_dir_for_mission` | `return _resolve_mission_read_path (` | yes | seam-internal (auto-blessed) | direct `_resolve_mission_read_path` inside `candidate_feature_dir_for_mission` — the seam definition. |
| specify_cli/missions/_read_path_resolver.py:1520 | `resolve_feature_dir_for_slug` | `feature_dir : Path = _resolve_mission_read_path (` | yes | seam-internal (auto-blessed) | direct `_resolve_mission_read_path` inside `resolve_feature_dir_for_slug` — the seam definition. |

## Routed caller summary

The many downstream callers that reach a blessed resolver
(`resolve_feature_dir_for_mission` / `candidate_feature_dir_for_mission` /
`resolve_feature_dir_for_slug` / `resolve_handle_to_read_path` /
`resolve_status_surface`) OUTSIDE the seam files are classified
`routed-through-resolver` by definition — they delegate without inline path
composition. They are covered in aggregate here (a point-in-time reviewer
reference), NOT gated per-row: the audit's job is to make bypass under-counting
and ghost over-documentation impossible, not to enumerate every blessed call.
The heaviest routed callers are the CLI command modules
(`cli/commands/agent/tasks.py`, `cli/commands/agent/workflow.py`,
`cli/commands/merge.py`, `cli/commands/implement.py`) plus `workspace/context.py`
and `acceptance/__init__.py`.

## Audited-surface list anchor

The stable surface list WP08's guard anchors on is maintained as a separate
machine-readable artifact: `audited-surfaces.md`.
