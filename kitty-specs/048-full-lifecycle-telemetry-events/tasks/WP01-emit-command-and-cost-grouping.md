---
work_package_id: WP01
title: Telemetry Emit CLI Command + Cost Grouping
lane: "done"
dependencies: []
base_branch: develop
base_commit: f53a68adce92a03bcb2117a75e4d40951c851479
created_at: '2026-02-16T14:22:42.307280+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
phase: Phase 1 - Core Implementation
assignee: ''
agent: claude
shell_pid: '838332'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-02-16T14:16:58Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – Telemetry Emit CLI Command + Cost Grouping

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP01
```

No dependencies — branches from target branch directly.

---

## Objectives & Success Criteria

1. A new `spec-kitty agent telemetry emit` CLI command exists that persists ExecutionEvents to a feature's JSONL file
2. The emit command always persists an event, even when optional fields are missing (never silently skips)
3. `cost_summary()` supports `group_by="role"` for per-phase cost breakdown
4. The `spec-kitty agent telemetry cost --group-by role` CLI flag works
5. Existing telemetry emissions in `feature.py` and `workflow.py` no longer require `--agent` and `--model` to emit
6. All changes have unit tests with 90%+ coverage
7. `mypy --strict` passes on modified files
8. `ruff check` passes on modified files

## Context & Constraints

- **Spec**: `kitty-specs/048-full-lifecycle-telemetry-events/spec.md`
- **Plan**: `kitty-specs/048-full-lifecycle-telemetry-events/plan.md`
- **Constitution**: `.kittify/memory/constitution.md` — requires test-first (ATDD + TDD), mypy --strict, 90%+ coverage
- **Existing telemetry API**: `src/specify_cli/telemetry/emit.py` — `emit_execution_event()` is the core function
- **Existing CLI module**: `src/specify_cli/cli/commands/agent/telemetry.py` — already has `cost` command, add `emit` here
- **Fire-and-forget**: The emit command must never fail with non-zero exit code. All exceptions caught internally.
- **Lamport clocks**: Already handled by `emit_execution_event()` — no manual clock management needed.

## Subtasks & Detailed Guidance

### Subtask T001 – Add `emit` subcommand to telemetry CLI

**Purpose**: Provide a generic CLI entry point for slash command templates to emit telemetry events at the end of each workflow phase.

**Steps**:

1. Open `src/specify_cli/cli/commands/agent/telemetry.py`
2. Add a new `@app.command("emit")` function with these parameters:
   - `--feature` (required, `str`): Feature slug (e.g., `048-full-lifecycle-telemetry-events`)
   - `--role` (required, `str`, Choice): One of `specifier`, `planner`, `implementer`, `reviewer`, `merger`
   - `--agent` (`str | None`): Tool identifier (claude, copilot, codex, cursor, etc.)
   - `--model` (`str | None`): LLM model identifier
   - `--input-tokens` (`int | None`): Input token count
   - `--output-tokens` (`int | None`): Output token count
   - `--cost-usd` (`float | None`): Cost in USD
   - `--duration-ms` (`int`, default 0): Duration in milliseconds
   - `--success` (`bool`, default True): Whether the phase succeeded
   - `--wp-id` (`str`, default "N/A"): Work package ID (for implement/review phases)
   - `--json` (`bool`): JSON output mode

3. Implementation logic:

   ```python
   @app.command("emit")
   def emit_cmd(
       feature: str = typer.Option(..., "--feature", "-f", help="Feature slug"),
       role: str = typer.Option(
           ..., "--role", "-r", help="Phase role",
           click_type=click.Choice(["specifier", "planner", "implementer", "reviewer", "merger"]),
       ),
       agent: str | None = typer.Option(None, "--agent", help="Agent identifier"),
       model: str | None = typer.Option(None, "--model", help="Model used"),
       input_tokens: int | None = typer.Option(None, "--input-tokens", help="Input tokens"),
       output_tokens: int | None = typer.Option(None, "--output-tokens", help="Output tokens"),
       cost_usd: float | None = typer.Option(None, "--cost-usd", help="Cost in USD"),
       duration_ms: int = typer.Option(0, "--duration-ms", help="Duration in milliseconds"),
       success: bool = typer.Option(True, "--success/--failure", help="Phase outcome"),
       wp_id: str = typer.Option("N/A", "--wp-id", help="Work package ID"),
       json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
   ) -> None:
   ```

4. Resolve feature directory: `repo_root / "kitty-specs" / feature`
   - If directory doesn't exist, create it (first event for a new feature)

5. Call `emit_execution_event()` wrapped in try/except:

   ```python
   try:
       from specify_cli.telemetry.emit import emit_execution_event
       emit_execution_event(
           feature_dir=feature_dir,
           feature_slug=feature,
           wp_id=wp_id,
           agent=agent or "unknown",
           role=role,
           model=model,
           input_tokens=input_tokens,
           output_tokens=output_tokens,
           cost_usd=cost_usd,
           duration_ms=duration_ms,
           success=success,
           node_id="cli",
       )
   except Exception as exc:
       # Fire-and-forget: log warning but don't fail
       logger.warning("Telemetry emission failed: %s", exc)
   ```

6. Output result (JSON or text) and always exit 0.

**Files**:

- `src/specify_cli/cli/commands/agent/telemetry.py` (modify, add ~60 lines)

**Notes**:

- Import `click` for `click.Choice` (already imported in file for cost command)
- The `--success/--failure` flag pair is a typer boolean flag pattern

---

### Subtask T002 – Add `group_by="role"` to cost_summary()

**Purpose**: Enable per-phase cost aggregation so users can see how much each workflow phase costs.

**Steps**:

1. Open `src/specify_cli/telemetry/cost.py`
2. In the `cost_summary()` function, add a new elif branch at line ~88:

   ```python
   elif group_by == "role":
       key = payload.get("role", "unknown")
   ```

3. Update the docstring to mention "role" as a valid `group_by` value
4. Update the `ValueError` message to include "role"

**Files**:

- `src/specify_cli/telemetry/cost.py` (modify, ~5 lines changed)

**Validation**:

- Call `cost_summary(events, group_by="role")` with events containing different roles
- Verify events are grouped by role (specifier, planner, implementer, reviewer, merger)

---

### Subtask T003 – Add "role" to click.Choice in cost CLI command

**Purpose**: Expose the new `group_by="role"` option in the CLI.

**Steps**:

1. Open `src/specify_cli/cli/commands/agent/telemetry.py`
2. Find the `cost_cmd` function's `group_by` parameter (around line 51-54)
3. Change: `click_type=click.Choice(["agent", "model", "feature"])`
4. To: `click_type=click.Choice(["agent", "model", "feature", "role"])`
5. Update the help text to mention "role"

**Files**:

- `src/specify_cli/cli/commands/agent/telemetry.py` (modify, 1 line changed)

---

### Subtask T004 – Remove `if agent and model` gate in feature.py

**Purpose**: Ensure telemetry events are always emitted when feature commands complete, even without explicit `--agent`/`--model` flags.

**Steps**:

1. Open `src/specify_cli/cli/commands/agent/feature.py`
2. Find all occurrences of `if agent and model:` that guard `emit_execution_event()` calls (there are 3: create-feature ~line 404, setup-plan ~line 672, finalize-tasks ~line 1252)
3. For each occurrence:
   - Remove the `if agent and model:` condition
   - Keep the try/except wrapper
   - Default `agent` to `agent or "unknown"` in the `emit_execution_event()` call
   - Model can remain `None` (already nullable in the API)

**Example transformation**:

```python
# BEFORE:
if agent and model:
    try:
        from specify_cli.telemetry.emit import emit_execution_event
        emit_execution_event(
            feature_dir=feature_dir,
            feature_slug=feature_slug,
            wp_id="N/A",
            agent=agent,
            role="planner",
            ...
        )
    except Exception:
        pass

# AFTER:
try:
    from specify_cli.telemetry.emit import emit_execution_event
    emit_execution_event(
        feature_dir=feature_dir,
        feature_slug=feature_slug,
        wp_id="N/A",
        agent=agent or "unknown",
        role="planner",
        ...
    )
except Exception:
    pass
```

**Files**:

- `src/specify_cli/cli/commands/agent/feature.py` (modify, 3 locations)

**Notes**:

- Keep the `try/except` — fire-and-forget behavior must be preserved
- The `except Exception: pass` pattern is intentional for telemetry (non-blocking)

---

### Subtask T005 – Remove `if agent and model` gate in workflow.py

**Purpose**: Same as T004, but for implement and review commands.

**Steps**:

1. Open `src/specify_cli/cli/commands/agent/workflow.py`
2. Find all occurrences of `if agent and model:` guarding `emit_execution_event()` (there are 2: implement ~line 633, review ~line 1157)
3. Apply the same transformation as T004:
   - Remove the `if` guard
   - Default `agent` to `agent or "unknown"`
   - Keep try/except wrapper

**Files**:

- `src/specify_cli/cli/commands/agent/workflow.py` (modify, 2 locations)

---

### Subtask T006 – Unit tests for emit CLI command

**Purpose**: Verify the new `emit` command works correctly across all scenarios.

**Steps**:

1. Create `tests/specify_cli/cli/commands/agent/test_telemetry_emit.py` (or add to existing test file if one exists for telemetry CLI)
2. Test cases:
   - **Happy path**: `emit --feature test-feature --role specifier --agent claude --model opus-4` → event in JSONL
   - **Minimal flags**: `emit --feature test-feature --role planner` → event in JSONL with agent=unknown, model=None
   - **All flags**: Include `--input-tokens`, `--output-tokens`, `--cost-usd`, `--duration-ms`, `--wp-id`
   - **JSON output**: `--json` flag returns structured output
   - **Failure mode**: `--failure` flag sets `success: false` in event payload
   - **Invalid role**: Non-existent role rejected by click.Choice
   - **Missing feature dir**: Feature directory doesn't exist yet → created automatically
   - **Fire-and-forget**: If `emit_execution_event` raises, command still exits 0

3. Use `tmp_path` fixture for isolated feature directories
4. Use `typer.testing.CliRunner` for CLI invocation
5. Read the JSONL file directly to verify event content

**Files**:

- `tests/specify_cli/cli/commands/agent/test_telemetry_emit.py` (new, ~150 lines)

**Notes**:

- Follow Arrange-Act-Assert pattern per constitution
- Use descriptive test names: `test_emit_specifier_event_with_all_flags`, etc.

---

### Subtask T007 – Unit tests for group_by="role" cost aggregation

**Purpose**: Verify the new `group_by="role"` grouping in `cost_summary()`.

**Steps**:

1. Find existing test file for cost module (likely `tests/specify_cli/telemetry/test_cost.py`)
2. Add test cases:
   - **Multi-role grouping**: Events with different roles → separate CostSummary per role
   - **Single role**: All events same role → one CostSummary
   - **Unknown role**: Events without `role` in payload → grouped under "unknown"
   - **CLI integration**: `spec-kitty agent telemetry cost --group-by role` works

3. Create test events using the Event model with different `role` values in payload

**Files**:

- `tests/specify_cli/telemetry/test_cost.py` (modify, add ~60 lines)

---

### Subtask T008 – Tests for always-emit behavior

**Purpose**: Verify that removing the `if agent and model` gate doesn't break existing commands and that events now emit without explicit flags.

**Steps**:

1. Find existing test files for feature.py and workflow.py commands
2. Add/update test cases:
   - **No flags**: `create-feature "test"` without `--agent`/`--model` → event still emitted with `agent="unknown"`
   - **Agent only**: `create-feature "test" --agent claude` without `--model` → event emitted with model=None
   - **Both flags**: Still works as before (regression check)
   - **Same for**: `setup-plan`, `finalize-tasks`, `implement`, `review`

3. Verify event content: agent defaults to "unknown", model is None, other fields populated correctly

**Files**:

- Existing test files for feature.py and workflow.py (modify, add ~40 lines each)

**Notes**:

- May need to mock or check the JSONL file output depending on existing test patterns
- Some existing tests may assert that no event is emitted without flags — update those assertions

---

## Test Strategy

Constitution requires ATDD + TDD (test-first). Implementation order:

1. Write acceptance tests first (T006, T007, T008) — they must fail (RED)
2. Implement production code (T001-T005) — tests should pass (GREEN)
3. Refactor if needed while keeping tests green

**Commands**:

```bash
pytest tests/specify_cli/cli/commands/agent/test_telemetry_emit.py -v
pytest tests/specify_cli/telemetry/test_cost.py -v -k role
mypy --strict src/specify_cli/cli/commands/agent/telemetry.py src/specify_cli/telemetry/cost.py
ruff check src/specify_cli/cli/commands/agent/ src/specify_cli/telemetry/
```

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Existing tests assert `if agent and model` gate behavior | Update those tests in T008 to expect always-emit |
| `emit_execution_event()` may have required `agent` parameter | Check function signature — agent may need to accept None or "unknown" |
| Import of `click` may need updating in telemetry.py | Already imported for cost command — verify |

## Review Guidance

- Verify the emit command always exits 0 (fire-and-forget)
- Verify events are persisted to the correct JSONL file path
- Verify `group_by="role"` produces correct grouping
- Verify gate removal doesn't break existing test suite: `pytest tests/ -v`
- Verify `mypy --strict` passes on all modified files
- Verify `ruff check` passes

## Activity Log

- 2026-02-16T14:16:58Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-02-16T14:22:43Z – claude – shell_pid=807657 – lane=doing – Assigned agent via workflow command
- 2026-02-16T15:23:51Z – claude – shell_pid=807657 – lane=for_review – Ready for review: emit CLI command, role cost grouping, always-emit gate removal, 23 tests passing
- 2026-02-16T15:48:31Z – claude – shell_pid=838332 – lane=doing – Started review via workflow command
- 2026-02-16T15:49:54Z – claude – shell_pid=838332 – lane=done – Review passed
