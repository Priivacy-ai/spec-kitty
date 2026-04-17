---
work_package_id: WP03
title: Neutrality Regression Test
dependencies:
- WP02
requirement_refs:
- FR-010
- FR-011
- NFR-001
- NFR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
phase: Phase 2 — Regression gates
assignee: ''
agent: "claude:opus-4-6:reviewer:reviewer"
shell_pid: "11649"
history:
- timestamp: '2026-04-17T09:03:02Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: tests/charter/test_neutrality_lint.py
execution_mode: code_change
owned_files:
- tests/charter/test_neutrality_lint.py
tags: []
---

# Work Package Prompt: WP03 – Neutrality Regression Test

## Objective

Wire the WP02 scanner into a pytest module that gates the repository. Three things: (1) assert baseline is clean, (2) prove a synthetic regression is caught (SC-005 fault-injection), and (3) bound runtime at ≤ 5 seconds (NFR-001).

## Context

WP02 delivered `charter.neutrality.run_neutrality_lint`. This WP delivers the test harness that calls it and makes the result block CI. The contract is at `contracts/neutrality-lint-contract.md` (C-3); follow it closely.

## Branch Strategy

Planning base branch is `main`; merge target is `main`. Execution worktree path is resolved by the runtime from `lanes.json`.

## Implementation Sketch

### Subtask T010 — Author `test_generic_artifacts_are_neutral`

**File**: `tests/charter/test_neutrality_lint.py` (new, ~140 lines).

```python
"""Regression gate: generic-scoped doctrine artifacts contain no banned terms.

Contract: kitty-specs/charter-ownership-consolidation-and-neutrality-hardening-01KPD880/
         contracts/neutrality-lint-contract.md (C-3)
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from charter.neutrality import run_neutrality_lint


def _format_failure(result) -> str:
    lines = ["Neutrality lint failed.", "", "HITS:"]
    for h in result.hits:
        lines.append(f"  {h.file}:{h.line}:{h.column} — term_id={h.term_id} matched={h.match!r}")
    if result.stale_allowlist_entries:
        lines.append("")
        lines.append("STALE ALLOWLIST ENTRIES:")
        for p in result.stale_allowlist_entries:
            lines.append(f"  {p}  (no file resolves this path)")
    lines += [
        "",
        "Remediation for each HIT:",
        "  (a) Remove the banned term from the file, OR",
        "  (b) Add the file's path to src/charter/neutrality/language_scoped_allowlist.yaml",
        "      if the file is INTENTIONALLY language-scoped.",
        "",
        "Remediation for STALE entries:",
        "  Delete the stale path from language_scoped_allowlist.yaml, or restore the expected file.",
    ]
    return "\n".join(lines)


def test_generic_artifacts_are_neutral() -> None:
    result = run_neutrality_lint()
    assert result.passed, _format_failure(result)
```

**Failure-message contract**: the string produced by `_format_failure` MUST include:

- one line per hit with file:line:column, term id, and matched text (exactly what the contract specifies);
- a remediation block naming both remediation options (remove term OR allowlist the path);
- a separate remediation note for stale allowlist entries.

Reviewers will fail the WP if the failure message is generic ("lint failed") without pointing to specific files or remediation.

### Subtask T011 — Fault-injection test (SC-005)

Add a second test case that proves the lint would catch a regression:

```python
def test_fault_injection_catches_regression(tmp_path: Path) -> None:
    # Create a synthetic "generic" artifact that would fail the lint.
    fake_root = tmp_path / "src" / "doctrine" / "fake"
    fake_root.mkdir(parents=True)
    (fake_root / "generic.md").write_text(
        "To run tests, invoke pytest on the command line.\n"
    )

    # Point the scanner at the tmp tree only, with no allowlist coverage.
    result = run_neutrality_lint(
        repo_root=tmp_path,
        scan_roots=[tmp_path / "src" / "doctrine"],
    )
    assert not result.passed
    assert any(hit.term_id == "PY-001" for hit in result.hits), (
        f"Expected PY-001 ('pytest') hit; got hits={result.hits}"
    )
```

This test is what SC-005 demands: a deliberate regression that the lint catches. It also doubles as coverage for the scanner's hit-recording logic.

### Subtask T012 — Runtime budget (NFR-001)

```python
def test_runtime_budget() -> None:
    start = time.perf_counter()
    run_neutrality_lint()
    elapsed = time.perf_counter() - start
    assert elapsed < 5.0, f"Neutrality lint took {elapsed:.2f}s, budget is 5s"
```

If this fails on a typical dev machine, the scanner in WP02 has a performance bug (e.g., compiling regexes inside the inner loop). Fix the scanner, not the test.

### Subtask T013 — Coverage ≥ 90% on `lint.py`

Run:

```bash
pytest tests/charter/test_neutrality_lint.py --cov=src/charter/neutrality --cov-report=term-missing
```

Verify coverage on `src/charter/neutrality/lint.py` is ≥ 90%. Any under-tested branches must be covered by additional targeted tests in this WP. Common gaps:

- Regex vs literal dispatch.
- Glob vs literal allowlist matching.
- Stale-allowlist-entry detection.
- Column number accuracy in hits.

Add parametrized unit tests if the scanner helpers are not covered by the three integration tests above.

## Files

- **New**: `tests/charter/test_neutrality_lint.py`

## Definition of Done

- [ ] Test file exists with the three test cases above (plus any coverage top-ups).
- [ ] `pytest tests/charter/test_neutrality_lint.py -v` passes.
- [ ] Fault-injection test fails **without** the scanner fix (verify by temporarily breaking the scanner — then restore).
- [ ] Runtime on a typical dev machine is well under 5 seconds (report the actual number in the PR body).
- [ ] Coverage report shows ≥ 90% on `src/charter/neutrality/lint.py`.
- [ ] `mypy --strict tests/charter/test_neutrality_lint.py` passes.

## Risks

- **Scanner performance**: if WP02's scanner is slow (e.g., re-opens files for each term), T012 will catch it. Pushing back on WP02 is the right response; do not bump the 5-second budget.
- **Hidden hits on first run**: if WP02's allowlist missed a file, this test will surface it. Do not quietly add to the allowlist — investigate first.
- **Tmp-path scan root isolation**: `run_neutrality_lint(repo_root=tmp_path, scan_roots=[...])` must NOT fall back to reading the real repo's banned-terms YAML. Verify during T011 that the scanner accepts all path inputs as explicit overrides and doesn't silently prefer real paths.

## Reviewer Checklist

- [ ] All three contract test cases present: baseline pass, fault-injection, runtime budget.
- [ ] Failure message matches the contract format (file:line:col, term id, remediation block).
- [ ] Fault-injection uses `tmp_path`, never pollutes the real repo.
- [ ] Coverage ≥ 90% on `lint.py`.
- [ ] Tests run under 5 s combined on the reviewer's machine.

## Activity Log

- 2026-04-17T09:44:21Z – claude:sonnet-4-6:implementer:implementer – shell_pid=11041 – Started implementation via action command
- 2026-04-17T09:47:10Z – claude:sonnet-4-6:implementer:implementer – shell_pid=11041 – Ready for review: neutrality regression test gate wired via charter.neutrality.run_neutrality_lint. 7 tests (baseline, fault-injection, allowlist literal/glob, stale entries, regex column accuracy, runtime budget). Baseline passes (0 hits, 0 stale), coverage 93% on lint.py, mypy --strict clean, runtime ~0.8s. (--force used: only uncommitted file is gitignored dossier snapshot.)
- 2026-04-17T09:47:40Z – claude:opus-4-6:reviewer:reviewer – shell_pid=11649 – Started review via action command
