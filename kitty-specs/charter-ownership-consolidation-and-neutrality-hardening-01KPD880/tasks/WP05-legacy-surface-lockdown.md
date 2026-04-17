---
work_package_id: WP05
title: Legacy Surface Lockdown
dependencies:
- WP04
requirement_refs:
- FR-003
- FR-004
- FR-006
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
phase: Phase 2 — Regression gates
assignee: ''
agent: "claude:sonnet-4-6:implementer:implementer"
shell_pid: "13407"
history:
- timestamp: '2026-04-17T09:03:02Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: tests/specify_cli/charter/test_no_new_legacy_modules.py
execution_mode: code_change
owned_files:
- tests/specify_cli/charter/test_no_new_legacy_modules.py
tags: []
---

# Work Package Prompt: WP05 – Legacy Surface Lockdown

## Objective

Install the premortem mitigation for the "shim surface grows back" risk category (research.md pre-mortem item 1). A test that enumerates every file under `src/specify_cli/charter/` and fails if any file is not a thin re-export shim. This is the longer-term safety net behind WP04's per-WP checks.

## Context

The baseline state of `src/specify_cli/charter/` after WP04 lands:

- `__init__.py` — the deprecation-warning package, 4 metadata attributes + `_warnings.warn(...)` + ~108 lines of `from charter.* import ...` re-exports.
- `compiler.py`, `interview.py`, `resolver.py` — each a 9-line `sys.modules` aliasing shim with no declarations beyond the alias assignment.

Anything beyond this shape is a regression. A contributor adding `src/specify_cli/charter/new_thing.py` with real logic would silently undo the consolidation. This test catches that.

The approach mirrors the "allowed file set + content shape" guard pattern used elsewhere in the repo: enumerate the legal filenames, assert no others exist, and for each legal file assert its AST contains only the expected node shapes.

## Branch Strategy

Planning base branch is `main`; merge target is `main`. Execution worktree path is resolved by the runtime from `lanes.json`.

## Implementation Sketch

### Subtask T018 — Author `tests/specify_cli/charter/test_no_new_legacy_modules.py`

**File**: `tests/specify_cli/charter/test_no_new_legacy_modules.py` (new, ~140 lines).

Allowed filenames (the only four files permitted under `src/specify_cli/charter/`):

```python
ALLOWED_SHIM_FILES: frozenset[str] = frozenset({
    "__init__.py",
    "compiler.py",
    "interview.py",
    "resolver.py",
})
```

Two test cases:

```python
"""Premortem guard: the specify_cli.charter shim package must not regrow.

Contract: any file under src/specify_cli/charter/ beyond the 4 known shim
files is a regression of the Mission A consolidation. This test enumerates
the directory and fails with a named, actionable diagnostic if an unknown
file appears.

It is intentional that this test is strict. Adding a new file here is a
per-mission decision that must ship alongside an occurrence_map.yaml update
and a conscious owner review. Do NOT loosen this test to accommodate a PR.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


ALLOWED_SHIM_FILES: frozenset[str] = frozenset({
    "__init__.py",
    "compiler.py",
    "interview.py",
    "resolver.py",
})


@pytest.fixture(scope="module")
def shim_dir(repo_root: Path) -> Path:
    d = repo_root / "src" / "specify_cli" / "charter"
    assert d.is_dir(), f"Expected shim package at {d}"
    return d


def test_no_new_files_under_shim_package(shim_dir: Path) -> None:
    present = {p.name for p in shim_dir.iterdir() if p.is_file() and p.suffix == ".py"}
    unexpected = present - ALLOWED_SHIM_FILES
    assert not unexpected, (
        f"Unexpected file(s) under src/specify_cli/charter/: {sorted(unexpected)}.\n"
        f"The shim package is frozen at the 4 files in ALLOWED_SHIM_FILES.\n"
        f"If this file genuinely needs to exist, it belongs under src/charter/ "
        f"(the canonical owner), not under the legacy shim surface."
    )
```

The `repo_root` fixture is the same one authored in WP01. Import it or co-locate a conftest helper — do not duplicate the walk-to-find-pyproject.toml logic.

### Subtask T019 — Add content-shape assertions

Second test case: each shim file must match its expected AST shape.

Rules:

- **`compiler.py`, `interview.py`, `resolver.py`** — 9-line `sys.modules` aliasing shim. The AST must contain **no `ClassDef`**, **no `FunctionDef` or `AsyncFunctionDef`** at module level. Permitted top-level nodes: `Import`, `ImportFrom`, `Assign` (for the alias + any `__deprecated__` / `__canonical_import__` constants), `AnnAssign`, `Expr` (docstring).
- **`__init__.py`** — permitted nodes include `Expr` (docstring), `Import`, `ImportFrom`, `Assign` (for the `__deprecated__`, `__canonical_import__`, `__removal_release__`, `__deprecation_message__` constants), and a single top-level `Expr` whose value is a `Call` to `_warnings.warn(...)`. **No `ClassDef`** and **no `FunctionDef`** are permitted — the package is re-exports and metadata only.

```python
def _assert_shim_shape(path: Path) -> None:
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            raise AssertionError(
                f"{path.name} contains a top-level {type(node).__name__} "
                f"(name={node.name!r}). The shim package must stay re-export-only; "
                f"move the definition to src/charter/."
            )


@pytest.mark.parametrize("filename", sorted(ALLOWED_SHIM_FILES))
def test_shim_file_has_no_top_level_definitions(shim_dir: Path, filename: str) -> None:
    _assert_shim_shape(shim_dir / filename)
```

Optional (recommended): verify the three submodule shims each contain a `sys.modules[__name__] = sys.modules["charter.<submod>"]` assignment. A missed alias means the re-export silently breaks. This is cheap to check and closes the loop:

```python
def test_submodule_shims_alias_canonical_module(shim_dir: Path) -> None:
    for submod in ("compiler", "interview", "resolver"):
        src = (shim_dir / f"{submod}.py").read_text()
        assert f'sys.modules["charter.{submod}"]' in src, (
            f"{submod}.py does not alias sys.modules['charter.{submod}']. "
            f"The shim is broken — imports via specify_cli.charter.{submod} "
            f"will not resolve to the canonical module."
        )
```

### Subtask T020 — Document the guard's purpose in an in-file docstring

The module docstring at the top of the file (shown in T018) MUST state:

- This test is a premortem guard against regrowth of the legacy shim surface.
- Adding a file here is a per-mission decision (not a bypass to add inside an unrelated PR).
- The correct location for new logic is `src/charter/`.
- Loosening this test is a governance change and requires reviewer consensus + a contract update.

Reviewers will verify the docstring covers these four points.

## Files

- **New**: `tests/specify_cli/charter/test_no_new_legacy_modules.py`

## Definition of Done

- [ ] Test file exists at the specified path.
- [ ] `pytest tests/specify_cli/charter/test_no_new_legacy_modules.py -v` passes on baseline.
- [ ] `ALLOWED_SHIM_FILES` is a `frozenset[str]` with exactly 4 entries matching the four shim files.
- [ ] Parametrized shape test covers all 4 files and rejects any `ClassDef`/`FunctionDef` at module level.
- [ ] Submodule alias test asserts the `sys.modules` line is present in all three submodule shims.
- [ ] Module docstring covers the four governance points from T020.
- [ ] `mypy --strict tests/specify_cli/charter/test_no_new_legacy_modules.py` passes.

## Risks

- **Fixture duplication**: if this WP imports a `repo_root` fixture from WP01's test, it creates a cross-test-file dependency. Preferred: add `repo_root` to a shared `tests/conftest.py` (if not already there). Acceptable fallback: each test file resolves `repo_root` independently via `Path(__file__).resolve().parents[N]` walking up to `pyproject.toml`.
- **False-positive on legitimate additions**: if a future mission genuinely needs to add a module here, the test will fail. That is the desired behavior — loosening it is a governance decision, not a PR-level shortcut.
- **Legitimate metadata drift in `__init__.py`**: if WP07 adds a new metadata constant (e.g., `__removal_pr__`), the AST check must still pass because `Assign` nodes are permitted. Do NOT over-tighten the shape check to enumerate exact metadata names.

## Reviewer Checklist

- [ ] `ALLOWED_SHIM_FILES` enumerates exactly `__init__.py`, `compiler.py`, `interview.py`, `resolver.py` — no more, no less.
- [ ] The unexpected-file test fails with a message naming the offending file AND pointing at `src/charter/` as the canonical location.
- [ ] No top-level `ClassDef`/`FunctionDef` is allowed in any of the four files.
- [ ] The submodule alias check covers all three submodule shims.
- [ ] The docstring covers premortem purpose, correct-location guidance, and the governance-change caveat.

## Activity Log

- 2026-04-17T09:50:57Z – claude:sonnet-4-6:implementer:implementer – shell_pid=13407 – Started implementation via action command
