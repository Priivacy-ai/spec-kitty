---
work_package_id: WP02
title: Named Reason Code for Carrier-Format Files
dependencies: []
requirement_refs:
- FR-003
tracker_refs: []
planning_base_branch: fix/analysis-report-coord-worktree-fix
merge_target_branch: fix/analysis-report-coord-worktree-fix
branch_strategy: Planning artifacts for this mission were generated on fix/analysis-report-coord-worktree-fix. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/analysis-report-coord-worktree-fix unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-analysis-report-coord-worktree-fix-01KV6DC9
base_commit: fda8135534a6400ff1048afcde9415ea77be52c6
created_at: '2026-06-15T20:40:55.472272+00:00'
subtasks:
- T005
- T006
- T007
- T008
- T009
agent: claude
shell_pid: '51286'
history:
- event: created
  at: '2026-06-15T19:57:30Z'
  actor: architect-alphonso
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/analysis_report.py
- tests/specify_cli/test_analysis_report.py
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

Add a stable named reason constant `ANALYSIS_REPORT_REASON_CARRIER_FORMAT` to
`src/specify_cli/analysis_report.py` and a carrier-detection branch in
`check_analysis_report_current()` so the implement gate can distinguish
carrier-format files (written directly by agents) from files with unrelated
frontmatter formats.

This is the data-model change described in `data-model.md` — adding the new
`carrier_format_not_wrapped` reason to the taxonomy without changing the
`AnalysisFreshness` dataclass shape.

## Branch Strategy

- **Planning/execution branch**: `fix/analysis-report-coord-worktree-fix`
- **Merge target**: `fix/analysis-report-coord-worktree-fix`
- Run: `spec-kitty agent action implement WP02 --agent claude`

## Context

### Relevant constants (already in `analysis_report.py`)

```python
FINDINGS_SCHEMA_V1 = "analysis-findings/v1"        # carrier schema key
ANALYSIS_REPORT_ARTIFACT_TYPE = "spec-kitty.analysis-report"  # outer-wrapper key
```

### `check_analysis_report_current()` current gate (lines 452–461)

```python
if frontmatter.get("artifact_type") != ANALYSIS_REPORT_ARTIFACT_TYPE:
    return AnalysisFreshness(
        ok=False,
        path=path,
        stale=True,
        missing=False,
        reason="invalid_analysis_report_artifact_type",
        mismatches={},
    )
```

The new carrier-detection branch is inserted BEFORE this block.

### How a carrier-format file looks

```yaml
---
schema: analysis-findings/v1
findings:
  - id: F001
    severity: medium
    category: spec-coverage
    summary: "Missing NFR for latency"
counts:
  critical: 0
  high: 0
  medium: 1
  low: 0
verdict_hint: ready
---
(report body follows)
```

Note: `schema` key (not `artifact_type`), `analysis-findings/v1` value.

### How the outer-wrapper format looks

```yaml
---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: my-mission
...
---
```

Note: `artifact_type` key (not `schema`).

## Subtask Guidance

### T005 — Add `ANALYSIS_REPORT_REASON_CARRIER_FORMAT` constant

**Purpose**: Establish a stable, importable string constant for the new reason code
so both `analysis_report.py` (setter) and `workflow.py` (matcher) reference the same
string without hardcoding it.

**Steps**:

1. In `src/specify_cli/analysis_report.py`, locate the block of module-level constants
   near lines 28–31:
   ```python
   ANALYSIS_REPORT_FILENAME = "analysis-report.md"
   ANALYSIS_REPORT_ARTIFACT_TYPE = "spec-kitty.analysis-report"
   ANALYSIS_REPORT_COMMAND = "/spec-kitty.analyze"
   _HASH_INPUTS = ("spec.md", "plan.md", "tasks.md")
   ```

2. Add the new constant immediately after the existing ones:
   ```python
   ANALYSIS_REPORT_REASON_CARRIER_FORMAT = "carrier_format_not_wrapped"
   ```

3. No other changes in this subtask.

**Files**: `src/specify_cli/analysis_report.py`

**Validation**:
- [ ] `from specify_cli.analysis_report import ANALYSIS_REPORT_REASON_CARRIER_FORMAT` works
- [ ] `ruff check src/specify_cli/analysis_report.py` passes

---

### T006 — Add carrier-detection branch in `check_analysis_report_current()`

**Purpose**: Return the new named reason when a carrier-format file is detected,
before the generic `artifact_type` check can fire.

**Steps**:

1. In `check_analysis_report_current()` (around line 453), locate the `artifact_type` check:
   ```python
   if frontmatter.get("artifact_type") != ANALYSIS_REPORT_ARTIFACT_TYPE:
       return AnalysisFreshness(
           ok=False, path=path, stale=True, missing=False,
           reason="invalid_analysis_report_artifact_type",
           mismatches={},
       )
   ```

2. Insert the carrier-detection block BEFORE this check:
   ```python
   if frontmatter.get("schema") == FINDINGS_SCHEMA_V1:
       return AnalysisFreshness(
           ok=False,
           path=path,
           stale=True,
           missing=False,
           reason=ANALYSIS_REPORT_REASON_CARRIER_FORMAT,
           mismatches={},
       )
   ```

3. The ordering is critical:
   - First: `FrontmatterError` check (already exists)
   - Second: **carrier-format check** (new — T006)
   - Third: `artifact_type` check (already exists)
   - Fourth: `input_artifacts` check (already exists)
   - Fifth: hash comparison (already exists)

**Files**: `src/specify_cli/analysis_report.py`

**Validation**:
- [ ] A file with `schema: analysis-findings/v1` frontmatter returns `reason="carrier_format_not_wrapped"`
- [ ] A file with `artifact_type: spec-kitty.analysis-report` still returns `ok=True` (passes)
- [ ] A file with neither `schema` nor `artifact_type` returns `reason="invalid_analysis_report_artifact_type"`
- [ ] `ruff check` and `mypy --strict` pass on the modified file

---

### T007 — Unit test: carrier-format file returns `carrier_format_not_wrapped`

**Purpose**: Directly test the new branch added in T006.

**Steps**:

1. Add to `tests/specify_cli/test_analysis_report.py`:

```python
def test_implement_gate_detects_carrier_format_file(tmp_path):
    """check_analysis_report_current returns carrier_format_not_wrapped for v1 carrier files."""
    from specify_cli.analysis_report import (
        ANALYSIS_REPORT_FILENAME,
        ANALYSIS_REPORT_REASON_CARRIER_FORMAT,
        check_analysis_report_current,
    )

    feature_dir = tmp_path / "kitty-specs" / "my-mission"
    feature_dir.mkdir(parents=True)

    # Write a carrier-format file (analysis-findings/v1 schema, not outer-wrapper)
    carrier_content = (
        "---\n"
        "schema: analysis-findings/v1\n"
        "findings: []\n"
        "counts:\n"
        "  critical: 0\n"
        "  high: 0\n"
        "  medium: 0\n"
        "  low: 0\n"
        "verdict_hint: ready\n"
        "---\n\n"
        "Report body.\n"
    )
    (feature_dir / ANALYSIS_REPORT_FILENAME).write_text(carrier_content, encoding="utf-8")

    result = check_analysis_report_current(feature_dir, tmp_path)

    assert result.ok is False
    assert result.stale is True
    assert result.missing is False
    assert result.reason == ANALYSIS_REPORT_REASON_CARRIER_FORMAT
```

**Files**: `tests/specify_cli/test_analysis_report.py`

**Validation**:
- [ ] Test fails before T006 is applied (returns `invalid_analysis_report_artifact_type`)
- [ ] Test passes after T006 is applied (returns `carrier_format_not_wrapped`)

---

### T008 — Regression test: outer-wrapper format still returns `ok=True`

**Purpose**: Confirm the new carrier-detection branch does not intercept valid outer-wrapper files.

**Steps**:

1. The existing `test_implement_gate_allows_current_analysis_report` in `test_analysis_report.py`
   already covers this. Run it and verify it still passes after T006.

2. If the existing test does not exist or is insufficient, add:

```python
def test_implement_gate_passes_valid_outer_wrapper(tmp_path):
    """check_analysis_report_current passes files with artifact_type: spec-kitty.analysis-report."""
    # Write a properly-formed outer-wrapper file (use write_analysis_report to produce one)
    ...
    result = check_analysis_report_current(feature_dir, tmp_path)
    assert result.ok is True
```

**Files**: `tests/specify_cli/test_analysis_report.py`

**Validation**:
- [ ] `test_implement_gate_allows_current_analysis_report` passes
- [ ] No existing test that passes before T006 begins failing after T006

---

### T009 — Regression test: arbitrary frontmatter returns `invalid_analysis_report_artifact_type`

**Purpose**: Verify that files with unrelated frontmatter (e.g., a markdown file with
a YAML block that is neither a carrier nor an outer-wrapper) still fall through to the
generic reason code, not the new carrier reason.

**Steps**:

1. Add a test that writes a file with arbitrary frontmatter (no `schema` key, no `artifact_type` key):

```python
def test_implement_gate_returns_generic_reason_for_arbitrary_frontmatter(tmp_path):
    feature_dir = tmp_path / "kitty-specs" / "my-mission"
    feature_dir.mkdir(parents=True)
    (feature_dir / "analysis-report.md").write_text(
        "---\ntitle: Some Random File\nauthor: Alice\n---\n\nBody.\n",
        encoding="utf-8",
    )
    result = check_analysis_report_current(feature_dir, tmp_path)
    assert result.reason == "invalid_analysis_report_artifact_type"
```

**Files**: `tests/specify_cli/test_analysis_report.py`

**Validation**:
- [ ] Test passes (arbitrary frontmatter does not trigger `carrier_format_not_wrapped`)
- [ ] `pytest tests/specify_cli/test_analysis_report.py -v` all pass

---

## Definition of Done

- [ ] T005: `ANALYSIS_REPORT_REASON_CARRIER_FORMAT = "carrier_format_not_wrapped"` constant defined
- [ ] T006: Carrier-detection branch in `check_analysis_report_current()` before `artifact_type` check
- [ ] T007: New test `test_implement_gate_detects_carrier_format_file` passes
- [ ] T008: Existing outer-wrapper regression test still passes
- [ ] T009: Arbitrary-frontmatter regression test passes
- [ ] `ruff check` and `mypy --strict` pass with zero issues
- [ ] `pytest tests/specify_cli/test_analysis_report.py -v` all pass

## Risks

- **Branch ordering**: The carrier check must come before the `artifact_type` check. Inserting it after would mean carrier-format files (which lack `artifact_type`) fall through to the generic reason first — defeating the purpose.
- **FINDINGS_SCHEMA_V1 constant**: Ensure the comparison uses the existing `FINDINGS_SCHEMA_V1 = "analysis-findings/v1"` constant, not a hardcoded string.

## Reviewer Guidance

- Verify the branch ordering: carrier check before `artifact_type` check.
- Verify `ANALYSIS_REPORT_REASON_CARRIER_FORMAT` is exported (no leading underscore).
- Verify T007 explicitly checks that `.reason == ANALYSIS_REPORT_REASON_CARRIER_FORMAT` (string comparison).
- Confirm T009 uses frontmatter with no `schema` key to test the generic fallthrough.
