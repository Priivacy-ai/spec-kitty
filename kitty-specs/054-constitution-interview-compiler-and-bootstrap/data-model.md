# Data Model: Constitution Interview Compiler and Context Bootstrap

**Feature**: 054 | **Date**: 2026-03-09

This feature extends existing constitution artifacts rather than introducing a new database-backed domain. The key design work is the shape of interview input, compiled references, and action-scoped context metadata.

---

## Entity: `InterviewAnswers`

**Location**: `.kittify/constitution/interview/answers.yaml`

**Purpose**: Canonical maintainer input to `spec-kitty constitution generate`.

### Core fields

| Field | Type | Required | Notes |
|------|------|----------|-------|
| `mission` | string | yes | Expected mission key, typically `software-dev` |
| `profile` | string | yes | Interview profile such as `minimal` or `comprehensive` |
| `selected_paradigms` | list[string] | yes | Validated against shipped paradigm catalog |
| `selected_directives` | list[string] | yes | Validated against shipped directive catalog |
| `available_tools` | list[string] | yes | Validated against shipped tool catalog/runtime tool registry rules |
| `template_set` | string | yes | Validated against shipped template catalog with filesystem fallback |
| `answers` | map[string, string] | yes | Interview question responses |
| `local_supporting_files` | list[`LocalDoctrineFileDeclaration`] | no | Explicit project-local doctrine support files declared by the maintainer |

### Example

```yaml
mission: software-dev
profile: minimal
selected_paradigms:
  - test-first
selected_directives:
  - 003-decision-documentation-requirement
  - 010-specification-fidelity-requirement
available_tools:
  - git
  - pytest
template_set: software-dev-default
answers:
  project_type: existing-cli
  team_size: small
local_supporting_files:
  - path: docs/governance/project-planning.md
    action: plan
    target_kind: directive
    target_id: 003-decision-documentation-requirement
```

### Validation rules

- Shipped doctrine selections are validated against the shipped-only doctrine catalog by default.
- `_proposed/` doctrine artifacts do not participate unless a caller explicitly opts into curation-mode catalog loading.
- `local_supporting_files[*].path` must be an explicit file path, not a directory or glob.
- Local files may be declared without a target, but when `target_kind` + `target_id` identify a shipped concept, the local file is additive only and triggers a warning on conflict.

---

## Entity: `LocalDoctrineFileDeclaration`

**Declared in**: `answers.yaml`  
**Materialized in**: `references.yaml`

**Purpose**: Describes one project-local doctrine support file that participates in generation/context without becoming authoritative over shipped doctrine.

| Field | Type | Required | Notes |
|------|------|----------|-------|
| `path` | string | yes | Explicit project-relative or absolute file path |
| `action` | enum(`specify`,`plan`,`implement`,`review`) or null | no | Null means global; otherwise action-scoped |
| `target_kind` | enum(`directive`,`paradigm`,`tactic`,`styleguide`,`toolguide`,`procedure`,`template_set`) or null | no | Optional doctrinal concept the file supplements |
| `target_id` | string or null | no | Optional shipped concept ID the file supplements |
| `relationship` | enum(`additive`) | derived | Always additive in this feature |
| `warning` | string or null | derived | Present when the declaration overlaps a shipped concept |

### State rules

- A declaration with `action: null` participates in all action contexts.
- A declaration with an action participates only in that action's context retrieval.
- If `target_kind` and `target_id` match a shipped artifact, shipped content remains primary and the declaration is surfaced with a warning.

---

## Entity: `CompiledReferences`

**Location**: `.kittify/constitution/references.yaml`

**Purpose**: Generated manifest used by `constitution context` for runtime scoping and output reporting.

### Proposed shape

```yaml
mission: software-dev
template_set: software-dev-default
selected_paradigms:
  - test-first
selected_directives:
  - 003-decision-documentation-requirement
selected_tools:
  - git
  - pytest
references:
  - id: "DIRECTIVE:003-decision-documentation-requirement"
    kind: directive
    summary: "Record material decisions and their rationale."
  - id: "LOCAL:docs/governance/project-planning.md"
    kind: local_support
    path: docs/governance/project-planning.md
    action: plan
    target_kind: directive
    target_id: 003-decision-documentation-requirement
    relationship: additive
    warning: "Local support file overlaps shipped directive 003-decision-documentation-requirement; shipped content remains primary."
```

### Rules

- Shipped doctrine entries stay concise and do not copy full prose.
- Local support files are represented explicitly so `generate --json` can surface them via `library_files`.
- `references.yaml` is the runtime bridge between interview declarations and action-scoped context retrieval.

---

## Entity: `ActionIndex`

**Location**: `src/doctrine/missions/software-dev/actions/<action>/index.yaml`

**Purpose**: Declares which shipped doctrine artifacts are eligible for a given action.

```yaml
action: plan
directives:
  - 003-decision-documentation-requirement
  - 010-specification-fidelity-requirement
tactics:
  - requirements-validation-workflow
paradigms:
  - test-first
styleguides: []
toolguides:
  - efficient-local-tooling
procedures: []
```

### Retrieval rule

For each artifact type:

`eligible_ids = action_index[type] intersect project_selected_ids`

Action-scoped local support files are then appended if their `action` matches the requested action or is null.

---

## Entity: `ContextState`

**Location**: `.kittify/constitution/context-state.json`

**Purpose**: Tracks whether a given action has already received bootstrap-depth context.

```json
{
  "specify": {"loaded_at": "2026-03-09T10:00:00Z"},
  "plan": {"loaded_at": "2026-03-09T10:05:00Z"}
}
```

### State transitions

- Missing action key -> first call defaults to depth 2 bootstrap mode.
- Present action key -> subsequent calls default to depth 1 compact mode.
- Explicit `--depth` overrides bootstrap-derived default without changing the declaration model.

---

## Output Files Affected by This Feature

| File | Produced by | Purpose |
|------|-------------|---------|
| `.kittify/constitution/constitution.md` | `generate` | Human-readable selection manifest |
| `.kittify/constitution/references.yaml` | `generate` | Runtime reference manifest including local support declarations |
| `.kittify/constitution/governance.yaml` | `sync` | Existing sync output |
| `.kittify/constitution/directives.yaml` | `sync` | Existing sync output |
| `.kittify/constitution/metadata.yaml` | `sync` | Existing sync output |
| `.kittify/constitution/context-state.json` | `context` | Bootstrap state tracking |

`agents.yaml` remains absent. Generated `library/` materialization remains removed.
