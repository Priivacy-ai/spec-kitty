# Implementation Plan: Planning Artifact and Query Consistency

**Branch**: `main` | **Date**: 2026-04-08 | **Spec**: [spec.md](spec.md)
**Input**: `kitty-specs/078-planning-artifact-and-query-consistency/spec.md`

---

## Summary

Normalize runtime behavior for planning-artifact work packages and fresh-run mission queries without inventing synthetic execution lanes or requiring artifact migration.

The implementation plan uses four coordinated changes:

1. Normalize missing `execution_mode` once per command/session for supported historical missions.
2. Make `src/specify_cli/workspace_context.py` the single execution-mode-aware workspace resolver, reusing the existing planning-artifact routing already present in `src/specify_cli/core/worktree.py`.
3. Surface planning-artifact lifecycle and stale semantics explicitly in status and stale-detection outputs.
4. Update `spec-kitty next` query mode so `--agent` is optional, fresh runs return `mission_state: "not_started"` plus `preview_step`, and invalid runtimes fail clearly instead of reporting `unknown`.

No new dependencies are required. The work is a targeted refactor across existing Python modules and active documentation.

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, pydantic v2, pytest, mypy --strict, existing `spec-kitty-runtime`
**Storage**: Filesystem only (`kitty-specs/*`, JSON, JSONL, Markdown, YAML frontmatter)
**Testing**: pytest unit tests, CLI integration tests, mypy --strict, 90%+ coverage on modified code paths
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows 10+)
**Project Type**: Single Python package rooted at `src/specify_cli/`
**Performance Goals**: `spec-kitty next`, `spec-kitty agent tasks status`, and workspace/stale lookups remain under 2 seconds for typical local missions and under 1 second for missions with up to 20 WPs
**Constraints**: No synthetic lane membership for planning-artifact WPs; no mandatory migration; query mode remains read-only; planning-artifact stale state must surface as `not_applicable`; no new network calls; no new agent-context update surface exists in the current CLI
**Scale/Scope**: One mission, around a dozen Python modules, two new JSON contracts, two new Markdown contracts, and updates to active docs under `docs/`

---

## Charter Check

Charter file: `/private/tmp/500-552/spec-kitty/.kittify/charter/charter.md`

| Gate | Status | Notes |
|------|--------|-------|
| Python 3.11+ | PASS | All planned changes stay in the existing Python CLI codebase |
| mypy --strict | PASS | New helper types and dataclasses will be fully annotated |
| 90%+ test coverage | PASS | Unit and integration coverage is planned for resolver, stale, and query paths |
| Integration tests for CLI commands | PASS | `spec-kitty next`, `spec-kitty agent tasks status`, `spec-kitty agent action implement`, and context resolution all need integration coverage |
| CLI operations <2s | PASS | All changes are local file reads plus process-local normalization caches |
| No new required network calls | PASS | All behavior remains local to repo and runtime state |
| Decision documentation | PASS | Research, data model, contracts, and quickstart capture the contract changes explicitly |

Post-Phase 1 re-check: PASS. The design keeps existing dependencies, preserves local-only execution, and documents the intentional machine-facing contract changes.

Agent context update note: `spec-kitty agent context --help` shows only `resolve`; the old update-context command has been removed from the current CLI. No agent context file mutation is required or possible for this mission.

---

## Project Structure

### Planning artifacts (this mission)

```
kitty-specs/078-planning-artifact-and-query-consistency/
|- spec.md
|- plan.md
|- research.md
|- data-model.md
|- quickstart.md
|- contracts/
|  |- workspace-resolution.md
|  |- planning-artifact-lifecycle.md
|  |- next-query-response.schema.json
|  `- stale-status.schema.json
`- tasks.md                    # Created later by /spec-kitty.tasks
```

### Source code changes

```
src/specify_cli/
|- workspace_context.py                 # MODIFY: one canonical execution-mode-aware resolver + session normalization cache
|- core/worktree.py                     # REUSE: existing planning-artifact repo-root routing becomes shared contract input
|- core/stale_detection.py              # MODIFY: structured stale result + not_applicable for repo-root planning work
|- cli/commands/implement.py            # MODIFY: stop treating lanes as universal validation for all WPs
|- lanes/implement_support.py           # MODIFY: branch between lane allocation and repo-root planning workspace
|- cli/commands/agent/workflow.py       # MODIFY: workflow prompt generation uses canonical resolver for planning-artifact WPs
|- cli/commands/agent/tasks.py          # MODIFY: status JSON/human output exposes execution mode and structured stale state
|- core/execution_context.py            # MODIFY: action-context resolution consumes canonical workspace contract
|- core/worktree_topology.py            # MODIFY: mixed-mission topology supports repo-root planning entries
|- next/decision.py                     # MODIFY: query decision schema gains preview_step; agent becomes nullable in query mode
|- next/runtime_bridge.py               # MODIFY: fresh-run query semantics, preview generation, validation error path
|- cli/commands/next_cmd.py             # MODIFY: query mode makes --agent optional, advancing mode still requires it
|- next/prompt_builder.py               # MODIFY: prompt rendering accepts repo-root planning workspaces
`- ownership/inference.py               # REUSE: deterministic compatibility inference for missing execution_mode

tests/
|- runtime/test_workspace_context_unit.py                # EXTEND: normalization + repo-root resolver coverage
|- agent/test_implement_command.py                       # EXTEND: planning-artifact implement path
|- next/test_next_command_integration.py                 # EXTEND: not_started + preview_step query contract
|- specify_cli/core/test_worktree_topology.py            # NEW: repo-root topology coverage for planning-artifact WPs
|- specify_cli/cli/commands/agent/test_tasks_canonical_cleanup.py    # EXTEND: status/stale JSON + human output
|- specify_cli/cli/commands/agent/test_tasks_planning_artifact_lifecycle.py # NEW: approved/done transitions for planning WPs
|- specify_cli/cli/commands/agent/test_workflow_canonical_cleanup.py # EXTEND: workflow resolution uses repo root for planning WPs
`- specify_cli/cli/commands/agent/test_tests_stale_check.py          # EXTEND or split: stale-detection edge cases

docs/
|- index.md
|- explanation/runtime-loop.md
|- reference/cli-commands.md
`- reference/agent-subcommands.md
```

**Structure decision**: Keep all changes inside the existing single-package CLI structure under `src/specify_cli/`, with matching tests under `tests/` and contract docs in `kitty-specs/078-planning-artifact-and-query-consistency/contracts/`.

---

## Phase 0 Research Outputs

`kitty-specs/078-planning-artifact-and-query-consistency/research.md` resolves the planning unknowns and records the chosen design for:

- one-time in-memory execution-mode normalization
- canonical workspace resolution
- planning-artifact lifecycle completion semantics
- structured stale-state behavior for repo-root planning work
- fresh-run query semantics and machine-facing compatibility
- the removed agent-context update surface

No `[NEEDS CLARIFICATION]` markers remain after Phase 0.

---

## Phase 1 Design Outputs

- `kitty-specs/078-planning-artifact-and-query-consistency/data-model.md`
- `kitty-specs/078-planning-artifact-and-query-consistency/quickstart.md`
- `kitty-specs/078-planning-artifact-and-query-consistency/contracts/workspace-resolution.md`
- `kitty-specs/078-planning-artifact-and-query-consistency/contracts/planning-artifact-lifecycle.md`
- `kitty-specs/078-planning-artifact-and-query-consistency/contracts/next-query-response.schema.json`
- `kitty-specs/078-planning-artifact-and-query-consistency/contracts/stale-status.schema.json`

Agent context update result: skipped by current architecture. There is no `spec-kitty agent context update-context` command in the current CLI, and this mission introduces no new technology that would require agent-context mutation.

---

## Candidate Work Packages

### WP01 - Session normalization and canonical workspace resolution

**Scope**: Load WP metadata once per mission, infer missing `execution_mode` in memory for supported historical missions, and make the canonical resolver return either a lane workspace or repo root.

**Files**: `src/specify_cli/workspace_context.py`, `src/specify_cli/core/worktree.py`, `src/specify_cli/ownership/inference.py`, `tests/runtime/test_workspace_context_unit.py`

**Dependencies**: none

### WP02 - Implement, workflow, action-context, and topology integration

**Scope**: Replace lane-only assumptions in implement, workflow, context, and topology code paths so planning-artifact WPs can start and resolve correctly from repo root without collapsing informational topology rendering.

**Files**: `src/specify_cli/cli/commands/implement.py`, `src/specify_cli/lanes/implement_support.py`, `src/specify_cli/cli/commands/agent/workflow.py`, `src/specify_cli/core/execution_context.py`, `src/specify_cli/core/worktree_topology.py`, `src/specify_cli/next/prompt_builder.py`, `tests/agent/test_implement_command.py`, `tests/specify_cli/cli/commands/agent/test_workflow_canonical_cleanup.py`, `tests/specify_cli/core/test_worktree_topology.py`

**Dependencies**: WP01

### WP03 - Status, stale-state, and done-transition cleanup

**Scope**: Emit structured stale information, preserve deprecated flat stale fields during the transition, remove merge-ancestry gating for planning-artifact `done` transitions, and update human-readable status output.

**Files**: `src/specify_cli/core/stale_detection.py`, `src/specify_cli/cli/commands/agent/tasks.py`, `kitty-specs/078-planning-artifact-and-query-consistency/contracts/stale-status.schema.json`, `kitty-specs/078-planning-artifact-and-query-consistency/contracts/planning-artifact-lifecycle.md`, `tests/specify_cli/cli/commands/agent/test_tasks_canonical_cleanup.py`, `tests/specify_cli/cli/commands/agent/test_tasks_planning_artifact_lifecycle.py`

**Dependencies**: WP01

### WP04 - Query-mode contract and runtime bridge cleanup

**Scope**: Make query mode agent-optional, add `preview_step`, return `not_started` for fresh runs, and fail clearly when a mission has no issuable first step.

**Files**: `src/specify_cli/next/decision.py`, `src/specify_cli/next/runtime_bridge.py`, `src/specify_cli/cli/commands/next_cmd.py`, `kitty-specs/078-planning-artifact-and-query-consistency/contracts/next-query-response.schema.json`, `tests/next/test_next_command_integration.py`

**Dependencies**: none

### WP05 - Documentation and compatibility surface updates

**Scope**: Update docs, CLI help examples, and contract references so users and automation see one public model.

**Files**: `docs/index.md`, `docs/explanation/runtime-loop.md`, `docs/reference/cli-commands.md`, `docs/reference/agent-subcommands.md`, `README.md` only if needed for active command examples

**Dependencies**: WP01, WP03, WP04

---

## Dependency Graph

```
WP01 ---------------------------- no deps
WP04 ---------------------------- no deps
WP02 depends on WP01
WP03 depends on WP01
WP05 depends on WP01, WP03, WP04
```

Suggested lane grouping for later `/spec-kitty.tasks` generation:

- Lane A: WP01 -> WP02
- Lane B: WP01 -> WP03
- Lane C: WP04 -> WP05

WP05 should not start until both the resolver contract and query contract are stable enough to document.

---

## Testing Strategy

### Unit tests

**WP01**

- Normalization populates missing `execution_mode` once per mission load.
- Inferred legacy planning-artifact WPs resolve to repo root without `lanes.json` membership.
- Impossible classification fails once with an actionable compatibility error.
- Code-change WPs still resolve through existing lane-backed behavior.

**WP02**

- Implement command does not hard-fail on planning-artifact lane absence.
- Workflow prompt generation emits repo-root workspace paths for planning-artifact WPs.
- Action context resolution reports the correct workspace path for both execution modes.
- Worktree topology materialization no longer raises when a planning-artifact WP lacks lane membership; it represents repo-root planning entries explicitly.

**WP03**

- `spec-kitty agent tasks move-task <wp-id> --to approved` and `--to done` succeed for planning-artifact WPs without merge ancestry checks or done overrides.
- Code-change WPs still require merge ancestry or explicit override for `--to done`.
- `spec-kitty agent tasks status --json` emits `stale.status = "not_applicable"` and `reason = "planning_artifact_repo_root_shared_workspace"` for planning-artifact WPs in progress.
- `spec-kitty agent tasks status --json` continues to emit deprecated flat fields (`is_stale`, `minutes_since_commit`, `worktree_exists`) during the transition window, derived from the canonical nested `stale` object.
- Human-readable status output shows `stale: n/a (repo-root planning work)` instead of stale warnings.
- Shared repo-root activity is never interpreted as proof that a planning-artifact WP is fresh.

**WP04**

- `spec-kitty next --mission <slug> --json` succeeds without `--agent` in query mode.
- Fresh runs return `mission_state = "not_started"` plus `preview_step`.
- Query mode does not advance runtime state.
- Query mode fails clearly when the mission definition has no issuable first step.
- Advancing mode still requires `--agent` and `--result`.

**WP05**

- Command reference examples match actual CLI parsing.
- Runtime-loop docs no longer teach `unknown` as the valid fresh-run query state.

### Integration tests

- Start a planning-artifact WP from `planned` using `spec-kitty agent action implement <wp-id>` and verify repo-root resolution.
- Move a planning-artifact WP through `approved` to `done` and verify no merge-ancestry guardrail blocks completion.
- Run `spec-kitty agent tasks status --json` on a mixed mission and verify planning-artifact WPs appear in lifecycle status output without missing-lane errors.
- Run `spec-kitty next --mission <slug> --json` against a fresh run and verify `not_started` plus `preview_step`.
- Run the same query twice and verify no runtime state change between calls.

### Verification commands

```bash
pytest tests/runtime/test_workspace_context_unit.py -v
pytest tests/agent/test_implement_command.py -v
pytest tests/next/test_next_command_integration.py -v
pytest tests/specify_cli/core/test_worktree_topology.py -v
pytest tests/specify_cli/cli/commands/agent/test_tasks_canonical_cleanup.py -v
pytest tests/specify_cli/cli/commands/agent/test_tasks_planning_artifact_lifecycle.py -v
pytest tests/specify_cli/cli/commands/agent/test_workflow_canonical_cleanup.py -v
mypy src/specify_cli/ --strict
```

---

## Backwards Compatibility

| Surface | Impact | Mitigation |
|---------|--------|-----------|
| Historical WPs missing `execution_mode` | Previously could fail or drift by call site | Normalize once in memory per command/session; no disk rewrite required |
| `resolve_workspace_for_wp()` result shape | No longer purely lane-oriented | Extend the dataclass to describe both lane workspaces and repo-root planning work |
| Planning-artifact stale reporting | Boolean stale/fresh is no longer meaningful | Canonical contract becomes structured `stale` object with `status = not_applicable` and a reason; deprecated flat fields remain during the transition window for current machine consumers |
| Planning-artifact done transitions | Existing done guard is branch-ancestry based | Keep ancestry enforcement for `code_change`; bypass it for planning-artifact WPs and define completion in artifact terms |
| Fresh-run query JSON | `mission_state: unknown` is replaced by `mission_state: not_started` plus `preview_step` | Intentional machine-facing contract change documented in spec, plan, contracts, and docs |
| Query-mode CLI syntax | `--agent` no longer required when `--result` is omitted | Compatibility form with `--agent` remains accepted in query mode |
| Lane manifests | No new lanes are created for planning-artifact WPs | `planning_artifact_wps` remains the exclusion surface in `lanes.json` |

---

## Complexity Tracking

No charter exceptions or design-complexity waivers are required.

---

## Branch Contract (final)

- Current branch at plan start: `main`
- Planning/base branch: `main`
- Merge target: `main`
- `branch_matches_target`: `true`

**Next command**: `/spec-kitty.tasks`
