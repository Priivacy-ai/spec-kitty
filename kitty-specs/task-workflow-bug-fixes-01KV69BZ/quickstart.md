# Quickstart: Task Workflow Bug Fixes

## For the implementer

Two independent fixes. Either can be started first; they do not share code.

---

### Fix A — IC-01: map-requirements spec.md path (P1)

**File**: `src/specify_cli/cli/commands/agent/tasks.py`

1. Locate the `map_requirements` function (~line 3429).
2. Find the block starting around line 3533:
   ```python
   feature_dir = resolve_feature_dir_for_slug(main_repo_root, mission_slug)
   ...
   spec_md = feature_dir / SPEC_MD_FILENAME
   ```
3. Add the topology-blind resolver for spec.md:
   ```python
   primary_dir = primary_feature_dir_for_mission(main_repo_root, mission_slug)
   spec_md = primary_dir / SPEC_MD_FILENAME
   ```
4. Confirm `primary_feature_dir_for_mission` is imported from `specify_cli.missions.feature_dir_resolver`. If not, add it.
5. `feature_dir` (the topology-aware path) must remain in place for WP file access downstream.

**Verify**: `mypy --strict src/specify_cli/cli/commands/agent/tasks.py` — no new errors.

---

### Fix B — IC-02: validate_glob_matches error hint (P2)

**File**: `src/specify_cli/ownership/validation.py`

1. Locate `validate_glob_matches` (~line 319).
2. Find the `else` branch that handles literal zero-match (~line 370).
3. Replace the trailing hint:
   ```python
   # BEFORE
   msg += (
       " If this file will be created by this WP, add it to "
       "'create_intent' in the WP frontmatter."
   )
   # AFTER
   msg += (
       " If this file will be created during implementation, "
       f"declare it in the WP frontmatter:\n  create_intent:\n    - {pattern}"
   )
   ```

**Verify**: `mypy --strict src/specify_cli/ownership/validation.py` — no new errors.

---

### Tests — IC-03

**IC-01 regression test** (add to relevant test file under `tests/specify_cli/`):
- Arrange: create a temp directory to simulate a coord worktree existing; mock or stub `CoordinationWorkspace.worktree_path` to return that temp dir.
- Act: call the resolver path that `map_requirements` uses for spec.md.
- Assert: the returned path is under the primary checkout, not the mock coord worktree.

**IC-02 regression test** (add to `tests/specify_cli/` ownership test file):
- Arrange: build an `OwnershipManifest` with `owned_files` containing a literal path absent from the tmp repo root; pass no `create_intent`.
- Act: call `validate_glob_matches(manifests, tmp_path)`.
- Assert: `result.passed is False`; `"create_intent"` in `result.errors[0]`; the absent path string in `result.errors[0]`.

---

### Local test run

```bash
# Parallel run (fastest):
PWHEADLESS=1 pytest tests/specify_cli/ -n auto --dist loadfile -p no:cacheprovider -q

# Targeted (during development):
PWHEADLESS=1 pytest tests/specify_cli/ownership/ tests/specify_cli/cli/ -q
```

Both `ruff check .` and `mypy --strict src/` must pass before opening the PR.
