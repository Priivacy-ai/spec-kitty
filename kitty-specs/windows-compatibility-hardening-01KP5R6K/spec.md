# Mission Specification: Windows Compatibility Hardening Pass

**Mission ID**: `01KP5R6KRZDXV1BKM3Q1FZMY77`
**Mission slug**: `windows-compatibility-hardening-01KP5R6K`
**Mission type**: software-dev
**Target branch**: `main`
**Status**: Draft
**Created**: 2026-04-14

---

## Overview

Spec Kitty has shipped a repeating tail of Windows regressions (examples: `fcntl` import crash #586, `python3` assumption in pre-commit hook #105, UTF-8 startup crash #101, empty dashboard response #71) and still carries open structural Windows issues (Credential Manager dependency #603, worktree subdirectory incompatibility #260). A prior audit at commit `51c7cd0b` against a fresh clone at `/tmp/spec-kitty-scan-20260414-120646` confirmed that the Windows behavior, storage paths, hook installer, CI coverage, and user-facing messaging are still inconsistent on Windows.

This mission is a hardening pass, not a greenfield port. Its purpose is to give Spec Kitty one intentional, coherent, tested Windows story across the historically fragile surfaces, close the relevant open issues, and make sure future Windows regressions are caught by CI instead of by users.

## Goals

- Make Windows auth storage intentional and Windows-native, with the Credential Manager dependency removed (addresses #603).
- Unify Windows runtime state (auth, tracker, sync, daemon, runtime cache) under a single Windows-native root.
- Make the generated git pre-commit hook robust on Windows without assuming POSIX shell semantics or a bare `python`/`python3` binary.
- Make user-facing path messaging (help text, status output, migration messages, docs) accurate for Windows.
- Revalidate worktree and symlink fallback behavior end to end on Windows rather than by source inspection alone.
- Add a native `windows-latest` CI job that would have caught the historically-shipped regressions.
- Run a second-pass repo-wide scan for residual Unix-only assumptions and fix or file follow-ups for each.

## Non-Goals

- Running the entire pytest suite on Windows CI as a blocking gate.
- Introducing an opt-in or configurable Credential Manager secret-store path on Windows.
- Maintaining multiple long-term Windows runtime state roots as an intentional steady state.
- Changing non-Windows platform behavior except as a direct consequence of required refactors.
- Rewriting the auth subsystem, tracker, sync, or daemon beyond what is needed to land the Windows story.

## User Scenarios & Testing

### Primary user: Windows developer installing and using Spec Kitty

1. A developer on Windows installs `spec-kitty-cli` (via `pipx` or equivalent).
2. They run `spec-kitty --version` and a routine command (for example `spec-kitty agent tasks status`) in a fresh terminal. The CLI starts without `ModuleNotFoundError`, without an encoding crash, without prompting for a keyring backend, and without referencing Unix-only paths in its messaging.
3. They authenticate against the SaaS surface. Credentials are written to a documented Windows-native location under `%LOCALAPPDATA%\spec-kitty\auth\`. No Credential Manager prompt is shown. No keyring dependency is required.
4. They initialize or open a project. Tracker credentials, sync state, and daemon files land under `%LOCALAPPDATA%\spec-kitty\`. Any legacy state under `~/.spec-kitty` or `~/.kittify` is migrated once, idempotently, with clear messaging.
5. They run `spec-kitty implement WP##`. Worktree creation succeeds. Files that are symlinks on POSIX (`.kittify/memory`, `AGENTS.md`, active mission handle) are materialized via the documented Windows fallback without breaking downstream commands.
6. They commit. The installed pre-commit hook runs the commit guard successfully without requiring a `python` or `python3` binary on PATH and without relying on POSIX shell semantics.
7. Every piece of user-facing output they see referencing Spec Kitty state paths shows the real Windows path (e.g. `%LOCALAPPDATA%\spec-kitty\...`), not `~/.spec-kitty` or `~/.kittify`.

### Secondary user: Existing Windows user on a prior install

1. The user upgrades. On first run, migration detects legacy locations (`~/.spec-kitty`, `~/.kittify`, legacy auth fallback directories under `~/.config/spec-kitty`) and moves relevant state to `%LOCALAPPDATA%\spec-kitty\`.
2. Migration is idempotent: a second run is a no-op.
3. If migration is skipped or fails, the CLI gives clear guidance and does not silently fall back to writing state into the legacy location.

### Secondary user: Spec Kitty maintainer reviewing a pull request

1. Any pull request touching the historically fragile surfaces (auth storage, tracker/sync/daemon, worktree, hook installer, path helpers, encoding, file locking) runs a blocking `windows-latest` CI job.
2. A PR that reintroduces any of the Windows regressions tracked in this mission (`fcntl` import, `python3` assumption, Unix-only fallback directory, `~/.kittify` messaging, etc.) turns the Windows job red before merge.
3. Every confirmed bug fixed in this mission has at least one test that runs on the native Windows job.

### Acceptance scenarios

- AS-01: `python -c "import specify_cli"` succeeds on `windows-latest` with the default PATH for the install method (pipx or uv).
- AS-02: A fresh `spec-kitty` auth login on Windows writes credentials to `%LOCALAPPDATA%\spec-kitty\auth\` and succeeds without any Credential Manager prompt or keyring package installed.
- AS-03: After upgrade, legacy state in `~/.spec-kitty` on Windows is moved to `%LOCALAPPDATA%\spec-kitty\` on first run, with a user-visible migration message, and does not re-trigger on second run.
- AS-04: `spec-kitty` installs a pre-commit hook that executes successfully on Git for Windows and on a virtualenv install without a `python` or `python3` symlink on PATH.
- AS-05: `spec-kitty agent status` and `spec-kitty migrate ...` help/output on Windows display `%LOCALAPPDATA%\spec-kitty\...` style paths, never `~/.kittify` or `~/.spec-kitty`.
- AS-06: `spec-kitty implement WP##` succeeds in a worktree on Windows where symlinks are not permitted; dependent commands can read the materialized `.kittify/memory` and `AGENTS.md` content.
- AS-07: The blocking Windows CI job fails if any of the regression tests for #586, #105, #101, or #71 regresses.
- AS-08: After this mission merges, `rg -n "~/.kittify|~/\.spec-kitty" src/` returns no match in user-facing output or help text producing code paths.

### Edge cases

- EC-01: Windows user has `%LOCALAPPDATA%` redirected or unset. The CLI must resolve via platformdirs and fail with a clear, actionable error rather than silently writing to the home directory.
- EC-02: Windows user has an existing encrypted auth file in the old Unix-style `~/.config/spec-kitty` location. Migration must detect and move it without losing the encryption key association.
- EC-03: Windows user is on a filesystem where `chmod +x` is a no-op (NTFS). The hook installer must produce a hook that Git for Windows will invoke correctly regardless.
- EC-04: Windows user runs Spec Kitty inside WSL. WSL is treated as Linux, not Windows, and must continue to use the Linux storage layout.
- EC-05: Two concurrent CLI invocations attempt to migrate legacy state at the same time. Migration must be safe under contention (lock or atomic rename) and not corrupt state.
- EC-06: Windows runner has a non-UTF-8 default code page. CLI startup and output must not crash on Unicode path rendering (regression coverage for #101).
- EC-07: A worktree is created in a path that contains spaces, non-ASCII characters, or a long (>260 char) Windows path. Downstream command invocations must still work.
- EC-08: The curated Windows CI suite flakes on one test. The job design must make the failing test visible rather than being masked by retry or an unrelated unit.

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | On Windows, the auth subsystem MUST use the encrypted file-backed store at `%LOCALAPPDATA%\spec-kitty\auth\` (resolved via platformdirs) as the sole production storage path, with no Credential Manager / `keyring` dependency in the Windows code path. | Draft |
| FR-002 | The auth storage selector (`SecureStorage.from_environment()` or its replacement) MUST make platform-specific choices explicitly, with Windows selecting the file-backed store directly rather than falling back from a failed keychain attempt. | Draft |
| FR-003 | On Windows, tracker credentials and state that currently live under `Path.home() / ".spec-kitty"` MUST move to `%LOCALAPPDATA%\spec-kitty\`. | Draft |
| FR-004 | On Windows, sync and daemon state that currently lives under `Path.home() / ".spec-kitty"` MUST move to `%LOCALAPPDATA%\spec-kitty\`. | Draft |
| FR-005 | On Windows, `kernel/paths.py` and the unified storage root MUST agree on a single `%LOCALAPPDATA%\spec-kitty\` root used for auth, tracker, sync, daemon, and runtime cache. | Draft |
| FR-006 | The CLI MUST provide a one-time, idempotent migration that detects Windows legacy locations (`~/.spec-kitty`, `~/.kittify`, `~/.config/spec-kitty` for auth fallback) and moves relevant state to `%LOCALAPPDATA%\spec-kitty\`. | Draft |
| FR-007 | Migration MUST be safe under concurrent CLI invocation (either lock-protected or implemented via atomic rename semantics that tolerate contention). | Draft |
| FR-008 | If migration cannot complete (for example, permission denied, destination exists with conflicting content), the CLI MUST surface a clear, actionable error and MUST NOT silently continue writing to the legacy location. | Draft |
| FR-009 | The generated git pre-commit hook MUST invoke the exact Python interpreter that installed it (by absolute path captured from `sys.executable` at install time, or via a platform-appropriate shim), rather than assuming `python` or `python3` on PATH. | Draft |
| FR-010 | The generated pre-commit hook MUST execute successfully on Git for Windows in at least the pipx-installed and uv-installed cases, and on POSIX shells where Git delegates hook execution. | Draft |
| FR-011 | Pre-commit hook tests MUST validate executable behavior (that the hook actually runs and invokes the commit guard), not just that the file was written. | Draft |
| FR-012 | All user-facing output that names Spec Kitty runtime state paths MUST render the correct platform-native path (e.g. `%LOCALAPPDATA%\spec-kitty\...` on Windows) and MUST NOT hardcode `~/.kittify` or `~/.spec-kitty` on Windows. | Draft |
| FR-013 | The CLI MUST replace stale `~/.kittify` references in `migrate_cmd.py` and `agent/status.py` (and any other locations found in the repo-wide audit) with platform-aware path rendering. | Draft |
| FR-014 | On Windows, worktree creation MUST handle symlink-equivalent artifacts (`.kittify/memory`, `AGENTS.md`, active mission handle) via the documented copy or junction fallback, and downstream commands MUST read the materialized content correctly. | Draft |
| FR-015 | The repository MUST include a `windows-latest` GitHub Actions job that is blocking on pull requests and runs the curated Windows-critical test suite. | Draft |
| FR-016 | The curated Windows-critical suite MUST cover, at minimum: CLI import/startup, auth storage (file-backed), tracker/sync/daemon critical paths, worktree creation and symlink-vs-copy behavior, pre-commit hook installation and actual execution, path helpers, UTF-8 / encoding-sensitive flows, file locking / `msvcrt`-vs-`fcntl` branches, and regression tests for #586, #105, #101, and #71. | Draft |
| FR-017 | Every confirmed Windows bug fixed in this mission MUST ship with at least one test that executes on the native Windows CI job and that fails against the pre-fix code. | Draft |
| FR-018 | A second-pass repo-wide audit MUST be executed searching for: `windows`, `win32`, `powershell`, `credential manager`, `python3`, bare `python` invocation, `fcntl`, encoding/UTF-8 assumptions, `symlink`, `junction`, `worktree`, `localappdata`, `appdata`, `pre-commit`, `hook`, `chmod`, `msvcrt`; each finding MUST be either fixed, covered by new CI, or filed as a follow-up issue with a clear Windows label. | Draft |
| FR-019 | Docs (including `CLAUDE.md` references, CLI help, `docs/` pages describing state locations and auth) MUST be updated so the Windows path story is explicit and consistent with the implemented behavior. | Draft |

### Non-Functional Requirements

| ID | Requirement | Measurable Threshold | Status |
|---|---|---|---|
| NFR-001 | Windows CLI cold-start latency MUST NOT regress materially due to this mission's changes. | Median cold-start time on `windows-latest` for `spec-kitty --version` increases by no more than 150 ms vs. the pre-mission baseline measured on the same runner. | Draft |
| NFR-002 | The curated Windows CI job MUST provide timely feedback on pull requests. | Curated Windows job p95 wall-clock time on `windows-latest` is ≤ 15 minutes end-to-end. | Draft |
| NFR-003 | The one-time Windows migration MUST be safe and bounded. | Migration of a state tree with ≤ 100 files and ≤ 50 MB total size completes in ≤ 5 seconds on a normal `windows-latest` runner, and is idempotent (second invocation is a no-op). | Draft |
| NFR-004 | Windows auth storage MUST be robust under concurrent access from at least two processes (CLI + daemon). | Concurrent read/write stress test covering ≥ 100 alternating reads and writes across 2 processes produces zero data corruption and zero lost writes on `windows-latest`. | Draft |
| NFR-005 | User-visible error messages for Windows-specific failures (missing `%LOCALAPPDATA%`, migration conflict, hook install failure) MUST be actionable. | Each Windows-specific error path has a message that names the affected path or resource, explains what went wrong, and tells the user what to do next. Verified by test assertions. | Draft |
| NFR-006 | The curated Windows CI job MUST be green on `main` after this mission lands. | 10 consecutive scheduled or post-merge runs on `main` are green, with zero intermittent failures attributed to mission-introduced tests. | Draft |

### Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | No Credential Manager / `keyring` dependency on the Windows auth code path, including transitive imports under the Windows branch. | Draft |
| C-002 | No new cross-platform abstraction that introduces a long-term dual Windows storage root. On Windows, `%LOCALAPPDATA%\spec-kitty\` is the single root for auth, tracker, sync, daemon, and runtime cache. | Draft |
| C-003 | The generated pre-commit hook must not assume `python` or `python3` exist on PATH, and must not rely on POSIX shell semantics unavailable in Git for Windows' bundled shell. | Draft |
| C-004 | The Windows CI job added in this mission is blocking on pull requests, not nightly-only. | Draft |
| C-005 | WSL is treated as Linux for storage layout decisions; WSL behavior must not change as a side effect of this mission. | Draft |
| C-006 | This mission must not introduce backwards-compatibility fallbacks that keep writing to legacy Windows locations after migration. Migration is one-directional. | Draft |
| C-007 | Every behavioral fix must ship with a native Windows test; documentation-only mitigations are not acceptable for items listed in FR-001 through FR-018. | Draft |

## Success Criteria

- SC-001: On a clean `windows-latest` runner, installing Spec Kitty and running the primary user scenario (install → version check → auth → worktree command → commit) completes end-to-end with no manual intervention.
- SC-002: Windows users see 0 references to `~/.kittify` or `~/.spec-kitty` in CLI output, help text, status messages, or migration messages.
- SC-003: The blocking `windows-latest` CI job fails against the pre-fix version of the codebase for at least one of the historical regressions tracked in this mission, and passes against the post-fix version.
- SC-004: Every confirmed bug listed in this mission's prior-scan findings has at least one automated test that executes on the Windows CI job.
- SC-005: The repo-wide second-pass audit produces an explicit finding list, and each finding is either fixed, covered by new CI, or tracked in a filed follow-up issue.
- SC-006: Issue #603 is closeable after this mission merges (Credential Manager dependency removed from Windows).
- SC-007: Issue #260 is either closeable after this mission merges or has a concrete, filed follow-up scope note describing what remains.

## Key Entities

- **Windows runtime state root**: The single `%LOCALAPPDATA%\spec-kitty\` directory on Windows that holds auth, tracker, sync, daemon, and runtime cache subtrees.
- **Auth storage backend**: The platform-selected secure store. On Windows, this is the encrypted file-backed store rooted in the runtime state root. On macOS/Linux, the existing keychain path is retained.
- **Legacy Windows state location**: Any pre-mission path where Spec Kitty historically wrote state on Windows (`~/.spec-kitty`, `~/.kittify`, `~/.config/spec-kitty`). In steady state these are migration sources only.
- **Pre-commit hook shim**: The installed Git hook and whatever cross-platform launcher it uses to invoke the commit guard via the current Python interpreter.
- **Curated Windows CI suite**: The set of tests declared Windows-critical and executed on the blocking `windows-latest` job. Test selection is explicit, not "everything that happens to pass."
- **Windows regression corpus**: Reproductions and tests for the named historical issues (#586, #105, #101, #71, and any new findings from the second-pass scan).

## Assumptions

- `windows-latest` GitHub-hosted runners remain available and free for the repository's visibility tier.
- Users on Windows are running Git for Windows (the standard distribution), not a custom or WSL-only git install.
- The canonical Python install methods on Windows are `pipx` and `uv`, both of which expose `sys.executable` reliably at install time.
- `platformdirs` remains the project's supported cross-platform path resolver.
- Existing non-Windows storage decisions (keychain on macOS/Linux, `~/.spec-kitty` semantics on POSIX) are considered correct and out of scope.
- There is no material population of Windows users relying on Credential Manager-stored credentials today whose removal path needs its own dedicated migration UX beyond the one-time file migration described here.

## Dependencies

- The project's current `platformdirs` usage in `src/kernel/paths.py` provides the canonical Windows app-data resolution.
- GitHub Actions `windows-latest` runners are required for the blocking CI job.
- The existing auth file-fallback encryption code in `src/specify_cli/auth/secure_storage/file_fallback.py` is the foundation for FR-001. Its `_DEFAULT_DIR` must be corrected; the encryption-at-rest design is not in scope for redesign.
- Open issue #603 and closed issues #586, #105, #101, #71 must be reviewed and linked from the implementation plan.

## Risks

- **Test matrix instability on Windows.** A curated suite can still expose tests that implicitly assumed POSIX. Mitigation: triage and either port or scope out each item explicitly, rather than marking as `xfail` silently.
- **Migration conflicts on real user machines.** An existing user may have partial legacy state in multiple locations. Mitigation: define explicit precedence rules, log both source and destination, and refuse rather than merge when destination conflicts with legacy source content.
- **Hook executability on Git for Windows.** Windows Git shells may interpret the hook differently depending on install method. Mitigation: test against pipx and uv install topologies in CI, not just the file-written assertion.
- **Encoding regressions in rarely-exercised code paths.** Not every UTF-8-sensitive path is in the curated suite. Mitigation: the second-pass audit explicitly searches for encoding assumptions and files follow-ups for anything not covered.
- **Scope creep.** This mission is a hardening pass, not a full port. Mitigation: non-goals are enforced in review; items outside scope are filed as follow-up issues rather than pulled in.

## Deliverables

- Code fixes covering FR-001 through FR-019.
- A native `windows-latest` blocking CI job and its curated suite.
- Tests for each confirmed Windows bug that execute on the Windows CI job.
- One-time Windows migration code and its tests.
- Updated docs and CLI/help text for Windows path messaging.
- A residual-risk section in the PR description listing any Windows items intentionally deferred, with filed follow-up issues.
- Issue status updates for #603 and #260 (closed or re-scoped with a clear follow-up).

## References

- Prior audit clone: `/tmp/spec-kitty-scan-20260414-120646` (commit `51c7cd0b`).
- Open issues: #603 (remove Credential Manager dependency), #260 (worktree subdirectory incompatibility).
- Recently closed Windows issues to revalidate: #586 (`fcntl` import), #105 (`python3` assumption), #101 (UTF-8 startup crash), #71 (dashboard empty response on Windows).
- Machine-specific testing rule: `SPEC_KITTY_ENABLE_SAAS_SYNC=1` must be set for any local testing that exercises SaaS, tracker, or sync behavior.
- Directives invoked: DIRECTIVE_010 (Specification Fidelity), DIRECTIVE_003 (Decision Documentation).
