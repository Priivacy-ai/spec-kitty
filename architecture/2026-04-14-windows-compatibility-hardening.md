# Windows Compatibility Hardening — Audit Report (2026-04-14)

**Mission**: windows-compatibility-hardening-01KP5R6K
**Commit range**: c26a7dd8..4fce47a1 (lane-a) + ff93078b (lane-b)
**Method**: Second-pass repo-wide grep audit per FR-018 pattern list (see `research.md` R-12).
**Date**: 2026-04-14
**Auditor**: claude:opus-4.6:implementer:implementer (WP09)

---

## Summary

| Category | Count |
|----------|-------|
| Total raw hits (non-empty grep lines across all 7 pattern sets) | 1417 |
| Safe (false positives — docs/specs/comments/test metadata) | 1369 |
| Fixed by this mission (WP01–WP08) | 29 |
| Covered by new Windows CI (`@pytest.mark.windows_ci`) | 12 |
| Filed as follow-up issues | 7 |

**Net Windows-risk residual in source code**: 7 findings → 3 follow-up issues filed (see §Follow-up issues filed).

---

## Closeable GitHub Issues

| Issue | Title | Posture |
|-------|-------|---------|
| [#603](https://github.com/Priivacy-ai/spec-kitty/issues/603) | Cut over CLI auth storage to encrypted file-only backend | **CLOSEABLE.** Fixed by WP03. `keyring` absent from Windows install (CI-asserted in `ci-windows.yml`). Auth hard-splits on `sys.platform == "win32"` to `WindowsFileStorage`. See ADR `architecture/adrs/2026-04-14-1-windows-auth-platform-split.md`. |
| [#260](https://github.com/Priivacy-ai/spec-kitty/issues/260) | Worktree 'incompatibility' when changing to worktree sub-directory | **SCOPED / PARTIAL.** Root cause is MCP tool (Serena) using repo root as its working directory while the agent `cd`s into a worktree. This is an editor-side MCP server configuration issue, not a Spec Kitty code bug. Spec Kitty's workspace resolution (WP08 lane-b) does not change the worktree topology. Follow-up issue #`windows-260-worktree-mcp-root` filed to document the workaround and to explore a `--in-place` mode. See §Follow-up issues filed. |
| [#586](https://github.com/Priivacy-ai/spec-kitty/issues/586) | fcntl on Windows | **CLOSEABLE.** All three `import fcntl` sites in source are inside `sys.platform == "win32"` guards (`if sys.platform == "win32": import msvcrt; else: import fcntl`). WP05 re-rooted daemon paths to `%LOCALAPPDATA%\spec-kitty\`. |
| [#105](https://github.com/Priivacy-ai/spec-kitty/issues/105) | Hard-coded `~/.spec-kitty` paths | **CLOSEABLE.** WP01 (RuntimeRoot/render_runtime_path), WP04 (path messaging sweep), and WP05 (tracker/sync/daemon re-rooting) eliminated all runtime uses. Remaining occurrences are documentation strings and schema `path_pattern` metadata — not actual Path operations. |
| [#101](https://github.com/Priivacy-ai/spec-kitty/issues/101) | UnicodeDecodeError on Windows stdout | **CLOSEABLE.** WP08 added UTF-8 enforcement in `main()` (`sys.stdout.reconfigure(encoding="utf-8")`) and a regression test `tests/regressions/test_issue_101_utf8_startup.py`. CI sets `PYTHONUTF8=1`. |
| [#71](https://github.com/Priivacy-ai/spec-kitty/issues/71) | Dashboard renders empty on Windows | **CLOSEABLE.** WP08 added regression test `tests/regressions/test_issue_71_dashboard_empty.py` with `@pytest.mark.windows_ci`. Root cause was UTF-8 encoding — addressed by the same fix as #101. |

---

## Classification Table

Every hit is classified as one of: **Safe** (false positive / docs / non-runtime), **Fixed** (addressed by WP01–WP08), **CI-covered** (regression prevented by new Windows CI test), or **Follow-up** (real Windows risk not covered by this mission).

### Category 1: Literals (`~/\.kittify`, `~/\.spec-kitty`, `.config/spec-kitty`)

Total raw hits: 650. Breakdown by file location:

| Hit | File | Label | WP / Test / Note |
|-----|------|-------|-----------------|
| `~/\.kittify/` in docstrings/comments | `src/kernel/paths.py:4,25,29,38` | Safe | POSIX doc in module that dispatches Windows to `%LOCALAPPDATA%\spec-kitty\` |
| `~/\.kittify/` in enum comment | `src/specify_cli/state_contract.py:18` | Safe | `path_pattern` is schema metadata, never resolved as a path on Windows |
| `~/\.spec-kitty/` in `path_pattern` strings | `src/specify_cli/state_contract.py:406–499` | Safe | Schema documentation strings; resolved at runtime through `get_runtime_root()` which handles Windows correctly |
| All `~/` hits in `kitty-specs/**/` | Multiple spec files | Safe | Planning artifacts / historical documentation |
| All `~/` hits in `architecture/**`, `docs/**`, `CHANGELOG.md`, `MANUAL_TEST_PLAN.md`, `contracts/**` | Multiple | Safe | Documentation only |
| All `~/` hits in `tests/**` | Multiple test files | Safe | Test strings that confirm POSIX paths; tests that validate Windows-specific paths use `RuntimeRoot` / `render_runtime_path` |

**Verdict**: All 650 literal hits outside `src/specify_cli/state_contract.py` and `src/kernel/paths.py` are in documentation, planning artifacts, or tests. The two source-code occurrences are schema metadata and doc comments, not path operations. **No live Windows-risk literals remain.**

### Category 2: Platform calls (`fcntl`, `msvcrt`, `os.symlink`, `os.link`, `Path.symlink_to`)

Total raw hits: 16.

| Hit | File:Line | Label | Detail |
|-----|-----------|-------|--------|
| `import msvcrt` | `src/specify_cli/tracker/credentials.py:20` | Fixed (WP05) | Inside `if sys.platform == "win32":` guard; WP05 re-rooted the path it uses |
| `import fcntl` | `src/specify_cli/tracker/credentials.py:22` | Fixed (WP05) | Inside `else:` of the same guard |
| `import msvcrt` | `src/specify_cli/paths/windows_migrate.py:177` | Fixed (WP02) | Inside `sys.platform == "win32"` guard; intentional Windows-only import |
| `import msvcrt` | `src/specify_cli/sync/daemon.py:25` | Fixed (WP05) | Inside `if sys.platform == "win32":` guard at module top |
| `import fcntl` | `src/specify_cli/sync/daemon.py:27` | Fixed (WP05) | Inside `else:` of the same guard |
| `import msvcrt` | `src/specify_cli/runtime/bootstrap.py:49` | Fixed (WP05) | Inside `if sys.platform == "win32":` guard |
| `import fcntl` | `src/specify_cli/runtime/bootstrap.py:53` | Fixed (WP05) | Inside `else:` of the same guard |
| `os.symlink` | `src/specify_cli/upgrade/migrations/m_0_8_0_worktree_agents_symlink.py:116` | Follow-up (#FU-1) | Called without a Windows guard; catches `OSError` and falls back to `shutil.copy2`. The fallback is correct behavior but the error path on Windows is untested. See §Follow-up. |
| `os.link` hits | Various doc strings / tests | Safe | No bare `os.link` calls in production source |

### Category 3: Subprocess smells (`shell=True`, `sh -c`, `/bin/sh`, `python3`, bare `python`)

Total raw hits: 91.

| Hit | File:Line | Label | Detail |
|-----|-----------|-------|--------|
| `shell=True` | `src/specify_cli/review/baseline.py:278` | Follow-up (#FU-2) | Used to run a user-supplied `test_command` template string. `shell=True` is unsafe on Windows when the command string is not a cmd.exe idiom. CI-untested on Windows. |
| `shell=True` | `src/specify_cli/acceptance_matrix.py:269` | Follow-up (#FU-2) | Same pattern — runs `ni.verification_command` with `shell=True`. |
| `shell=True` in `src/doctrine/skills/spec-kitty-mission-review/SKILL.md:390,410` | Skill markdown | Safe | Grep patterns in a doc skill, not executable code |
| `python` in `src/specify_cli/policy/hook_installer.py:HOOK_SCRIPT` (lane-a) | `hook_installer.py` | Fixed (WP06) | Lane-a version used bare `python`. WP06 (lane-b) replaced with `sys.executable` path pinning. |
| `/bin/sh` shebang in `HOOK_TEMPLATE` | `src/specify_cli/policy/hook_installer.py` (lane-b) | Fixed (WP06) | Standard POSIX shebang for git hooks; Git for Windows' sh handles this. Atomic write with `os.replace`. |
| All other hits | Various test files, spec docs, CI yamls | Safe | Either test utilities exercising git, or documentation examples |

### Category 4: Encoding (`.decode()` without `errors=`)

Total raw hits: 47.

| Hit | File:Line | Label | Detail |
|-----|-----------|-------|--------|
| `.decode("utf-8")` | `src/specify_cli/sync/daemon.py:234,301` | Safe | Explicit `"utf-8"` codec; JSON payloads over wire — deterministically UTF-8 |
| `.decode("utf-8")` | `src/specify_cli/sync/body_upload.py:122` | Safe | Explicit `"utf-8"` for file content |
| `.decode("utf-8", errors="replace")` | `src/specify_cli/merge/conflict_resolver.py:135,136` | Safe | Has `errors=` parameter |
| `.decode(encoding)` + fallback | `src/specify_cli/text_sanitization.py:174,180` | Safe | Tries detected encoding, falls back with `errors="replace"` |
| `.decode("utf-8")` + fallback | `src/specify_cli/acceptance.py:371,379,384` | Safe | Three-tier decode with `errors="replace"` fallback |
| `.decode("utf-8")` | `src/specify_cli/dossier/hasher.py:110` | Safe | UTF-8 explicit; file content in a try block |
| `.decode('utf-8')` | `src/specify_cli/dashboard/handlers/base.py:43` | Safe | HTTP request body — explicit UTF-8 |
| `.decode("utf-8")` | `src/specify_cli/dashboard/templates/__init__.py:22` | Safe | Package-embedded HTML resource; deterministically UTF-8 |
| `.decode('utf-8')` | `src/specify_cli/dashboard/lifecycle.py:180` | Safe | Websocket payload |
| `.decode("utf-8")` | `src/specify_cli/auth/secure_storage/file_fallback.py:211` | Fixed (WP03) | Auth file read with explicit UTF-8; WP03 hardened this path |
| `.decode(encoding)` / `.decode("utf-8", errors="replace")` | `src/specify_cli/cli/commands/validate_encoding.py:168,173` | Safe | Encoding validator command itself — handles error paths |
| `.decode("utf-8", errors="replace")` | `src/specify_cli/cli/commands/upgrade.py:33` | Safe | Has `errors=` |
| `.decode("ascii")` | `src/specify_cli/auth/loopback/pkce.py:47` | Safe | Base64 output is pure ASCII by definition |
| `.decode("ascii")` | `src/specify_cli/auth/http/transport.py:301` | Safe | HTTP path parsing; ASCII only |
| All remaining `.decode()` in tests | Various | Safe | Test assertions with explicit encoding |

**Verdict**: All `.decode()` calls in production source either use explicit `"utf-8"` codec (acceptable — deterministic wire format), specify `errors=`, or use `"ascii"` on guaranteed-ASCII content. **No silent codec-selection risk remains.** WP08 additionally enforces `PYTHONUTF8=1` in CI and reconfigures `sys.stdout`/`sys.stderr` in `main()`.

### Category 5: Windows idioms (`os.name`, `sys.platform`, `%APPDATA%`, `%LOCALAPPDATA%`, `powershell`, `cmd.exe`, `PYTHONUTF8`)

Total raw hits: 343.

| Hit | File(s) | Label | Detail |
|-----|---------|-------|--------|
| `sys.platform == "win32"` guards | `src/specify_cli/auth/secure_storage/__init__.py:23`, `abstract.py:64`, `file_fallback.py:43` | Fixed (WP03) | Hard auth split — exactly the right idiom |
| `sys.platform == "win32"` guards | `src/specify_cli/sync/daemon.py:24,46,60,108,560,596` | Fixed (WP05) | Daemon platform dispatch |
| `sys.platform == "win32"` | `src/specify_cli/__init__.py:203` | Fixed (WP08) | UTF-8 enforcement guard |
| `sys.platform` in `upgrade/runner.py:341` | `runner.py` | Safe | Passed as metadata field in upgrade telemetry |
| `sys.platform` in `paths/windows_migrate.py:14` | `windows_migrate.py` | Fixed (WP02) | Module-level doc note about guard pattern |
| `os.name == "nt"` | `src/kernel/paths.py:21` | Fixed (WP01) | `_is_windows()` helper in the paths subpackage |
| `os.name == "nt"` | `src/specify_cli/migration/rewrite_shims.py:68`, `runtime/agent_commands.py:85`, `upgrade/migrations/m_2_1_3/4:113` | Safe | PowerShell vs sh shim selection — correct Windows idiom |
| `os.name == "nt"` | `src/specify_cli/__init__.py:170` | Fixed (WP08) | UTF-8 enforcement guard |
| `os.name == "nt"` | `src/specify_cli/runtime/home.py:18` | Safe | `is_windows()` helper |
| `os.name != "nt"` | `src/specify_cli/tracker/credentials.py:130` | Fixed (WP05) | POSIX-only chmod guard |
| `PYTHONUTF8` | `src/specify_cli/__init__.py`, `.github/workflows/ci-windows.yml` | Fixed (WP08) | CI sets it; startup enforces it |
| `%LOCALAPPDATA%` | `src/specify_cli/paths/windows_paths.py`, `windows_migrate.py`, `kernel/paths.py` | Fixed (WP01,WP02) | Canonical Windows root resolution via `platformdirs` |
| All `sys.platform`/`os.name` in tests | Test files | Safe | Test platform dispatching — expected |
| All in docs/specs | Various | Safe | Documentation references |

### Category 6: Hook/install (`pre-commit`, `hooks/`, `chmod`, `0o755`, `0o644`)

Total raw hits: 270.

| Hit | File:Line | Label | Detail |
|-----|-----------|-------|--------|
| `hook_path.chmod(... stat.S_IEXEC)` | `src/specify_cli/policy/hook_installer.py:57` (lane-a) | Fixed (WP06) | Lane-b replaces with `0o755` + atomic `os.replace` |
| `os.chmod(tmp_path_str, 0o755)` | `hook_installer.py` (lane-b) | Fixed (WP06) | `0o755` chmod on NTFS is no-op; Git for Windows reads the executable bit from the shebang, not the mode. Correct behavior. |
| `os.chmod(self._salt_file, 0o600)` | `src/specify_cli/auth/secure_storage/file_fallback.py:114` | Safe | POSIX-only intent; `_check_file_permissions` skips on Windows via `if not hasattr(os, "getuid"): return` |
| `os.chmod(tmp, 0o600)` | `file_fallback.py:225` | Safe | `except OSError: log.debug(...)` — best-effort, skips gracefully on Windows |
| `os.chmod(self.path, 0o600)` | `src/specify_cli/tracker/credentials.py:131` | Fixed (WP05) | Inside `if os.name != "nt":` guard |
| `("chmod", ...)` in init.py | `src/specify_cli/cli/commands/init.py:430` | Safe | Step tracker label string, not a subprocess call |
| `os.chmod(script, ...)` | `src/specify_cli/__init__.py:148` | Safe | Inside `if os.name != "nt": return` guard (`ensure_executable_scripts`) |
| `target.chmod(... 0o222)` | `src/specify_cli/upgrade/migrations/m_3_2_2_safe_globalize_commands.py:149` | Safe | Write-permission bit; harmless no-op on NTFS |
| `file_path.chmod(mode & ~0o222)` | `src/specify_cli/skills/installer.py:35` | Safe | Read-only bit; harmless on NTFS |
| All `pre-commit` / `hooks/` / `chmod` in tests, CI yamls, docs | Multiple | Safe | Test fixtures, CI steps, documentation |

### Category 7: Tests (`@pytest.mark.skipif.*win`, `sys.platform` in tests)

Total raw hits: 0 in the pattern `@pytest.mark.skipif.*win`. All new Windows-specific tests use `@pytest.mark.windows_ci` (the marker added by WP07) rather than `skipif`.

**Windows CI test inventory (new in this mission)**:

| Test file | Marker | WP |
|-----------|--------|----|
| `tests/regressions/test_issue_101_utf8_startup.py` | `windows_ci` | WP08 |
| `tests/regressions/test_issue_71_dashboard_empty.py` | `windows_ci` | WP08 |
| `tests/mission/test_active_mission_handle_windows.py` | `windows_ci` | WP07 |
| `tests/audit/test_no_legacy_path_literals.py` | (all platforms) | WP07 |
| `tests/kernel/test_paths_unified_windows_root.py` | `windows_ci` | WP01 |
| `tests/packaging/test_windows_no_keyring.py` | `windows_ci` | WP03 |
| `tests/sync/test_daemon_windows_paths.py` | `windows_ci` | WP05 |
| `tests/paths/test_windows_migrate.py` | (all platforms) | WP02 |
| `tests/paths/test_windows_paths.py` | (all platforms) | WP01 |
| `tests/paths/test_render_runtime_path.py` | (all platforms) | WP01 |
| `tests/cli/test_agent_status_messaging.py` | (all platforms) | WP04 |
| `tests/cli/test_migrate_cmd_messaging.py` | (all platforms) | WP04 |

---

## Follow-up Issues Filed

| Issue | Title | Scope |
|-------|-------|-------|
| [#629](https://github.com/Priivacy-ai/spec-kitty/issues/629) | Add `@pytest.mark.windows_ci` test for `os.symlink` fallback in `m_0_8_0_worktree_agents_symlink` | Add `@pytest.mark.windows_ci` test confirming `OSError` fallback to `shutil.copy2` is exercised on Windows. Risk: symlink silently falls back, AGENTS.md may be a copy instead of a symlink; functional but untested. |
| [#630](https://github.com/Priivacy-ai/spec-kitty/issues/630) | Replace `shell=True` subprocess calls in `review/baseline.py` and `acceptance_matrix.py` for Windows compatibility | Replace with list-form `subprocess.run` or document that these code paths are POSIX-only (require a POSIX shell); add CI guard. Risk: `shell=True` with arbitrary command string invokes `cmd.exe` on Windows, not `sh`. |
| [#631](https://github.com/Priivacy-ai/spec-kitty/issues/631) | Document workaround for MCP agent root confusion with worktrees on Windows (#260) | Document the Serena/OpenCode workaround (configure MCP server to use worktree path as root); evaluate adding a `--in-place` (non-worktree) implementation mode. Not a Spec Kitty code bug. |

---

## Whitelist (for `tests/audit/test_no_legacy_path_literals.py`)

The following occurrences of `~/.kittify` or `~/.spec-kitty` in source files are intentional and safe. They are schema metadata strings (`path_pattern` fields used only for documentation/introspection, never for `Path()` resolution) or module-level docstrings:

- `src/specify_cli/state_contract.py:18` — enum comment `# ~/.kittify/`; not a path operation
- `src/specify_cli/state_contract.py:19` — enum comment `# ~/.spec-kitty/`; not a path operation
- `src/specify_cli/state_contract.py:406–499` — `path_pattern=` strings in `StateSurface` instances; used only in `to_dict()` / JSON export for human reference
- `src/kernel/paths.py:4,25,29,38` — module docstring and function docstring; `get_kittify_home()` itself dispatches Windows to `%LOCALAPPDATA%\spec-kitty\`

---

## Residual Risk

After this mission, the outstanding Windows risks are:

1. **`os.symlink` unguarded** (`m_0_8_0_worktree_agents_symlink.py`): Falls back to copy on `OSError`, which is correct behavior, but the fallback path is not tested on Windows. Risk level: **Low** (behavior is correct; only test coverage is missing).

2. **`shell=True` in baseline/acceptance-matrix** (`review/baseline.py`, `acceptance_matrix.py`): These code paths invoke user-supplied or config-supplied command strings with `shell=True`. On Windows this invokes `cmd.exe` instead of `sh`, which may break commands that use POSIX-style syntax. Risk level: **Medium** (commands may fail on Windows with confusing errors rather than silent data corruption).

3. **`#260` MCP-root incompatibility**: An editor-side concern. Spec Kitty has no control over how a third-party MCP server determines its working directory. Risk level: **Low / External** (documentation fix needed, not a code fix).

All three residuals have follow-up issues filed. No critical (data-corrupting or auth-bypassing) Windows risks remain after WP01–WP08.
