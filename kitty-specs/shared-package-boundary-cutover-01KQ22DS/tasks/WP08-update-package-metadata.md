---
work_package_id: WP08
title: Update Package Metadata and Lockfile
dependencies:
- WP02
- WP05
- WP07
requirement_refs:
- FR-006
- FR-007
- FR-008
- FR-013
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T030
- T031
- T032
- T033
agent: "claude:opus-4.7:python-implementer:implementer"
shell_pid: "71202"
history:
- at: '2026-04-25T10:31:00+00:00'
  actor: planner
  event: created
authoritative_surface: pyproject.toml
execution_mode: code_change
owned_files:
- pyproject.toml
- uv.lock
- constraints.txt
tags: []
---

# WP08 — Update Package Metadata and Lockfile

## Objective

Rewrite `pyproject.toml`, regenerate `uv.lock`, and delete `constraints.txt` so
the dependency contract reflects the new boundary: compatibility ranges for
events / tracker (no exact pins, no editable sources), no `spec-kitty-runtime`
listed anywhere, no paper-over constraints file.

## Context

Pre-cutover state of `pyproject.toml`:

```toml
dependencies = [
    ...
    "spec-kitty-events==4.0.0",   # exact pin
    # spec-kitty-runtime is intentionally not listed here: ...
    "spec-kitty-tracker==0.4.2",  # exact pin
    ...
]

[tool.uv.sources]
spec-kitty-events = { path = "../spec-kitty-events", editable = true }
```

Pre-cutover `constraints.txt` exists to paper over the `spec-kitty-runtime`
transitive `spec-kitty-events<4.0` pin conflict.

Post-cutover target:

```toml
dependencies = [
    ...
    "spec-kitty-events>=4.0.0,<5.0.0",
    "spec-kitty-tracker>=0.4,<0.5",
    ...
]

# [tool.uv.sources] — empty/absent for events/tracker/runtime.
```

`constraints.txt` deleted.

The architectural shape tests from WP03 (`test_pyproject_shape.py`) currently
xfail; this WP removes the xfail markers as it lands the satisfying changes.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: convergence (depends on WP02, WP05, WP07).

## Implementation

### Subtask T030 — Rewrite `pyproject.toml` deps and `[tool.uv.sources]`

**Purpose**: Apply the deps-and-sources changes.

**Steps**:

1. In `[project.dependencies]`:
   - Replace `"spec-kitty-events==4.0.0",` with `"spec-kitty-events>=4.0.0,<5.0.0",`.
   - Replace `"spec-kitty-tracker==0.4.2",` with `"spec-kitty-tracker>=0.4,<0.5",`.
   - Remove the multi-line comment that explains why `spec-kitty-runtime` is
     not listed (the explanation was specific to the hybrid model with
     vendored events; with the cutover complete, the absence is enforced by
     `tests/architectural/test_pyproject_shape.py` and needs no inline
     comment).
   - Update the comment block above `spec-kitty-events` (if any) to read:
     "spec-kitty-events / spec-kitty-tracker: external PyPI dependencies.
     Compatibility ranges follow the upstream public-surface contracts. Exact
     pinned versions live in uv.lock, not here."

2. In `[tool.uv.sources]`:
   - Remove the line:
     `spec-kitty-events = { path = "../spec-kitty-events", editable = true }`.
   - The whole `[tool.uv.sources]` table may now be empty / absent. Either is
     acceptable; prefer absence for clarity.

3. Verify the `[tool.hatch.metadata]` line `allow-direct-references = true`
   is still present (other parts of the build config rely on it).

4. Remove the `xfail` markers from
   `tests/architectural/test_pyproject_shape.py` (added in WP03). The shape
   assertions become live.

   **Cross-WP coordination**: this edits a file in WP03's authoritative
   surface. Acceptable because WP03 explicitly designed the xfail markers as
   "WP08 lands the cutover; remove this marker." Document the cross-WP edit
   in the WP08 PR description with a one-liner: "Removes WP03 xfail markers
   on `test_pyproject_shape.py` per its planned activation contract."

**Files**:
- `pyproject.toml`
- `tests/architectural/test_pyproject_shape.py` (xfail removal)

**Validation**:
- `tomllib.loads(open("pyproject.toml").read())` parses cleanly.
- `tests/architectural/test_pyproject_shape.py` passes (after xfail removal).

### Subtask T031 — Delete `constraints.txt` [P]

**Purpose**: The file's only reason to exist (papering over the
`spec-kitty-runtime` transitive events pin conflict) is gone.

**Steps**:

1. `git rm constraints.txt`.

2. Audit references:
   ```bash
   grep -rn "constraints.txt\|constraints\\.txt" .
   ```

   Anything outside `kitty-specs/` planning artifacts gets fixed in this WP.
   Likely candidates:
   - CI workflow files that reference `-c constraints.txt`.
   - `Makefile` targets.
   - `RELEASE_CHECKLIST.md`.
   - `docs/development/*` docs.

3. For each match: remove the `-c constraints.txt` flag (or the entire line
   if it was constraint-specific). The dependency resolution now works
   without it.

**Files**:
- `constraints.txt` (deletion).
- Any CI / docs / Makefile file that referenced it.

**Validation**:
- The file is gone.
- `grep` shows no live references in build / CI / docs paths.

### Subtask T032 — Regenerate `uv.lock`

**Purpose**: The lockfile must reflect the new compatibility ranges.

**Steps**:

1. Run:
   ```bash
   uv lock
   ```

2. Inspect the diff:
   ```bash
   git diff uv.lock
   ```

   Expected changes:
   - `spec-kitty-events` resolved version is still 4.0.0 (or the latest 4.x
     released — whichever uv picks).
   - `spec-kitty-tracker` resolved version is still 0.4.2 (or the latest 0.4.x).
   - No `path = ...` source for events.
   - `spec-kitty-runtime` is not present in the lockfile (it is not a dep).

3. If `uv lock` fails with a resolver error: investigate. Common cases:
   - A transitive dep requires `spec-kitty-events<4.0`. Solution: that dep's
     publisher needs to update; in the meantime, document the resolver
     conflict in a CHANGELOG entry and tighten the events range temporarily.
   - The local `path = "../spec-kitty-events"` source was being relied on for
     local development. Solution: the local override now lives in
     `docs/development/local-overrides.md` (created by WP10); in CI / on
     PyPI, the dep resolves cleanly.

**Files**: `uv.lock`.

**Validation**:
- `uv lock --check` passes (zero diff).
- `pip install -e .` (or `uv sync`) succeeds against the new lockfile in a
  clean checkout.

### Subtask T033 — `uv lock --check` zero diff

**Purpose**: Lockfile reproducibility (NFR-005).

**Steps**:

1. Run:
   ```bash
   uv lock --check
   ```

2. Expected: zero diff. If not zero diff, T032 was incomplete; rerun.

3. Run a clean install dry-run:
   ```bash
   uv sync --dry-run --no-install-project
   ```

   Expected: events and tracker resolve to versions inside their compatibility
   ranges; `spec-kitty-runtime` does not appear.

**Files**: None modified directly; this is a verification subtask.

**Validation**:
- `uv lock --check` is zero diff.
- Clean install resolves the expected dep set.

## Definition of Done

- [ ] All 4 subtasks complete with checkboxes ticked above (`mark-status` updates the per-WP checkboxes here as the WP advances).
- [ ] `pyproject.toml` lists events / tracker via compatibility ranges, no
  exact pins.
- [ ] `pyproject.toml` does not list `spec-kitty-runtime` as a dep.
- [ ] `[tool.uv.sources]` does not contain entries for events / tracker /
  runtime.
- [ ] `constraints.txt` does not exist.
- [ ] `uv.lock` is regenerated with the new ranges; `uv lock --check` is zero
  diff.
- [ ] WP03's `test_pyproject_shape.py` passes (xfail removed).
- [ ] No CI / Makefile / doc still references `constraints.txt`.

## Risks

- **Loose ranges pull an incompatible upstream release at install time.**
  Mitigation: WP07's consumer tests catch contract changes explicitly.
- **A transitive dep pinning `spec-kitty-events<4.0` exists somewhere.**
  Mitigation: T032's resolver-conflict step. If unfixable, scope a follow-up
  to address the offending transitive dep.

## Reviewer guidance

- Verify the ranges are exactly `>=4.0.0,<5.0.0` for events and `>=0.4,<0.5`
  for tracker.
- Verify `spec-kitty-runtime` does not appear anywhere in `pyproject.toml` or
  `uv.lock`.
- Verify `constraints.txt` is gone.
- Verify `uv lock --check` is zero diff.
- Verify WP03 xfail markers were removed and tests pass.

## Implementation command

```bash
spec-kitty agent action implement WP08 --agent <name> --mission shared-package-boundary-cutover-01KQ22DS
```

## Activity Log

- 2026-04-25T12:03:53Z – claude:opus-4.7:python-implementer:implementer – shell_pid=71202 – Started implementation via action command
- 2026-04-25T12:06:37Z – claude:opus-4.7:python-implementer:implementer – shell_pid=71202 – pyproject.toml: events/tracker switched to compatibility ranges; runtime absent; [tool.uv.sources] removed. constraints.txt deleted. uv.lock generated (events 4.0.0, tracker 0.4.2, no runtime) and tracked via .gitignore exception. WP03 xfail markers removed; 12/12 architectural tests pass. Refs FR-006, FR-007, FR-008, FR-013, NFR-005.
