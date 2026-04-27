---
work_package_id: WP03
title: Install-method detection + upgrade hint catalog
dependencies: []
requirement_refs:
- FR-006
- FR-007
- FR-023
planning_base_branch: main
merge_target_branch: main
branch_strategy: Worktree branch derived from lanes.json by spec-kitty implement; final merge target is main.
subtasks:
- T011
- T012
- T013
history:
- at: '2026-04-27T08:19:12Z'
  actor: planner
  note: WP authored from /spec-kitty.tasks
authoritative_surface: src/specify_cli/compat/_detect/
execution_mode: code_change
mission_id: 01KQ6YDNMX2X2AN4WH43R5K2ZS
mission_slug: cli-upgrade-nag-lazy-project-migrations-01KQ6YDN
owned_files:
- src/specify_cli/compat/_detect/__init__.py
- src/specify_cli/compat/_detect/install_method.py
- src/specify_cli/compat/upgrade_hint.py
- tests/specify_cli/compat/test_install_method.py
- tests/specify_cli/compat/test_upgrade_hint.py
priority: P0
tags: []
---

# WP03 — Install-method detection + upgrade hint catalog

## Branch Strategy

- **Planning base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP03 --agent <name>` from `lanes.json`.

## Objective

Detect how the user installed the running `spec-kitty-cli` (pipx, pip-user, pip-system, brew, system-package, source, unknown) and produce a sanitised, copy-pasteable upgrade hint per install method. The detection is consumed by the planner to fill `Plan.upgrade_hint` and shown in `Plan.rendered_human`.

## Context

- Spec: FR-006 (exact upgrade instructions when install method known), FR-007 (safe manual instructions otherwise), FR-023 case `install_method_unknown`.
- Plan: §"Engineering Alignment" Q2-A.
- Research: [`research.md`](../research.md) §R-03 (detection chain).
- Data model: [`data-model.md`](../data-model.md) §1.7 (`InstallMethod`), §1.8 (`UpgradeHint`).
- Security checklist: CHK028 (sanitise hints), CHK031 (unknown method MUST NOT be a runnable command), CHK032 (detection errors must not crash the host).

## Subtasks

### T011 — `InstallMethod` enum + detection chain

**Steps**:
1. In `src/specify_cli/compat/_detect/install_method.py`:
   - `InstallMethod` enum with members `PIPX, PIP_USER, PIP_SYSTEM, BREW, SYSTEM_PACKAGE, SOURCE, UNKNOWN` (string values matching data-model §1.7).
   - `detect_install_method(*, executable: str | None = None, distribution_loader=None) -> InstallMethod` — pure function with injectable dependencies for testing. Default `executable=sys.executable`. Default `distribution_loader=importlib.metadata.distribution`.
2. **Detection chain (first match wins)** — implement exactly per research §R-03:
   1. Source/dev install: package's `__file__` is under cwd AND a `pyproject.toml` exists at the package root.
   2. pipx: `executable` matches `*/pipx/venvs/spec-kitty*` or lives under `~/.local/pipx/venvs/`.
   3. brew: `executable` lives under `/opt/homebrew/`, `/usr/local/Cellar/`, `/usr/local/opt/`, or `<brew --prefix>/Cellar` (subprocess with 1s timeout; on failure fall through silently).
   4. System package: `executable.startswith("/usr/bin/python")` AND `distribution_loader("spec-kitty-cli").read_text("INSTALLER")` returns one of `apt`, `dnf`, `pacman`, `yum`, `zypper`.
   5. pip-user vs pip-system: `INSTALLER` text equals `"pip"`. If distribution location is under `site.getusersitepackages()` → `PIP_USER`, else `PIP_SYSTEM`.
   6. Fallback: `UNKNOWN`.
3. Each branch wrapped in try/except; any unexpected exception silently falls through to the next branch (CHK032). The function MUST never raise.
4. The function MUST NOT print, log at warning+, or perform any I/O beyond what the branch needs.

**Files**: `src/specify_cli/compat/_detect/__init__.py` (empty), `src/specify_cli/compat/_detect/install_method.py`.

**Validation**: each branch returns the expected enum value when its conditions hold.

### T012 — `UpgradeHint` builder

**Steps**:
1. In `src/specify_cli/compat/upgrade_hint.py`:
   - `UpgradeHint` frozen dataclass per data-model §1.8 (`install_method`, `command`, `note`).
   - `build_upgrade_hint(install_method: InstallMethod, *, package: str = "spec-kitty-cli") -> UpgradeHint`.
2. Static command table (sanitised against regex `^[A-Za-z0-9 .\-+_/=:]{1,128}$` at construction time):
   - `PIPX` → `"pipx upgrade spec-kitty-cli"`
   - `PIP_USER` → `"pip install --user --upgrade spec-kitty-cli"`
   - `PIP_SYSTEM` → `"pip install --upgrade spec-kitty-cli"`
   - `BREW` → `"brew upgrade spec-kitty-cli"`
   - `SYSTEM_PACKAGE` → `note` (no single-line command — multi-line manual instruction; `command=None`).
   - `SOURCE` → `note` (manual: "Rebuild from source: pip install -e ." — `command=None`, security CHK031).
   - `UNKNOWN` → `note` (multi-line manual: "Your install method could not be detected automatically. Upgrade Spec Kitty using the same method you used to install it." `command=None`, security CHK031).
3. Exactly one of `command` / `note` is non-None per `UpgradeHint`.

**Files**: `src/specify_cli/compat/upgrade_hint.py`.

**Validation**: every `InstallMethod` value yields a valid `UpgradeHint` with the correct invariant.

### T013 — Unit tests for each install-method branch and hint

**Steps**:
1. `tests/specify_cli/compat/test_install_method.py`:
   - One test per branch, mocking `executable` and `distribution_loader` to force each path.
   - Test that the chain returns `UNKNOWN` when no branch matches.
   - Test that an exception from `distribution_loader` does not crash detection (returns next branch's result or UNKNOWN).
   - Test that `brew --prefix` subprocess timeout is bounded (mock `subprocess.run` to raise `TimeoutExpired`; expect fallthrough to next branch, not a crash).
2. `tests/specify_cli/compat/test_upgrade_hint.py`:
   - Every `InstallMethod` value yields a hint that satisfies the invariant.
   - The command pattern regex rejects an injected ANSI escape (assert that an attempt to construct an `UpgradeHint` with such a command raises ValueError; or that the table builder never produces such commands).

**Files**: `tests/specify_cli/compat/test_install_method.py`, `tests/specify_cli/compat/test_upgrade_hint.py`.

**Validation**: `pytest tests/specify_cli/compat/test_install_method.py tests/specify_cli/compat/test_upgrade_hint.py -v` green; coverage ≥ 90% on both source files.

## Definition of Done

- [ ] All seven `InstallMethod` values implemented and tested.
- [ ] Detection chain follows research §R-03 ordering.
- [ ] No branch raises; all branches caught and fall through.
- [ ] Hint commands sanitised against regex; `SOURCE` and `UNKNOWN` produce `note`, never `command` (CHK031).
- [ ] `mypy --strict` clean.
- [ ] `ruff check` clean.
- [ ] Coverage ≥ 90% on `_detect/install_method.py` and `upgrade_hint.py`.

## Risks

- `subprocess.run(["brew", "--prefix"], timeout=1.0)` may take longer than 1s on cold disk — accept the timeout cost; the fallthrough is harmless.
- macOS users with a non-standard Homebrew prefix: heuristic still works because `Cellar/` substring is checked.

## Reviewer Guidance

1. **No raises**: every branch wrapped in try/except; the function MUST always return.
2. **Sanitisation**: try to construct an `UpgradeHint` with a command containing `\x1b[31m` — must be rejected.
3. **`UNKNOWN` is not a command**: confirm the unknown hint's `command` field is `None`.
4. **Subprocess bounding**: `subprocess.run` calls have `timeout=1.0`.
5. **Pure detection**: detection is testable without mocking the OS — all I/O is behind injectable dependencies.

## Implementation command

```bash
spec-kitty agent action implement WP03 --agent <name>
```
