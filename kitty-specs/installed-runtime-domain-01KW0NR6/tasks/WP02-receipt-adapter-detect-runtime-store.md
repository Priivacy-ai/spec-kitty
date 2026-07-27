---
work_package_id: WP02
title: UvReceiptReader + detect_runtime() shim + UpgradeAttemptStore
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-003
- FR-007
- FR-013
- FR-015
- FR-017
- NFR-001
- NFR-003
- NFR-005
- NFR-006
- NFR-009
tracker_refs: []
planning_base_branch: feat/installed-runtime-domain
merge_target_branch: feat/installed-runtime-domain
branch_strategy: Planning artifacts for this mission were generated on feat/installed-runtime-domain. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/installed-runtime-domain unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
- T013
phase: Phase 2 - Adapter + runtime detection + store (strangler step 2)
assignee: ''
agent: ''
shell_pid: '1100822'
history:
- at: '2026-06-26T00:00:00Z'
  actor: system
  action: Prompt generated via spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/compat/_adapters/
create_intent:
- src/specify_cli/compat/_adapters/uv_receipt.py
- tests/specify_cli/compat/test_uv_receipt_reader.py
- tests/specify_cli/compat/test_history_store.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/compat/_adapters/uv_receipt.py
- tests/specify_cli/compat/test_uv_receipt_reader.py
- tests/specify_cli/compat/test_history_store.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – UvReceiptReader + detect_runtime() shim + UpgradeAttemptStore

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: src/specify_cli/compat/_adapters/`.

---

## Objective

Implement three independent surfaces that become available once the WP01 types exist:

1. **`UvReceiptReader`** — the single authoritative uv-receipt.toml parser, in the pre-staged `compat/_adapters/uv_receipt.py`.
2. **`detect_runtime()`** and the **`detect_install_method()` shim** — extend `compat/_detect/runtime.py` so the existing 7 call sites stay green.
3. **`UpgradeAttemptStore`** — the full SQLite history store in `compat/history.py`, gated on the blast-radius assessment already committed in `data-model.md` §6.

**Gate**: All 7 existing `detect_install_method()` call sites must return the same `InstallMethod` value as before this WP — the shim is behavioral parity, not a new function.

## Context & Constraints

Ground truth — read before editing:
- [`spec.md`](../spec.md) FR-002, FR-003, FR-007, FR-013, FR-015, FR-017, NFR-001, NFR-003, NFR-005, NFR-006
- [`data-model.md`](../data-model.md) §3 (`UvReceiptReader`), §6 (SQLite schema), §7 (query interface)
- [`contracts/history-store-query.md`](../contracts/history-store-query.md)
- [`research.md`](../research.md) §3 (public contracts), §4 (shared-home assessment)
- [`plan.md`](../plan.md) IC-02

**Key constraint (C-001)**: `detect_install_method()` must continue to work at all 7 call sites. Do NOT modify any call site in this WP.

**`_adapters` placement (C-007)**: `UvReceiptReader` goes to `compat/_adapters/uv_receipt.py`. The `compat/_adapters/__init__.py` is pre-staged and empty — do not add public exports to it yet.

**Fail-soft contracts**: Both `UvReceiptReader.read_for_executable()` and `detect_runtime()` must never raise (NFR-001, NFR-003). Every probe wrapped in `try/except Exception` with `# noqa: BLE001`.

## Branch Strategy

- **Planning base branch**: `feat/installed-runtime-domain`
- **Merge target branch**: `feat/installed-runtime-domain`

## Subtasks & Detailed Guidance

### T007 — Implement `UvReceiptReader` in `compat/_adapters/uv_receipt.py`

The module is pre-staged (`_adapters/__init__.py` exists, empty).

**`UvReceiptResult` frozen dataclass** (data-model.md §3): 8 fields — all may be None/empty on error.

**`UvReceiptReader` class** with two static methods:

**`read_for_executable(executable: str) -> UvReceiptResult`:**
1. Derive `tool_env_dir` from `executable` path: walk up until finding a directory whose parent is a uv tool-env root (i.e., has a `uv-receipt.toml`). Use the detection chain from the existing `_has_uv_tool_receipt()` in `install_method.py` as a reference for path derivation.
2. Read `uv-receipt.toml` using `tomllib.loads()` (stdlib, Python 3.11+). Return empty `UvReceiptResult` on any `OSError` or `tomllib.TOMLDecodeError`.
3. Extract from TOML:
   - `receipt_path` — the absolute Path to the receipt file
   - `tool_dir` — the uv tool-env parent directory (from env var `UV_TOOL_DIR` if set, else via `platformdirs` default)
   - `bin_dir` — from `receipt["tool"]["bin_dir"]` if present, else None
   - `is_default_tool_dir` — compare `tool_dir` against `platformdirs.user_data_dir("uv")` default tool dir
   - `is_default_bin_dir` — compare `bin_dir` against `platformdirs.user_data_dir("uv") + "/bin"` default
   - `python` — from `receipt["tool"]["python"]` if present, else None
   - `requirements` — tuple of `UvRequirement` from `receipt["tool"]["requirements"]` list; each entry maps TOML keys to fields; unknown keys ignored; empty if list missing
   - `package_source` — derive from the first requirement entry matching "spec-kitty-cli" (by name); if not found, `PackageSource.UNKNOWN`

All parsing in a single `try/except Exception as exc: # noqa: BLE001` block returning an empty `UvReceiptResult` on any error.

**`exists_for(exe_path: Path) -> bool`:**
Check whether a `uv-receipt.toml` exists in the expected location for this executable. Never raises. Used by `detect_install_method()` detection chain (Set C in research.md) as a lightweight probe — no full parse.

### T008 — Implement `detect_runtime()` in `compat/_detect/runtime.py`

Add the `detect_runtime()` function to the module created in WP01.

```python
def detect_runtime() -> InstalledCliRuntime:
    """Return an immutable snapshot of the running spec-kitty-cli installation.

    CHK032 / NFR-001: NEVER raises. Every probe wrapped in try/except.
    """
```

Implementation:
1. Call `detect_install_method()` from `install_method.py` to get `install_method`.
2. For UV_TOOL installs: call `UvReceiptReader.read_for_executable(sys.executable)` to populate receipt fields.
3. For all other installs: set receipt/dir/python fields to None, `requirements = ()`, `package_source = PackageSource.UNKNOWN`.
4. Derive `platform`: `"windows"` if `sys.platform == "win32"`, else `"posix"`.
5. Derive `safe_for_auto_upgrade`: True iff `install_method` is in the `_SAFE_AUTO_UPGRADE_METHODS` set from `install_method.py` (PIPX, UV_TOOL, BREW, PIP_USER, PIP_SYSTEM) — C-006.
6. Wrap the entire body in `try/except Exception: # noqa: BLE001` returning a safe default `InstalledCliRuntime` with `install_method=UNKNOWN` on catastrophic failure.

All deferred imports (`sys`, `UvReceiptReader`, `InstallMethod`) inside the function body if circular imports are a concern — follow existing pattern in `install_method.py`.

### T009 — Add `detect_install_method()` shim

Add to `compat/_detect/runtime.py` (after `detect_runtime()`):

```python
def detect_install_method() -> "InstallMethod":
    """Backward-compatible shim. Delegates to detect_runtime().install_method.

    Preserved through migration step 6 (FR-017 through FR-021).
    Retired in step 7 (WP07 / FR-022).

    CHK032: Never raises (inherits detect_runtime() guarantee).
    """
    return detect_runtime().install_method
```

This shim must NOT be exported from `compat/__init__.py` yet — that is WP07. The existing export stays pointing to the old definition in `install_method.py`. The shim lives here as the future canonical location; its re-export migration happens in WP07.

### T010 — Implement `UpgradeAttemptStore` in `compat/history.py`

Extend the module from WP01 with the full store implementation.

**`default_history_db_path() -> Path`:**
Resolution order (contracts/history-store-query.md):
1. `SPEC_KITTY_HISTORY_DB_PATH` env var if set and non-empty.
2. `platformdirs.user_cache_dir("spec-kitty") / "upgrade-history.db"`.
3. Manual XDG/OS fallback matching NagCache `_resolve_cache_dir()` pattern.

**`UpgradeAttemptStore` class:**

`__init__(self, db_path: Path | None = None)`:
- Resolves `db_path` via `default_history_db_path()` if None.
- Stores path; does NOT open connection in `__init__` (lazy open on first use).

`_connect(self) -> sqlite3.Connection`:
- Calls `db_path.parent.mkdir(parents=True, exist_ok=True)`.
- Opens with `check_same_thread=False`.
- Sets `PRAGMA journal_mode=WAL`.
- Creates table + indexes using exact DDL from `data-model.md` §6.

`append(self, record: UpgradeAttemptRecord) -> None` (fail-safe):
- `INSERT OR IGNORE INTO upgrade_attempts ...` — use `attempt_id` UNIQUE constraint for idempotency.
- After insert: run retention trim (DELETE beyond last 200 per install_method).
- Both in a single transaction.
- Swallow ALL exceptions: `except Exception: # noqa: BLE001 pass`.

`is_idempotent(self, attempt: UpgradeAttemptRecord) -> bool` (fail-open):
- Returns True iff a record with `outcome='success'`, same `install_method`, same `target_version` (non-None) exists.
- Returns False if `attempt.target_version is None` or on any error.

`consecutive_failure_count(self, install_method, *, window_seconds=300) -> int` (fail-open):
- Query at most last 100 records for `install_method` within `window_seconds` of now.
- Count consecutive failures from the tail until first non-failure.
- Return 0 on any error.

`last_success_timestamp(self, install_method) -> datetime | None` (fail-open):
- Return UTC datetime of most recent `outcome='success'` for `install_method`.
- Return None if none or on error.

**SPEC_KITTY_HISTORY_DB_PATH escape hatch** (test isolation): must be respected in `default_history_db_path()`.

### T011 — Write `tests/specify_cli/compat/test_uv_receipt_reader.py`

Cover:
- Happy path: mock `uv-receipt.toml` TOML content with all fields; assert all `UvReceiptResult` fields populated correctly.
- Malformed TOML → returns empty result, no raise (NFR-003).
- Missing receipt file (`OSError`) → returns empty result, no raise.
- Receipt present but no spec-kitty requirement → `requirements=()`, `package_source=UNKNOWN`.
- Custom `UV_TOOL_DIR` env var → `tool_dir` reflects env var value.
- `exists_for()` returns True when receipt exists, False when absent.

Use `tmp_path` fixtures; no internet/uv process required.

### T012 — Write `tests/specify_cli/compat/test_history_store.py`

Cover:
- `append()` + read back via `last_success_timestamp()`.
- `is_idempotent()`: True after success record, False before, False when `target_version=None`.
- `consecutive_failure_count()`: 0 with no failures; 3 after 3 failures; stops counting at success record.
- Duplicate `attempt_id` → second insert is silent no-op (`INSERT OR IGNORE`).
- Retention trim: insert 205 records for same install_method; query returns ≤200.
- `SPEC_KITTY_HISTORY_DB_PATH` env var → store uses the specified path.
- Swallow append errors: corrupt db_path (read-only dir) → `append()` returns normally.
- Concurrent writes: two threads appending simultaneously → no corruption (WAL mode; test with `threading.Thread`).

### T013 — Green-gate verification

Verify all 7 existing `detect_install_method()` call sites still work:
```bash
grep -rn "detect_install_method" src/specify_cli/ | grep -v "def detect_install_method\|# noqa\|install_method.py\|runtime.py"
```
All 7 call sites shown above must import and invoke successfully with the same return type.

Run full test suite:
```bash
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -q
pytest tests/architectural/test_no_legacy_terminology.py -q
```

Run ruff + mypy on new/modified files:
```bash
ruff check src/specify_cli/compat/_adapters/uv_receipt.py src/specify_cli/compat/_detect/runtime.py src/specify_cli/compat/history.py
mypy src/specify_cli/compat/_adapters/uv_receipt.py src/specify_cli/compat/_detect/runtime.py src/specify_cli/compat/history.py
```

## Success Criteria

- [ ] `UvReceiptReader.read_for_executable()` extracts all fields from a well-formed receipt; returns empty result on any error (NFR-003)
- [ ] `detect_runtime()` never raises; single receipt read for UV_TOOL installs (SC-001)
- [ ] `detect_install_method()` shim returns identical `InstallMethod` values as the original function
- [ ] All 7 shim call sites still green
- [ ] `UpgradeAttemptStore` passes all query-interface contracts from `contracts/history-store-query.md`
- [ ] History store uses `SPEC_KITTY_HISTORY_DB_PATH` env var for test isolation
- [ ] Full test suite green; zero ruff/mypy issues on new/modified files

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| uv receipt path derivation differs across platforms | Use `sys.executable` path and `UvReceiptReader.exists_for()` from WP01 pattern; test on Linux and Windows paths |
| SQLite WAL mode not supported in some CI environments | WAL mode degrades gracefully to DELETE journal if unsupported; test passes because `append()` is fail-safe |
| Concurrent-write test is flaky on slow CI | Use `threading.Barrier` to synchronize thread start; assert no exception rather than exact row count if timing sensitive |
| Shim circular import (runtime.py imports install_method.py which may import runtime.py) | Keep shim in same module as detect_runtime(); use deferred local import inside function body |
