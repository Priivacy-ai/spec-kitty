---
work_package_id: WP02
title: Introduce AgentAssignment & WPMetadata.resolved_agent()
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
history: []
authoritative_surface: src/specify_cli/status/
execution_mode: code_change
owned_files:
- src/specify_cli/status/models.py
- src/specify_cli/tasks_support.py
- tests/specify_cli/status/test_agent_assignment.py
tags: []
agent: "claude:sonnet:reviewer:reviewer"
shell_pid: "1552"
---

# WP02: Introduce AgentAssignment & WPMetadata.resolved_agent()

**Objective**: Define `AgentAssignment` as a frozen dataclass and implement `WPMetadata.resolved_agent()` to unify legacy agent coercion logic. This enables WP04 (workflow.py migration) and other consumers to access resolved agent metadata without duplicating fallback logic.

---

## Context

Currently, consumers manually coerce agent metadata with scattered fallback logic:
```python
if isinstance(wp.agent, str):
    tool = wp.agent
    model = wp.model or "unknown-model"
elif isinstance(wp.agent, dict):
    tool = wp.agent.get("tool", "unknown")
    model = wp.agent.get("model", wp.model or "unknown-model")
else:
    tool = "unknown"
    model = wp.model or "unknown-model"
```

This pattern is error-prone and duplicated. By centralizing it in `WPMetadata.resolved_agent()` and returning a typed `AgentAssignment` value object, we:
- Ensure consistent fallback behavior across all consumers
- Make agent resolution testable as a unit
- Enable mypy to catch missing fields statically

**Design Decision**: `AgentAssignment` is a frozen dataclass (immutable, safe to share); `resolved_agent()` implements a deterministic fallback order: direct assignment → model field → agent_profile field → role field, with sensible defaults for all missing values.

---

## Detailed Guidance

### T004: Define AgentAssignment Frozen Dataclass

**Purpose**: Create a clean, immutable value object representing resolved agent assignment.

**Steps**:
1. Locate `src/specify_cli/status/models.py` (or create if missing).
2. Add the `AgentAssignment` dataclass:
   ```python
   from dataclasses import dataclass
   from typing import Optional

   @dataclass(frozen=True)
   class AgentAssignment:
       """Resolved agent assignment with complete context.
       
       Represents the fully-resolved agent assigned to a work package,
       including the tool (AI agent type), model, optional profile ID, and role.
       
       This value object is the output of legacy coercion and fallback resolution
       from WPMetadata.resolved_agent(). It provides a clean, typed interface for
       consumers to access agent assignment context.
       
       Attributes:
           tool: AI agent identifier (e.g., 'claude', 'copilot', 'gemini', 'cursor').
           model: Model identifier (e.g., 'claude-opus-4-6', 'gpt-4-turbo').
           profile_id: Optional profile identifier for agent configuration override.
           role: Optional role for this assignment (e.g., 'reviewer', 'implementer').
       
       Example:
           >>> assignment = wp_metadata.resolved_agent()
           >>> print(assignment.tool)  # 'claude'
           >>> print(assignment.model)  # 'claude-opus-4-6'
       """
       tool: str
       model: str
       profile_id: Optional[str] = None
       role: Optional[str] = None
   ```
3. Verify dataclass compiles and has correct type hints.
4. Add import if not already present: `from dataclasses import dataclass`

**Validation**: Dataclass is frozen, all fields have correct types, docstring is clear.

---

### T005: Implement WPMetadata.resolved_agent() Method

**Purpose**: Implement the fallback resolution algorithm in `WPMetadata`.

**Steps**:
1. Locate `WPMetadata` class in `src/specify_cli/tasks_support.py` (or wherever it lives in the codebase).
2. Add the `resolved_agent()` method:
   ```python
   def resolved_agent(self) -> AgentAssignment:
       """Resolve agent assignment with legacy coercion and fallback.
       
       Unifies agent metadata resolution across all legacy formats and fallback fields.
       Handles string agents, dict agents, None, and falls back to model, agent_profile,
       and role fields when the primary agent field is incomplete.
       
       Fallback Order:
       1. Direct AgentAssignment from agent field (if already an AgentAssignment)
       2. String agent field → tool=value, model=self.model (fallback to default)
       3. Dict agent field → tool/model/profile_id/role from dict, fallback to other fields
       4. None/missing agent → tool=default, model=self.model (fallback to default)
       5. Fallback to agent_profile field for profile_id
       6. Fallback to role field for role
       7. Return sensible defaults for missing values
       
       Returns:
           AgentAssignment with all resolved values (no None fields except optional ones)
       """
       # Step 1: If already AgentAssignment, return it
       if isinstance(self.agent, AgentAssignment):
           return self.agent
       
       # Step 2-4: Extract from string/dict/None
       tool = None
       model = None
       profile_id = None
       role_val = None
       
       if isinstance(self.agent, str):
           tool = self.agent
           model = self.model or "unknown-model"
       elif isinstance(self.agent, dict):
           tool = self.agent.get("tool")
           model = self.agent.get("model")
           profile_id = self.agent.get("profile_id")
           role_val = self.agent.get("role")
       else:
           # None or unrecognized type
           tool = "unknown"
           model = self.model or "unknown-model"
       
       # Step 5-7: Fallback and normalize
       if not profile_id:
           profile_id = getattr(self, "agent_profile", None)
       if not role_val:
           role_val = getattr(self, "role", None)
       
       if not tool:
           tool = "unknown"
       if not model:
           model = "unknown-model"
       
       return AgentAssignment(
           tool=tool,
           model=model,
           profile_id=profile_id,
           role=role_val,
       )
   ```
3. Ensure `AgentAssignment` is imported at the top of the file.
4. Handle edge cases: empty strings should be treated as missing (use `or "default"`).

**Validation**: Method compiles, handles all coercion scenarios, returns `AgentAssignment` object with sensible defaults.

---

### T006: Write Behavior Tests for resolved_agent()

**Purpose**: Verify `resolved_agent()` correctly handles all legacy input formats and fallback scenarios.

**Steps**:
1. Create or locate `tests/specify_cli/status/test_agent_assignment.py`.
2. Write parametrized tests covering all coercion scenarios:
   ```python
   @pytest.mark.parametrize("agent,model,agent_profile,role,expected_tool,expected_model,expected_profile,expected_role", [
       # String agent
       ("claude", "claude-opus-4-6", None, None, "claude", "claude-opus-4-6", None, None),
       # String agent with model fallback
       ("claude", None, None, None, "claude", "unknown-model", None, None),
       # Dict agent with all fields
       ({"tool": "copilot", "model": "gpt-4", "profile_id": "p1", "role": "reviewer"}, "ignored", "ignored", "ignored", 
        "copilot", "gpt-4", "p1", "reviewer"),
       # Dict agent with partial fields + fallback
       ({"tool": "gemini"}, "default-model", "p2", "implementer", 
        "gemini", "default-model", "p2", "implementer"),
       # None agent with fallback
       (None, "default-model", "p3", "reviewer", 
        "unknown", "default-model", "p3", "reviewer"),
       # Empty string agent (treat as None)
       ("", "model-x", None, None, 
        "unknown", "model-x", None, None),
       # AgentAssignment passthrough (if already resolved)
       (AgentAssignment("claude", "claude-opus-4-6"), "ignored", "ignored", "ignored",
        "claude", "claude-opus-4-6", None, None),
   ])
   def test_resolved_agent(agent, model, agent_profile, role, expected_tool, expected_model, expected_profile, expected_role):
       metadata = WPMetadata(agent=agent, model=model, agent_profile=agent_profile, role=role)
       assignment = metadata.resolved_agent()
       assert assignment.tool == expected_tool
       assert assignment.model == expected_model
       assert assignment.profile_id == expected_profile
       assert assignment.role == expected_role
   ```
3. Add edge case tests:
   - Empty dict agent: `{}`
   - None model with string agent fallback
   - AgentAssignment already in agent field (passthrough)
4. Verify all tests pass.

**Validation**: All scenarios tested, edge cases covered, parametrize used for clarity.

---

## Test Strategy

**Scope**: Behavior tests only. No integration tests needed for WP02.

**Coverage Target**: 100% of `resolved_agent()` method and `AgentAssignment` dataclass.

**Test Cases**:
- All coercion scenarios (string, dict, None)
- Fallback order (model field, agent_profile field, role field)
- Edge cases (empty strings, None values, already-resolved AgentAssignment)
- Type check: Returned object is frozen and has correct field types

---

## Definition of Done

- [ ] `AgentAssignment` frozen dataclass added to `src/specify_cli/status/models.py`
- [ ] `WPMetadata.resolved_agent()` method implemented with full fallback order
- [ ] All coercion scenarios tested (string, dict, None, passthrough)
- [ ] Fallback behavior verified (model field, agent_profile field, role field)
- [ ] mypy --strict passes on both files
- [ ] All new tests pass locally
- [ ] No regressions in existing WPMetadata tests

---

## Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| Fallback order not deterministic | Document fallback order in docstring; verify with tests |
| Missing field handling (empty strings) | Treat empty strings as falsy; use `or "default"` pattern |
| Type safety | mypy --strict enforces return type; AgentAssignment frozen ensures immutability |
| Consumers still use old coercion | WP04 (workflow.py) will migrate to use resolved_agent() |

---

## Reviewer Guidance

- Verify fallback order is documented and deterministic
- Check that all legacy input formats are handled correctly
- Ensure AgentAssignment is truly frozen (no mutations possible)
- Confirm tests cover all scenarios and edge cases
- Verify type hints are correct for mypy --strict

---

## Change Log

- **2026-04-09**: Initial WP for 080-wpstate-lane-consumer-strangler-fig-phase-2

## Activity Log

- 2026-04-09T15:18:39Z – claude:haiku:implementer:implementer – shell_pid=18417 – Started implementation via action command
- 2026-04-09T15:30:36Z – claude:haiku:implementer:implementer – shell_pid=18417 – Ready for review: AgentAssignment frozen dataclass and WPMetadata.resolved_agent() implemented with 27 passing behavior tests covering all coercion scenarios, fallback order, edge cases, and immutability
- 2026-04-09T15:30:57Z – claude:sonnet:reviewer:reviewer – shell_pid=55620 – Started review via action command
- 2026-04-09T15:33:09Z – claude:sonnet:reviewer:reviewer – shell_pid=55620 – Review passed: AgentAssignment frozen dataclass correctly added to models.py with proper types/docstring; WPMetadata.resolved_agent() implements deterministic fallback order (passthrough->string->dict->None) with model/agent_profile/role field fallbacks; 27 tests cover all coercion scenarios, edge cases, fallback priority, and immutability; no regressions in 235 status tests; no mypy errors in WP02 target files
- 2026-04-09T16:50:05Z – claude:sonnet:implementer:implementer – shell_pid=80049 – Started implementation via action command
- 2026-04-09T16:57:25Z – claude:sonnet:implementer:implementer – shell_pid=80049 – Ready for review: AgentAssignment frozen dataclass and WPMetadata.resolved_agent() implemented with 25 passing behavior tests covering all coercion scenarios (string, dict, None, passthrough), fallback order, immutability, and status package importability
- 2026-04-09T17:00:13Z – claude:sonnet:reviewer:reviewer – shell_pid=1552 – Started review via action command
- 2026-04-09T17:05:01Z – claude:sonnet:reviewer:reviewer – shell_pid=1552 – Review passed: AgentAssignment correct fields (tool, model, profile_id, role), full coercion coverage (passthrough/string/dict/None), exported from status/__init__.py, 25 tests call WPMetadata.resolved_agent() directly and would fail if removed
