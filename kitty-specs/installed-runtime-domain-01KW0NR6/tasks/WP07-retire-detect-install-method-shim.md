---
work_package_id: WP07
title: Retire detect_install_method() shim — migrate all remaining call sites
dependencies:
- WP06
requirement_refs:
- FR-022
- NFR-008
tracker_refs: []
planning_base_branch: feat/installed-runtime-domain
merge_target_branch: feat/installed-runtime-domain
branch_strategy: Planning artifacts for this mission were generated on feat/installed-runtime-domain. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/installed-runtime-domain unless the human explicitly redirects the landing branch.
subtasks:
- T032
- T033
- T034
- T035
- T036
- T037
phase: Phase 7 - shim retirement (strangler step 7)
assignee: ''
agent: ''
history:
- at: '2026-06-26T00:00:00Z'
  actor: system
  action: Prompt generated via spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/compat/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/upgrade.py
- src/specify_cli/compat/planner.py
- src/specify_cli/compat/__init__.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – Retire detect_install_method() shim

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: src/specify_cli/compat/`.

---

## Objective

Retire the `detect_install_method()` shim introduced in WP02. Migrate the remaining
call sites in `upgrade.py` (×2) and `planner.py` (×1) to `detect_runtime().install_method`.
Update `compat/__init__.py` to remove the shim from the public API and add
`detect_runtime`. Delete the shim function.

After this WP, `grep -rn "detect_install_method" src/` must return **zero production hits**.

## Context & Constraints

Ground truth — read before editing:
- [`spec.md`](../spec.md) FR-022, NFR-008
- [`research.md`](../research.md) §2 (caller audit table — all 7 sites)
- [`plan.md`](../plan.md) IC-07

**Pre-conditions (verify before starting):** WP04 migrated `review/__init__.py` (site 1). WP05 migrated `upgrade_ux.py` (sites 5+6). WP06 handled `version_checker.py` and `schema_version.py` if not deferred. The only remaining sites in production code are:
- site 2: `upgrade.py` line 350
- site 3: `upgrade.py` line 668
- site 4: `planner.py` line 896
- site 7: `compat/__init__.py` line 66+120 (re-export, not a call site)

**Deletion gate (mandatory before merge):**
```bash
grep -rn "detect_install_method" src/specify_cli/ | grep -v "def detect_install_method\|# noqa\|install_method.py"
```
Expected: **zero lines**.

**C-001 lifted**: After this WP, the constraint that `detect_install_method()` must remain callable is fully satisfied and the function is retired.

## Branch Strategy

- **Planning base branch**: `feat/installed-runtime-domain`
- **Merge target branch**: `feat/installed-runtime-domain`

## Subtasks & Detailed Guidance

### T032 — Enumerate remaining call sites

Run the audit command before any edits:
```bash
grep -rn "detect_install_method" src/specify_cli/ | grep -v "__pycache__\|.pyc"
```

Expected results (from research.md §2):
- `upgrade.py:326` — deferred import line
- `upgrade.py:350` — call site 2: `install_method = detect_install_method()`
- `upgrade.py:665` — deferred import (inside function)
- `upgrade.py:668` — call site 3: `method = detect_install_method()`
- `planner.py:757` — deferred import
- `planner.py:896` — call site 4: `install_method = detect_install_method()`
- `compat/__init__.py:18` — import
- `compat/__init__.py:66` — re-export
- `compat/__init__.py:120` — `__all__` entry
- `install_method.py` — definition (expected, will be kept)
- `runtime.py` — shim definition (expected, to be deleted)

Record the exact lines found for reference during T033–T036.

### T033 — Migrate `upgrade.py` sites 2 and 3

**Site 2** (`upgrade.py` around line 350, in `_agent_check_payload` or equivalent):
```python
# Old:
from specify_cli.compat._detect.install_method import detect_install_method
install_method = detect_install_method()

# New:
from specify_cli.compat._detect.runtime import detect_runtime
install_method = detect_runtime().install_method
```

If `runtime` is already available in the calling context (because an earlier call to
`detect_runtime()` was already added in this file), reuse it — do not call
`detect_runtime()` twice.

**Site 3** (`upgrade.py` around line 668, in schema-version check branch):
Same replacement pattern. The deferred import at line 665 becomes:
```python
from specify_cli.compat._detect.runtime import detect_runtime
```

After both migrations, remove any now-unused `detect_install_method` imports from `upgrade.py`.

### T034 — Migrate `planner.py` site 4

**Site 4** (`planner.py` around line 896, in `_plan_impl` function):
```python
# Old (deferred import at line 757):
from specify_cli.compat._detect.install_method import detect_install_method
install_method = detect_install_method()

# New (deferred import inside function body, or update line 757):
from specify_cli.compat._detect.runtime import detect_runtime
install_method = detect_runtime().install_method
```

If `planner.py` is already constructing an `InstalledCliRuntime` elsewhere in `_plan_impl`
(because WP03 changed `build_upgrade_hint()` to call `detect_runtime()`), consider
whether the two calls can be unified into one `runtime = detect_runtime()` at the top
of `_plan_impl`. Prefer a single call (SC-001).

Remove any now-unused `detect_install_method` imports from `planner.py`.

### T035 — Update `compat/__init__.py` public API

In `compat/__init__.py`:

1. Remove `detect_install_method` from the import line (around line 66):
   ```python
   # Old:
   from specify_cli.compat._detect.install_method import InstallMethod, detect_install_method
   # New:
   from specify_cli.compat._detect.install_method import InstallMethod
   ```

2. Add `detect_runtime` to the public re-export (alongside `InstallMethod`):
   ```python
   from specify_cli.compat._detect.runtime import detect_runtime
   ```

3. Update `__all__` (around line 120):
   - Remove `"detect_install_method"` entry
   - Add `"detect_runtime"` entry

4. Verify the existing `from specify_cli.compat import InstallMethod, detect_install_method` imports in consumer code do not exist in the test suite or sample code. Run a grep to confirm no test imports `detect_install_method` from `compat`:
   ```bash
   grep -rn "detect_install_method" tests/
   ```
   If any test imports it, update those tests to use `detect_runtime().install_method`.

### T036 — Delete the `detect_install_method()` shim from `runtime.py`

In `src/specify_cli/compat/_detect/runtime.py`, delete the shim function added in WP02:
```python
# DELETE this entire function:
def detect_install_method() -> "InstallMethod":
    """Backward-compatible shim..."""
    return detect_runtime().install_method
```

The original `detect_install_method()` in `install_method.py` remains in place (it is
the canonical definition and may be used by other internal paths, e.g., `_is_uv_tool_install()`).
Only the shim in `runtime.py` is deleted.

After deletion, verify that `install_method.py` still has the canonical definition:
```bash
grep -n "def detect_install_method" src/specify_cli/compat/_detect/install_method.py
```
Expected: exactly one result.

### T037 — Final audit + green-gate

**Mandatory deletion gate:**
```bash
grep -rn "detect_install_method" src/specify_cli/ | grep -v "def detect_install_method\|install_method.py"
```
Expected: **zero lines**. Do not proceed to commit until this passes.

**Test suite:**
```bash
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -q
pytest tests/architectural/test_no_legacy_terminology.py -q
```

**ruff + mypy on all modified files:**
```bash
ruff check src/specify_cli/cli/commands/upgrade.py src/specify_cli/compat/planner.py src/specify_cli/compat/__init__.py src/specify_cli/compat/_detect/runtime.py
mypy src/specify_cli/cli/commands/upgrade.py src/specify_cli/compat/planner.py src/specify_cli/compat/__init__.py src/specify_cli/compat/_detect/runtime.py
```

Zero issues required before merging.

## Success Criteria

- [ ] `grep -rn "detect_install_method" src/` returns zero production hits (excluding the canonical definition in `install_method.py`)
- [ ] `upgrade.py` sites 2 and 3 use `detect_runtime().install_method`
- [ ] `planner.py` site 4 uses `detect_runtime().install_method`
- [ ] `compat/__init__.py` exports `detect_runtime`; `detect_install_method` removed from `__all__`
- [ ] Shim in `runtime.py` deleted
- [ ] Full test suite green; zero ruff/mypy issues
- [ ] SC-005: no migration step has introduced a regression in the full test suite

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Test imports `detect_install_method` from `compat` directly | Grep `tests/` before deleting the re-export; update any such tests |
| `planner.py` already calls `detect_runtime()` via `build_upgrade_hint()` (WP03) | Consolidate into single `runtime = detect_runtime()` call; avoid double-probe |
| `install_method.py` canonical function mistakenly deleted | Deletion gate grep explicitly excludes `install_method.py`; double-check the file after WP07 |
| WP06 was deferred — `version_checker.py` / `schema_version.py` still call shim | If WP06 was deferred, these files use deferred-import `detect_install_method` from `install_method.py` (not the shim in `runtime.py`) — the canonical function is NOT deleted in this WP, so those sites remain green until a follow-up addresses FR-021 |
