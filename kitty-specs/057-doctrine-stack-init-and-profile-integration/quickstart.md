# Quickstart: Doctrine Stack Init and Profile Integration

**Feature**: 057-doctrine-stack-init-and-profile-integration
**Date**: 2026-03-20

## Phase Execution Order

```
Phase A (Pre-work)     →  Phase B (Core Profile)     →  Phase C (Init Doctrine)
  WP-A1: Flag rename        WP-B1: Inheritance            WP-C1: Defaults + init
  WP-A2: Glossary            WP-B2: Generic-agent          WP-C2: Profile-context migration
                             WP-B3: Workflow injection     WP-C3: Task template roles
```

**Hard rule**: Each phase must be fully reviewed, merged, and cleaned up before the next phase begins.

## Per-WP Workflow

```bash
# 1. Create worktree
spec-kitty implement WP-A1 --feature 057-doctrine-stack-init-and-profile-integration

# 2. Write acceptance tests FIRST (ATDD)
#    Derive from WP acceptance scenarios in tasks/WP-A1.md
#    Tests must FAIL before implementation

# 3. Implement using ZOMBIES TDD
#    Zero → One → Many → Boundaries → Interfaces → Exceptions → Simple

# 4. Quality gates
ruff check .
ruff format --check .
mypy src/specify_cli/cli/commands/  # (or relevant changed paths)
pytest tests/ -x

# 5. Boy Scout cleanup on touched files
#    Fix lint warnings, add type annotations to modified functions, clean dead imports

# 6. Move to review
spec-kitty agent tasks move-task WP-A1 --to for_review
```

## Key Implementation Patterns

### Flag Rename (WP-A1)

```python
# New shared utility (e.g., src/specify_cli/cli/flag_compat.py)
def resolve_mission_or_feature(
    mission: str | None,
    feature: str | None,
) -> str | None:
    if mission and feature and mission != feature:
        raise typer.BadParameter("--mission and --feature conflict")
    if feature:
        console.print("[yellow]⚠ --feature is deprecated, use --mission[/yellow]")
        return feature
    return mission

# Per command:
def my_command(
    mission: Optional[str] = typer.Option(None, "--mission", help="Mission slug"),
    feature: Optional[str] = typer.Option(None, "--feature", hidden=True),
):
    slug = resolve_mission_or_feature(mission, feature)
```

### Profile Inheritance (WP-B1)

```python
# In resolve_profile() — change list merge from replace to union:
def _merge_list_field(parent_values: list, child_values: list) -> list:
    """Union merge preserving order: parent first, then child additions."""
    seen = set()
    merged = []
    for v in parent_values + child_values:
        key = v if isinstance(v, str) else str(v)
        if key not in seen:
            seen.add(key)
            merged.append(v)
    return merged

def _apply_excluding(profile: AgentProfile) -> AgentProfile:
    """Remove excluded fields/values after merge."""
    if not profile.excluding:
        return profile
    # field-level: excluding: [directives] → clear the field
    # value-level: excluding: {directives: [DIRECTIVE_010]} → remove from list
```

### Workflow Injection (WP-B3)

```python
# In workflow.py, alongside _render_constitution_context():
def _render_profile_context(repo_root: Path, wp_frontmatter: dict) -> str:
    profile_id = wp_frontmatter.get("agent_profile", "generic-agent")
    try:
        repo = AgentProfileRepository(
            shipped_dir=_default_shipped_dir(),
            project_dir=repo_root / ".kittify" / "profiles",
        )
        profile = repo.resolve_profile(profile_id)
        return _format_identity_fragment(profile)
    except Exception:
        logger.warning("Profile not found, proceeding without specialist identity")
        return ""
```

## File Quick Reference

| WP | Primary Files | Test Files |
|----|--------------|------------|
| A1 | 16 command files + `flag_compat.py` | `test_mission_flag_rename.py` |
| A2 | `glossary/contexts/orchestration.md`, `glossary/historical-terms.md` | Glossary integrity checks |
| B1 | `repository.py`, `profile.py` | `test_profile_inheritance.py` |
| B2 | `_proposed/generic-agent.agent.yaml` | `test_generic_agent_profile.py` |
| B3 | `workflow.py` | `test_workflow_profile_injection.py` |
| C1 | `init.py`, `defaults.yaml` | `test_init_doctrine.py` |
| C2 | New migration file | Migration test |
| C3 | Mission template YAML, task gen logic | Task template test |
