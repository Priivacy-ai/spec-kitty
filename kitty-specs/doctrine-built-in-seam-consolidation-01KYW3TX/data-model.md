# Data Model — Built-In Doctrine Seam Consolidation (Phase 1)

This mission has no persisted-data schema; the "model" is the **resolution authority** and the
**vocabulary authority**. Entities below are code-level authorities and their invariants.

## Entity: Built-in kind directory authority

- **Home**: `src/doctrine/pack_paths.py`
- **Shape**: `built_in_dir(kind: ArtifactKind) -> Path`
- **Derivation**: `resolve_pack_root("built-in") / kind.plural` (plural from `ArtifactKind.plural`, the SSOT).
- **Invariants**:
  - I1 (single authority): no other `src/` module joins `resolve_pack_root("built-in")` or a `"built-in"` string path-part (enforced by the arch ratchet).
  - I2 (fail-closed): if the pack root cannot be located, `resolve_pack_root` raises `PackRootNotFound`; `built_in_dir` never returns a path to a non-existent-but-silent-empty dir as a substitute.
  - I3 (carve-out): `built_in_dir(ArtifactKind.MISSION_STEP_CONTRACT)` raises a named error (it is package-resource-resolved; #3091).
  - I4 (behaviour-preserving): for every non-carve-out shipped kind, `built_in_dir(kind)` resolves to `packs/built-in/<plural>/`, which exists and is non-empty for `agent_profiles` (anti-vacuity).

## Entity: DoctrineService (post-consolidation)

- **Home**: `src/doctrine/service.py`
- **Change**: the `built_in_root` constructor parameter and the nested `_built_in_dir(artifact)` method are **removed**. The service delegates built-in location entirely to each repository's `_default_built_in_dir()` → `built_in_dir(kind)`.
- **Invariant**: there is exactly one way to locate a built-in root; no caller can inject a nested-shape root that fails open. Test-only synthetic tiers are injected via `SPEC_KITTY_PACKS_ROOT` (honoured by `resolve_pack_root` step 1).

## Entity: Activation-key vocabulary authority

- **Home**: `src/charter/activation/pack_manager.py` — `YAML_KEY_MAP` (derived from `doctrine.artifact_kinds.CHARTER_KIND_TOKENS`).
- **Derived consumers** (must be set-equal to the authority):
  - `src/charter/activation/charter_yaml_io.py` `_ACTIVATION_KEYS`
  - `src/specify_cli/upgrade/migrations/m_unify_charter_activation_finalize.py` `ACTIVATION_KEYS`
- **Invariant**: all consumers derive from `YAML_KEY_MAP` (via a cheap exported plain-tuple); a guard test asserts set-equality. The live drift (`activated_glossary_packs` missing from the migration copy) is closed.

## Entity: ArtifactKind (consumed, not changed)

- **Home**: `src/doctrine/artifact_kinds.py` — `ArtifactKind.plural` / `CHARTER_KIND_TOKENS` are the plural + vocabulary SSOTs. This mission *consumes* them so hand-written literals go away; it does not modify them.

## State / lifecycle

None. This is a structural consolidation; there are no state transitions or persisted lifecycle
entities. The only externally observable "state" is the built-in doctrine **graph identity**, which
MUST be unchanged (NFR-001 / SC-004) — the mission's behaviour-preservation invariant.
