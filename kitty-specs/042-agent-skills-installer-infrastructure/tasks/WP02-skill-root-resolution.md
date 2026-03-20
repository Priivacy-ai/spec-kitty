---
work_package_id: WP02
title: Skill Root Resolution
lane: in_progress
dependencies: [WP01]
base_branch: 042-agent-skills-installer-infrastructure-WP01
base_commit: 06eb8070106b6ece8424249f8a245949d4c4169b
created_at: '2026-03-20T16:58:22.384743+00:00'
subtasks:
- T008
- T009
- T010
- T011
- T012
phase: Phase 1 - Foundation
assignee: ''
agent: codex
shell_pid: '96492'
review_status: has_feedback
reviewed_by: Robert Douglass
review_feedback: feedback://042-agent-skills-installer-infrastructure/WP02/20260320T170636Z-e7183cd3.md
history:
- timestamp: '2026-03-20T16:29:09Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- FR-012
- NFR-002
---

# Work Package Prompt: WP02 – Skill Root Resolution

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you begin addressing feedback.

---

## Review Feedback

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

Depends on WP01 (needs `AGENT_SURFACE_CONFIG` and `DistributionClass`).

---

## Objectives & Success Criteria

1. `resolve_skill_roots()` returns the **minimum set** of project skill root directories for any agent selection and `--skills` mode.
2. Pure computation — no filesystem I/O, no side effects.
3. All four modes implemented: `auto`, `native`, `shared`, `wrappers-only`.
4. Exhaustive parametrized tests cover edge cases.
5. Passes `mypy --strict` and `ruff check`.

## Context & Constraints

- **Spec**: FR-004 through FR-012, NFR-002
- **Plan**: Section 3 (Skill Root Resolution)
- **Data model**: DistributionClass enum from WP01
- **PRD 8.2**: Distribution classes and root selection rules

## Subtasks & Detailed Guidance

### Subtask T008 – Create skills package

**Purpose**: Initialize the `src/specify_cli/skills/` package for all skill-related modules.

**Steps**:
1. Create `src/specify_cli/skills/__init__.py`
2. Add docstring: `"""Skill installation, manifest, and verification utilities."""`
3. Add public API imports (will grow as WP03/WP04 add modules):
   ```python
   from specify_cli.skills.roots import resolve_skill_roots

   __all__ = ["resolve_skill_roots"]
   ```

**Files**: `src/specify_cli/skills/__init__.py` (new, ~10 lines)

### Subtask T009 – Create roots.py with resolve_skill_roots

**Purpose**: Define the function signature and mode dispatch.

**Steps**:
1. Create `src/specify_cli/skills/roots.py`
2. Define:
   ```python
   from __future__ import annotations
   from specify_cli.core.agent_surface import AGENT_SURFACE_CONFIG, DistributionClass

   def resolve_skill_roots(
       selected_agents: list[str],
       mode: str = "auto",
   ) -> list[str]:
       """Return the minimum set of project skill root directories to create.

       Args:
           selected_agents: Agent keys selected by the user.
           mode: One of "auto", "native", "shared", "wrappers-only".

       Returns:
           Sorted list of unique directory paths relative to project root.
           Empty list if mode is "wrappers-only" or no skill-capable agents selected.

       Raises:
           ValueError: If mode is not a recognized value.
       """
   ```

**Files**: `src/specify_cli/skills/roots.py` (new, ~80 lines)

### Subtask T010 – Implement auto and shared mode logic

**Purpose**: The two most common modes — `auto` (default) and `shared`.

**Steps**:
1. Both `auto` and `shared` follow the same algorithm:
   - If any selected agent has `distribution_class == SHARED_ROOT_CAPABLE`, add `.agents/skills/` to the result set
   - For each selected agent with `distribution_class == NATIVE_ROOT_REQUIRED`, add its first skill root (e.g., `.claude/skills/`)
   - Agents with `distribution_class == WRAPPER_ONLY` contribute nothing
   - Return sorted unique list

2. Difference between `auto` and `shared`: Currently identical in Phase 0. `auto` is the default; `shared` is explicitly stated. They share the same logic path now. In future phases, `auto` may add heuristics.

**Example**:
```python
resolve_skill_roots(["claude", "codex", "opencode"], mode="auto")
# → [".agents/skills/", ".claude/skills/"]
# .agents/skills/ from codex + opencode (shared-root-capable)
# .claude/skills/ from claude (native-root-required)

resolve_skill_roots(["q"], mode="auto")
# → []
# q is wrapper-only

resolve_skill_roots(["claude"], mode="auto")
# → [".claude/skills/"]
# No shared-root agent selected, so no .agents/skills/
```

**Files**: `src/specify_cli/skills/roots.py`

### Subtask T011 – Implement native and wrappers-only modes

**Purpose**: Cover remaining distribution modes.

**Steps**:
1. **`wrappers-only`**: Always return `[]`. No skill roots.

2. **`native`**: For each selected skill-capable agent, use the vendor-native root even if the agent also supports `.agents/skills/`:
   - For `SHARED_ROOT_CAPABLE` agents: use the **second** skill root if available (vendor-native), or the first if only `.agents/skills/` (like codex which only lists `.agents/skills/`)
   - For `NATIVE_ROOT_REQUIRED` agents: use the first (only) skill root
   - For `WRAPPER_ONLY` agents: nothing
   - Return sorted unique list

   Example:
   ```python
   resolve_skill_roots(["copilot", "codex", "claude"], mode="native")
   # → [".agents/skills/", ".claude/skills/", ".github/skills/"]
   # copilot → .github/skills/ (native, second in list)
   # codex → .agents/skills/ (only root available)
   # claude → .claude/skills/ (native-required)
   ```

3. **Invalid mode**: Raise `ValueError(f"Invalid skills mode: {mode}. Must be one of: auto, native, shared, wrappers-only")`

**Files**: `src/specify_cli/skills/roots.py`

### Subtask T012 – Parametrized unit tests

**Purpose**: Exhaustive verification of all mode × agent combinations and edge cases.

**Steps**:
1. Create `tests/specify_cli/test_skills/test_roots.py`
2. Tests:

```python
# Auto mode: shared + native agents → both roots
def test_auto_mixed_agents():
    roots = resolve_skill_roots(["claude", "codex", "opencode"], mode="auto")
    assert ".agents/skills/" in roots  # codex, opencode
    assert ".claude/skills/" in roots  # claude
    assert len(roots) == 2

# Auto mode: only wrapper-only → empty
def test_auto_wrapper_only():
    assert resolve_skill_roots(["q"], mode="auto") == []

# Auto mode: only native → no shared root
def test_auto_native_only():
    roots = resolve_skill_roots(["claude", "qwen"], mode="auto")
    assert ".agents/skills/" not in roots
    assert ".claude/skills/" in roots
    assert ".qwen/skills/" in roots

# Auto mode: all 12 agents
def test_auto_all_agents():
    all_agents = list(AGENT_SURFACE_CONFIG.keys())
    roots = resolve_skill_roots(all_agents, mode="auto")
    assert ".agents/skills/" in roots
    assert ".claude/skills/" in roots
    assert ".qwen/skills/" in roots
    assert ".kilocode/skills/" in roots

# Wrappers-only: always empty
@pytest.mark.parametrize("agents", [
    ["claude"], ["codex"], ["claude", "codex", "q"], list(AGENT_SURFACE_CONFIG.keys()),
])
def test_wrappers_only_always_empty(agents):
    assert resolve_skill_roots(agents, mode="wrappers-only") == []

# Native mode: prefer vendor roots
def test_native_copilot_gets_github_root():
    roots = resolve_skill_roots(["copilot"], mode="native")
    assert ".github/skills/" in roots
    assert ".agents/skills/" not in roots

# Shared mode: same as auto
def test_shared_same_as_auto():
    agents = ["claude", "codex", "copilot"]
    assert resolve_skill_roots(agents, "shared") == resolve_skill_roots(agents, "auto")

# Empty agent list
def test_empty_agents():
    assert resolve_skill_roots([], mode="auto") == []

# Invalid mode
def test_invalid_mode_raises():
    with pytest.raises(ValueError, match="Invalid skills mode"):
        resolve_skill_roots(["claude"], mode="invalid")

# Results are sorted
def test_results_sorted():
    roots = resolve_skill_roots(["qwen", "claude", "codex"], mode="auto")
    assert roots == sorted(roots)

# No duplicates
def test_no_duplicates():
    roots = resolve_skill_roots(["codex", "copilot", "opencode"], mode="auto")
    assert len(roots) == len(set(roots))
    # All three are shared-root-capable, so only .agents/skills/ once
    assert roots.count(".agents/skills/") == 1
```

**Files**: `tests/specify_cli/test_skills/test_roots.py` (new, ~100 lines)

## Test Strategy

- Pure unit tests — no filesystem
- Parametrized across modes and agent sets
- Edge cases: empty list, all same class, invalid mode
- Run: `pytest tests/specify_cli/test_skills/test_roots.py -v`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Native mode logic for agents with only `.agents/skills/` (like codex) | Test explicitly — codex in native mode should still get `.agents/skills/` since that's its only root |
| Future modes not handled | ValueError for unknown modes catches this early |

## Review Guidance

1. Verify auto mode produces **minimum** root set (no unnecessary vendor roots for shared-capable agents).
2. Verify wrappers-only always returns empty list regardless of agent selection.
3. Verify native mode prefers vendor roots over `.agents/skills/` where available.
4. Check for duplicate roots when multiple agents share `.agents/skills/`.

## Activity Log

- 2026-03-20T16:29:09Z – system – lane=planned – Prompt created.
- 2026-03-20T16:58:22Z – coordinator – shell_pid=68466 – lane=doing – Assigned agent via workflow command
- 2026-03-20T17:01:35Z – coordinator – shell_pid=68466 – lane=for_review – Ready for review: resolve_skill_roots() implemented with all 4 modes, 28 passing tests, mypy --strict clean, ruff clean
- 2026-03-20T17:02:56Z – codex – shell_pid=77176 – lane=doing – Started review via workflow command
- 2026-03-20T17:06:37Z – codex – shell_pid=77176 – lane=planned – Moved to planned
- 2026-03-20T17:07:40Z – coordinator – shell_pid=91362 – lane=doing – Started implementation via workflow command
- 2026-03-20T17:09:31Z – coordinator – shell_pid=91362 – lane=for_review – Fixed: added type: ignore[misc] to parametrize decorator per reviewer feedback. mypy --strict now clean on all WP02 files. 28 tests passing.
- 2026-03-20T17:10:40Z – codex – shell_pid=96492 – lane=doing – Started review via workflow command
