# Data Model: Constitution Parser and Structured Config

**Feature**: 045-constitution-doctrine-config-sync
**Date**: 2026-02-15

## Entities

### ConstitutionSection

Represents a parsed section of the constitution markdown.

| Field | Type | Description |
|-------|------|-------------|
| heading | str | Section heading text (e.g., "Testing Requirements") |
| level | int | Heading level (2 = ##, 3 = ###) |
| content | str | Raw markdown content of the section |
| structured_data | dict | Deterministically extracted key-value pairs (if any) |
| requires_ai | bool | True if section contains only prose (no tables/lists/code) |

### GovernanceConfig

Pydantic model for `governance.yaml` output.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| testing.min_coverage | int | 0 | Minimum test coverage percentage |
| testing.tdd_required | bool | False | Whether TDD is mandatory |
| testing.framework | str | "" | Test framework name |
| testing.type_checking | str | "" | Type checking command |
| quality.linting | str | "" | Linting tool/command |
| quality.pr_approvals | int | 1 | Required PR approvals |
| quality.pre_commit_hooks | bool | False | Pre-commit hooks enabled |
| commits.convention | str \| None | None | Commit convention name |
| performance.cli_timeout_seconds | float | 2.0 | Max CLI operation time |
| performance.dashboard_max_wps | int | 100 | Max WPs for dashboard |
| branch_strategy.main_branch | str | "main" | Primary branch name |
| branch_strategy.dev_branch | str \| None | None | Development branch name |
| branch_strategy.rules | list[str] | [] | Branch rules |
| enforcement | dict[str, str] | {} | Rule ID → severity overrides |

### AgentsConfig

Pydantic model for `agents.yaml` output.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| profiles | list[AgentProfile] | [] | Agent profile definitions |
| selection.strategy | str | "preferred" | Selection strategy |
| selection.preferred_implementer | str \| None | None | Preferred impl agent |
| selection.preferred_reviewer | str \| None | None | Preferred review agent |

### AgentProfile

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| agent_key | str | (required) | Agent identifier |
| role | str | "implementer" | Agent role |
| preferred_model | str \| None | None | Model preference |
| capabilities | list[str] | [] | Capability declarations |

### DirectivesConfig

Pydantic model for `directives.yaml` output.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| directives | list[Directive] | [] | Extracted directives |

### Directive

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| id | str | (required) | Directive ID (e.g., "DIR-001") |
| title | str | (required) | Directive title |
| description | str | "" | Full description |
| severity | str | "warn" | Default severity |
| applies_to | list[str] | [] | Lifecycle hooks |

### ExtractionMetadata

Pydantic model for `metadata.yaml` output.

| Field | Type | Description |
|-------|------|-------------|
| schema_version | str | Schema version (e.g., "1.0.0") |
| extracted_at | str | ISO 8601 timestamp |
| constitution_hash | str | SHA-256 hash of constitution content |
| source_path | str | Path to constitution.md |
| extraction_mode | str | "deterministic", "hybrid", or "ai_only" |
| sections_parsed.structured | int | Count of deterministically parsed sections |
| sections_parsed.ai_assisted | int | Count of AI-parsed sections |
| sections_parsed.skipped | int | Count of unparseable sections |

## State Transitions

```
Constitution.md written/edited
    ↓
ConstitutionParser.parse()
    ↓
[ConstitutionSection, ...]  (section tree)
    ↓
Extractor.extract()
    ↓ (deterministic sections)         ↓ (prose sections, if AI available)
GovernanceConfig                    AI prompt → parse response
DirectivesConfig                        ↓
AgentsConfig                       Merge into configs
    ↓
Schema validation (Pydantic)
    ↓
YAML emission → .kittify/constitution/*.yaml
    ↓
ExtractionMetadata written
```

## Relationships

```
ConstitutionParser 1──* ConstitutionSection
    │
    ↓ (extraction pipeline)
    │
Extractor 1──1 GovernanceConfig
Extractor 1──1 AgentsConfig  
Extractor 1──1 DirectivesConfig
Extractor 1──1 ExtractionMetadata
    │
    ↓ (consumers)
    │
Feature 044 (Governance) reads GovernanceConfig + DirectivesConfig
Feature 046 (Routing) reads AgentsConfig
Dashboard reads constitution.md (rendered markdown)
```
