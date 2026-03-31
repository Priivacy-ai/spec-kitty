# Canonical Status Model Cleanup

## Overview

Make the 3.0 canonical status model true everywhere in the spec-kitty repo. Work package status lives only in `status.events.jsonl` and reducer-derived outputs (`status.json`), never in WP frontmatter or WP-local lane logs. This is a hard cutover for active runtime code, templates, docs, and tests. Historical checked-in artifacts under `kitty-specs/` are preserved but fenced off so they stop teaching or influencing current behavior.

## Problem Statement

The 3.0 status model (`status.events.jsonl` + reducer) was introduced but never fully propagated. The codebase has dual authority:

- Active WP frontmatter still carries `lane`, `review_status`, `reviewed_by`, `review_feedback`, and `progress` fields that compete with canonical events
- Runtime commands fall back to frontmatter lane when canonical state is missing, silently masking bootstrap failures
- Templates and generation surfaces still emit `lane: "planned"` in WP frontmatter and lane-bearing history entries
- Active docs, README, and command help still describe frontmatter-lane semantics as current behavior
- Tests construct modern WPs with `lane:` in frontmatter, validating the abandoned model
- Historical kitty-specs examples are cited as active guidance, mixing 2.x and 3.0 semantics

This dual authority causes silent correctness bugs, confusing error paths, and stale teaching surfaces.

## Actors

| Actor | Description |
|-------|-------------|
| CLI User | Developer running spec-kitty commands for feature planning and implementation |
| AI Agent | Automated agent (Claude, Codex, etc.) consuming templates and prompts to implement work packages |
| Runtime | spec-kitty Python CLI runtime executing workflow, task, merge, and dashboard commands |

## User Scenarios & Acceptance

### Scenario 1: Task Finalization Seeds Canonical State

**Given** a feature with newly generated WP files after `/spec-kitty.tasks`
**When** the user runs `spec-kitty agent feature finalize-tasks`
**Then** every WP that lacks canonical state gets an initial `planned` status event emitted to `status.events.jsonl`, `status.json` is materialized, and the WP files contain no `lane` field in their frontmatter.

### Scenario 2: Runtime Hard-Fails on Missing Canonical State

**Given** a feature whose WP files exist but `status.events.jsonl` does not
**When** the user runs any runtime command (workflow implement, tasks move-task, next, status, merge)
**Then** the command fails immediately with a clear error: "Canonical status not found. Run `spec-kitty agent feature finalize-tasks` to bootstrap status." No frontmatter fallback occurs.

### Scenario 3: Generated WPs Are Lane-Free

**Given** a user running `/spec-kitty.tasks` to generate work packages
**When** the WP prompt files are written
**Then** no WP file contains `lane:` in its YAML frontmatter. History entries contain only timestamp, actor, and action text — no lane field.

### Scenario 4: Agent Reads Status from Canonical Source

**Given** an AI agent implementing a WP in a worktree
**When** the agent needs to check WP status or move a WP between lanes
**Then** all status reads come from the canonical reducer (`status.json` or `status.events.jsonl`), and all status writes go through `emit_status_transition()`. The agent never reads or writes `lane` in WP frontmatter.

### Scenario 5: Dashboard Reads Canonical State Only

**Given** a user running `spec-kitty agent tasks status` or the dashboard scanner
**When** the board is rendered
**Then** WP lane positions come from the materialized `status.json`, not from frontmatter. WPs without canonical state are shown as "unknown/uninitialized" rather than inferred from frontmatter.

### Scenario 6: Historical Artifacts Don't Pollute Active Behavior

**Given** old feature records in `kitty-specs/` with frontmatter `lane:` fields
**When** any active runtime command scans for WP state
**Then** the old frontmatter lanes are ignored. Only canonical event state is used. Active docs do not cite these old records as examples of current behavior.

### Scenario 7: Validate-Only Checks Bootstrap Readiness

**Given** a feature with WP files but no canonical state yet
**When** the user runs `spec-kitty agent feature finalize-tasks --validate-only`
**Then** the output reports which WPs lack canonical state and what finalization would do, without mutating any files.

### Scenario 8: Migration Tools Still Work

**Given** a legacy feature with frontmatter-lane state but no event log
**When** the user runs explicit migration tooling
**Then** the migration reads frontmatter lanes and bootstraps canonical events from them. This is the only code path that reads frontmatter lane as authoritative.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `finalize-tasks` emits an initial `planned` status event for every WP that lacks canonical state in `status.events.jsonl`. | Proposed |
| FR-002 | `finalize-tasks` materializes `status.json` after seeding initial events. | Proposed |
| FR-003 | `finalize-tasks --validate-only` reports which WPs lack canonical state and whether bootstrap would succeed, without mutating files. | Proposed |
| FR-004 | Active WP frontmatter schema no longer includes `lane`, `review_status`, `reviewed_by`, `review_feedback`, or `progress` as top-level fields. | Proposed |
| FR-005 | Frontmatter validation for active WPs requires only static definition fields (work_package_id, title, dependencies, subtasks, owned_files, authoritative_surface, execution_mode, planning_base_branch, merge_target_branch, branch_strategy) and never requires `lane`. | Proposed |
| FR-006 | Active WP history entries contain only timestamp (`at`), actor/agent, optional shell PID, and action text. No `lane` field in history entries. | Proposed |
| FR-007 | Active body-section activity log text does not include `lane=` entries or lane-transition records. | Proposed |
| FR-008 | All runtime commands that read WP status (workflow implement/review, tasks move-task/status/list, next, dashboard, acceptance, merge/preflight) read from canonical reducer state only — never from frontmatter `lane`. | Proposed |
| FR-009 | When canonical state (`status.events.jsonl`) is missing for a feature, runtime commands fail with a clear error directing the user to run finalize-tasks or migration tooling. No silent frontmatter fallback. | Proposed |
| FR-010 | Active planning prompts and templates (task-generation guidance, tasks README bootstrap, generic WP templates, mission-specific templates) do not emit `lane: "planned"` or lane-bearing history examples. | Proposed |
| FR-011 | Active docs (README, command help, generated README text) describe `status.events.jsonl` as sole status authority, `status.json` as derived snapshot, and WP frontmatter as static definition only. | Proposed |
| FR-012 | Old "frontmatter-only lane" explanations in docs are relabeled as historical/versioned context, not current guidance. | Proposed |
| FR-013 | Active tests do not construct modern WPs with `lane:` in frontmatter except in explicit legacy/migration test coverage. | Proposed |
| FR-014 | Migration-only code paths that read frontmatter lane remain functional for explicit migration commands. | Proposed |
| FR-015 | Any parser or helper that reconstructs status from WP-local history is either deleted or demoted to migration-only. | Proposed |
| FR-016 | Historical `kitty-specs/*` records are preserved unchanged. Active guidance does not cite them as examples of current behavior. | Proposed |
| FR-017 | Operational metadata fields (`agent`, `assignee`, `shell_pid`, `requirement_refs`) remain in WP frontmatter unchanged. This cleanup does not remove non-status operational metadata. | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold |
|----|-------------|-----------|
| NFR-001 | Runtime error messages for missing canonical state are actionable. | Every hard-fail message names the missing file, the affected feature, and the exact command to run to fix it. |
| NFR-002 | Test coverage on new/modified code. | 90%+ line coverage on modified finalization, runtime reader, and template generation code. |
| NFR-003 | Type checking passes on all new and modified code. | `mypy --strict` produces zero errors on changed files. |
| NFR-004 | No regression in existing features with canonical state. | All features that already have `status.events.jsonl` continue to work identically after this change. |

## Constraints

| ID | Constraint |
|----|------------|
| C-001 | Historical `kitty-specs/*` records are preserved unchanged. Do not mass-rewrite old feature records. |
| C-002 | Only the spec-kitty repo is in scope. `spec-kitty-orchestrator` override cleanup is a follow-up. |
| C-003 | Non-status operational metadata (`agent`, `assignee`, `shell_pid`, `requirement_refs`) remains unchanged in WP frontmatter. |
| C-004 | Explicit migration tools must still be able to ingest legacy frontmatter-lane artifacts. Migration-only code is preserved. |
| C-005 | No fallback logic. If canonical state is missing, fail — do not silently reconstruct from frontmatter. |
| C-006 | WP-local history remains allowed as human-readable non-authoritative notes, but must not encode lane state. |

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | After finalize-tasks, every WP in a feature has canonical state in `status.events.jsonl` and a materialized `status.json`. |
| SC-002 | No active runtime command reads `lane` from WP frontmatter for status determination. |
| SC-003 | No active template or generation surface emits `lane:` in WP frontmatter or lane-bearing history entries. |
| SC-004 | Runtime commands hard-fail with actionable guidance when canonical state is missing. |
| SC-005 | Active docs and README consistently describe the 3.0 status model without referencing frontmatter-lane as current behavior. |
| SC-006 | All active tests construct WPs without `lane:` in frontmatter, except explicit migration/legacy test fixtures. |
| SC-007 | Features with existing canonical state (e.g., 059-saas-mediated-cli-tracker-reflow) work identically after this change. |

## Key Entities

| Entity | Description |
|--------|-------------|
| status.events.jsonl | Append-only event log per feature. Sole authority for WP lane state. Each line is a StatusEvent JSON object. |
| status.json | Derived materialized snapshot produced by the reducer from status.events.jsonl. Read-only view used by dashboard and runtime queries. |
| WP Frontmatter | YAML frontmatter in WP prompt files. After this cleanup: static definition fields + operational metadata only. No mutable status fields. |
| WP History | YAML `history` array and body activity notes in WP files. After this cleanup: lane-free records (timestamp, actor, action text). Non-authoritative. |
| finalize-tasks | CLI command that validates WPs, parses dependencies, and (after this cleanup) seeds initial canonical status for newly generated WPs. |
| StatusEvent | Pydantic model in `specify_cli/status/models.py`. Immutable event representing a lane transition. |
| Reducer | `specify_cli/status/reducer.py`. Deterministic function: events → snapshot. Same events always produce same state. |

## Dependencies

| Dependency | Status | Impact |
|------------|--------|--------|
| Feature 034 (Status State Model Remediation) | Complete | Introduced the canonical status model this feature enforces everywhere. |
| Feature 059 (SaaS Tracker Reflow) | Complete | Most recent feature sprint — validates that existing canonical state continues working. |
| Existing `specify_cli/status/` package | Available | `emit.py`, `reducer.py`, `store.py`, `models.py`, `transitions.py` — all reused, not rewritten. |

## Assumptions

| # | Assumption |
|---|------------|
| A-001 | The `specify_cli/status/` package (emit, reducer, store, models, transitions) is correct and stable. This feature uses it, does not redesign it. |
| A-002 | All active features created after Feature 034 already have `status.events.jsonl`. This cleanup primarily affects generation surfaces, templates, and runtime fallback paths. |
| A-003 | Historical `kitty-specs/*` records will never be migrated in bulk. They are inert artifacts preserved for git history. |
| A-004 | `spec-kitty-orchestrator/.kittify/overrides` cleanup is deferred to a follow-up. |

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Breaking features that rely on frontmatter-lane fallback | Low | Medium | Features created after 034 already have canonical state. Hard-fail error directs users to finalize-tasks. |
| Template changes reintroducing lane fields later | Medium | Low | Add grep-based regression test that scans active templates for `lane:` in frontmatter positions. |
| Tests that construct WPs with `lane:` are missed | Medium | Medium | Systematic search for `lane:` in test fixtures; update all non-migration tests. |

## Out of Scope

- Redesigning the canonical status model itself (Feature 034 scope)
- Removing non-status operational metadata (agent, assignee, shell_pid) from frontmatter
- Mass-rewriting historical kitty-specs records
- `spec-kitty-orchestrator` override cleanup (follow-up)
- Adding new status model features (new lanes, new event types)
