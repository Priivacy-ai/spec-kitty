# Data Model: CLI Bug Sweep & Tool Surface Self-Registration

Only IC-04 introduces a new entity. ICs 01–03 have no new entities.

---

## SurfaceRegistration

A value object declared by each tool surface provider module at module level. Aggregated into `SurfaceProviderRegistry` at import time. Replaces the four centralized literal regions in `service.py`.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `provider_class` | `type[ReportingSurfaceProvider]` | The provider class to instantiate |
| `definitions` | `tuple[SurfaceDefinition, ...]` | One or more definition factories this provider contributes. Most providers: 1 element. `session_presence`: 3 elements. |
| `kind_tokens` | `dict[str, SurfaceKind]` | CLI `--kind` token strings → `SurfaceKind` values. Includes both hyphen and underscore aliases where the existing `_KIND_TOKENS` dict has them. |
| `synthetic_key` | `str \| None` | When set, definitions are registered exactly once under this key instead of being fanned out per configured tool key. `None` for all standard providers. `PLUGIN_BUNDLE_TOOL_KEY` for `plugin_bundle`. |
| `order` | `int` | Explicit stable integer controlling position in `build_providers()` output. Must be unique across all registrations. |

### Invariants

- `definitions` must be non-empty.
- `kind_tokens` must be non-empty.
- `order` values must be unique across all registered `SurfaceRegistration` instances (enforced by `SurfaceProviderRegistry.register()`).
- When `synthetic_key` is set, `definitions` must contain exactly one element (the synthetic key implies a single registration point).

### State transitions

Not applicable — `SurfaceRegistration` is an immutable value object. The `SurfaceProviderRegistry` class store is populated once at import time and not mutated at runtime.

---

## SurfaceProviderRegistry

A class-variable store that aggregates `SurfaceRegistration` instances. Analogous to `MigrationRegistry` in `src/specify_cli/upgrade/registry.py`.

### Responsibilities

- Accepts `register(SurfaceRegistration)` calls at module import time.
- Provides `build_kind_tokens() → dict[str, SurfaceKind]` (replaces `_KIND_TOKENS`).
- Provides `build_providers() → list[ReportingSurfaceProvider]` (replaces `build_providers()` function).
- Provides `build_registry(tool_keys) → ToolSurfaceRegistry` (replaces `build_registry()` function).

### Ordering guarantee

Registrations are sorted by `SurfaceRegistration.order` before any list is built. The `order` field is the only determinism source — import order is not relied upon.

---

## Existing entities (unchanged)

| Entity | Location | Relationship |
|--------|----------|--------------|
| `ReportingSurfaceProvider` | `src/specify_cli/tool_surface/providers/protocol.py` | `SurfaceRegistration.provider_class` is a subclass of this |
| `SurfaceDefinition` | `src/specify_cli/tool_surface/` | Elements of `SurfaceRegistration.definitions` |
| `SurfaceKind` | `src/specify_cli/tool_surface/` | Values in `SurfaceRegistration.kind_tokens` |
| `ToolSurfaceRegistry` | `src/specify_cli/tool_surface/registry.py` | Produced by `SurfaceProviderRegistry.build_registry()` |
