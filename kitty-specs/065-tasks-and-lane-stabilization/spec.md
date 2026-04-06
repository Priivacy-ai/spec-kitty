# Tasks And Lane Stabilization

## Overview

Make the planning/tasks control plane trustworthy and executable end to end. After this mission, Spec Kitty can go from task generation to executable work packages without silently mutating artifacts, dropping dependency intent, collapsing valid parallelism, or emitting command guidance that agents immediately fail on.

This is a P0 stabilization mission. The current highest-risk failures happen before implementation starts. If these are not fixed first, downstream review/merge improvements sit on an unreliable substrate.

## Problem Statement

Six confirmed bugs in the planning/tasks pipeline break the contract between task generation and task execution:

1. **Dependency loss during finalization** (#406): `finalize-tasks` re-parses `tasks.md` with a regex that does not match the bullet-list dependency format the `/spec-kitty.tasks` template instructs LLMs to generate, then unconditionally overwrites WP frontmatter `dependencies` fields with its (usually empty) parse result.

2. **Validate-only is not read-only** (#417): `finalize-tasks --validate-only` runs the full frontmatter-rewrite loop before checking the flag, destroying any manually repaired WP state.

3. **Impossible WPs and incomplete lane graphs** (#422): Task generation can emit WPs that own nonexistent files, WPs whose owned-file sets are too narrow to satisfy their own definitions of done, and lane graphs that silently omit WPs defined in `tasks.md`.

4. **Silent parallelism collapse** (#423): The lane computation algorithm unions WPs by dependency edges, write-scope overlap, and surface-keyword heuristics. Broad or imprecise ownership and aggressive surface matching collapse independent WPs into a single lane with no explanation, making parallelism cosmetic in `tasks.md` but absent in the executable lane graph.

5. **Task-state mutation format mismatch** (#438): `mark-status` only recognizes checkbox-style task lines but `/spec-kitty.tasks` can generate pipe-table format in `tasks.md`, causing agents to fail when updating task state.

6. **First-try agent command failure** (#434): Generated command guidance omits the required `--mission` flag, and error messages use inconsistent flag names (`--feature` vs `--mission`), causing agents to fail on every first invocation of `spec-kitty agent context resolve`.

## Actors

| Actor | Description |
|-------|-------------|
| Spec Kitty CLI Runtime | The Python CLI that executes finalization, lane computation, status mutation, and context resolution |
| AI Agent | An external coding agent (Claude, Codex, Gemini, etc.) that follows generated slash-command prompts and CLI guidance to implement work packages |
| Mission Operator | A human developer running Spec Kitty commands to plan, finalize, and coordinate feature work |

## User Scenarios & Acceptance

### Scenario 1: Dependency Preservation Through Finalization

**Given** a feature where the LLM has written WP prompt files with `dependencies: [WP01, WP02]` in YAML frontmatter, matching bullet-list dependency sections in `tasks.md`
**When** the operator runs `spec-kitty agent mission finalize-tasks --mission <slug> --json`
**Then** the finalized WP files retain the declared dependencies. If the parser extracts a non-empty dependency list from `tasks.md` that disagrees with the WP's existing non-empty frontmatter `dependencies`, finalization fails with a diagnostic error naming the WP, the parsed values, and the existing values — it does not silently merge, supplement, or replace. If the parser extracts an empty list and frontmatter has a non-empty list, the existing value is preserved. The JSON output accurately reports which WPs were modified and which were unchanged.

### Scenario 2: Validate-Only Is Non-Mutating

**Given** a feature with WP files that have been manually patched (e.g., dependency restoration after a previous finalization)
**When** the operator runs `spec-kitty agent mission finalize-tasks --mission <slug> --validate-only --json`
**Then** every file on disk is byte-identical before and after the command. The JSON output reports validation results (pass/fail, which WPs would be modified) without writing any changes.

### Scenario 3: Lane Graph Completeness

**Given** a finalized feature with N WPs defined in `tasks.md` and corresponding `tasks/WP*.md` files
**When** lane computation runs (during finalization or explicitly)
**Then** every executable (non-planning-artifact) WP appears in exactly one lane in `lanes.json`. WPs with `execution_mode: planning_artifact` are intentionally excluded from lane assignment but listed in a diagnostic summary so operators can verify the exclusion is correct. If an executable WP cannot be assigned (e.g., missing ownership manifest), the command fails with a diagnostic error naming the problematic WP, rather than silently omitting it.

### Scenario 4: Parallelism Preserved When Ownership Is Disjoint

**Given** a feature where WP01 owns `src/a/**` and WP02 owns `src/b/**`, with no dependency between them
**When** lane computation runs
**Then** WP01 and WP02 are assigned to different parallel lanes. If they are collapsed into one lane despite disjoint ownership, the output includes an explanation of which rule caused the collapse (e.g., shared surface heuristic).

### Scenario 5: Lane Collapse Explanation

**Given** a feature where the lane computation algorithm collapses WPs that the dependency graph declares as independent
**When** the operator views the lane computation output
**Then** the output includes a collapse report: which WPs were merged, which rule triggered the merge (dependency, write-scope overlap, or surface heuristic), and which specific files or surfaces caused the overlap.

### Scenario 6: Task-State Update on Pipe-Table Format

**Given** a feature whose `tasks.md` uses pipe-table rows for task tracking (e.g., `| T001 | description | WP01 | [P] |`)
**When** the operator or agent runs `spec-kitty agent tasks mark-status T001 --status done`
**Then** the command finds and updates the task's status in the pipe-table row. This is required for backward compatibility with existing generated artifacts. Future task generation may additionally be standardized to a single format, but `mark-status` must support both checkbox and pipe-table formats.

### Scenario 7: Agent Command Guidance Includes Required Context

**Given** an AI agent following the generated `/spec-kitty.tasks` slash-command prompt in a multi-mission repository
**When** the agent reaches any step that invokes a `spec-kitty agent` subcommand requiring mission context (e.g., `context resolve`, `check-prerequisites`, `finalize-tasks`, `mark-status`)
**Then** the generated guidance explicitly includes `--mission <slug>` in every example command. The agent succeeds on the first try without needing to parse an error message for available features.

### Scenario 8: Consistent Flag Naming in Error Messages

**Given** an agent that omits the mission flag from any `spec-kitty agent` command
**When** the error message is displayed
**Then** the error message uses the same flag name as the command's actual CLI parameter (`--mission`), not a different name like `--feature`. The error message includes the exact command syntax needed to succeed.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The `finalize-tasks` dependency parser recognizes both inline format (`Depends on: WP01, WP02`) and bullet-list format (`### Dependencies\n- WP01\n- WP02`) when extracting dependencies from `tasks.md`. | Proposed |
| FR-002 | When the dependency parser extracts an empty dependency list for a WP but the WP's frontmatter already contains a non-empty `dependencies` field, the existing value is preserved. | Proposed |
| FR-002a | When the dependency parser extracts a non-empty dependency list that disagrees with an existing non-empty `dependencies` field in WP frontmatter, finalization fails with a diagnostic error naming the WP, the parsed values, and the existing values. No silent merge, supplement, or replacement occurs. | Proposed |
| FR-003 | The `finalize-tasks` JSON output accurately reports which WPs had their frontmatter modified and which were unchanged. | Proposed |
| FR-004 | When `--validate-only` is passed to `finalize-tasks`, no files on disk are written, moved, or deleted. The flag gates all mutation steps, not just the final commit. | Proposed |
| FR-005 | `--validate-only` output reports what mutations would occur without executing them: which WPs would have dependencies updated, which would have other frontmatter fields changed. | Proposed |
| FR-006 | Lane computation produces a lane assignment for every executable (non-planning-artifact) WP in the finalized task set. WPs with `execution_mode: planning_artifact` are intentionally excluded but listed in a diagnostic summary. No executable WP is silently omitted from `lanes.json`. | Proposed |
| FR-007 | If an executable WP cannot be assigned to a lane (missing ownership manifest, unresolvable conflict), lane computation fails with a diagnostic error naming the specific WP and the reason. | Proposed |
| FR-008 | Lane computation emits a collapse report when WPs that are independent in the dependency graph are merged into the same lane. The report names the merging rule and the specific files, globs, or surfaces that triggered the merge. | Proposed |
| FR-009 | Surface-heuristic lane merging (Rule 3) is refined so that broad keyword matches (e.g., "sidebar" matching "app-shell") do not collapse WPs with disjoint owned files. | Proposed |
| FR-010 | `mark-status` supports both checkbox-style (`- [ ] T001`) and pipe-table (`| T001 | ... | [P] |`) task row formats. Checkbox is the canonical emitted format; pipe-table is a backward-compatible input/mutation format for existing artifacts. | Proposed |
| FR-010a | New `tasks.md` generation (via `/spec-kitty.tasks`) emits checkbox format exclusively. Existing pipe-table `tasks.md` files remain editable by `mark-status` without migration. | Proposed |
| FR-010b | No user-facing format-selection feature is added. No mutation command rewrites existing pipe-table files to checkbox format. | Proposed |
| FR-011 | All generated slash-command prompts and command examples across the tasks/action surface — including `context resolve`, `check-prerequisites`, `finalize-tasks`, `mark-status`, and any other `spec-kitty agent` subcommand that requires mission context — include the `--mission <slug>` parameter explicitly. | Proposed |
| FR-012 | Error messages for missing mission context use the same flag name as the CLI parameter (`--mission`), not alternative names like `--feature`. | Proposed |
| FR-013 | The `require_explicit_feature()` error message includes a concrete example using the first available mission slug from `kitty-specs/`, formatted as a complete copy-pasteable command. | Proposed |
| FR-014 | Ownership manifest validation warns when a WP's `owned_files` globs match zero files in the current repository. | Proposed |
| FR-015 | The default ownership fallback (`src/**`) is either narrowed or emits a warning when applied, so operators know that a WP's file scope is synthetic. | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold |
|----|-------------|-----------|
| NFR-001 | Test coverage for modified code | 90%+ line coverage on all modified finalization, lane computation, status mutation, and context resolution code |
| NFR-002 | Type checking | `mypy --strict` produces zero errors on all changed files |
| NFR-003 | No regressions in existing features | All features with existing `status.events.jsonl`, `lanes.json`, and `tasks.md` continue to work identically |
| NFR-004 | Finalization performance | `finalize-tasks` completes in under 5 seconds for features with up to 20 WPs |
| NFR-005 | Error message quality | Every failure-path error message names the affected entity, the root cause, and the corrective action |

## Constraints

| ID | Constraint |
|----|------------|
| C-001 | This mission does not include rejection/fix-loop improvements or review UX changes. Specifically excludes issues #430, #432, #433, #439, #440, #441, #443, #444, #442, #241. |
| C-002 | Historical `kitty-specs/*` records are preserved unchanged. Fixes apply to runtime code, templates, and active generation surfaces only. |
| C-003 | The `set_scalar()` / `FrontmatterManager` API contract must be respected. If `set_scalar()` cannot handle list values, use `FrontmatterManager.update_field()` or equivalent. |
| C-004 | Both `agent mission finalize-tasks` and `agent tasks finalize-tasks` entry points must exhibit identical behavior after fixes. |
| C-005 | Lane computation changes must not break existing features that already have valid `lanes.json` files and are mid-implementation. |

## Scope Boundary

### In Scope

- Dependency parsing and frontmatter preservation in `finalize-tasks` (both entry points)
- `--validate-only` non-mutation guarantee
- Lane graph completeness (every executable WP in lanes.json, planning-artifact WPs diagnostically surfaced)
- Lane collapse explanation reporting
- Surface-heuristic refinement for lane computation
- `mark-status` backward-compatible pipe-table and checkbox format support
- Generated command guidance for `--mission` flag across the full tasks/action command surface
- Error message flag-name consistency
- Ownership validation warnings
- Regression tests for all of the above

### Out of Scope

- Review loop mechanics (#430, #432, #433)
- Review UX (#439, #440, #441, #443, #444)
- Acceptance pipeline (#442)
- SaaS dashboard (#241)
- Lane computation algorithm redesign (only targeted refinements to collapse rules)
- New lane computation strategies beyond the existing union-find approach

## Key Entities

| Entity | Description |
|--------|-------------|
| WP Frontmatter | YAML metadata in WP prompt files: dependencies, owned_files, execution_mode, etc. |
| tasks.md | Human/LLM-authored task breakdown with dependency declarations and task tracking rows |
| lanes.json | Computed execution lane assignments mapping WPs to worktree lanes |
| Dependency Graph | DAG of WP-to-WP dependencies parsed from tasks.md and/or WP frontmatter |
| Ownership Manifest | Per-WP declaration of owned file globs, used for lane conflict detection |
| Collapse Report | New diagnostic output explaining why independent WPs were merged into a single lane |

## Dependencies & Assumptions

### Dependencies

- The existing `FrontmatterManager` API in `src/specify_cli/frontmatter.py` correctly handles YAML list values via ruamel.yaml
- The existing `status.events.jsonl` canonical status model (feature 060) is stable and does not need changes
- The existing union-find lane computation in `src/specify_cli/lanes/compute.py` is the correct algorithmic foundation; only its rules and reporting need refinement

### Assumptions

- The bullet-list dependency format in tasks.md is the primary format LLMs generate; inline format is secondary but must remain supported
- Surface-heuristic merging (Rule 3) can be made less aggressive without breaking existing valid lane assignments
- Checkbox is the canonical emitted format for `tasks.md`; pipe-table is a backward-compatible input format. `mark-status` supports both. No format-selection feature or automatic migration is added in this mission
- Planning-artifact WPs (`execution_mode: planning_artifact`) are intentionally excluded from lane assignment by the existing execution model; this mission does not change that model, only makes the exclusion visible and diagnostic

## Success Criteria

1. A fresh Spec Kitty feature with multi-WP dependencies can be finalized into executable WPs and lanes without any manual repair of dependencies, lanes, or task state
2. Running `finalize-tasks --validate-only` on any feature leaves zero files changed on disk
3. Lane computation produces multi-lane output for features with genuinely independent WPs and disjoint file ownership
4. When lane collapse occurs, operators can read the collapse report and understand exactly why
5. External agents following generated slash-command prompts succeed on the first invocation of context-resolution commands
6. All six referenced issues (#406, #417, #422, #423, #434, #438) have their root causes addressed and regression tests preventing recurrence

## Suggested WP Decomposition

- **WP01 — Dependency and Frontmatter Truth**: Fixes #406 and #417. Parser/finalizer contracts, source-of-truth rules, non-mutating validation.
- **WP02 — Lane Materialization Correctness**: Fixes the completeness half of #422. Every WP in lanes.json, diagnostic failure on unassignable WPs.
- **WP03 — Realistic Parallelism Preservation**: Fixes #423. Refine overlap handling, emit collapse reports, tighten surface heuristics.
- **WP04 — Mutable Task-State Compatibility**: Fixes #438. Support pipe-table format or standardize generation to checkbox, align prompts.
- **WP05 — Command Ergonomics for External Agents**: Fixes #434. Explicit `--mission` in generated examples, consistent flag naming in errors.

## Linked Issues

| Issue | Title | WP |
|-------|-------|----|
| [#406](https://github.com/Priivacy-ai/spec-kitty/issues/406) | finalize-tasks strips LLM-authored dependencies from WP frontmatter | WP01 |
| [#417](https://github.com/Priivacy-ai/spec-kitty/issues/417) | finalize-tasks --validate-only mutates WP frontmatter | WP01 |
| [#422](https://github.com/Priivacy-ai/spec-kitty/issues/422) | spec-kitty.tasks can generate impossible WPs and incomplete lane graphs | WP02 |
| [#423](https://github.com/Priivacy-ai/spec-kitty/issues/423) | lane computation can silently erase declared parallelism | WP03 |
| [#438](https://github.com/Priivacy-ai/spec-kitty/issues/438) | agent tasks mark-status cannot update pipe-table tasks.md rows | WP04 |
| [#434](https://github.com/Priivacy-ai/spec-kitty/issues/434) | agents never get context resolve right on the first try | WP05 |
