---
work_package_id: WP03
title: CLI Identity Flags
lane: "done"
dependencies:
- WP01
- WP02
subtasks:
- T010
- T011
- T012
- T013
- T014
phase: Phase 2 - Identity Integration
assignee: ''
agent: "claude-sonnet-4-6"
shell_pid: ''
review_status: "approved"
reviewed_by: "Stijn Dejongh"
review_feedback: ''
history:
- timestamp: '2026-03-08T10:13:04Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-003
- FR-010
---

# Work Package Prompt: WP03 – CLI Identity Flags

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check `review_status`. If it says `has_feedback`, read `review_feedback` first.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Implementation Command

```bash
spec-kitty implement WP03 --base WP02
```

---

## Objectives & Success Criteria

- Add `--tool`, `--model`, `--profile`, `--role` individual CLI flags to all commands that accept `--agent`
- Implement mutual exclusion between `--agent` (compound) and individual flags
- Wire parsed identity through `emit_status_transition()` to produce structured events
- Ensure CLI flag identity → JSONL event actor is fully traceable

**Success metrics**:
- `spec-kitty agent tasks move-task WP01 --to doing --agent claude:opus-4:impl:impl` → event has structured actor
- `spec-kitty agent tasks move-task WP01 --to doing --tool claude --model opus-4 --profile impl --role impl` → identical result
- `--agent claude --tool claude` → clear error message

## Context & Constraints

- **Spec**: FR-003 (Compound CLI Identity Flag), FR-010 (End-to-End Pipeline)
- **Contracts**: `contracts.md` — Contract 2 (parse_agent_identity)
- **Dependency**: WP01 (ActorIdentity), WP02 (frontmatter integration)
- **Key files**: `src/specify_cli/cli/commands/agent/tasks.py` (move-task), `src/specify_cli/cli/commands/agent/workflow.py` (implement, review)
- **Key file**: `src/specify_cli/status/emit.py` — `emit_status_transition()` currently takes `actor: str`

## Subtasks & Detailed Guidance

### Subtask T010 – Create parse_agent_identity() Function

**Purpose**: Centralised parser that converts CLI flags (compound or individual) into `ActorIdentity`.

**Steps**:
1. Add to `src/specify_cli/identity.py`:
   ```python
   import typer

   def parse_agent_identity(
       agent: str | None = None,
       tool: str | None = None,
       model: str | None = None,
       profile: str | None = None,
       role: str | None = None,
   ) -> ActorIdentity | None:
       """Parse CLI identity flags into ActorIdentity.
       
       Args:
           agent: Compound string "tool:model:profile:role" or legacy bare name
           tool, model, profile, role: Individual identity flags
       
       Returns:
           ActorIdentity if any flags provided, None if all are None
       
       Raises:
           typer.BadParameter: If both compound and individual flags are provided
       """
       individual_flags = [tool, model, profile, role]
       has_individual = any(f is not None for f in individual_flags)
       
       if agent is not None and has_individual:
           raise typer.BadParameter(
               "Cannot use --agent with --tool/--model/--profile/--role. "
               "Use either --agent 'tool:model:profile:role' OR individual flags, not both."
           )
       
       if agent is not None:
           return ActorIdentity.from_compact(agent)
       
       if has_individual:
           return ActorIdentity(
               tool=tool or "unknown",
               model=model or "unknown",
               profile=profile or "unknown",
               role=role or "unknown",
           )
       
       return None
   ```

**Files**: `src/specify_cli/identity.py` (add to existing file from WP01)
**Parallel?**: No — T011, T012 depend on this

### Subtask T011 – Add Identity Flags to move-task Command

**Purpose**: Extend the `move-task` CLI command with individual identity flags.

**Steps**:
1. In `src/specify_cli/cli/commands/agent/tasks.py`, locate the `move_task()` function (~line 777)
2. Add new parameters after the existing `--agent` parameter:
   ```python
   tool: Annotated[str | None, typer.Option("--tool", help="Agent tool name (e.g., claude, copilot)")] = None,
   model: Annotated[str | None, typer.Option("--model", help="Agent model variant (e.g., claude-opus-4-6)")] = None,
   profile: Annotated[str | None, typer.Option("--profile", help="Agent governance profile ID")] = None,
   role: Annotated[str | None, typer.Option("--role", help="Agent role (e.g., implementer, reviewer)")] = None,
   ```
3. Early in the function body, parse identity:
   ```python
   from specify_cli.identity import parse_agent_identity
   parsed_identity = parse_agent_identity(agent=agent, tool=tool, model=model, profile=profile, role=role)
   ```
4. Pass `parsed_identity` (or its compact string) where `agent` was previously passed to downstream functions
5. Where the agent is passed to `emit_status_transition()`, pass the `ActorIdentity` object

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`
**Parallel?**: Yes — can proceed in parallel with T012

### Subtask T012 – Add Identity Flags to Workflow Commands

**Purpose**: Extend `implement` and `review` workflow commands with the same individual identity flags.

**Steps**:
1. In `src/specify_cli/cli/commands/agent/workflow.py`, locate the `implement()` and `review()` functions
2. Add the same `--tool`, `--model`, `--profile`, `--role` parameters as in T011
3. Parse identity using `parse_agent_identity()` at the start of each function
4. Pass `ActorIdentity` to downstream status emission

**Files**: `src/specify_cli/cli/commands/agent/workflow.py`
**Parallel?**: Yes — can proceed in parallel with T011

### Subtask T013 – Wire Parsed Identity Through emit_status_transition()

**Purpose**: Update `emit_status_transition()` to accept `ActorIdentity` in addition to bare strings, coercing at the boundary.

**Steps**:
1. In `src/specify_cli/status/emit.py`, update the `actor` parameter type:
   ```python
   # Before:
   def emit_status_transition(
       ...,
       actor: str,
       ...
   )
   
   # After:
   def emit_status_transition(
       ...,
       actor: str | ActorIdentity,
       ...
   )
   ```
2. At the top of the function, coerce string to `ActorIdentity`:
   ```python
   if isinstance(actor, str):
       actor = ActorIdentity.from_legacy(actor) if actor else ActorIdentity.from_legacy("unknown")
   ```
3. Pass the `ActorIdentity` object when constructing `StatusEvent`
4. Add import: `from specify_cli.identity import ActorIdentity`

**Files**: `src/specify_cli/status/emit.py`
**Parallel?**: No — depends on T010, needed by T011/T012

### Subtask T014 – Mutual Exclusion Validation

**Purpose**: Ensure that using both `--agent` compound flag and any individual flag (`--tool`, `--model`, etc.) raises a clear, actionable error.

**Steps**:
1. This is already implemented in `parse_agent_identity()` (T010), but verify it works end-to-end:
   - Test: `spec-kitty agent tasks move-task WP01 --to doing --agent claude --tool copilot`
   - Expected: Error message: "Cannot use --agent with --tool/--model/--profile/--role..."
2. Verify the error message includes both flag forms so users know the alternatives
3. Ensure the error is raised before any state changes (no partial writes)

**Files**: `src/specify_cli/identity.py` (validation in `parse_agent_identity()`), test files
**Parallel?**: No — validation logic already in T010, this is verification

## Test Strategy

- Unit tests for `parse_agent_identity()` in `tests/specify_cli/test_identity.py`:
  - Compound string → correct ActorIdentity
  - Individual flags → correct ActorIdentity
  - Both compound + individual → `typer.BadParameter`
  - All None → None
  - Partial individual flags → fills unknown
- CLI integration test: `move-task` with `--agent` compound → verify event JSONL
- CLI integration test: `move-task` with individual flags → verify event JSONL
- Regression: `pytest tests/specify_cli/cli/ -v` should pass

## Risks & Mitigations

- **emit.py callers**: Many places call `emit_status_transition()` with `actor: str` → the `str | ActorIdentity` union type ensures backwards compat
- **Typer flag conflicts**: `--profile` might conflict with existing flags in some commands → check each command's existing flags before adding

## Review Guidance

- Verify mutual exclusion error message is clear and actionable
- Verify `emit_status_transition()` coerces str at boundary
- Verify JSONL events contain structured actor dict (not string)
- Check that `--profile` doesn't conflict with existing constitution `--profile` flag in workflow commands

## Activity Log

- 2026-03-08T10:13:04Z – system – lane=planned – Prompt created.
- 2026-03-09T04:29:02Z – claude-sonnet-4-6 – lane=done – Implementation complete and merged | Done override: History was rebased; branch ancestry tracking not applicable
