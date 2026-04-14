# ADR 1 (2026-04-14): Windows Auth Platform Split

**Date:** 2026-04-14
**Status:** Accepted
**Deciders:** spec-kitty core team
**Technical Story:** [Priivacy-ai/spec-kitty#603](https://github.com/Priivacy-ai/spec-kitty/issues/603) (Remove dependency on Windows Credential Manager)
**Tags:** windows, auth, keyring, platform-split, secure-storage, hardening

---

## Context and Problem Statement

Mission `080` (browser-mediated OAuth/OIDC) introduced session persistence via OS-managed secret
stores: macOS Keychain, Windows Credential Manager, and Linux Secret Service — all via the
`keyring` library. This created several problems:

- **Windows Credential Manager**: adds a desktop-credential-infrastructure dependency to a CLI
  tool that runs in terminal, CI, and headless automation contexts.
- **macOS Keychain**: prompts the user because the requesting process identity is bare `python`,
  not a signed application bundle.
- **All platforms**: `keyring` is pulled as an install dependency, complicating packaging and
  creating an unexpected permission surface on headless hosts.
- **Historical regression (#586)**: prior split/fallback logic imported `fcntl` on Windows,
  causing `ImportError` on first use.

Mission `082` added a file-fallback store at `~/.config/spec-kitty/auth/` (later normalised
to `~/.spec-kitty/auth/`) as a backup, but the OS-secret-store backend remained the default.

The product decision (issue #603) is to cut over to the file-backed store on **all platforms**
and remove OS-secret-store backends entirely. The decision is not a fallback; zero customers have
used the new auth flow, so no migration of OS-secret-store-backed sessions is needed.

For the Windows hardening mission (`windows-compatibility-hardening-01KP5R6K`) the scope was
narrower: ensure that `keyring` is **never imported or installed on Windows**, and that
`WindowsFileStorage` is the sole Windows auth backend. The full cross-platform file-only cutover
(removing macOS Keychain too) is deferred to a follow-on mission.

---

## Decision Drivers

- `keyring` must not be installed or imported on Windows (FR-001, C-001).
- Windows CI must assert `keyring` absent post-install (`ci-windows.yml` step).
- The auth split must be a HARD dispatch with no runtime fallback (spec constraint C-001).
- `pyproject.toml` must carry a PEP 508 `sys_platform` marker so the Windows wheel/sdist is
  built without `keyring` (research R-11).
- Type checking (`mypy --strict`) must continue to verify `keychain.py` on all platforms
  without importing `keyring` at runtime on Windows.

---

## Considered Options

- **Option A (chosen): Hard platform split.** `if sys.platform == "win32"` at the
  `SecureStorage.from_environment()` dispatch site. Windows → `WindowsFileStorage`; non-Windows
  → existing keychain-first logic. `keyring` guarded behind `TYPE_CHECKING` on Windows.
  `pyproject.toml` marker: `keyring>=24.0; sys_platform != "win32"`.

- **Option B: Runtime `try/except ImportError`.** Import `keyring` speculatively and fall back
  on failure. Rejected: weaker posture; `keyring` could still be pulled transitively; violates
  the "no dependency on Windows code path" spirit of FR-001.

- **Option C: Optional extras (`spec-kitty-cli[keyring]`).** Keyring installed only if the user
  opts in. Rejected: unnecessary user-facing configuration burden; the product decision is that
  OS secret stores are not a supported backend at all.

- **Option D: Full plugin registry.** Auth backend discovered via entry points; `keyring` is
  one possible plugin. Rejected: over-engineered for the immediate hardening goal; deferred to
  a future extensibility mission.

---

## Decision

Adopt **Option A**: hard platform split in the auth dispatch.

### Implementation

1. `src/specify_cli/auth/secure_storage/__init__.py` conditionally imports `keychain` only when
   `sys.platform != "win32"`:
   ```python
   if sys.platform != "win32":
       from .keychain import KeychainStorage
   ```

2. `src/specify_cli/auth/secure_storage/abstract.py` — `SecureStorage.from_environment()` is a
   HARD split:
   ```python
   import sys  # deferred so callers can monkeypatch sys.platform in tests
   if sys.platform == "win32":
       return WindowsFileStorage(...)
   # else: existing keychain-first logic
   ```

3. `src/specify_cli/auth/secure_storage/windows_storage.py` — `WindowsFileStorage` wraps
   `EncryptedFileStorage` rooted at `%LOCALAPPDATA%\spec-kitty\auth\`. Does **not** depend on
   `keyring` or Windows Credential Manager.

4. `pyproject.toml` dependency marker:
   ```toml
   "keyring>=24.0; sys_platform != \"win32\"",
   ```
   Windows wheels/sdists install without `keyring`.

5. `.github/workflows/ci-windows.yml` asserts `keyring` is absent:
   ```yaml
   - name: Assert keyring is NOT installed on Windows
     shell: bash
     run: |
       if pipx runpip spec-kitty-cli show keyring >/dev/null 2>&1; then
         echo "::error::keyring IS installed on Windows"
         exit 1
       fi
   ```

6. `tests/packaging/test_windows_no_keyring.py` (`@pytest.mark.windows_ci`) asserts that
   `keyring` is not importable from within the spec-kitty-cli environment on Windows.

---

## Consequences

### Positive

- Windows users never have an auth dependency on Credential Manager or any OS secret store.
- Packaging is cleaner: Windows wheels carry fewer transitive dependencies.
- CI definitively asserts the packaging invariant on every PR.
- Support story is simpler: one auth backend, one set of file paths, one error message.
- Closes #603 and #586.

### Negative

- macOS and Linux still use `keyring` / Keychain / Secret Service (the full cross-platform
  cutover to file-only is deferred). This creates a temporary asymmetry where Windows users
  have a slightly different auth story than macOS/Linux users.
- `keychain.py` is retained in the codebase. It is never imported on Windows, but it remains
  as dead code from a Windows perspective until the follow-on mission removes it.

### Neutral

- `TYPE_CHECKING`-only import shape for `keychain.py` on Windows retains `mypy --strict`
  coverage without runtime import.
- PEP 508 `sys_platform` markers are the canonical mechanism for this — supported by pip,
  pipx, uv, and all modern Python packaging tools.

---

## References

- Spec: FR-001, C-001 (mission `windows-compatibility-hardening-01KP5R6K`)
- Research: R-04 (Windows auth storage hard split implementation), R-11 (keyring packaging marker)
- WP03 commit: `2c93de2b` — `feat(WP03): hard platform split for auth secure_storage; conditional keyring`
- Audit report: `architecture/2026-04-14-windows-compatibility-hardening.md`
- Issue: [#603](https://github.com/Priivacy-ai/spec-kitty/issues/603)
- Issue: [#586](https://github.com/Priivacy-ai/spec-kitty/issues/586)
