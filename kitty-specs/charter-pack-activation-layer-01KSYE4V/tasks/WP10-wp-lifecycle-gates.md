---
work_package_id: WP10
title: WP Lifecycle Gates
dependencies:
- WP02
- WP04
requirement_refs:
- FR-017
- FR-018
tracker_refs: []
planning_base_branch: pr/charter-doctrine-mission-type-configuration
merge_target_branch: pr/charter-doctrine-mission-type-configuration
branch_strategy: Planning artifacts for this mission were generated on pr/charter-doctrine-mission-type-configuration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/charter-doctrine-mission-type-configuration unless the human explicitly redirects the landing branch.
subtasks:
- T044
- T045
- T046
- T047
agent: claude
history:
- at: '2026-05-31T11:44:22Z'
  event: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/mission.py
- src/specify_cli/cli/commands/agent/workflow.py
- src/charter/exceptions.py
- tests/specify_cli/test_charter_lifecycle_gates.py
role: implementer
tags: []
---

## Do This First: Load Agent Profile

Before reading anything else, load the implementer profile:

```
/ad-hoc-profile-load python-pedro
```

You are implementing as **python-pedro** (Python implementer). Work precisely, make
only the changes described, validate after each subtask, and do not touch files
outside the `owned_files` list above.

---

## Objective

Add charter activation gates to two CLI entry points (`finalize-tasks` and
`agent action implement`) so that work packages whose `agent_profile` frontmatter
field names a profile that is not in the project's activated charter set are
rejected with a clear, actionable error. Also wire a hard-fail on non-activated
artifact lookups in the charter context resolution path.

WP02 must be `approved` or `done` before this WP starts (it delivers the three-state
`PackContext` fields including `activated_agent_profiles`). WP04 must also be
`approved` or `done` (it delivers `CharterPackManager` and the pack infrastructure
that stores activated profiles).

---

## Context

### What `activated_agent_profiles` means

`PackContext.activated_agent_profiles` is one of the 8 new three-state fields added
by WP02. Three states:

- `None` — key `activated_agent_profiles` absent from `.kittify/config.yaml`; all
  built-in agent profiles are available. **No gate check fires.**
- `frozenset()` — key present but empty; nothing is activated. Every WP with any
  `agent_profile` will fail.
- `frozenset({"python-pedro", "reviewer-renata"})` — only those profiles are active.

The gate fires only when `activated_profiles is not None` (i.e. the operator has
opted into an explicit restriction).

### C-006 ordering constraint

The precondition check in `agent action implement` MUST complete BEFORE any git
worktree is created or any status transition is emitted. The current implement
entry point (`workflow.py:800`) already performs a sparse-checkout preflight before
workspace creation. The charter gate must be inserted at the same "before workspace"
point, after loading the WP frontmatter but before `resolve_workspace_for_wp` is
called.

### FR-019 — hard-fail on deactivated artifact lookup

When a charter-aware resolution path receives a filtered DRG (after WP08 wires
`filter_graph_by_activation`) and the requested artifact is absent from the filtered
graph, the caller must raise `CharterActivationError`, not return silently. The error
must include the artifact identifier, the activated set, and the exact resolution
command.

---

## Branch Strategy

```
planning_base_branch: pr/charter-doctrine-mission-type-configuration
merge_target_branch:  pr/charter-doctrine-mission-type-configuration
```

All commits go directly onto `pr/charter-doctrine-mission-type-configuration` in the
lane worktree allocated by `finalize-tasks`. Do not create additional git branches.

---

## Subtasks

### T044 — Add charter profile gate to `finalize-tasks` (FR-017)

**File**: `src/specify_cli/cli/commands/agent/mission.py`

The `finalize_tasks` command is defined at line 1725. It loops over parsed WP files
to infer frontmatter. Add the activation check inside that loop, after frontmatter
is loaded but before any artifact is written.

1. Locate the finalize-tasks WP processing loop. Run:
   ```bash
   grep -n "agent_profile\|frontmatter\|for wp\|for task\|for wps" \
     src/specify_cli/cli/commands/agent/mission.py | head -20
   ```

2. Import `PackContext` at the top of the module (after other charter imports):
   ```python
   from charter.pack_context import PackContext
   ```
   Check first whether it is already imported:
   ```bash
   grep -n "PackContext\|pack_context" src/specify_cli/cli/commands/agent/mission.py | head -10
   ```

3. After loading WP frontmatter and extracting `agent_profile`, add:
   ```python
   if profile := frontmatter.get("agent_profile"):
       pack_context = PackContext.from_config(repo_root)
       activated_profiles = pack_context.activated_agent_profiles
       if activated_profiles is not None and profile not in activated_profiles:
           activated_list = ", ".join(sorted(activated_profiles)) or "(none)"
           console.print(
               f"[red]✗ Charter activation gate FAILED[/red]\n"
               f"  WP {wp_id} assigns profile: [bold]{profile}[/bold]\n"
               f"  '{profile}' is not in the activated agent-profile set.\n"
               f"  Currently activated: {activated_list}\n"
               f"  Resolution: spec-kitty charter activate agent-profile {profile}"
           )
           raise typer.Exit(code=1)
   ```

4. The check must fire **before** any `write_text` or `commit` call on WP files.
   Use `--validate-only` dry-run mode as the test path: the gate must trigger even
   when `--validate-only` is passed.

**Acceptance criterion**: Running `finalize-tasks` with a WP whose `agent_profile`
is not in the activated set exits with code 1 and prints the resolution command
before any file is written.

---

### T045 — Add charter precondition to `agent action implement` (FR-018, C-006)

**File**: `src/specify_cli/cli/commands/agent/workflow.py`

The `implement` function is defined at line 800. The sparse-checkout preflight runs
at approximately line 852. The charter gate must be inserted **after** loading the
WP file (the `locate_work_package` call at approximately line 901) but **before**
`resolve_workspace_for_wp` at line 912. This satisfies C-006.

1. Locate the exact insertion point. Run:
   ```bash
   grep -n "locate_work_package\|resolve_workspace\|PackContext\|charter" \
     src/specify_cli/cli/commands/agent/workflow.py | head -20
   ```

2. Import `PackContext` if not already present:
   ```bash
   grep -n "PackContext" src/specify_cli/cli/commands/agent/workflow.py | head -5
   ```

3. After `wp = locate_work_package(...)` succeeds, read the `agent_profile` from
   `wp.frontmatter` (or equivalent attribute — check how the WP object exposes
   frontmatter fields):
   ```bash
   grep -n "wp\.frontmatter\|wp\.agent_profile\|frontmatter" \
     src/specify_cli/cli/commands/agent/workflow.py | head -10
   ```

4. Insert the gate after the WP is loaded, before workspace resolution:
   ```python
   # C-006 charter precondition: check BEFORE any worktree creation or
   # status transition.
   _wp_profile = getattr(wp, "agent_profile", None) or (
       wp.frontmatter.get("agent_profile") if hasattr(wp, "frontmatter") else None
   )
   if _wp_profile:
       from charter.pack_context import PackContext  # noqa: PLC0415
       _pack_ctx = PackContext.from_config(main_repo_root)
       _activated = _pack_ctx.activated_agent_profiles
       if _activated is not None and _wp_profile not in _activated:
           _activated_list = ", ".join(sorted(_activated)) or "(none)"
           print(
               f"Error: WP{normalized_wp_id} charter precondition FAILED\n"
               f"  Assigned profile '{_wp_profile}' is not accessible through "
               f"the active charter.\n"
               f"  Currently activated: {_activated_list}\n"
               f"  Run: spec-kitty charter activate agent-profile {_wp_profile}"
           )
           raise typer.Exit(code=1)
   ```

5. Verify ordering by reading lines around the insertion point to confirm no
   worktree creation or `emit_status_transition` call precedes the gate.

**Acceptance criterion**: `spec-kitty agent action implement WP01 --agent claude`
exits code 1 with the resolution command printed, and no worktree directory is
created on disk, when the WP's profile is not activated.

---

### T046 — Wire hard-fail on non-activated artifact lookup (FR-019)

**File**: `src/charter/context.py`

After WP08 wires `filter_graph_by_activation`, the filtered DRG will be empty for
kinds that are explicitly deactivated. The charter context builder needs to detect
when a specific requested artifact is absent from the filtered graph and raise a
structured error.

1. Understand the current context build flow. Run:
   ```bash
   grep -n "def _prepare_context_state\|filter_graph\|artifact\|tactic\|directive" \
     src/charter/context.py | head -20
   ```

2. Define `CharterActivationError` at module level in `src/charter/context.py`
   (or in `src/charter/drg.py` if a shared location is preferred — check first):
   ```bash
   grep -rn "CharterActivationError" src/charter/ --include="*.py" | head -5
   ```
   If it does not exist, add it as a `RuntimeError` subclass:
   ```python
   class CharterActivationError(RuntimeError):
       """Raised when a requested artifact is not in the activated charter set.

       Carries the artifact identifier, the activated set, and the resolution
       command so callers can surface an actionable error to the operator.
       """
   ```
   Export it from `src/charter/__init__.py` if other modules will catch it:
   ```bash
   grep -n "CharterActivationError\|__all__" src/charter/__init__.py | head -5
   ```

3. In the path that resolves a specific artifact by ID (after the filtered DRG is
   produced), add a presence check:
   ```python
   filtered_graph = filter_graph_by_activation(raw_graph, pack_context)
   artifact_node = _find_node_in_graph(filtered_graph, artifact_id)
   if artifact_node is None:
       activated_ids = _ids_for_kind(pack_context, kind)
       raise CharterActivationError(
           f"Artifact '{artifact_id}' (kind: {kind}) is not in the activated "
           f"charter set.\n"
           f"Activated {kind}: {sorted(activated_ids) if activated_ids is not None else '(all)'}\n"
           f"Resolution:\n  spec-kitty charter activate {kind} {artifact_id}"
       )
   ```

4. The hard-fail applies only when `activated_ids is not None` — i.e. an explicit
   restriction is in place. When `activated_ids is None`, the artifact is considered
   available (backward compatibility / no restriction configured).

---

### T047 — Write lifecycle gate tests

**New file**: `tests/specify_cli/test_charter_lifecycle_gates.py`

Create the file from scratch. Use `pytest.mark.fast` for all tests; they must not
touch the real filesystem beyond `tmp_path` fixtures.

```bash
# Verify the tests directory exists
ls tests/specify_cli/ | head -5
```

Write the following tests:

**Test 1 — finalize-tasks hard-fails when profile not activated**

```python
def test_finalize_tasks_hard_fails_when_profile_not_activated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-017: finalize-tasks exits 1 when WP agent_profile is not activated."""
    # Arrange: config with activated profiles that exclude researcher-robbie
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text(
        "activated_agent_profiles:\n  - python-pedro\n  - reviewer-renata\n",
        encoding="utf-8",
    )
    # WP file with researcher-robbie profile
    feature_dir = tmp_path / "kitty-specs" / "099-test"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    wp_file = tasks_dir / "WP01-test.md"
    wp_file.write_text(
        "---\nwork_package_id: WP01\nagent_profile: researcher-robbie\n---\n\n# WP01\n",
        encoding="utf-8",
    )

    # Patch locate_project_root and the finalize-tasks internals as needed
    # (exact patch targets depend on the command's import paths)
    ...
    # Assert: exits non-zero
    # Assert: error message contains researcher-robbie
    # Assert: error message contains the resolution command
```

**Test 2 — finalize-tasks passes when profile is activated**

Mirror of Test 1 but with `researcher-robbie` in the activated set. Assert that
the gate does not fire and execution continues.

**Test 3 — finalize-tasks skips check when `activated_agent_profiles` is None**

Config has no `activated_agent_profiles` key. Assert that the gate does not fire
even when the WP has an `agent_profile` set.

**Test 4 — implement hard-fails when profile not activated**

Same scenario for `agent action implement`. The test must verify that no worktree
directory is created on disk (check `tmp_path` for absence of `.worktrees/`).

**Test 5 — implement skips check when no explicit activation**

Backward-compat scenario: config has no `activated_agent_profiles` key. Assert that
implement proceeds past the charter gate (it may fail later for unrelated reasons,
but not at the gate step).

**Test 6 — error message contains exact resolution command**

Use `capsys` or capture the output. Assert that the error message contains the
string `charter activate agent-profile researcher-robbie` verbatim.

**ATDD fixture review**: Check the following existing finalize-tasks test fixtures:

```bash
grep -n "agent_profile\|activated_agent_profiles" \
  tests/tasks/test_finalize_tasks_json_output_unit.py \
  tests/tasks/test_finalize_tasks_owned_files_validation.py \
  tests/specify_cli/test_task_profile_suggestion.py
```

For each fixture that includes `agent_profile` in a WP but has no config with an
explicit `activated_agent_profiles` key: confirm the config either has no
`activated_agent_profiles` key (gate skipped) or includes the profile (gate passes).
If any existing test would be broken by the new gate, update its fixture to set
`activated_agent_profiles: null` equivalent (i.e. omit the key from config.yaml).

---

## Validation Commands

After completing all subtasks, run these in order:

```bash
# 1. Static analysis
cd src && ruff check ../src/specify_cli/cli/commands/agent/mission.py \
                     ../src/specify_cli/cli/commands/agent/workflow.py \
                     ../src/charter/context.py

# 2. Type checking on touched files
cd src && python -m mypy --strict \
  specify_cli/cli/commands/agent/mission.py \
  specify_cli/cli/commands/agent/workflow.py \
  charter/context.py

# 3. New lifecycle gate tests
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty && \
  pytest tests/specify_cli/test_charter_lifecycle_gates.py -x -v

# 4. Affected existing tests
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty && \
  pytest tests/tasks/ tests/specify_cli/test_task_profile_suggestion.py -x -v

# 5. Full fast suite — must be clean
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty && \
  pytest tests/ -m fast -x -q
```

All five commands must complete without errors or failures.

---

## Definition of Done

- `spec-kitty agent mission finalize-tasks` hard-fails (exit code 1) when a WP's
  `agent_profile` is not in `PackContext.activated_agent_profiles` (when the field
  is non-None).
- `spec-kitty agent action implement` hard-fails before any worktree creation when
  the WP's `agent_profile` is not activated (C-006 ordering respected).
- Both gates are silently skipped when `activated_agent_profiles is None`
  (backward-compatible with pre-upgrade projects).
- `CharterActivationError` is defined and raised for deactivated artifact lookups
  in the charter context resolution path (FR-019).
- Error messages include: WP ID (or artifact ID), the inactive profile/artifact,
  the currently activated set, and the exact `charter activate` resolution command.
- `pytest tests/specify_cli/test_charter_lifecycle_gates.py -x` passes.
- `pytest tests/ -m fast -x -q` passes (zero regressions in fast suite).
- `ruff check` and `mypy --strict` pass on all modified files.
