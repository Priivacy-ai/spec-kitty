# Research: Hybrid Prompt and Shim Agent Surface

**Feature**: 058-hybrid-prompt-and-shim-agent-surface
**Date**: 2026-03-30

## R1: Where Command Templates Come From

**Decision**: Restore `src/specify_cli/missions/software-dev/command-templates/` as the canonical source for prompt-driven commands.

**Rationale**: The existing `generate_agent_assets()` function and 4-tier resolution chain (`overrides → legacy → global runtime → package`) still work. They just need source files to read. Restoring the files in the package source is the minimal fix.

**Alternatives considered**:
- New `src/doctrine/prompts/` directory: Adds a new location. Rejected — the existing `missions/*/command-templates/` path is already wired into `ensure_runtime()`, `generate_agent_assets()`, and the 4-tier resolver.
- Embed prompts in Python code: Would make them hard to edit and review. Rejected.

## R2: Hybrid Init Strategy

**Decision**: Call `generate_agent_assets()` for 9 prompt-driven commands, `generate_all_shims()` for 7 CLI-driven commands.

**Rationale**: `generate_agent_assets()` already handles multi-agent rendering (12 agents × different formats). `generate_all_shims()` already handles thin shim generation. Using both in init is simpler than building a new unified installer.

**Alternatives considered**:
- Single installer that reads a manifest: More elegant but more code. Rejected for pragmatism.
- All shims + separate skill-based prompts: Agents would need to read from two locations. Rejected — `.claude/commands/` is the single surface agents use.

## R3: Source of Prompt Content

**Decision**: Port the current `.claude/commands/` files (with today's fixes applied) as the canonical source, with cleanup to remove dev-repo-specific content.

**Rationale**: These files are battle-tested — agents have been using them successfully in the spec-kitty dev repo. They contain all the fixes from today's session (project root checkout terminology, template path warnings, ownership guidance, --feature hints).

**Cleanup needed**:
- Remove `057-canonical-context-architecture-cleanup` references
- Remove any hardcoded `/Users/robert/` paths
- Ensure `--feature` guidance is present in every prompt
- Verify no `.kittify/missions/` template read instructions remain
