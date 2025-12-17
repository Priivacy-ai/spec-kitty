---
work_package_id: "WP04"
subtasks: ["T054", "T055", "T056", "T057", "T058", "T059", "T060", "T061", "T062", "T063", "T064", "T065", "T066", "T067", "T068", "T069"]
title: "Agent Context Management"
phase: "Phase 4 - Context Commands (Stream C)"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "79328"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-17T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Agent Context Management

## Objectives & Success Criteria

**Goal**: Migrate agent context update bash script (600 lines) to Python for updating CLAUDE.md, GEMINI.md, etc. with tech stack from plan.md.

**Success Criteria**:
- `spec-kitty agent update-context --json` updates agent context files
- Tech stack extracted from plan.md Technical Context section
- Manual additions between `<!-- MANUAL ADDITIONS -->` markers preserved
- All 12 agent types supported (Claude, Gemini, Copilot, Cursor, Windsurf, etc.)
- 90%+ test coverage for `context.py` and `agent_context.py`

---

## Context & Constraints

**Prerequisites**: WP01 complete ✅
**Stream Assignment**: Stream C (Agent Gamma) - Parallel with WP02, WP03, WP05
**Files Owned**: `src/specify_cli/cli/commands/agent/context.py`, `src/specify_cli/core/agent_context.py`
**Bash script to replace**: `.kittify/scripts/bash/update-agent-context.sh` (600 lines)

---

## Subtasks & Detailed Guidance

### T054-T058 – Create agent_context.py module with utilities

**T054**: Create `src/specify_cli/core/agent_context.py` module

**T055**: Implement `parse_plan_for_tech_stack(plan_path)`:
```python
def parse_plan_for_tech_stack(plan_path: Path) -> dict:
    """Extract tech stack from plan.md ## Technical Context section."""
    with open(plan_path) as f:
        content = f.read()
    
    # Find ## Technical Context section
    # Parse language, dependencies, testing info
    # Return structured dict
    
    return {
        "language": "Python 3.11+",
        "dependencies": ["Typer", "Rich", "pathlib"],
        "testing": "pytest",
        # ...
    }
```

**T056**: Implement `update_agent_context(agent_type, tech_stack, feature_dir)`:
- Read agent context file (e.g., `CLAUDE.md`)
- Update Active Technologies section
- Update Recent Changes section
- Call `preserve_manual_additions()` before writing

**T057**: Implement `preserve_manual_additions(content, markers)`:
```python
def preserve_manual_additions(old_content: str, new_content: str) -> str:
    """Preserve content between <!-- MANUAL ADDITIONS START/END --> markers."""
    # Extract manual section from old_content
    # Inject into new_content at same markers
    # Return merged content
```

**T058**: Support all 12 agent types:
- Claude (CLAUDE.md)
- Gemini (GEMINI.md)
- Copilot (COPILOT.md)
- Cursor (CURSOR.md)
- Windsurf (WINDSURF.md)
- ... (7 more agent types)

---

### T059-T062 – Implement update-context command

**T059**: Create command in `src/specify_cli/cli/commands/agent/context.py`:
```python
@app.command(name="update-context")
def update_context(
    agent_type: Annotated[str, typer.Option("--agent-type")] = "claude",
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Update agent context file with tech stack from plan.md."""
    try:
        repo_root = locate_project_root()
        feature_dir = # detect feature dir
        
        plan_path = feature_dir / "plan.md"
        tech_stack = parse_plan_for_tech_stack(plan_path)
        
        update_agent_context(agent_type, tech_stack, repo_root)
        
        if json_output:
            print(json.dumps({"result": "success", "agent_type": agent_type}))
        else:
            console.print(f"[green]✓[/green] Updated {agent_type.upper()}.md")
    except Exception as e:
        # Error handling...
```

**T060-T062**: Add flags and dual output mode

---

### T063-T069 – Testing

**T063-T066**: Unit tests for all utilities:
- Test tech stack parsing from various plan.md formats
- Test manual additions preservation (edge cases: missing markers, nested content)
- Test context updates for all 12 agent types
- Test command with all flags

**T067-T068**: Integration tests:
- Update context for multiple agent types
- Preserve manual additions across multiple updates

**T069**: Verify 90%+ coverage

---

## Definition of Done Checklist

- [ ] All utilities implemented (T054-T058)
- [ ] update-context command implemented (T059-T062)
- [ ] Unit tests passing (T063-T066)
- [ ] Integration tests passing (T067-T068)
- [ ] 90%+ coverage achieved (T069)
- [ ] Manual additions preserved correctly
- [ ] All 12 agent types supported

---

## Activity Log

- 2025-12-17T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-12-17T22:42:22Z – claude – shell_pid=79328 – lane=doing – Started implementation of agent context management
