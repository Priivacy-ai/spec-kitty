---
work_package_id: WP01
title: Production Delegation Shim
dependencies: []
requirement_refs:
- C-001
- C-002
- C-003
- C-006
- FR-001
- FR-002
- FR-003
- FR-004
- NFR-002
- NFR-003
- NFR-004
tracker_refs: []
planning_base_branch: feat/locate-project-root-consolidation
merge_target_branch: feat/locate-project-root-consolidation
branch_strategy: Planning artifacts for this mission were generated on feat/locate-project-root-consolidation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/locate-project-root-consolidation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-locate-project-root-consolidation-01KV5SX1
base_commit: c29ee0790efd383097160821e2679409b4c9f997
created_at: '2026-06-15T14:54:24.352240+00:00'
subtasks:
- T001
- T002
- T003
agent: claude
shell_pid: '73512'
history:
- date: '2026-06-15'
  event: Created during /spec-kitty.tasks by Architect Alphonso
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/core/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/core/project_resolver.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load implementer-ivan
```

This sets your role scope, boundaries, and governance context for this work package.

---

## Objective

Replace the 7-line `.kittify` walk body in `src/specify_cli/core/project_resolver.py::locate_project_root` with a deferred-import delegation shim that calls the authoritative implementation in `src/specify_cli/core/paths.py`. Add the rationale docstring required by C-006. Confirm static analysis passes with zero new violations.

**This is a ~7-line production change.** The function body shrinks to two lines of logic; the docstring grows to explain the shim contract.

---

## Context

**Why this change:** Three implementations of `locate_project_root` exist. The one in `project_resolver.py` is a plain `.kittify` walk that ignores `SPECIFY_REPO_ROOT` and git worktree pointers. Four callers import from `project_resolver` and therefore silently misresolve the project root in CI/CD and worktree environments. The fix makes `project_resolver.locate_project_root` a transparent shim into the authoritative `paths.locate_project_root`.

**Why deferred import (not module-level):** `core/__init__.py` imports from `project_resolver`, and `project_resolver` would then import from `paths`. If the import were at module level, Python's import system could trigger `specify_cli` package initialisation before it finishes loading, causing a cycle. The deferred import (inside the function body) fires only at call time, when the package is fully loaded. This is the same pattern already used by `paths.py` itself for its `git_ops` and `feature_dir_resolver` imports. Removing the deferred pattern to a module-level import is a regression — do not do it.

**Root diagnosis (Debugger Debbie, 2026-06-15):** Behavioral divergence began at commit `2e071e8ad` when `SPECIFY_REPO_ROOT` was added to `paths.py` without a matching change to `project_resolver.py`. The split was acknowledged in commit `8431dd931` and tracked as issue #1971.

---

## Branch Strategy

**Planning base branch:** `feat/locate-project-root-consolidation`  
**Final merge target:** `feat/locate-project-root-consolidation`  
**Execution workspace:** allocated per `lanes.json` — your agent runtime will resolve the exact worktree path via `spec-kitty agent action implement WP01 --agent claude`.

---

## Subtask T001 — Replace walk body with deferred delegation shim

**Purpose:** Remove the 7-line `.kittify` directory walk from `locate_project_root` and replace it with a single call to `paths.locate_project_root`, using a deferred import.

**File to change:** `src/specify_cli/core/project_resolver.py`

**Current body (lines ~8–40, approximately):**
```python
def locate_project_root(start: Path | None = None) -> Path | None:
    """Walk upwards from *start* (or CWD) to find the directory that owns .kittify.
    
    NOTE (#1971 — three-way resolver consolidation, deferred): ...
    """
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".kittify").is_dir():
            return candidate
    return None
```

**Replacement body:**
```python
def locate_project_root(start: Path | None = None) -> Path | None:
    """Delegates to the authoritative implementation in :mod:`specify_cli.core.paths`.

    All resolution authority — ``SPECIFY_REPO_ROOT`` env-var check (Tier 1),
    git worktree ``.git`` pointer following (Tier 2), and ``.kittify`` directory
    walk (Tier 3) — lives in :func:`specify_cli.core.paths.locate_project_root`.

    The import is deferred to the function body (not module-level) to preserve
    import-cycle safety: ``core/__init__.py`` imports from this module, and a
    module-level import of ``paths`` here could trigger ``specify_cli`` package
    initialisation before it finishes loading. The deferred pattern fires only at
    call time, after the package is fully loaded. This is the same mechanism used
    by ``paths.py`` itself for its ``git_ops`` and ``feature_dir_resolver``
    deferred imports. Reverting to a module-level import is a regression. (#1971)
    """
    from specify_cli.core.paths import locate_project_root as _authoritative
    return _authoritative(start)
```

**Steps:**
1. Read `src/specify_cli/core/project_resolver.py` in full.
2. Identify the `locate_project_root` function (starts around line 8, ends before `resolve_template_path`).
3. Replace only the function (docstring + body). Do not touch anything else in the file.
4. Verify that `resolve_template_path` below it is unchanged.
5. Verify the module-level imports at the top (`from __future__ import annotations`, `from pathlib import Path`) are still present — they are still needed for `resolve_template_path`.

**Validation:**
- [ ] `locate_project_root` body is exactly two lines: the deferred import and the return call
- [ ] `resolve_template_path` is byte-for-byte identical to the original
- [ ] Module-level imports are unchanged
- [ ] No walk logic (`for candidate in [current, ...]`) remains anywhere in the function

---

## Subtask T002 — Write rationale docstring (C-006)

**Purpose:** The docstring written in T001 already satisfies C-006. This subtask is a verification and polish pass — confirm the docstring covers all six required points.

**C-006 requires the docstring to explain:**
1. That this function is a shim (not the canonical implementation)
2. Where the authority lives (`specify_cli.core.paths.locate_project_root`)
3. What "authority" means (Tier 1 env-var, Tier 2 worktree, Tier 3 walk)
4. Why the import is deferred (import-cycle safety)
5. The mechanism that makes deferral safe (call-time resolution)
6. A reference to issue #1971

**Steps:**
1. Read the docstring written in T001.
2. Check each of the six points above is present.
3. If any point is missing, add it. Keep the docstring concise (under 20 lines).
4. Confirm the `:func:` and `:mod:` cross-references use Sphinx-compatible syntax so they render correctly in generated docs.

**Validation:**
- [ ] Docstring references `specify_cli.core.paths.locate_project_root` by name
- [ ] Docstring mentions `SPECIFY_REPO_ROOT` (Tier 1)
- [ ] Docstring mentions worktree pointer following (Tier 2)
- [ ] Docstring explains deferred import is intentional and why
- [ ] Docstring includes `(#1971)` reference

---

## Subtask T003 — Verify static analysis (mypy + ruff)

**Purpose:** Confirm the change introduces zero new type errors or lint violations before tests are written.

**Steps:**
1. Run: `mypy --strict src/specify_cli/core/project_resolver.py`
   - Expected: `Success: no issues found in 1 source file`
   - If errors: fix them in `project_resolver.py` — do NOT add `# type: ignore`
2. Run: `ruff check src/specify_cli/core/project_resolver.py`
   - Expected: no output (zero violations)
   - If violations: fix the code — do NOT add `# noqa`
3. Run a quick smoke import: `python -c "from specify_cli.core.project_resolver import locate_project_root; print('OK')"`
   - Expected: `OK`
   - If import error: diagnose and fix (likely a missing deferred import or syntax error)
4. Measure import time (NFR-004): `python -c "import time; t=time.time(); import specify_cli.core.project_resolver; print(time.time()-t)"`
   - Expected: < 0.005 (5 ms) — the deferred import fires at call time, not at module load
   - If ≥ 5 ms: the deferred import leaked to module scope; check for accidental top-level `from specify_cli.core.paths import ...`

**Common failure modes:**
- `error: Module "specify_cli.core.paths" has no attribute "locate_project_root"` — check the import path spelling
- `ruff: C901 Function is too complex` — should not occur for a 2-line function; if it does, check for leftover walk code
- `ModuleNotFoundError: No module named 'specify_cli'` — run from the repo root with `.venv` active: `.venv/bin/mypy --strict src/specify_cli/core/project_resolver.py`

**Validation:**
- [ ] `mypy --strict` exits 0 with "no issues found"
- [ ] `ruff check` exits 0 with no output
- [ ] `python -c "from specify_cli.core.project_resolver import locate_project_root; print('OK')"` prints `OK`
- [ ] Import time measurement prints < 0.005

---

## Definition of Done

- [ ] `src/specify_cli/core/project_resolver.py` contains the deferred delegation shim with rationale docstring
- [ ] No walk logic remains in the file
- [ ] `resolve_template_path` is unchanged
- [ ] `mypy --strict` passes with zero errors
- [ ] `ruff check` passes with zero violations
- [ ] Import smoke test passes
- [ ] Import time measurement prints < 0.005 (NFR-004)

## Risks

- **Cycle regression**: If someone later "cleans up" the deferred import to a module-level import, the cycle risk returns. The docstring is the guard — make it explicit.
- **Incomplete replacement**: If any of the walk body lines remain (e.g., the `for candidate` loop), the shim is not complete and tests in WP02 will catch it.

## Reviewer Guidance

- Confirm `locate_project_root` body is exactly 2 lines (import + return)
- Confirm `resolve_template_path` is untouched (compare git diff carefully)
- Confirm no module-level import of `specify_cli.core.paths` was added
- Confirm docstring covers all 6 C-006 points listed in T002
