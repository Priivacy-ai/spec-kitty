# Research: Constitution Parser and Structured Config

**Feature**: 045-constitution-doctrine-config-sync
**Date**: 2026-02-15

## Research Questions

### RQ-1: Markdown Parsing Approach for Constitution Sections

**Decision**: Use Python `re` module for heading/section extraction, dedicated parsers for tables and code blocks.

**Rationale**: The constitution follows consistent markdown conventions (## headings, | tables |, ```yaml blocks). A lightweight regex-based parser is sufficient — no need for a full markdown AST library (markdown-it, mistune) which would add dependencies.

**Implementation**:
- Split on `## ` headings to get sections
- Parse markdown tables with regex: `\|.*\|` rows, strip header separator
- Parse YAML code blocks: `` ```yaml ... ``` `` fenced blocks
- Parse numbered lists: `^\d+\.\s+(.*)` for directive-style rules
- Everything else → prose (AI fallback candidate)

**Alternatives considered**:
- **mistune/markdown-it-py**: Full AST parsing. Rejected — adds dependency, overkill for well-structured constitution
- **frontmatter-only**: Only parse YAML frontmatter. Rejected — constitution is prose with embedded structure, not frontmatter-driven

### RQ-2: AI Fallback Integration

**Decision**: Use subprocess call to the configured agent CLI (same pattern as orchestrator).

**Rationale**: The orchestrator already invokes agents via subprocess. Reusing this pattern ensures consistency and leverages existing agent configuration.

**Implementation**:
- Check if an agent is configured (from `.kittify/config.yaml`)
- Build a structured prompt: "Extract the following from this text: [schema fields]. Input: [prose section]. Output: YAML."
- Parse YAML from agent response
- If agent unavailable: skip prose sections, log warning, mark in metadata

**Alternatives considered**:
- **Direct API call**: Would require API key management separate from agent config. Rejected — agents already handle auth.
- **In-process LLM**: Requires model loading. Rejected — too heavy for a CLI tool.

### RQ-3: Content Hashing for Staleness Detection

**Decision**: SHA-256 hash of constitution.md file content (normalized whitespace).

**Rationale**: SHA-256 is fast, collision-resistant, and standard. Normalizing whitespace prevents false positives from trailing newline changes.

**Implementation**:
```python
import hashlib

def hash_constitution(content: str) -> str:
    normalized = content.strip()
    return f"sha256:{hashlib.sha256(normalized.encode()).hexdigest()}"
```

### RQ-4: Existing Constitution Path References

**Finding**: 6 code locations reference `.kittify/memory/constitution.md`:

| File | Line | Reference Type |
|------|------|---------------|
| `src/specify_cli/dashboard/handlers/api.py` | 110 | Path construction |
| `src/specify_cli/missions/software-dev/command-templates/constitution.md` | 22 | Location comment |
| `src/specify_cli/upgrade/migrations/m_0_10_8_fix_memory_structure.py` | 38 | Destination path |
| `src/specify_cli/cli/commands/init.py` | 62 | Comment |
| `src/specify_cli/core/worktree.py` | ~290 | Symlink setup |
| Agent command templates (12 agents) | Various | Path references |

**Migration scope**: All references must be updated to `.kittify/constitution/constitution.md`.

### RQ-5: Existing Constitution Content Analysis

**Finding**: The current constitution contains these extractable sections:

| Section | Extraction Method | Target YAML |
|---------|-------------------|-------------|
| Testing Requirements (90%+ coverage, TDD, pytest, mypy) | Deterministic — keywords + numbers | `governance.yaml → testing` |
| Quality Gates (ruff, PR approvals, pre-commit) | Deterministic — table/list parsing | `governance.yaml → quality` |
| Performance (< 2 seconds CLI, 100+ WPs) | Deterministic — number extraction | `governance.yaml → performance` |
| Branch Strategy (1.x/2.x) | Deterministic — heading + keywords | `governance.yaml → branch_strategy` |
| Architecture decisions (spec-kitty-events) | Prose — AI fallback | Not extracted (qualitative) |
| Amendment process | Prose — AI fallback | Not extracted (qualitative) |

**Conclusion**: ~70% of the current constitution is deterministically extractable. AI fallback needed only for architecture rationale and governance process prose.
