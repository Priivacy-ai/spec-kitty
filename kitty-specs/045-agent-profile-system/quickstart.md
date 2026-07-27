# Quickstart: Agent Profile System

## For Implementers

### WP05 — Doctrine Wheel Packaging

```bash
# Test-first: write wheel content verification test
pytest tests/doctrine/test_wheel_packaging.py -v  # (fails — no pyproject.toml yet)

# Create src/doctrine/pyproject.toml
# Update root pyproject.toml to add doctrine dependency
# Verify: build wheel, install in isolated venv, import doctrine
```

### WP08 — ToolConfig Upgrade Migration

```bash
# Test-first: write migration test with agents→tools key rename
pytest tests/specify_cli/upgrade/test_tool_config_migration.py -v

# Create migration in src/specify_cli/upgrade/migrations/
# Update load_tool_config() for backward-compat fallback
```

### WP09 — CI & Test Alignment

```bash
# Verify doctrine tests run in CI
pytest tests/doctrine/ -v

# Add wheel smoke test
pytest tests/doctrine/test_package_smoke.py -v
```

### WP10 — Shipped Directives

```bash
# Test-first: write consistency test
pytest tests/doctrine/test_directive_consistency.py -v  # (fails — directives missing)

# Create 19 directive YAML files following directive.schema.yaml format
# Run consistency test until green
```

### WP11 — Agent Profile Interview

```bash
# Test-first: write interview flow tests
pytest tests/specify_cli/cli/commands/agent/test_profile_interview.py -v

# Implement interview following constitution/interview.py pattern
```

### WP12 — Agent Init CLI

```bash
# Test-first: write init command tests
pytest tests/specify_cli/cli/commands/agent/test_profile_init.py -v

# Implement init: resolve profile → detect tool → generate context fragment
```

### WP13 — Structure Templates

```bash
# Test-first: write template presence tests
pytest tests/doctrine/test_structure_templates.py -v

# Adapt REPO_MAP.md and SURFACES.md from doctrine_ref
# Add init integration
```

### WP14 — Mission Schema Integration

```bash
# Test-first: write schema validation tests with agent-profile field
pytest tests/doctrine/test_mission_schema.py -v

# Update mission.schema.yaml and mission-runtime format
```

### WP15 — Profile Inheritance Resolution

```bash
# Test-first: write resolve_profile() tests
pytest tests/doctrine/test_profile_inheritance.py -v

# Implement resolve_profile() in repository.py
# Update find_best_match() to use resolved profiles
```

## Parallelization Guide

```
Sequential:  WP05 → WP10 → WP11 → WP12  (critical path: 4 steps)
Parallel:    After WP05, launch WP08/WP09/WP10/WP13/WP14/WP15 simultaneously
```

## Key Files to Touch

| WP | Primary Files |
|----|---------------|
| WP05 | `src/doctrine/pyproject.toml` (new), root `pyproject.toml` |
| WP08 | `src/specify_cli/upgrade/migrations/m_*_tool_config.py` (new), `src/specify_cli/core/tool_config.py` |
| WP09 | CI config, `tests/doctrine/test_package_smoke.py` (new) |
| WP10 | `src/doctrine/directives/*.directive.yaml` (18 new), `tests/doctrine/test_directive_consistency.py` (new) |
| WP11 | `src/specify_cli/cli/commands/agent/profile.py`, `tests/specify_cli/cli/commands/agent/test_profile_interview.py` (new) |
| WP12 | `src/specify_cli/cli/commands/agent/profile.py`, `tests/specify_cli/cli/commands/agent/test_profile_init.py` (new) |
| WP13 | `src/doctrine/templates/structure/REPO_MAP.md` (new), `SURFACES.md` (new) |
| WP14 | `src/doctrine/schemas/mission.schema.yaml` |
| WP15 | `src/doctrine/agent_profiles/repository.py`, `tests/doctrine/test_profile_inheritance.py` (new) |
