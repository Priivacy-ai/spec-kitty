# Phase 1 Data Model — Resolution & Activation Foundation

This mission changes **resolution seams and an authority source**, not persisted data. No schema
migration, no new stored entity. The "entities" are the code-level seams whose identity and
invariants the mission pins. Revised for DR-1 (unified resolver): the former Seam 1 (door) and Seam 2
(`default_missions_root`) collapse into **one** primitive.

## Seam 1 — Built-in-pack-root resolver (the unified primitive)

- **Represents**: the single function that reads `SPEC_KITTY_PACKS_ROOT` and locates the built-in pack
  root (`packs/built-in`); the missions tree is `<that root>/missions`.
- **Owner (after)**: `kernel` (the PACKS_ROOT-aware entry point, built on the existing env-agnostic
  `kernel.sibling_paths.resolve_installed_sibling`). Consumed **downward** by:
  - `doctrine.pack_paths._resolve_built_in` (delegates; its own `SPEC_KITTY_PACKS_ROOT` read at
    `pack_paths.py:204` is retired),
  - `doctrine.missions.repository.default_missions_root` = `built_in_root()/"missions"`,
  - `kernel.paths.get_package_asset_root` (the door) = `<root>/missions`,
  - `specify_cli.runtime.home.get_package_asset_root` (thin delegation; legacy fallbacks removed).
- **Inputs**: `SPEC_KITTY_PACKS_ROOT` (pack-root location), install layout. `SPEC_KITTY_TEMPLATE_ROOT`
  is **not** an input to pack-root location — it stays the asset-copy/template override (C-009).
- **Invariants**:
  - I-1: exactly one `SPEC_KITTY_PACKS_ROOT` read + one built-in-pack-root resolution body (NFR-001).
  - I-2: lives in `kernel`; kernel imports no `doctrine`/`specify_cli` (C-005). Reading an env var in
    kernel is layer-legal and adds no upward edge.
  - I-3: `default_missions_root()` and `get_package_asset_root()` resolve the **same** tree under the
    **same** env (default / PACKS_ROOT / both-vars).
  - I-4: fails closed (`MissionsRootNotFound`/`SiblingPathNotFound`/`PackRootNotFound` translation) —
    no fall-through to `specify_cli/missions`/`dev_root`, never a nonexistent path. **NB (delta review):**
    since `built_in_root()` only verifies `packs/built-in` exists, `default_missions_root =
    built_in_root()/"missions"` must re-add an `.is_dir()` check on the `/missions` leaf + raise
    `MissionsRootNotFound` — a bare join would return a nonexistent path and regress this invariant.
  - I-5: the `PackRootNotFound` translation survives at the `doctrine.pack_paths` boundary (a consumer
    depends on that specific type).
  - I-6: the sibling shape is owned once (kernel `built-in` pattern + `missions` leaf name), FR-012.

## Seam 2 — Activation authority (`activated_mission_types`)

- **Represents**: the single source of which mission types a project has.
- **Owner**: `charter.PackContext.activated_mission_types`, sourced from config `mission_type_activations`,
  provisioned by **copying** `packs/default.yaml`'s authored list.
- **State resolution (after)**:
  | Config state | Result (after) |
  |---|---|
  | `mission_type_activations` present (non-empty) | that set, verbatim (custom entries preserved) |
  | `mission_type_activations: []` (authored empty) | empty set — **unchanged** (C-008/FR-039) |
  | key absent, project provisioned | from the provisioned charter |
  | key absent, unprovisionable install (no `default.yaml`) | **fail closed**, actionable error (FR-011) |
  | key absent (old behavior) | ~~silent all-four backfill~~ **removed** (FR-008) |
- **Invariants**:
  - I-7: no implicit "all four" backfill site remains (NFR-001), scoped to `mission_type_activations`
    (the `_read_activated_kinds` FR-039 fallback is a different contract, untouched).
  - I-8: provisioning never intersects the built-in catalog — custom types survive (FR-010).
  - I-9: provisioning is idempotent — byte-identical config on re-run (NFR-004).
  - I-10: provisioning **copies** the authored list; it does not re-derive via the env-sensitive
    resolver — so Seam 2 has no runtime dependency on Seam 1's env (keeps IC-02→IC-05 decoupled).

## Roster note

"The four built-in types" is never a literal — the roster is the disk-scanned, cached
`builtin_mission_type_id_set()`. Assertions reference the function, not a hardcoded set.

## Explicitly unchanged (scope fence)

- `mission-type` is **not** an `ArtifactKind` — `MissionTypeNotAnArtifactKind` still raised (C-001).
- Availability readers `list_available_missions` / `_build_discovery_context` remain filesystem-based
  and are **not** repointed (C-003).
