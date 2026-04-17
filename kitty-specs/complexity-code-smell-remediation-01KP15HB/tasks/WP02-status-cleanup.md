---
work_package_id: WP02
title: 'Status: Complexity Reduction and Cleanup'
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-004
- FR-005
planning_base_branch: feat/complexity-debt-remediation
merge_target_branch: feat/complexity-debt-remediation
branch_strategy: Planning artifacts for this feature were generated on feat/complexity-debt-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/complexity-debt-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
agent: "codex:gpt-5.4:python-reviewer:reviewer"
shell_pid: "53183"
history:
- date: '2026-04-12'
  action: created
  author: spec-kitty.tasks
authoritative_surface: src/specify_cli/status/
execution_mode: code_change
owned_files:
- src/specify_cli/status/wp_metadata.py
- src/specify_cli/status/locking.py
- tests/specify_cli/status/test_wp_metadata.py
tags: []
---

# WP02 — Status: Complexity Reduction and Cleanup

## Objective

Reduce `resolved_agent` cyclomatic complexity from 18 to ≤ 10 by extracting named resolution
steps. Fix a bare exception chain (`raise ValueError` without `from err`). Rename
`FeatureStatusLockTimeout` to `FeatureStatusLockTimeoutError`.

**FRs**: FR-002, FR-004, FR-005
**Governing tactics**: `refactoring-extract-first-order-concept`, `refactoring-guard-clauses-before-polymorphism`, `change-apply-smallest-viable-diff`
**Procedure**: `src/doctrine/procedures/shipped/refactoring.procedure.yaml`
**Directives**: DIRECTIVE_034 (characterize before restructuring), DIRECTIVE_024 (locality)

## Branch Strategy

- **Lane**: A (second — do not start until WP01 is merged)
- **Planning base / merge target**: `feat/complexity-debt-remediation`
- **Worktree**: Same Lane A worktree as WP01 (after WP01 merge, rebase the lane worktree)
- **Implementation command**: `spec-kitty agent action implement WP02 --agent <name>`

**Before starting**: Verify WP01 is merged: `git log feat/complexity-debt-remediation --oneline | head -5`.

## Context

`resolved_agent` in `WPMetadata` handles four distinct input shapes for the `agent` field:
already-an-`AgentAssignment`, a string, a dict, and `None`. All four paths share 7 fallback
steps inlined in the same function body, creating CC=18. The fix is to extract each input shape
into a named helper that returns a partial `AgentAssignment`, then compose in a clean top-level
function.

The exception chain fix (`raise ... from err`) is a one-line correction that preserves the
original exception as the `__cause__` for debugging.

`FeatureStatusLockTimeout` is a naming convention violation — Python convention for exception
classes is the `Error` suffix. Only 2 files reference it.

## Subtask T008 — Characterization tests for `resolved_agent`

**Purpose**: Lock existing behaviour before restructuring (DIRECTIVE_034).

**File**: `tests/specify_cli/status/test_wp_metadata.py`

**Required test coverage**: All 4 input shapes of `WPMetadata.agent` field:

```python
# Shape 1: agent is already AgentAssignment
def test_resolved_agent_when_already_agent_assignment():
    wp = WPMetadata(work_package_id="WP01", agent=AgentAssignment(tool="claude", model="sonnet"))
    result = wp.resolved_agent()
    assert result.tool == "claude"
    assert result.model == "sonnet"

# Shape 2: agent is a non-empty string
def test_resolved_agent_when_string():
    wp = WPMetadata(work_package_id="WP01", agent="claude", model="opus")
    result = wp.resolved_agent()
    assert result.tool == "claude"
    assert result.model == "opus"

# Shape 3: agent is a dict
def test_resolved_agent_when_dict():
    wp = WPMetadata(work_package_id="WP01", agent={"tool": "cursor", "model": "gpt-4o", "profile_id": "arch"})
    result = wp.resolved_agent()
    assert result.tool == "cursor"
    assert result.model == "gpt-4o"
    assert result.profile_id == "arch"

# Shape 4: agent is None — fallbacks to agent_profile, role, model
def test_resolved_agent_when_none_uses_fallbacks():
    wp = WPMetadata(work_package_id="WP01", agent=None, model="haiku", agent_profile="architect", role="reviewer")
    result = wp.resolved_agent()
    assert result.tool == "unknown"
    assert result.model == "haiku"
    assert result.profile_id == "architect"
    assert result.role == "reviewer"
```

Add additional edge cases:
- `agent={}` (empty dict) — verifies fallback to model/profile
- `agent=""` (empty string) — verifies fallback to `tool="unknown"`

Run: `pytest tests/specify_cli/status/test_wp_metadata.py -x` — all tests must pass against
the **unmodified** `resolved_agent` before proceeding.

---

## Subtask T009 — Decompose `resolved_agent` (CC=18 → ≤ 10)

**Purpose**: Extract each input-shape handler into a named helper function.

**File**: `src/specify_cli/status/wp_metadata.py`

**Current structure** (see lines 212–270): One large function with 4 `isinstance` branches
and 7 shared fallback steps mixed with extraction logic.

**Target structure**:

```python
def _resolve_agent_from_assignment(agent: AgentAssignment, ...) -> AgentAssignment:
    """Input shape: already an AgentAssignment — return as-is."""
    return agent

def _resolve_agent_from_string(tool: str, model: str | None, ...) -> AgentAssignment:
    """Input shape: agent is a non-empty string."""
    return AgentAssignment(
        tool=tool,
        model=model or "unknown-model",
        profile_id=...,  # from fallback
        role=...,         # from fallback
    )

def _resolve_agent_from_dict(d: dict, ...) -> AgentAssignment:
    """Input shape: agent is a dict with optional tool/model/profile_id/role."""
    tool = d.get("tool") or "unknown"
    model = d.get("model") or None
    profile_id = d.get("profile_id") or None
    role_val = d.get("role") or None
    return AgentAssignment(
        tool=tool,
        model=model or ...,
        profile_id=profile_id or ...,
        role=role_val or ...,
    )

def _resolve_agent_fallback(model: str | None, ...) -> AgentAssignment:
    """Input shape: agent is None, empty string, or unrecognized — use model/profile/role fields."""
    return AgentAssignment(
        tool="unknown",
        model=model or "unknown-model",
        profile_id=...,
        role=...,
    )

def resolved_agent(self) -> AgentAssignment:
    """Top-level dispatcher — delegates to per-shape helpers."""
    if isinstance(self.agent, AgentAssignment):
        return _resolve_agent_from_assignment(self.agent)
    if isinstance(self.agent, str) and self.agent:
        return _resolve_agent_from_string(self.agent, self.model, ...)
    if isinstance(self.agent, dict):
        return _resolve_agent_from_dict(self.agent, ...)
    return _resolve_agent_fallback(self.model, ...)
```

**Steps**:
1. Extract each helper as a module-level private function (not a method — they are pure functions).
2. Ensure the fallback chain (agent_profile, role) is applied consistently in each helper.
3. Run `ruff check src/specify_cli/status/wp_metadata.py --select C901` after extraction — CC must be ≤ 10 for `resolved_agent`.
4. Run characterization tests: `pytest tests/specify_cli/status/test_wp_metadata.py -x` — must pass.

**Note**: The helpers themselves will each have CC ≤ 4. The combined function is smaller and easier to reason about. Do not add new external callers for the private helpers.

---

## Subtask T010 — Fix exception chain in `wp_metadata.py:194`

**Purpose**: Preserve exception context in `except` blocks (FR-004).

**File**: `src/specify_cli/status/wp_metadata.py` — find the bare `raise ValueError(...)` inside an `except ValueError:` block around line 194.

**Change** (one line):
```python
# Before
except ValueError:
    raise ValueError(f"Invalid lane: {raw_lane}")

# After
except ValueError as err:
    raise ValueError(f"Invalid lane: {raw_lane}") from err
```

This is a `change-apply-smallest-viable-diff` application — one line changed, no restructuring.

**Validation**: `ruff check src/specify_cli/status/wp_metadata.py --select B904` — zero violations.

---

## Subtask T011 — Rename `FeatureStatusLockTimeout` → `FeatureStatusLockTimeoutError`

**Purpose**: Conform to Python `Error` suffix convention for exception classes (FR-005).

**Sequential hand-off note**: `tests/git_ops/test_atomic_status_commits_unit.py` is listed in both
WP01's and WP02's `owned_files`. WP01 (Lane A, first) will have already migrated the
`emit_status_transition` call sites in that file. WP02 may additionally need to update any
`FeatureStatusLockTimeout` references it contains. Run `grep -n "FeatureStatusLockTimeout"
tests/git_ops/test_atomic_status_commits_unit.py` after WP01 merges to confirm whether an
update is needed.

**Files affected** (only 2):
```bash
grep -rn "FeatureStatusLockTimeout" src/ tests/ --include="*.py"
```

Expected: `src/specify_cli/status/locking.py` (definition) and one or two import sites.

**Steps**:
1. Rename the class in `src/specify_cli/status/locking.py`
2. Update the `__all__` export in `locking.py` if present
3. Update `src/specify_cli/status/__init__.py` export if `FeatureStatusLockTimeout` is exported there
4. Update all import sites atomically (all in the same commit — C-004)
5. Verify: `grep -r "FeatureStatusLockTimeout[^E]" src/ tests/` → zero matches (the old name is gone)

**Validation**:
- `grep -r "FeatureStatusLockTimeout[^E]" src/ tests/ --include="*.py"` — zero results
- `pytest tests/ -x -k "lock"` — no failures

---

## Subtask T012 — Quality gate

**Purpose**: Verify the full quality suite passes for WP02.

```bash
ruff check src/
mypy src/
pytest tests/ -x --timeout=120
```

**Expected outcomes**:
- ruff: zero violations (including B904 for exception chains)
- mypy: zero errors
- pytest: no new failures compared to WP01 baseline

---

## Definition of Done

- [ ] `resolved_agent` measures CC ≤ 10 (verified: `ruff check src/specify_cli/status/wp_metadata.py --select C901`)
- [ ] Each resolution input shape (AgentAssignment / string / dict / None) handled in its own named function
- [ ] Characterization tests pass for all 4 input shapes + edge cases
- [ ] `raise ValueError(...) from err` at `wp_metadata.py:194` (B904 clean)
- [ ] `FeatureStatusLockTimeoutError` is the only name in the codebase; `FeatureStatusLockTimeout` (without `Error`) is gone
- [ ] `ruff check src/` — zero violations
- [ ] `mypy src/` — zero errors
- [ ] `pytest tests/` — no new failures

## Reviewer Guidance

1. Run `ruff check src/specify_cli/status/wp_metadata.py --select C901` and confirm the reported
   CC for `resolved_agent` is ≤ 10.
2. Confirm `grep -r "FeatureStatusLockTimeout[^E]" src/ tests/ --include="*.py"` returns nothing.
3. Check that the 4 characterization test cases are present and cover the edge cases.
4. Verify `raise ... from err` at the exception chain site.

## Activity Log

- 2026-04-13T11:55:49Z – claude – shell_pid=53068 – Started implementation via action command
- 2026-04-13T13:09:16Z – claude – shell_pid=53068 – Ready for review: reduced resolved_agent complexity, fixed lane error chaining, renamed lock timeout exception
- 2026-04-13T13:11:59Z – codex:gpt-5.4:python-reviewer:reviewer – shell_pid=53183 – Started review via action command
- 2026-04-13T13:12:49Z – codex:gpt-5.4:python-reviewer:reviewer – shell_pid=53183 – Moved to planned
- 2026-04-13T13:36:41Z – codex:gpt-5.4:python-implementer:implementer – shell_pid=53183 – Started implementation via action command
- 2026-04-13T14:12:13Z – codex:gpt-5.4:python-implementer:implementer – shell_pid=53183 – Ready for review: reduced resolved_agent complexity, fixed lane error chaining, renamed lock timeout exception, focused checks green
- 2026-04-13T14:21:03Z – codex:gpt-5.4:python-reviewer:reviewer – shell_pid=53183 – Started review via action command
- 2026-04-13T14:21:41Z – codex:gpt-5.4:python-reviewer:reviewer – shell_pid=53183 – Review passed: resolved_agent helpers extracted, exception chaining preserved, timeout exception rename covered by tests
