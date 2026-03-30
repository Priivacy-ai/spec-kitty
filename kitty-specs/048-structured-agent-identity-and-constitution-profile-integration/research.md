# Research: Structured Agent Identity & Constitution-Profile Integration

**Feature**: 048 | **Date**: 2026-03-08

## R1: ActorIdentity Serialisation Strategy

**Decision**: `ActorIdentity` serialises to a dict `{"tool": ..., "model": ..., "profile": ..., "role": ...}` inside `StatusEvent.to_dict()`. Legacy bare-string actors are coerced to `ActorIdentity` at the `from_dict()` boundary.

**Rationale**: Keeps the event log backwards-compatible (C-001). Old readers that don't know about structured identity see a dict where they expected a string — but `store.py` delegates to `to_dict()` so the JSONL format naturally evolves. The `from_dict()` path detects `str` vs `dict` and constructs the appropriate `ActorIdentity`.

**Alternatives considered**:
- *Union type `str | ActorIdentity`*: Rejected — forces every consumer to branch on type. Coercion at the boundary gives a single type everywhere.
- *Compact string in JSONL*: Rejected — a dict is self-documenting and easier to query with `jq`.

## R2: Compound String Parsing

**Decision**: The compound format is `tool:model:profile:role` with `:` as separator. Fewer than 4 parts fills from the right with `"unknown"`. A bare string (no colons) becomes `ActorIdentity(tool=string, model="unknown", profile="unknown", role="unknown")`.

**Rationale**: Colons are not valid in tool names, model identifiers, profile IDs, or role names in the existing doctrine YAML convention. The "fill from right" strategy matches natural usage — an agent knows its tool name first, model second, and may not know its profile/role.

**Alternatives considered**:
- *JSON string*: Rejected — harder to type on CLI.
- *Slash separator*: Rejected — clashes with path-like patterns.

## R3: DoctrineCatalog Expansion Loading

**Decision**: Reuse the existing `_load_yaml_id_catalog(directory, pattern)` function for tactics (`*.tactic.yaml`), styleguides (`*.styleguide.yaml`), toolguides (`*.toolguide.yaml`), and procedures (`*.procedure.yaml`). Profiles use `*.agent.yaml` with `profile-id` field (existing convention).

**Rationale**: The loading function is already battle-tested, handles parse errors gracefully, and supports ID extraction from YAML `id` field with filename-stem fallback.

**Alternatives considered**:
- *Use DoctrineService repositories for catalog*: Rejected for catalog — the catalog is a lightweight enumeration used before DoctrineService is available. Repositories are heavier (Pydantic validation).

## R4: Transitive Resolution Algorithm

**Decision**: Depth-first traversal with visited set for cycle detection, following the pattern in `doctrine/curation/engine.py:depth_first_order()`. Operates on typed Pydantic models via `DoctrineService` repositories rather than raw dicts.

**Rationale**: The existing DFS pattern is proven correct and cycle-safe. Using typed models via `DoctrineService` ensures validation happens at load time, not during resolution.

**Alternatives considered**:
- *BFS traversal*: Rejected — DFS produces a more natural reading order (directive → its tactics → their guides).
- *Pre-computed adjacency matrix*: Rejected — doctrine asset counts are small (<100), graph construction overhead not justified.

## R5: Compiler Fallback Path

**Decision**: `compile_constitution()` gains an optional `doctrine_service: DoctrineService | None` parameter. When `None`, the existing `_index_yaml_assets()` / `_load_yaml_asset()` path is used. When provided, transitive resolution via `DoctrineService` repositories replaces the YAML scanning. A diagnostic warning is emitted on fallback.

**Rationale**: Satisfies C-003 (compiler must not hard-depend on DoctrineService). The fallback path is the existing code — no changes needed, just guarded by an `if doctrine_service is not None` branch.

**Alternatives considered**:
- *Always require DoctrineService*: Rejected — breaks bare installations and violates C-003.
- *Strategy pattern (pluggable resolver)*: Rejected — over-engineering for two code paths.

## R6: GovernanceResolution Extension

**Decision**: Extend `GovernanceResolution` with `tactics: list[str]`, `styleguides: list[str]`, `toolguides: list[str]`, `profile_id: str | None`, `role: str | None`. All new fields default to empty/None for backwards compatibility.

**Rationale**: The resolution result must express the full transitive closure of governance artifacts selected for a profile. The existing `paradigms`, `directives`, `tools`, `template_set`, `metadata`, and `diagnostics` fields are preserved.

**Alternatives considered**:
- *Separate `ProfileGovernanceResolution` subclass*: Rejected — introduces type hierarchy complexity; a single flat dataclass with optional fields is simpler.

## R7: generate-for-agent Subcommand

**Decision**: New CLI subcommand `spec-kitty constitution generate-for-agent --profile <id> [--role <role>]` rather than adding flags to existing `generate` command.

**Rationale**: Different semantics — `generate` produces a general constitution from interview answers; `generate-for-agent` produces a profile-aware, transitively resolved constitution. Mixing both into one command with flags creates confusing precedence rules.

**Alternatives considered**:
- *`--profile` flag on existing `generate`*: Rejected — `generate` already has a `--profile` flag with different semantics (interview profile, not agent profile).
