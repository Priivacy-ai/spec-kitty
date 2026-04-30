---
work_package_id: WP01
title: Wire Synthesis-State Validation and Fix --json Stdout
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-009
planning_base_branch: main
merge_target_branch: main
branch_strategy: Implementation happens in a worktree on a kitty lane branch. Planning artifacts stay on main. Merge target is main via PR fix/charter-p7-release-closure.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
agent: claude
history:
- event: created
  at: '2026-04-30T13:57:24Z'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/charter_bundle.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

Then return here and continue.

---

## Objective

Fix two bugs in `src/specify_cli/cli/commands/charter_bundle.py`:

1. **Missing synthesis-state gate** (FR-001 to FR-004): `validate_synthesis_state()` from `src/charter/bundle.py` is never called. Synthesized doctrine artifacts can exist without matching provenance sidecars and pass validation silently.

2. **`--json` stdout leakage** (FR-005 to FR-006): When `_collect_provenance_validation_errors()` returns errors, the current code prints Rich-formatted text to `console` (stdout) and raises `typer.Exit(code=1)` before the `json_output` branch is ever reached. This means `--json` mode does not emit JSON on sidecar errors — it emits formatted text.

The fix: refactor to a single rendering path that always runs, accumulate all errors into the report dict, and emit JSON or human output from one exit gate.

---

## Context

**Relevant files** (read before starting):
- `src/specify_cli/cli/commands/charter_bundle.py` — the target file (full read required)
- `src/charter/bundle.py` — source of `validate_synthesis_state()` and `BundleValidationResult` (read lines 100–200)
- `kitty-specs/charter-p7-release-closure-01KQF9B9/contracts/validate-json-output.md` — the target JSON contract

**Key existing code** (lines in `charter_bundle.py`):
- Line 24: `from charter.bundle import CANONICAL_MANIFEST, CharterBundleManifest` — extend this import
- Lines 301–391: the `validate()` command — this is where all changes happen
- Lines 310–311: `console = Console()` (stdout), `err_console = Console(stderr=True)` — use `err_console` for error rendering in human mode
- Lines 377–382: the buggy early-exit block — remove this
- Lines 384–391: the json_output branch and final exit — this becomes the unified exit gate

**What `validate_synthesis_state()` does:**
- Checks every artifact under `.kittify/doctrine/**` has a provenance sidecar
- Checks every provenance sidecar references an existing artifact file
- If `synthesis-manifest.yaml` exists, verifies `content_hash` values per artifact against on-disk bytes
- Returns `BundleValidationResult(synthesis_state_present, errors, warnings, passed)`
- For legacy bundles (no doctrine dir, no sidecars): returns `synthesis_state_present=False`, empty errors — safe to call unconditionally

---

## Subtask T001 — Extend Import

**Purpose**: Add `validate_synthesis_state` and `BundleValidationResult` to the import from `charter.bundle`.

**Change**:
```python
# Before (line 24):
from charter.bundle import CANONICAL_MANIFEST, CharterBundleManifest

# After:
from charter.bundle import (
    CANONICAL_MANIFEST,
    BundleValidationResult,
    CharterBundleManifest,
    validate_synthesis_state,
)
```

**Validation**:
- [ ] `from charter.bundle import validate_synthesis_state` resolves without ImportError
- [ ] `mypy --strict src/specify_cli/cli/commands/charter_bundle.py` still passes (no new type errors from import)

---

## Subtask T002 — Refactor Sidecar Error Handling

**Purpose**: Remove the early exit that bypasses the json_output branch; keep sidecar errors local for later accumulation into the report.

**Current code (lines 375–382)**:
```python
# FR-006 / FR-007: Validate provenance sidecar content.
# Parse each sidecar as ProvenanceEntry; fail closed on validation errors.
sidecar_errors = _collect_provenance_validation_errors(canonical_root)

if sidecar_errors:
    for msg in sidecar_errors:
        console.print(f"[red]Provenance validation error:[/red] {msg}")
    raise typer.Exit(code=1)
```

**After**:
```python
# Collect provenance sidecar content validation errors (FR-006 / FR-007).
# Do NOT exit here — accumulate into report and let the unified exit gate below handle it.
sidecar_errors = _collect_provenance_validation_errors(canonical_root)
```

Delete the `if sidecar_errors:` block entirely. The sidecar errors will be surfaced via the report in T004/T005.

**Validation**:
- [ ] The `if sidecar_errors: console.print(...); raise typer.Exit(code=1)` block is gone
- [ ] `sidecar_errors` is still assigned from `_collect_provenance_validation_errors(canonical_root)`

---

## Subtask T003 — Call `validate_synthesis_state()`

**Purpose**: Invoke the synthesis-state helper and capture its result.

**Insert after the `sidecar_errors = ...` line**:
```python
# FR-001 to FR-004: Call the full synthesis-state gate.
synth_result: BundleValidationResult = validate_synthesis_state(canonical_root)
```

Place this immediately after T002's `sidecar_errors` assignment, before the `report = {...}` dict is built.

**Validation**:
- [ ] `synth_result` is assigned before `report` is built
- [ ] mypy resolves `synth_result` as `BundleValidationResult` without error

---

## Subtask T004 — Build `synthesis_state` Dict and Mirrored `errors` List

**Purpose**: Add `synthesis_state` and a top-level `errors` list to the report, per the JSON contract.

**After building the existing `report` dict**, add the following fields:

```python
# Build mirrored top-level errors list (FR-007).
# Provenance sidecar errors get a "provenance:" prefix so consumers can distinguish them.
provenance_error_strings = [f"provenance: {e}" for e in sidecar_errors]
synthesis_error_strings = [f"synthesis_state: {e}" for e in synth_result.errors]
all_errors = provenance_error_strings + synthesis_error_strings

# Extend the report with synthesis state (FR-005 / FR-007).
report["errors"] = all_errors
report["synthesis_state"] = {
    "present": synth_result.synthesis_state_present,
    "passed": synth_result.passed,
    "errors": list(synth_result.errors),
    "warnings": list(synth_result.warnings),
}
```

**Validation**:
- [ ] `report["errors"]` is a list of strings
- [ ] `report["synthesis_state"]["present"]` is a bool
- [ ] `report["synthesis_state"]["passed"]` is a bool
- [ ] `report["synthesis_state"]["errors"]` and `["warnings"]` are lists of strings
- [ ] When no synthesis state exists (legacy bundle): `report["synthesis_state"] == {"present": False, "passed": True, "errors": [], "warnings": []}`

---

## Subtask T005 — Update `result`/`passed` and Single Exit Gate

**Purpose**: Compute the overall pass/fail state from all checks; render once and exit once.

**Replace the current final block** (lines ~384–391):
```python
# Current (broken):
if json_output:
    sys.stdout.write(_json.dumps(report, indent=2) + "\n")
else:
    _render_human(report, console)

raise typer.Exit(code=0 if bundle_compliant else 1)
```

**With**:
```python
# Overall gate: pass only if charter manifest, sidecar content, AND synthesis state all pass.
overall_passed = bundle_compliant and not sidecar_errors and synth_result.passed
report["result"] = "success" if overall_passed else "failure"

if json_output:
    # Strict JSON to stdout — no Rich output on this path (FR-006).
    sys.stdout.write(_json.dumps(report, indent=2) + "\n")
else:
    _render_human(report, console)
    # Surface all errors in human mode using stderr.
    if all_errors:
        err_console.print("")
        for msg in all_errors:
            err_console.print(f"[red]Validation error:[/red] {msg}")

raise typer.Exit(code=0 if overall_passed else 1)
```

**Key invariants**:
- Stdout in `--json` mode: only the `sys.stdout.write(...)` line. Nothing else.
- `bundle_compliant` semantics unchanged — still reflects charter manifest structure only.
- `report["result"]` is now driven by `overall_passed`, not `bundle_compliant` alone.

**Validation**:
- [ ] `overall_passed` uses all three checks
- [ ] `report["result"]` is set to "success"/"failure" based on `overall_passed`
- [ ] `json_output=True` path: only `sys.stdout.write(...)` — no `console.print()` calls before or after
- [ ] Human path: `_render_human` then `err_console` for errors (not `console`)
- [ ] Single `raise typer.Exit(...)` at the end

---

## Subtask T006 — Extend `_render_human` and Verify

**Purpose**: Update the human-readable output to include synthesis state; confirm existing tests pass; confirm mypy passes.

**Extend `_render_human`** to display `synthesis_state` if present in the report. Add after the existing `bundle_compliant` line:

```python
synth = report.get("synthesis_state")
if synth:
    if synth["present"]:
        if synth["passed"]:
            console.print("[green]Synthesis state: valid (all artifacts have provenance).[/green]")
        else:
            console.print("[red]Synthesis state: INVALID.[/red]")
            for err in synth["errors"]:
                console.print(f"  [red]• {err}[/red]")
    else:
        console.print("[dim]Synthesis state: not present (legacy bundle).[/dim]")
```

**Run validation**:

```bash
cd src
uv run mypy --strict specify_cli/cli/commands/charter_bundle.py
```

```bash
uv run pytest tests/charter/test_bundle_validate_cli.py -q
uv run pytest tests/specify_cli/cli/commands/test_charter_status_provenance.py -q
uv run pytest tests/doctrine/test_versioning.py tests/specify_cli/upgrade/test_charter_bundle_v2_migration.py -q
uv run ruff check specify_cli/cli/commands/charter_bundle.py
```

All existing tests must pass before committing.

**Definition of Done for WP01**:
- [ ] `validate_synthesis_state()` is called in `validate()`
- [ ] `synthesis_state` key present in JSON output for all paths (pass, fail, legacy)
- [ ] `errors` key present in JSON output, mirroring synthesis and provenance errors
- [ ] `--json` stdout is valid JSON for every path (json.loads succeeds)
- [ ] No Rich/console output to stdout when `--json` is active
- [ ] Existing tests in `test_bundle_validate_cli.py` and `test_charter_status_provenance.py` pass
- [ ] `mypy --strict` passes on `charter_bundle.py`
- [ ] `ruff check` passes

---

## Branch Strategy

**Planning base branch**: `main`
**Final merge target**: `main`

Execution worktrees are allocated per computed lane from `lanes.json`. The implementing agent enters via:

```bash
spec-kitty agent action implement WP01 --agent claude
```

Do not push or merge directly to `main`. Implementation lives in the lane worktree branch. The PR target is `main` via `fix/charter-p7-release-closure`.

---

## Reviewer Guidance

- Confirm no `console.print(...)` calls appear in the `--json` path. Grep for `console.print` inside the `if json_output:` branch — there should be none.
- Confirm `sys.stdout.write` is the only stdout write in the function.
- Confirm `overall_passed` uses all three checks: `bundle_compliant and not sidecar_errors and synth_result.passed`.
- Confirm `report["synthesis_state"]` is always a dict (never absent) in JSON output.
- Confirm `report["errors"]` is always a list (never absent) in JSON output.
- Confirm legacy bundle path: `synthesis_state.present=False`, `synthesis_state.passed=True`, `errors=[]`.
