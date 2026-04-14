# Quickstart: Windows Compatibility Hardening Pass

**Mission**: `windows-compatibility-hardening-01KP5R6K`
**Audience**: Implementer picking up a work package in this mission.

This quickstart gives you what you need to start coding on any lane within 10 minutes.

## Repository prep

```bash
cd /Users/robert/spec-kitty-dev/windows/spec-kitty
git status                # should be clean on main
spec-kitty agent mission setup-plan --mission 01KP5R6K --json
```

Branch contract: plan on `main`, merge into `main`. `/spec-kitty.implement WP##` will create a lane worktree at `.worktrees/windows-compatibility-hardening-01KP5R6K-lane-<id>/`.

## Read order

Read in this order before coding:

1. [`spec.md`](./spec.md) — what we're shipping.
2. [`plan.md`](./plan.md) — how it's cut into lanes.
3. [`research.md`](./research.md) — the resolved decisions (Q1/Q2/Q3 locked + Phase-0 research).
4. [`data-model.md`](./data-model.md) — `RuntimeRoot`, migration outcomes, storage selection.
5. [`contracts/*.md`](./contracts/) — per-surface behavior contracts and test tables.

## Lane summaries (drop-in work maps)

### Lane A — Storage foundation

**Goal**: New `src/specify_cli/paths/` subpackage with `windows_paths.py` (unified Windows root + `render_runtime_path`) and `windows_migrate.py` (destination-wins with timestamped quarantine).

**Start here**:
```bash
git grep -n "Path.home() / \".spec-kitty\"" src/
git grep -n "Path.home() / \".kittify\"" src/
git grep -n "_DEFAULT_DIR" src/specify_cli/auth/secure_storage/
```

**Acceptance**: All lane-A unit tests pass on macOS/Linux and on `windows-latest`. See `contracts/cli-migrate.md` T-MIG-01..07 and `contracts/cli-agent-status.md` T-RNDR-01..02.

### Lane B — Auth hard split

**Goal**: Windows never imports `keychain.py`; `keyring` is non-Windows-only in `pyproject.toml`.

**Start here**:
```bash
sed -n '1,80p' src/specify_cli/auth/secure_storage/abstract.py
sed -n '1,80p' src/specify_cli/auth/secure_storage/file_fallback.py
grep -n "keyring" pyproject.toml
```

**Acceptance**: Contract `auth-secure-storage.md` G-01..G-03 and T-AUTH-01, T-AUTH-02, T-PKG-01 pass.

### Lane C — Path messaging sweep

**Goal**: Replace `~/.kittify` / `~/.spec-kitty` literals in user-facing output with `render_runtime_path(...)`.

**Start here**:
```bash
git grep -n "~/\.kittify\|~/\.spec-kitty" src/specify_cli/cli/
```

**Acceptance**: `contracts/cli-agent-status.md` T-STAT-01 and T-AUDIT-01 pass. Audit report (lane H) lists all call-sites found and fixed.

### Lane D — Tracker/sync/daemon re-rooting

**Goal**: `tracker/credentials.py`, `sync/daemon.py`, `kernel/paths.py` all consume `get_runtime_root()`.

**Start here**:
```bash
sed -n '1,40p' src/specify_cli/tracker/credentials.py
sed -n '1,40p' src/specify_cli/sync/daemon.py
sed -n '1,40p' src/kernel/paths.py
```

**Acceptance**: Tests under `windows_ci` for each consumer pass on `windows-latest`; all three consumers resolve under the same `RuntimeRoot.base`.

### Lane E — Hook installer hardening

**Goal**: `policy/hook_installer.py` pins absolute `sys.executable`; executable tests include a path-with-spaces fixture.

**Start here**:
```bash
sed -n '1,120p' src/specify_cli/policy/hook_installer.py
```

**Acceptance**: `contracts/hook-installer.md` G-01..G-07 verified via T-HOOK-01..06.

### Lane F — Native Windows CI + marker

**Goal**: `.github/workflows/ci-windows.yml` is blocking on PRs; `pytest.mark.windows_ci` registered.

**Start here**:
```bash
ls .github/workflows/
cat pyproject.toml | grep -A5 "\[tool.pytest"
```

**Acceptance**: `contracts/windows-ci-job.md` G-01..G-08 verified. Branch-protection update requested in PR description.

### Lane G — Encoding + worktree + mission revalidation

**Goal**: Regression tests for #101 / #71 / #586 now run natively under `windows_ci`; worktree symlink fallback covered.

**Start here**:
```bash
sed -n '1,60p' tests/sync/test_issue_586_windows_import.py
sed -n '1,80p' src/specify_cli/core/worktree.py
sed -n '1,60p' src/specify_cli/mission.py
```

**Acceptance**: Tests `tests/regressions/test_issue_*_*.py` and `tests/core/test_worktree_symlink_fallback.py` all pass on `windows-latest`; the UTF-8 regression test reproduces #101 against pre-fix code.

### Lane H — Audit report + ADRs + follow-ups

**Goal**: Committed `architecture/2026-04-14-windows-compatibility-hardening.md`, two ADRs, and filed GitHub follow-ups for any residuals.

**Start here**:
```bash
# Per FR-018 pattern list — run from repo root:
git grep -n "~/\.kittify\|~/\.spec-kitty\|\.config/spec-kitty"
git grep -n "import fcntl\|import msvcrt"
git grep -n "shell=True\|python3 \|\"python\""
git grep -n "os\.symlink\|Path\.symlink_to"
git grep -n "open(\"" | grep -v "encoding="
git grep -n "os\.name\|sys\.platform\|%APPDATA%\|%LOCALAPPDATA%"
git grep -n "chmod\|0o755\|0o644"
```

**Acceptance**: Report committed; two ADRs committed; follow-up issues filed with `windows` label; PR description includes residual-risk section.

## Running the curated Windows suite locally (non-Windows hosts)

On macOS/Linux, you can run platform-mocked lane tests locally:
```bash
pytest -m windows_ci tests/auth/secure_storage/test_from_environment_platform_split.py
pytest -m windows_ci tests/paths/test_render_runtime_path.py
pytest -m windows_ci tests/paths/test_windows_migrate.py -k "not test_concurrent"
```

For the real thing, push to a branch and let the Windows CI job run.

## SaaS testing rule

Per machine-level rule: any local testing that exercises SaaS / tracker / sync behavior MUST set:
```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
```
CI's Windows job sets this to `"0"` by default; sync-specific tests opt in explicitly.

## Done criteria per lane

Before marking any WP `done`:
1. All contract tests for the lane pass (both local and `windows-latest`).
2. `mypy --strict` passes on touched modules.
3. Coverage for new code ≥ 90% (charter CG-02).
4. No new `[NEEDS CLARIFICATION]` markers.
5. Lane's spec FR/NFR/C ids explicitly referenced in the commit message / PR body.
