---
work_package_id: WP02
title: Fix acceptance.py Import Ordering
dependencies: []
requirement_refs:
- FR-001
planning_base_branch: feat/080-ci-hardening-and-lint-cleanup
merge_target_branch: feat/080-ci-hardening-and-lint-cleanup
branch_strategy: Planning artifacts for this feature were generated on feat/080-ci-hardening-and-lint-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/080-ci-hardening-and-lint-cleanup unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-080-ci-hardening-and-lint-cleanup
base_commit: a9a38afc46d26b59fa7d74715a584b845220ae00
created_at: '2026-04-09T14:41:27.300529+00:00'
subtasks:
- T006
- T007
- T008
- T009
shell_pid: "50468"
agent: "claude"
history:
- date: '2026-04-09'
  action: created
  actor: claude-sonnet-4-6
authoritative_surface: src/specify_cli/acceptance.py
execution_mode: code_change
owned_files:
- src/specify_cli/acceptance.py
tags: []
---

# WP02 — Fix acceptance.py Import Ordering

## Objective

Resolve the E402 cascade in `src/specify_cli/acceptance.py` — a `logger =
logging.getLogger(__name__)` call placed before other imports causes 8 E402 violations on
every subsequent import line. Fixing the root cause also unblocks cleanup of the UP035
(deprecated typing imports) and F401 (unused imports) violations in the same file.

After this WP, `ruff check src/specify_cli/acceptance.py` and `mypy src/specify_cli/acceptance.py` both exit 0.

## Context

**Root cause:** Python module-level code that runs before the import block produces E402 on
every import that follows. The logger init at line 10 is the culprit. The correct fix is to
move it after all imports.

**Doctrine:** DIRECTIVE_030 (quality gate), DIRECTIVE_025 (boy scout rule — this fix goes
slightly beyond the minimum required but is the correct approach to eliminate the cascade).

**This WP is part of Batch 1 (parallel).** Only one file is touched. Safe to implement
simultaneously with WP01, WP03–WP05.

## Subtask Guidance

### T006 — Move logger init below imports (E402 root cause)

**File:** `src/specify_cli/acceptance.py`

Read the file first to understand the current import block structure. The logger initialization
`logger = logging.getLogger(__name__)` appears at approximately line 10, before several
`import` and `from ... import` statements.

**Fix:**
1. Identify the last import statement in the file (the line with the final `import` or
   `from ... import`).
2. Move `logger = logging.getLogger(__name__)` to the line immediately after the last import.
3. If there is a blank line separating the stdlib imports from the third-party imports, and
   another blank line separating third-party from local imports, place the logger init after
   the final local import block, separated by one blank line.

**Expected structure after fix:**
```python
# stdlib imports
import logging
import re
from collections.abc import Iterable, MutableMapping  # (may be removed in T007/T008)

# third-party imports (if any)
...

# local imports
from specify_cli.some_module import something

# Module-level setup (after all imports)
logger = logging.getLogger(__name__)
```

**Validation (partial — full validation in T009):**
```bash
ruff check --select E402 src/specify_cli/acceptance.py
```
Should return no E402 violations.

---

### T007 — Remove unused imports (F401: MutableMapping, extract_scalar, find_repo_root)

**File:** `src/specify_cli/acceptance.py`

After fixing E402, identify the F401 violations. Three imports are unused:
- `MutableMapping` (from `collections.abc` or `typing`)
- `extract_scalar` (from a local module)
- `find_repo_root` (from a local module)

**Fix:** Delete the unused import lines entirely.

Before deleting, run a quick search to confirm they are not used elsewhere in the file:
```bash
grep -n "MutableMapping\|extract_scalar\|find_repo_root" src/specify_cli/acceptance.py
```

If any symbol appears in a function body or type annotation, do NOT delete it — the F401
error would be incorrect (this can happen with re-exports or `__all__` usage). Check for
`__all__` at the top of the file.

**Validation:**
```bash
ruff check --select F401 src/specify_cli/acceptance.py
```

---

### T008 — Replace deprecated `typing.*` with builtins/`collections.abc` (UP035)

**File:** `src/specify_cli/acceptance.py`

UP035 flags imports from `typing` that have direct equivalents in Python 3.9+ builtins or
`collections.abc`. The affected imports are typically: `Dict`, `List`, `Set`, `Tuple`,
`Iterable`, `Callable`, `Optional`.

**Fix approach (auto-fix recommended per C-004):**
```bash
ruff check --fix --select UP035 src/specify_cli/acceptance.py
```

Ruff will rewrite the imports and update type annotations in the file. Review the diff to
confirm:
1. `from typing import Dict, List, Set` → removed (builtins `dict`, `list`, `set` used inline)
2. `from typing import Iterable` → `from collections.abc import Iterable`
3. `from typing import Optional` → removed; `Optional[X]` → `X | None`

**Note:** If any annotation was `Dict[str, Any]`, ruff rewrites it as `dict[str, Any]`.
If the file has `from __future__ import annotations` at the top, this syntax is valid even on
Python 3.8. Check whether this import exists; if not, Python 3.9+ is required for the builtin
generic syntax — which is fine since the codebase targets 3.11+.

**Validation:**
```bash
ruff check --select UP035 src/specify_cli/acceptance.py
```
All UP035 violations should be gone.

---

### T009 — Verify `acceptance.py` passes ruff + mypy; run affected tests

**Final verification gate** (DIRECTIVE_030):

```bash
# Full ruff check for the file
ruff check src/specify_cli/acceptance.py

# Full mypy check for the file
mypy src/specify_cli/acceptance.py

# Run tests that exercise acceptance.py
# The acceptance module is used by charter validation workflows; run:
pytest tests/ -k "acceptance" -m "fast or git_repo" -q
```

If `mypy` reports errors after the UP035 substitutions:
- `type[X] is not subtype of type[Y]` — check if a function's return type annotation needs
  updating to match the new generic form
- `Cannot determine type of ...` — may happen if `Optional` was removed improperly; ensure
  `X | None` syntax is used correctly

If tests fail:
- Check whether the removed imports (`find_repo_root`, `extract_scalar`) were actually used
  in a code path that tests exercise — restore them if needed

**Commit the changes** once all gates pass.

## Definition of Done

- [ ] `ruff check src/specify_cli/acceptance.py` exits 0 (no E402, F401, UP035, or other violations)
- [ ] `mypy src/specify_cli/acceptance.py` exits 0
- [ ] All acceptance-related tests pass
- [ ] `logger = logging.getLogger(__name__)` appears after all import statements
- [ ] No unused imports remain
- [ ] No `typing.Dict`, `typing.List`, `typing.Set`, `typing.Tuple` remain (replaced with builtins or `collections.abc`)
- [ ] Changes committed to `feat/080-ci-hardening-and-lint-cleanup`

## Risks

- **Type annotation breakage from UP035 rewrite:** Ruff's auto-fix is reliable but review
  the diff — particularly for complex nested generic types like `Dict[str, List[Tuple[int, str]]]`.
- **Hidden usage of removed imports:** `extract_scalar` or `find_repo_root` may appear in
  a string annotation (`"find_repo_root"`) that `grep` misses. Run mypy after removal to
  catch any such reference.
- **Logger used before first import in some call paths:** The logger placement change is
  safe as long as `logging.getLogger(__name__)` is a pure module-level call (no side effects
  beyond registering the logger). Confirm this is the case.

## Reviewer Guidance

The diff should show: (1) `logger = ...` line moved down, (2) 2–3 import lines deleted,
(3) `typing` import rewrites. Any behavioral change in the file's logic would be a red flag.
The function bodies should be unchanged.

## Activity Log

- 2026-04-09T14:41:27Z – claude – shell_pid=50468 – Assigned agent via action command
