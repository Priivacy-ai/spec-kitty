# Implementation Plan: Constitution Parser and Structured Config

**Branch**: `045-constitution-parser-and-structured-config` | **Date**: 2026-02-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/045-constitution-doctrine-config-sync/spec.md`

## Summary

Parse the constitution narrative markdown (`.kittify/memory/constitution.md`) into structured YAML config files within a new `.kittify/constitution/` directory. Uses a hybrid parser: deterministic extraction for structured sections (markdown tables, YAML blocks, numbered lists) with AI fallback for ambiguous prose. Schemas defined upfront. Migration moves constitution to new path, updates all references. Post-save hook is a synchronous Python function; async extraction delegated to CI.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: ruamel.yaml (YAML output), hashlib (content hashing), re (markdown parsing), typer (CLI), rich (console output)
**Storage**: Filesystem only — YAML files in `.kittify/constitution/`
**Testing**: pytest with 90%+ coverage, mypy --strict, ruff
**Target Platform**: Cross-platform (Linux, macOS, Windows 10+)
**Project Type**: Single (extends existing CLI)
**Performance Goals**: YAML loading < 100ms; deterministic extraction < 500ms; full sync (with AI) < 30s
**Constraints**: Extraction must be idempotent for deterministic sections; AI fallback is best-effort
**Scale/Scope**: Typical constitution is 100-500 lines of markdown

## Architecture Decisions

### AD-1: Hybrid Parsing Strategy

**Decision**: Deterministic parser for structured sections + AI fallback for prose.

**Rationale**: Constitution contains both structured data (tables, code blocks, numbered rules) and qualitative prose. Deterministic parsing guarantees idempotency for structured content. AI handles the long tail of natural language guidance that can't be reliably regex-parsed.

**Implementation**:

- `ConstitutionParser` class with `parse_structured()` (deterministic) and `parse_prose()` (AI-assisted)
- `parse_structured()` extracts: markdown tables → dicts, YAML code blocks → dicts, numbered lists → lists, heading hierarchy → section tree
- `parse_prose()` sends unparsed sections to LLM with a structured output prompt
- Extraction pipeline: parse_structured → identify unstructured gaps → parse_prose → merge → emit YAML

### AD-2: Schema-First YAML Output

**Decision**: Define strict schemas for all output files before parsing implementation.

**Rationale**: Consumers (Feature 044 governance hooks) need a stable contract. Schema-first ensures the parser targets a well-defined output format.

**Schemas**:

```yaml
# governance.yaml
testing:
  min_coverage: 90          # integer, percent
  tdd_required: true        # boolean
  framework: "pytest"       # string
  type_checking: "mypy --strict"  # string
quality:
  linting: "ruff"           # string
  pr_approvals: 1           # integer
  pre_commit_hooks: true    # boolean
commits:
  convention: "conventional"  # string or null
performance:
  cli_timeout_seconds: 2    # number
  dashboard_max_wps: 100    # integer
branch_strategy:
  main_branch: "1.x"
  dev_branch: "2.x"
  rules: []                 # list of branch rules
enforcement: {}             # rule_id → severity overrides (for Feature 044)

# agents.yaml
profiles: []                # list of agent profile objects (for Feature 044/046)
  # - agent_key: "claude"
  #   role: "implementer"
  #   preferred_model: "claude-sonnet-4-20250514"
  #   capabilities: ["python", "testing"]
selection:
  strategy: "preferred"     # from existing config.yaml
  preferred_implementer: null
  preferred_reviewer: null

# directives.yaml
directives: []              # list of directive objects
  # - id: "DIR-001"
  #   title: "TDD Required"
  #   description: "All implementation must follow test-first TDD"
  #   severity: "warn"       # default severity
  #   applies_to: ["pre_implement", "pre_review"]

# metadata.yaml
schema_version: "1.0.0"
extracted_at: "2026-02-15T21:00:00+00:00"  # ISO 8601
constitution_hash: "sha256:abc123..."       # content hash
source_path: ".kittify/constitution/constitution.md"
extraction_mode: "hybrid"   # deterministic | hybrid | ai_only
sections_parsed:
  structured: 5             # count of deterministically parsed sections
  ai_assisted: 2            # count of AI-parsed sections
  skipped: 0                # count of sections that couldn't be parsed
```

### AD-3: Migration Strategy — Move and Update References

**Decision**: Move file from `.kittify/memory/constitution.md` → `.kittify/constitution/constitution.md`, update all internal references, no symlink.

**References to update**:

1. `src/specify_cli/dashboard/handlers/api.py` line 110 — constitution path
2. `src/specify_cli/missions/software-dev/command-templates/constitution.md` line 22 — location comment
3. `src/specify_cli/upgrade/migrations/m_0_10_8_fix_memory_structure.py` — destination path
4. `src/specify_cli/cli/commands/init.py` line 62 — comment
5. `src/specify_cli/core/worktree.py` — symlink setup
6. Agent command templates referencing constitution path

### AD-4: Post-Save Hook — Synchronous Python Function

**Decision**: Synchronous Python function hook after CLI writes. External CI handles async re-extraction on manual edits.

**Implementation**: After any CLI command writes to `constitution.md`, call `extract_constitution(constitution_path)` inline. Fast for deterministic sections (< 500ms). AI fallback may add latency but only triggers for prose sections.

### AD-5: AI Fallback Invocation

**Decision**: CLI-invoked subprocess for AI extraction of prose sections.

**Implementation**: Use the existing agent invocation infrastructure (orchestrator's `AgentInvoker` pattern or direct subprocess call to configured agent CLI). Prompt includes the prose section text and expected YAML schema. Response parsed and merged with deterministic output.

## Constitution Check

*GATE: Validated against constitution.*

| Check | Status | Notes |
|-------|--------|-------|
| Python 3.11+ | ✅ | Existing codebase requirement |
| pytest 90%+ coverage | ✅ | Will write tests first (TDD) |
| mypy --strict | ✅ | Type hints on all functions |
| ruff linting | ✅ | Standard compliance |
| Locality of change | ✅ | New `constitution/` subpackage + migration |
| CLI < 2 seconds | ✅ | YAML loading < 100ms; full sync may exceed for AI sections (acceptable, user-initiated) |

## Project Structure

### Documentation (this feature)

```
kitty-specs/045-constitution-doctrine-config-sync/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (NOT created by plan)
```

### Source Code (repository root)

```
src/specify_cli/
├── constitution/                  # NEW subpackage
│   ├── __init__.py               # Public API exports
│   ├── parser.py                 # ConstitutionParser — hybrid markdown→dict
│   ├── schemas.py                # Pydantic models for YAML output schemas
│   ├── extractor.py              # Extraction pipeline (deterministic + AI)
│   ├── sync.py                   # sync() function — orchestrates parse→emit
│   └── hasher.py                 # Content hashing + staleness detection
├── cli/commands/
│   └── constitution.py           # NEW — `spec-kitty constitution sync|status` CLI
├── dashboard/handlers/
│   └── api.py                    # MODIFIED — update constitution path
├── upgrade/migrations/
│   └── m_0_XX_0_constitution_directory.py  # NEW — migration
└── core/
    └── worktree.py               # MODIFIED — update symlink path

tests/specify_cli/
├── constitution/                  # NEW test subpackage
│   ├── __init__.py
│   ├── test_parser.py            # Parser unit tests
│   ├── test_schemas.py           # Schema validation tests
│   ├── test_extractor.py         # Extraction pipeline tests
│   ├── test_sync.py              # Sync integration tests
│   └── test_hasher.py            # Hashing tests
├── cli/commands/
│   └── test_constitution_cli.py  # CLI command tests
└── upgrade/migrations/
    └── test_constitution_migration.py  # Migration tests
```

**Structure Decision**: New `src/specify_cli/constitution/` subpackage alongside existing `status/`, `telemetry/`, `merge/` subpackages. Follows established codebase patterns.

## Dependency Graph

```
Parser (deterministic markdown→dict)
    ↓
Schemas (Pydantic validation + YAML emission)
    ↓
Extractor (pipeline: parse→validate→emit)
    ↓
Sync (orchestration: hash check→extract→write)
    ↓
CLI Commands (spec-kitty constitution sync|status)
    ↓
Migration (move file, update refs, initial extraction)
    ↓
Integration (dashboard API path update, post-save hook)
```
