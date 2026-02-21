---
work_package_id: WP02
title: Slash Command Template Updates and Migration
lane: "done"
dependencies: [WP01]
base_branch: 048-full-lifecycle-telemetry-events-WP01
base_commit: fa4e81cceabd7f250e1c6ac7a3537e7d610327cc
created_at: '2026-02-16T15:41:39.157553+00:00'
subtasks:
- T009
- T010
- T011
- T012
- T013
- T014
- T015
phase: Phase 2 - Template Integration
assignee: ''
agent: claude
shell_pid: '839063'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-02-16T14:16:58Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Slash Command Template Updates and Migration

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
spec-kitty implement WP02 --base WP01
```

Depends on WP01 — branches from WP01's branch.

---

## Objectives & Success Criteria

1. All 5 slash command templates (specify, plan, tasks, review, merge) include a telemetry emit section as their final instruction
2. The telemetry section instructs agents to call `spec-kitty agent telemetry emit` with appropriate `--role` and optional flags
3. A migration exists that propagates template updates to all configured agents
4. Migration uses `get_agent_dirs_for_project()` (config-aware)
5. Migration tests pass across all agent types
6. `mypy --strict` passes on migration code
7. `ruff check` passes

## Context & Constraints

- **Spec**: `kitty-specs/048-full-lifecycle-telemetry-events/spec.md`
- **Plan**: `kitty-specs/048-full-lifecycle-telemetry-events/plan.md`
- **Constitution**: `.kittify/memory/constitution.md`
- **Template source location**: `src/specify_cli/missions/software-dev/command-templates/` — these are the SOURCE files to edit (per CLAUDE.md)
- **Agent directories**: 12 agents total, but only configured agents are processed (per CLAUDE.md agent management)
- **Migration helper**: `from specify_cli.upgrade.migrations.m_0_9_1_complete_lane_migration import get_agent_dirs_for_project`
- **DO NOT edit**: `.claude/commands/`, `.amazonq/prompts/`, etc. — these are generated copies

## Subtasks & Detailed Guidance

### Subtask T009 – Update specify.md template

**Purpose**: Add telemetry emission as the final step of the specify workflow.

**Steps**:

1. Open `src/specify_cli/missions/software-dev/command-templates/specify.md`
2. Find the final reporting step (step 9 in the current template, "Report completion")
3. Add a new section AFTER the reporting step, before any closing notes:

```markdown
## Telemetry (final step)

After completing all steps above and reporting to the user, emit a telemetry event to record this specification phase:

\```bash
spec-kitty agent telemetry emit \
  --feature <feature-slug> \
  --role specifier \
  --agent <your-agent-name> \
  --model <your-model-id>
\```

If your agent runtime provides usage metrics, include them:
- `--input-tokens <count>` — total input tokens consumed during this phase
- `--output-tokens <count>` — total output tokens generated during this phase
- `--cost-usd <amount>` — total cost in USD for this phase
- `--duration-ms <milliseconds>` — duration of this phase

This event is fire-and-forget. If the command fails, continue normally — telemetry failures never block the workflow.
```

4. Replace `<feature-slug>` with the appropriate template variable or instruction to use the feature slug from the create-feature output

**Files**:

- `src/specify_cli/missions/software-dev/command-templates/specify.md` (modify, add ~20 lines)

**Notes**:

- Keep consistent formatting with the rest of the template
- The telemetry section should be clearly labeled and easy to find
- Include the fire-and-forget disclaimer

---

### Subtask T010 – Update plan.md template

**Purpose**: Add telemetry emission as the final step of the planning workflow.

**Steps**:

1. Open `src/specify_cli/missions/software-dev/command-templates/plan.md`
2. Find the "STOP and report" section (step 6 in the current template)
3. Add the telemetry section BEFORE the stop point but AFTER the reporting:

```markdown
## Telemetry (before stopping)

Emit a telemetry event to record this planning phase:

\```bash
spec-kitty agent telemetry emit \
  --feature <feature-slug> \
  --role planner \
  --agent <your-agent-name> \
  --model <your-model-id>
\```

Include `--input-tokens`, `--output-tokens`, `--cost-usd`, `--duration-ms` if your agent runtime provides usage metrics. This is fire-and-forget — failures never block the workflow.
```

**Files**:

- `src/specify_cli/missions/software-dev/command-templates/plan.md` (modify, add ~15 lines)

---

### Subtask T011 – Update tasks.md template

**Purpose**: Add telemetry emission as the final step of the task generation workflow.

**Steps**:

1. Open `src/specify_cli/missions/software-dev/command-templates/tasks.md`
2. Find the "Report" section (step 8)
3. Add telemetry section after the report but before closing:

```markdown
## Telemetry (final step)

Emit a telemetry event to record this task generation phase:

\```bash
spec-kitty agent telemetry emit \
  --feature <feature-slug> \
  --role planner \
  --agent <your-agent-name> \
  --model <your-model-id>
\```

Note: Task generation uses `--role planner` because it's part of the planning lifecycle.

Include `--input-tokens`, `--output-tokens`, `--cost-usd`, `--duration-ms` if your agent runtime provides usage metrics. This is fire-and-forget.
```

**Files**:

- `src/specify_cli/missions/software-dev/command-templates/tasks.md` (modify, add ~15 lines)

---

### Subtask T012 – Update review.md template

**Purpose**: Add telemetry emission as the final step of the review workflow. This supplements the existing `move-task` emission.

**Steps**:

1. Open `src/specify_cli/missions/software-dev/command-templates/review.md`
2. Find the final step after the review decision is made
3. Add telemetry section:

```markdown
## Telemetry (final step)

Emit a telemetry event to record this review phase:

\```bash
spec-kitty agent telemetry emit \
  --feature <feature-slug> \
  --role reviewer \
  --wp-id <WP-ID> \
  --agent <your-agent-name> \
  --model <your-model-id>
\```

Note: Include `--wp-id` to associate this review event with the specific work package. The `move-task` command also emits a telemetry event — this is intentional (captures both the task transition and the review phase completion).

Include `--input-tokens`, `--output-tokens`, `--cost-usd`, `--duration-ms` if available. This is fire-and-forget.
```

**Files**:

- `src/specify_cli/missions/software-dev/command-templates/review.md` (modify, add ~15 lines)

---

### Subtask T013 – Update merge.md template

**Purpose**: Add telemetry emission as the final step of the merge workflow.

**Steps**:

1. Open `src/specify_cli/missions/software-dev/command-templates/merge.md`
2. Find the final reporting/completion section
3. Add telemetry section:

```markdown
## Telemetry (final step)

Emit a telemetry event to record this merge phase:

\```bash
spec-kitty agent telemetry emit \
  --feature <feature-slug> \
  --role merger \
  --agent <your-agent-name> \
  --model <your-model-id>
\```

Include `--input-tokens`, `--output-tokens`, `--cost-usd`, `--duration-ms` if available. This is fire-and-forget.
```

**Files**:

- `src/specify_cli/missions/software-dev/command-templates/merge.md` (modify, add ~15 lines)

---

### Subtask T014 – Create migration for template propagation

**Purpose**: Propagate the updated templates to all configured agents so the telemetry emit step is available in all agent slash commands.

**Steps**:

1. Determine next migration version number by checking existing migrations in `src/specify_cli/upgrade/migrations/`
2. Create new migration file following naming convention (e.g., `m_X_Y_Z_telemetry_emit_templates.py`)
3. Import the config-aware helper:

   ```python
   from .m_0_9_1_complete_lane_migration import get_agent_dirs_for_project
   ```

4. Migration logic:
   - Get configured agent dirs via `get_agent_dirs_for_project(project_path)`
   - For each configured agent:
     - Skip if directory doesn't exist (`if not agent_dir.exists(): continue`)
     - Copy updated templates from `src/specify_cli/missions/software-dev/command-templates/` to agent directory
     - Only copy the 5 modified templates (specify, plan, tasks, review, merge)
5. Follow the migration class pattern used by existing migrations (check the latest one for the interface)

**Files**:

- `src/specify_cli/upgrade/migrations/m_X_Y_Z_telemetry_emit_templates.py` (new, ~80 lines)

**Notes**:

- DO NOT create agent directories that don't exist — respect user deletions
- DO NOT hardcode `AGENT_DIRS` — import from `m_0_9_1`
- Use `importlib.resources` to locate source templates (same pattern as existing migrations)
- Template file naming convention: the templates are copied with `spec-kitty.` prefix (e.g., `spec-kitty.specify.md`)

---

### Subtask T015 – Write migration tests

**Purpose**: Verify the migration correctly propagates templates to configured agents and skips unconfigured ones.

**Steps**:

1. Create test file following existing migration test patterns
2. Test cases:
   - **Config-aware**: Migration only processes agents in config.yaml
   - **Skip missing directories**: Unconfigured agent dirs not recreated
   - **Template content**: Updated templates contain the telemetry section
   - **Parametrized across agents**: Test at least claude, codex, opencode (per CLAUDE.md)
   - **Legacy project**: No config.yaml → falls back to all agents
   - **Idempotent**: Running migration twice produces same result

3. Use `tmp_path` fixture for isolated project directories
4. Create minimal config.yaml and agent directories for testing

**Files**:

- `tests/specify_cli/upgrade/test_telemetry_template_migration.py` (new, ~120 lines)

**Notes**:

- Follow existing migration test patterns (check `tests/specify_cli/test_agent_config_migration.py` for reference)
- Use `@pytest.mark.parametrize` for agent type variations

---

## Test Strategy

Constitution requires ATDD + TDD. Implementation order:

1. Write migration tests first (T015) — must fail (RED)
2. Write template updates (T009-T013)
3. Implement migration (T014) — tests should pass (GREEN)
4. Refactor if needed

**Commands**:

```bash
pytest tests/specify_cli/upgrade/test_telemetry_template_migration.py -v
mypy --strict src/specify_cli/upgrade/migrations/m_X_Y_Z_telemetry_emit_templates.py
ruff check src/specify_cli/upgrade/migrations/ src/specify_cli/missions/
```

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Template changes break existing template parsing | Only add new section at the end — no structural changes |
| Migration version conflicts with other in-flight features | Check latest version number immediately before creating file |
| Large template files hard to edit precisely | Use targeted edits (append section) rather than rewriting entire file |
| Agent directory naming inconsistencies | Use `AGENT_DIRS` mapping from `m_0_9_1` for correct dir/subdir pairs |

## Review Guidance

- Verify all 5 templates have the telemetry section with correct `--role` value
- Verify migration uses `get_agent_dirs_for_project()` (not hardcoded AGENT_DIRS)
- Verify migration skips missing directories (`if not exists: continue`)
- Verify migration tests are parametrized across agent types
- Check template formatting is consistent with surrounding content
- Run full test suite: `pytest tests/ -v` to check for regressions

## Activity Log

- 2026-02-16T14:16:58Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-02-16T15:46:21Z – unknown – shell_pid=834031 – lane=for_review – All 5 templates updated with telemetry section, migration created, 20 tests passing
- 2026-02-16T15:49:59Z – claude – shell_pid=839063 – lane=doing – Started review via workflow command
- 2026-02-16T15:51:02Z – claude – shell_pid=839063 – lane=done – Review passed
