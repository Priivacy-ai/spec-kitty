# Phase 1 Data Model — Doctrine Public API Surface

There are no runtime data entities in this mission. The "model" is the **surface taxonomy**:
how each doctrine path is classified and which door fronts it. This table is the authoritative
disposition IC-01 (re-)produces from a plan-start census.

> **WP01 re-census — finalized 2026-08-10 (this is the authority; the snapshot below it is
> superseded).** The machine-readable disposition manifest lives in
> `tests/architectural/test_doctrine_census.py` (the `DISPOSITION`, `EXEMPT_MANAGEMENT_SURFACE`,
> `TICKETED_BASELINE`, `ORPHAN_REACHED_EXCEPTIONS` constants); the census gate re-runs the AST
> sweep against the live tree so the table cannot drift from what CI enforces. WP02 (INTERNAL
> negative) and WP04 (lazy-import ratchet baseline) import those constants directly.
>
> **Real numbers (measured on-branch, not the snapshot magnitudes):**
>
> | Metric | Snapshot estimate | Re-censused (authority) |
> |---|---|---|
> | Module-level direct `from doctrine …` (`level==0`) | 0 | **0** |
> | Lazy (function-body) direct doctrine imports | 34 files / 70 lines | **29 files / 54 lines** |
> | `if TYPE_CHECKING:` doctrine imports (excluded from reach-through) | — | 11 files / 16 lines |
> | Distinct doctrine module-paths reached (non-TYPE_CHECKING) | 26 | **23** |
> | Laundered `specify_cli.doctrine.*` consumer files | ~10–30 | 14 |
> | Committed golden `packs/built-in/**/*.graph.yaml` fragments | 14 | **14** |
>
> **Resolved "decide IC-01" rows** (prefer FACADE-ONLY / avoid widening the exempt surface):
> `missions.step_projection` → **FACADE-ONLY** (clean `charter.missions` door); `missions.mission_step_repository` → **FACADE-ONLY**;
> `drg.override_policy` → **TICKETED-BASELINE** (doorless mgmt internal, #3179); `drg.migration.hand_authored_overlay.write_reference_graph_with_overlay` → **TICKETED-BASELINE** (doorless mgmt internal, #3179).
> **No reached path is tagged MANAGEMENT** — the per-path MANAGEMENT set is intentionally empty (a
> MANAGEMENT tag widens exemptions, the opposite of this mission's goal).
>
> **Census-drift findings (absent from the snapshot below, surfaced by the re-run):**
> - `doctrine.base` (`DoctrineLayerCollisionWarning`, consumed by `_doctrine_collect.py`) — **FACADE-ONLY** (doorable; prefer a clean door over widening the exempt surface). Consumer is WP05-owned.
> - `src/specify_cli/cli/commands/charter/interview.py` reaches `doctrine.artifact_kinds` (line 70) and the laundered `specify_cli.doctrine.org_charter` conduit (line 187) but is **owned by no migration WP (WP05/06/07)** — an **orphaned reach-through**. Recorded as a documented, ticket-referenced `ORPHAN_REACHED_EXCEPTIONS` entry (#3179) and flagged here for the reviewer/planner to fold into a migration WP (WP07 candidate). The catch-all owner check fails on any *new* orphan.

## Management-surface enumeration (WP01 T004 — SOLE owner)

The **inbound-only management surface** — the only runtime location permitted to import
`doctrine.*` directly — is exactly:

- `src/specify_cli/doctrine/` (the org-pack management subpackage: registry, snapshot, validator, org-charter loader).

This is pinned as the frozen constant `EXEMPT_MANAGEMENT_SURFACE` in
`tests/architectural/test_doctrine_census.py`; `test_management_surface_is_frozen` makes any
growth a deliberate, reviewed diff. **No later WP may reclassify a module into this surface.**
The surface is inbound-only: `specify_cli.doctrine.*` modules may import doctrine, but must not
re-export doctrine-origin symbols in their `__all__` (the laundering conduit, closed source-side
by WP05 / C-005).

## Charter C-007 `__all__` convention — mission extension note (C-007-mission)

The charter C-007 `__all__` declaration convention binds `charter`/`kernel` today. This mission
**consciously extends it to `src/doctrine/`**: the new `doctrine/api.py` (WP02) carries an
explicit `__all__` enumerating the PUBLIC surface, and the census/facade gates pin it. C-007
explicitly permits a per-mission scope decision; this note records that decision. The extension
is behavior-neutral (a curated public surface + enforcement tests), introduces no new package,
and does not mint `src/charter/pyproject.toml` (C-004).

## Taxonomy (value set)

- **PUBLIC** — belongs in `doctrine/api.py __all__`; a stable, externally-consumable symbol.
- **FACADE-ONLY** — reached by non-exempt runtime; fronted by a `charter.*` symbol-level identity re-export. (Most rows.)
- **MANAGEMENT** — reached only by the enumerated inbound-only management surface (`src/specify_cli/doctrine/` + any module IC-01 explicitly adds); no public door.
- **INTERNAL** — no non-exempt consumer; absent from `api.py` and all facades; asserted by a negative test.
- **CONSTRUCTION-ROUTED** — not a re-export at all; obtained via the charter sole-door builder (only `DoctrineService`).

## Disposition table (snapshot — re-census at implement start)

| Doctrine path (symbols) | Sites | Existing door | Disposition | Target door (IC-03) |
|---|---|---|---|---|
| `agent_profiles.profile` (`AgentProfile`, `Role`) | 6 | `charter.profiles` | FACADE-ONLY | existing |
| `agent_profiles.repository` (`AgentProfileRepository`) | 2 | `charter.profiles` | FACADE-ONLY | existing |
| `agent_profiles.capabilities` (`DEFAULT_ROLE_CAPABILITIES`) | 2 | `charter.profiles` | FACADE-ONLY | existing |
| `agent_profiles.diagnostics` (`SkippedProfile`) | 1 | `charter.profiles` | FACADE-ONLY | existing |
| `artifact_kinds.ArtifactKind` | 2 | `charter.drg` | FACADE-ONLY / PUBLIC | existing (also in api.py) |
| `drg.models` (`DRGGraph`, `Relation`, `NodeKind`) | 5 | `charter.drg` | FACADE-ONLY | existing |
| `drg.loader` (`load_graph`, `load_built_in_graph`, `DRGLoadError`) | 1 | partial | FACADE-ONLY | widen `charter.drg` |
| `drg.merge` (`OrgDRGConflict`, `OrgDRGConflictError`) | 2 | partial | FACADE-ONLY | widen `charter.drg` |
| `drg.org_pack_config` (`resolve_org_roots`, errors) | 5 (+~10 laundered) | none | FACADE-ONLY | widen `charter.drg` + close conduit (IC-04) |
| `drg.validator` (`DRGValidationError`) | 1 | none | FACADE-ONLY | widen `charter.drg` |
| `missions.step_contracts` (`MissionStepContract*`) | 3 | `charter.mission_steps` | FACADE-ONLY | existing |
| `missions.step_contracts.GateBinding` | 1 | none | FACADE-ONLY | widen `charter.mission_steps` |
| `missions.repository` (`MissionTemplateRepository`) | 7 | none | FACADE-ONLY / PUBLIC | new `charter.missions` |
| `missions.repository.MissionsRootNotFound` | — | none | FACADE-ONLY | new `charter.missions` |
| `missions.mission_type_repository` (`MissionTypeRepository`, `builtin_mission_type_ids`) | 6 | none | FACADE-ONLY / PUBLIC | new `charter.missions` |
| `missions.step_projection` (`project_template_set`) | 1 | none | **FACADE-ONLY** (WP01: clean door, not MANAGEMENT) | new `charter.missions` |
| `missions.mission_step_repository` | 1 | none | **FACADE-ONLY** (WP01: clean door, not MANAGEMENT) | new `charter.missions` |
| `base` (`DoctrineLayerCollisionWarning`) | 1 | none | **FACADE-ONLY** (WP01 census-drift; doorable) | new narrow door (WP03) |
| `model_task_routing.evaluator/loader` (`RoutingRecommendation`) | 3 | none | PUBLIC | new `charter.model_routing` (symbol-level) |
| `assets.repository`/`assets.models` (`AssetRepository`, `AssetManifest`, errors) | 3 | none | PUBLIC | new `charter.assets` |
| `glossary_packs.GlossaryPack` | 1 | none | FACADE-ONLY | new narrow door |
| `spdd_reasons.apply_spdd_blocks_for_project` | 2 | none | FACADE-ONLY | new narrow door |
| `template_catalog` (`TierRoot`, `resolve_template_by_id`) | 1 | `charter.template_catalog` (partial — `TierRoot` yes, `resolve_template_by_id` NO) | FACADE-ONLY | **widen** `charter.template_catalog` (WP03) with `resolve_template_by_id` |
| `pack_paths` (`built_in_dir`, `built_in_root`) | 2 | none | FACADE-ONLY | new narrow door |
| `drg.override_policy` | 1 | none | **ticketed-baseline** (WP01 T004) — mgmt internal, no clean door | ratchet allowlist + ticket |
| `drg.migration.hand_authored_overlay.write_reference_graph_with_overlay` | 1 | none | **ticketed-baseline** (WP01 T004) — mgmt internal, no clean door | ratchet allowlist + ticket |
| `service.DoctrineService` (raw) | 5 | wrapper exists | CONSTRUCTION-ROUTED | `charter.activation.doctrine_service_builder` (IC-05) |
| `import doctrine` (metadata introspection) | 2 | n/a | INTERNAL/exempt (FR-006 decides) | ratchet policy |

**Truly-INTERNAL (negative-test set, IC-07):** only paths with *no* non-exempt consumer after
IC-01 reconciliation. The four "decide IC-01" rows above must land in MANAGEMENT or
FACADE-ONLY, not pure INTERNAL, because a non-exempt module imports each today.

## Invariants (enforced by architectural tests)

1. **Identity**: for every facade door, `facade.SYMBOL is doctrine.SYMBOL` and `SYMBOL in facade.__all__`.
2. **No direct reach-through**: no non-exempt `src/specify_cli/` module imports `doctrine.*` (module-level or lazy, `level==0`), excluding `TYPE_CHECKING`.
3. **No laundering (source-side)**: no `src/specify_cli/doctrine/*` module lists a doctrine-origin symbol in its `__all__` (the conduit is closed at the source, since a consumer-side check cannot distinguish a laundered symbol from a genuine first-party one).
4. **Sole door**: zero unwrapped raw `doctrine.service.DoctrineService` constructions outside the charter builder.
5. **Negative internal**: the truly-INTERNAL set appears in neither `doctrine/api.py __all__` nor any facade `__all__`.
6. **Behavior preservation**: `regenerate-graph` output byte-identical to the base-commit golden snapshot; facade round-trips unchanged.
