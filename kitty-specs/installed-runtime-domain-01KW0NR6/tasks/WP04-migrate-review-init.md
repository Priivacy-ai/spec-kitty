---
work_package_id: WP04
title: Migrate review/__init__.py (delete Set A helpers)
dependencies:
- WP03
requirement_refs:
- FR-008
- FR-010
- FR-019
- NFR-008
- C-001
tracker_refs: []
planning_base_branch: feat/installed-runtime-domain
merge_target_branch: feat/installed-runtime-domain
branch_strategy: Planning artifacts for this mission were generated on feat/installed-runtime-domain. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/installed-runtime-domain unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
phase: Phase 4 - review/__init__.py migration (strangler step 4)
assignee: ''
agent: ''
shell_pid: '1730852'
history:
- at: '2026-06-26T00:00:00Z'
  actor: system
  action: Prompt generated via spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/cli/commands/review/
create_intent:
- tests/specify_cli/compat/test_review_migration.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/review/__init__.py
- tests/specify_cli/compat/test_review_migration.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Migrate review/__init__.py (delete Set A helpers)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: src/specify_cli/cli/commands/review/`.

---

## Objective

Delete the **Set A** duplicate receipt-parsing helpers from `cli/commands/review/__init__.py`
(~120 LOC across 10 functions) and replace their call sites with `UvReceiptReader` +
`plan_remediation()`. Migrate the `detect_install_method()` call at line 91 to
`detect_runtime()`.

The public behavior of the `review` command must be byte-for-byte identical for all
install methods after this change (SC-002, SC-003). The snapshot parity tests committed
in WP03 are the regression guard.

## Context & Constraints

Ground truth — read before editing:
- [`spec.md`](../spec.md) FR-008, FR-010, FR-019, NFR-008, C-001
- [`research.md`](../research.md) §1 (Set A helpers table — exact function names and call sites)
- [`plan.md`](../plan.md) IC-04

**Deletion gate (research.md §1):** Before committing, run:
```bash
grep -n "_active_uv_tool_receipt\|_active_uv_tool_dir\|_same_path\|_uv_tool_python_args\|_uv_tool_env_prefix\|_uv_tool_env_values\|_powershell_quote" src/specify_cli/cli/commands/review/__init__.py
```
Expected: **zero results**. Do not merge if any helper name remains.

**C-001**: The `detect_install_method()` shim from WP02 remains alive — this WP migrates only the one call site in `review/__init__.py`. Do not modify any other call site.

**Strangler order**: Do NOT delete Set B helpers (those are in `upgrade_ux.py` — WP05). Do not touch `upgrade_ux.py`.

## Branch Strategy

- **Planning base branch**: `feat/installed-runtime-domain`
- **Merge target branch**: `feat/installed-runtime-domain`

## Subtasks & Detailed Guidance

### T019 — Delete Set A helpers; replace call sites

The 10 Set A helpers (research.md §1) and their consumers:

| To Delete | Replace With |
|-----------|-------------|
| `_active_uv_tool_receipt_path()` | `UvReceiptReader.read_for_executable(sys.executable).receipt_path` |
| `_active_uv_tool_receipt()` | `UvReceiptReader.read_for_executable(sys.executable)` (returns `UvReceiptResult`) |
| `_active_uv_tool_receipt_has_spec_kitty()` | `UvReceiptReader.read_for_executable(sys.executable).requirements` is non-empty (check by name) |
| `_active_uv_tool_dir()` | `detect_runtime().tool_dir` |
| `_active_uv_tool_bin_dir()` | `detect_runtime().bin_dir` |
| `_same_path(left, right)` | `left is not None and right is not None and Path(left).resolve() == Path(right).resolve()` (inline) |
| `_uv_tool_python_args(receipt)` | consumed by `plan_remediation()` internally — remove call site |
| `_uv_tool_env_prefix()` | consumed by `plan_remediation().render()` — remove call site |
| `_uv_tool_env_values()` | consumed by `plan_remediation()` internally — remove call site |
| `_powershell_quote(value)` | consumed by `RemediationCommand.render("windows")` — remove call site |

**Primary replacement pattern** for `_uv_tool_reinstall_command()` and `_fallback_uv_tool_reinstall_command()`:

```python
# Old: build reinstall command from helpers
# New:
runtime = detect_runtime()
cmd = plan_remediation(runtime, RemediationIntent.REINSTALL_WITH_TEST, target_version=None)
try:
    rendered = cmd.render(runtime.platform)
except ValueError:
    rendered = cmd.note or "see spec-kitty docs"
```

Read each existing call site carefully (line numbers from research.md §1) and map the new call to the exact function being replaced. The public entry point `_missing_test_extra_remediation()` keeps its signature but its body is replaced.

Update imports at the top of `review/__init__.py`:
- Remove: `from specify_cli.compat._detect.install_method import detect_install_method` (or adjust the import from `compat.__init__`)
- Add: `from specify_cli.compat._detect.runtime import detect_runtime`
- Add: `from specify_cli.compat._adapters.uv_receipt import UvReceiptReader`
- Add: `from specify_cli.compat.remediation import plan_remediation, RemediationIntent`

### T020 — Migrate `detect_install_method()` call at line 91

At line 91 in `review/__init__.py`:
```python
# Old:
install_method = detect_install_method()
# New:
runtime = detect_runtime()
install_method = runtime.install_method
```

Pass `runtime` to downstream functions that now need the full context (e.g., wherever Set A helpers were re-reading the receipt, the `runtime` object already has all fields).

Consider whether `runtime = detect_runtime()` can be called once near the top of the function and passed down, rather than calling it multiple times. A single call at function entry is preferred (SC-001 — single receipt read per invocation).

### T021 — Write `tests/specify_cli/compat/test_review_migration.py`

Snapshot parity tests (user story 4, acceptance scenario 3):

- **Byte-for-byte parity**: For a uv-tool install with a custom `tool_dir` and `python` override, assert that the reinstall command string produced by the migrated `review` command path equals the string the legacy helpers would have produced (captured as a hardcoded snapshot from pre-migration output).
- **PIPX install**: assert that `review` produces the same upgrade hint as the legacy `_HINT_TABLE` entry for PIPX.
- **Malformed receipt**: assert that `review` degrades gracefully (returns MANUAL_GUIDANCE note, does not raise).
- **Windows platform**: mock `runtime.platform = "windows"` and assert PowerShell-safe output format.

Use `unittest.mock.patch` to inject a controlled `InstalledCliRuntime` without requiring an actual uv installation.

### T022 — Deletion gate + green-gate

Run deletion gate:
```bash
grep -n "_active_uv_tool_receipt\|_active_uv_tool_dir\|_same_path\|_uv_tool_python_args\|_uv_tool_env_prefix\|_uv_tool_env_values\|_powershell_quote" src/specify_cli/cli/commands/review/__init__.py
```
Expected: zero results.

Run full suite:
```bash
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -q
pytest tests/architectural/test_no_legacy_terminology.py -q
```

Run ruff + mypy:
```bash
ruff check src/specify_cli/cli/commands/review/__init__.py
mypy src/specify_cli/cli/commands/review/__init__.py
```

## Success Criteria

- [ ] All 10 Set A helper functions deleted from `review/__init__.py`
- [ ] `detect_install_method()` call at line 91 migrated to `detect_runtime().install_method`
- [ ] Deletion gate grep returns zero results
- [ ] Snapshot parity tests pass (byte-for-byte for uv-tool reinstall command)
- [ ] Existing review command tests pass
- [ ] Full test suite green; zero ruff/mypy issues
- [ ] `upgrade_ux.py` not modified (Set B deletion deferred to WP05)

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `_uv_tool_reinstall_command()` call graph is complex | Map each call site from research.md §1 table before editing; test each path in T021 |
| Single `detect_runtime()` call vs. multiple reads | Call once at function entry and thread `runtime` through; avoid repeated calls that re-read receipt |
| `_missing_test_extra_remediation()` output changes | Lock output with a snapshot test before deleting helpers; assert no change after |
| Import order causes circular dependency | Use deferred imports inside functions where needed (follow WP02 pattern) |
