# Research: Centralize installed CLI runtime + remediation planning

**Mission**: `installed-runtime-domain-01KW0NR6`
**Branch**: `feat/installed-runtime-domain`
**Date**: 2026-06-26

---

## §1 — Caller Audit: FR-008 (3 Duplicate Receipt-Parser Sets)

FR-008 requires that the three independent receipt-parser helper sets be deleted after migration, so each call site is confirmed to have migrated before deletion. The three sets are:

### Set A — `src/specify_cli/cli/commands/review/__init__.py`

| Helper | Defined at | Used by |
|--------|-----------|---------|
| `_active_uv_tool_receipt() -> dict | None` | line 146 | `_uv_tool_reinstall_command()` (120), `_active_uv_tool_receipt_has_spec_kitty()` (186), `_active_uv_tool_bin_dir()` (343) |
| `_active_uv_tool_receipt_path() -> Path | None` | line 159 | `_fallback_uv_tool_reinstall_command()` (110), `_active_uv_tool_receipt()` (148) |
| `_active_uv_tool_receipt_has_spec_kitty() -> bool` | line 185 | `_missing_test_extra_remediation()` (87) |
| `_active_uv_tool_dir() -> Path | None` | line 329 | `_uv_tool_env_values()` (316) |
| `_active_uv_tool_bin_dir() -> Path | None` | line 342 | `_uv_tool_env_values()` (319) |
| `_same_path(left, right) -> bool` | line 361 | `_uv_tool_env_values()` (317, 320) |
| `_uv_tool_python_args(receipt) -> list[str]` | line 286 | `_uv_tool_reinstall_command()` (138) |
| `_uv_tool_env_prefix() -> str` | line 304 | `_uv_tool_reinstall_command()` (141), `_fallback_uv_tool_reinstall_command()` (115) |
| `_uv_tool_env_values() -> list[tuple]` | line 314 | `_uv_tool_env_prefix()` (305) |
| `_powershell_quote(value) -> str` | line 325 | `_uv_tool_env_prefix()` (308) |

**Migration target (WP04)**: All helpers in Set A are replaced by calls to `UvReceiptReader` (for receipt/dir/python fields) and `plan_remediation()` (for command construction). The public entry point `_missing_test_extra_remediation()` is preserved but its implementation replaced.

**Deletion gate**: Every internal call site migrated. Post-migration `grep` for `_active_uv_tool_receipt\|_active_uv_tool_dir\|_same_path\|_uv_tool_python_args\|_uv_tool_env_prefix\|_uv_tool_env_values\|_powershell_quote` in `review/__init__.py` returns zero results.

---

### Set B — `src/specify_cli/readiness/upgrade_ux.py`

| Helper | Defined at | Used by |
|--------|-----------|---------|
| `_active_uv_tool_receipt() -> dict | None` | line 291 | `_uv_tool_python_args()` (279), `_uv_tool_upgrade_env()` implicitly via `_active_uv_tool_dir()` |
| `_active_uv_tool_dir() -> Path | None` | line 315 | `_uv_tool_upgrade_env()` (270) |
| `_same_path(left, right) -> bool` | line 328 | `_uv_tool_upgrade_env()` (271) |
| `_uv_tool_python_args() -> list[str]` | line 278 | `_default_upgrade_runner()` (239) |

**Migration target (WP05)**: All helpers in Set B are replaced by consuming `InstalledCliRuntime` fields directly (`runtime.python`, `runtime.tool_dir`, `runtime.is_default_tool_dir`). `_default_upgrade_runner` is rewritten to accept a `RemediationCommand` (from `plan_remediation()`) and consume `.argv` + `.env` directly.

**Deletion gate**: Post-WP05 `grep` for `_active_uv_tool_receipt\|_active_uv_tool_dir\|_same_path\|_uv_tool_python_args` in `upgrade_ux.py` returns zero results.

---

### Set C — `src/specify_cli/compat/_detect/install_method.py` (partial overlap)

`_has_uv_tool_receipt()` at line 112 reads the uv receipt ONLY to confirm UV_TOOL detection (i.e., "does this executable belong to a uv-managed tool env?"). It does NOT extract receipt fields for use downstream.

**Status**: This function is NOT in scope for deletion under FR-008. It is logically part of the detection chain (`_is_uv_tool_install()` at line 88) and performs a different role from Sets A and B.

After the migration, `UvReceiptReader` in `_adapters/uv_receipt.py` becomes the authoritative field-extraction path. `_has_uv_tool_receipt()` in `install_method.py` can be simplified to delegate to `UvReceiptReader.exists_for(exe_path)` in step 2, or retained as-is (it is a detect-only probe, not a parsing path).

---

## §2 — Caller Audit: FR-022 (7 detect_install_method() Call Sites)

All 7 sites must be migrated to `detect_runtime().install_method` (or an equivalent that does not call the shim) before the shim is retired in step 7 (WP07). Evidence table:

| # | File | Line | Usage form | Migration action |
|---|------|------|-----------|-----------------|
| 1 | `src/specify_cli/cli/commands/review/__init__.py` | 91 | `install_method = detect_install_method()` | Replace with `detect_runtime().install_method` |
| 2 | `src/specify_cli/cli/commands/upgrade.py` | 350 | `install_method = detect_install_method()` | Replace with `detect_runtime().install_method` in `_agent_check_payload` |
| 3 | `src/specify_cli/cli/commands/upgrade.py` | 668 | `method = detect_install_method()` | Replace with `detect_runtime().install_method` in schema-version check branch |
| 4 | `src/specify_cli/compat/planner.py` | 896 | `install_method = detect_install_method()` | Replace with `detect_runtime().install_method` in `_plan_impl` (deferred import at 757 updates too) |
| 5 | `src/specify_cli/readiness/upgrade_ux.py` | 648 | `installer_detector = detect_install_method` (callable ref) | Replace with `lambda: detect_runtime().install_method` (or pass `detect_runtime` and unwrap at call site 695) |
| 6 | `src/specify_cli/readiness/upgrade_ux.py` | 695 | `method = installer_detector()` (default resolves to `detect_install_method()`) | Call site 695 is covered by migration of site 5 |
| 7 | `src/specify_cli/compat/__init__.py` | 66 | `from ... import InstallMethod, detect_install_method` (public re-export) | Remove `detect_install_method` from re-export; update `__all__` at line 120; add `detect_runtime` to public API |

**Verification command (run before WP07 merge)**:
```bash
grep -rn "detect_install_method" src/specify_cli/ | grep -v "def detect_install_method\|# noqa\|install_method.py"
```
Expected output: zero lines.

---

## §3 — Public Contracts That Must Stay Intact

The following contracts are preserved verbatim across all migration steps (C-002):

| Contract | Location | What must stay identical |
|---------|----------|--------------------------|
| `UpgradeHint` frozen dataclass | `compat/upgrade_hint.py` | Fields: `install_method`, `command: str | None`, `note: str | None`; `__post_init__` invariant (exactly one of command/note non-None) |
| `_HINT_TABLE` dict | `compat/upgrade_hint.py` | All 8 keys/values unchanged; eagerly-validated at import time |
| CHK028 regex | `compat/upgrade_hint.py` line 29 | `^[A-Za-z0-9 .\-+_/=:]{1,128}$` — must be the same regex used in `RemediationCommand.render()` |
| `build_upgrade_hint(install_method, *, package, target_version)` | `compat/upgrade_hint.py` | Public signature unchanged; return type `UpgradeHint`; after WP03, internal implementation delegates to `plan_remediation()` but callers see no behavioral change |
| `Plan.upgrade_hint` JSON contract | `compat/planner.py` | `{"install_method": str, "command": str | null, "note": str | null}` in `rendered_json`; no field added or removed |

---

## §4 — Shared-Home Blast Radius Assessment

### Context

The spec (C-008) requires that the history store schema design and blast-radius assessment for Docker/SaaS installs be committed before WP02 implementation begins.

### Current home-dir isolation model

The existing upgrade-nag subsystem stores state in two locations:

| Store | Path | Isolation unit |
|-------|------|---------------|
| NagCache | `platformdirs.user_cache_dir("spec-kitty") / "upgrade-nag.json"` | OS user (`$HOME` / `$XDG_CACHE_HOME`) |
| OfflineQueue (legacy) | `~/.spec-kitty/queue.db` | OS user |
| OfflineQueue (scoped) | `~/.spec-kitty/queues/<server|user|team>.db` | User+team login session |

### Blast-radius analysis for the history store

**Scenario: shared OS user in Docker**

If two spec-kitty instances (e.g., two Docker containers with `~/.cache/spec-kitty/` volume-mounted from a shared host directory) run as the same OS user:

- They would share the same `upgrade-history.db` file.
- Their `UpgradeAttemptRecord` entries would be interleaved in the same table.
- An idempotency query ("was this upgrade already completed?") keyed on `(install_method, target_version)` could return True for container B if container A already ran the same upgrade.

**Assessment: acceptable and bounded**

1. Containers that share the same OS user and home directory are already sharing `upgrade-nag.json` (NagCache), `~/.spec-kitty/` (OfflineQueue legacy), and credentials. The history store introduces no new blast radius beyond what already exists.

2. The idempotency "false positive" scenario (container B deduplicates against container A's record) is safe: it means "don't re-run an upgrade that already succeeded," which is the correct outcome for two instances of the same install.

3. Proper Docker isolation requires separate OS users per tenant; this is the documented responsibility of the operator, not the application.

4. An override escape hatch (`SPEC_KITTY_HISTORY_DB_PATH` env var) allows operators to redirect the store to a container-local path if stronger isolation is needed, following the same pattern as other path overrides.

**Conclusion**: No additional scoping key is required in the history store. The OS-user-level isolation is sufficient and matches the existing NagCache pattern.

**No PII in isolation**: We do NOT use `sha256(sys.executable)` or any path-derived identifier as a scoping key — that would violate NFR-007. The `install_method` column (a StrEnum value like `"uv-tool"`) is sufficient for per-method query filtering.

---

## §5 — OfflineQueue Precedent (Mission 047)

The history store follows the SQLite sibling-table pattern established in `src/specify_cli/sync/queue.py` (OfflineQueue) and `src/specify_cli/sync/body_queue.py` (OfflineBodyUploadQueue):

| Pattern | OfflineQueue | UpgradeAttemptStore |
|---------|-------------|---------------------|
| DB layer | `sqlite3` stdlib | `sqlite3` stdlib |
| Schema init | `CREATE TABLE IF NOT EXISTS` in `_init_db()` | Same pattern in `_ensure_schema()` |
| Write strategy | `INSERT` with `UNIQUE` index + `INSERT OR IGNORE` | `INSERT OR IGNORE` on `attempt_id` UNIQUE |
| Concurrent writes | Thread-lock-free append (SQLite WAL mode) | Same (WAL mode for concurrent readers) |
| Path resolution | `default_queue_db_path()` → platformdirs | `default_history_db_path()` → platformdirs |
| Fail-soft | Best-effort; exceptions swallowed at caller | Best-effort; `# noqa: BLE001` on write failures |

**Key difference**: OfflineQueue is an outbox (events are drained remotely). The history store is a bounded local log (no drain; retention policy = last N records per `install_method`).

---

## §6 — uv Receipt TOML Schema

The uv receipt TOML file (`uv-receipt.toml`) in a tool environment has this structure (derived from source inspection across three parse sites):

```toml
[tool]
python = "3.11"                   # optional python override
requirements = [
  { name = "spec-kitty-cli", specifier = "==3.2.0" },
  { name = "pytest", specifier = ">=7.0" },
  # Optional per-requirement keys:
  # directory = "/path/to/dir"
  # editable = "/path/to/editable"
  # path = "/path/to/whl"
  # git = "https://github.com/..."
  # url = "https://..."
]
entrypoints = [
  { name = "spec-kitty", install-path = "/home/user/.local/bin/spec-kitty" },
]
```

`UvReceiptReader` extracts:
- `receipt_path`: path to the `uv-receipt.toml` file (not stored in the record per NFR-007; passed as field of `InstalledCliRuntime`)
- `tool_dir`: parent of the tool-env directory (executable_parent.parent.parent)
- `bin_dir`: derived from `entrypoints[].install-path` parent
- `python`: `tool.python` or None
- `requirements`: `tuple[UvRequirement, ...]` from `tool.requirements`
- `is_default_tool_dir`: whether `tool_dir == default UV tools dir`
- `is_default_bin_dir`: whether `bin_dir == ~/.local/bin`

Fail-soft: any parse error, missing key, or type mismatch returns `None` for the affected field without raising (NFR-003).

---

## §7 — Alternatives Considered

### History store: JSONL append-only file vs SQLite

| Criterion | JSONL | SQLite |
|-----------|-------|--------|
| Concurrent write safety | Requires atomic rename (temp file + os.replace) | WAL mode provides concurrent read + serial write |
| Idempotency queries | O(n) full scan + parse | O(log n) via UNIQUE index on `attempt_id` |
| Retention policy | File truncation is non-atomic | `DELETE WHERE id NOT IN (SELECT id FROM ... LIMIT N)` atomic |
| In-repo precedent | status.events.jsonl (but that's per-mission, not global) | OfflineQueue, OfflineBodyUploadQueue |

**Decision**: SQLite sibling table. Stronger concurrent-write guarantees, atomic retention, direct query support without full parse.

### detect_runtime() placement: compat/_detect/ vs compat/

Placing `detect_runtime()` in `compat/_detect/runtime.py` (parallel to `install_method.py`) keeps the detection chain in one sub-package and avoids cluttering `compat/` top-level. The public API re-export in `compat/__init__.py` provides the stable surface.

### plan_remediation() placement: compat/remediation.py vs inline in upgrade_hint.py

Keeping `plan_remediation()` in a separate module prevents `upgrade_hint.py` from growing into a god module and allows `plan_remediation()` to be imported and tested without the CHK028 validation overhead of `UpgradeHint`.
