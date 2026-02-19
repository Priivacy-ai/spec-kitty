# Quickstart: Agent Profile Domain Model

**Feature**: 047-agent-profile-domain-model

## Key Concepts

- **AgentProfile** — behavioral identity (who an agent IS): purpose, specialization, collaboration
- **ToolConfig** — tool stack availability (which IDE/CLI): claude, copilot, cursor
- These are orthogonal: a tool (claude) can operate as any agent profile (architect, implementer)

## Package Layout

```
src/doctrine/           # Domain model (zero imports from specify_cli)
  model/profile.py      # AgentProfile, value objects
  model/hierarchy.py    # SpecializationHierarchy, context matching
  model/capabilities.py # RoleCapabilities, canonical verbs
  repository/           # AgentProfileRepository
  agents/               # Shipped reference profiles (.agent.yaml)
  schema/               # JSON Schema for validation

src/specify_cli/
  orchestrator/tool_config.py  # Renamed from agent_config.py
  cli/commands/agent/profile.py  # CLI commands
```

## Common Operations

### Load profiles programmatically

```python
from doctrine.repository import AgentProfileRepository
from pathlib import Path

repo = AgentProfileRepository(
    shipped_dir=None,  # auto-detects from package
    project_dir=Path(".kittify/constitution/agents"),
)

# List all
profiles = repo.list_all()

# Get by ID
architect = repo.get("architect")

# Find by role
implementers = repo.find_by_role("implementer")

# Find best match for task context
from doctrine.model.hierarchy import TaskContext
context = TaskContext(language="python", framework="fastapi")
hierarchy = repo.get_hierarchy()
best = hierarchy.find_best_match(context)
```

### CLI commands

```bash
# List all profiles (shipped + custom)
spec-kitty agent profile list

# Show full profile details
spec-kitty agent profile show architect

# Create custom profile from template
spec-kitty agent profile create --from-template implementer

# Show hierarchy tree
spec-kitty agent profile hierarchy
```

### Profile YAML format

```yaml
# .kittify/constitution/agents/my-specialist.agent.yaml
schema_version: "1.0"
profile_id: my-specialist
name: "My Specialist"
role: implementer
capabilities: [read, write, edit, bash]
specializes_from: implementer
routing_priority: 75
max_concurrent_tasks: 5

specialization_context:
  languages: [python]
  frameworks: [django]
  file_patterns: ["**/models.py", "**/views.py"]

purpose: >
  Implement Django-specific features with deep knowledge of
  the Django ORM, middleware, and template system.

specialization:
  primary_focus: "Django web application development"
  avoidance_boundary: "Frontend JavaScript, infrastructure"

collaboration:
  canonical_verbs: [generate, refine]
  output_artifacts: [code, migration, test]
```

## Testing

```bash
# Run doctrine package tests
pytest tests/doctrine/ -v

# Run ToolConfig rename tests
pytest tests/specify_cli/orchestrator/test_tool_config.py -v

# Run CLI profile tests
pytest tests/specify_cli/cli/commands/agent/test_profile_cli.py -v

# Verify import boundary
pytest tests/test_doctrine_import_boundary.py -v

# Full suite with coverage
pytest -v --cov=src/doctrine --cov-report=term-missing
```

## Files Modified by This Feature

### New files (`src/doctrine/`)
- `src/doctrine/__init__.py`
- `src/doctrine/py.typed`
- `src/doctrine/model/__init__.py`
- `src/doctrine/model/profile.py`
- `src/doctrine/model/hierarchy.py`
- `src/doctrine/model/capabilities.py`
- `src/doctrine/repository/__init__.py`
- `src/doctrine/repository/profile_repository.py`
- `src/doctrine/schema/agent_profile.schema.json`
- `src/doctrine/_validation.py`
- `src/doctrine/agents/*.agent.yaml` (6+ reference profiles)

### New files (`src/specify_cli/`)
- `src/specify_cli/orchestrator/tool_config.py`
- `src/specify_cli/cli/commands/agent/profile.py`

### Modified files
- `pyproject.toml` — add `src/doctrine` to packages list
- `src/specify_cli/orchestrator/agent_config.py` — replaced with deprecation alias
- `src/specify_cli/cli/commands/agent/__init__.py` — register profile subcommand
- `src/specify_cli/agent_utils/directories.py` — update import
- `src/specify_cli/orchestrator/scheduler.py` — update import
- `src/specify_cli/orchestrator/monitor.py` — update import
- `src/specify_cli/orchestrator/config.py` — update import
- `src/specify_cli/orchestrator/__init__.py` — update re-exports
- `src/specify_cli/cli/commands/init.py` — update import
- `src/specify_cli/cli/commands/agent/config.py` — update import
- `src/specify_cli/upgrade/migrations/m_0_14_0_centralized_feature_detection.py` — update import
