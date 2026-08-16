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

read-side-seam-primary-primitive-closure-01KYKMMT WP08 (T038) hand-edit: the
public wrapper `primary_feature_dir_for_mission` is DELETED (T035, SC-001).
Every row below that used to name it as `sink` called an internal, seam-owned
composition that has moved to the module-private `_compose_primary_feature_dir`
leaf — a name this OLDER audit's scanner does not track as a sink (it predates
WP03's T015 leaf extraction and was never taught the new name; the newer,
whole-tree `test_no_read_side_bypass.py` census is the terminal authority for
that migration — see `docs/development/read-side-seam-classification.md`).
Sixteen rows were removed outright (the seam's own internal composition calls
in `mission_runtime/resolution.py`, `specify_cli/missions/_read_path_resolver.py`,
and `specify_cli/status/aggregate.py` — all resolver-internal self-reference,
never a bypass, already covered by the OTHER census's sanctioned-module
entries). One row — `coordination/surface_resolver.py`'s foundation site
(FR-005/NFR-009, one of WP08's four named foundation sites) — is KEPT and
tagged `[inventory-only]` rather than removed, since it is still a real,
permanently-unrouted foundation site worth documenting even though this
scanner no longer tracks its (leaf) callee name. One row is ADDED: the leaf's
own definition body, discovered under its new qualname
`_compose_primary_feature_dir` (the direct successor of the removed
`primary_feature_dir_for_mission`-definition row).

| file:line | qualname | token | handle source | sink | disposition | rationale |
| --- | --- | --- | --- | --- | --- | --- |
| mission_runtime/resolution.py:859 | `resolve_topology` | `candidate_dir = candidate_feature_dir_for_mission (` | repo_root | candidate_feature_dir_for_mission | routed-through-resolver | `resolve_topology` delegates to `candidate_feature_dir_for_mission` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| mission_runtime/resolution.py:910 | `mission_context_for` | `candidate_dir = candidate_feature_dir_for_mission (` | primary_root | candidate_feature_dir_for_mission | routed-through-resolver | `mission_context_for` delegates to `candidate_feature_dir_for_mission` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| mission_runtime/resolution.py:1059 | `_resolve_status_surface_dir` | `surface = resolve_status_surface ( primary_root , mission_slug , topology )` | primary_root | resolve_status_surface | routed-through-resolver | `_resolve_status_surface_dir` delegates to `resolve_status_surface` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| mission_runtime/resolution.py:1068 | `_resolve_status_surface_dir` | `fallback_dir : Path = candidate_feature_dir_for_mission (` | primary_root | candidate_feature_dir_for_mission | routed-through-resolver | `_resolve_status_surface_dir` delegates to `candidate_feature_dir_for_mission` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| mission_runtime/resolution.py:1322 | `resolve_placement_only` | `candidate_dir = candidate_feature_dir_for_mission (` | repo_root | candidate_feature_dir_for_mission | routed-through-resolver | `resolve_placement_only` delegates to `candidate_feature_dir_for_mission` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| specify_cli/coordination/status_transition.py:618 | `_canonical_primary_feature_dir` | `resolved = resolve_status_surface_with_anchor ( repo_root , mission_slug )` | repo_root | resolve_status_surface_with_anchor | routed-through-resolver | `_canonical_primary_feature_dir` delegates to `resolve_status_surface_with_anchor` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| specify_cli/coordination/surface_resolver.py:528 | `_coord_mid8` | `coord_candidate = repo_root` | mission_slug | raw-path-join | raw-bypass | `_coord_mid8` composes KITTY_SPECS_DIR/slug inline ONLY for a fail-closed `StatusReadPathNotFound` diagnostic `raise` payload — the path is never opened (no FS sink; operationally safe). |
| specify_cli/coordination/surface_resolver.py:533 | `_coord_mid8` | `primary_candidate = repo_root / KITTY_SPECS_DIR / mission_slug ,` | mission_slug | raw-path-join | raw-bypass | `_coord_mid8` composes KITTY_SPECS_DIR/slug inline ONLY for a fail-closed `StatusReadPathNotFound` diagnostic `raise` payload — the path is never opened (no FS sink; operationally safe). |
| specify_cli/coordination/surface_resolver.py:627 | `resolve_status_surface` | `return resolve_status_surface_with_anchor (` | repo_root | resolve_status_surface_with_anchor | routed-through-resolver | `resolve_status_surface` delegates to `resolve_status_surface_with_anchor` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| specify_cli/coordination/surface_resolver.py:675 | `resolve_status_surface_with_anchor` | `feature_dir : Path = candidate_feature_dir_for_mission ( repo_root , mission_slug )` | repo_root | candidate_feature_dir_for_mission | routed-through-resolver | `resolve_status_surface_with_anchor` delegates to `candidate_feature_dir_for_mission` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| specify_cli/coordination/surface_resolver.py:748 | `resolve_status_surface_with_anchor` | `primary_dir : Path = _compose_primary_feature_dir (` | repo_root | _compose_primary_feature_dir | topology-blind-by-design | WP08 (T035) foundation site 4/4 (FR-005/NFR-009): re-pointed from the deleted `primary_feature_dir_for_mission` wrapper at the module-private `_compose_primary_feature_dir` leaf in the same commit as the wrapper's deletion — routing through the seam here would be self-referential (this module IS part of what the seam's COORD leg serves). `[inventory-only]`: this scanner's tracked-sink name set predates the leaf and does not recognise it, so there is no live-matching composite key for this row; kept for documentation continuity per `tasks.md` §6's four-foundation-sites carve-out rather than silently dropped. |
| specify_cli/core/mission_creation.py:464 | `create_mission_core` | `feature_dir = effective_root / KITTY_SPECS_DIR / mission_slug_formatted` | mission_slug_formatted | raw-path-join | routed-through-resolver | `create_mission_core` joins `mission_slug_formatted`, the OUTPUT of the canonical `mission_dir_name` grammar seam (FR-032/FR-044) — not a raw operator slug; create-time-canonical (the dir is being created here). |
| specify_cli/missions/_read_path_resolver.py:1142 | `resolve_surface_dir_or_typed_error` | `surface : Path = resolve_status_surface ( repo_root , mission_slug )` | repo_root | resolve_status_surface | routed-through-resolver | `resolve_surface_dir_or_typed_error` delegates to `resolve_status_surface` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| specify_cli/missions/_read_path_resolver.py:1303 | `_compose_primary_feature_dir` | `primary_dir : Path = get_main_repo_root ( repo_root ) / KITTY_SPECS_DIR / mission_slug` | mission_slug | raw-path-join | topology-blind-by-design | `_compose_primary_feature_dir` IS the topology-blind primitive definition (WP08 T035: the direct successor of the deleted `primary_feature_dir_for_mission`, whose body this join is byte-identical to); `assert_safe_path_segment` guards the slug just above the join (NFR-002); permanent (C-004), deliberately primary-only. |
| specify_cli/missions/_read_path_resolver.py:1326 | `_compose_mission_anchor_feature_dir` | `return Path ( mission_anchor_root . resolve ( ) / KITTY_SPECS_DIR / mission_slug )` | mission_slug | raw-path-join | topology-blind-by-design | Sanctioned leaf after the caller has resolved and validated the Mission operation anchor; it preserves that caller-owned anchor instead of folding a linked worktree back to the primary checkout. `assert_safe_path_segment(mission_slug)` guards the only untrusted segment immediately before composition. |
| specify_cli/missions/_read_path_resolver.py:1460 | `resolve_planning_read_dir` | `return candidate_feature_dir_for_mission ( repo_root , mission_slug , resolver = resolver )` | repo_root | candidate_feature_dir_for_mission | routed-through-resolver | `resolve_planning_read_dir` delegates to `candidate_feature_dir_for_mission` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |
| specify_cli/status/aggregate.py:542 | `MissionStatus._find_meta_path` | `candidate_dir = candidate_feature_dir_for_mission ( repo_root , mission_slug )` | repo_root | candidate_feature_dir_for_mission | routed-through-resolver | `MissionStatus._find_meta_path` delegates to `candidate_feature_dir_for_mission` — the coord-aware canonical resolver / surface authority (routed; no inline path composition). |

## Disposition summary

| disposition | count | meaning |
| --- | --- | --- |
| routed-through-resolver | 12 | goes through a canonical blessed resolver (cite it) |
| topology-blind-by-design | 2 | deliberately primary-only; the leaf's own definition (live) + the one `[inventory-only]` foundation-site row (WP08 T038) |
| raw-bypass | 3 | 2 compose KITTY_SPECS_DIR/slug inline for a fail-closed diagnostic `raise` payload (no FS sink); 1 composes it for a write-side local staging path (genuine FS write, deferred CLI-arg) |
| **total** | **17** | all AST-discovered ResolutionRow callsites (16 live-matching + 1 `[inventory-only]`) |

## Read-SELECTION callsites (FR-006a)

`discover_selection_callsites()` enumerates every direct
`resolve_mission_read_path(...)` call — the read-side SELECTION authority.
Seam-internal calls are auto-blessed; external calls must be allowlisted in
`audit.py::ALLOWLISTED_SELECTION_CALLSITES`. The table is cross-checked by the
SAME composite undercount/overcount seams as the sink table. On the collapsed
tree all 3 direct selection callsites are seam-internal (zero external).

| file:line | qualname | token | in seam file | disposition | notes |
| --- | --- | --- | --- | --- | --- |
| specify_cli/missions/_read_path_resolver.py:1065 | `resolve_handle_to_read_path` | `return _resolve_mission_read_path (` | yes | seam-internal (auto-blessed) | direct `_resolve_mission_read_path` inside `resolve_handle_to_read_path` — the seam definition. |
| specify_cli/missions/_read_path_resolver.py:1214 | `candidate_feature_dir_for_mission` | `return _resolve_mission_read_path (` | yes | seam-internal (auto-blessed) | direct `_resolve_mission_read_path` inside `candidate_feature_dir_for_mission` — the seam definition. |
| specify_cli/missions/_read_path_resolver.py:1594 | `resolve_feature_dir_for_slug` | `feature_dir : Path = _resolve_mission_read_path (` | yes | seam-internal (auto-blessed) | direct `_resolve_mission_read_path` inside `resolve_feature_dir_for_slug` — the seam definition. |

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
