---
work_package_id: WP03
title: BackgroundDaemonPolicy config extension
dependencies: []
requirement_refs:
- FR-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
agent: "claude:sonnet:python-implementer:implementer"
shell_pid: "66132"
history:
- at: '2026-04-11T06:22:58Z'
  actor: claude:/spec-kitty.tasks
  event: created
  note: Generated from data-model.md §§5–6 and contracts/background_daemon_policy.md.
authoritative_surface: src/specify_cli/sync/config.py
execution_mode: code_change
feature_slug: 082-stealth-gated-saas-sync-hardening
owned_files:
- src/specify_cli/sync/config.py
- tests/sync/test_config_background_daemon.py
priority: P2
tags: []
---

# WP03 — BackgroundDaemonPolicy config extension

## Objective

Extend the existing `SyncConfig` dataclass at `src/specify_cli/sync/config.py:12-70` with a new user-level TOML key `[sync].background_daemon = "auto" | "manual"` (default `"auto"`). Ship a typed `BackgroundDaemonPolicy` enum and a forgiving loader that case-insensitively parses the value, warns and defaults on unknown input, and rejects empty strings. This WP is the config surface; WP04 will consult it from `ensure_sync_daemon_running()`.

## Context

Research R-004 fixed the home of the new key: user-level `~/.spec-kitty/config.toml` under the existing `[sync]` table. This choice reflects that daemon auto-start is a per-machine operator preference (local resource consumption) rather than a per-repo setting. Project-level layering is explicitly out of scope for this mission but documented in research.md as the future path.

The current `SyncConfig` has exactly two fields today (`server_url` at line 36, `max_queue_size` at line 55). Adding a third field with an enum type is a small change, but the loader must be backwards compatible: config files without the new key must load cleanly and default to `AUTO`, because the current behavior — which is "auto-start when called" — is what `AUTO` describes.

This WP is independent of WP01 and WP02 and can run in parallel with them.

**Branch strategy**: Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main. Execution worktrees are allocated per computed lane from `lanes.json`; this WP has no dependencies and is the head of Lane B (config+daemon).

## Files touched

| File | Action | Notes |
|---|---|---|
| `src/specify_cli/sync/config.py` | **modify** | Add `BackgroundDaemonPolicy` enum; add `get_background_daemon()` and `set_background_daemon()` methods to the existing `SyncConfig` class. |
| `tests/sync/test_config_background_daemon.py` | **create** | Coverage of default, case-insensitive parsing, warn-and-default on unknown, reject-empty. |

## IMPORTANT — `SyncConfig` shape

**`SyncConfig` is NOT a `@dataclass`.** It is a plain Python class defined at `src/specify_cli/sync/config.py:12-70`. It has no fields — configuration lives in `~/.spec-kitty/config.toml` and is read/written on demand through method pairs backed by private `_load()` and `_save()` helpers:

- `_load() -> dict[str, Any]` — returns `toml.load(config_file)` or `{}` on missing/invalid (lines 19-26)
- `_save(config: dict[str, Any]) -> None` — persists via `atomic_write` (lines 28-31)
- `get_server_url() -> str` / `set_server_url(url: str) -> None` (lines 33-45)
- `get_max_queue_size() -> int` / `set_max_queue_size(size: int) -> None` (lines 47-68)

This mission adds a new **method pair** — `get_background_daemon()` and `set_background_daemon()` — that mirrors the existing getter/setter pattern. **Do NOT convert `SyncConfig` to a dataclass** and do NOT add instance fields; that would be a breaking shape change out of scope for this mission.

## Subtasks

### T012 — Add `BackgroundDaemonPolicy` enum and `SyncConfig` methods

**Purpose**: Provide the typed vocabulary for the new key and add the getter/setter pair to the existing `SyncConfig` class.

**Steps**:

1. At the top of `src/specify_cli/sync/config.py` (near other imports, after the existing `import toml` / `from .queue import DEFAULT_MAX_QUEUE_SIZE` block), add:

   ```python
   from enum import Enum


   class BackgroundDaemonPolicy(str, Enum):
       AUTO = "auto"
       MANUAL = "manual"
   ```

2. Add `get_background_daemon()` to the existing `SyncConfig` class, mirroring `get_max_queue_size`'s on-demand `_load()` pattern. Skeleton:

   ```python
   def get_background_daemon(self) -> BackgroundDaemonPolicy:
       """Get background daemon policy from config.

       Config key: [sync] background_daemon = "auto" | "manual"
       Default: "auto"
       """
       config = self._load()
       raw = config.get("sync", {}).get("background_daemon")
       # (parsing logic per T013)
   ```

3. Add `set_background_daemon(policy: BackgroundDaemonPolicy) -> None` mirroring `set_server_url`:

   ```python
   def set_background_daemon(self, policy: BackgroundDaemonPolicy) -> None:
       config = self._load()
       if "sync" not in config:
           config["sync"] = {}
       config["sync"]["background_daemon"] = policy.value
       self._save(config)
   ```

4. Do not touch the existing `get_server_url` / `set_server_url` / `get_max_queue_size` / `set_max_queue_size` methods.

**Files**: `src/specify_cli/sync/config.py` (additions totaling ~30 lines)

**Validation**: `python -c "from specify_cli.sync.config import SyncConfig, BackgroundDaemonPolicy; print(SyncConfig().get_background_daemon())"` prints `BackgroundDaemonPolicy.AUTO` on a fresh machine with no config file. mypy --strict clean.

### T013 — `get_background_daemon` parsing: case-insensitive, warn+default, reject empty

**Purpose**: Parse the new TOML value with the resilience characteristics called out in `contracts/background_daemon_policy.md`, inside the getter introduced by T012.

**Steps**:

1. Fill in the body of `get_background_daemon()` (the skeleton from T012) to handle every case:
   - Missing key / `raw is None` → return `BackgroundDaemonPolicy.AUTO`.
   - Non-string value (e.g., TOML somehow decoded an int) → emit warning and return `AUTO`.
   - Empty string after `.strip()` → **raise** the config error idiom the rest of `sync/config.py` uses. If no existing error type is present (the current file uses `return {}` on parse failure rather than raising), raise a new `ValueError` with message `"[sync].background_daemon must be 'auto' or 'manual', not an empty string"`. Keep the behavior consistent with whatever T014 tests assert.
   - Non-empty string → `.strip().casefold()` and look up in `{"auto": AUTO, "manual": MANUAL}` (or `BackgroundDaemonPolicy._value2member_map_`). Match found → return the member.
   - String that does not match any member (e.g., `"banana"`, `"sometimes"`) → emit a one-line warning to stderr: `"[sync].background_daemon value 'banana' is unknown; defaulting to 'auto'"` and return `AUTO`. Use `print(..., file=sys.stderr)` — do not introduce a new logging dependency. Note that the existing `sync/config.py` does not currently import `sys`; add the import.

2. Case-insensitive matching: `"AUTO"`, `"Auto"`, `"auto"`, `"MANUAL"`, `"Manual"`, `"manual"` all round-trip.
3. Each call to `get_background_daemon()` re-reads the file via `_load()`. There is no caching. This is intentional — mirrors `get_server_url` / `get_max_queue_size`.

**Files**: `src/specify_cli/sync/config.py` (modifications within the method body, ~30 lines)

**Validation**: T014 tests assert every branch. mypy --strict clean.

### T014 — Tests: `tests/sync/test_config_background_daemon.py`

**Purpose**: Lock the loader behavior against regression.

**Steps**:

1. Create the new test module under `tests/sync/` (package already exists per exploration).
2. Each test builds a temporary `config.toml` in `tmp_path`, monkey-patches `SyncConfig` to point at it (the simplest way is to monkeypatch `Path.home` to return `tmp_path` so `SyncConfig.__init__` resolves `config_dir` there; follow whatever pattern existing `tests/sync/test_daemon.py` uses).
3. Write test cases calling `SyncConfig().get_background_daemon()`:
   - `test_default_when_missing` — no config file at all → returns `BackgroundDaemonPolicy.AUTO`.
   - `test_default_when_sync_table_missing` — file exists with no `[sync]` table → returns `AUTO`.
   - `test_default_when_key_missing` — `[sync]` exists with `server_url` but no `background_daemon` → returns `AUTO`.
   - `test_auto_lowercase`, `test_auto_uppercase`, `test_auto_mixed_case` — `"auto"` / `"AUTO"` / `"Auto"` → `AUTO`.
   - `test_manual_lowercase`, `test_manual_mixed_case` — `"manual"` / `"Manual"` → `MANUAL`.
   - `test_unknown_value_warns_and_defaults` — value `"banana"` → returns `AUTO` AND stderr (captured via `capsys`) contains the warning wording `"[sync].background_daemon value 'banana' is unknown; defaulting to 'auto'"`.
   - `test_empty_string_raises` — value `""` → `pytest.raises(<error type chosen in T013>)`.
   - `test_whitespace_value_accepted` — value `"  auto  "` → returns `AUTO` (the getter strips before parsing).
   - `test_backcompat_existing_config_without_new_key_loads_cleanly` — regression guard: an existing `[sync]\nserver_url = "https://example.com"\nmax_queue_size = 500` config still returns `AUTO` and existing getters still return their values.
   - `test_setter_roundtrip` — `set_background_daemon(MANUAL)` followed by `get_background_daemon()` returns `MANUAL`.

**Files**: `tests/sync/test_config_background_daemon.py` (~180 lines, ~8 test cases)

**Validation**: `pytest tests/sync/test_config_background_daemon.py -q` green. Full suite `pytest -q` still green.

## Test Strategy

Test coverage for this WP is the whole point — the loader must never silently accept malformed input and must never reject well-formed input. Every branch of the loader has a test. The backcompat test protects existing users.

## Definition of Done

- [ ] `BackgroundDaemonPolicy` enum exists and is importable from `specify_cli.sync.config`.
- [ ] `SyncConfig.get_background_daemon()` and `SyncConfig.set_background_daemon()` methods exist, mirroring the existing getter/setter pattern on the class.
- [ ] `SyncConfig` remains a regular class (NOT converted to `@dataclass`); no new instance fields were added.
- [ ] `get_background_daemon()` parses case-insensitive values, warns-and-defaults on unknown, rejects empty strings.
- [ ] `tests/sync/test_config_background_daemon.py` passes with all test cases above.
- [ ] Existing tests in `tests/sync/` still pass (backcompat).
- [ ] `pytest -q` full suite green.
- [ ] `mypy --strict src/specify_cli/sync/config.py` clean.
- [ ] No files outside `owned_files` modified.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Implementer converts `SyncConfig` to a dataclass "for consistency" | Explicitly prohibited in this WP's IMPORTANT section. `SyncConfig` is a regular class; we add methods only. |
| `_load()` returns `{}` on TOML parse errors today — empty-string rejection may silently pass through | Check `_load()` at `sync/config.py:19-26`: it returns `{}` only when the file is missing or the TOML parse raises. An empty string value inside an otherwise valid TOML file still reaches the getter, which is where rejection happens. |
| Warning output interferes with JSON command output in some code path | The warning is stderr-only; JSON output is stdout. Verify with an end-to-end `spec-kitty` command that produces JSON. |
| Rich console vs plain print — which does `sync/config.py` use today? | The existing file uses neither — it's pure stdlib. Use `print(..., file=sys.stderr)` and `import sys` at the top. Do not introduce a logging dependency. |

## Reviewer Guidance

- Verify `get_background_daemon()` handles every input branch via tests.
- Confirm `SyncConfig` is still a regular class — NO `@dataclass` decorator, no instance fields added.
- Confirm the two existing methods (`get_server_url`, `get_max_queue_size`) still work exactly as before.
- Confirm the error type for empty-string rejection matches whatever the existing `sync/config.py` or its test fixtures already use.
- Confirm the backcompat test uses a realistic "pre-0.11.0" TOML shape with only `server_url` and `max_queue_size` keys present.

## Implementation command

```bash
spec-kitty agent action implement WP03 --agent <name>
```

## Activity Log

- 2026-04-11T08:43:43Z – claude:sonnet:python-implementer:implementer – shell_pid=66132 – Started implementation via action command
- 2026-04-11T08:51:12Z – claude:sonnet:python-implementer:implementer – shell_pid=66132 – BackgroundDaemonPolicy + getter/setter pair added to existing SyncConfig class
