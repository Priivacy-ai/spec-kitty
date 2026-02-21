# Data Model: Agent Profile Domain Model

**Feature**: 047-agent-profile-domain-model
**Date**: 2026-02-16

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   AgentProfile                          │
│ (frozen dataclass — src/doctrine/model/profile.py)      │
├─────────────────────────────────────────────────────────┤
│ profile_id: str              [PK, required]             │
│ name: str                    [required]                 │
│ description: str             [default: ""]              │
│ schema_version: str          [default: "1.0"]           │
│ role: Role | str             [default: Role.IMPLEMENTER]│
│ capabilities: list[str]      [default: []]              │
│ specializes_from: str | None [FK → AgentProfile]        │
│ routing_priority: int        [0-100, default: 50]       │
│ max_concurrent_tasks: int    [>0, default: 5]           │
├─────────────────────────────────────────────────────────┤
│ context_sources: ContextSources          [section 1]    │
│ purpose: str                             [section 2]    │
│ specialization: Specialization           [section 3]    │
│ collaboration: CollaborationContract     [section 4]    │
│ mode_defaults: list[ModeDefault]         [section 5]    │
│ initialization_declaration: str          [section 6]    │
│ specialization_context: SpecializationContext | None     │
│ directive_references: list[DirectiveRef] [optional]     │
├─────────────────────────────────────────────────────────┤
│ + to_dict() → dict[str, Any]                            │
│ + from_dict(data) → AgentProfile                        │
│ + validate() → list[str]  (returns error messages)      │
└─────────────────────────────────────────────────────────┘
         │ specializes_from
         ▼
┌─────────────────────────────────────────────────────────┐
│            SpecializationHierarchy                       │
│ (dataclass — src/doctrine/model/hierarchy.py)           │
├─────────────────────────────────────────────────────────┤
│ roots: list[HierarchyNode]                              │
│ _index: dict[str, HierarchyNode]                        │
├─────────────────────────────────────────────────────────┤
│ + build(profiles: list[AgentProfile]) → Self            │
│ + find_best_match(ctx: TaskContext) → AgentProfile|None │
│ + get_node(profile_id: str) → HierarchyNode | None     │
│ + get_children(profile_id: str) → list[HierarchyNode]  │
│ + get_ancestors(profile_id: str) → list[str]            │
│ + as_tree() → dict  (for Rich Tree rendering)           │
│ + validate() → list[str]                                │
└─────────────────────────────────────────────────────────┘
         │ contains
         ▼
┌─────────────────────────────────────────────────────────┐
│                   HierarchyNode                         │
│ (frozen dataclass)                                      │
├─────────────────────────────────────────────────────────┤
│ profile: AgentProfile                                   │
│ parent: HierarchyNode | None                            │
│ children: list[HierarchyNode]                           │
│ depth: int                                              │
└─────────────────────────────────────────────────────────┘
```

## Value Objects

### Role (StrEnum)

```python
class Role(StrEnum):
    IMPLEMENTER = "implementer"
    REVIEWER = "reviewer"
    ARCHITECT = "architect"
    PLANNER = "planner"
    RESEARCHER = "researcher"
    CURATOR = "curator"
    MANAGER = "manager"
```

Custom roles are supported as plain strings where `Role` is typed as `Role | str`.

### Specialization (frozen dataclass)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `primary_focus` | `str` | Yes | What the agent primarily does |
| `secondary_awareness` | `str` | No | Adjacent domains the agent monitors |
| `avoidance_boundary` | `str` | No | What the agent explicitly avoids |
| `success_definition` | `str` | No | How success is measured for this agent |

### CollaborationContract (frozen dataclass)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `handoff_to` | `list[str]` | `[]` | Profile IDs this agent hands work to |
| `handoff_from` | `list[str]` | `[]` | Profile IDs that hand work to this agent |
| `works_with` | `list[str]` | `[]` | Profile IDs for peer collaboration |
| `output_artifacts` | `list[str]` | `[]` | Expected output types (ADR, spec, code, review) |
| `operating_procedures` | `list[str]` | `[]` | Step-by-step workflow rules |
| `canonical_verbs` | `list[str]` | `[]` | Allowed action verbs (from Directive 009) |

### SpecializationContext (frozen dataclass)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `languages` | `list[str]` | `[]` | Programming languages (python, typescript, rust) |
| `frameworks` | `list[str]` | `[]` | Frameworks (fastapi, django, react) |
| `file_patterns` | `list[str]` | `[]` | Glob patterns (`**/*.py`, `src/api/**`) |
| `domain_keywords` | `list[str]` | `[]` | Task domain keywords (api, testing, security) |
| `writing_style` | `list[str]` | `[]` | Writing style preferences (technical, narrative) |
| `complexity_preference` | `list[str]` | `[]` | Preferred complexity levels (low, medium, high) |

### ContextSources (frozen dataclass)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `doctrine_layers` | `list[str]` | `[]` | Doctrine layers this agent loads |
| `directives` | `list[str]` | `[]` | Directive codes this agent adheres to |
| `additional` | `list[str]` | `[]` | Additional context source paths |

### ModeDefault (frozen dataclass)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | `str` | Yes | Mode identifier (e.g., `/analysis-mode`) |
| `description` | `str` | Yes | What this mode does |
| `use_case` | `str` | Yes | When to use this mode |

### DirectiveRef (frozen dataclass)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | `str` | Yes | Directive code (e.g., "001", "007") |
| `name` | `str` | Yes | Directive name |
| `rationale` | `str` | Yes | Why this agent uses this directive |

### TaskContext (frozen dataclass — input to hierarchy matching)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `language` | `str \| None` | `None` | Target language |
| `framework` | `str \| None` | `None` | Target framework |
| `file_paths` | `list[str]` | `[]` | Files involved in the task |
| `keywords` | `list[str]` | `[]` | Task description keywords |
| `complexity` | `str` | `"medium"` | Task complexity (low/medium/high) |
| `required_role` | `Role \| str \| None` | `None` | Required role |
| `active_tasks` | `dict[str, int]` | `{}` | profile_id → current active task count |

## Weighted Context Matching Algorithm (from DDR-011)

```
score(profile, context) =
    language_match(profile.specialization_context.languages, context.language) × 0.40
  + framework_match(profile.specialization_context.frameworks, context.framework) × 0.20
  + file_pattern_match(profile.specialization_context.file_patterns, context.file_paths) × 0.20
  + keyword_match(profile.specialization_context.domain_keywords, context.keywords) × 0.10
  + exact_id_match(profile.profile_id, context) × 0.10

adjusted_score = score
  × workload_penalty(profile, context.active_tasks)
  × complexity_adjustment(profile, context.complexity)
  × (profile.routing_priority / 100)
```

### Workload Penalty

| Active tasks | Penalty factor |
|-------------|----------------|
| 0-2 | 1.0 (no penalty) |
| 3-4 | 0.85 (15% penalty) |
| 5+ | 0.70 (30% penalty) |

### Complexity Adjustment

| Complexity | Specialist | Parent/Generalist |
|-----------|-----------|-------------------|
| low | +10% (1.10) | neutral (1.0) |
| medium | neutral (1.0) | neutral (1.0) |
| high | -10% (0.90) | +10% (1.10) |

## Repository Service

### AgentProfileRepository

```
AgentProfileRepository
├── __init__(shipped_dir: Path, project_dir: Path | None)
├── list_all() → list[AgentProfile]
├── get(profile_id: str) → AgentProfile | None
├── find_by_role(role: Role | str) → list[AgentProfile]
├── find_by_specialization(context: TaskContext) → list[AgentProfile]
├── get_hierarchy() → SpecializationHierarchy
├── save(profile: AgentProfile) → None  # writes to project_dir
└── delete(profile_id: str) → bool      # removes from project_dir only
```

### Loading Order

1. Scan `shipped_dir` (via `importlib.resources`) for `*.agent.yaml` files
2. Parse each into `AgentProfile` via `from_dict()`, skip invalid with warning
3. Scan `project_dir` (filesystem Path) for `*.agent.yaml` files
4. For each project profile:
   - If `profile_id` matches a shipped profile → field-level merge (project wins)
   - If `profile_id` is new → add to set
5. Build `SpecializationHierarchy` from merged profile set
6. Return immutable profile set + hierarchy

### Field-Level Merge Semantics

When a project profile overrides a shipped profile:

- Each top-level field is compared independently
- If the project profile provides a non-default value, it replaces the shipped value
- If the project profile omits a field (or provides default/empty), the shipped value is retained
- Nested value objects (Specialization, CollaborationContract) are merged recursively at field level
- List fields are replaced wholesale (no list merging) — project list replaces shipped list

## YAML File Format (.agent.yaml)

```yaml
# architect.agent.yaml
schema_version: "1.0"
profile_id: architect
name: "Architect Alphonso"
description: "Clarify complex systems with contextual trade-offs."
role: architect
capabilities:
  - read
  - write
  - search
  - edit
  - bash
routing_priority: 50
max_concurrent_tasks: 3

context_sources:
  doctrine_layers:
    - general_guidelines
    - operational_guidelines
  directives:
    - "001"
    - "003"
    - "007"

purpose: >
  Clarify and decompose complex socio-technical systems, surfacing trade-offs
  and decision rationale. Provide architecture patterns and interfaces that
  improve shared understanding and traceability.

specialization:
  primary_focus: "System decomposition, design interfaces, ADRs"
  secondary_awareness: "Cultural, political, and process constraints"
  avoidance_boundary: "Coding-level specifics, tool evangelism, premature optimization"
  success_definition: "Architectural clarity improves decision traceability"

collaboration:
  handoff_to:
    - planner
    - implementer
  handoff_from:
    - researcher
  works_with:
    - reviewer
  output_artifacts:
    - ADR
    - architecture-diagram
    - interface-contract
  operating_procedures:
    - "Decompose before delegating"
    - "Always document alternatives considered"
  canonical_verbs:
    - audit
    - synthesize
    - plan

mode_defaults:
  - mode: "/analysis-mode"
    description: "Structured reasoning"
    use_case: "Technical or conceptual analysis"
  - mode: "/creative-mode"
    description: "Generative narrative"
    use_case: "Drafting vision docs, storytelling"
  - mode: "/meta-mode"
    description: "Process reflection"
    use_case: "Context validation, retrospectives"

initialization_declaration: |
  Agent "Architect Alphonso" initialized.
  Context layers: Operational, Strategic, Command, Bootstrap.
  Purpose acknowledged: Clarify systems, surface trade-offs.

directive_references:
  - code: "001"
    name: "CLI & Shell Tooling"
    rationale: "Repo/file discovery, structural scans"
  - code: "003"
    name: "Repository Quick Reference"
    rationale: "Fast topology recall for decomposition"
  - code: "007"
    name: "Agent Declaration"
    rationale: "Ensure authority confirmation prior to ADR emission"
```

## ToolConfig (renamed from AgentConfig)

No schema changes — only naming:

| Old Name | New Name |
|----------|----------|
| `AgentConfig` | `ToolConfig` |
| `AgentSelectionConfig` | `ToolSelectionConfig` |
| `AgentConfigError` | `ToolConfigError` |
| `config.yaml` key `agents:` | `tools:` (with `agents:` fallback) |

The class structure, fields, and behavior remain identical.
