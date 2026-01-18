---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "Foundation & Config"
phase: "Phase 0 - Foundation"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "43211"
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-18T16:21:51Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Foundation & Config

## Objectives & Success Criteria

Establish the orchestrator package structure and configuration system that all other components depend on.

**Success Criteria**:
- Orchestrator package exists at `src/specify_cli/orchestrator/`
- All enums from data-model.md implemented
- OrchestratorConfig and AgentConfig dataclasses implemented
- Config loads from `.kittify/agents.yaml` with validation
- Default config generates for installed agents when no config exists

## Context & Constraints

**Reference Documents**:
- [spec.md](../spec.md) - FR-016, FR-017, FR-018 (configuration requirements)
- [plan.md](../plan.md) - Project structure, technical context
- [data-model.md](../data-model.md) - Entity schemas, validation rules, file schemas

**Constraints**:
- Use Python 3.11+ features (dataclasses, `|` union syntax)
- Use `ruamel.yaml` for YAML parsing (existing codebase convention)
- Follow existing spec-kitty code patterns

**Implementation Command**:
```bash
spec-kitty implement WP01
```

## Subtasks & Detailed Guidance

### Subtask T001 – Create orchestrator package structure

**Purpose**: Establish the directory structure and `__init__.py` files for the new orchestrator package.

**Steps**:
1. Create directory: `src/specify_cli/orchestrator/`
2. Create `__init__.py` with public API exports
3. Create `agents/` subdirectory with its own `__init__.py`
4. Create placeholder files for all modules listed in plan.md

**Files**:
```
src/specify_cli/orchestrator/
├── __init__.py          # Export main classes
├── scheduler.py         # Placeholder
├── executor.py          # Placeholder
├── monitor.py           # Placeholder
├── state.py             # Placeholder
├── config.py            # Implemented in T004
└── agents/
    ├── __init__.py      # Export invokers
    └── base.py          # Implemented in WP02
```

**Notes**:
- Use docstrings in `__init__.py` to document the package
- Placeholders can be empty with just a docstring

---

### Subtask T002 – Implement enums

**Purpose**: Define the status enums used throughout orchestration.

**Steps**:
1. Create enums matching data-model.md exactly:
   - `OrchestrationStatus`: PENDING, RUNNING, PAUSED, COMPLETED, FAILED
   - `WPStatus`: PENDING, READY, IMPLEMENTATION, REVIEW, COMPLETED, FAILED
   - `FallbackStrategy`: NEXT_IN_LIST, SAME_AGENT, FAIL
2. Use `str` as mixin for JSON serialization: `class OrchestrationStatus(str, Enum)`

**Files**:
- `src/specify_cli/orchestrator/config.py` (or a separate `enums.py`)

**Example**:
```python
from enum import Enum

class OrchestrationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
```

**Parallel?**: Yes - can proceed alongside T003

---

### Subtask T003 – Implement config dataclasses

**Purpose**: Define dataclasses for agent and orchestrator configuration.

**Steps**:
1. Implement `AgentConfig` dataclass:
   ```python
   @dataclass
   class AgentConfig:
       agent_id: str
       enabled: bool
       roles: list[str]
       priority: int
       max_concurrent: int
       timeout_seconds: int
   ```

2. Implement `OrchestratorConfig` dataclass:
   ```python
   @dataclass
   class OrchestratorConfig:
       version: str
       defaults: dict[str, list[str]]
       agents: dict[str, AgentConfig]
       fallback_strategy: FallbackStrategy
       max_retries: int
       single_agent_mode: bool
       single_agent: str | None
       global_concurrency: int
       global_timeout: int
   ```

**Files**:
- `src/specify_cli/orchestrator/config.py`

**Parallel?**: Yes - can proceed alongside T002

---

### Subtask T004 – Implement config.py with YAML parsing and validation

**Purpose**: Parse `.kittify/agents.yaml` into OrchestratorConfig with validation.

**Steps**:
1. Implement `load_config(path: Path) -> OrchestratorConfig`:
   - Read YAML file using `ruamel.yaml`
   - Parse into OrchestratorConfig dataclass
   - Apply validation rules from data-model.md

2. Implement validation:
   - All agent IDs in `defaults` must exist in `agents`
   - If `single_agent_mode.enabled`, `single_agent_mode.agent` must be set and enabled
   - `max_retries` >= 0
   - `global_concurrency` >= 1

3. Raise `ConfigValidationError` with clear messages on failures

**Files**:
- `src/specify_cli/orchestrator/config.py`

**Example**:
```python
def load_config(config_path: Path) -> OrchestratorConfig:
    """Load and validate orchestrator configuration."""
    if not config_path.exists():
        return generate_default_config()

    yaml = YAML()
    with open(config_path) as f:
        data = yaml.load(f)

    config = parse_config(data)
    validate_config(config)
    return config
```

---

### Subtask T005 – Implement default config generation

**Purpose**: Generate sensible defaults when no `agents.yaml` exists.

**Steps**:
1. Implement `generate_default_config() -> OrchestratorConfig`:
   - Detect installed agents using `shutil.which()`
   - Order by default priority: claude > codex > copilot > gemini > qwen > opencode > kilocode > augment > cursor
   - Set reasonable defaults:
     - `max_concurrent`: 2 per agent
     - `timeout_seconds`: 600 (10 minutes)
     - `global_concurrency`: 5
     - `fallback_strategy`: NEXT_IN_LIST
     - `max_retries`: 3

2. Agent detection order and CLI commands:
   ```python
   AGENT_COMMANDS = {
       "claude-code": "claude",
       "codex": "codex",
       "copilot": "copilot",
       "gemini": "gemini",
       "qwen": "qwen",
       "opencode": "opencode",
       "kilocode": "kilocode",
       "augment": "auggie",
       "cursor": "cursor",
   }
   ```

**Files**:
- `src/specify_cli/orchestrator/config.py`

**Notes**:
- If no agents installed, raise clear error with installation instructions
- Log which agents were detected

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| YAML parsing errors | Clear error messages with line numbers |
| No agents installed | Helpful error with installation links |
| Config validation edge cases | Comprehensive validation with specific error messages |

## Definition of Done Checklist

- [ ] Orchestrator package structure exists
- [ ] All enums implemented and match data-model.md
- [ ] AgentConfig and OrchestratorConfig dataclasses implemented
- [ ] `load_config()` parses YAML correctly
- [ ] Validation rules enforced with clear error messages
- [ ] `generate_default_config()` works with installed agents
- [ ] Public API exported from `__init__.py`

## Review Guidance

- Verify enum values match data-model.md exactly
- Check dataclass fields match schema
- Test config loading with valid and invalid YAML
- Verify default generation detects real installed agents
- Check error messages are actionable

## Activity Log

- 2026-01-18T16:21:51Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-18T17:38:27Z – claude-opus – shell_pid=42425 – lane=doing – Started implementation via workflow command
- 2026-01-18T17:41:32Z – claude-opus – shell_pid=42425 – lane=for_review – Ready for review: Foundation package with enums, config dataclasses, YAML parsing/validation, and default config generation for 9 agents
- 2026-01-18T17:43:57Z – claude-opus – shell_pid=43211 – lane=doing – Started review via workflow command
