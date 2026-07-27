# Feature Specification: State Model Cleanup Foundations

## Overview

The spec-kitty CLI manages persistent state across three filesystem roots, multiple formats, and varying Git boundaries. The 007 state architecture audit revealed that several repo-local runtime surfaces are not gitignored, the CLI has no machine-readable manifest of its own state surfaces, and there is no diagnostic command that tells a maintainer where state lives and what is safe to commit.

This sprint creates the foundational layer that all later state-model cleanup depends on: a typed state contract, explicit root-path terminology, aligned Git boundaries for unambiguous runtime state, and doctor checks that surface the classification to operators.

## Problem Statement

1. **No canonical state manifest.** State surfaces are documented only in prose (audit notes, CLAUDE.md). There is no single code-owned source of truth that maps every durable state path to its owner, authority class, and Git policy.

2. **Git boundary gaps.** The audit identifies seven repo-local runtime surfaces (`.kittify/runtime/`, `.kittify/merge-state.json`, `.kittify/events/`, `.kittify/dossiers/`, and three constitution outputs) that are *not* gitignored. They can be accidentally committed, polluting project history with machine-local residue.

3. **Inconsistent runtime protection.** `GitignoreManager.RUNTIME_PROTECTED_ENTRIES` only covers two entries (`.dashboard`, `missions/__pycache__/`). The repo `.gitignore` covers more, but neither matches the full set of runtime surfaces defined by 2.x code.

4. **No diagnostic visibility.** There is no CLI command that shows a maintainer the expected state roots, their classifications, or whether any unsafe runtime files are present in the working tree. The existing `spec-kitty agent status doctor` is feature-scoped (status events/drift), not state-model-scoped.

## Actors

- **CLI maintainer**: Develops and debugs spec-kitty. Needs to know where state lives, what is safe to commit, and whether Git policy matches the intended architecture.
- **Project user**: Uses spec-kitty in their repo. Needs runtime state to stay out of Git without manual intervention.
- **CI pipeline**: Runs spec-kitty commands. Must not encounter unexpected untracked files from runtime state.

## User Scenarios & Testing

### Scenario 1: Maintainer inspects state layout
A maintainer runs `spec-kitty doctor state-roots` in a project repo. The CLI prints a table of all three state roots with their expected surfaces, classified by authority and Git policy. Surfaces that exist on disk are marked present; those that don't are marked absent. No error is raised for absent surfaces (they are lazily created).

### Scenario 2: Maintainer detects unsafe runtime files
A maintainer runs `spec-kitty doctor state-roots` after a `spec-kitty next` session that created `.kittify/runtime/` files. The doctor output flags these as "runtime, should be ignored" and reports whether they are currently covered by `.gitignore`. If not covered, the output warns that they could be accidentally committed.

### Scenario 3: User initializes a new project
A user runs `spec-kitty init`. The `GitignoreManager` now adds all runtime-classified repo-local surfaces to `.gitignore`, not just `.dashboard` and `__pycache__`. After init, `git status` shows no untracked `.kittify/runtime/` or `.kittify/events/` files.

### Scenario 4: Upgrade aligns existing project
A user upgrades spec-kitty. A migration adds the missing runtime gitignore entries. After upgrade, previously-unprotected runtime directories are now ignored.

### Scenario 5: Developer imports state contract in tests
A test imports `StateSurface` entries from `state_contract.py` and asserts that every surface classified as `local_runtime` has a corresponding `.gitignore` entry. This prevents future drift between the contract and the ignore policy.

## Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | Create `src/specify_cli/state_contract.py` containing a typed registry of all durable CLI state surfaces with fields: path pattern, owning module, format, authority class, Git class, creation trigger, and deprecation status. | proposed |
| FR-002 | Define enums for `StateRoot` (project, global_runtime, global_sync), `AuthorityClass` (authoritative, derived, compatibility, local_runtime, secret, git_internal, deprecated), `GitClass` (tracked, ignored, inside_repo_not_ignored, git_internal, outside_repo), and `StateFormat` (json, yaml, toml, jsonl, sqlite, markdown, symlink, text, lockfile, directory). | proposed |
| FR-003 | Define a frozen `StateSurface` dataclass with fields: `name`, `path_pattern`, `root`, `format`, `authority`, `git_class`, `owner_module`, `creation_trigger`, `deprecated`, and `notes`. | proposed |
| FR-004 | Populate the registry with all surfaces from audit sections A–G, using the authority and Git classifications from the audit. Constitution surfaces that have deferred Git policy should use `git_class=GitClass.INSIDE_REPO_NOT_IGNORED` with a note indicating the decision is deferred. | proposed |
| FR-005 | Add helper functions: `get_surfaces_by_root(root)`, `get_surfaces_by_git_class(git_class)`, `get_runtime_gitignore_entries()` (returns path patterns for all project-root surfaces with `git_class=IGNORED` or `authority=LOCAL_RUNTIME`). | proposed |
| FR-006 | Update `GitignoreManager.RUNTIME_PROTECTED_ENTRIES` to be derived from `state_contract.get_runtime_gitignore_entries()` so the ignore list is always consistent with the contract. | proposed |
| FR-007 | Update the repo `.gitignore` (via migration) to add entries for: `.kittify/runtime/`, `.kittify/merge-state.json`, `.kittify/events/`, `.kittify/dossiers/`. | proposed |
| FR-008 | Create a new CLI command `spec-kitty doctor state-roots` that prints: (a) the three state roots and their resolved paths, (b) a table of all registered surfaces grouped by root, showing authority class, Git class, and on-disk presence, (c) warnings for any repo-local runtime surfaces not covered by `.gitignore`. | proposed |
| FR-009 | The doctor command must support `--json` output for machine consumption. | proposed |
| FR-010 | Add a migration that adds the missing runtime gitignore entries to existing projects during `spec-kitty upgrade`. | proposed |
| FR-011 | The state contract must include a `to_dict()` method on `StateSurface` for JSON serialization. | proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | State contract module has zero runtime dependencies beyond Python stdlib and existing spec-kitty imports. | 0 new dependencies | proposed |
| NFR-002 | `spec-kitty doctor state-roots` completes in under 2 seconds for a project with 20 features. | < 2s wall time | proposed |
| NFR-003 | State contract registry is data-first: no business logic beyond lookup helpers. | Manual review: no side effects in module-level code | proposed |

## Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | Do not change the Git boundary for constitution surfaces (`.kittify/constitution/interview/answers.yaml`, `.kittify/constitution/references.yaml`, `.kittify/constitution/library/**`). Classify them in the contract but defer the ignore/track decision. | active |
| C-002 | Do not remove legacy compatibility state (e.g., `.kittify/active-mission`). Classify it as deprecated in the contract only. | active |
| C-003 | Do not change acceptance to stop reading Activity Log. Out of scope for this sprint. | active |
| C-004 | Do not modify SaaS architecture, tracker providers, or broad runtime design. | active |
| C-005 | The migration must be safe to run on projects that already have some of the gitignore entries (idempotent). | active |
| C-006 | Python 3.11+ required (existing spec-kitty baseline). | active |

## Success Criteria

1. Every durable state surface in the 007 audit has a corresponding entry in `state_contract.py` with one named owner module.
2. No repo-local runtime surface touched by this sprint has an ambiguous Git boundary: it is either explicitly tracked or explicitly ignored.
3. `spec-kitty doctor state-roots` outputs the three roots with resolved paths and flags any runtime files present but not ignored.
4. A test asserts that every `LOCAL_RUNTIME`-classified project surface has a matching gitignore pattern.
5. `GitignoreManager.RUNTIME_PROTECTED_ENTRIES` is derived from the state contract, not a separate hardcoded list.

## Scope Boundaries

### In Scope
- Machine-readable state contract (`state_contract.py`)
- Root-path enums and terminology (project / global_runtime / global_sync)
- `.gitignore` additions for unambiguous runtime state
- `GitignoreManager` alignment with the contract
- Migration for existing projects
- `spec-kitty doctor state-roots` command
- Tests for contract, gitignore alignment, and doctor output

### Out of Scope
- SaaS architecture changes
- Tracker provider implementation
- Major workflow refactors
- Removing legacy compatibility state
- Changing acceptance to stop reading Activity Log
- Broad runtime redesign
- Constitution Git boundary decisions (deferred, classified only)
- Atomic write utilities (later sprint)
- Single `meta.json` writer API (later sprint)
- User-home credential/schema cleanup (later sprint)

## Dependencies & Assumptions

### Dependencies
- The 007 state architecture audit (sections 02, 04, 06) as the authoritative inventory
- Existing `GitignoreManager` in `src/specify_cli/gitignore_manager.py`
- Existing doctor infrastructure in `src/specify_cli/status/doctor.py` and `src/specify_cli/runtime/doctor.py`
- Existing CLI command structure under `src/specify_cli/cli/commands/`

### Assumptions
- The audit inventory is complete for 2.x as of v2.0.9. If surfaces are discovered that the audit missed, they should be added to the contract with a note.
- Constitution surfaces will get their own Git boundary sprint later; this sprint only classifies them.
- The `GitignoreManager` pattern of adding entries via `ensure_entries()` is sufficient; no need for removal logic in this sprint.

## Key Entities

| Entity | Description |
|---|---|
| `StateSurface` | A single durable state path with its classification metadata |
| `StateRoot` | Enum: `PROJECT` (`.kittify/`), `GLOBAL_RUNTIME` (`~/.kittify/`), `GLOBAL_SYNC` (`~/.spec-kitty/`), `FEATURE` (`kitty-specs/<feature>/`), `GIT_INTERNAL` (`.git/spec-kitty/`) |
| `AuthorityClass` | Enum classifying who owns the truth: authoritative, derived, compatibility, local_runtime, secret, git_internal, deprecated |
| `GitClass` | Enum for Git boundary: tracked, ignored, inside_repo_not_ignored, git_internal, outside_repo |
| `StateFormat` | Enum for serialization format |

## Deferred Ambiguities

These surfaces have unclear Git policy and are explicitly deferred to later sprints:

1. **`.kittify/constitution/interview/answers.yaml`** — authored input, currently not ignored. Classified as authoritative. Decision deferred to constitution cleanup sprint.
2. **`.kittify/constitution/references.yaml`** — derived compiler output, currently not ignored. Classified as derived. Decision deferred.
3. **`.kittify/constitution/library/**`** — derived compiler output, currently not ignored. Classified as derived. Decision deferred.
