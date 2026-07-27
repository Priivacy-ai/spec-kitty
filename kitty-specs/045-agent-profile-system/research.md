# Research: Agent Profile System

*Phase 0 output for feature 045-agent-profile-system*

## Decision Log

### D1: Doctrine Packaging Model

**Decision**: Separate PyPI package with own `pyproject.toml`
**Rationale**: Domain separation — doctrine concepts (profiles, directives, paradigms, tactics) are a governance domain model reusable beyond the CLI. Independent versioning allows doctrine to evolve on its own cadence.
**Alternatives considered**:
- Single wheel with two top-level packages — rejected: conflates distribution lifecycle
- Namespace package (`spec_kitty.doctrine`) — rejected: import paths would change for all existing code

### D2: Init Tool Configuration Mechanism

**Decision**: Generate tool-specific context fragment (stateless)
**Rationale**: Spec-kitty supports parallel agent execution. A persistent session file (e.g., `active-profile.yaml`) would create conflicts when multiple agents run simultaneously. Context fragments written to tool-specific directories (`.claude/commands/`, `.codex/prompts/`) are isolated per-tool and parallelism-safe.
**Alternatives considered**:
- Session file (`.kittify/active-profile.yaml`) — rejected: conflicts with parallel execution
- Both fragment + session file — rejected: unnecessary complexity
- Stdout text for manual paste — rejected: poor UX

### D3: Inheritance Merge Strategy

**Decision**: Shallow merge within sections
**Rationale**: Child keys override parent keys one level deep within each section. Parent keys absent from child are preserved. This provides the right balance: a child can override `languages: [python]` without losing the parent's `frameworks: [django]` within the same `specialization-context` section.
**Alternatives considered**:
- Section-level replace — rejected: too aggressive, forces child to redeclare everything in any section it touches
- Deep recursive merge — rejected: complex semantics for nested dicts/lists, hard to reason about
- Per-section configurable — rejected: unnecessary complexity, inconsistent behavior

### D4: Directive Content Source

**Decision**: Follow established `directive.schema.yaml` format, use `doctrine_ref/directives/` as content reference
**Rationale**: The `test-first.directive.yaml` already in `src/doctrine/directives/` establishes the canonical format. The 18 remaining directives follow the same schema (schema_version, id, title, intent, tactic_refs, enforcement). Content is adapted from doctrine_ref reference materials.
**Alternatives considered**:
- Verbatim copy from doctrine_ref — rejected: doctrine_ref uses a different format (markdown, not YAML)
- Subset extraction — rejected: the schema already defines a minimal format

### D5: WP Dependency Structure

**Decision**: WP05 as root, 6 WPs parallelizable in Wave 1, WP11 after WP10, WP12 last
**Rationale**: Maximum parallelization reduces implementation time. WP12 (init CLI) depends on both WP11 (interview creates profiles) and WP15 (init needs resolved profiles). WP11 depends on WP10 (interview references directive list).
**Alternatives considered**:
- Fully sequential (9 WPs) — rejected: 2.5x longer than necessary
- WP12 in Wave 1 — rejected: init without inheritance resolution would produce incomplete governance context

### D6: YAML Key Rename Strategy

**Decision**: Migration renames `agents` to `tools` with backward-compatible fallback in `load_tool_config()`
**Rationale**: The `agents` key stores tool identifiers (claude, codex, opencode) not agent identities. Per the canonical glossary, this should be `tools`. Backward-compat fallback ensures existing configs work during the transition period.
**Alternatives considered**:
- No rename (keep `agents` key) — rejected: perpetuates glossary confusion
- Hard rename without fallback — rejected: breaks existing projects that haven't run migration
