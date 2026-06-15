---
work_package_id: WP03
title: Recovery-Message Branching in _require_current_analysis_report()
dependencies:
- WP02
requirement_refs:
- FR-004
- FR-005
tracker_refs: []
planning_base_branch: fix/analysis-report-coord-worktree-fix
merge_target_branch: fix/analysis-report-coord-worktree-fix
branch_strategy: Planning artifacts for this mission were generated on fix/analysis-report-coord-worktree-fix. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/analysis-report-coord-worktree-fix unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
- T015
agent: claude
shell_pid: '8055'
history:
- event: created
  at: '2026-06-15T19:57:30Z'
  actor: architect-alphonso
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/workflow.py
- tests/agent/test_workflow_review_lane_gate.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Update `_require_current_analysis_report()` in
`src/specify_cli/cli/commands/agent/workflow.py` to branch on the reason codes
returned by `check_analysis_report_current()` and emit exact, copy-pasteable
recovery commands for each error case.

**Prerequisite**: WP02 must be merged first. This WP imports
`ANALYSIS_REPORT_REASON_CARRIER_FORMAT` from `analysis_report.py`.

## Branch Strategy

- **Planning/execution branch**: `fix/analysis-report-coord-worktree-fix`
- **Merge target**: `fix/analysis-report-coord-worktree-fix`
- Run: `spec-kitty agent action implement WP03 --agent claude`

## Context

### Current `_require_current_analysis_report()` (lines 1072–1087 of `workflow.py`)

```python
def _require_current_analysis_report(feature_dir: Path, repo_root: Path, mission_slug: str) -> None:
    """Block implementation until `/spec-kitty.analyze` is persisted and fresh."""
    from specify_cli.analysis_report import check_analysis_report_current

    analysis_freshness = check_analysis_report_current(feature_dir, repo_root)
    if analysis_freshness.ok:
        return
    print("Error: analysis_report_required: /spec-kitty.analyze must be run before implementation.")
    if analysis_freshness.missing:
        print(f"  Missing: {analysis_freshness.path}")
    elif analysis_freshness.reason:
        print(f"  Reason: {analysis_freshness.reason}")
    if analysis_freshness.mismatches:
        print("  Stale inputs:")
        for artifact_name in sorted(analysis_freshness.mismatches):
            print(f"    - {artifact_name}")
    print(f"  Run: /spec-kitty.analyze --mission {mission_slug}")
    raise typer.Exit(1)
```

### Error Recovery Contract (source of truth)

The binding format for each branch is in
`kitty-specs/analysis-report-coord-worktree-fix-01KV6DC9/contracts/error-recovery-contract.md`.

Key outputs:

**Carrier-format branch** (`reason == "carrier_format_not_wrapped"`):
```
Error: analysis_report_required: /spec-kitty.analyze must be run before implementation.
  Reason: analysis-report.md is in carrier format (analysis-findings/v1) — written directly
          rather than via record-analysis. The implement gate requires the persisted
          outer-wrapper format (artifact_type: spec-kitty.analysis-report).
  Recovery: spec-kitty agent mission record-analysis --mission <mission_slug> --input-file <path>
```

**Missing-report branch** (`analysis_freshness.missing is True`):
```
Error: analysis_report_required: /spec-kitty.analyze must be run before implementation.
  Missing: <path>
  Run step 1: /spec-kitty.analyze
  Run step 2: spec-kitty agent mission record-analysis --mission <mission_slug> --input-file -
```

**Stale branch** (unchanged from current behavior):
```
Error: analysis_report_required: /spec-kitty.analyze must be run before implementation.
  Reason: stale_analysis_report
  Stale inputs:
    - <artifact_name>
  Run: /spec-kitty.analyze --mission <mission_slug>
```

**Catch-all** (unchanged):
```
Error: analysis_report_required: /spec-kitty.analyze must be run before implementation.
  Reason: <reason>
  Run: /spec-kitty.analyze --mission <mission_slug>
```

## Subtask Guidance

### T010 — Import `ANALYSIS_REPORT_REASON_CARRIER_FORMAT` in `workflow.py`

**Purpose**: Make the constant available in `_require_current_analysis_report()` without
adding a module-level import that would create a circular import (keep the import local,
matching the existing `from specify_cli.analysis_report import check_analysis_report_current`
pattern).

**Steps**:

1. In `_require_current_analysis_report()`, update the existing local import:
   ```python
   # BEFORE:
   from specify_cli.analysis_report import check_analysis_report_current

   # AFTER:
   from specify_cli.analysis_report import (
       ANALYSIS_REPORT_REASON_CARRIER_FORMAT,
       check_analysis_report_current,
   )
   ```

2. No other changes in this subtask.

**Files**: `src/specify_cli/cli/commands/agent/workflow.py`

**Validation**:
- [ ] Import resolves without error
- [ ] `mypy --strict` passes (no unresolved name errors)

---

### T011 — Add `carrier_format_not_wrapped` branch

**Purpose**: Emit the exact carrier-format recovery message when the reason code
indicates a carrier-format file is present.

**Steps**:

1. Replace the body of `_require_current_analysis_report()` with the branched version.
   The new structure:

```python
def _require_current_analysis_report(feature_dir: Path, repo_root: Path, mission_slug: str) -> None:
    """Block implementation until `/spec-kitty.analyze` is persisted and fresh."""
    from specify_cli.analysis_report import (
        ANALYSIS_REPORT_REASON_CARRIER_FORMAT,
        check_analysis_report_current,
    )

    analysis_freshness = check_analysis_report_current(feature_dir, repo_root)
    if analysis_freshness.ok:
        return

    # Header line is always emitted first.
    print("Error: analysis_report_required: /spec-kitty.analyze must be run before implementation.")

    if analysis_freshness.reason == ANALYSIS_REPORT_REASON_CARRIER_FORMAT:
        print(
            "  Reason: analysis-report.md is in carrier format (analysis-findings/v1) — written directly\n"
            "          rather than via record-analysis. The implement gate requires the persisted\n"
            "          outer-wrapper format (artifact_type: spec-kitty.analysis-report)."
        )
        print(f"  Recovery: spec-kitty agent mission record-analysis --mission {mission_slug} --input-file {analysis_freshness.path}")
    elif analysis_freshness.missing:
        print(f"  Missing: {analysis_freshness.path}")
        print("  Run step 1: /spec-kitty.analyze")
        print(f"  Run step 2: spec-kitty agent mission record-analysis --mission {mission_slug} --input-file -")
    elif analysis_freshness.mismatches:
        print(f"  Reason: {analysis_freshness.reason}")
        print("  Stale inputs:")
        for artifact_name in sorted(analysis_freshness.mismatches):
            print(f"    - {artifact_name}")
        print(f"  Run: /spec-kitty.analyze --mission {mission_slug}")
    else:
        if analysis_freshness.reason:
            print(f"  Reason: {analysis_freshness.reason}")
        print(f"  Run: /spec-kitty.analyze --mission {mission_slug}")

    raise typer.Exit(1)
```

2. Note: the `elif analysis_freshness.missing` branch now also emits the two-step recovery
   (T012 below) — do both T011 and T012 together in this single replacement.

**Files**: `src/specify_cli/cli/commands/agent/workflow.py`

**Validation**:
- [ ] `ruff check` and `mypy --strict` pass
- [ ] The function still raises `typer.Exit(1)` in all error branches

---

### T012 — Update `missing_analysis_report` branch to two-step recovery

This is implemented as part of T011 above (the `elif analysis_freshness.missing` branch).
No separate code change is needed — T012 is satisfied by the `elif missing` block in T011.

**Validation**:
- [ ] When `analysis_freshness.missing is True`, output contains `Run step 1:` and `Run step 2:`
- [ ] Output includes the mission slug in the `record-analysis` command

---

### T013 — Verify stale-inputs branch output is unchanged

**Purpose**: Confirm the existing stale-inputs test still passes after the restructuring.

**Steps**:

1. Run the existing test suite for `_require_current_analysis_report`:
   ```bash
   pytest tests/specify_cli/test_analysis_report.py -v -k "implement_gate"
   ```

2. If any existing test asserts on the old stale-inputs output format, verify the
   new `elif analysis_freshness.mismatches` branch produces identical output.

3. If a test explicitly checks for `  Run: /spec-kitty.analyze --mission <slug>`,
   confirm that line is still emitted in the stale branch.

**Files**: `tests/specify_cli/test_analysis_report.py` (read-only verification)

**Validation**:
- [ ] `pytest tests/specify_cli/test_analysis_report.py -v -k "implement_gate"` passes
- [ ] No pre-existing passing test begins failing after T011

---

### T014 — Unit test: carrier-format branch emits `Recovery:` line

**Purpose**: Assert the carrier-format error output matches the contract exactly.

**Steps**:

1. Add to `tests/specify_cli/test_analysis_report.py` (or `tests/agent/test_workflow_review_lane_gate.py`):

```python
def test_require_analysis_report_carrier_format_emits_recovery_command(tmp_path, capsys):
    """_require_current_analysis_report emits exact recovery command for carrier-format files."""
    from specify_cli.analysis_report import ANALYSIS_REPORT_FILENAME, ANALYSIS_REPORT_REASON_CARRIER_FORMAT
    # Import the function under test from workflow — or use monkeypatching
    # to control check_analysis_report_current's return value.
    import pytest
    from specify_cli.analysis_report import AnalysisFreshness

    feature_dir = tmp_path / "kitty-specs" / "my-mission"
    feature_dir.mkdir(parents=True)

    # Write a carrier-format file
    carrier_content = (
        "---\nschema: analysis-findings/v1\nfindings: []\ncounts:\n"
        "  critical: 0\n  high: 0\n  medium: 0\n  low: 0\nverdict_hint: ready\n---\n\nBody.\n"
    )
    (feature_dir / ANALYSIS_REPORT_FILENAME).write_text(carrier_content, encoding="utf-8")

    # Call _require_current_analysis_report directly (import from workflow)
    from specify_cli.cli.commands.agent.workflow import _require_current_analysis_report
    with pytest.raises(SystemExit):
        _require_current_analysis_report(feature_dir, tmp_path, "my-mission")

    captured = capsys.readouterr()
    assert "carrier_format_not_wrapped" not in captured.out  # reason code is NOT shown raw
    assert "carrier format (analysis-findings/v1)" in captured.out
    assert "Recovery: spec-kitty agent mission record-analysis" in captured.out
    assert "--mission my-mission" in captured.out
    assert str(feature_dir / ANALYSIS_REPORT_FILENAME) in captured.out
```

**Files**: `tests/specify_cli/test_analysis_report.py`

**Validation**:
- [ ] Test fails before T011 (old code emits `Reason: carrier_format_not_wrapped` not the full message)
- [ ] Test passes after T011

---

### T015 — Unit test: missing branch emits `Run step 1:` and `Run step 2:` lines

**Steps**:

1. Add:

```python
def test_require_analysis_report_missing_emits_two_step_recovery(tmp_path, capsys):
    """_require_current_analysis_report emits two-step recovery for missing report."""
    import pytest
    feature_dir = tmp_path / "kitty-specs" / "my-mission"
    feature_dir.mkdir(parents=True)
    # Do NOT write analysis-report.md

    from specify_cli.cli.commands.agent.workflow import _require_current_analysis_report
    with pytest.raises(SystemExit):
        _require_current_analysis_report(feature_dir, tmp_path, "my-mission")

    captured = capsys.readouterr()
    assert "Run step 1: /spec-kitty.analyze" in captured.out
    assert "Run step 2: spec-kitty agent mission record-analysis --mission my-mission --input-file -" in captured.out
```

**Files**: `tests/specify_cli/test_analysis_report.py`

**Validation**:
- [ ] Test fails before T012 (old code emits `Run: /spec-kitty.analyze --mission ...` not `Run step 1:`)
- [ ] Test passes after T012

---

## Definition of Done

- [ ] T010: `ANALYSIS_REPORT_REASON_CARRIER_FORMAT` imported in the local import block
- [ ] T011: `carrier_format_not_wrapped` branch emits full recovery message with file path
- [ ] T012: Missing branch emits `Run step 1:` / `Run step 2:` sequence
- [ ] T013: Stale-inputs output unchanged; existing tests pass
- [ ] T014: Carrier-format recovery command test passes
- [ ] T015: Missing-report two-step recovery test passes
- [ ] `ruff check` and `mypy --strict` pass on `workflow.py`
- [ ] `pytest tests/specify_cli/test_analysis_report.py tests/agent/test_workflow_review_lane_gate.py -v` pass

## Risks

- **Header line invariant**: The line `"Error: analysis_report_required: /spec-kitty.analyze must be run before implementation."` must appear in ALL branches. Do not omit it in the carrier-format branch.
- **`analysis_freshness.path` type**: It is a `Path` object. When interpolating into the recovery command string, `str(analysis_freshness.path)` or an f-string will produce the full absolute path. The test should verify the path appears in the output.
- **Import order**: The local import of `ANALYSIS_REPORT_REASON_CARRIER_FORMAT` must be added to the SAME `from specify_cli.analysis_report import ...` statement as `check_analysis_report_current`, not as a separate import line (Sonar/ruff may flag duplicate imports from the same module).

## Reviewer Guidance

- Check all four branches (carrier, missing, stale, catch-all) emit the header line first.
- Verify `Recovery:` (not `Run:`) is used for the carrier branch.
- Verify `Run step 1:` / `Run step 2:` is used for the missing branch.
- Verify the stale branch still emits `Run:` (not `Recovery:`) to preserve existing behavior.
- Confirm tests assert on the final output text, not on reason code strings.
