# Contracts — Resolution & Activation Foundation

Behavioral (import-surface + CLI) contracts, not HTTP endpoints. Each is a testable assertion an
acceptance test pins (ATDD-first). Revised for DR-1 (unified resolver). "Door" = `get_package_asset_root`.

## C-R1 — Single built-in-pack-root resolution primitive (FR-001, FR-002, FR-012; SC-001)

- **Given** the shipped source tree,
- **When** an architectural test enumerates (a) `SPEC_KITTY_PACKS_ROOT` env reads, (b) `get_package_asset_root` bodies, (c) `_find_relocated_missions_ancestor` defs, (d) the `packs/built-in/missions` sibling-pattern literal,
- **Then** the env read + built-in-pack-root resolution live in exactly one kernel primitive; `doctrine.pack_paths._resolve_built_in`, `default_missions_root`, and the door delegate to it; there is one ancestor-walk def; and the sibling pattern is owned once (kernel `built-in` pattern + `missions` leaf), not forked across three modules.

## C-R2 — Both resolvers relocate via `SPEC_KITTY_PACKS_ROOT` (FR-003; NFR-006; SC-002)

- **Given** `SPEC_KITTY_PACKS_ROOT=<PACKS_ROOT>` with `<PACKS_ROOT>/built-in/missions` present,
- **When** `default_missions_root()` **and** `get_package_asset_root()` each resolve,
- **Then** both resolve under `<PACKS_ROOT>/built-in/missions` — the same tree (proven by a regression test that does not exist today).

## C-R3 — Env precedence is defined (FR-004; C-009)

- **Given** BOTH `SPEC_KITTY_PACKS_ROOT` and `SPEC_KITTY_TEMPLATE_ROOT` are set,
- **When** the built-in pack root is located vs. when the asset-copy/template path runs,
- **Then** `SPEC_KITTY_PACKS_ROOT` governs pack-root **location** and wins for it; `SPEC_KITTY_TEMPLATE_ROOT` still governs the asset-copy/template path (existing callers `template/manager.py`, `init.py`, `bootstrap.py`, upgrade migrations behave unchanged) — pinned by a test that sets both.

## C-R4 — Fail-closed resolution, no legacy fall-through (FR-006, FR-013; SC-001)

- **Given** a pack root with no `built-in/missions` tree (or a legacy layout carrying only `specify_cli/missions`),
- **When** the door or `default_missions_root` resolves,
- **Then** it raises a closed, named error (`MissionsRootNotFound`/`SiblingPathNotFound`/translation) — it does **not** fall through to `specify_cli/missions` or `dev_root` (those fallbacks are intentionally removed, DR-2) and never returns a nonexistent path.

## C-R5 — Documentation truth (FR-005)

- **Given** `kernel/__init__.py`, `kernel/README.md`, and `doctrine/missions/repository.py:37-44`,
- **Then** none asserts a `specify_cli.runtime.home` "re-export" that isn't literally true after IC-01, and none describes a non-existent `dev_roots` tuple; a named test (grep/assertion) pins the absence of the false claims.

## C-A1 — Activation authority, no implicit backfill (FR-007, FR-008; NFR-001)

- **Given** a project config with `mission_type_activations` absent and the project provisioned,
- **When** `PackContext.activated_mission_types` is read,
- **Then** the set comes from the provisioned charter; and a test asserts no code path returns the built-in roster from an *implicit* config-absent default (scoped to `mission_type_activations`, NOT the `_read_activated_kinds` FR-039 fallback).

## C-A2 — Authored-empty preserved (C-008; preserves FR-039)

- **Given** `mission_type_activations: []`,
- **Then** the activation set is empty — provisioning/backfill is NOT triggered.

## C-A3 — Fresh-init provisioning copies default.yaml (FR-009; SC-003)

- **Given** a brand-new `spec-kitty init`,
- **When** init completes,
- **Then** the project config carries an explicit, non-empty `mission_type_activations` **copied from `packs/default.yaml`'s authored list** — not re-derived by scanning the tree via the (env-sensitive) resolver.

## C-A4 — Fail-closed on unprovisionable install (FR-011)

- **Given** a broken install missing `packs/default.yaml`,
- **When** init or migration provisions,
- **Then** it fails with an actionable error — never an empty or implicit set.

## C-A5 — Idempotence + customization-safety (FR-010; NFR-004)

- **Given** an already-provisioned project (incl. a custom, non-built-in mission type),
- **When** provisioning/migration re-runs,
- **Then** config is byte-identical (0 drift) and the custom entry is retained (no catalog intersection).

## C-A6 — Behavior parity at the activation authority (NFR-003; SC-004)

- **Given** a normally-provisioned project under default env,
- **When** the set returned by the **activation authority** (`charter.activation.mission_type_profiles.existing_mission_types` / drg gating at `mission_type_profiles.py:498`, `charter/drg.py:441,471`) and the resolved mission-asset paths are compared before vs after the mission,
- **Then** both are identical (0 diff). **Explicitly NOT measured via `list_available_missions`/`_build_discovery_context`** (fenced unchanged by C-003 — measuring there is a guaranteed no-op).

## C-S1 — Scope fence (C-001, C-003; SC-005)

- **Then** `MissionTypeNotAnArtifactKind` is still raised; `_MISSION_TYPE_UNIVERSE_EXTENSION` intact; `list_available_missions` and `_build_discovery_context` unchanged; `src/specify_cli/missions/` not deleted.
- **Note**: C-002 (nested-vs-flat) and C-004 (keystone/schema) are **review-only fences** — no positive code marker to assert. Optional guard: assert `built_in_dir(kind)` gains no mission-type entry.
