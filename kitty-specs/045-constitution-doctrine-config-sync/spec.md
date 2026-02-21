# Feature Specification: Constitution Parser and Structured Config

**Feature Branch**: `045-constitution-parser-and-structured-config`
**Created**: 2026-02-15
**Status**: Draft
**Input**: Parse the constitution narrative markdown into structured YAML config files within a `.kittify/constitution/` directory. Extraction is agentic (AI-driven) and triggered both by post-save hooks on CLI writes and via explicit `spec-kitty constitution sync` command.

## Overview

The constitution (`.kittify/memory/constitution.md`) is currently a human-readable narrative document with no machine-parseable representation. The governance system (Feature 044) needs structured rules (testing thresholds, quality gates, agent profiles) extracted from the constitution to evaluate at lifecycle hooks. The agent context system needs structured config to inject governance rules into agent prompts.

This feature introduces:

1. **Constitution directory** — `.kittify/constitution/` replaces `.kittify/memory/constitution.md` as the consolidated location for all repository-level governance and guidance. Contains both the narrative markdown and extracted structured YAML files.
2. **Agentic extraction** — an AI-driven parser that reads `constitution.md` and generates structured YAML files (`governance.yaml`, `agents.yaml`, etc.) representing the machine-parseable rules.
3. **Dual trigger** — extraction runs automatically after any CLI write to the constitution (post-save hook) and manually via `spec-kitty constitution sync` for manual edits.
4. **Governance integration** — the extracted YAML files are the input to Feature 044's governance hooks, replacing raw markdown parsing at runtime.

### Directory Structure

```
.kittify/constitution/
├── constitution.md          # Human-readable narrative (moved from .kittify/memory/)
├── governance.yaml          # Extracted: testing standards, quality gates, commit conventions
├── agents.yaml              # Extracted: agent profiles, behavioral patterns, role assignments
├── directives.yaml          # Extracted: numbered cross-cutting constraints
└── metadata.yaml            # Extraction metadata: version, timestamp, constitution hash
```

### Design Decisions

- **Agentic extraction over rule-based parsing**: Constitution is natural language — an AI parser handles ambiguity, non-standard headings, and qualitative statements better than regex/heuristic parsing.
- **YAML output format**: Structured, well-known, already used throughout spec-kitty for config. Governance hooks can load YAML directly without custom parsers.
- **Constitution directory replaces memory/constitution.md**: Consolidates all repository-level governance in one location. Migration moves the file.
- **No drift by design**: Constitution is generally written through the CLI. Post-save hooks extract immediately. Manual edits covered by explicit sync command. Git server workflows can trigger sync on markdown changes.
- **One-way flow**: Constitution.md is always the source of truth. YAML files are derived — never edited directly. Re-sync overwrites YAML without merge.

**2.x baseline**: `.kittify/memory/constitution.md` (narrative document, served via dashboard API), `.kittify/config.yaml` (minimal agent/vcs config), `src/specify_cli/orchestrator/agent_config.py` (reads agents from config.yaml, not constitution).

## User Scenarios & Testing

### User Story 1 — Extract Structured Config from Constitution (Priority: P1)

As a project owner, after creating or updating my constitution via the CLI, the system extracts structured YAML files from the narrative markdown, so that the governance system can evaluate machine-parseable rules at lifecycle hooks.

**Why this priority**: Extraction is the core mechanism. Without it, governance rules remain locked in prose and cannot be evaluated programmatically.

**Independent Test**: Create a constitution with "Testing: minimum 80% coverage, TDD required" and "Commit convention: conventional commits". Run `spec-kitty constitution sync`. Verify `governance.yaml` contains `testing: { min_coverage: 80, tdd_required: true }` and `commits: { convention: conventional }`.

#### Functional Requirements

- **FR-1.1**: The system SHALL provide a `spec-kitty constitution sync` CLI command that triggers agentic extraction from `constitution.md` to structured YAML files.
- **FR-1.2**: The extraction process SHALL use an AI agent to parse the constitution markdown and generate structured YAML output.
- **FR-1.3**: The extraction SHALL produce at minimum: `governance.yaml` (testing, quality, commits, branch strategy), `agents.yaml` (agent profiles, roles, patterns), and `metadata.yaml` (extraction timestamp, constitution file hash, schema version).
- **FR-1.4**: The extraction SHALL produce `directives.yaml` when the constitution contains numbered directives or cross-cutting constraints.
- **FR-1.5**: Each YAML output file SHALL include a header comment: `# Auto-generated from constitution.md — do not edit directly. Run 'spec-kitty constitution sync' to regenerate.`
- **FR-1.6**: The extraction SHALL be idempotent — running sync twice on the same constitution produces identical YAML output.
- **FR-1.7**: The `metadata.yaml` SHALL include a hash of `constitution.md` content, enabling the governance system to detect whether extraction is stale.

### User Story 2 — Post-Save Hook on CLI Writes (Priority: P1)

As a project owner, when I complete the `/spec-kitty.constitution` or `/spec-kitty.bootstrap` flow, the structured config is automatically extracted without requiring a separate sync step.

**Why this priority**: Automatic extraction on CLI writes eliminates the most common source of drift — forgetting to sync after updating the constitution.

**Independent Test**: Run `/spec-kitty.constitution` and complete the interview. Verify that YAML files in `.kittify/constitution/` are updated without manually running sync. Verify the extraction timestamp in `metadata.yaml` matches the write time.

#### Functional Requirements

- **FR-2.1**: After any spec-kitty CLI command writes to `constitution.md`, the system SHALL automatically trigger extraction.
- **FR-2.2**: The post-save hook SHALL run synchronously after the CLI write completes. Deterministic extraction completes in under 500ms.
- **FR-2.3**: If extraction fails (AI agent unavailable, parse error), the system SHALL log a warning and leave the previous YAML files intact.
- **FR-2.4**: The post-save hook SHALL update `metadata.yaml` with the new extraction timestamp and constitution hash.
- **FR-2.5**: The `/spec-kitty.constitution` and `/spec-kitty.bootstrap` commands SHALL both trigger the post-save extraction hook.

### User Story 3 — Constitution Directory Migration (Priority: P1)

As an existing spec-kitty user upgrading to this version, I want my constitution to be migrated from `.kittify/memory/constitution.md` to `.kittify/constitution/constitution.md` with initial extraction, so that I can use the new governance features without manual setup.

**Why this priority**: Migration is essential for adoption. Existing projects must upgrade seamlessly.

**Independent Test**: Create a project with constitution at `.kittify/memory/constitution.md`. Run `spec-kitty upgrade`. Verify the file is moved to `.kittify/constitution/constitution.md`, initial YAML extraction runs, and `.kittify/memory/` is cleaned up (or symlinked for backward compat).

#### Functional Requirements

- **FR-3.1**: The upgrade migration SHALL move `constitution.md` from `.kittify/memory/` to `.kittify/constitution/`.
- **FR-3.2**: The migration SHALL create the `.kittify/constitution/` directory if it does not exist.
- **FR-3.3**: The migration SHALL trigger initial agentic extraction to populate YAML files.
- **FR-3.4**: If the AI agent is unavailable during migration, the migration SHALL still move the file and log a warning to run `spec-kitty constitution sync` manually.
- **FR-3.5**: The migration SHALL update any internal references to the old constitution path (dashboard API, worktree symlinks).
- **FR-3.6**: The dashboard SHALL serve the constitution from the new path (`/api/constitution` endpoint updated).

### User Story 4 — Governance System Integration (Priority: P2)

As the governance system (Feature 044), when evaluating rules at lifecycle hooks, I want to load structured YAML config from `.kittify/constitution/` instead of parsing raw markdown, so that rule evaluation is fast and deterministic.

**Why this priority**: This connects the extraction output to its primary consumer. Without it, extracted config has no purpose.

**Independent Test**: Configure governance rules. Trigger a lifecycle hook. Verify the governance system loads `governance.yaml` (not `constitution.md` directly) and evaluates rules from the structured data.

#### Functional Requirements

- **FR-4.1**: The governance system SHALL load rules from `.kittify/constitution/governance.yaml` as its primary data source for constitution-derived rules.
- **FR-4.2**: The governance system SHALL check `metadata.yaml` hash against current `constitution.md` hash to detect stale extraction, logging a warning if mismatched.
- **FR-4.3**: Agent profile governance (Feature 044 FR-5.x) SHALL read profiles from `.kittify/constitution/agents.yaml`.
- **FR-4.4**: If YAML files are missing (extraction never ran), the governance system SHALL fall back to a best-effort markdown parse with a warning to run sync.
- **FR-4.5**: YAML loading SHALL complete in under 100ms (no AI agent invocation at hook time — extraction is pre-computed).

### User Story 5 — Manual Edit Detection and Sync Guidance (Priority: P3)

As a project owner who occasionally edits `constitution.md` manually (outside the CLI), I want the system to detect that the structured config is stale and remind me to sync.

**Why this priority**: Manual edits are the edge case — most updates go through the CLI. But when they happen, the system should guide the user.

**Independent Test**: Edit `constitution.md` manually. Run any lifecycle hook. Verify a warning appears: "Constitution changed since last sync. Run `spec-kitty constitution sync` to update structured config."

#### Functional Requirements

- **FR-5.1**: The governance system SHALL compare the constitution.md file hash against the hash in `metadata.yaml` before evaluating rules.
- **FR-5.2**: If hashes differ, the system SHALL log a warning: "Constitution changed since last sync. Run `spec-kitty constitution sync` to update."
- **FR-5.3**: The `spec-kitty constitution status` command SHALL display: last sync time, constitution hash match (synced/stale), and a list of extracted YAML files.
- **FR-5.4**: The stale detection SHALL NOT block governance evaluation — it uses the last extracted YAML and warns.

## Success Criteria

1. **SC-1**: `spec-kitty constitution sync` extracts structured YAML from constitution.md with correct values for testing, quality, commit, and agent profile sections.
2. **SC-2**: Post-save hook triggers extraction automatically after CLI-driven constitution writes.
3. **SC-3**: Migration from `.kittify/memory/constitution.md` to `.kittify/constitution/` completes without data loss.
4. **SC-4**: Governance hooks load structured YAML in under 100ms (no AI agent invocation at hook time).
5. **SC-5**: Stale extraction is detected and warned about, never silently ignored.
6. **SC-6**: Extraction is idempotent — same constitution content produces identical YAML output.

## Scope Boundaries

### In Scope

- Constitution directory structure (`.kittify/constitution/`)
- Agentic extraction from markdown to YAML
- Post-save hook + explicit sync command
- Migration from `.kittify/memory/` path
- Governance system integration (YAML loading)
- Stale detection via content hashing
- Dashboard API path update

### Out of Scope

- Bi-directional sync (YAML → constitution.md) — one-way only
- Git server webhook configuration — noted as possible but not implemented
- Constitution versioning/history — deferred (git handles version history)
- Schema validation of extracted YAML — best-effort extraction, governance system validates at load time
- Custom extraction rules — agentic extraction handles all section types

## Dependencies

- **Feature 044** (Governance + Doctrine Provider) — primary consumer of extracted YAML files; defines the governance rules schema
- **Feature 042** (Bootstrap) — bootstrap constitution phase writes to the new constitution directory path
- **Feature 043** (Telemetry) — extraction events (success/failure/timing) logged to telemetry

## Glossary Alignment

| Term | Definition (per project glossary) |
|------|-----------------------------------|
| **Constitution** | Project-level governance document in `.kittify/constitution/`. Contains both the human-readable narrative and extracted machine-parseable YAML config. |
| **Agentic Extraction** | AI-driven process that parses constitution markdown and generates structured YAML files. Triggered by CLI post-save hooks or explicit sync command. |
| **Structured Config** | Machine-parseable YAML files derived from the constitution narrative. Used by governance hooks for fast rule evaluation. |
| **Stale Extraction** | State where constitution.md has been modified since the last extraction, detectable via content hash comparison. |
