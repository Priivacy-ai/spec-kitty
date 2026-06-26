---
work_package_id: WP05
title: Migrate upgrade_ux.py + event emission + history records
dependencies:
- WP04
requirement_refs:
- FR-008
- FR-010
- FR-012
- FR-014
- FR-020
- NFR-007
- NFR-008
- C-001
tracker_refs: []
planning_base_branch: feat/installed-runtime-domain
merge_target_branch: feat/installed-runtime-domain
branch_strategy: Planning artifacts for this mission were generated on feat/installed-runtime-domain. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/installed-runtime-domain unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
- T027
- T028
phase: Phase 5 - upgrade_ux.py migration + event + history (strangler step 5)
assignee: ''
agent: ''
shell_pid: '2377874'
history:
- at: '2026-06-26T00:00:00Z'
  actor: system
  action: Prompt generated via spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/readiness/
create_intent:
- tests/specify_cli/readiness/test_upgrade_ux_migration.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/readiness/upgrade_ux.py
- tests/specify_cli/readiness/test_upgrade_ux_migration.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Migrate upgrade_ux.py + event emission + history records

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: src/specify_cli/readiness/`.

---

## Objective

Delete the **Set B** duplicate receipt-parsing helpers from `readiness/upgrade_ux.py`,
migrate the `detect_install_method` callable reference at line 648, update
`_default_upgrade_runner` to consume `RemediationCommand.argv` and `.env` directly,
emit `UvToolInstallationVerified` events (UV_TOOL installs only), and append
`UpgradeAttemptRecord` to the history store on every completion (best-effort).

## Context & Constraints

Ground truth — read before editing:
- [`spec.md`](../spec.md) FR-008, FR-010, FR-012, FR-014, FR-020, NFR-007, NFR-008, C-001
- [`research.md`](../research.md) §1 Set B (4 helpers), §2 call sites 5+6 (callable ref at line 648)
- [`plan.md`](../plan.md) IC-05
- [`data-model.md`](../data-model.md) §4 (`UvToolInstallationVerified`), §5/§7 (`UpgradeAttemptStore.append()`)

**Deletion gate (research.md §1 Set B):** Before committing, run:
```bash
grep -n "_active_uv_tool_receipt\|_active_uv_tool_dir\|_same_path\|_uv_tool_python_args" src/specify_cli/readiness/upgrade_ux.py
```
Expected: **zero results**.

**Event emission gate (spec.md FR-014):** `UvToolInstallationVerified` is emitted ONLY for `UV_TOOL` installs. Other install methods append an `UpgradeAttemptRecord` to the history store but do NOT emit this event.

**History store is best-effort (contracts/history-store-query.md):** `UpgradeAttemptStore.append()` swallows all exceptions. The upgrade runner must not fail if the store is unreachable.

**C-001**: The `detect_install_method()` shim remains alive for the other 3 call sites (upgrade.py×2, planner.py×1). Do NOT touch those files in this WP.

## Branch Strategy

- **Planning base branch**: `feat/installed-runtime-domain`
- **Merge target branch**: `feat/installed-runtime-domain`

## Subtasks & Detailed Guidance

### T023 — Delete Set B helpers; update `_default_upgrade_runner`

The 4 Set B helpers (research.md §1 Set B):

| To Delete | Where consumed | Replace With |
|-----------|---------------|-------------|
| `_active_uv_tool_receipt()` | `_uv_tool_python_args()` | `detect_runtime().python` (already in `InstalledCliRuntime`) |
| `_active_uv_tool_dir()` | `_uv_tool_upgrade_env()` | `detect_runtime().tool_dir`, `detect_runtime().is_default_tool_dir` |
| `_same_path(left, right)` | `_uv_tool_upgrade_env()` | `Path(left).resolve() == Path(right).resolve()` (inline, not needed after migration) |
| `_uv_tool_python_args()` | `_default_upgrade_runner()` line 239 | consumed by `plan_remediation()` internally |

**New `_default_upgrade_runner` signature** — the runner now accepts a pre-built `RemediationCommand`:

```python
def _default_upgrade_runner(
    cmd: RemediationCommand,
    runtime: InstalledCliRuntime,
    *,
    dry_run: bool = False,
) -> subprocess.CompletedProcess[str]:
```

Or adapt the existing call site to call `detect_runtime()` + `plan_remediation()` once before passing to the runner. The exact refactoring depends on the existing call graph — read the function and its callers before editing.

The runner body now:
1. Executes `subprocess.run(list(cmd.argv), env={**os.environ, **cmd.env}, ...)` using `.argv` and `.env` from the `RemediationCommand`.
2. No longer reconstructs argv from receipt helpers.

### T024 — Migrate `install_detector` callable ref (call sites 5+6)

At line 648 (research.md §2 site 5):
```python
# Old:
installer_detector = detect_install_method
# New:
installer_detector = lambda: detect_runtime().install_method
```

At line 695 (site 6 — covered by site 5 migration): the call `method = installer_detector()` already works after site 5 is updated.

Update the import at the top of `upgrade_ux.py`:
- Remove: `from specify_cli.compat._detect.install_method import detect_install_method` (or adjust if coming from `compat.__init__`)
- Add: `from specify_cli.compat._detect.runtime import detect_runtime`

### T025 — Add `UvToolInstallationVerified` event emission

In `_default_upgrade_runner`, after the subprocess completes:

```python
if runtime.install_method == InstallMethod.UV_TOOL:
    from specify_cli.compat.install_events import UvToolInstallationVerified, VerificationConfidence
    # Re-read receipt post-upgrade for entrypoint_match
    post_receipt = UvReceiptReader.read_for_executable(sys.executable)
    entrypoint_match = _check_entrypoint_present(post_receipt)
    confidence = _derive_confidence(result.returncode, entrypoint_match)
    event = UvToolInstallationVerified(
        receipt_path=post_receipt.receipt_path,
        entrypoint_match=entrypoint_match,
        package_binding=_derive_package_binding(post_receipt),
        confidence=confidence,
    )
    # Emit event — use the existing event-emission infrastructure if present,
    # otherwise store in a module-level list for test inspection
    _emit_install_verified_event(event)
```

Helper functions to add (all private, within `upgrade_ux.py`):
- `_check_entrypoint_present(receipt: UvReceiptResult) -> bool`: True if "spec-kitty" entrypoint exists in the receipt's entrypoints list after upgrade.
- `_derive_confidence(exit_code: int | None, entrypoint_match: bool) -> VerificationConfidence`: HIGH if exit_code == 0 and entrypoint_match; MEDIUM if exit_code == 0 and not entrypoint_match; LOW otherwise.
- `_derive_package_binding(receipt: UvReceiptResult) -> str`: first requirement's `name + specifier` or `"unknown"`.
- `_emit_install_verified_event(event: UvToolInstallationVerified) -> None`: best-effort emit (swallow errors); integrate with any existing event-bus infrastructure.

**NFR-007**: Do NOT log or transmit `event.receipt_path`. Wrap the entire emission in `try/except Exception: # noqa: BLE001`.

### T026 — Append `UpgradeAttemptRecord` to history store

In `_default_upgrade_runner`, after the subprocess completes (all install methods):

```python
from specify_cli.compat.history import UpgradeAttemptRecord, UpgradeAttemptOutcome, UpgradeAttemptStore
import ulid  # or uuid if ulid not available — see note

outcome = UpgradeAttemptOutcome.SUCCESS if result.returncode == 0 else UpgradeAttemptOutcome.FAILURE
record = UpgradeAttemptRecord(
    attempt_id=str(ulid.new()),  # or uuid4() as fallback
    timestamp=datetime.now(tz=timezone.utc),
    install_method=runtime.install_method,
    intent="upgrade",
    outcome=outcome,
    exit_code=result.returncode,
    target_version=None,  # populated if available from caller context
)
store = UpgradeAttemptStore()
store.append(record)  # best-effort — swallows all errors
```

**ULID vs UUID**: If `python-ulid` is not a project dependency, use `str(uuid.uuid4())` as the `attempt_id` fallback. Do NOT add a new package dependency without checking `pyproject.toml` first. The store only requires a collision-resistant, non-PII identifier.

**NFR-007**: `record` must contain no user paths, hostnames, or project slugs. `target_version` may be populated from the upgrade intent if the caller passes it; otherwise None.

### T027 — Write `tests/specify_cli/readiness/test_upgrade_ux_migration.py`

Test cases (all using mocked subprocess and `InstalledCliRuntime`):

1. **UV_TOOL success** — runner exits 0 → `UvToolInstallationVerified` event emitted with `confidence=HIGH` (or MEDIUM if entrypoint check fails) AND `UpgradeAttemptRecord(outcome=SUCCESS)` appended to store.
2. **UV_TOOL failure** — runner exits non-zero → `UvToolInstallationVerified` with `confidence=LOW` AND `UpgradeAttemptRecord(outcome=FAILURE)`.
3. **PIPX success** — runner exits 0 → NO `UvToolInstallationVerified` event AND `UpgradeAttemptRecord(outcome=SUCCESS)` appended.
4. **Store unreachable** — store path is a read-only dir → `_default_upgrade_runner()` returns normally (best-effort swallow).
5. **Event emission failure** — `_emit_install_verified_event` raises → runner returns normally (best-effort swallow).
6. **Set B deletion parity** — mock UV_TOOL runtime with `python="3.12"` and custom `tool_dir`; assert that the subprocess call uses the correct env and `--python` flag (from `RemediationCommand.env` and `.argv`).

Use `SPEC_KITTY_HISTORY_DB_PATH` env var to isolate each test's store in `tmp_path`.

### T028 — Deletion gate + green-gate

Run deletion gate:
```bash
grep -n "_active_uv_tool_receipt\|_active_uv_tool_dir\|_same_path\|_uv_tool_python_args" src/specify_cli/readiness/upgrade_ux.py
```
Expected: zero results.

Run full suite:
```bash
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -q
pytest tests/architectural/test_no_legacy_terminology.py -q
```

Run ruff + mypy:
```bash
ruff check src/specify_cli/readiness/upgrade_ux.py
mypy src/specify_cli/readiness/upgrade_ux.py
```

## Success Criteria

- [ ] All 4 Set B helpers deleted from `upgrade_ux.py`
- [ ] `detect_install_method` callable ref (line 648) migrated to `detect_runtime`
- [ ] `_default_upgrade_runner` uses `RemediationCommand.argv` + `.env`
- [ ] `UvToolInstallationVerified` emitted after UV_TOOL completions only
- [ ] `UpgradeAttemptRecord` appended to history store after every completion
- [ ] Deletion gate grep returns zero results
- [ ] Full test suite green; zero ruff/mypy issues
- [ ] `upgrade.py` and `planner.py` call sites NOT modified (deferred to WP07)

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `_default_upgrade_runner` has complex call graph | Read caller chain before editing; trace from the public `run_upgrade()` entry point inward |
| `ulid` package not a dependency | Check `pyproject.toml` first; fall back to `uuid4()` if not available |
| Event emission infrastructure unclear | Look for existing event-bus patterns in `upgrade_ux.py` or sibling modules; if none, use a simple list or no-op placeholder that tests can inspect |
| Best-effort append test unreliable | Use a read-only `tmp_path` fixture to simulate store unavailability |
