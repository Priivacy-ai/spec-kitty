# Data Model: Doctrine Artifact Domain Models

**Date**: 2026-02-25
**Feature**: 046-doctrine-artifact-domain-models

## Entity Diagram

```
DoctrineService
├── DirectiveRepository  → Directive
├── TacticRepository     → Tactic (contains TacticStep, TacticReference)
├── StyleguideRepository → Styleguide (contains AntiPattern)
├── ToolguideRepository  → Toolguide
├── ParadigmRepository   → Paradigm
└── AgentProfileRepository → AgentProfile (existing, unchanged)
```

## Entities

### Directive

| Field | Type | Required | YAML Key | Notes |
|-------|------|----------|----------|-------|
| `id` | `str` | Yes | `id` | Pattern: `^[A-Z][A-Z0-9_-]*$` (SCREAMING_SNAKE_CASE) |
| `schema_version` | `str` | Yes | `schema-version` | Pattern: `^1\.0$` |
| `title` | `str` | Yes | `title` | Human-readable name |
| `intent` | `str` | Yes | `intent` | Multiline: behavioral context and purpose |
| `enforcement` | `Enforcement` | Yes | `enforcement` | Enum: `required`, `advisory` |
| `tactic_refs` | `list[str]` | No | `tactic-refs` | Kebab-case tactic IDs; default empty list |
| `scope` | `str` | No | `scope` | Multiline: when directive applies, exceptions |
| `procedures` | `list[str]` | No | `procedures` | Ordered steps to follow |
| `integrity_rules` | `list[str]` | No | `integrity-rules` | Hard constraints |
| `validation_criteria` | `list[str]` | No | `validation-criteria` | Compliance verification criteria |

**Identity**: Looked up by `id` (e.g., `"DIRECTIVE_004"`) or numeric shorthand (e.g., `"004"`).
**File convention**: `{NNN}-{slug}.directive.yaml` or `{slug}.directive.yaml`

### Tactic

| Field | Type | Required | YAML Key | Notes |
|-------|------|----------|----------|-------|
| `id` | `str` | Yes | `id` | Pattern: `^[a-z][a-z0-9-]*$` (kebab-case) |
| `schema_version` | `str` | Yes | `schema-version` | |
| `name` | `str` | Yes | `name` | Human-readable name |
| `purpose` | `str` | No | `purpose` | Multiline description |
| `steps` | `list[TacticStep]` | Yes | `steps` | minItems: 1 |
| `references` | `list[TacticReference]` | No | `references` | Cross-artifact references |

**TacticStep**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `title` | `str` | Yes | Step name |
| `description` | `str` | No | Multiline prose |
| `examples` | `list[str]` | No | Illustrative examples |
| `references` | `list[TacticReference]` | No | Per-step cross-references |

**TacticReference**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | `str` | Yes | Reference name |
| `type` | `ReferenceType` | Yes | Enum: `styleguide`, `tactic`, `directive`, `toolguide` |
| `id` | `str` | Yes | Artifact ID |
| `when` | `str` | Yes | When to invoke |

**File convention**: `{slug}.tactic.yaml`

### Styleguide

| Field | Type | Required | YAML Key | Notes |
|-------|------|----------|----------|-------|
| `id` | `str` | Yes | `id` | Kebab-case |
| `schema_version` | `str` | Yes | `schema-version` | |
| `title` | `str` | Yes | `title` | |
| `scope` | `Scope` | Yes | `scope` | Enum: `code`, `docs`, `architecture`, `testing`, `operations`, `glossary` |
| `principles` | `list[str]` | Yes | `principles` | minItems: 1 |
| `anti_patterns` | `list[AntiPattern]` | No | `anti_patterns` | |
| `quality_test` | `str` | No | `quality_test` | Multiline |
| `references` | `list[str]` | No | `references` | |

**AntiPattern**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | `str` | Yes | |
| `description` | `str` | Yes | |
| `bad_example` | `str` | Yes | |
| `good_example` | `str` | Yes | |

**File convention**: `{slug}.styleguide.yaml`

### Toolguide

| Field | Type | Required | YAML Key | Notes |
|-------|------|----------|----------|-------|
| `id` | `str` | Yes | `id` | Kebab-case |
| `schema_version` | `str` | Yes | `schema-version` | |
| `tool` | `str` | Yes | `tool` | Tool name |
| `title` | `str` | Yes | `title` | |
| `guide_path` | `str` | Yes | `guide-path` | Pattern: `^src/doctrine/.+\.md$` |
| `summary` | `str` | Yes | `summary` | |
| `commands` | `list[str]` | No | `commands` | |

**File convention**: `{slug}.toolguide.yaml`

### Paradigm

| Field | Type | Required | YAML Key | Notes |
|-------|------|----------|----------|-------|
| `id` | `str` | Yes | `id` | Kebab-case |
| `schema_version` | `str` | Yes | `schema-version` | |
| `name` | `str` | Yes | `name` | |
| `summary` | `str` | Yes | `summary` | Multiline |

**File convention**: `{slug}.paradigm.yaml`

### DoctrineService

| Attribute | Type | Notes |
|-----------|------|-------|
| `directives` | `DirectiveRepository` | Lazy-initialized |
| `tactics` | `TacticRepository` | Lazy-initialized |
| `styleguides` | `StyleguideRepository` | Lazy-initialized |
| `toolguides` | `ToolguideRepository` | Lazy-initialized |
| `paradigms` | `ParadigmRepository` | Lazy-initialized |
| `agent_profiles` | `AgentProfileRepository` | Lazy-initialized, reuses existing class |

**Constructor**: `DoctrineService(shipped_root: Path | None = None, project_root: Path | None = None)`

## Enumerations

### Enforcement

```
required | advisory
```

### Scope (Styleguide)

```
code | docs | architecture | testing | operations | glossary
```

### ReferenceType (Tactic)

```
styleguide | tactic | directive | toolguide
```

## Relationships

- **Directive → Tactic**: via `tactic_refs` list (string IDs, resolved on-demand through `TacticRepository`)
- **Tactic → other artifacts**: via `references` list (`TacticReference` with type + ID)
- **AgentProfile → Directive**: via `directive_references` list (existing, unchanged)
- **DoctrineService → all repositories**: composition (holds references)

All cross-artifact references are string IDs resolved on-demand — no eager loading or embedded objects.
