# Phase 0 Research: Windows Compatibility Hardening Pass

**Mission**: `windows-compatibility-hardening-01KP5R6K`
**Date**: 2026-04-14

This document resolves every technical unknown required before Phase 1 design. Each section records Decision → Rationale → Alternatives considered, per DIRECTIVE_003.

## R-01. Canonical Windows runtime state location

**Decision**: `%LOCALAPPDATA%\spec-kitty\` resolved via `platformdirs.user_data_dir("spec-kitty", appauthor=False, roaming=False)`. On Windows 10/11 this expands to `C:\Users\<user>\AppData\Local\spec-kitty\`. Subdirectories used by this mission: `auth/`, `tracker/`, `sync/`, `daemon/`, `cache/`.

**Rationale**:
- Matches `kernel/paths.py`'s existing platformdirs usage (avoids resurrecting the inconsistency with `~/.spec-kitty`).
- `LOCAL` (non-roaming) is correct because these files are machine-local state (auth secrets, PIDs, tracker DBs) that should not follow a user across machines via roaming profiles.
- Aligns with Microsoft guidance for per-user, per-machine application data.
- Avoids `%APPDATA%` (roaming) which would replicate secrets and lock files across hosts.

**Alternatives considered**:
- `%APPDATA%\spec-kitty\` (roaming) — rejected: auth secrets and PID files must not replicate.
- `%PROGRAMDATA%\spec-kitty\` (all-users) — rejected: per-user state, would require admin to write.
- Keep `~/.spec-kitty` on Windows — rejected by Q3=C.
- Use `XDG_DATA_HOME` polyfill on Windows — rejected: not a Windows idiom.

## R-02. Legacy locations that must be migrated on Windows

**Decision**: Migration considers three legacy roots in this order:
1. `~/.spec-kitty/` → `%LOCALAPPDATA%\spec-kitty\` (tracker, sync, daemon state)
2. `~/.kittify/` → legacy messaging-only; no state-carrying files to move, but stale references purged from UI
3. `~/.config/spec-kitty/` → `%LOCALAPPDATA%\spec-kitty\auth\` (historical auth file-fallback `_DEFAULT_DIR`)

**Rationale**:
- Enumerated directly from the spec's Assumptions and FR-006.
- Matches the call-sites audited in the prior scan (`tracker/credentials.py`, `sync/daemon.py`, `auth/secure_storage/file_fallback.py`).

**Alternatives considered**:
- Migrate `~/.kittify/` contents too — rejected: `kernel/paths.py` already resolves Windows to `%LOCALAPPDATA%\kittify\`, so `~/.kittify` on Windows is a messaging bug, not a real storage root. No files to move.
- Include `.\.kittify\` per-project state — rejected: that is project-local state (committed to repos), not user state. Out of scope.

## R-03. Destination-wins migration algorithm (idempotent, safe under contention)

**Decision**: Per legacy root:
1. Resolve `legacy_root`. If it does not exist, record `status: absent` and continue.
2. Resolve `dest_root` under `%LOCALAPPDATA%\spec-kitty\...`.
3. Acquire `%LOCALAPPDATA%\spec-kitty\.migrate.lock` via `msvcrt.locking()` with a short timeout; on timeout, exit with an actionable error.
4. If `dest_root` is absent or empty: `os.replace(legacy_root, dest_root)` (atomic on same volume; fallback to copy-and-remove across volumes).
5. If `dest_root` is non-empty: rename `legacy_root` to `legacy_root.parent / f"{legacy_root.name}.bak-{ts}"` where `ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")`. Record `status: quarantined`.
6. Release lock, emit single summary CLI message naming: canonical destination, legacy sources acted on, quarantine paths.

**Idempotency**: Step 1 makes repeat invocations no-ops. Step 5 collision is avoided by the ISO-UTC timestamp in the backup name; if two backups are created within the same UTC second (extremely rare), an `_N` suffix is appended.

**Rationale**:
- `os.replace` is atomic when source and destination share a volume (standard Windows case).
- The `msvcrt.locking()` lock prevents two concurrent CLI invocations from racing into half-migrated state (NFR-004, FR-007).
- Timestamped quarantine (as chosen in Q2=A) preserves rollback capability and avoids any destructive merge.

**Alternatives considered**:
- `shutil.move` only — rejected: non-atomic across volumes; hides partial-failure states.
- File-level `fcntl.flock` — rejected: not available on Windows (would reintroduce #586).
- SQLite-backed migration journal — rejected: overkill for a one-time migration of a small tree.

## R-04. Windows auth storage: hard platform split implementation

**Decision**:
1. `SecureStorage.from_environment()` becomes: `if sys.platform == "win32": return WindowsFileStorage(...)` else existing keychain-first logic.
2. `WindowsFileStorage` is a thin subclass / factory around the existing `file_fallback.EncryptedFileStorage` wired to `%LOCALAPPDATA%\spec-kitty\auth\`.
3. `src/specify_cli/auth/secure_storage/__init__.py` conditional-imports `keychain` only when `sys.platform != "win32"`.
4. `pyproject.toml` marker: `keyring >= X; sys_platform != "win32"`. Windows wheels/sdists do not pull `keyring`.
5. Type checking: `keychain.py` gets a `TYPE_CHECKING`-only import shape so `mypy --strict` still verifies it on all platforms, but runtime import is suppressed on Windows.

**Rationale**:
- Matches Q1=A exactly: Windows never imports `keychain.py`; `keyring` is not a Windows dependency.
- `sys_platform` environment markers are the canonical PEP 508 way to conditionalize Windows-only vs non-Windows-only deps. Supported by pip, uv, and pipx.
- `TYPE_CHECKING` guard retains mypy coverage without importing keyring at runtime on Windows.

**Alternatives considered**:
- Runtime `try/except ImportError` for keyring — rejected: weaker posture; keyring could be pulled transitively; fails the "no dependency" spirit of FR-001.
- Optional extras (`spec-kitty-cli[keyring]`) — rejected: unnecessary user-facing configuration burden; not in scope for a hardening pass.
- Full plugin registry — rejected in Q1.

## R-05. Pre-commit hook: absolute `sys.executable` pinning

**Decision**: At install time (`hook_installer.install(...)`):
1. Capture `interpreter = Path(sys.executable).resolve()`.
2. Capture `module = "specify_cli.policy.commit_guard_hook"`.
3. Render the `pre-commit` file with `#!/bin/sh` shebang and an `exec "<interpreter>" -m <module> "$@"` body. The interpreter path is quoted to survive spaces, and a `case` guard strips a leading `/` on Windows-style paths if the hook is invoked under Git for Windows' MSYS (which translates `C:\…` → `/c/…` when Git calls hooks).
4. Make the hook executable (`0o755`) — no-op semantics on NTFS but required for Git hook discovery on POSIX.
5. On Windows, also write a `pre-commit.ps1` next to the hook ONLY if FR-010 testing surfaces a Git-for-Windows topology that cannot exec the sh hook. (Default: do not write.)

**MSYS path translation**: Git for Windows' `sh.exe` mangles drive-letter arguments. The installer writes the interpreter path in the form Git's sh accepts: the raw `C:\...\python.exe` string works if the shebang line invokes it directly (bash preserves shebangs), but to be safe the hook body uses a POSIX-style `/c/...` form computed at install time when `sys.platform == "win32"`. Both forms are validated by the executable-hook test.

**Rationale**:
- Q3=A locks the single-file shape with absolute interpreter pinning.
- MSYS path translation is a well-documented Git-for-Windows quirk; dealing with it at install time beats dealing with it in the hook body.
- `0o755` is harmless on NTFS and required on POSIX; no conditional.

**Alternatives considered**:
- `py -3 ...` launcher — rejected in Q3.
- `.cmd` companion — rejected in Q3 unless FR-010 testing proves necessity.
- `#!python` shebang (PEP 394-ish) — rejected: PATH-dependent.

## R-06. Curated `windows_ci` pytest marker scope

**Decision**: New marker `@pytest.mark.windows_ci` registered in `pyproject.toml` under `[tool.pytest.ini_options] markers`. Selection rules:
- A test is `windows_ci` iff its outcome is load-bearing for a Windows-specific code path or a regression issue named in the spec.
- The Windows CI job runs `pytest -m windows_ci`. The default (Linux) job runs `pytest -m "not windows_ci"` so Windows-only tests do not accidentally run on Linux runners that can't exercise them.
- Tests that can run on both platforms without Windows-specific skips do NOT get the marker.

**Initial `windows_ci` set**:
- `tests/auth/secure_storage/test_file_fallback_windows_root.py`
- `tests/paths/test_windows_migrate.py`
- `tests/policy/test_hook_installer_execution.py`
- `tests/sync/test_daemon_windows_paths.py`, `tests/sync/test_issue_586_windows_import.py` (upgraded)
- `tests/tracker/test_credentials_windows_paths.py`
- `tests/core/test_worktree_symlink_fallback.py`
- `tests/kernel/test_paths_unified_windows_root.py`
- `tests/regressions/test_issue_101_utf8_startup.py`
- `tests/regressions/test_issue_105_hook_python_lookup.py`
- `tests/regressions/test_issue_71_dashboard_empty.py` (if reachable on runner)

**Rationale**:
- Markers are first-class pytest and require zero test-runner changes.
- Explicit marker is easier to reason about than directory-based selection when fragile surfaces span multiple existing directories.
- NFR-002 (p95 ≤ 15 min) is easier to meet with a curated set than with the full suite.

**Alternatives considered**:
- Directory-based selection (`tests/windows_critical/`) — rejected: forces physical reorganization; mixes non-Windows test files awkwardly.
- File-naming convention (`test_*_windows.py`) — rejected: conflates "tests about Windows code" with "tests that must run on Windows."

## R-07. Windows CI runner install topology

**Decision**: Single job on `windows-latest` that installs via `pipx`:
```yaml
- name: Install pipx
  run: python -m pip install --user pipx && python -m pipx ensurepath
- name: Install spec-kitty in editable mode
  run: pipx install --editable .
- name: Install test deps
  run: python -m pip install pytest pytest-cov
- name: Run Windows-critical suite
  env:
    PYTHONUTF8: "1"
  run: pytest -m windows_ci --maxfail=1
```

**Rationale**:
- Matches the project's canonical install path (`pipx` per user-global CLAUDE.md).
- `PYTHONUTF8=1` prevents the Windows default ANSI codepage from breaking Unicode tests (touches #101 territory).
- `--maxfail=1` keeps CI cycle time low (NFR-002) and makes the failing test immediately obvious.

**Alternatives considered**:
- `pip install .` — rejected: that's not how users install; CI should match reality.
- Multi-install matrix (pipx × uv) — rejected by scope; plan leaves follow-up room if FR-010 testing uncovers topology divergence.

## R-08. UTF-8 / encoding policy on Windows

**Decision**:
1. CLI entrypoint (`specify_cli.cli.main`) unconditionally ensures UTF-8 I/O on Windows by calling `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` and `sys.stderr.reconfigure(...)` when `sys.platform == "win32"` and the streams are text I/O.
2. All file I/O that touches user-rendered paths uses `encoding="utf-8"` explicitly.
3. CI job sets `PYTHONUTF8=1` to mirror user-facing guidance (docs update in FR-019).
4. Regression test for #101 asserts that startup + status commands render a synthetic non-ASCII path without crashing under a non-UTF-8 code page.

**Rationale**:
- Python 3.11+ supports `reconfigure()` on `TextIOWrapper`; this is the canonical safe knob.
- `PYTHONUTF8=1` is the Microsoft-endorsed approach for Windows Python I/O.
- Regression coverage prevents #101 from recurring.

**Alternatives considered**:
- `chcp 65001` via subprocess — rejected: console-global side effect, unreliable.
- Do nothing, hope for user PYTHONUTF8 — rejected: regression #101 proved this is insufficient.

## R-09. Worktree + symlink-vs-copy fallback revalidation

**Decision**: Keep existing `core/worktree.py` and `mission.py` logic (which the prior scan confirmed is Windows-aware). Add native-Windows integration tests under `windows_ci`:
- `test_worktree_symlink_fallback.py`:
  - Creates a worktree on a `windows-latest` tmp path.
  - Asserts `.kittify/memory/` content is readable (copy fallback materialized).
  - Asserts `AGENTS.md` content matches source.
  - Asserts the test works on a path containing a space.
- `test_active_mission_handle_windows.py` (extracted from/added to `mission.py` test surface):
  - Asserts active-mission handle writes and reads round-trip on Windows without symlink support.

**Rationale**:
- Spec calls out that existing logic "looked intentionally Windows-aware" but needs near-native validation. Tests close the gap.
- No code change needed if tests pass; if they fail, a targeted fix lands in the same lane G.

**Alternatives considered**:
- Introduce Windows Developer Mode symlink support — rejected: user machines cannot be assumed to have it; copy fallback is the robust default.
- Use NTFS junction points programmatically — rejected: outside scope; existing fallback is copy-based and works.

## R-10. User-facing path rendering helper shape

**Decision**: `render_runtime_path(path: Path, *, for_user: bool = True) -> str` under `src/specify_cli/paths/windows_paths.py` (and re-exported from the subpackage). Behavior:
- On non-Windows, returns `~/...`-style tilde-compressed path using `path.expanduser` reverse logic if `for_user=True`, else `str(path)`.
- On Windows, returns the real path as a string (no tilde substitution; real absolute path e.g. `C:\Users\alice\AppData\Local\spec-kitty\auth`).
- CLI call-sites replace literals (`"~/.kittify"`, `"~/.spec-kitty"`) with `render_runtime_path(get_runtime_root() / "auth")`-style calls.

**Rationale**:
- One helper with one signature; easy to audit and test.
- Explicitly separates "user-facing rendering" from "actual path ops" (which always use `Path`).
- Makes FR-012/FR-013 enforceable via a simple grep in CI (audit report documents the grep pattern).

**Alternatives considered**:
- Per-platform f-string constants — rejected: spreads policy across call-sites.
- `rich.Path` rendering — rejected: not a rendering policy layer; we need more than formatting.

## R-11. `keyring` packaging marker correctness

**Decision**: In `pyproject.toml`:
```toml
dependencies = [
    "typer>=...",
    "rich>=...",
    "ruamel.yaml>=...",
    "platformdirs>=...",
    # ... existing deps ...
    "keyring>=25; sys_platform != \"win32\"",
]
```
Windows wheels/sdists install without keyring. macOS/Linux unchanged.

**Rationale**:
- PEP 508 environment markers; supported by every installer in the project's matrix (pip, pipx, uv).
- Closes the "Windows still pulls keyring" loophole that a runtime-only fix would leave open (FR-001 / C-001).

**Alternatives considered**:
- Runtime-only import guard — rejected: keyring still gets installed on Windows; violates spirit of "no dependency on Windows code path."
- Optional extra — rejected: introduces configuration surface we don't want.

## R-12. Second-pass audit methodology

**Decision**: The audit is a grep+review pass producing a committed `architecture/2026-04-14-windows-compatibility-hardening.md` report. Pattern set (FR-018):
- Literals: `~/.kittify`, `~/.spec-kitty`, `.config/spec-kitty`
- Platform calls: `fcntl`, `msvcrt`, `os.symlink`, `os.link`, `Path.symlink_to`
- Subprocess smells: `shell=True`, `"sh -c"`, `/bin/sh` invocations, `python3`, bare `python` as a subprocess argv[0]
- Encoding: `open(` without `encoding=`, `os.fspath`-bypass, `.decode()` without `errors=`
- Windows idioms: `os.name`, `sys.platform`, `%APPDATA%`, `%LOCALAPPDATA%`, `powershell`, `cmd.exe`, `PYTHONUTF8`
- Hook/install: `pre-commit`, `hooks/`, `chmod`, `0o755`, `0o644`
- Tests: `@pytest.mark.skipif.*win`, `sys.platform` branches inside tests

For each hit: (a) fix in a lane, (b) add a `windows_ci` test, or (c) file a GitHub follow-up with label `windows` and link it from the audit report.

**Rationale**:
- DIRECTIVE_003 compliance (decision + context preserved).
- SC-005 depends on this artifact existing and being reviewable.

**Alternatives considered**:
- Automated linter rule — rejected: too high-effort for a one-time pass; a grep-report is traceable and auditable.
- GitHub project board — rejected: audit report in-repo is permanent; project board is ephemeral.

## Open questions

None. All Technical Context unknowns resolved; no `[NEEDS CLARIFICATION]` markers remain. Phase 1 proceeds.
