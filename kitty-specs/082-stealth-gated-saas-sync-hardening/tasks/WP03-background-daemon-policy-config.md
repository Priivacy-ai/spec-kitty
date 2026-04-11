---
work_package_id: WP03
title: BackgroundDaemonPolicy config extension
dependencies: []
requirement_refs:
- FR-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: 'Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main.'
subtasks:
- T012
- T013
- T014
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
| `src/specify_cli/sync/config.py` | **modify** | Add `BackgroundDaemonPolicy` enum; add `background_daemon` field to `SyncConfig`; extend loader. |
| `tests/sync/test_config_background_daemon.py` | **create** | Coverage of default, case-insensitive parsing, warn-and-default on unknown, reject-empty. |

## Subtasks

### T012 — Add `BackgroundDaemonPolicy` enum and `SyncConfig` field

**Purpose**: Provide the typed vocabulary for the new key and wire it into the existing dataclass.

**Steps**:

1. At the top of `src/specify_cli/sync/config.py` (near other imports), add:

   ```python
   from enum import Enum


   class BackgroundDaemonPolicy(str, Enum):
       AUTO = "auto"
       MANUAL = "manual"
   ```

2. Extend the `SyncConfig` dataclass (currently at lines 12–70) with a new field **after** the existing `max_queue_size` field so existing positional construction is preserved:

   ```python
   background_daemon: BackgroundDaemonPolicy = BackgroundDaemonPolicy.AUTO
   ```

3. Update `__all__` (if present) to include `BackgroundDaemonPolicy`.
4. Do not change the existing `server_url` or `max_queue_size` defaults or validation.

**Files**: `src/specify_cli/sync/config.py` (modifications totaling ~15 lines)

**Validation**: `python -c "from specify_cli.sync.config import SyncConfig, BackgroundDaemonPolicy; print(SyncConfig().background_daemon)"` prints `BackgroundDaemonPolicy.AUTO`. mypy --strict clean.

### T013 — Loader: case-insensitive parsing, warn+default, reject empty

**Purpose**: Parse the new TOML key with the resilience characteristics called out in `contracts/background_daemon_policy.md`.

**Steps**:

1. Locate the `SyncConfig` loader function in `src/specify_cli/sync/config.py`. It currently reads `[sync].server_url` and `[sync].max_queue_size` from the TOML tree. Add a third read:
   - If the `background_daemon` key is **missing** → use the default `BackgroundDaemonPolicy.AUTO`.
   - If the value is a non-empty string → `.strip().casefold()` → look up in `BackgroundDaemonPolicy._value2member_map_` (or equivalent) → match found → use the member.
   - If the value is an **empty string** → raise the existing config error type (whatever `SyncConfig` currently raises for malformed input — check `sync/config.py:12-70` to find the pattern). The error message should say `"[sync].background_daemon must be 'auto' or 'manual', not an empty string"`.
   - If the value is a **string that does not match any member** (e.g., `"banana"`, `"sometimes"`) → emit a **one-line warning to stderr** using Rich's existing console pattern if already available in this module, otherwise a plain `print(..., file=sys.stderr)`: `"[sync].background_daemon value 'banana' is unknown; defaulting to 'auto'"`. Then use `AUTO`.
2. Case-insensitive matching: `"AUTO"`, `"Auto"`, `"auto"`, `"MANUAL"`, `"Manual"`, `"manual"` all round-trip.
3. Make sure the loader is called during `SyncConfig.load()` (or whatever the existing entry point is) — do **not** duplicate the loader logic.

**Files**: `src/specify_cli/sync/config.py` (modifications totaling ~30 lines)

**Validation**: T014 tests assert every branch. mypy --strict clean.

### T014 — Tests: `tests/sync/test_config_background_daemon.py`

**Purpose**: Lock the loader behavior against regression.

**Steps**:

1. Create the new test module under `tests/sync/` (package already exists per exploration).
2. Write test cases:
   - `test_default_when_missing` — TOML with no `background_daemon` key → `SyncConfig.background_daemon == BackgroundDaemonPolicy.AUTO`
   - `test_auto_lowercase`, `test_auto_uppercase`, `test_auto_mixed_case` — `"auto"` / `"AUTO"` / `"Auto"` all parse to `AUTO`
   - `test_manual_lowercase`, `test_manual_mixed_case` — same for `"manual"` / `"Manual"`
   - `test_unknown_value_warns_and_defaults` — value `"banana"` → result is `AUTO` AND stderr (captured via `capsys`) contains the warning wording
   - `test_empty_string_rejected` — value `""` → `pytest.raises(<the config error type>)`
   - `test_whitespace_value_rejected_or_accepted` — decide: value `"  auto  "` should be accepted after `.strip()`. Assert behavior matches the loader's intent; document either way.
   - `test_backcompat_existing_config_without_new_key_loads_cleanly` — regression guard: an existing minimal `[sync]\nserver_url = "..."` config loads without errors and gets `AUTO`
3. Each test builds a temporary TOML file in `tmp_path` and passes it to the loader (mirror the pattern used by existing tests in `tests/sync/` — e.g., `tests/sync/test_daemon.py` likely has a similar fixture).

**Files**: `tests/sync/test_config_background_daemon.py` (~180 lines, ~8 test cases)

**Validation**: `pytest tests/sync/test_config_background_daemon.py -q` green. Full suite `pytest -q` still green.

## Test Strategy

Test coverage for this WP is the whole point — the loader must never silently accept malformed input and must never reject well-formed input. Every branch of the loader has a test. The backcompat test protects existing users.

## Definition of Done

- [ ] `BackgroundDaemonPolicy` enum exists and is importable from `specify_cli.sync.config`.
- [ ] `SyncConfig.background_daemon` field exists with default `AUTO`.
- [ ] Loader parses case-insensitive values, warns-and-defaults on unknown, rejects empty strings.
- [ ] `tests/sync/test_config_background_daemon.py` passes with all test cases above.
- [ ] Existing tests in `tests/sync/` still pass (backcompat).
- [ ] `pytest -q` full suite green.
- [ ] `mypy --strict src/specify_cli/sync/config.py` clean.
- [ ] No files outside `owned_files` modified.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| `SyncConfig` is constructed positionally somewhere and the new field breaks the call | Add the field **last** in the dataclass (after `max_queue_size`). Default value means no caller needs to update. Verify with `rg "SyncConfig\(" src/ tests/`. |
| Warning output interferes with JSON command output in some code path | The warning is stderr-only; JSON output is stdout. Verify with an end-to-end `spec-kitty` command that produces JSON. |
| The existing `tests/sync/test_daemon.py` fixture pattern is different from TOML-based | Use whatever pattern already exists; mirror, do not reinvent. |
| Rich console vs plain print — which does `sync/config.py` use today? | Inspect the existing file before adding the warning call; match the existing style. Do not introduce a new logging dependency. |

## Reviewer Guidance

- Verify the loader handles every input branch via tests.
- Confirm no positional `SyncConfig(...)` construction exists that would break with the new field. Run `rg "SyncConfig\("` across the repo.
- Confirm the error type for empty-string rejection matches whatever the existing `server_url` validation raises (consistency).
- Confirm the backcompat test uses a realistic "pre-0.11.0" TOML shape.

## Implementation command

```bash
spec-kitty agent action implement WP03 --agent <name>
```
