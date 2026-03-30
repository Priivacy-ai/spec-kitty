# Research: Canonical Context Architecture Cleanup

**Feature**: 057-canonical-context-architecture-cleanup
**Date**: 2026-03-27

## Overview

Research phase for the big-bang architectural cleanup. All major design decisions were resolved during planning interrogation. This document captures the rationale, alternatives considered, and codebase findings that informed those decisions.

---

## R1: Context Token Format

**Decision**: Opaque ULID-based tokens persisted in `.kittify/runtime/contexts/`.

**Rationale**: Semantic tokens (e.g., `ctx-057-WP03`) invite tools and agents to parse meaning from the token string, which recreates the context-rediscovery problem. Opaque tokens force all consumers to look up the bound context, ensuring identity is always resolved from the persisted object.

**Alternatives considered**:
- **(A) File paths**: Too coupled to filesystem layout; brittle for agents and runtime wrappers that may not share the same working directory.
- **(B) Semantic tokens** (e.g., `ctx-057-WP03`): Invites parsing meaning back out, defeats purpose of eliminating heuristic resolution.
- **(C) Inline JSON**: Too verbose for slash-command ecosystems; error-prone for copy-paste between agent invocations.

**Codebase finding**: Current `WorkspaceContext` in `src/specify_cli/workspace_context.py` already uses per-WP JSON files in `.kittify/workspaces/`. The new context tokens follow the same pattern but with opaque filenames and richer content.

---

## R2: Identity Lifecycle and wp_code Separation

**Decision**: Separate `work_package_id` (immutable ULID) from `wp_code` (display alias like "WP03").

**Rationale**: `WP03` is currently overloaded as both identity and presentation. Reordering, splitting, or regenerating display codes would break references if `WP03` were the identity. The immutable internal ID allows the display alias to change without breaking context tokens, event log references, or dependency graphs.

**Alternatives considered**:
- **Use WP03 as identity**: Simpler but fragile — any WP reordering or splitting would invalidate all references.
- **Use sequential integers**: Not collision-safe across concurrent task-finalization sessions.

**Codebase finding**: Current codebase uses `wp_id` field in `StatusEvent` (e.g., "WP01", "WP03"). The migration must map these to new ULIDs while preserving the display alias.

---

## R3: Tracked vs Derived Boundary

**Decision**: Track only human-authored artifacts + event log. All projections (status.json, board summaries, dossier snapshots, prompt surfaces, cached manifests) go to `.kittify/derived/` (gitignored). Runtime ephemera (context tokens, locks, merge state) go to `.kittify/runtime/` (gitignored).

**Rationale**: Generated state in merge paths causes merge noise and fragile reviews. Separating derived from runtime prevents confusion between "useful cache" and "pure scratch state."

**Alternatives considered**:
- **(A) Gitignore all derived + regenerate on clone**: Clean but requires regeneration step after every clone. Rejected as too disruptive.
- **(B) Track derived artifacts**: Current approach. Causes merge conflicts on status.json, dossier snapshots, and generated prompts. Rejected as the root cause of the problem.

**Codebase finding**: Current `.gitignore` already ignores `.kittify/events/`, `.kittify/workspaces/`, `.kittify/dossiers/`, `.kittify/runtime/`. But `kitty-specs/*/status.json` and `kitty-specs/*/status.events.jsonl` are currently tracked in the feature directory. The event log stays tracked (it's the canonical authority). `status.json` must be moved to `.kittify/derived/` and gitignored.

**Important constraint**: `owned_files` manifests are NOT derived — they are tracked as part of the authoritative execution contract (static WP frontmatter).

---

## R4: Merge Workspace Location

**Decision**: `.kittify/runtime/merge/<mission_id>/workspace/` using real git worktree mechanics, not under `.worktrees/`.

**Rationale**: Merge is not a work package. Merge workspaces should not be discovered by WP/worktree heuristics, should be clearly ephemeral, and should not pollute the operator's mental model.

**Alternatives considered**:
- **(A) Under `.worktrees/`**: Consistent with WP worktree convention but conflates merge machinery with implementation workspaces. Would be discovered by feature detection heuristics.
- **(B) Pure temp directory**: No persistence, can't resume interrupted merges.

**Codebase finding**: Current `MergeState` lives at `.kittify/merge-state.json` (single file, not scoped per mission). Current merge in `executor.py` operates on the main repo's checked-out branch directly — no dedicated workspace.

---

## R5: Thin Shim Entrypoint Design

**Decision**: `spec-kitty agent shim <command> --agent <name> --raw-args "$ARGUMENTS"` handles resolve-if-missing → persist → execute internally.

**Rationale**: Putting context resolution inside the CLI (not in the shim) preserves the thin-shim principle. Requiring a preexisting token creates hidden session state and brittle failures. A visible two-step in markdown recreates agent-specific drift.

**Alternatives considered**:
- **Require preexisting token**: Would need a separate "resolve" step before every slash command, adding friction and failure modes.
- **Two-step in shim markdown**: Recreates the exact problem of agent-specific workflow logic in generated files.
- **Pure one-liner with no framing**: Insufficient for LLM agents that need minimal context about what they're executing.

**Codebase finding**: Current command templates in `src/specify_cli/missions/software-dev/command-templates/` are ~100-500 lines each and contain full workflow logic, recovery instructions, argument parsing, and conditional branching. The 12 agent directories each get copies of these files via migrations, leading to drift when templates are updated.

---

## R6: Schema Version vs Heuristic Detection

**Decision**: Schema-version integer in `metadata.yaml`, not heuristic directory/file detection.

**Rationale**: Heuristic detection (`VersionDetector` in `detector.py`) checks for directory existence, gitignore patterns, and file presence to guess the version. This is fragile and has caused version deadlocks. A simple integer version with a capabilities list is deterministic and forward-compatible.

**Codebase finding**: Current `VersionDetector` in `src/specify_cli/upgrade/detector.py` uses ~15 heuristic checks (e.g., "has `.specify/` directory" → v0.1.0, "has `.worktrees/`" → v0.11.0+). The 53 existing migrations use `should_apply()` methods that re-check heuristics. The new model: `schema_version >= N` is the only gate.

---

## R7: Aggressive Deletion Strategy

**Decision**: Delete all superseded code as part of this feature. No preservation of legacy runtime paths.

**Rationale**: Keeping dead code creates confusion about what's authoritative, increases maintenance burden, and invites re-introduction of old patterns. The one-shot migration handles legacy-to-new conversion; after that, old code has no runtime purpose.

**Estimated deletion**: ~2,500+ lines of Python across ~10 deleted files, plus ~56 deleted markdown command templates (14 per mission x 4 missions), plus removal of legacy code paths from ~20 surviving files.

**Risk mitigation**: The migration module preserves the ability to read legacy formats (frontmatter lane fields, heuristic version markers, old merge state location) but only as migration inputs, never as runtime behavior.
