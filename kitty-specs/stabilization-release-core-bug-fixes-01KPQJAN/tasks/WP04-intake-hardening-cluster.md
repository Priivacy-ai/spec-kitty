---
work_package_id: WP04
title: Intake Hardening Cluster
dependencies:
- WP03
requirement_refs:
- C-003
- C-005
- FR-013
- FR-014
- FR-015
- FR-016
- FR-017
- NFR-001
- NFR-002
- NFR-003
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T024
- T025
- T026
- T027
history:
- 2026-04-21T08:41:50Z – planned – stabilization WP04
authoritative_surface: src/specify_cli/mission_brief.py
execution_mode: code_change
mission_id: 01KPQJAN4P2V4MTHRFGS7VW17M
mission_slug: stabilization-release-core-bug-fixes-01KPQJAN
owned_files:
- src/specify_cli/mission_brief.py
- src/specify_cli/cli/commands/intake.py
- src/specify_cli/intake_sources.py
- tests/specify_cli/test_mission_brief*.py
- tests/specify_cli/cli/commands/test_intake*.py
- tests/specify_cli/test_intake_sources*.py
tags: []
---

# WP04 — Intake Hardening Cluster

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Dependency**: WP03 must be approved before this WP is claimed.
- **Workspace**: Enter with `spec-kitty agent action implement WP04 --agent <name>`.

## Objective

Apply four targeted hardening fixes across three intake-path modules:

1. **#723**: Make `write_mission_brief()` atomic — use PID-namespaced temp files + `Path.replace()` so a crash mid-write leaves no blocking partial state.
2. **#722**: Add a named file-size constant and a size guard to `intake.py` that rejects oversized briefs before reading them into memory.
3. **#720**: Enforce repo-root containment in `scan_for_plans()` — resolved paths outside the repo root are silently excluded.
4. **#721**: Exclude symlinks during directory expansion in `scan_for_plans()`.

Ship regression tests for all four fixes. Valid in-repo markdown intake must remain unchanged.

**Fixes**: Issues #723, #722, #720, #721  
**Requirements**: FR-013, FR-014, FR-015, FR-016, FR-017, C-003, C-005, NFR-001–004

---

## Subtask T020 — Atomic write in `write_mission_brief()`

**File**: `src/specify_cli/mission_brief.py`

**Current behavior** (around lines 55–79): `brief_path.write_text(...)` is called first, then `source_path.write_text(...)`. A crash between these two calls leaves `mission-brief.md` present without `brief-source.yaml`, which blocks subsequent re-ingest.

**Steps**:

1. Import `os` at the top of the file (if not already imported).

2. Replace the two `write_text` calls with atomic temp-file logic:

   ```python
   import os

   # Write to PID-namespaced temp files in the same directory first.
   # Both temps are fully written before either replace is called,
   # so a crash before the first replace leaves no committed state.
   tmp_brief = kittify / f".tmp-brief-{os.getpid()}.md"
   tmp_source = kittify / f".tmp-source-{os.getpid()}.yaml"
   try:
       tmp_brief.write_text(brief_text, encoding="utf-8")
       tmp_source.write_text(
           yaml.safe_dump(source_data, default_flow_style=False),
           encoding="utf-8",
       )
       tmp_brief.replace(brief_path)      # atomic on POSIX (os.rename)
       tmp_source.replace(source_path)    # atomic on POSIX
   except Exception:
       tmp_brief.unlink(missing_ok=True)  # clean up on any error
       tmp_source.unlink(missing_ok=True)
       raise
   ```

3. `Path.replace()` is atomic on POSIX. On Windows it is best-effort (not atomic but still safe in practice for this use case). No platform guard is needed.

4. Do not change the return value or the function signature — `write_mission_brief()` still returns `(brief_path, source_path)`.

**Validation**:
- [ ] After a successful call, both `brief_path` and `source_path` exist and contain correct content
- [ ] No temp files (`.tmp-brief-*.md`, `.tmp-source-*.yaml`) remain after a successful call
- [ ] A simulated crash mid-way (e.g., exception after `tmp_brief.write_text` but before `tmp_brief.replace`) leaves no partial state at `brief_path`

---

## Subtask T021 — File size cap in `intake.py`

**File**: `src/specify_cli/cli/commands/intake.py`

**Steps**:

1. Add a module-level constant near the top of the file (after imports, before function definitions):
   ```python
   # Maximum size for a mission brief file. Rejects files before reading into memory.
   MAX_BRIEF_FILE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB
   ```

2. In `_write_brief_from_candidate()` (around line 163), add a size check **before** `found_path.read_text()`:
   ```python
   try:
       file_size = found_path.stat().st_size
   except OSError:
       file_size = 0  # if stat fails, let read_text raise its own error
   if file_size > MAX_BRIEF_FILE_SIZE_BYTES:
       err_console.print(
           f"[red]File is too large to ingest ({file_size / 1024 / 1024:.1f} MB). "
           f"Maximum allowed size is {MAX_BRIEF_FILE_SIZE_BYTES // 1024 // 1024} MB.[/red]"
       )
       raise typer.Exit(1)
   content = found_path.read_text(encoding="utf-8")
   ```

3. In the explicit-path intake path (around line 175, inside the `else:` branch for non-stdin intake):
   ```python
   file_path_obj = Path(path)
   try:
       file_size = file_path_obj.stat().st_size
   except OSError:
       file_size = 0
   if file_size > MAX_BRIEF_FILE_SIZE_BYTES:
       err_console.print(
           f"[red]File is too large to ingest ({file_size / 1024 / 1024:.1f} MB). "
           f"Maximum allowed size is {MAX_BRIEF_FILE_SIZE_BYTES // 1024 // 1024} MB.[/red]"
       )
       raise typer.Exit(1)
   content = file_path_obj.read_text(encoding="utf-8")
   ```

4. Do **not** apply the size check to stdin (the `path == "-"` branch) — stdin has no meaningful size.

**Validation**:
- [ ] `MAX_BRIEF_FILE_SIZE_BYTES` is a named constant at module level (not inline)
- [ ] A file larger than 5 MB is rejected with the size error message before `read_text()` is called
- [ ] A file exactly at 5 MB is accepted (check is `>`, not `>=`)
- [ ] A file smaller than 5 MB is accepted normally
- [ ] The error message includes the actual file size in MB and the limit in MB

---

## Subtask T022 — Repo-root containment in `scan_for_plans()`

**File**: `src/specify_cli/intake_sources.py`

**Current behavior** (around lines 175–195): `abs_path = cwd / rel_path` is built, but `abs_path.resolve()` is never checked against `cwd.resolve()`. A `rel_path` of `../../escape/plan.md` passes through.

**Steps**:

1. Resolve `cwd` once before the loop (avoids repeated calls):
   ```python
   cwd_resolved = cwd.resolve()
   ```

2. In the loop, after building `abs_path`, add the containment check:
   ```python
   abs_path = cwd / rel_path
   try:
       if not abs_path.resolve().is_relative_to(cwd_resolved):
           continue  # silently skip out-of-bounds paths
   except (ValueError, OSError):
       continue  # resolve() failure → skip
   ```

3. Apply the same check inside the directory-expansion branch, for the directory itself:
   ```python
   elif abs_path.is_dir():
       try:
           if not abs_path.resolve().is_relative_to(cwd_resolved):
               continue  # directory outside repo root
       except (ValueError, OSError):
           continue
       for child in sorted(abs_path.iterdir()):
           ...  # existing logic
   ```

4. **Note**: `Path.is_relative_to()` is Python 3.9+. The project requires Python 3.11+, so this is available without a compatibility shim.

**Validation**:
- [ ] A `rel_path` of `../../escape/plan.md` (resolves outside cwd) → excluded
- [ ] A `rel_path` of `.opencode/plans/brief.md` (in-bounds) → included as before
- [ ] A directory path that resolves outside cwd → excluded (the whole directory, not just children)

---

## Subtask T023 — Symlink exclusion in directory expansion

**File**: `src/specify_cli/intake_sources.py`

**Current behavior**: Inside the directory-expansion `for child in sorted(abs_path.iterdir()):` loop, `child.is_file()` follows symlinks, so a symlink to an external file is included.

**Steps**:

1. Before the `if child.is_file()` check, add a symlink guard:
   ```python
   for child in sorted(abs_path.iterdir()):
       try:
           if child.is_symlink():
               continue  # never follow symlinks out of the tree
           if child.is_file() and child.suffix == ".md":
               results.append((child, harness_key, source_agent_value))
       except (PermissionError, OSError):
           pass
   ```

2. The symlink guard must come **before** `is_file()` because `is_file()` follows the link.

3. No change to the direct `abs_path.is_file()` check for non-directory paths — if a harness source entry is itself a symlink pointing to an in-bounds file, we rely on the containment check from T022 to enforce bounds. Symlink exclusion only applies to the directory-expansion iteration.

**Validation**:
- [ ] A symlink inside `.opencode/plans/` pointing to `/etc/passwd` → excluded
- [ ] A symlink inside `.opencode/plans/` pointing to another file inside the repo → also excluded (symlinks unconditionally excluded in directory expansion)
- [ ] A regular `.md` file in `.opencode/plans/` → included as before

---

## Subtask T024 — Tests: brief atomicity

**File**: `tests/specify_cli/test_mission_brief.py` (create if absent; check for existing test file)

**Tests to write**:

```python
def test_write_mission_brief_both_files_present_after_success(tmp_path):
    """Both brief and sidecar are written atomically."""
    brief_path, source_path = write_mission_brief(
        tmp_path, "# Test brief", "test.md"
    )
    assert brief_path.exists()
    assert source_path.exists()
    # No temp files left behind
    assert not list(tmp_path.glob(".kittify/.tmp-brief-*.md"))
    assert not list(tmp_path.glob(".kittify/.tmp-source-*.yaml"))

def test_write_mission_brief_no_partial_state_on_error(tmp_path, monkeypatch):
    """A crash between the two write_text calls leaves no partial state at the final paths."""
    call_count = [0]
    original_write_text = Path.write_text

    def patched_write_text(self, text, **kwargs):
        call_count[0] += 1
        if call_count[0] == 2:
            raise OSError("simulated crash")
        return original_write_text(self, text, **kwargs)

    monkeypatch.setattr(Path, "write_text", patched_write_text)

    with pytest.raises(OSError):
        write_mission_brief(tmp_path, "# Test", "test.md")

    kittify = tmp_path / ".kittify"
    # Neither final path should exist (temp files cleaned up, replace never called)
    assert not (kittify / "mission-brief.md").exists()
    # No temp files should remain either
    assert not list(kittify.glob(".tmp-brief-*.md"))
    assert not list(kittify.glob(".tmp-source-*.yaml"))

def test_write_mission_brief_return_value_unchanged(tmp_path):
    """write_mission_brief still returns (brief_path, source_path) tuple."""
    result = write_mission_brief(tmp_path, "# content", "source.md")
    assert isinstance(result, tuple)
    assert len(result) == 2
    brief, source = result
    assert brief.name == "mission-brief.md"
    assert source.name == "brief-source.yaml"
```

**Validation**:
- [ ] All three tests pass
- [ ] The crash-simulation test verifies no partial state (key requirement from FR-013)

---

## Subtask T025 — Tests: oversized file rejection

**File**: `tests/specify_cli/cli/commands/test_intake.py` (create or add to existing)

**Tests to write**:

```python
def test_intake_rejects_oversized_file(tmp_path, runner):
    """Intake exits 1 with a size error for files exceeding MAX_BRIEF_FILE_SIZE_BYTES."""
    from specify_cli.cli.commands.intake import MAX_BRIEF_FILE_SIZE_BYTES

    big_file = tmp_path / "big_brief.md"
    # Write a file slightly over the limit
    big_file.write_bytes(b"x" * (MAX_BRIEF_FILE_SIZE_BYTES + 1))

    result = runner.invoke(app, ["intake", str(big_file)])
    assert result.exit_code == 1
    assert "too large" in result.output.lower() or "too large" in (result.stderr or "").lower()

def test_intake_accepts_file_at_limit(tmp_path, runner):
    """A file exactly at MAX_BRIEF_FILE_SIZE_BYTES is accepted."""
    from specify_cli.cli.commands.intake import MAX_BRIEF_FILE_SIZE_BYTES

    exact_file = tmp_path / "exact.md"
    exact_file.write_bytes(b"# brief\n" + b"x" * (MAX_BRIEF_FILE_SIZE_BYTES - 8))
    # Should not raise (may fail for other reasons but not size)
    # ... test that the size check passes (exit code not 1 due to size)

def test_intake_size_cap_is_named_constant():
    """MAX_BRIEF_FILE_SIZE_BYTES is importable as a named constant."""
    from specify_cli.cli.commands.intake import MAX_BRIEF_FILE_SIZE_BYTES
    assert isinstance(MAX_BRIEF_FILE_SIZE_BYTES, int)
    assert MAX_BRIEF_FILE_SIZE_BYTES == 5 * 1024 * 1024

def test_intake_rejects_before_reading(tmp_path, monkeypatch, runner):
    """Size check fires before read_text() is called."""
    from specify_cli.cli.commands.intake import MAX_BRIEF_FILE_SIZE_BYTES

    read_called = [False]
    original_read = Path.read_text
    def spy_read(self, **kwargs):
        read_called[0] = True
        return original_read(self, **kwargs)
    monkeypatch.setattr(Path, "read_text", spy_read)

    big_file = tmp_path / "big.md"
    big_file.write_bytes(b"x" * (MAX_BRIEF_FILE_SIZE_BYTES + 1))
    runner.invoke(app, ["intake", str(big_file)])
    assert not read_called[0], "read_text should not be called on oversized file"
```

**Validation**:
- [ ] All four tests pass
- [ ] The spy test confirms the file is never read (key requirement from FR-014)

---

## Subtask T026 — Tests: out-of-bounds path exclusion

**File**: `tests/specify_cli/test_intake_sources.py` (create or add to existing)

**Tests to write**:

```python
def test_scan_for_plans_excludes_out_of_bounds_path(tmp_path, monkeypatch):
    """Paths that resolve outside cwd are excluded from results."""
    from specify_cli.intake_sources import scan_for_plans, HARNESS_PLAN_SOURCES

    # Create an in-bounds file
    inbound = tmp_path / ".opencode" / "plans" / "brief.md"
    inbound.parent.mkdir(parents=True)
    inbound.write_text("# brief")

    # Create an out-of-bounds file (in a parent directory)
    escape_dir = tmp_path.parent / "escape"
    escape_dir.mkdir(exist_ok=True)
    escape_file = escape_dir / "plan.md"
    escape_file.write_text("# escape")

    # Patch HARNESS_PLAN_SOURCES to include the out-of-bounds path
    patched_sources = [
        ("opencode", "opencode", [".opencode/plans/brief.md"]),
        ("escape", None, [f"../../escape/plan.md"]),  # traverses out
    ]
    monkeypatch.setattr("specify_cli.intake_sources.HARNESS_PLAN_SOURCES", patched_sources)

    results = scan_for_plans(tmp_path)
    paths = [r[0] for r in results]
    assert inbound.resolve() in [p.resolve() for p in paths], "in-bounds file should be included"
    assert escape_file.resolve() not in [p.resolve() for p in paths], "escape file should be excluded"

def test_scan_for_plans_includes_valid_inbounds_paths(tmp_path):
    """Normal in-repo paths are still returned after containment check."""
    brief = tmp_path / ".opencode" / "plans" / "brief.md"
    brief.parent.mkdir(parents=True)
    brief.write_text("# brief")
    # ... configure and call scan_for_plans
    # Assert brief is in results
```

**Validation**:
- [ ] Tests pass
- [ ] Out-of-bounds path not in results; in-bounds path is present

---

## Subtask T027 — Tests: symlink exclusion

**File**: `tests/specify_cli/test_intake_sources.py`

**Tests to write**:

```python
def test_scan_for_plans_excludes_symlink_in_directory(tmp_path):
    """Symlinks in plan directories are not followed."""
    plans_dir = tmp_path / ".opencode" / "plans"
    plans_dir.mkdir(parents=True)

    # Regular file (should be included)
    regular = plans_dir / "brief.md"
    regular.write_text("# real brief")

    # Symlink pointing outside (should be excluded)
    outside = tmp_path.parent / "outside.md"
    outside.write_text("# outside")
    symlink = plans_dir / "linked.md"
    symlink.symlink_to(outside)

    results = scan_for_plans(tmp_path)
    paths = [r[0] for r in results]
    assert regular.resolve() in [p.resolve() for p in paths], "regular file should be included"
    assert symlink not in paths, "symlink should be excluded"
    assert outside.resolve() not in [p.resolve() for p in paths], "symlink target should be excluded"

def test_scan_for_plans_excludes_inbound_symlink_too(tmp_path):
    """Even a symlink pointing within the repo is excluded (symlinks unconditionally excluded)."""
    plans_dir = tmp_path / ".opencode" / "plans"
    plans_dir.mkdir(parents=True)
    target = tmp_path / "real.md"
    target.write_text("# target")
    symlink = plans_dir / "inbound_link.md"
    symlink.symlink_to(target)

    results = scan_for_plans(tmp_path)
    paths = [r[0] for r in results]
    assert symlink not in paths
```

**Validation**:
- [ ] Tests pass
- [ ] Symlinks are excluded regardless of where they point
- [ ] The `symlink_to` call works on macOS/Linux; skip test on platforms that don't support symlinks if needed (use `pytest.mark.skipif(not hasattr(os, "symlink"), ...)`)

---

## Definition of Done

- [ ] `write_mission_brief()` uses atomic temp-file + replace pattern
- [ ] `MAX_BRIEF_FILE_SIZE_BYTES = 5 * 1024 * 1024` constant in `intake.py` (module level)
- [ ] Size check in `intake.py` fires before `read_text()` in both candidate and explicit-path flows
- [ ] `scan_for_plans()` checks `resolve().is_relative_to(cwd_resolved)` for all candidates
- [ ] `scan_for_plans()` directory expansion skips symlinks before `is_file()` check
- [ ] Regression tests exist for all four fixes (T024–T027), covering both the fix and the happy path
- [ ] No pre-existing intake or mission_brief tests fail
- [ ] `mypy --strict src/specify_cli/mission_brief.py src/specify_cli/cli/commands/intake.py src/specify_cli/intake_sources.py` exits 0
- [ ] FR-013, FR-014, FR-015, FR-016, FR-017 satisfied (verify spec scenarios S-07 through S-11)

## Risks

- **Temp file cleanup on Windows**: `Path.replace()` on Windows requires the destination to not exist. `brief_path` and `source_path` may already exist (overwrite scenario). Test the overwrite case on the CI platform.
- **Stat failure edge case**: If `stat()` raises (e.g., file disappears between detection and stat), we set `file_size = 0` and let `read_text()` raise its own `FileNotFoundError`. This is the correct behavior — don't swallow stat errors silently.
- **`is_relative_to` on Python 3.9 vs 3.11**: The project requires 3.11+, so this is fine. But if a CI matrix runs 3.9 for any reason, this will fail. Confirm CI matrix in `pyproject.toml`.
- **Symlink resolution edge case**: On some filesystems, `child.is_symlink()` returns `False` for bind mounts. This is out of scope for this fix.

## Reviewer Guidance

1. Confirm `write_mission_brief()` has no direct `write_text()` calls — only the atomic temp-file pattern.
2. Confirm `MAX_BRIEF_FILE_SIZE_BYTES` is at module level in `intake.py` and importable.
3. Confirm the size check comes before `read_text()` in both intake paths (use test T025's spy to verify).
4. Confirm `is_symlink()` check appears **before** `is_file()` check in the directory iteration loop.
5. Confirm `is_relative_to(cwd_resolved)` is applied to both direct file paths and directory expansion.
6. Run the full intake test suite and the mission_brief test suite to confirm zero regressions.
