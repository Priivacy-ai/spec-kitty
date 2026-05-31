---
work_package_id: WP03
title: ProjectContext + Invocation Context Module
dependencies:
- WP02
requirement_refs:
- FR-024
- FR-040
tracker_refs: []
planning_base_branch: pr/charter-doctrine-mission-type-configuration
merge_target_branch: pr/charter-doctrine-mission-type-configuration
branch_strategy: All changes land on pr/charter-doctrine-mission-type-configuration. Worktree allocated by finalize-tasks lane computation.
subtasks:
- T011
- T012
- T013
- T014
agent: claude
history:
- at: '2026-05-31T11:44:22Z'
  event: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: src/charter/invocation_context.py
execution_mode: code_change
owned_files:
- src/charter/invocation_context.py
- tests/charter/test_invocation_context.py
- tests/architectural/test_no_dead_symbols.py
- tests/architectural/_baselines.yaml
role: implementer
tags: []
---

# WP03 — ProjectContext + Invocation Context Module

## Overview

This WP introduces `src/charter/invocation_context.py`, the canonical invocation-context module for the `charter.*` package. It defines three dataclasses: `ContextPreconditionError`, `ProjectContext`, and `OperationalContext`. `ProjectContext` provides a `from_repo()` factory that produces fully-populated instances from a repository root path. Guard methods on both context types raise `ContextPreconditionError` (not `ValueError`) when a required field is absent.

`OperationalContext` is specced here but not wired to any production call site — it is an in-flight stub whose symbols are explicitly allowlisted in the dead-symbol architectural test so the ratchet does not reject them.

**Requirement refs**: FR-024, FR-040

**ATDD rule**: Every subtask that creates or changes behaviour also creates or updates the test file in the same WP.

---

## Orientation: Files to Read Before Starting

Before touching any file in this WP, read:

1. `src/charter/pack_context.py` — understand `PackContext` and its `from_config()` factory (produced by WP02). `ProjectContext.from_repo()` calls `PackContext.from_config()`. Do not import `PackContext` at the module level to avoid circular imports (use `TYPE_CHECKING`).
2. `tests/architectural/test_no_dead_symbols.py` lines 395–495 — understand the category-C in-flight allowlist mechanism and the `_SYMBOL_ALLOWLIST` aggregate.
3. `tests/architectural/_baselines.yaml` lines 112–141 — understand the ratchet baseline format; `category_c_wp_in_flight_charter_scope` must be bumped from 0 to 4.
4. `src/specify_cli/context/` (list only, do not modify) — confirm this is the existing `MissionContext` identity package. It must not be touched.

---

## T011 — Create `src/charter/invocation_context.py` class bodies

**Goal**: Define the three classes with correct `@dataclass(frozen=True)` declarations, field types, `__all__`, and `TYPE_CHECKING`-gated import for `PackContext`.

### Step-by-step

1. Create `src/charter/invocation_context.py` (new file).

2. Write the module header exactly as follows — the `from __future__ import annotations` line is mandatory because `OperationalContext.tech_stack` uses `frozenset[str]` which requires the postponed-evaluation semantics under Python 3.11, and because the `TYPE_CHECKING` guard for `PackContext` relies on annotation strings:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from charter.pack_context import PackContext
```

3. Define `ContextPreconditionError`. It must be a `@dataclass(frozen=True)` subclass of `RuntimeError`, not a plain `Exception`. The frozen dataclass pattern requires calling `object.__setattr__` via the generated `__init__`, which `@dataclass` handles automatically:

```python
@dataclass(frozen=True)
class ContextPreconditionError(RuntimeError):
    """Raised by context guard methods when a required field is absent."""

    field: str
    context_type: str

    def __str__(self) -> str:
        return (
            f"Context precondition failed: '{self.field}' is required "
            f"but absent in {self.context_type}"
        )
```

   Note: `RuntimeError.__init__` takes a message string. Because `dataclass(frozen=True)` generates `__init__`, you do not call `super().__init__()` — that is correct here; the `__str__` override provides the message surface consumers need.

4. Define `ProjectContext`:

```python
@dataclass(frozen=True)
class ProjectContext:
    """Resolved context for a spec-kitty project.

    All fields are optional so instances can be constructed partially
    in tests and in partial-discovery scenarios.
    ``from_repo()`` always returns a fully-populated instance.
    """

    repo_root: Path | None = None
    pack_context: PackContext | None = None
    org_root: Path | None = None
    specs_dir: Path | None = None
    architecture_dir: Path | None = None
```

5. Define `OperationalContext`:

```python
@dataclass(frozen=True)
class OperationalContext:
    """Runtime context about the active agent session.

    Stub — wiring to a live resolver is deferred to a follow-on mission
    (charter-pack-activation-layer WP03).
    """

    active_model: str | None = None
    active_profile: str | None = None
    active_role: str | None = None
    current_activity: str | None = None
    tech_stack: frozenset[str] = field(default_factory=frozenset)
```

6. Add `__all__` at the bottom of the module:

```python
__all__ = [
    "ContextPreconditionError",
    "OperationalContext",
    "ProjectContext",
    "build_operational_context",
]
```

   (Guard methods do not need to appear in `__all__` — they are instance methods, not module-level symbols.)

### Validation

```bash
# File must exist
test -f src/charter/invocation_context.py && echo OK

# No specify_cli imports
grep -n "from specify_cli\|import specify_cli" src/charter/invocation_context.py && echo "VIOLATION" || echo "clean"

# __all__ must be present
grep -n "__all__" src/charter/invocation_context.py
```

---

## T012 — Implement `from_repo()` factory and guard methods

**Goal**: Add the `from_repo()` classmethod to `ProjectContext`, the `require_*` guard methods to both dataclasses, and the `build_operational_context()` module-level stub.

### Step-by-step for `ProjectContext`

1. Add the `from_repo()` classmethod. The import of `PackContext` and `resolve_org_roots` must happen **inside** the method body (runtime import) so the module-level `TYPE_CHECKING` guard stays intact:

```python
@classmethod
def from_repo(cls, repo_root: Path) -> ProjectContext:
    """Construct a fully-populated ProjectContext from a repository root.

    Resolves PackContext via ``PackContext.from_config()``.
    Resolves ``org_root`` as the first entry from ``resolve_org_roots()``
    if any are found; ``None`` otherwise.
    ``specs_dir`` and ``architecture_dir`` are set only when the
    corresponding directories exist on disk.
    """
    from charter.pack_context import PackContext  # runtime import — avoids circular

    try:
        from doctrine.drg.org_pack_config import resolve_org_roots

        org_roots = resolve_org_roots(repo_root)
        org_root: Path | None = org_roots[0] if org_roots else None
    except Exception:
        org_root = None

    pack_ctx = PackContext.from_config(repo_root)

    specs_path = repo_root / "kitty-specs"
    arch_path = repo_root / "architecture"

    return cls(
        repo_root=repo_root,
        pack_context=pack_ctx,
        org_root=org_root,
        specs_dir=specs_path if specs_path.is_dir() else None,
        architecture_dir=arch_path if arch_path.is_dir() else None,
    )
```

   Key decisions:
   - `PackContext.from_config()` must not raise when `.kittify/` is absent — that contract is guaranteed by WP02. If it does raise, it is a WP02 bug.
   - `resolve_org_roots` is wrapped in `try/except Exception` because the DRG may not be importable in all environments (e.g., the charm is not installed in unit-test virtualenvs). Falling back to `None` is safer than letting an ImportError propagate.

2. Add the three guard methods:

```python
def require_repo_root(self) -> Path:
    """Return ``repo_root`` or raise ``ContextPreconditionError``."""
    if self.repo_root is None:
        raise ContextPreconditionError(
            field="repo_root", context_type="ProjectContext"
        )
    return self.repo_root

def require_pack_context(self) -> PackContext:
    """Return ``pack_context`` or raise ``ContextPreconditionError``."""
    if self.pack_context is None:
        raise ContextPreconditionError(
            field="pack_context", context_type="ProjectContext"
        )
    return self.pack_context

def require_org_root(self) -> Path:
    """Return ``org_root`` or raise ``ContextPreconditionError``."""
    if self.org_root is None:
        raise ContextPreconditionError(
            field="org_root", context_type="ProjectContext"
        )
    return self.org_root
```

### Step-by-step for `OperationalContext`

Add two guard methods and the module-level stub:

```python
# Inside OperationalContext:

def require_active_profile(self) -> str:
    """Return ``active_profile`` or raise ``ContextPreconditionError``."""
    if self.active_profile is None:
        raise ContextPreconditionError(
            field="active_profile", context_type="OperationalContext"
        )
    return self.active_profile

def require_active_role(self) -> str:
    """Return ``active_role`` or raise ``ContextPreconditionError``."""
    if self.active_role is None:
        raise ContextPreconditionError(
            field="active_role", context_type="OperationalContext"
        )
    return self.active_role
```

```python
# Module-level stub (below the class definitions, before __all__):

def build_operational_context() -> OperationalContext:
    """Stub factory — wiring to a live resolver is deferred to a follow-on mission."""
    return OperationalContext()
```

### mypy check

```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
python -m mypy src/charter/invocation_context.py --strict 2>&1 | head -30
```

Expected: zero errors. If you see `error: Need type annotation for "pack_context"` it means the `TYPE_CHECKING` guard is not in place correctly — re-check the import block.

If you see `error: Argument 1 to "ContextPreconditionError" has incompatible type` because `RuntimeError.__init__` expects positional `args`, add:

```python
def __post_init__(self) -> None:
    # Ensure the RuntimeError base receives the message string.
    super().__init__(str(self))
```

This is only needed if `ContextPreconditionError` is raised and then caught as a plain `RuntimeError` with `str(exc)` — the dead-symbol tests do not require it, but downstream callers may. Add it defensively.

---

## T013 — Add OperationalContext symbols to dead-symbol allowlist

**Goal**: Update `tests/architectural/test_no_dead_symbols.py` to allowlist the four `OperationalContext` symbols that are specced but have no production call sites yet. Update `tests/architectural/_baselines.yaml` to bump the baseline count from 0 to 4.

### Step-by-step: `test_no_dead_symbols.py`

1. Open `tests/architectural/test_no_dead_symbols.py`. Navigate to line 405 (confirmed by grep). The current content is:

```python
_CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE: frozenset[str] = frozenset()
```

2. Replace that single line with the following block:

```python
# specced, wiring deferred to follow-on mission (charter-pack-activation-layer WP03)
_CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE: frozenset[str] = frozenset(
    {
        "charter.invocation_context::OperationalContext",
        "charter.invocation_context::build_operational_context",
        "charter.invocation_context::OperationalContext.require_active_profile",
        "charter.invocation_context::OperationalContext.require_active_role",
    }
)
```

   Note: `ProjectContext` and its guard methods are NOT in this allowlist because `from_repo()` is a production-use factory that will be called by `specify_cli.*` code importing from `charter.invocation_context`. The dead-symbol scanner considers a symbol "live" when it appears in any `import` statement in the `src/` tree — `from_repo` will be exercised immediately once any caller in `specify_cli` imports `ProjectContext`. Only the `OperationalContext` family needs the stub treatment.

3. Verify the `_SYMBOL_ALLOWLIST` aggregate at line 485 already includes `_CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE` — it does (confirmed from file read). No change needed there.

### Step-by-step: `_baselines.yaml`

1. Open `tests/architectural/_baselines.yaml`. Navigate to line 136 (confirmed by grep):

```yaml
  category_c_wp_in_flight_charter_scope: 0
```

2. Replace it with:

```yaml
  category_c_wp_in_flight_charter_scope: 4  # justification: OperationalContext family specced, wiring deferred (charter-pack-activation-layer WP03)
```

   The comment is required by the per-PR edit policy in the file's header (line 13–17): "Growing a baseline requires the YAML diff in the same PR PLUS a `# justification:` comment on the changed line."

### Validation

```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
python -m pytest tests/architectural/test_no_dead_symbols.py -x -q 2>&1 | tail -20
python -m pytest tests/architectural/test_ratchet_baselines.py -x -q 2>&1 | tail -20
```

Both must pass with zero failures. If `test_ratchet_baselines.py` fails with "baseline mismatch", the frozenset in the test file and the baseline YAML are out of sync — recount.

---

## T014 — Write `tests/charter/test_invocation_context.py`

**Goal**: Full unit test coverage for all public surfaces defined in T011–T012.

### File location

`tests/charter/test_invocation_context.py` (new file).

### Fixtures and imports

```python
from __future__ import annotations

import pytest
from pathlib import Path

from charter.invocation_context import (
    ContextPreconditionError,
    OperationalContext,
    ProjectContext,
    build_operational_context,
)
```

If `tests/charter/__init__.py` does not exist, create it as an empty file first (check with `ls tests/charter/`).

### Test cases — `ContextPreconditionError`

```python
class TestContextPreconditionError:
    def test_field_and_context_type_set(self) -> None:
        err = ContextPreconditionError(field="repo_root", context_type="ProjectContext")
        assert err.field == "repo_root"
        assert err.context_type == "ProjectContext"

    def test_str_message_format(self) -> None:
        err = ContextPreconditionError(field="pack_context", context_type="ProjectContext")
        msg = str(err)
        assert "pack_context" in msg
        assert "ProjectContext" in msg

    def test_is_runtime_error(self) -> None:
        err = ContextPreconditionError(field="x", context_type="Y")
        assert isinstance(err, RuntimeError)
```

### Test cases — `ProjectContext` construction

```python
class TestProjectContextDefaults:
    def test_all_none_defaults_valid(self) -> None:
        ctx = ProjectContext()
        assert ctx.repo_root is None
        assert ctx.pack_context is None
        assert ctx.org_root is None
        assert ctx.specs_dir is None
        assert ctx.architecture_dir is None

    def test_frozen_cannot_set_field(self) -> None:
        ctx = ProjectContext()
        with pytest.raises((AttributeError, TypeError)):
            ctx.repo_root = Path("/tmp")  # type: ignore[misc]
```

### Test cases — `ProjectContext.from_repo()`

```python
class TestProjectContextFromRepo:
    def test_repo_root_populated(self, tmp_path: Path) -> None:
        ctx = ProjectContext.from_repo(tmp_path)
        assert ctx.repo_root == tmp_path

    def test_pack_context_non_none(self, tmp_path: Path) -> None:
        """from_repo() always populates pack_context even without .kittify/."""
        ctx = ProjectContext.from_repo(tmp_path)
        assert ctx.pack_context is not None

    def test_specs_dir_detected_when_present(self, tmp_path: Path) -> None:
        (tmp_path / "kitty-specs").mkdir()
        ctx = ProjectContext.from_repo(tmp_path)
        assert ctx.specs_dir == tmp_path / "kitty-specs"

    def test_specs_dir_none_when_absent(self, tmp_path: Path) -> None:
        ctx = ProjectContext.from_repo(tmp_path)
        assert ctx.specs_dir is None

    def test_architecture_dir_detected_when_present(self, tmp_path: Path) -> None:
        (tmp_path / "architecture").mkdir()
        ctx = ProjectContext.from_repo(tmp_path)
        assert ctx.architecture_dir == tmp_path / "architecture"

    def test_architecture_dir_none_when_absent(self, tmp_path: Path) -> None:
        ctx = ProjectContext.from_repo(tmp_path)
        assert ctx.architecture_dir is None

    def test_no_raise_without_kittify(self, tmp_path: Path) -> None:
        """from_repo() must not raise when .kittify/ directory is absent.

        PackContext.from_config() is responsible for graceful absent-config
        handling (WP02 contract). This test verifies the contract end-to-end.
        """
        assert not (tmp_path / ".kittify").exists()
        ctx = ProjectContext.from_repo(tmp_path)
        assert ctx.repo_root == tmp_path
```

### Test cases — guard methods

```python
class TestProjectContextGuards:
    def test_require_repo_root_returns_value(self) -> None:
        ctx = ProjectContext(repo_root=Path("/some/path"))
        assert ctx.require_repo_root() == Path("/some/path")

    def test_require_repo_root_raises_when_none(self) -> None:
        ctx = ProjectContext()
        with pytest.raises(ContextPreconditionError) as exc_info:
            ctx.require_repo_root()
        assert exc_info.value.field == "repo_root"
        assert exc_info.value.context_type == "ProjectContext"

    def test_require_pack_context_returns_value(self, tmp_path: Path) -> None:
        ctx = ProjectContext.from_repo(tmp_path)
        pc = ctx.require_pack_context()
        assert pc is not None

    def test_require_pack_context_raises_when_none(self) -> None:
        ctx = ProjectContext()
        with pytest.raises(ContextPreconditionError) as exc_info:
            ctx.require_pack_context()
        assert exc_info.value.field == "pack_context"
        assert exc_info.value.context_type == "ProjectContext"

    def test_require_org_root_raises_when_none(self) -> None:
        ctx = ProjectContext()
        with pytest.raises(ContextPreconditionError) as exc_info:
            ctx.require_org_root()
        assert exc_info.value.field == "org_root"
        assert exc_info.value.context_type == "ProjectContext"
```

### Test cases — `OperationalContext`

```python
class TestOperationalContext:
    def test_all_none_defaults(self) -> None:
        ctx = OperationalContext()
        assert ctx.active_model is None
        assert ctx.active_profile is None
        assert ctx.active_role is None
        assert ctx.current_activity is None
        assert ctx.tech_stack == frozenset()

    def test_require_active_profile_raises_when_none(self) -> None:
        ctx = OperationalContext()
        with pytest.raises(ContextPreconditionError) as exc_info:
            ctx.require_active_profile()
        assert exc_info.value.field == "active_profile"
        assert exc_info.value.context_type == "OperationalContext"

    def test_require_active_profile_returns_value(self) -> None:
        ctx = OperationalContext(active_profile="python-pedro")
        assert ctx.require_active_profile() == "python-pedro"

    def test_require_active_role_raises_when_none(self) -> None:
        ctx = OperationalContext()
        with pytest.raises(ContextPreconditionError) as exc_info:
            ctx.require_active_role()
        assert exc_info.value.field == "active_role"
        assert exc_info.value.context_type == "OperationalContext"

    def test_require_active_role_returns_value(self) -> None:
        ctx = OperationalContext(active_role="implementer")
        assert ctx.require_active_role() == "implementer"


class TestBuildOperationalContext:
    def test_returns_operational_context_instance(self) -> None:
        ctx = build_operational_context()
        assert isinstance(ctx, OperationalContext)

    def test_all_fields_none(self) -> None:
        ctx = build_operational_context()
        assert ctx.active_profile is None
        assert ctx.active_role is None
        assert ctx.tech_stack == frozenset()
```

### Test markers

Add `pytestmark = pytest.mark.unit` at the top of the file (after imports) so these tests are collected by the fast/unit marker filters.

### Validation

```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
python -m pytest tests/charter/test_invocation_context.py -x -v 2>&1 | tail -40
```

---

## Definition of Done

All of the following must hold before this WP is marked `for_review`:

1. `src/charter/invocation_context.py` exists with `ProjectContext`, `OperationalContext`, `ContextPreconditionError`, `build_operational_context`, and `__all__`.
2. `tests/charter/test_invocation_context.py` exists and covers all the cases listed in T014.
3. `tests/architectural/test_no_dead_symbols.py` line 405 has the four-symbol frozenset (not `frozenset()`).
4. `tests/architectural/_baselines.yaml` has `category_c_wp_in_flight_charter_scope: 4` with justification comment.
5. `src/specify_cli/context/` is untouched (run `git diff src/specify_cli/context/` — must be empty).
6. No `from specify_cli` or `import specify_cli` appears anywhere in `src/charter/invocation_context.py`.

### Final validation commands

```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty

# 1. Unit tests
python -m pytest tests/charter/test_invocation_context.py -x -q

# 2. Dead-symbol architectural test
python -m pytest tests/architectural/test_no_dead_symbols.py -x -q

# 3. Ratchet baseline meta-test
python -m pytest tests/architectural/test_ratchet_baselines.py -x -q

# 4. mypy strict on the new module
python -m mypy src/charter/invocation_context.py --strict

# 5. ruff
cd src && ruff check charter/invocation_context.py
cd ..

# 6. No specify_cli imports in authoritative surface
grep -n "specify_cli" src/charter/invocation_context.py && echo "VIOLATION" || echo "OK"

# 7. specify_cli/context/ untouched
git diff src/specify_cli/context/
```
