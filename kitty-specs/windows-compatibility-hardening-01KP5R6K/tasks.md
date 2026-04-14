# Tasks: Windows Compatibility Hardening Pass

**Mission**: `windows-compatibility-hardening-01KP5R6K`
**Branch**: planning `main` → merge target `main`
**Feature dir**: `/Users/robert/spec-kitty-dev/windows/spec-kitty/kitty-specs/windows-compatibility-hardening-01KP5R6K`
**Generated**: 2026-04-14

---

## Subtask Index

This index is a reference table (not a tracking surface). Per-WP tracking rows live as checkboxes under each WP section.

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Create `src/specify_cli/paths/__init__.py` package skeleton with public exports | WP01 | | [D] |
| T002 | Implement `RuntimeRoot` dataclass and `get_runtime_root()` in `windows_paths.py` | WP01 | | [D] |
| T003 | Implement `render_runtime_path(path, *, for_user=True)` helper | WP01 | [D] |
| T004 | Unit tests for `RuntimeRoot` + `get_runtime_root` (platform-mocked) | WP01 | [D] |
| T005 | Unit tests for `render_runtime_path` (platform-mocked) | WP01 | [D] |
| T006 | Implement `MigrationOutcome` + `LegacyWindowsRoot` dataclasses in `windows_migrate.py` | WP02 | |
| T007 | Implement `migrate_windows_state(dry_run=False)` with destination-wins + timestamped quarantine | WP02 | |
| T008 | Add `msvcrt.locking`-based contention lock (Windows-only; POSIX is no-op) | WP02 | |
| T009 | Tests: absent noop, move to empty, quarantine on conflict, idempotent second run, dry-run | WP02 | [P] |
| T010 | Concurrency stress test: two subprocesses racing the migration lock | WP02 | [P] |
| T011 | Refactor `SecureStorage.from_environment()` to hard-dispatch on `sys.platform` | WP03 | |
| T012 | Create `WindowsFileStorage` in new `windows_storage.py` pointed at `get_runtime_root().auth_dir` | WP03 | |
| T013 | Replace `_DEFAULT_DIR` module constant with `default_store_dir()` function in `file_fallback.py` | WP03 | |
| T014 | Gate `keychain` import with `TYPE_CHECKING` + `sys.platform` so Windows never imports it at runtime | WP03 | |
| T015 | Update `pyproject.toml`: `keyring>=25; sys_platform != "win32"` + register `windows_ci` pytest marker | WP03 | |
| T016 | Unit test: `from_environment()` under `sys.platform="win32"` → `WindowsFileStorage`; keychain not in `sys.modules` | WP03 | [P] |
| T017 | Windows-native test (`windows_ci`): encrypted file-store round-trip under `%LOCALAPPDATA%\spec-kitty\auth\` | WP03 | [P] |
| T018 | Packaging test (`windows_ci`): `importlib.util.find_spec('keyring')` returns `None` | WP03 | [P] |
| T019 | Replace `~/.kittify` / `~/.spec-kitty` literals in `migrate_cmd.py` with `render_runtime_path(...)` | WP04 | |
| T020 | Replace legacy path literals in `agent/status.py` with `render_runtime_path(...)` | WP04 | [P] |
| T021 | Wire `migrate_cmd.py` to invoke `migrate_windows_state()` on Windows; emit single-summary message | WP04 | |
| T022 | Windows-native test: `spec-kitty agent status` output contains no `~/.kittify` / `~/.spec-kitty` substring | WP04 | [P] |
| T023 | Windows-native tests: `migrate_cmd` happy-path + conflict-path emit contracted messages with real `C:\` paths | WP04 | [P] |
| T024 | Static audit test: grep over `src/specify_cli/cli/` for legacy path literals returns zero hits (whitelist in audit report) | WP04 | [P] |
| T025 | Refactor `tracker/credentials.py` to consume `get_runtime_root().tracker_dir` on Windows; POSIX path unchanged | WP05 | [P] |
| T026 | Refactor `sync/daemon.py` to consume `get_runtime_root().sync_dir` / `daemon_dir` on Windows; POSIX unchanged | WP05 | [P] |
| T027 | Refactor `src/kernel/paths.py` so Windows callers resolve via `get_runtime_root().base` | WP05 | [P] |
| T028 | Windows-native test for `tracker/credentials.py` path resolution | WP05 | [P] |
| T029 | Windows-native test for `sync/daemon.py` path resolution | WP05 | [P] |
| T030 | Windows-native cross-module test: auth, tracker, sync, daemon, kernel.paths all resolve under the same `RuntimeRoot.base` | WP05 | |
| T031 | Refactor `hook_installer.install()` to capture `Path(sys.executable).resolve()` at install time | WP06 | |
| T032 | Rewrite hook template: `#!/bin/sh` + single quoted `exec "<abs_interpreter>" -m specify_cli.policy.commit_guard_hook "$@"` | WP06 | |
| T033 | Implement atomic install via temp-file-then-rename; ensure mode `0o755` post-write | WP06 | |
| T034 | Return `HookInstallRecord` from installer (per data-model E-05) for testability | WP06 | [P] |
| T035 | Rendering tests: shebang, single quoted interpreter line, mode `0o755` | WP06 | [P] |
| T036 | Execution test (`windows_ci`): hook runs successfully on Git for Windows; exit code propagates | WP06 | [P] |
| T037 | Execution test (`windows_ci`): hook executes when interpreter path contains a space | WP06 | [P] |
| T038 | Regression test (`windows_ci`) for issue #105: PATH stripped of `python`/`python3`/`py` → hook still executes | WP06 | [P] |
| T039 | POSIX execution smoke test: hook still works on Linux runner (cross-platform parity) | WP06 | [P] |
| T040 | Create `.github/workflows/ci-windows.yml`: `windows-latest`, Python 3.11, pipx install, `PYTHONUTF8=1`, `pytest -m windows_ci --maxfail=1` | WP07 | |
| T041 | Add "keyring NOT installed" assertion step to the Windows workflow (packaging enforcement of C-001) | WP07 | [P] |
| T042 | Update `ci-quality.yml` (Linux) to run `pytest -m "not windows_ci"` | WP07 | [P] |
| T043 | Set workflow `timeout-minutes: 20` and `--maxfail=1` for fast feedback | WP07 | [P] |
| T044 | Document branch-protection required-check update in the WP PR description (for maintainer to apply post-merge) | WP07 | [P] |
| T045 | Smoke-test workflow: verify it executes the curated suite end-to-end on a scratch push | WP07 | |
| T046 | Add UTF-8 enforcement at CLI entrypoint: new `src/specify_cli/encoding.py` + call at startup in `src/specify_cli/cli/__init__.py` | WP08 | |
| T047 | Windows-native regression test for issue #101: non-UTF-8 codepage; CLI startup + status rendering non-ASCII paths | WP08 | [P] |
| T048 | Windows-native regression test for issue #71: dashboard path returns non-empty response on Windows | WP08 | [P] |
| T049 | Upgrade `tests/sync/test_issue_586_windows_import.py` from simulated to native (add `windows_ci` marker) | WP08 | [P] |
| T050 | Windows-native test: worktree symlink-vs-copy fallback — `.kittify/memory` + `AGENTS.md` readable; path-with-spaces covered | WP08 | [P] |
| T051 | Windows-native test: active-mission handle round-trip without symlink support | WP08 | [P] |
| T052 | Run repo-wide grep audit per FR-018 pattern list; capture all findings | WP09 | |
| T053 | Classify each finding: fixed / covered-by-CI / follow-up-issue | WP09 | |
| T054 | Write `architecture/2026-04-14-windows-compatibility-hardening.md` audit report with full classification table | WP09 | |
| T055 | Write ADR `architecture/adrs/2026-04-14-1-windows-auth-platform-split.md` | WP09 | [P] |
| T056 | Write ADR `architecture/adrs/2026-04-14-2-windows-runtime-state-unification.md` | WP09 | [P] |
| T057 | Write `docs/explanation/windows-state.md` — canonical Windows layout + migration documentation | WP09 | [P] |
| T058 | Update `CLAUDE.md` with Windows state-layout section (FR-019) | WP09 | [P] |
| T059 | File GitHub follow-up issues for residuals with `windows` label; link from audit report | WP09 | [P] |
| T060 | Verify #603 closeable; verify #260 either closeable or has scoped follow-up issue | WP09 | [P] |

---

## Execution order summary

- **Start in parallel**: WP01, WP06
- **After WP01**: WP02, WP03, WP05 start in parallel
- **After WP01 + WP02**: WP04 starts
- **After WP03**: WP07 starts
- **After WP07**: WP08 starts
- **Finalizer (after all prior WPs)**: WP09

---

## Work Packages

### WP01 — Windows paths subpackage + render helper

**Prompt file**: [`tasks/WP01-windows-paths-subpackage.md`](./tasks/WP01-windows-paths-subpackage.md)

**Goal**: Create a new `src/specify_cli/paths/` subpackage that exposes the canonical `RuntimeRoot` resolution and the `render_runtime_path` helper used by every downstream consumer in this mission.

**Priority**: P0 (foundational). Unblocks WP02, WP03, WP04, WP05.

**Independent test**: Unit tests for `get_runtime_root` and `render_runtime_path` pass on POSIX (platform-mocked). Real Windows execution happens in downstream WPs.

**Estimated prompt size**: ~350 lines (5 subtasks × ~70 lines)

**Dependencies**: none

**Risks**:
- `platformdirs` API version drift — pin explicit version in `pyproject.toml` if not already pinned.
- Imports from this package must not cycle with the auth subsystem (keep `windows_paths` standalone).

**Included subtasks**:
- [x] T001 Create `src/specify_cli/paths/__init__.py` package skeleton with public exports
- [x] T002 Implement `RuntimeRoot` dataclass and `get_runtime_root()` in `windows_paths.py`
- [x] T003 Implement `render_runtime_path(path, *, for_user=True)` helper
- [x] T004 Unit tests for `RuntimeRoot` + `get_runtime_root` (platform-mocked)
- [x] T005 Unit tests for `render_runtime_path` (platform-mocked)

---

### WP02 — Windows runtime state migration module

**Prompt file**: [`tasks/WP02-windows-state-migration.md`](./tasks/WP02-windows-state-migration.md)

**Goal**: Implement `src/specify_cli/paths/windows_migrate.py` — a one-time, idempotent, destination-wins migration of legacy Windows state (`~/.spec-kitty`, `~/.kittify`, `~/.config/spec-kitty`) to `%LOCALAPPDATA%\spec-kitty\`, with timestamped quarantine on destination conflict and `msvcrt.locking`-based contention safety.

**Priority**: P0 (foundational for CLI wiring in WP04 and downstream consumers).

**Independent test**: Unit + integration tests for absent/moved/quarantined/idempotent/dry-run outcomes pass on POSIX (mocked `sys.platform`); native Windows coverage runs in WP07 CI.

**Estimated prompt size**: ~400 lines (5 subtasks × ~80 lines)

**Dependencies**: WP01

**Risks**:
- `msvcrt.locking` doesn't exist on POSIX — module must conditionally import and no-op on non-Windows.
- Cross-volume `os.replace` raises `EXDEV`; fallback must never delete source.
- Quarantine name collisions within a single second — resolve via `_N` suffix.

**Included subtasks**:
- [ ] T006 Implement `MigrationOutcome` + `LegacyWindowsRoot` dataclasses in `windows_migrate.py`
- [ ] T007 Implement `migrate_windows_state(dry_run=False)` with destination-wins + timestamped quarantine
- [ ] T008 Add `msvcrt.locking`-based contention lock (Windows-only; POSIX is no-op)
- [ ] T009 Tests: absent noop, move to empty, quarantine on conflict, idempotent second run, dry-run
- [ ] T010 Concurrency stress test: two subprocesses racing the migration lock

---

### WP03 — Auth hard platform split + `pyproject.toml` markers

**Prompt file**: [`tasks/WP03-auth-hard-platform-split.md`](./tasks/WP03-auth-hard-platform-split.md)

**Goal**: Implement the hard platform split in `SecureStorage.from_environment()` so Windows never imports `keychain.py`. Narrow `keyring` to a non-Windows conditional dependency. Register the `windows_ci` pytest marker.

**Priority**: P0 (unblocks WP07 CI and closes #603).

**Independent test**: Unit test with mocked `sys.platform="win32"` verifies `WindowsFileStorage` is returned AND `specify_cli.auth.secure_storage.keychain` is not in `sys.modules`. Windows-native tests in CI verify encrypted round-trip and keyring-absence.

**Estimated prompt size**: ~550 lines (8 subtasks × ~70 lines)

**Dependencies**: WP01

**Risks**:
- `mypy --strict` must still type-check `keychain.py` on all platforms — use `TYPE_CHECKING` guarded imports.
- Existing tests may assert keychain-first fallback behavior on macOS/Linux — verify no behavioral change on non-Windows.
- `pyproject.toml` edits must preserve the existing dep table shape; use PEP 508 markers.

**Included subtasks**:
- [ ] T011 Refactor `SecureStorage.from_environment()` to hard-dispatch on `sys.platform`
- [ ] T012 Create `WindowsFileStorage` in new `windows_storage.py` pointed at `get_runtime_root().auth_dir`
- [ ] T013 Replace `_DEFAULT_DIR` module constant with `default_store_dir()` function in `file_fallback.py`
- [ ] T014 Gate `keychain` import with `TYPE_CHECKING` + `sys.platform` so Windows never imports it at runtime
- [ ] T015 Update `pyproject.toml`: `keyring` conditional + register `windows_ci` pytest marker
- [ ] T016 Unit test: `from_environment()` under `sys.platform="win32"` → `WindowsFileStorage`; keychain not in `sys.modules`
- [ ] T017 Windows-native test (`windows_ci`): encrypted file-store round-trip under `%LOCALAPPDATA%\spec-kitty\auth\`
- [ ] T018 Packaging test (`windows_ci`): `importlib.util.find_spec('keyring')` returns `None`

---

### WP04 — Path messaging sweep + `migrate_cmd` wiring

**Prompt file**: [`tasks/WP04-path-messaging-and-migrate-wiring.md`](./tasks/WP04-path-messaging-and-migrate-wiring.md)

**Goal**: Replace every `~/.kittify` / `~/.spec-kitty` literal in CLI user-facing output with `render_runtime_path(...)`. Wire `migrate_cmd.py` to invoke `migrate_windows_state()` on Windows and emit the contracted single-summary message. Add a static audit test asserting no legacy literals remain in touched files.

**Priority**: P1 (user-facing correctness; SC-002).

**Independent test**: Windows-native tests assert CLI output contains real `C:\` paths and no legacy literals; static audit test blocks regressions.

**Estimated prompt size**: ~400 lines (6 subtasks × ~70 lines)

**Dependencies**: WP01, WP02

**Risks**:
- Missed call-sites — compensated by the static audit test (T024) and by the repo-wide audit in WP09.
- `migrate_cmd.py` may already have complex logic — do not regress non-Windows migration paths.

**Included subtasks**:
- [ ] T019 Replace `~/.kittify` / `~/.spec-kitty` literals in `migrate_cmd.py` with `render_runtime_path(...)`
- [ ] T020 Replace legacy path literals in `agent/status.py` with `render_runtime_path(...)`
- [ ] T021 Wire `migrate_cmd.py` to invoke `migrate_windows_state()` on Windows; emit single-summary message
- [ ] T022 Windows-native test: `spec-kitty agent status` output contains no `~/.kittify` / `~/.spec-kitty` substring
- [ ] T023 Windows-native tests: `migrate_cmd` happy-path + conflict-path emit contracted messages with real `C:\` paths
- [ ] T024 Static audit test: grep over `src/specify_cli/cli/` for legacy path literals returns zero hits

---

### WP05 — Tracker / sync / daemon / `kernel.paths` re-rooting

**Prompt file**: [`tasks/WP05-runtime-consumers-re-rooting.md`](./tasks/WP05-runtime-consumers-re-rooting.md)

**Goal**: Point every Windows-state consumer at the unified `RuntimeRoot`: tracker credentials, sync/daemon files, and `kernel.paths`. Preserve POSIX behavior exactly. Add cross-module consistency test.

**Priority**: P1 (enables the single-root property asserted by C-002 / FR-005).

**Independent test**: Per-module Windows tests verify each consumer resolves under `%LOCALAPPDATA%\spec-kitty\...`. Cross-module test verifies they all share the same `RuntimeRoot.base`.

**Estimated prompt size**: ~400 lines (6 subtasks × ~65 lines)

**Dependencies**: WP01

**Risks**:
- `kernel.paths` may already have platformdirs-based logic that disagrees with the unified root — verify alignment rather than duplicate logic.
- Tracker SQLite files on Windows may have open handles — migration of live DB files is out of scope here (migration happens in WP02 before consumers read).

**Included subtasks**:
- [ ] T025 Refactor `tracker/credentials.py` to consume `get_runtime_root().tracker_dir` on Windows; POSIX unchanged
- [ ] T026 Refactor `sync/daemon.py` to consume `get_runtime_root().sync_dir` / `daemon_dir` on Windows; POSIX unchanged
- [ ] T027 Refactor `src/kernel/paths.py` so Windows callers resolve via `get_runtime_root().base`
- [ ] T028 Windows-native test for `tracker/credentials.py` path resolution
- [ ] T029 Windows-native test for `sync/daemon.py` path resolution
- [ ] T030 Windows-native cross-module test: auth, tracker, sync, daemon, kernel.paths all resolve under the same `RuntimeRoot.base`

---

### WP06 — Pre-commit hook installer hardening

**Prompt file**: [`tasks/WP06-hook-installer-hardening.md`](./tasks/WP06-hook-installer-hardening.md)

**Goal**: Rewrite the pre-commit hook generator to pin the absolute Python interpreter at install time. Validate actual executable behavior — on Windows (Git for Windows `sh.exe`) and POSIX, including paths with spaces and with `python`/`python3`/`py` stripped from PATH (issue #105 reproduction).

**Priority**: P0 (parallelizable with other lanes; closes a historical regression class).

**Independent test**: Hook rendering tests + executable-run tests pass on both POSIX and `windows-latest`.

**Estimated prompt size**: ~600 lines (9 subtasks × ~65 lines)

**Dependencies**: none

**Risks**:
- Git for Windows' MSYS `sh.exe` mangles drive-letter arguments in some contexts — verify via execution test, not source inspection.
- Interpreter path with spaces (`C:\Program Files\Python311\python.exe`) is a well-known failure mode — single quoting discipline matters.
- `0o755` is a no-op on NTFS but required for POSIX; do not conditionalize.

**Included subtasks**:
- [ ] T031 Refactor `hook_installer.install()` to capture `Path(sys.executable).resolve()` at install time
- [ ] T032 Rewrite hook template: `#!/bin/sh` + single quoted `exec "<abs_interpreter>" -m ... "$@"`
- [ ] T033 Implement atomic install via temp-file-then-rename; ensure mode `0o755` post-write
- [ ] T034 Return `HookInstallRecord` from installer (per data-model E-05) for testability
- [ ] T035 Rendering tests: shebang, single quoted interpreter line, mode `0o755`
- [ ] T036 Execution test (`windows_ci`): hook runs on Git for Windows; exit code propagates
- [ ] T037 Execution test (`windows_ci`): hook executes when interpreter path contains a space
- [ ] T038 Regression test (`windows_ci`) for #105: PATH stripped of `python`/`python3`/`py` → hook still executes
- [ ] T039 POSIX execution smoke test: hook still works on Linux runner

---

### WP07 — Native Windows CI workflow

**Prompt file**: [`tasks/WP07-native-windows-ci-workflow.md`](./tasks/WP07-native-windows-ci-workflow.md)

**Goal**: Create `.github/workflows/ci-windows.yml` as a blocking PR status check running `pytest -m windows_ci` on `windows-latest` with `PYTHONUTF8=1` and a pipx install topology. Update `ci-quality.yml` to exclude `windows_ci` markers. Document branch-protection update for maintainer application.

**Priority**: P0 (required for all other lanes' Windows assertions to have teeth).

**Independent test**: Workflow runs on scratch push and executes the curated suite end-to-end; smoke test green.

**Estimated prompt size**: ~350 lines (6 subtasks × ~60 lines)

**Dependencies**: WP03 (for registered `windows_ci` marker).

**Risks**:
- `pipx install --editable` on Windows requires `venv` available; `setup-python@v5` provides it.
- GitHub-hosted `windows-latest` shell is PowerShell by default; multi-line `run` blocks need `shell: bash` if bash-specific.
- `ci-quality.yml` edit must not disable any existing PR-required test; only add the `-m "not windows_ci"` marker selection.

**Included subtasks**:
- [ ] T040 Create `.github/workflows/ci-windows.yml` with `windows-latest`, Python 3.11, pipx, `PYTHONUTF8=1`, `pytest -m windows_ci --maxfail=1`
- [ ] T041 Add "keyring NOT installed" assertion step to the Windows workflow
- [ ] T042 Update `ci-quality.yml` (Linux) to run `pytest -m "not windows_ci"`
- [ ] T043 Set workflow `timeout-minutes: 20` and `--maxfail=1` for fast feedback
- [ ] T044 Document branch-protection required-check update in PR description for maintainer
- [ ] T045 Smoke-test workflow: verify end-to-end execution on a scratch push

---

### WP08 — Encoding + worktree + mission revalidation

**Prompt file**: [`tasks/WP08-encoding-worktree-mission-tests.md`](./tasks/WP08-encoding-worktree-mission-tests.md)

**Goal**: Enforce UTF-8 at the CLI entrypoint on Windows (regression coverage for #101). Upgrade the simulated `fcntl`-import test (#586) to native execution. Add native Windows tests for worktree symlink-vs-copy fallback and active-mission handle round-trip (closes #260-adjacent risk). Add native regression test for #71.

**Priority**: P1 (closes the historical regression tail).

**Independent test**: All listed regression + integration tests pass on `windows-latest` under `windows_ci`.

**Estimated prompt size**: ~420 lines (6 subtasks × ~70 lines)

**Dependencies**: WP07

**Risks**:
- `sys.stdout.reconfigure` may already be called elsewhere — avoid double-call; idempotent implementation.
- Windows Developer Mode (required for symlinks) is NOT assumed on runners; tests must exercise the copy fallback path.
- Active-mission handle fallback semantics must match `mission.py`'s current Windows branch — do not add a new branch.

**Included subtasks**:
- [ ] T046 Add UTF-8 enforcement at CLI entrypoint: new `src/specify_cli/encoding.py` + call in `src/specify_cli/cli/__init__.py`
- [ ] T047 Windows-native regression test for #101: non-UTF-8 codepage; CLI startup + status rendering non-ASCII paths
- [ ] T048 Windows-native regression test for #71: dashboard path returns non-empty response
- [ ] T049 Upgrade `tests/sync/test_issue_586_windows_import.py` from simulated to native (add `windows_ci` marker)
- [ ] T050 Windows-native test: worktree symlink-vs-copy fallback — `.kittify/memory` + `AGENTS.md` readable
- [ ] T051 Windows-native test: active-mission handle round-trip without symlink support

---

### WP09 — Audit report + ADRs + docs + follow-ups

**Prompt file**: [`tasks/WP09-audit-report-and-docs.md`](./tasks/WP09-audit-report-and-docs.md)

**Goal**: Run the second-pass repo-wide Windows audit per FR-018. Commit the audit report (`architecture/2026-04-14-windows-compatibility-hardening.md`) with a classification table for every finding. Commit two ADRs documenting the auth split and storage unification. Write `docs/explanation/windows-state.md`. Update `CLAUDE.md` with Windows state layout. File GitHub follow-up issues for any residuals. Verify close-out posture for #603 and #260.

**Priority**: P2 (finalizer; depends on all prior lanes landing).

**Independent test**: Audit report file exists, contains all classified findings, and links to filed follow-up issues (if any); ADRs are valid Markdown and follow the existing ADR format under `architecture/adrs/`.

**Estimated prompt size**: ~600 lines (9 subtasks × ~65 lines)

**Dependencies**: WP01, WP02, WP03, WP04, WP05, WP06, WP07, WP08

**Risks**:
- Grep audit may surface residuals that require a code change at the finalizer stage — file each as a follow-up with `windows` label rather than slipping scope.
- `CLAUDE.md` is a high-traffic file — land this WP cleanly on top of `main` with no conflicts.
- Issue close-out for #603 / #260 requires GitHub permissions — if unavailable, document the closeable-posture in the audit report and open a comment requesting closure.

**Included subtasks**:
- [ ] T052 Run repo-wide grep audit per FR-018 pattern list; capture all findings
- [ ] T053 Classify each finding: fixed / covered-by-CI / follow-up-issue
- [ ] T054 Write `architecture/2026-04-14-windows-compatibility-hardening.md` audit report
- [ ] T055 Write ADR `architecture/adrs/2026-04-14-1-windows-auth-platform-split.md`
- [ ] T056 Write ADR `architecture/adrs/2026-04-14-2-windows-runtime-state-unification.md`
- [ ] T057 Write `docs/explanation/windows-state.md` — canonical Windows layout + migration doc
- [ ] T058 Update `CLAUDE.md` with Windows state-layout section
- [ ] T059 File GitHub follow-up issues for residuals with `windows` label; link from audit report
- [ ] T060 Verify #603 closeable; verify #260 either closeable or has scoped follow-up

---

## Parallelization highlights

- Immediately after starting: **WP01** and **WP06** run in parallel.
- Once WP01 lands: **WP02, WP03, WP05** run in parallel (all depend only on WP01).
- Once WP02 lands: **WP04** starts.
- Once WP03 lands: **WP07** starts.
- Once WP07 lands: **WP08** starts.
- **WP09** runs last and depends on all prior WPs.

## MVP scope

The hardening pass is not a progressive-value feature — it's a coherent unit. If an MVP slice is ever needed for a partial release, **WP01 + WP03 + WP07** together constitute the Credential Manager closure (closes #603, demonstrates Windows file-backed auth on CI). WP02/WP04 ship the migration UX. WP05–WP09 complete the coherence and audit story.

---

## Implementation handoff

Run finalize:
```bash
spec-kitty agent mission finalize-tasks --mission windows-compatibility-hardening-01KP5R6K --json
```

Then start the agent loop:
```bash
spec-kitty next --agent claude --mission 01KP5R6K
```

Branch contract reminder: planning `main` → merge target `main`. Every execution worktree is created per-lane under `.worktrees/windows-compatibility-hardening-01KP5R6K-lane-<id>/`.
