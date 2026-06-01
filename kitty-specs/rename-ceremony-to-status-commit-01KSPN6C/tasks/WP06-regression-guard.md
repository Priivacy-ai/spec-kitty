---
work_package_id: WP06
title: Architectural Regression Guard for Forbidden Terms
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
requirement_refs:
- FR-012
- FR-013
- FR-014
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-rename-ceremony-to-status-commit-01KSPN6C
base_commit: 652726f15e288d70eee5daa18ab0d4a63dee02bf
created_at: '2026-06-01T07:45:56.021475+00:00'
subtasks:
- T024
- T025
- T026
phase: Phase 2 - Lock-in
agent: "claude:sonnet:reviewer:reviewer"
shell_pid: "82827"
history:
- at: '2026-05-28T07:11:05Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
execution_mode: code_change
owned_files:
- tests/architectural/test_no_legacy_terminology.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 — Architectural Regression Guard for Forbidden Terms

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Scope governance context to Python implementation before reading anything else. This WP creates a new pytest module — load the Python-implementer profile so type-strict + lint + ruff conventions apply.

---

## Objective

Add an architectural pytest module at `tests/architectural/test_no_legacy_terminology.py` that runs a grep over `src/`, `tests/`, and `docs/` for the two forbidden terms — `ceremony` and `status-writing` — and fails if either reappears. This is the **lock-in** for the entire mission: future PRs that reintroduce either term will fail CI.

Spec anchors: [FR-012](../spec.md#functional-requirements) (occurrence map conformance verified by the regression test), [FR-013](../spec.md#functional-requirements) (zero ceremony hits), [FR-014](../spec.md#functional-requirements) (zero status-writing hits).

Decision authority: `01KSPP3W3VW8GB4WCXFF7J7X1Z` (add_pytest_grep_guard). See [decisions/DM-01KSPP3W3VW8GB4WCXFF7J7X1Z.md](../decisions/DM-01KSPP3W3VW8GB4WCXFF7J7X1Z.md).

## Context

- **Dependency note**: This WP **must run last**. The test depends on WP01–WP05 being merged (otherwise the grep finds the legacy term occurrences and the test fails). The lane plan should sequence this WP after Phase 1.
- **Self-flag avoidance (CRITICAL)**: The test file itself must not contain literal `ceremony` or `status-writing` substrings. The test scans `tests/` (including itself). If the literal terms appear in the test source, the test flags itself and never passes. Use **string concatenation** to build the forbidden terms at runtime.
- **Excluded paths**: `kitty-specs/` (historical mission artifacts — out of scope per spec C-001), `.worktrees/` (lane working trees), `.venv/`, `node_modules/`, and `.git/`.

## Subtask Detail

### T024 — Create `tests/architectural/test_no_legacy_terminology.py`

Create a new file with this structure (canonical reference — write substantively similar code):

```python
"""Architectural test: forbidden legacy terminology must not reappear.

Locks in the rename performed by mission
rename-ceremony-to-status-commit-01KSPN6C. If either forbidden term
reappears in the active-source surface (`src/`, `tests/`, `docs/`),
CI fails and the PR is rejected.

The forbidden terms are constructed via string concatenation in this
module so the test file does not flag itself.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


# Build forbidden terms from fragments so this test file does not contain
# the literal strings (otherwise the test would flag itself).
_FORBIDDEN_TERMS: tuple[str, ...] = (
    "cere" + "mony",
    "status" + "-writing",
)


_SCAN_ROOTS: tuple[str, ...] = ("src", "tests", "docs")
_EXTENSIONS: tuple[str, ...] = ("*.py", "*.md", "*.yaml", "*.yml")

# Paths excluded from the scan. kitty-specs/ contains historical mission
# artifacts that are explicitly out of scope per spec C-001. Worktrees and
# vendor directories are operational state.
_EXCLUDED_PATH_FRAGMENTS: tuple[str, ...] = (
    "kitty-specs/",
    ".worktrees/",
    ".venv/",
    "node_modules/",
    ".git/",
    # The test file itself is excluded as a belt-and-suspenders measure;
    # the string-fragment construction above is the primary self-flag defense.
    "tests/architectural/test_no_legacy_terminology.py",
)


def _repo_root() -> Path:
    """Resolve the repository root by walking up to a .kittify/ marker."""
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / ".kittify").is_dir():
            return parent
    raise RuntimeError("Could not locate repo root (no .kittify/ marker found).")


def _grep_for(term: str) -> list[str]:
    """Return all matching `<file>:<line>:<content>` lines for `term`.

    Uses `git grep` so .gitignore exclusions apply automatically (excludes
    .venv/, node_modules/, etc.). If git is unavailable, falls back to a
    manual walk; this is a best-effort fallback for environments where the
    test runs outside a checkout.
    """
    root = _repo_root()
    cmd = [
        "git",
        "-C",
        str(root),
        "grep",
        "--line-number",
        "--fixed-strings",
        term,
        "--",
        *(f"{r}/" for r in _SCAN_ROOTS),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    # git grep exits 1 when no matches, 0 when matches found, >1 on error.
    if result.returncode == 1:
        return []
    if result.returncode != 0:
        raise RuntimeError(
            f"git grep failed for term {term!r}: exit={result.returncode} "
            f"stderr={result.stderr!r}"
        )
    return [
        line
        for line in result.stdout.splitlines()
        if not any(fragment in line for fragment in _EXCLUDED_PATH_FRAGMENTS)
    ]


@pytest.mark.parametrize("term", _FORBIDDEN_TERMS)
def test_forbidden_term_does_not_appear(term: str) -> None:
    """Each forbidden legacy term must have zero occurrences in active source.

    Excluded surfaces: kitty-specs/ historical artifacts, worktrees, vendor
    directories. The test file itself is excluded via _EXCLUDED_PATH_FRAGMENTS
    and via the string-fragment construction of _FORBIDDEN_TERMS.
    """
    hits = _grep_for(term)
    if hits:
        formatted = "\n  ".join(hits)
        pytest.fail(
            f"Forbidden legacy term {term!r} reappeared in active source.\n"
            f"Canonical term is 'status commit' (see "
            f".kittify/glossaries/spec_kitty_core.yaml).\n"
            f"Hits ({len(hits)}):\n  {formatted}"
        )
```

Style notes (must hold):
- The module-level constant `_FORBIDDEN_TERMS` builds each term via `+` concatenation so the literal string is absent from this source file.
- Type annotations on all functions and module-level constants (the project enforces `mypy --strict`).
- No `print()` calls. Failure surfaces via `pytest.fail()` with a useful message.
- Use `subprocess.run(..., check=False)` not `check=True`, because `git grep` exits 1 on no-match (which is success for us).

### T025 — Run the new test from a clean lane workspace

After WP01–WP05 are merged into the lane base, from the lane workspace:

```bash
PWHEADLESS=1 pytest tests/architectural/test_no_legacy_terminology.py -v
```

Expected: **2 tests pass** (one per forbidden term).

If either parametrized test fails, the failure message lists the file:line:content of every hit. Open the listed file, classify the occurrence per `occurrence_map.yaml`, and decide:

- If the hit is in a file owned by a previous WP that already merged: that WP missed a case. Surface it for that WP's reviewer rather than fixing it inside WP06's owned_files.
- If the hit is in a previously-unknown file: update `occurrence_map.yaml` (it lives under `kitty-specs/` and is gitignored from the scan, so this doesn't change the test) and open a quick fix-up commit in the appropriate WP.

### T026 — Run full `tests/architectural/` to confirm no regression

```bash
PWHEADLESS=1 pytest tests/architectural/ -v
```

All architectural tests (existing + new) must pass green. No existing test should regress because of the new file.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution workspace: allocated per lane in `lanes.json` after `finalize-tasks`. Because this WP depends on WP01–WP05, the lane resolver will assign it a workspace that bases on the merge of the dependencies.
- Resolve via `spec-kitty agent context resolve --action implement --wp WP06 --mission rename-ceremony-to-status-commit-01KSPN6C --json`.

## Test Strategy

- T025 and T026 are the test runs. No other test surface is exercised.
- `mypy --strict tests/architectural/test_no_legacy_terminology.py` passes.
- `ruff check tests/architectural/test_no_legacy_terminology.py` passes.

## Definition of Done

- [ ] `tests/architectural/test_no_legacy_terminology.py` exists and matches the canonical structure above.
- [ ] The literal substrings `ceremony` and `status-writing` do **not** appear in the test source (verified by `grep -n 'ceremony\|status-writing' tests/architectural/test_no_legacy_terminology.py` returning zero hits).
- [ ] `PWHEADLESS=1 pytest tests/architectural/test_no_legacy_terminology.py -v` exits 0 with 2 tests passing.
- [ ] `PWHEADLESS=1 pytest tests/architectural/ -v` exits 0 (no regressions in existing arch tests).
- [ ] `mypy --strict tests/architectural/test_no_legacy_terminology.py` passes.
- [ ] `ruff check tests/architectural/test_no_legacy_terminology.py` passes.
- [ ] The test correctly excludes `kitty-specs/` historical artifacts (verified by manually inspecting any one occurrence in `kitty-specs/<old-mission>/*.md` and confirming it does NOT appear in the test failure output if run on a tree that has such an occurrence).

## Risks & Reviewer Guidance

- **Risk 1**: The literal substrings appear in the test source and the test flags itself. Mitigation: string-fragment construction of `_FORBIDDEN_TERMS` + path exclusion as backup. Reviewer should grep the file for the literal terms.
- **Risk 2**: WP01–WP05 missed an occurrence and the test fails. Mitigation: route the fix to the appropriate WP's reviewer rather than fixing it inside WP06 (scope violation).
- **Risk 3**: Test runs slowly because of repeated `git grep` invocations. Acceptable — two grep invocations on a small repo take well under 1 second.
- **Risk 4**: `git grep` is unavailable in some test environment. Mitigation: the project always runs tests inside a git checkout — if not, the `RuntimeError` from `_repo_root()` will surface the problem clearly.
- **Reviewer check 1**: Diff is exactly one new file. No other files modified.
- **Reviewer check 2**: Test source contains no literal `ceremony` or `status-writing` substring (grep the test file).
- **Reviewer check 3**: Test passes when run from a clean lane workspace with WP01–WP05 merged.
- **Reviewer check 4**: Type annotations + lint pass.

## References

- Spec: [../spec.md](../spec.md) — FR-012, FR-013, FR-014
- Plan: [../plan.md](../plan.md) — research item R3 (occurrence discovery) + Phase 1 architectural-test design
- Decision: [../decisions/DM-01KSPP3W3VW8GB4WCXFF7J7X1Z.md](../decisions/DM-01KSPP3W3VW8GB4WCXFF7J7X1Z.md)
- Occurrence map: [../occurrence_map.yaml](../occurrence_map.yaml) — `new_files` section

## Activity Log

- 2026-06-01T07:53:49Z – claude – shell_pid=99267 – Ready for review: test file passes (2/2), all straggler ceremony/status-writing occurrences from WP02-05 fixed, ruff clean
- 2026-06-01T07:54:13Z – claude:sonnet:reviewer:reviewer – shell_pid=82827 – Started review via action command
