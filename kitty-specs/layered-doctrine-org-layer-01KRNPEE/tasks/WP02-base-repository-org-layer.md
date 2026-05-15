---
work_package_id: WP02
title: BaseDoctrineRepository Org Layer
dependencies:
- WP01
requirement_refs:
- C-003
- C-006
- FR-001
- FR-002
- FR-003
- NFR-004
- NFR-005
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: All planning and implementation targets feat/org-doctrine-layer. Worktree branch allocated by finalize-tasks lane computation.
subtasks:
- T006
- T007
- T008
- T009
- T010
agent: codex
history:
- date: '2026-05-15'
  event: created
agent_profile: python-pedro
authoritative_surface: src/doctrine/base.py
execution_mode: code_change
owned_files:
- src/doctrine/base.py
- src/doctrine/directives/repository.py
- src/doctrine/tactics/repository.py
- src/doctrine/styleguides/repository.py
- src/doctrine/toolguides/repository.py
- src/doctrine/paradigms/repository.py
- src/doctrine/procedures/repository.py
- src/doctrine/agent_profiles/repository.py
- src/doctrine/mission_step_contracts/repository.py
- tests/doctrine/test_base_org_layer.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Extend `BaseDoctrineRepository` with a three-layer loading pipeline: shipped → org → project.
Add provenance tracking so every resolved artifact is tagged with its source layer. Update
all 8 concrete repository subclasses to accept and forward the new `org_dir` parameter.

---

## Context

`BaseDoctrineRepository` (in `src/doctrine/base.py`) is the shared base for all 8 doctrine
artifact repositories. It currently implements a two-step `_load()`:
1. `_load_shipped_items()` — walks shipped YAML dir, returns `dict[str, T]`
2. `_apply_project_overrides()` — merges project dir over shipped, updates `self._items`

This WP adds a third step between them:
3. `_apply_org_overrides()` — merges org dir over shipped, updates `self._items`

Provenance is tracked in `self._provenance: dict[str, str]`, parallel to `self._items`.
Values are `"shipped"`, `"org"`, or `"project"`.

**Key invariant to preserve**: The existing `_merge()` (field-level merge) is used within
the project override step for artifacts whose ID exists in shipped (project fields override
shipped fields). The same field-level merge is used for org overrides of shipped. New
artifacts introduced by org or project layers are full-replace (no merge needed).

---

## Branch Strategy

- **Planning/base branch**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Implement command**: `spec-kitty agent action implement WP02 --agent codex`

---

## Subtask T006 — Add `org_dir` parameter to `BaseDoctrineRepository.__init__`

**File**: `src/doctrine/base.py`

Add `org_dir: Path | None = None` as the second positional parameter (after `shipped_dir`,
before `project_dir`). Update the constructor signature:

```python
def __init__(
    self,
    shipped_dir: Path,
    org_dir: Path | None = None,
    project_dir: Path | None = None,
    active_languages: list[str] | tuple[str, ...] | None = None,
) -> None:
    self._shipped_dir = shipped_dir
    self._org_dir = org_dir
    self._project_dir = project_dir
    ...
    self._provenance: dict[str, str] = {}
    self._load()
```

The `_provenance` dict is initialised to empty before `_load()`.

**Backward compatibility**: `org_dir` defaults to `None`. All existing call sites that pass
only `shipped_dir` and `project_dir` as positional args will break because `org_dir` is now
the second positional arg. To avoid breaking callers, use keyword-only enforcement:

```python
def __init__(
    self,
    shipped_dir: Path,
    *,
    org_dir: Path | None = None,
    project_dir: Path | None = None,
    active_languages: list[str] | tuple[str, ...] | None = None,
) -> None:
```

This makes `org_dir`, `project_dir`, and `active_languages` keyword-only. All existing
subclass `__init__` calls (e.g., `DirectiveRepository(shipped_dir=..., project_dir=...)`)
already use keyword arguments, so this is safe. Verify by running the test suite.

---

## Subtask T007 — Add `_apply_org_overrides()` with provenance tagging

**File**: `src/doctrine/base.py`

Model `_apply_org_overrides()` on `_apply_project_overrides()`. Key differences:
- Uses `self._org_dir` instead of `self._project_dir`
- Tags artifacts as `"org"` in `self._provenance`
- Scans with `self._project_scan(self._org_dir)` (same scan method as project)

```python
def _apply_org_overrides(self, yaml_parser: YAML, shipped: dict[str, T]) -> None:
    """Merge org-dir artifacts into self._items; tag provenance as 'org'."""
    if not (self._org_dir and self._org_dir.exists()):
        return
    for yaml_file in self._project_scan(self._org_dir):
        try:
            data = yaml_parser.load(yaml_file)
            if data is None:
                continue
            self._pre_validate(data, yaml_file)
            item_id = data.get("id")
            if not item_id:
                warnings.warn(
                    f"Skipping org {self._kind} {yaml_file.name}: no id",
                    UserWarning,
                    stacklevel=3,
                )
                continue
            if item_id in shipped:
                merged = self._merge(shipped[item_id], data)
                if self._include_item(merged):
                    self._items[item_id] = merged
                    self._provenance[item_id] = "org"
            else:
                obj = self._schema.model_validate(data)
                if self._include_item(obj):
                    self._items[self._key(obj)] = obj
                    self._provenance[self._key(obj)] = "org"
        except (YAMLError, ValidationError, OSError) as exc:
            warnings.warn(
                f"Skipping invalid org {self._kind} {yaml_file.name}: {exc}",
                UserWarning,
                stacklevel=3,
            )
```

Also update `_load_shipped_items()` to populate `_provenance` for shipped items (tag as
`"shipped"`). Update `_apply_project_overrides()` to tag overridden/new items as
`"project"`.

---

## Subtask T008 — Update `_load()` to invoke org override step

**File**: `src/doctrine/base.py`

Update the `_load()` method to insert the org step between shipped loading and project
overrides:

```python
def _load(self) -> None:
    yaml_parser = YAML(typ="safe")
    shipped = self._load_shipped_items(yaml_parser)
    self._items = shipped.copy()
    # Tag all shipped items as 'shipped'
    self._provenance = {k: "shipped" for k in self._items}
    # Org layer overrides shipped
    self._apply_org_overrides(yaml_parser, shipped)
    # Project layer overrides shipped + org
    self._apply_project_overrides(yaml_parser, shipped)
```

Note: `_apply_project_overrides()` receives the original `shipped` dict so it can still
call `self._merge(shipped[item_id], data)` for project overrides of shipped artifacts.
For project overrides of org artifacts (item in `self._items` but not in `shipped`), the
existing logic already handles this: it finds `item_id in shipped` is False, so it
full-replaces by creating a new `obj`. The provenance tag is updated to `"project"`.

---

## Subtask T009 — Update all 8 repository subclasses

**Files**: one per artifact type (see `owned_files` in frontmatter)

Each repository subclass `__init__` must accept and forward `org_dir`. The pattern is
identical across all 8:

Before (example from `DirectiveRepository`):
```python
def __init__(
    self,
    shipped_dir: Path | None,
    project_dir: Path | None = None,
) -> None:
    super().__init__(
        shipped_dir=shipped_dir or Path(),
        project_dir=project_dir,
    )
```

After:
```python
def __init__(
    self,
    shipped_dir: Path | None,
    *,
    org_dir: Path | None = None,
    project_dir: Path | None = None,
) -> None:
    super().__init__(
        shipped_dir=shipped_dir or Path(),
        org_dir=org_dir,
        project_dir=project_dir,
    )
```

Apply this pattern to: `DirectiveRepository`, `TacticRepository`, `StyleguideRepository`,
`ToolguideRepository`, `ParadigmRepository`, `ProcedureRepository`,
`AgentProfileRepository`, `MissionStepContractRepository`.

Some subclasses also accept `active_languages`; preserve that parameter and forwarding.

---

## Subtask T010 — Unit tests for three-layer merge

**File**: `tests/doctrine/test_base_org_layer.py` (new file)

Use a concrete subclass or a minimal test double of `BaseDoctrineRepository`. Create
temp-path fixtures to set up shipped/org/project directories with YAML files.

**Key test cases**:

| Test | Setup | Expected |
|---|---|---|
| `test_shipped_only` | shipped: A. org: none. project: none. | `_items = {A: shipped_A}`, `_provenance = {A: "shipped"}` |
| `test_org_overrides_shipped` | shipped: A. org: A (different label). | `_items = {A: org_A}`, `_provenance = {A: "org"}` |
| `test_org_adds_new_artifact` | shipped: A. org: B. | Both in `_items`; A=shipped, B=org |
| `test_project_overrides_org` | shipped: A. org: A(v2). project: A(v3). | `_items = {A: v3}`, `_provenance = {A: "project"}` |
| `test_project_overrides_shipped_not_org` | shipped: A. org: B. project: A(v2). | A=project(v2), B=org |
| `test_bad_org_file_skipped` | shipped: A. org: malformed.yaml + B. | A=shipped, B=org; warning emitted |
| `test_language_scope_applied_after_org` | shipped: A(all). org: C(python-only). active=java. | C excluded from `_items` |
| `test_project_new_artifact_provenance` | shipped: A. project: B. | A=shipped, B=project |

---

## Definition of Done

- [ ] `BaseDoctrineRepository.__init__` accepts `org_dir` as keyword-only parameter
- [ ] `_provenance: dict[str, str]` populated by `_load()` for all artifacts
- [ ] `_apply_org_overrides()` method present and invoked in `_load()`
- [ ] All 8 repository subclasses updated to accept and forward `org_dir`
- [ ] `test_base_org_layer.py` all tests pass
- [ ] All existing doctrine repository tests pass (`pytest tests/doctrine/`)
- [ ] `get_provenance(item_id: str) -> str | None` public method added to `BaseDoctrineRepository`

## Risks

- The keyword-only change to `__init__` must not break any existing call site that currently
  passes `shipped_dir` and `project_dir` positionally. Run `grep -r "Repository(" src/`
  to find all instantiation sites before finalising.
- `_apply_project_overrides()` accesses `shipped` dict for merge — must still work correctly
  when org layer has introduced new artifacts not in `shipped`.

## Reviewer Guidance

1. Verify `_provenance` is populated for ALL code paths: shipped, org-override, org-new,
   project-override, project-new.
2. Verify `get_provenance()` returns `None` for unknown IDs (not raises `KeyError`).
3. Confirm the three-layer invariants from `data-model.md` §6 are covered by tests.
