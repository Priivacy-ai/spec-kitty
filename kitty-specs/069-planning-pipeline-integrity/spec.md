# Spec: Planning Pipeline Integrity and Runtime Reliability

**Mission**: 069-planning-pipeline-integrity
**Version**: 1.0
**Status**: Draft
**Target Branch**: main

---

## Overview

Spec-kitty's planning and runtime surfaces exhibit four structural fragilities discovered during active development of mission 068. Each makes the tool unreliable for agents running automated workflows, for CI pipelines checking repo cleanliness, and for humans authoring mission plans.

**Problem summary:**

1. **Dirty-git reads (#524)** — Read-only CLI commands silently modify the git working tree by unconditionally rewriting a derived status cache file on every invocation.
2. **Corrupted lane assignments (#525)** — Work package dependency extraction silently produces wrong lane assignments by scanning unbounded prose regions in `tasks.md`.
3. **Ghost completions (#526)** — The mission state machine advances on every bare invocation of `next`, even when no work was completed.
4. **Slug validator mismatch (#527)** — The `specify` command rejects all feature slugs that follow spec-kitty's own `NNN-*` naming convention.

This feature resolves all four.

---

## Actors

| Actor | Description |
|-------|-------------|
| **Agent** | An automated AI coding assistant executing spec-kitty commands in a worktree or main repository checkout. |
| **Human operator** | A developer or release engineer running spec-kitty commands interactively. |
| **CI pipeline** | An automated pipeline that asserts git tree cleanliness after spec-kitty command runs. |
| **Planner** | An LLM generating mission planning artifacts (`wps.yaml`, `tasks.md`, WP prompt files). |

---

## User Scenarios

### SC-001: Agent reads task status and worktree stays clean

An agent running inside a git worktree calls the task status command to check which work packages are in which lane. After the call, `git status` shows no modified or untracked files. The agent can continue working without needing to stash or reset unexpected changes.

**Acceptance**: `git status --porcelain` output is empty after running any status, query-mode next, or dashboard command against a previously-clean repository.

### SC-002: Planner writes prose-heavy WP prompt files without corrupting dependencies

A planner generates a `wps.yaml` manifest declaring `WP05: dependencies: []`. It also writes a rich WP05 prompt file containing a "Dependency Graph" section that cross-references other WPs. When `finalize-tasks` runs, WP05's dependencies remain empty as declared. The lane planner assigns WP05 to a parallel lane.

**Acceptance**: After `finalize-tasks`, WP05 is not assigned any dependency derived from prose content in any WP prompt file or `tasks.md`.

### SC-003: Disoriented agent uses next for orientation

An agent recovering from an error calls `spec-kitty next` (without `--result`) to find out where it is in the mission. The command returns the current step name and pending action. The output begins with `[QUERY — no result provided, state not advanced]`. The state machine does not advance. The agent sees the label, understands it must use `--result success` when it has actually completed a step.

**Acceptance**: The mission state machine step counter is identical before and after a bare `spec-kitty next` call.

### SC-004: Human specifies a numbered feature slug

A human operator runs `spec-kitty specify 068-post-merge-reliability-and-release-hardening` to create a new mission following spec-kitty's own naming convention. The command does not error on the slug. It proceeds to mission creation or discovery input.

**Acceptance**: No slug validation error is raised for any slug matching the pattern `NNN-*` where N is a digit.

### SC-005: Legacy mission without wps.yaml continues to work

A human operator runs `finalize-tasks` against an older mission that has only `tasks.md` and per-WP prompt files (no `wps.yaml`). The command falls back to the prose parser and completes without error, with dependency behavior unchanged from the previous release.

**Acceptance**: `finalize-tasks` completes successfully for missions created before `wps.yaml` was introduced.

### SC-006: CI pipeline clean-tree check passes after spec-kitty commands

A CI pipeline runs a status check command and then asserts no files were modified. The pipeline passes. Previously, this pipeline would fail due to the status cache file being unconditionally rewritten.

**Acceptance**: `git diff --exit-code` exits with code 0 after any read-only spec-kitty command on a clean repository.

---

## Functional Requirements

### Status Cache Idempotency — Problem 1 (#524)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The status cache file is only written when the underlying event log has changed since the last materialization. | Proposed |
| FR-002 | The `materialized_at` timestamp in the status cache is derived from the timestamp of the last event in the event log, not from the wall clock at read time. | Proposed |
| FR-003 | All read-only spec-kitty commands (task status, query-mode next, dashboard rendering) leave zero modified files in the git working tree on a previously-clean repository. | Proposed |

### Structured WP Manifest — Problem 2 (#525)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-004 | A structured WP manifest file (`wps.yaml`) is defined at `kitty-specs/<slug>/wps.yaml`. Each entry contains: `id`, `title`, `dependencies`, `owned_files`, `requirement_refs`, `subtasks`, and `prompt_file`. | Proposed |
| FR-005 | `wps.yaml` has a published JSON Schema at a documented location within the repository. | Proposed |
| FR-006 | When `wps.yaml` is present, `finalize-tasks` derives all WP metadata (id, title, dependencies, owned_files) exclusively from `wps.yaml`. It does not scan `tasks.md` prose for dependency or file-ownership patterns. | Proposed |
| FR-007 | An explicit `dependencies: []` declaration in `wps.yaml` is never overwritten or augmented by the planning pipeline at any stage. | Proposed |
| FR-008 | When `wps.yaml` is present, `tasks.md` is generated as a presentation artifact derived from `wps.yaml`, not authored directly by the planner for dependency purposes. | Proposed |
| FR-009 | The `/spec-kitty.tasks-outline` planning prompt produces a `wps.yaml` manifest as a primary output, alongside `tasks.md`. | Proposed |
| FR-010 | The `/spec-kitty.tasks-packages` planning prompt updates `wps.yaml` with per-WP details (owned_files, requirement_refs, subtasks, prompt_file). | Proposed |
| FR-011 | Missions without `wps.yaml` continue to function using the existing prose parser as a fallback. No behavior change for these missions. | Proposed |

### Query-Mode Safety for next — Problem 3 (#526)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-012 | `spec-kitty next` called without a `--result` argument enters query mode: it returns the current step identifier and pending action description without advancing the state machine. | Proposed |
| FR-013 | Query mode output is prefixed with `[QUERY — no result provided, state not advanced]` so agents and humans can distinguish it from an advancement response. | Proposed |
| FR-014 | `spec-kitty next --result success` retains its current behavior: advances the state machine to the next step. | Proposed |
| FR-015 | `spec-kitty next --result failed` and `spec-kitty next --result blocked` retain their current advancing behaviors. | Proposed |

### Slug Validator Fix — Problem 4 (#527)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-016 | The slug validator accepts slugs that begin with one or more digits followed by a hyphen and additional alphanumeric-and-hyphen segments (e.g., `068-post-merge-reliability`, `001-foo`). | Proposed |
| FR-017 | The slug validator continues to reject slugs containing uppercase letters, spaces, or special characters other than hyphens. | Proposed |
| FR-018 | The slug validator continues to reject empty slugs and slugs consisting solely of hyphens. | Proposed |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Read-only spec-kitty commands complete without modifying the git working tree. | Zero files appear in `git status --porcelain` on a clean repository after any read-only command. | Proposed |
| NFR-002 | `wps.yaml` schema validation produces a clear, actionable error message when a manifest is malformed. | Error message names the failing field and expected value within 1 second of invocation. | Proposed |
| NFR-003 | The `wps.yaml` presence check adds no measurable overhead for legacy missions that lack the file. | Fallback detection completes in under 10ms per mission. | Proposed |
| NFR-004 | `spec-kitty next` in query mode returns output within the same latency bounds as the current advancing call. | No measurable regression in p95 response time compared to the current release. | Proposed |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | `status.events.jsonl` remains the sole authority for WP status. `status.json` is and must remain a derived cache that can be fully regenerated at any time from the event log alone. | Required |
| C-002 | `wps.yaml` is a new file format. A JSON Schema must be published and documented before `finalize-tasks` begins consuming it. | Required |
| C-003 | Existing missions without `wps.yaml` must continue to function without any required modification to their artifacts. | Required |
| C-004 | No new required network calls are introduced by any of the four fixes. | Required |
| C-005 | `spec-kitty next --result success` retains its advancing behavior. The change affects only calls that omit `--result`. | Required |
| C-006 | WP prompt files (`tasks/WP01-*.md`) remain unrestricted authoring surfaces. Arbitrary prose, cross-references, and summary sections in prompt files must not influence dependency or lane assignment. | Required |
| C-007 | `tasks.md` generated from `wps.yaml` must preserve all information needed for a human to understand the WP breakdown and sequencing. It may not omit WP titles, dependencies, or subtask counts. | Required |

---

## Success Criteria

1. Running any read-only spec-kitty command (`agent tasks status`, `next` without `--result`, dashboard) against a clean repository leaves zero modified files in `git status`.
2. A planner can write arbitrary prose in any WP prompt file — including sections that cross-reference other WPs — without risk of corrupting dependency or lane assignments.
3. Calling `spec-kitty next` without `--result` returns the current step with a `[QUERY — no result provided, state not advanced]` label and does not advance the mission state machine.
4. `spec-kitty specify 068-any-slug` completes slug validation without error.
5. A mission with `dependencies: []` explicitly declared in `wps.yaml` cannot have those dependencies overwritten or augmented by the planning pipeline.
6. Missions created before `wps.yaml` was introduced complete `finalize-tasks` without behavioral regression.

---

## Assumptions

- The three candidate approaches to fix #524 (deterministic `materialized_at`, skip-write-on-no-change, exclude from git tracking) are implementation choices. The spec requires only the behavioral outcome: clean reads. The chosen implementation must not break any consumer that reads `status.json` as a cache.
- The JSON Schema for `wps.yaml` will be stored within the spec-kitty repository at a location determined during planning.
- The legacy prose parser is retained as a fallback code path until all active missions have migrated; it is not deleted in this feature.
- Query mode for `spec-kitty next` is activated by the absence of `--result`, not by a new `--query` flag, to minimize changes to existing agent invocation patterns.
- The slug fix applies to all spec-kitty commands that validate slugs, not only the `specify` subcommand.

---

## Out of Scope

- Automatic migration of existing missions from `tasks.md`-only format to `wps.yaml`.
- Sunset timeline or removal of the legacy prose parser.
- Changes to the `status.events.jsonl` event schema or the 7-lane state machine.
- Restrictions on how WP prompt file prose may be authored or structured.
- Validation of `owned_files` glob patterns against the actual filesystem (pattern syntax validation only, not file existence checks).
- Changes to the lane planner algorithm beyond consuming `wps.yaml` as the authoritative dependency source.
