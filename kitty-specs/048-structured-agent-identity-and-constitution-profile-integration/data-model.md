# Data Model: Structured Agent Identity & Constitution-Profile Integration

**Feature**: 048 | **Date**: 2026-03-08

## Entities

### ActorIdentity (NEW)

**Location**: `src/specify_cli/identity.py`

```python
@dataclass(frozen=True)
class ActorIdentity:
    """Structured 4-part agent identity."""
    tool: str       # Agent tool name (e.g., "claude", "copilot")
    model: str      # Model variant (e.g., "claude-opus-4-6", "unknown")
    profile: str    # Governance profile ID (e.g., "implementer", "unknown")
    role: str       # Current role (e.g., "implementer", "reviewer", "unknown")
```

**Serialisation**:
- `to_dict()` → `{"tool": str, "model": str, "profile": str, "role": str}`
- `to_compact()` → `"tool:model:profile:role"`
- `from_compact(s: str)` → `ActorIdentity` (coerces bare strings, fills missing parts with `"unknown"`)
- `from_dict(d: dict)` → `ActorIdentity`
- `from_legacy(s: str)` → `ActorIdentity(tool=s, model="unknown", profile="unknown", role="unknown")`

**Validation rules**:
- All fields must be non-empty strings (validated at construction)
- `:` is forbidden within individual field values
- Unknown/unresolvable parts default to `"unknown"` (never None)

**Relationships**:
- Stored in `StatusEvent.actor` (replaces bare string)
- Stored in WP frontmatter `agent:` field (YAML mapping)
- Parsed from CLI `--agent` flag or `--tool/--model/--profile/--role` flags

---

### StatusEvent (MODIFIED)

**Location**: `src/specify_cli/status/models.py`

**Changed fields**:

| Field | Before | After |
|-------|--------|-------|
| `actor` | `str` | `ActorIdentity` |

**Serialisation changes**:
- `to_dict()`: `actor` emits `ActorIdentity.to_dict()` (a dict, not a string)
- `from_dict()`: Detects `str` vs `dict` for `actor` field; `str` → `ActorIdentity.from_legacy()`; `dict` → `ActorIdentity.from_dict()`

**Backwards compatibility**: Old JSONL files with `"actor": "claude"` read correctly via `from_legacy()`. New files write `"actor": {"tool": "claude", ...}`.

---

### DoctrineCatalog (EXTENDED)

**Location**: `src/specify_cli/constitution/catalog.py`

**New fields**:

| Field | Type | Source Pattern |
|-------|------|----------------|
| `tactics` | `frozenset[str]` | `_load_yaml_id_catalog(dir, "*.tactic.yaml")` |
| `styleguides` | `frozenset[str]` | `_load_yaml_id_catalog(dir, "*.styleguide.yaml")` |
| `toolguides` | `frozenset[str]` | `_load_yaml_id_catalog(dir, "*.toolguide.yaml")` |
| `procedures` | `frozenset[str]` | `_load_yaml_id_catalog(dir, "*.procedure.yaml")` |
| `profiles` | `frozenset[str]` | `_load_yaml_id_catalog(dir, "*.agent.yaml")` using `profile-id` field |

**Existing fields preserved**: `paradigms`, `directives`, `template_sets`

---

### GovernanceResolution (EXTENDED)

**Location**: `src/specify_cli/constitution/resolver.py`

**New fields**:

| Field | Type | Default |
|-------|------|---------|
| `tactics` | `list[str]` | `field(default_factory=list)` |
| `styleguides` | `list[str]` | `field(default_factory=list)` |
| `toolguides` | `list[str]` | `field(default_factory=list)` |
| `profile_id` | `str \| None` | `None` |
| `role` | `str \| None` | `None` |

**Existing fields preserved**: `paradigms`, `directives`, `tools`, `template_set`, `metadata`, `diagnostics`

---

### ResolvedReferenceGraph (NEW)

**Location**: `src/specify_cli/constitution/reference_resolver.py`

```python
@dataclass(frozen=True)
class ResolvedReferenceGraph:
    """Transitive closure of governance artifacts from a set of starting directives."""
    directives: list[str]         # Directive IDs in resolution order
    tactics: list[str]            # Tactic IDs discovered transitively
    styleguides: list[str]        # Styleguide IDs discovered transitively
    toolguides: list[str]         # Toolguide IDs discovered transitively
    unresolved: list[tuple[str, str]]  # (artifact_type, artifact_id) pairs not found
```

**Relationships**:
- Input: directive IDs + `DoctrineService`
- Output: consumed by `GovernanceResolution` construction and `compile_constitution()`

---

### ConstitutionInterview (EXTENDED)

**Location**: `src/specify_cli/constitution/interview.py`

**New optional fields**:

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `agent_profile` | `str \| None` | `None` | Agent profile ID for profile-aware compilation |
| `agent_role` | `str \| None` | `None` | Agent role for profile-aware compilation |

**Serialisation**: New fields included in `to_dict()` / `from_dict()` with None defaults for backwards compatibility.

---

## Entity Relationship Diagram

```
                    ┌─────────────────┐
                    │  ActorIdentity  │
                    │  (tool, model,  │
                    │  profile, role) │
                    └───────┬─────────┘
                            │ stored in
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
       ┌────────────┐ ┌──────────┐ ┌───────────┐
       │StatusEvent │ │   WP     │ │ CLI flags │
       │  .actor    │ │frontmatter│ │ --agent   │
       └────────────┘ └──────────┘ └───────────┘

    ┌───────────────┐    queries    ┌─────────────────┐
    │DoctrineService│◄─────────────│  Constitution    │
    │ .directives   │              │  Compiler        │
    │ .tactics      │              │  (compiler.py)   │
    │ .styleguides  │              └────────┬─────────┘
    │ .toolguides   │                       │ uses
    │ .agent_profiles│                      ▼
    └───────────────┘           ┌──────────────────────┐
                                │ResolvedReferenceGraph│
                                │ (reference_resolver) │
                                └──────────┬───────────┘
                                           │ populates
                                           ▼
                                ┌──────────────────────┐
                                │ GovernanceResolution  │
                                │ (extended with        │
                                │  tactics, styleguides,│
                                │  toolguides, profile) │
                                └──────────────────────┘
```
