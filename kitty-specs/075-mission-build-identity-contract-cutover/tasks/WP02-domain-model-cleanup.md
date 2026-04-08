---
work_package_id: WP02
title: Domain Model Cleanup
dependencies: []
requirement_refs:
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-075-mission-build-identity-contract-cutover
base_commit: 5bb0632a2e1dfadffdc36aa1c63a25c0eddb6ba7
created_at: '2026-04-08T05:24:18.436936+00:00'
subtasks:
- T009
- T010
- T011
- T012
- T013
- T014
- T015
shell_pid: '6359'
history:
- date: '2026-04-08'
  actor: planner
  action: created
authoritative_surface: src/specify_cli/core/
execution_mode: code_change
mission_slug: 075-mission-build-identity-contract-cutover
owned_files:
- src/specify_cli/status/wp_metadata.py
- src/specify_cli/status/progress.py
- src/specify_cli/core/identity_aliases.py
- src/specify_cli/core/worktree.py
- tests/specify_cli/status/test_wp_metadata.py
- tests/specify_cli/core/test_identity_aliases.py
- tests/specify_cli/core/test_worktree.py
tags: []
---

# WP02 — Domain Model Cleanup

## Branch Strategy

- **Planning base**: `main`
- **Merge target**: `main`
- **Workspace**: allocated by `spec-kitty implement WP02` (lane-based worktree)
- **Command**: `spec-kitty implement WP02 --mission 075-mission-build-identity-contract-cutover`
- **Note**: Can run in parallel with WP01 (no shared files). If WP01 has not yet merged, run `mypy` with both branches' changes in mind — some mypy errors from WP01 changes may appear during WP02 development. The T015 gate requires both WPs to be merged before confirming full mypy pass.

## Objective

Remove the remaining `feature_slug` domain model artifacts:
1. The `feature_slug` optional field from `WPMetadata` (Pydantic model)
2. The `with_tracked_mission_slug_aliases` function — its module (`core/identity_aliases.py`) is deleted; its callers in `status/progress.py` are updated
3. The `core/worktree.py` reader that accesses `.feature_slug` on frontmatter objects (changed to `.mission_slug`)

After this WP, `feature_slug` exists only in explicit migration/upgrade code paths.

## Context

**WPMetadata** (`status/wp_metadata.py`): has `feature_slug: str | None = None` at line 74. This is a Pydantic model field — removing it means `WPMetadata(...).model_dump()` no longer emits `feature_slug`. Nothing in the runtime reads this field for feature_slug logic; it's a vestigial schema artifact.

**`core/identity_aliases.py`**: provides one public function, `with_tracked_mission_slug_aliases(enriched)`, which backfills `mission_slug` from `feature_slug` in an outgoing dict. After WP01 removes it from `status/models.py` and this WP removes it from `status/progress.py`, no callers remain and the module can be deleted.

Known callers of `identity_aliases`:
- `status/models.py` — removed by WP01
- `status/progress.py` — removed by this WP

**`core/worktree.py:123`**:
```python
mission_slug = wp_frontmatter.feature_slug or ""
```
This reads `.feature_slug` on a WPMetadata-like frontmatter object. After T010 removes the field from `WPMetadata`, mypy will flag this. Fix: change to `.mission_slug or ""`.

## Subtask Guidance

### T009 — Write failing test: WPMetadata.model_dump() has no feature_slug

**File**: `tests/specify_cli/status/test_wp_metadata.py`

```python
from specify_cli.status.wp_metadata import WPMetadata

def test_wp_metadata_model_dump_has_no_feature_slug():
    """WPMetadata.model_dump() must not emit feature_slug — Scenario 5."""
    meta = WPMetadata(wp_id="WP01", mission_slug="075-test-mission")
    dumped = meta.model_dump()
    assert "feature_slug" not in dumped, (
        f"feature_slug should not appear in model_dump output, got keys: {list(dumped.keys())}"
    )
```

Run — should FAIL (because the field exists). Proceed to T010 to make it green.

---

### T010 — Remove feature_slug field from WPMetadata

**File**: `src/specify_cli/status/wp_metadata.py`, line 74

Locate:
```python
feature_slug: str | None = None
```

Delete this line entirely.

Run T009's test — should now pass.

Also run `mypy --strict src/specify_cli/status/wp_metadata.py` — must pass. Then run `grep -r "\.feature_slug" src/specify_cli/` — the remaining hit in `core/worktree.py:123` will be caught and fixed in T013-T014.

---

### T011 — Write failing test: identity_aliases no longer backfills mission_slug

**File**: `tests/specify_cli/core/test_identity_aliases.py`

This test documents the current behavior so it's clear what is being removed. The failing version asserts the NEW behavior (no backfill):

```python
import pytest

def test_identity_aliases_module_is_deleted():
    """core.identity_aliases must not exist after this WP is merged."""
    with pytest.raises(ModuleNotFoundError):
        from specify_cli.core import identity_aliases  # noqa: F401
```

Run — should FAIL (module still exists). Proceed to T012 to make it green.

**Alternative if you prefer a softer test**: write a test that imports the module but asserts the backfill function does NOT exist, then make the function a no-op in preparation for deletion. The delete-module approach is cleaner and consistent with the spec's fail-closed philosophy.

---

### T012 — Remove identity_aliases from progress.py; delete core/identity_aliases.py

**Step 1 — Update `src/specify_cli/status/progress.py`**:

Find (line ~19):
```python
from specify_cli.core.identity_aliases import with_tracked_mission_slug_aliases
```
Delete this import.

Find the usage (line ~75):
```python
return with_tracked_mission_slug_aliases({
    "mission_slug": ...,
    ...
})
```
Replace with the unwrapped dict (same as T008 in WP01 for `status/models.py`).

Verify `mypy --strict src/specify_cli/status/progress.py` passes.

**Step 2 — Verify no remaining callers**:
```bash
grep -r "identity_aliases\|with_tracked_mission_slug_aliases" src/ --include="*.py"
```
Expected output: zero hits (the only two callers were `models.py` and `progress.py`). If hits remain, fix them before proceeding.

**Step 3 — Delete the module**:
```bash
rm src/specify_cli/core/identity_aliases.py
```

Run T011's test — should now pass (ModuleNotFoundError as expected).

Run `pytest tests/specify_cli/core/test_identity_aliases.py` — green.

---

### T013 — Write failing test: core/worktree.py reads mission_slug not feature_slug

**File**: `tests/specify_cli/core/test_worktree.py`

Write a test that verifies the worktree slug resolution uses `mission_slug`. The easiest approach is to construct a minimal WPMetadata-like object (or mock) with `mission_slug` set and `feature_slug` absent, then assert the function returns the right slug.

```python
from unittest.mock import MagicMock
from specify_cli.core import worktree  # import the module, don't call directly yet

def test_worktree_uses_mission_slug_not_feature_slug():
    """core/worktree.py must read .mission_slug, not .feature_slug, from frontmatter."""
    frontmatter = MagicMock()
    frontmatter.mission_slug = "075-my-mission"
    # After T010, feature_slug attribute no longer exists on WPMetadata.
    # The mock will raise AttributeError if .feature_slug is accessed.
    del frontmatter.feature_slug

    # Call the internal function that reads the slug (adjust import as needed)
    from specify_cli.core.worktree import _get_mission_slug_from_frontmatter  # or equivalent
    result = _get_mission_slug_from_frontmatter(frontmatter)
    assert result == "075-my-mission"
```

**Note**: If `core/worktree.py` does not expose a named helper, test the behavior through a higher-level function that exercises line 123. Adjust the test to the actual API surface.

Run — should FAIL or raise `AttributeError` (because the code reads `.feature_slug`). Proceed to T014.

---

### T014 — Update core/worktree.py:123

**File**: `src/specify_cli/core/worktree.py`, line 123

Locate:
```python
mission_slug = wp_frontmatter.feature_slug or ""
```

Replace with:
```python
mission_slug = wp_frontmatter.mission_slug or ""
```

Run T013's test — should pass.

Run `mypy --strict src/specify_cli/core/worktree.py` — must pass.

---

### T015 — Full test + mypy pass gate

This is a gate task, not a code change.

1. Run `grep -r "feature_slug" src/specify_cli/ --include="*.py" -l` and exclude known-acceptable locations:
   - `src/specify_cli/upgrade/feature_meta.py` (migration — acceptable)
   - `src/specify_cli/migration/rebuild_state.py` (migration — acceptable)
   Any other hit is a blocker. Fix before marking done.

2. Run `mypy --strict src/specify_cli/status/ src/specify_cli/core/` — zero errors required.

3. Run `pytest tests/specify_cli/status/ tests/specify_cli/core/ -v` — all green.

4. If WP01 has already merged to `main`, rebase or merge `main` into this branch and run the full suite: `pytest tests/ -x` — must be green.

## Definition of Done

- [ ] `WPMetadata.model_dump()` emits no `feature_slug` key — asserted by test (Scenario 5)
- [ ] `core/identity_aliases.py` does not exist — asserted by ModuleNotFoundError test
- [ ] `status/progress.py` imports nothing from `identity_aliases`
- [ ] `core/worktree.py` reads `.mission_slug` at the former `.feature_slug` location
- [ ] `grep -r "feature_slug" src/specify_cli/ --include="*.py" -l` returns only `upgrade/feature_meta.py` and `migration/rebuild_state.py`
- [ ] `mypy --strict` passes on all modified modules
- [ ] All tests green

## Risks

| Risk | Mitigation |
|------|-----------|
| Additional callers of `with_tracked_mission_slug_aliases` found beyond `models.py` and `progress.py` | The grep in T012 Step 2 will surface them; fix before deleting the module |
| `core/worktree.py` line 123 is inside a deeply nested function with no test coverage | Write the test against the public-facing function, not the internal line; use the CliRunner path if needed |

## Reviewer Guidance

- `rm src/specify_cli/core/identity_aliases.py` is the expected diff — confirm the file is absent
- `grep -r "feature_slug" src/specify_cli/ --include="*.py"` must return only migration-path files
- `WPMetadata` Pydantic model no longer has a `feature_slug` field — check the class definition
- `core/worktree.py:123` (post-change line number may shift) reads `.mission_slug`
