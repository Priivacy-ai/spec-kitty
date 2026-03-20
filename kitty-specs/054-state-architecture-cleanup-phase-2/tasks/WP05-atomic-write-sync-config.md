---
work_package_id: WP05
title: Atomic Write Conversion — Sync and Config
lane: "doing"
dependencies: [WP01]
base_branch: 054-state-architecture-cleanup-phase-2-WP01
base_commit: b989de5f96e3c9e6c776a952a010cdeacc2e69e8
created_at: '2026-03-20T14:00:42.961383+00:00'
subtasks:
- T019
- T020
- T021
- T022
phase: Phase 2 - Hardening
assignee: ''
agent: ''
shell_pid: "94629"
review_status: ''
reviewed_by: ''
review_feedback: ''
history:
- timestamp: '2026-03-20T13:39:48Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-012
- FR-013
- FR-014
- FR-015
- NFR-001
---

# Work Package Prompt: WP05 – Atomic Write Conversion — Sync and Config

## Objectives & Success Criteria

- Convert 4 sync/config write paths to use the shared `atomic_write()` utility.
- Special handling for `clock.py` (replace inline atomic impl) and `auth.py` (preserve file lock + 600 permissions).
- Each converted path produces identical file content and maintains its existing concurrency guarantees.

## Context & Constraints

- **Depends on WP01**: The shared `atomic_write()` utility must exist.
- **clock.py already has atomic writes**: Replace its inline implementation with the shared utility (reduce code duplication).
- **auth.py has file locking**: The `filelock` context MUST be preserved. Atomic write goes inside the lock.
- **TOML serialization**: Both `auth.py` and `config.py` use `toml.dump()`. Need `toml.dumps()` for string serialization.

## Implementation Command

```bash
spec-kitty implement WP05 --base WP01
```

## Subtasks & Detailed Guidance

### Subtask T019 – Convert sync/clock.py to shared atomic_write

**Purpose**: Replace the inline atomic-write implementation with the shared utility.

**Steps**:

1. In `src/specify_cli/sync/clock.py`, find `LamportClock.save()` (lines 62-87):
   ```python
   fd, tmp_path = tempfile.mkstemp(dir=self._storage_path.parent, suffix=".tmp")
   try:
       with os.fdopen(fd, "w") as f:
           json.dump(data, f, indent=2)
       os.replace(tmp_path, self._storage_path)
   except Exception:
       try: os.unlink(tmp_path)
       except OSError: pass
       raise
   ```

2. Replace with:
   ```python
   from specify_cli.core.atomic import atomic_write

   content = json.dumps(data, indent=2)
   atomic_write(self._storage_path, content, mkdir=True)
   ```

3. Remove the `tempfile` and `os` imports if no longer needed elsewhere in the file.

**Files**: `src/specify_cli/sync/clock.py`

**Validation**: Existing clock tests should still pass. The write behavior is identical.

### Subtask T020 – Convert sync/auth.py (keep lock + permissions)

**Purpose**: Add atomic-write semantics inside the existing file-lock context. Preserve 600 permissions.

**Steps**:

1. In `src/specify_cli/sync/auth.py`, find `CredentialStore.save()` (lines 53-94):
   ```python
   with self._acquire_lock():
       with open(self.credentials_path, "w") as handle:
           toml.dump(data, handle)
       if os.name != "nt":
           os.chmod(self.credentials_path, 0o600)
   ```

2. Replace the inner write with:
   ```python
   from specify_cli.core.atomic import atomic_write

   with self._acquire_lock():
       content = toml.dumps(data)
       atomic_write(self.credentials_path, content)
       if os.name != "nt":
           os.chmod(self.credentials_path, 0o600)
   ```

3. **CRITICAL**: The `atomic_write` call MUST remain inside `self._acquire_lock()` — the lock prevents concurrent credential writes from different processes.

4. `os.chmod` MUST come after `atomic_write` because `os.replace()` creates a new inode that needs fresh permissions.

**Files**: `src/specify_cli/sync/auth.py`

**Edge Case**: Verify `toml.dumps()` exists in the TOML library used. If using `tomli_w`, it's `tomli_w.dumps()`. If using `toml`, it's `toml.dumps()`. Check the import at the top of the file.

### Subtask T021 – Convert sync/config.py

**Purpose**: Make `~/.spec-kitty/config.toml` writes atomic.

**Steps**:

1. In `src/specify_cli/sync/config.py`, find `set_server_url()` (lines 22-38):
   ```python
   self.config_dir.mkdir(exist_ok=True)
   # ... load existing config ...
   with open(self.config_file, 'w') as f:
       toml.dump(config, f)
   ```

2. Replace with:
   ```python
   from specify_cli.core.atomic import atomic_write

   content = toml.dumps(config)
   atomic_write(self.config_file, content, mkdir=True)
   ```

3. Remove `self.config_dir.mkdir(exist_ok=True)` — `mkdir=True` handles it.

4. Check for other write methods in this class (`SyncConfig`) and convert them too.

**Files**: `src/specify_cli/sync/config.py`

### Subtask T022 – Convert tracker/config.py

**Purpose**: Make tracker config writes to `.kittify/config.yaml` atomic.

**Steps**:

1. In `src/specify_cli/tracker/config.py`, find `save_tracker_config()` (lines 101-121):
   ```python
   yaml = YAML()
   yaml.preserve_quotes = True
   # ... load/modify payload ...
   with config_path.open("w", encoding="utf-8") as handle:
       yaml.dump(payload, handle)
   ```

2. Replace with string serialization:
   ```python
   import io
   from specify_cli.core.atomic import atomic_write

   yaml = YAML()
   yaml.preserve_quotes = True
   # ... load/modify payload ...
   buf = io.StringIO()
   yaml.dump(payload, buf)
   atomic_write(config_path, buf.getvalue(), mkdir=True)
   ```

3. Remove `config_path.parent.mkdir(parents=True, exist_ok=True)` — `mkdir=True` handles it.

**Files**: `src/specify_cli/tracker/config.py`

**Edge Case**: `ruamel.yaml.YAML.dump()` to `StringIO` should produce the same output as to a file handle, but verify by comparing output.

## Test Strategy

- For each module, verify the existing test suite passes after conversion.
- For `auth.py`, verify that file permissions are 600 after write (non-Windows).
- For `clock.py`, verify the inline atomic-write code is completely removed.

Run: `pytest tests/ -k "clock or auth or sync_config or tracker" -v`

## Risks & Mitigations

- **`toml.dumps()` availability**: Some TOML libraries don't have `dumps()`. Check the actual import (`toml`, `tomli_w`, `tomllib`). The `toml` package has `dumps()`. If using `tomli_w`, it also has `dumps()`.
- **Permission race in auth.py**: Between `atomic_write` and `os.chmod`, there's a brief window where the file has default permissions. This is acceptable inside the file lock.

## Review Guidance

- Verify `auth.py` lock context is preserved around the atomic write.
- Verify `clock.py` inline implementation is fully removed (no leftover `tempfile` usage).
- Verify `ruamel.yaml` StringIO output matches file output.

## Activity Log

- 2026-03-20T13:39:48Z – system – lane=planned – Prompt created.
