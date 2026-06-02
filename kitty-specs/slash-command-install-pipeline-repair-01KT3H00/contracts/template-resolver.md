# Contract: Template Resolver

**Module**: `src/specify_cli/runtime/agent_commands.py`
**Function**: `_get_command_templates_dir()`

## Pre-fix (broken)

- Returns `Path | None`
- Searches two stale locations that no longer exist
- Returns `None` when both miss → caller aborts silently

## Post-fix (this mission)

- Returns `Path` (never `None`)
- Resolution: `Path(doctrine.__file__).parent / "missions" / "mission-steps" / "software-dev"`
- Raises `FileNotFoundError` if the doctrine package is absent (should never happen in any supported install)

## Caller contract (`_sync_agent_commands`)

```
templates_dir: Path  # always a real directory post-fix
for step_dir in sorted(templates_dir.iterdir()):
    if not step_dir.is_dir():
        continue
    command = step_dir.name
    if command not in PROMPT_DRIVEN_COMMANDS:
        continue
    template_path = step_dir / "prompt.md"
    if not template_path.exists():
        continue  # graceful skip
    # render and write
```

## Invariants

- The returned path always contains at least the 8 `PROMPT_DRIVEN_COMMANDS` as subdirectories with `prompt.md`.
- The resolution is package-relative, not project-relative — it works identically in editable and wheel installs.
- No mutable state; calling the function twice returns the same path.
