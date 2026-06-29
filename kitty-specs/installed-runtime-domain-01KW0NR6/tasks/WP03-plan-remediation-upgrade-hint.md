---
work_package_id: WP03
title: plan_remediation() + build_upgrade_hint() on planner
dependencies:
- WP02
requirement_refs:
- FR-005
- FR-006
- FR-009
- FR-011
- FR-018
- NFR-002
- NFR-004
- C-002
- C-005
tracker_refs: []
planning_base_branch: feat/installed-runtime-domain
merge_target_branch: feat/installed-runtime-domain
branch_strategy: Planning artifacts for this mission were generated on feat/installed-runtime-domain. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/installed-runtime-domain unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
- T018
phase: Phase 3 - Planner (strangler step 3)
assignee: ''
agent: ''
shell_pid: '1410366'
history:
- at: '2026-06-26T00:00:00Z'
  actor: system
  action: Prompt generated via spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/compat/
create_intent:
- tests/specify_cli/compat/test_remediation.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/compat/upgrade_hint.py
- tests/specify_cli/compat/test_remediation.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – plan_remediation() + build_upgrade_hint() on planner

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: src/specify_cli/compat/`.

---

## Objective

Complete the `remediation.py` module (started in WP01) with the full
`plan_remediation()` pure function and `RemediationCommand.render()`. Then reimplement
`build_upgrade_hint()` in `compat/upgrade_hint.py` on top of the planner, preserving
the public `UpgradeHint` type, `_HINT_TABLE`, CHK028 contract, and `Plan.upgrade_hint`
JSON contract byte-for-byte.

**Snapshot parity tests committed in this WP** are the regression guard for all
subsequent migration steps (SC-003).

## Context & Constraints

Ground truth — read before editing:
- [`spec.md`](../spec.md) FR-005, FR-006, FR-009, FR-011, FR-018, NFR-002, NFR-004, C-002, C-005
- [`data-model.md`](../data-model.md) §2 (`RemediationCommand`, `render()` platform behavior)
- [`contracts/remediation-command-render.md`](../contracts/remediation-command-render.md)
- [`research.md`](../research.md) §3 (public contracts that must stay intact)
- [`plan.md`](../plan.md) IC-03

**`plan_remediation()` must be pure (NFR-004)** — no I/O, no side effects, deterministic for same inputs. This makes it fully unit-testable without stubs.

**Preserve unchanged (C-002):**
- `UpgradeHint` frozen dataclass and its `__post_init__` invariant
- `_HINT_TABLE` dict (all 8 entries, identical values)
- CHK028 regex in `upgrade_hint.py` (must match `_COMMAND_RE` in `remediation.py`)
- `build_upgrade_hint(install_method, *, package, target_version)` public signature
- `Plan.upgrade_hint` JSON: `{"install_method": str, "command": str | null, "note": str | null}`

**PowerShell branch (C-005)**: `render("windows")` must produce PowerShell-safe quoting using the same logic as `_powershell_quote()` in `review/__init__.py` line 325. Read that function before implementing.

## Branch Strategy

- **Planning base branch**: `feat/installed-runtime-domain`
- **Merge target branch**: `feat/installed-runtime-domain`

## Subtasks & Detailed Guidance

### T014 — Implement `plan_remediation()` in `compat/remediation.py`

Add the function to the module created in WP01 (after `RemediationCommand`):

```python
def plan_remediation(
    runtime: InstalledCliRuntime,
    intent: RemediationIntent,
    target_version: str | None,
) -> RemediationCommand:
    """Return a RemediationCommand for the given runtime and intent.

    NFR-004: Pure function — no I/O, no side effects. Deterministic.
    """
```

Implementation logic per install method and intent:

| Install method | UPGRADE argv | REINSTALL_WITH_TEST argv |
|---------------|-------------|------------------------|
| `UV_TOOL` (default tool dir, no python) | `("uv", "tool", "install", "--force", "spec-kitty-cli")` | **Provenance-preserving** (see below) |
| `UV_TOOL` (custom tool dir) | same argv; env = `{"UV_TOOL_DIR": str(runtime.tool_dir)}` | same env, plus `UV_TOOL_BIN_DIR` when `is_default_bin_dir is False` |
| `UV_TOOL` (python override) | argv includes `"--python", runtime.python` | same |
| `PIPX` | `("pipx", "upgrade", "spec-kitty-cli")` | `("pipx", "install", "--include-deps", "spec-kitty-cli[test]")` |
| `BREW` | `("brew", "upgrade", "spec-kitty-cli")` | MANUAL_GUIDANCE (no standard brew test extra) |
| `PIP_USER` | `("pip", "install", "--user", "--upgrade", "spec-kitty-cli")` | MANUAL_GUIDANCE |
| `PIP_SYSTEM` | `("pip", "install", "--upgrade", "spec-kitty-cli")` | MANUAL_GUIDANCE |
| `SOURCE` | MANUAL_GUIDANCE | MANUAL_GUIDANCE |
| `UNKNOWN` | MANUAL_GUIDANCE | MANUAL_GUIDANCE |

`env` defaults to empty `{}` for most methods.

> **UV_TOOL `REINSTALL_WITH_TEST` provenance contract (FR-019 / SC-003 / issue #1358).**
> An earlier revision of this table specified `spec-kitty-cli --extra test` for
> every uv-tool install. That is a **regression**: it re-pins a directory /
> editable / path / git / url install to the PyPI release, clobbering the user's
> real source. The issue's acceptance criteria require provenance modelled
> "with nothing discarded", so the planner MUST reconstruct from
> `runtime.requirements`, byte-for-byte with the pre-migration `review` command:
> `uv tool install --force [--python V] [--with <dep>… | --with-editable <dep>] --with pytest <package-args>`,
> where `<package-args>` is `<directory>` / `--editable <dir>` / `<path>` /
> `spec-kitty-cli --from git+<src>` / `<url>` / `spec-kitty-cli==<specifier>` /
> `spec-kitty-cli`. Injected deps are carried as `--with`/`--with-editable`;
> pytest is added via `--with pytest` (deduped if already present). A receipt
> entry whose shape is unsupported (`UvRequirement.is_supported is False`), or a
> present receipt with no spec-kitty entry, yields MANUAL_GUIDANCE (conservative
> — never re-pin to PyPI). Only the receipt-absent case (`receipt_path is None`)
> falls back to a PyPI reinstall, pinned to the running version when known.

`MANUAL_GUIDANCE` result: `RemediationCommand(intent=MANUAL_GUIDANCE, argv=None, env={}, note=<human description>)`.

For `REINSTALL_WITH_TEST` that uses MANUAL_GUIDANCE, the `note` should describe the appropriate manual steps.

**UV_TOOL env+python combination**: if both `is_default_tool_dir=False` AND `python` override present, include both the env var and `--python` flag.

### T015 — Complete `RemediationCommand.render()` in `compat/remediation.py`

Replace the WP01 stub with the full implementation from `contracts/remediation-command-render.md`.

```python
def render(self, platform: Literal["posix", "windows"]) -> str:
```

**Algorithm:**
1. If `self.intent == MANUAL_GUIDANCE`: raise `ValueError("cannot render MANUAL_GUIDANCE RemediationCommand — check intent before calling render()")`.
2. If `self.argv is None`: raise `ValueError("argv is None")`.
3. Build env prefix string:
   - posix: `"KEY=shlex.quote(value) "` per entry, space-joined, trailing space if non-empty.
   - windows: `"$env:KEY='<ps_quoted_value>'; "` per entry, space-joined, trailing space if non-empty.
   - PowerShell quoting: wrap value in single quotes; replace each `'` in value with `''`. (Copy logic from `review/__init__.py` `_powershell_quote()` exactly.)
4. Build argv string:
   - posix: `" ".join(shlex.quote(a) for a in self.argv)`.
   - windows: `" ".join(self.argv)` (no additional quoting).
5. Compose: `env_prefix + argv_str`.
6. Validate against `_COMMAND_RE`; raise `ValueError(f"CHK028 violation: {composed!r}")` on mismatch.
7. Return the validated string.

### T016 — Reimplement `build_upgrade_hint()` in `compat/upgrade_hint.py`

Read the existing `build_upgrade_hint()` implementation carefully. The signature must be preserved:

```python
def build_upgrade_hint(
    install_method: InstallMethod,
    *,
    package: str,
    target_version: str | None,
) -> UpgradeHint:
```

New implementation:
1. Import `detect_runtime` and `plan_remediation` (deferred to avoid circular imports if needed).
2. Call `detect_runtime()` to get the full runtime context.
3. Call `plan_remediation(runtime, RemediationIntent.UPGRADE, target_version)`.
4. Try `cmd.render(runtime.platform)` to get the command string; catch `ValueError` and fall back to `UpgradeHint(install_method=..., command=None, note="...")`.
5. Construct and return `UpgradeHint(install_method=install_method, command=rendered, note=None)`.

**Critical**: `UpgradeHint`, `_HINT_TABLE`, and `CHK028` must not change. The `__post_init__` invariant (exactly one of command/note non-None) must still hold. Run the existing `build_upgrade_hint()` tests before and after to confirm identical behavior.

### T017 — Write `tests/specify_cli/compat/test_remediation.py`

**Snapshot parity tests (SC-003):** For every install method in the acceptance table from `contracts/remediation-command-render.md`:
- Assert `plan_remediation(runtime, UPGRADE, None).render("posix")` == expected string
- Assert `plan_remediation(runtime, UPGRADE, None).render("windows")` == expected string (where applicable)
- Assert `build_upgrade_hint(install_method, package="spec-kitty-cli", target_version=None).command` equals pre-migration value

Commit these assertions as **snapshot tests** (parametrize over install methods); they become the regression guard for WP04 and WP05.

**CHK028 regression tests (spec.md NFR-002):**
- `render()` on a MANUAL_GUIDANCE command raises `ValueError`
- `render()` on a command with metacharacters in argv (e.g., `$(rm -rf /)`) raises `ValueError(CHK028 violation)`
- Valid commands pass CHK028 and return a matching string

**Additional edge cases:**
- UV_TOOL with `is_default_tool_dir=False` and `python="3.11"` → both env var and `--python` flag in output
- `plan_remediation()` is pure: calling it twice with same runtime returns equal `RemediationCommand` objects

### T018 — Green-gate verification

Run pre-migration `build_upgrade_hint()` tests and `Plan.upgrade_hint` JSON contract tests:
```bash
PWHEADLESS=1 pytest tests/ -k "upgrade_hint or plan or remediation" -q
```

Run full suite:
```bash
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -q
pytest tests/architectural/test_no_legacy_terminology.py -q
```

Run ruff + mypy on modified files:
```bash
ruff check src/specify_cli/compat/remediation.py src/specify_cli/compat/upgrade_hint.py
mypy src/specify_cli/compat/remediation.py src/specify_cli/compat/upgrade_hint.py
```

## Success Criteria

- [ ] `plan_remediation()` is a pure function: no I/O, deterministic
- [ ] `render("posix")` and `render("windows")` produce CHK028-validated, platform-appropriate strings
- [ ] PowerShell branch preserved: `render("windows")` uses `_powershell_quote()` equivalent
- [ ] `build_upgrade_hint()` behavior unchanged for all install methods (SC-003 snapshot tests pass)
- [ ] `UpgradeHint`, `_HINT_TABLE`, CHK028 regex in `upgrade_hint.py` unchanged
- [ ] `Plan.upgrade_hint` JSON contract unchanged
- [ ] Full test suite green; zero ruff/mypy issues

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `render()` PowerShell quoting diverges from `_powershell_quote()` | Copy exact logic from `review/__init__.py` line 325 before implementing; parametrize a test with the same inputs as the legacy function |
| `build_upgrade_hint()` uses `detect_runtime()` which may fail in tests | Tests that construct `InstalledCliRuntime` directly bypass `detect_runtime()`; snapshot tests mock `detect_runtime` to return a controlled runtime |
| Circular import: `upgrade_hint.py` imports `remediation.py` which imports `_detect/runtime.py` | Use deferred local import inside `build_upgrade_hint()` function body |
| `UpgradeHint.__post_init__` invariant violated | Write a dedicated test; the invariant (exactly one of command/note non-None) must hold before and after |
