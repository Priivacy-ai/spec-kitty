# Data Model: Doctrine Stack Init and Profile Integration

**Feature**: 057-doctrine-stack-init-and-profile-integration
**Date**: 2026-03-20

## Entity Changes

### AgentProfile (modified)

**Location**: `src/doctrine/agent_profiles/profile.py`

| Field | Type | Change | Description |
|-------|------|--------|-------------|
| `excluding` | `list[str] \| dict[str, list[str]] \| None` | **New** | Selective exclusion of inherited fields or values from parent profile |

**Excluding field semantics**:

```yaml
# Field-level: exclude entire inherited fields
excluding:
  - directives
  - canonical_verbs

# Value-level: exclude specific items within inherited lists
excluding:
  directives:
    - DIRECTIVE_010
  canonical_verbs:
    - implement
```

**Merge resolution order** (in `resolve_profile()`):

1. Walk ancestor chain from root to child (bottom-up resolution, top-down application)
2. For each ancestor → descendant pair:
   - Scalar fields: child value overrides parent (existing behavior, unchanged)
   - Dict section fields: child keys override parent keys one level deep (existing behavior, unchanged)
   - List fields: **union merge** — `parent_list ∪ child_list`, deduplicated, order preserved (parent first, then child additions)
3. After merge, apply `excluding`:
   - Field-level: remove entire field from merged result (field reverts to model default)
   - Value-level: remove specific items from merged list

### GenericAgentProfile (new)

**Location**: `src/doctrine/agent_profiles/_proposed/generic-agent.agent.yaml`

```yaml
schema-version: "1.0"
profile-id: generic-agent
name: Generic Agent
description: Default agent profile for work packages without explicit specialization.
role: implementer
routing-priority: 10
max-concurrent-tasks: 5

context-sources:
  doctrine-layers:
    - directives
  directives:
    - DIRECTIVE_028

purpose: >
  Execute general-purpose tasks using efficient local tooling.
  Serves as the default profile for work packages that do not specify
  an explicit agent_profile in their frontmatter.

specialization:
  primary-focus: General-purpose task execution with efficient tooling
  secondary-awareness: All domains — delegates to specialists when task complexity warrants it
  avoidance-boundary: None — generalist by design
  success-definition: Task completed using efficient local tooling, with specialist handoff suggested when appropriate

collaboration:
  handoff-to: [implementer, reviewer, architect]
  handoff-from: []
  works-with: [planner]
  output-artifacts: [implementation, test-suite]
  canonical-verbs: [execute, complete, delegate]

mode-defaults:
  - mode: execution
    description: Direct task execution with minimal ceremony
    use-case: Default mode for general-purpose work

directive-references:
  - code: "028"
    name: Efficient Local Tooling
    rationale: >
      All agents should prefer efficient, low-noise local tooling
      for repository operations.

initialization-declaration: >
  I am Generic Agent. I execute general-purpose tasks using efficient
  local tooling. When a task requires specialist expertise, I suggest
  the appropriate specialist profile for handoff.
```

### ConstitutionDefaults (new)

**Location**: `src/doctrine/constitution/defaults.yaml`

```yaml
# Predefined defaults for "accept defaults" init path.
# Loaded by init.py when user selects defaults.
# Format mirrors constitution generate input.

paradigms:
  - test-first

directives:
  - DIRECTIVE_001   # Architectural Integrity
  - DIRECTIVE_003   # Decision Documentation
  - DIRECTIVE_010   # Specification Fidelity
  - DIRECTIVE_018   # Doctrine Versioning
  - DIRECTIVE_024   # Locality of Change
  - DIRECTIVE_025   # Boy Scout Rule
  - DIRECTIVE_028   # Efficient Local Tooling
  - DIRECTIVE_029   # Agent Commit Signing
  - DIRECTIVE_030   # Test and Typecheck Quality Gate
  - DIRECTIVE_031   # Context-Aware Design
  - DIRECTIVE_032   # Conceptual Alignment

tools:
  - git
  - python
  - pytest
  - ruff
  - mypy
  - spec-kitty
```

### WP Frontmatter (modified)

**Location**: Work package markdown files in `kitty-specs/*/tasks/WP*.md`

| Field | Type | Change | Description |
|-------|------|--------|-------------|
| `agent_profile` | `str` | **New (optional)** | Profile ID the implementing agent operates under. Defaults to `generic-agent` when absent. |

```yaml
---
work_package_id: "WP01"
title: "Build API"
agent_profile: "implementer"    # New field
dependencies: ["WP01"]
---
```

## Relationships

```
AgentProfile
  ├── specializes-from → AgentProfile (parent, optional)
  ├── excluding → [field names] or {field: [values]}  (applied after merge)
  ├── directive-references → DirectiveRef[]
  │     └── code → Directive (in shipped/ or _proposed/)
  └── context-sources.directives → [directive IDs]

ConstitutionDefaults
  ├── paradigms → Paradigm[] (shipped)
  ├── directives → Directive[] (shipped)
  └── tools → Tool[] (runtime registry)

WP Frontmatter
  └── agent_profile → AgentProfile (resolved by AgentProfileRepository)
```

## State Transitions

### Profile Resolution

```
WP frontmatter read
  → agent_profile field present?
    → YES: resolve_profile(profile_id)
      → found in shipped/? → resolve with inheritance → inject identity fragment
      → found in _proposed/? → resolve with inheritance → inject identity fragment
      → not found? → warn "Profile not found, proceeding without specialist identity" → skip injection
    → NO: resolve_profile("generic-agent")
      → found? → inject identity fragment
      → not found? → warn → skip injection
```

### Init Doctrine Flow

```
spec-kitty init
  → .kittify/constitution/constitution.md exists?
    → YES: skip doctrine step, log "Existing constitution detected"
    → NO: prompt "Accept defaults or configure manually?"
      → "Accept defaults": load defaults.yaml → constitution generate
      → "Configure manually": prompt depth → constitution interview (inline)
  → --non-interactive?
    → Apply defaults automatically, no prompt
```

## Validation Rules

- `excluding` field is optional. When present, must be either `list[str]` (field names) or `dict[str, list[str]]` (field → values mapping). Mixed forms are invalid.
- `excluding` a nonexistent field or value is silently ignored.
- `agent_profile` in WP frontmatter is optional. When absent, defaults to `"generic-agent"`.
- `generic-agent.agent.yaml` must pass existing JSON schema validation (`src/doctrine/schemas/agent-profile.schema.yaml`).
- Constitution defaults must reference only shipped directives and paradigms.
