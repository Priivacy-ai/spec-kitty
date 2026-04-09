---
work_package_id: WP05
title: Fix Remaining Mypy Violations
dependencies: []
requirement_refs:
- FR-002
- FR-003
planning_base_branch: feat/079-ci-hardening-and-lint-cleanup
merge_target_branch: feat/079-ci-hardening-and-lint-cleanup
branch_strategy: Planning artifacts for this feature were generated on feat/079-ci-hardening-and-lint-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/079-ci-hardening-and-lint-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T024
- T025
- T026
history:
- date: '2026-04-09'
  action: created
  actor: claude-sonnet-4-6
authoritative_surface: src/specify_cli/sync/
execution_mode: code_change
owned_files:
- src/specify_cli/state_contract.py
- src/specify_cli/acceptance_matrix.py
- src/specify_cli/sync/config.py
- src/specify_cli/sync/body_transport.py
- src/specify_cli/merge/conflict_resolver.py
- src/specify_cli/version_utils.py
- src/specify_cli/upgrade/feature_meta.py
- src/specify_cli/tracker/credentials.py
- src/specify_cli/cli/commands/materialize.py
- src/specify_cli/migration/backfill_ownership.py
- src/doctrine/missions/repository.py
- pyproject.toml
tags: []
---

# WP05 — Fix Remaining Mypy Violations

## Objective

Fix bare generic types (`dict`/`list` without type parameters), `no-any-return` violations,
missing return type annotations, type incompatibilities, and add the `types-requests` dev
dependency so mypy can type-check `body_transport.py`.

After this WP, `mypy --strict src/` reports zero errors for all files listed in FR-002.

## Context

**Why this WP exists:** Mypy --strict rejects un-parameterized generic types (`dict` should
be `dict[str, Any]` or a specific subtype), functions that return `Any` when a specific type
is declared, functions without return annotations, and assignment of incompatible types.
These violations were previously masked or deferred; this WP resolves the remaining set not
handled by WP04.

**File ownership:** This WP does NOT touch `backfill_identity.py` (owned by WP04) or
`policy/audit.py` (owned by WP04). All files listed here are exclusive to this WP.

**Doctrine:** DIRECTIVE_030 (type quality gate), C-006 (`types-requests` must be dev-only).

**This WP is part of Batch 1 (parallel).** T020–T025 touch different files and can be
applied simultaneously.

## Subtask Guidance

### T020 — Fix bare `dict`/`list` generics (4 files)

**Files:**
- `src/specify_cli/state_contract.py:80` — `dict` → `dict[str, Any]` or specific type
- `src/specify_cli/acceptance_matrix.py:75,88` — two `dict` annotations
- `src/doctrine/missions/repository.py:56,74` — `list`/`dict` without type params
- `src/specify_cli/migration/backfill_ownership.py:86,151` — `dict` annotations

**Fix pattern for each location:**
1. Read the function or class attribute to understand what the dict/list actually contains.
2. Add the type parameter:
   - `dict` → `dict[str, Any]` (if truly heterogeneous) or `dict[str, str]` etc.
   - `list` → `list[SomeType]`
   - For return annotations: match what the function actually returns
   - If `Any` is needed: `from typing import Any` (already likely imported)

**Example:**
```python
# Before (bare generic):
def get_config(self) -> dict:
    return self._config

# After (parameterized):
def get_config(self) -> dict[str, Any]:
    return self._config
```

**Validation for each file:**
```bash
mypy src/specify_cli/state_contract.py
mypy src/specify_cli/acceptance_matrix.py
mypy src/doctrine/missions/repository.py
mypy src/specify_cli/migration/backfill_ownership.py
```

---

### T021 — Fix `no-any-return` violations (4 files)

**Files:**
- `src/specify_cli/version_utils.py:28`
- `src/specify_cli/upgrade/feature_meta.py:165`
- `src/doctrine/missions/repository.py:31,36,66,71,76`

**Note:** `backfill_identity.py` and `policy/audit.py` are handled in WP04. Do not touch them.

**Fix pattern:**
A `no-any-return` error means a function is declared to return `SomeType` but actually returns
`Any`. Fix options in order of preference:

1. **Narrow with a cast** (when you know the runtime type):
   ```python
   from typing import cast
   return cast(str, some_dynamic_value)
   ```

2. **Add a type assertion** (when you want runtime safety):
   ```python
   result = some_dynamic_value
   assert isinstance(result, str)
   return result
   ```

3. **Widen the return annotation** to include `Any` explicitly:
   ```python
   def my_func() -> str | Any:  # or just: Any
   ```
   This is a last resort — prefer narrowing.

For `version_utils.py:28`, the function likely returns a parsed version string from a package
metadata call (`importlib.metadata.version(...)`). This returns `str`, so the annotation
should be `-> str` and the return can be used directly.

For `feature_meta.py:165` and `repository.py` multiple lines, read the function body first
to understand the actual return type before choosing a fix.

---

### T022 — Fix missing return type annotations in `sync/config.py:15,39`

**File:** `src/specify_cli/sync/config.py`

Two functions at approximately lines 15 and 39 lack return type annotations. Mypy `--strict`
requires all functions to be annotated.

**Fix:**
1. Read each function's body to determine what it returns.
2. For functions that only perform setup/initialization and have no return statement: `-> None`
3. For functions returning a value: add the appropriate annotation

**Example:**
```python
# Before:
def setup_connection(self, host: str, port: int):
    self._conn = create_conn(host, port)

# After:
def setup_connection(self, host: str, port: int) -> None:
    self._conn = create_conn(host, port)
```

**Validation:**
```bash
mypy src/specify_cli/sync/config.py
```

---

### T023 — Fix type incompatibilities in `conflict_resolver.py:172` and `materialize.py:123`

**Files:**
- `src/specify_cli/merge/conflict_resolver.py:172` — sort key callable type mismatch
- `src/specify_cli/cli/commands/materialize.py:123` — `Any | None` assigned to `str`

**`conflict_resolver.py:172` (sort key):**
Python's `list.sort(key=...)` expects `Callable[[T], SupportsLessThan]`. Mypy is strict about
this. Read the sort call and the key function:
```python
# Common fix: explicit type annotation on the key lambda
items.sort(key=lambda x: x.some_field)  # mypy may infer incorrectly
# Fix: cast or annotate
items.sort(key=lambda x: str(x.some_field))  # if sorting by string
```

**`materialize.py:123` (`Any | None` → `str`):**
Read the assignment. The pattern is typically:
```python
some_var: str = possibly_none_value  # incompatible: str vs None
```
Fix:
```python
# Option A: default value
some_var: str = possibly_none_value or ""

# Option B: assertion
assert possibly_none_value is not None
some_var: str = possibly_none_value

# Option C: widen annotation if None is valid
some_var: str | None = possibly_none_value
```
Choose based on the semantic intent — if None is a valid value, widen; if None should never
occur here, assert.

**Validation:**
```bash
mypy src/specify_cli/merge/conflict_resolver.py
mypy src/specify_cli/cli/commands/materialize.py
```

---

### T024 — Fix `tracker/credentials.py`: remove stale ignore (line 15) + fix None→Module assignment (line 17)

**File:** `src/specify_cli/tracker/credentials.py`

Two adjacent issues:
1. **Line 15:** A stale `# type: ignore` (unused-ignore)
2. **Line 17:** `None` being assigned to a variable annotated as `types.ModuleType`

**Read lines 10–25 first.** The pattern is typically:
```python
import importlib
_module: types.ModuleType = None  # type: ignore  ← stale
```

**Fix:**
```python
import importlib
import types

_module: types.ModuleType | None = None  # widen annotation to allow None
```

Then at the point of use, add a None-check or assertion before dereferencing. Check how
`_module` is used downstream in the file to ensure the None-check is placed correctly.

After fixing the type annotation:
- Remove the `# type: ignore` from line 15 (it is now stale because line 17 is type-correct)

**Validation:**
```bash
mypy src/specify_cli/tracker/credentials.py
```
Zero errors (no unused-ignore, no incompatible assignment).

---

### T025 — Add `types-requests` to dev dependencies in `pyproject.toml`

**File:** `pyproject.toml`

**Constraint (C-006):** `types-requests` must be added ONLY to a development dependency group,
not to `[project.dependencies]` (runtime).

Read `pyproject.toml` to find the development/testing dependency groups. Common patterns:
- `[project.optional-dependencies]` with a `dev` or `test` group
- `[tool.hatch.envs.test.dependencies]`
- `[tool.poetry.dev-dependencies]`

Identify which group the other type stubs (if any) or test tools are in, and add
`types-requests` to the same group:

```toml
# Example — find the correct section:
[project.optional-dependencies]
dev = [
    "pytest",
    "mypy",
    "types-requests",   # ← add here
    ...
]
```

**Validation:**
```bash
# Install and verify mypy can find the stubs
pip install -e ".[dev]"
mypy src/specify_cli/sync/body_transport.py
```
The body_transport.py errors about missing `requests` stubs should be gone.

---

### T026 — Verify `mypy --strict src/` exits 0 for all FR-002 files; run full test suite

**Final verification gate:**

```bash
# 1. Strict mypy check for all files in FR-002 scope
mypy --strict \
  src/specify_cli/state_contract.py \
  src/specify_cli/acceptance_matrix.py \
  src/specify_cli/sync/config.py \
  src/specify_cli/sync/body_transport.py \
  src/specify_cli/merge/conflict_resolver.py \
  src/specify_cli/version_utils.py \
  src/specify_cli/upgrade/feature_meta.py \
  src/specify_cli/tracker/credentials.py \
  src/specify_cli/cli/commands/materialize.py \
  src/specify_cli/migration/backfill_ownership.py \
  src/doctrine/missions/repository.py

# 2. Run the full fast test suite to catch any regressions
pytest tests/ -m fast -q 2>&1 | tail -5
```

If mypy reports errors:
- Check which task's fix is incomplete
- For `no-any-return`: ensure the cast/annotation is in the right place
- For `type-arg`: check that parameterized generics are complete

**Commit** once all gates pass.

## Definition of Done

- [ ] `mypy --strict` exits 0 for all 11 source files listed in `owned_files` + `body_transport.py`
- [ ] `types-requests` is in dev dependencies only (not in `[project.dependencies]`)
- [ ] All existing tests pass
- [ ] No production behavior changed (type annotations only, plus the `None` guard for `tracker/credentials.py`)
- [ ] Changes committed to `feat/079-ci-hardening-and-lint-cleanup`

## Risks

- **`types-requests` version conflict:** If the installed `requests` version is older than the
  stubs expect, mypy may report stub version mismatch warnings. Pin `types-requests` to a
  compatible version if needed.
- **Cast masking a real bug:** Using `cast(SomeType, value)` bypasses type checking. Prefer
  `assert isinstance(value, SomeType)` where runtime safety matters.
- **`repository.py` has many violations:** Five separate `no-any-return` lines in
  `doctrine/missions/repository.py`. Read the full file before fixing to understand the
  pattern — it may be a single fix (a shared helper method) rather than 5 separate fixes.

## Reviewer Guidance

The diff should contain: type annotation additions/changes, a `pyproject.toml` change with
`types-requests`, and possibly a `cast()` or `assert isinstance()` call. No logic changes.
If any conditional branches are added or removed, that is outside the scope of a type-only fix.
