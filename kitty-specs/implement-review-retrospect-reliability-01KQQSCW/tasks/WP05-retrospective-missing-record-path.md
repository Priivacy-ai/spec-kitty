---
work_package_id: WP05
title: Retrospective Missing-Record Path
dependencies: []
requirement_refs:
- FR-009
- FR-010
- NFR-001
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
agent: "codex:gpt-5:default:reviewer"
shell_pid: "7315"
history:
- at: '2026-05-03T20:58:32Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent_retrospect.py
- src/specify_cli/retrospective/reader.py
- src/specify_cli/retrospective/writer.py
- src/specify_cli/retrospective/schema.py
- tests/cli/test_agent_retrospect_missing_record.py
- tests/cli/test_agent_retrospect_synthesize.py
priority: P1
tags: []
---

# Work Package Prompt: WP05 - Retrospective Missing-Record Path

## Objective

Give completed missions a first-class `agent retrospect` path when `.kittify/missions/<id>/retrospective.yaml` does not exist.

## Branch Strategy

- Planning/base branch at prompt creation: `main`
- Final merge target for completed work: `main`
- Execution workspace is resolved later by the implement action.

## Context

- Contract: `contracts/retrospective-cli.md`
- Existing command: `src/specify_cli/cli/commands/agent_retrospect.py`
- Existing retrospective package: `src/specify_cli/retrospective/`

## Subtasks

### T019 - Add structured missing-record outcomes

Update `synthesize --json` so missing records return parseable JSON outcomes rather than only `record_not_found`.

### T020 - Add capture/init or deterministic auto-initialization

Add an explicit `capture` or `init` command, or make synthesize initialize a missing record when completed mission artifacts are sufficient.

### T021 - Distinguish required states

Return distinct outcomes for:

- `retrospective_record_created`.
- `retrospective_synthesized`.
- `insufficient_mission_artifacts`.
- `mission_not_found`.

### T022 - Add JSON and compatibility regressions

Add tests for JSON parseability, missing mission, missing record, insufficient artifacts, and existing record behavior.

## Definition of Done

- [ ] Missing retrospective record no longer produces only a bare missing-record failure.
- [ ] JSON output distinguishes all required states.
- [ ] Existing synthesize behavior is preserved for existing records.

## Risks

- Do not fabricate retrospective findings when artifacts are insufficient. Return a structured insufficient-artifacts outcome instead.

## Implementation Command

```bash
spec-kitty agent action implement WP05 --agent <name>
```

## Activity Log

- 2026-05-03T21:41:25Z – codex:gpt-5:default:implementer – shell_pid=6815 – Started implementation via action command
- 2026-05-03T21:41:29Z – codex:gpt-5:default:implementer – shell_pid=6815 – Ready for review
- 2026-05-03T21:41:30Z – codex:gpt-5:default:reviewer – shell_pid=7315 – Started review via action command
