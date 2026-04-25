---
work_package_id: WP06
title: Lock the Deletion with Packaging Assertions
dependencies:
- WP05
requirement_refs:
- FR-012
- FR-019
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
history:
- at: '2026-04-25T10:31:00+00:00'
  actor: planner
  event: created
authoritative_surface: tests/contract/test_packaging_no_vendored_events.py
execution_mode: code_change
owned_files:
- tests/contract/test_packaging_no_vendored_events.py
tags: []
---

# WP06 — Lock the Deletion with Packaging Assertions

## Objective

Make C-002 (no vendored events tree) mechanically enforced at the wheel-shape
level so any future PR that re-introduces the vendored tree fails CI
immediately.

## Context

WP05 deleted `src/specify_cli/spec_kitty_events/`. WP03 added an import-graph
rule that catches `specify_cli.spec_kitty_events.*` imports. WP06 closes the
last gap: a PR could reintroduce the directory with files that are not yet
imported, and that would slip through the import-graph rule. The wheel-shape
and filesystem assertions catch that case.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: lane B (depends on WP05).

## Implementation

### Subtask T025 — Wheel-shape assertion

**Purpose**: Build the wheel and assert the resulting archive does not
contain `specify_cli/spec_kitty_events/` paths. This is FR-019's
verification.

**Steps**:

1. Create `tests/contract/test_packaging_no_vendored_events.py`:

   ```python
   """Wheel-shape assertion: no vendored spec-kitty-events tree.

   Per FR-019 / C-002 of mission shared-package-boundary-cutover-01KQ22DS,
   the built wheel must not ship a vendored copy of spec-kitty-events under
   specify_cli/spec_kitty_events/. The events package is consumed via the
   public PyPI dependency only.
   """
   from __future__ import annotations

   import shutil
   import subprocess
   import sys
   import zipfile
   from pathlib import Path

   import pytest

   pytestmark = [pytest.mark.distribution, pytest.mark.contract]


   REPO_ROOT = Path(__file__).resolve().parents[2]


   @pytest.fixture(scope="module")
   def built_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
       """Build a wheel into a tmp dir and return its path."""
       tmp = tmp_path_factory.mktemp("wheel-build")
       subprocess.run(
           [sys.executable, "-m", "build", "--wheel", "--outdir", str(tmp)],
           cwd=REPO_ROOT,
           check=True,
           capture_output=True,
       )
       wheels = list(tmp.glob("spec_kitty_cli-*.whl"))
       assert len(wheels) == 1, f"expected exactly one wheel, found {wheels}"
       return wheels[0]


   def test_wheel_does_not_contain_vendored_spec_kitty_events(built_wheel: Path) -> None:
       with zipfile.ZipFile(built_wheel) as z:
           offending = [
               name
               for name in z.namelist()
               if "specify_cli/spec_kitty_events/" in name
           ]
       assert not offending, (
           f"Wheel {built_wheel.name} contains vendored events paths: "
           f"{offending[:5]}{'...' if len(offending) > 5 else ''}. "
           "Per C-002 / FR-019, the CLI must not vendor or mirror the events package."
       )
   ```

2. The test is marked `@pytest.mark.distribution` and `@pytest.mark.contract`
   so it runs in the distribution / nightly gate, not the fast gate. It is
   slow (full wheel build) but cheap to interpret.

3. Add a corresponding entry to `tests/contract/conftest.py` if needed for
   marker registration; reuse the existing `distribution` marker definition
   from the project's `pyproject.toml` (already declared).

**Files**: `tests/contract/test_packaging_no_vendored_events.py`.

**Validation**:
- The test passes against the post-WP05 tree.
- The test fails when a fake `src/specify_cli/spec_kitty_events/__init__.py`
  is reintroduced (manual probe; do not commit the regression).

### Subtask T026 — Filesystem-state assertion in the architectural suite [P]

**Purpose**: A fast, unit-gate assertion that the directory does not exist on
disk. Complementary to the wheel-shape assertion (which is slow).

**Steps**:

1. Add to `tests/architectural/test_shared_package_boundary.py` (owned by
   WP03; this WP extends the file via cross-WP collaboration):

   ```python
   def test_vendored_events_tree_does_not_exist_on_disk():
       """C-002 / FR-003: src/specify_cli/spec_kitty_events/ must not exist.

       This is the cheapest possible enforcement of the deletion: a one-stat
       check. The wheel-shape assertion (test_packaging_no_vendored_events)
       is the full distribution gate; this is the fast-gate companion.
       """
       from pathlib import Path
       repo_root = Path(__file__).resolve().parents[2]
       vendored = repo_root / "src" / "specify_cli" / "spec_kitty_events"
       assert not vendored.exists(), (
           f"Vendored events tree was reintroduced at {vendored}. "
           "Per FR-003 / C-002 of shared-package-boundary-cutover-01KQ22DS, "
           "the CLI must consume events through the public spec_kitty_events "
           "PyPI package only."
       )
   ```

2. **Cross-WP coordination**: this subtask edits a file owned by WP03
   (`tests/architectural/test_shared_package_boundary.py`). Coordinate by:
   - Including the file in WP06's `owned_files` for the duration of this WP
     (yes, this means temporarily extending ownership). Document in the WP06
     PR description: "Extends WP03's authoritative surface with one assertion
     scoped to FR-003 / C-002 enforcement."
   - Alternatively (preferred if possible at finalize-tasks time): add the
     filesystem assertion to a NEW file in WP06's authoritative surface,
     `tests/contract/test_packaging_no_vendored_events.py` — i.e. include the
     filesystem assertion in the WP06-authoritative file, not in
     `test_shared_package_boundary.py`. This avoids the ownership overlap.

   **Decision**: Use the alternative — keep all of WP06's logic in its own
   file. The filesystem assertion sits in
   `tests/contract/test_packaging_no_vendored_events.py` as a fast unit-gated
   test (no marker), distinct from the wheel-shape test (marker-gated). This
   makes ownership clean.

3. Refactor T025 to also include the fast unit-gated filesystem assertion in
   the same file. The file ends up with two test functions:
   - `test_vendored_events_tree_does_not_exist_on_disk` (no marker; fast unit
     gate).
   - `test_wheel_does_not_contain_vendored_spec_kitty_events` (distribution
     marker; nightly gate).

**Files**: `tests/contract/test_packaging_no_vendored_events.py` (extended
from T025, not a new file).

**Validation**:
- Filesystem assertion passes on the post-WP05 tree.
- Filesystem assertion fails if `mkdir -p src/specify_cli/spec_kitty_events;
  touch src/specify_cli/spec_kitty_events/__init__.py` is run (manual probe;
  do not commit the regression).
- Filesystem assertion runs in <1s (fast gate).

## Definition of Done

- [ ] All 2 subtasks complete with checkboxes ticked above (`mark-status` updates the per-WP checkboxes here as the WP advances).
- [ ] `tests/contract/test_packaging_no_vendored_events.py` exists with both
  the fast filesystem assertion and the distribution-gated wheel-shape
  assertion.
- [ ] Both assertions pass against the post-WP05 tree.
- [ ] Both assertions fail when the vendored tree is artificially
  reintroduced.

## Risks

- **Wheel build is slow.** Mitigation: marker-gate the wheel-shape test;
  only run in distribution / nightly gate, not on every PR's fast gate.
- **A future contributor adds a non-Python file to
  `src/specify_cli/spec_kitty_events/` thinking it isn't covered.**
  Mitigation: the filesystem assertion checks `vendored.exists()`, not just
  the presence of `.py` files.

## Reviewer guidance

- Verify both assertions live in the same file.
- Verify the markers are correct (filesystem = no marker; wheel-shape =
  distribution).
- Verify the filesystem test runs in <1s.
- Verify the wheel-shape test passes when run against the post-WP05 tree.

## Implementation command

```bash
spec-kitty agent action implement WP06 --agent <name> --mission shared-package-boundary-cutover-01KQ22DS
```
