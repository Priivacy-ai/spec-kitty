# Data Model: Agent Profile System

*Phase 1 output for feature 045-agent-profile-system*

## Entities

### AgentProfile (existing — src/doctrine/agent_profiles/profile.py)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| profile_id | str (kebab-case) | Yes | Unique identifier |
| name | str | Yes | Display name |
| purpose | str | Yes | Agent's purpose statement |
| role | Role | No | Role enum or custom string |
| routing_priority | int (0-100) | No | Matching priority, default 50 |
| max_concurrent_tasks | int (>=1) | No | Workload limit |
| specializes_from | str | No | Parent profile ID for inheritance |
| context_sources | ContextSources | No | Doctrine references |
| specialization | Specialization | No | Focus areas and boundaries |
| specialization_context | SpecializationContext | No | Language/framework/file matching criteria |
| collaboration | CollaborationContract | No | Partner roles and handoff protocols |
| mode_defaults | ModeDefaults | No | Autonomy, communication, error handling |
| initialization | InitializationDeclaration | No | Startup greeting and context loading |

**Identity**: `profile_id` (globally unique within shipped + project scope)
**Lifecycle**: Immutable at shipped level; project profiles can be created/updated/deleted
**State transitions**: None (profiles are configuration, not stateful entities)

### Role (existing — src/doctrine/agent_profiles/profile.py)

StrEnum with values: `implementer`, `reviewer`, `architect`, `designer`, `planner`, `researcher`, `curator`, `manager`

Custom strings accepted with warning via `_missing_()` classmethod.

### ContextSources (existing — value object)

| Field | Type | Description |
|-------|------|-------------|
| paradigms | list[str] | Referenced paradigm IDs |
| directives | list[DirectiveRef] | Referenced directive codes + names |
| tactics | list[str] | Referenced tactic IDs |

### DirectiveRef (existing — value object)

| Field | Type | Description |
|-------|------|-------------|
| code | str | Directive code (e.g., "004") |
| name | str | Directive display name |

### Specialization (existing — value object)

| Field | Type | Description |
|-------|------|-------------|
| primary_focus | str | Main area of expertise |
| secondary_awareness | list[str] | Adjacent competencies |
| avoidance_boundary | list[str] | Explicitly out-of-scope areas |

### SpecializationContext (existing — value object)

| Field | Type | Description |
|-------|------|-------------|
| languages | list[str] | Programming languages |
| frameworks | list[str] | Frameworks/libraries |
| file_patterns | list[str] | Glob patterns (e.g., `**/*.py`) |
| keywords | list[str] | Matching keywords |

### CollaborationContract (existing — value object)

| Field | Type | Description |
|-------|------|-------------|
| partners | list[PartnerRole] | Collaboration partners with protocols |

### ModeDefaults (existing — value object)

| Field | Type | Description |
|-------|------|-------------|
| autonomy_level | str | "low" / "medium" / "high" |
| communication_style | str | Communication preference |
| error_handling | str | Error response strategy |

### InitializationDeclaration (existing — value object)

| Field | Type | Description |
|-------|------|-------------|
| greeting | str | Startup message |
| context_loading | list[str] | Context items to load |

### ToolConfig (existing — src/specify_cli/core/tool_config.py)

| Field | Type | Description |
|-------|------|-------------|
| available | list[str] | Tool identifiers (e.g., "claude", "codex") |
| selection | ToolSelectionConfig | Role-based tool preferences |

**YAML key**: `tools` (renamed from `agents` in WP08, backward-compat fallback reads `agents`)

### Directive (existing schema — src/doctrine/schemas/directive.schema.yaml)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| schema_version | str ("1.0") | Yes | Schema version |
| id | str (UPPER_SNAKE) | Yes | Directive identifier |
| title | str | Yes | Display title |
| intent | str | Yes | Governance intent statement |
| tactic_refs | list[str] | No | Referenced tactic IDs |
| enforcement | str ("required"/"advisory") | Yes | Enforcement level |

### TaskContext (existing — src/doctrine/agent_profiles/profile.py)

| Field | Type | Description |
|-------|------|-------------|
| language | str | Primary programming language |
| framework | str | Primary framework |
| complexity | str | "low" / "medium" / "high" |
| file_patterns | list[str] | Files involved |
| keywords | list[str] | Task-related keywords |
| current_tasks | int | Agent's current workload |
| profile_id | str | Specific profile request (optional) |

## Relationships

```
AgentProfile
  ├── has-one Role
  ├── has-one ContextSources
  │     ├── references-many Directive (via DirectiveRef.code)
  │     ├── references-many Paradigm (by ID)
  │     └── references-many Tactic (by ID)
  ├── has-one Specialization
  ├── has-one SpecializationContext
  ├── has-one CollaborationContract
  ├── has-one ModeDefaults
  ├── has-one InitializationDeclaration
  └── specializes-from AgentProfile (self-referential, optional)

AgentProfileRepository
  ├── loads-from shipped/ (immutable package data)
  ├── loads-from .kittify/constitution/agents/ (project overrides)
  ├── merges profiles (two-source: project overrides shipped)
  ├── resolves inheritance (shallow merge up ancestor chain) [WP15]
  └── matches TaskContext → AgentProfile (weighted scoring)

ToolConfig
  ├── reads-from .kittify/config.yaml (tools key)
  └── referenced-by AgentProfileRepository (for tool detection in init)

Mission (schema update in WP14)
  ├── has-many states/steps
  └── each state/step optionally references AgentProfile (by profile-id)
```

## Merge Semantics

### Two-Source Merge (existing — shipped + project)

When a project profile has the same `profile-id` as a shipped profile:
- Project fields override shipped fields at the top level
- Unspecified project fields fall through from shipped

### Inheritance Merge (new — WP15)

When a profile declares `specializes-from`:
1. Walk ancestor chain to root (cycle-safe via `validate_hierarchy()`)
2. Start from root ancestor profile
3. For each descendant in chain, shallow-merge on top:
   - For each section (dict): child keys override parent keys one level deep
   - Parent keys absent from child are preserved
   - Scalar fields: child value replaces parent value
4. Return fully resolved profile

**Example**:
```
Parent (implementer):
  specialization-context:
    languages: [python, javascript]
    frameworks: [django]
  mode-defaults:
    autonomy-level: medium
    communication-style: structured

Child (python-pedro, specializes-from: implementer):
  specialization-context:
    languages: [python]          # overrides parent's languages
  mode-defaults:
    autonomy-level: high         # overrides parent's autonomy-level

Resolved:
  specialization-context:
    languages: [python]          # from child
    frameworks: [django]         # inherited from parent
  mode-defaults:
    autonomy-level: high         # from child
    communication-style: structured  # inherited from parent
```
