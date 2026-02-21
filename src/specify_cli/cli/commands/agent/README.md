# Agent Command Architecture

## Principle: Agent Commands Are Thin Wrappers

Agent commands (`spec-kitty agent *`) are thin wrappers around top-level
commands, adding agent-specific UX enhancements:

1. **Auto-detection**: Auto-detect parameters from context (feature, WP)
2. **Prompt display**: Output implementation/review prompts
3. **Status updates**: Move WPs between lanes, track agent/PID
4. **Error recovery**: Auto-retry, navigation to correct worktree
5. **Dependency validation**: Validate dependencies before creating workspaces

## Pattern: Direct Import and Delegation

```python
from specify_cli.cli.commands.implement import implement as top_level_implement

@app.command(name="implement")
def implement_wrapper(...):
    # 1. Auto-detect parameters (feature, WP ID)
    # 2. Validate dependencies (CRITICAL for workspace creation)
    # 3. Add agent-specific logic (status updates, prompt display)
    # 4. Delegate to top-level command
    top_level_implement(...)
    # 5. Post-processing (display prompt, etc.)
```

## Critical: Dependency Validation

**ALWAYS** validate work package dependencies before creating workspaces!

```python
from specify_cli.core.implement_validation import (
    validate_and_resolve_base,
    validate_base_workspace_exists,
)

# Parse WP file to check dependencies
wp = locate_work_package(repo_root, feature_slug, wp_id)

# Validate dependencies (errors if single dep and no --base)
resolved_base, auto_merge = validate_and_resolve_base(
    wp_id=wp_id,
    wp_file=wp.path,
    base=base,  # User-provided or None
    feature_slug=feature_slug,
    repo_root=repo_root
)

# Validate base workspace exists (if resolved)
if resolved_base:
    validate_base_workspace_exists(resolved_base, feature_slug, repo_root)

# Now safe to create workspace
top_level_implement(wp_id=wp_id, base=resolved_base, ...)
```

**Why This Matters:**

- Without validation, WPs with dependencies branch from wrong base (main instead of WP01)
- Results in silent correctness bugs - workspace created but missing dependency code
- User discovers error only during implementation when imports fail

## Examples

### Agent Workflow Implement

**Responsibilities:**

- Auto-detect first planned WP (if not specified)
- Normalize WP ID formats (wp01 → WP01)
- **Validate dependencies** (error if single dep and no --base)
- Create workspace via top-level implement
- Display implementation prompt
- Update WP lane to "doing" with agent/PID tracking

**Implementation:**

```python
@app.command(name="implement")
def implement(wp_id: str | None, base: str | None, agent: str | None):
    # Auto-detect WP if omitted
    if not wp_id:
        wp_id = _find_first_planned_wp(repo_root, feature_slug)

    # Normalize format
    wp_id = _normalize_wp_id(wp_id)  # "wp01" → "WP01"

    # CRITICAL: Validate dependencies
    wp = locate_work_package(repo_root, feature_slug, wp_id)
    resolved_base, auto_merge = validate_and_resolve_base(
        wp_id, wp.path, base, feature_slug, repo_root
    )

    # Create workspace if needed
    if auto_merge or resolved_base or not workspace_exists:
        top_level_implement(wp_id, resolved_base, feature_slug)

    # Display prompt
    display_implement_prompt(wp_id, workspace_path)
```

### Agent Feature Accept

**Responsibilities:**

- Auto-detect feature from context
- Delegate to top-level accept command
- Map parameter names (lenient, no_commit, json_output)

**Implementation:**

```python
from specify_cli.cli.commands.accept import accept as top_level_accept

@app.command(name="accept")
def accept_feature(feature: str | None, mode: str, lenient: bool, json_output: bool):
    # Direct delegation - no complex logic needed
    top_level_accept(
        feature=feature,
        mode=mode,
        actor=None,  # Agent commands don't use --actor
        test=[],  # Agent commands don't use --test
        json_output=json_output,
        lenient=lenient,
        no_commit=no_commit,
        allow_fail=False,
    )
```

### Agent Feature Merge

**Responsibilities:**

- Auto-retry logic (navigate to latest worktree if in wrong location)
- Parameter name mapping (keep_branch → delete_branch inversion)
- Delegate to top-level merge command

**Implementation:**

```python
from specify_cli.cli.commands.merge import merge as top_level_merge

@app.command(name="merge")
def merge_feature(
    feature: str | None,
    target: str,
    strategy: str,
    push: bool,
    keep_branch: bool,
    keep_worktree: bool,
    auto_retry: bool,
):
    # Agent-specific: Auto-retry in correct worktree
    if auto_retry and not on_feature_branch():
        latest_worktree = _find_latest_feature_worktree(repo_root)
        if latest_worktree:
            # Re-run command in worktree
            subprocess.run(["spec-kitty", "agent", "feature", "merge", ...],
                         cwd=latest_worktree)
            return

    # Delegate to top-level (note parameter inversions!)
    top_level_merge(
        strategy=strategy,
        delete_branch=not keep_branch,  # INVERT: keep → delete
        remove_worktree=not keep_worktree,  # INVERT: keep → remove
        push=push,
        target_branch=target,  # Parameter name differs
        dry_run=dry_run,
        feature=feature,
        resume=False,  # Agent doesn't support resume
        abort=False,  # Agent doesn't support abort
    )
```

## Parameter Mapping Guidelines

When wrapping top-level commands, carefully map parameters:

| Agent Parameter | Top-Level Parameter | Notes |
|----------------|---------------------|-------|
| `target` | `target_branch` | Different name |
| `keep_branch` | `delete_branch` | **INVERTED** logic |
| `keep_worktree` | `remove_worktree` | **INVERTED** logic |
| `json_output` | `json_output` | Same name ✓ |
| `lenient` | `lenient` | Same name ✓ |

**Always document inversions in code comments!**

## DO NOT

- Duplicate business logic from top-level commands
- Call legacy `scripts/` code (tasks_cli.py is removed!)
- Re-implement validation/orchestration logic
- Skip dependency validation before workspace creation
- Use subprocess to call top-level commands (import and call directly!)

## DO

- Import and call top-level commands directly
- Add agent-specific UX (prompts, auto-detection, status tracking)
- Map parameter names if needed (document differences and inversions!)
- Validate dependencies **before** creating workspaces
- Handle typer.Exit gracefully (propagate, don't catch silently)

## Testing Requirements

When adding or modifying agent commands:

1. **Unit tests**: Verify parameter mapping and validation logic
2. **Integration tests**: Test full workflow (auto-detect → validate → delegate)
3. **Dependency tests**: Verify error when single dep and no --base
4. **Regression tests**: Test scenarios from bug reports

See `tests/integration/test_agent_command_wrappers.py` for examples.

## Common Pitfalls

### ❌ Skipping Dependency Validation

```python
# BAD: Creates workspace without checking dependencies
if base:
    top_level_implement(wp_id, base, feature)
# Otherwise just display prompt - NO VALIDATION!
```

**Result**: WP06 with dependency on WP04 branches from main, missing WP04's code.

### ✅ Always Validate First

```python
# GOOD: Validate before creating workspace
resolved_base, auto_merge = validate_and_resolve_base(...)
if resolved_base:
    validate_base_workspace_exists(...)
top_level_implement(wp_id, resolved_base, feature)
```

### ❌ Calling Legacy Scripts

```python
# BAD: Scripts don't exist anymore!
tasks_cli = repo_root / "scripts" / "tasks" / "tasks_cli.py"
subprocess.run([sys.executable, str(tasks_cli), "accept"])
```

### ✅ Import and Call Directly

```python
# GOOD: Direct import
from specify_cli.cli.commands.accept import accept as top_level_accept
top_level_accept(feature=feature, mode=mode, ...)
```

### ❌ Forgetting Parameter Inversions

```python
# BAD: Logic inverted!
top_level_merge(delete_branch=keep_branch)  # Wrong!
```

### ✅ Document and Invert

```python
# GOOD: Document inversion
# Note: Agent uses --keep-branch (default: False)
#       Top-level uses --delete-branch (default: True)
#       Invert the logic when mapping
top_level_merge(delete_branch=not keep_branch)  # Correct!
```

## Version History

- **0.13.4**: Created shared validation utility, fixed broken agent commands
- **0.11.0**: Introduced workspace-per-WP model, dependency tracking
- **0.10.x**: Legacy single-workspace model

## See Also

- [Dependency Validation](../../core/implement_validation.py) - Shared validation utility
- [Top-Level Implement](../implement.py) - Business logic for workspace creation
- [Top-Level Accept](../accept.py) - Acceptance workflow logic
- [Top-Level Merge](../merge.py) - Merge orchestration logic
- [Workspace-per-WP Documentation](../../../../docs/workspace-per-wp.md) - User guide
