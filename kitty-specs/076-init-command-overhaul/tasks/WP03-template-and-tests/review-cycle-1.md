## Review Cycle 1 — Changes Required

### Issue 1 (BLOCKER): init.py modified — out of scope for WP03

`src/specify_cli/cli/commands/init.py` is NOT in WP03's `owned_files` list. WP02 (different lane) already cleaned the `github_client` import from `init.py`. WP03 has added no-op stubs (`_NoOpHttpClient`, `build_http_client`, `parse_repo_slug`, `download_and_extract_template`) to `init.py`, which will cause a merge conflict when lanes merge.

**Required fix:** Revert all changes to `src/specify_cli/cli/commands/init.py`. The diff must produce empty output for:
```bash
git diff kitty/mission-076-init-command-overhaul..HEAD -- src/specify_cli/cli/commands/init.py
```

The stubs are not needed anywhere — `build_http_client`, `parse_repo_slug`, and `download_and_extract_template` were removed from init.py by WP02 and must simply not exist in this lane's view of that file.

### Issue 2 (BLOCKER): get_local_repo_root moved to template/__init__.py instead of deleted

T019 Part B says: **Remove `get_local_repo_root()`** — delete it entirely. Instead, the implementation moved it from `manager.py` into `src/specify_cli/template/__init__.py` as a re-implementation.

`get_local_repo_root` must not exist anywhere under `src/specify_cli/template/`:
```bash
grep -r "get_local_repo_root" src/specify_cli/template/
```
Must return 0 results.

**Required fix:**
1. Remove `get_local_repo_root` function definition from `src/specify_cli/template/__init__.py`
2. Remove `"get_local_repo_root"` from the `__all__` list in `__init__.py`
3. Remove the `import os`, `from pathlib import Path`, and `from rich.console import Console` imports from `__init__.py` if they were added only to support `get_local_repo_root` (check whether other exports still need them)
4. Any callers of `get_local_repo_root` in this lane must be updated to not call it (it should already have been removed from `init.py` by WP02)

### Issue 3 (MINOR): Test count is 13, spec requires 14

T022 specifies 14 test cases. The test `test_ensure_runtime_success_bootstraps` (FR-003, second row) is missing from `tests/specify_cli/cli/commands/test_init_integration.py`.

**Required fix:** Add `test_ensure_runtime_success_bootstraps` — when `ensure_runtime()` succeeds, the global runtime bootstrap is confirmed (e.g., the mocked `ensure_runtime` was called once).

---

### Passing criteria (for reference — these already pass and must remain passing)

- `src/specify_cli/template/github_client.py` deleted: PASS
- `tests/specify_cli/cli/commands/test_init_doctrine.py` deleted: PASS
- 13 of 14 integration tests green: PASS (fix Issue 3 to reach 14)
- `mypy --strict` on `manager.py`: PASS (no output = clean)
