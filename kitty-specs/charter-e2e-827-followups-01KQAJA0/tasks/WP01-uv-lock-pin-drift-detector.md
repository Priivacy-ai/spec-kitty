---
work_package_id: WP01
title: '#848 — uv.lock vs installed shared-package drift detector'
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
agent: claude
history:
- at: '2026-04-28T19:59:16Z'
  actor: planner
  note: Initial work package created from /spec-kitty.tasks.
agent_profile: python-pedro
authoritative_surface: tests/architectural/
execution_mode: code_change
mission_id: 01KQAJA02YZ2Q7SH5WND713HKA
mission_slug: charter-e2e-827-followups-01KQAJA0
model: claude-sonnet-4-6
owned_files:
- tests/architectural/test_uv_lock_pin_drift.py
- docs/development/review-gates.md
- kitty-specs/**/issue-matrix.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load the assigned agent profile so your behavior, tone, and boundaries match what this work package expects:

```
/ad-hoc-profile-load python-pedro
```

This sets your role to `implementer`, scopes your editing surface to the `owned_files` declared in the frontmatter above, and applies the Python-specialist authoring standards. Do not skip this step.

## Objective

Add a deterministic, fast architectural test that detects drift between `uv.lock` and installed versions of governed shared packages (`spec-kitty-events`, `spec-kitty-tracker`). Document the documented sync command (`uv sync --frozen`) in one place. Correct any stale issue-matrix language that mislabels the underlying risk as "verified-already-fixed".

This is the **first** of four work packages in mission `charter-e2e-827-followups-01KQAJA0` and the operator-mandated first WP to land in the PR. Without this hygiene check, the other three WPs' verification gates can fail on environment drift instead of real defects.

## Scope guardrail (binding)

Per Constraint **C-004** in [`spec.md`](../spec.md), this WP is **environment/review-gate hygiene only**. It MUST NOT:

- Modify `pyproject.toml` `[project.dependencies]` shape, ranges, or pins.
- Modify `[tool.uv.sources]`.
- Modify `uv.lock` or its semantics.
- Introduce new dependency-management abstractions, scripts, or replacement tooling.
- Change the existing compat-range vs exact-pin policy.

You are adding **one new pytest** plus **one documentation page**. If a reviewer cannot summarize your diff in those terms, the WP has crept beyond scope.

## Context

- The shared-package boundary cutover (mission `shared-package-boundary-cutover-01KQ22DS`) consumes `spec-kitty-events` and `spec-kitty-tracker` from PyPI. Compatibility ranges live in `pyproject.toml`; exact pins live in `uv.lock`.
- The existing `clean-install-verification` CI job (`.github/workflows/ci-quality.yml`) catches drift in CI, but local pre-PR review-gate runs that bypass the CI job can still fail on drift in confusing ways.
- The pattern for architectural tests is established: `tests/architectural/test_pyproject_shape.py`, `test_shared_package_boundary.py`, `test_no_runtime_pypi_dep.py`, etc.
- All architectural tests run under a shared budget cap of ≤30s total (NFR-006 in the shared-package-boundary mission). One more parser-level test is well within budget.

## Detailed guidance per subtask

### Subtask T001 — Author `tests/architectural/test_uv_lock_pin_drift.py`

**Purpose**: Detect `uv.lock` vs installed-package drift before a developer opens a PR.

**Steps**:

1. Create `tests/architectural/test_uv_lock_pin_drift.py`.
2. Module structure:
   - Constant: `GOVERNED_PACKAGES = ("spec-kitty-events", "spec-kitty-tracker")`. (Centralized; adding a future package is a one-line edit.)
   - Constant: `SYNC_COMMAND = "uv sync --frozen"`.
   - Helper: `_resolve_uv_lock_versions(lock_path: Path) -> dict[str, str]` — parse `uv.lock` (TOML) and return `{package_name: locked_version}` for each governed package present.
   - Helper: `_installed_version(pkg: str) -> str | None` — wrap `importlib.metadata.version(pkg)` and return None if not installed (very rare in dev envs but should not crash the test).
   - Test function: `test_uv_lock_matches_installed_versions()`.
3. Test logic:
   - Locate repo root deterministically (e.g. via existing pytest fixture or by walking up from `__file__`).
   - Parse `uv.lock` once.
   - For each governed package, compare locked vs installed.
   - Collect mismatches as `(package, locked_version, installed_version)` tuples.
   - If mismatches is non-empty, raise `pytest.fail(...)` with a multi-line message:
     ```
     uv.lock vs installed-package drift detected for governed shared packages:
       - spec-kitty-events: locked=X.Y.Z, installed=A.B.C
       - spec-kitty-tracker: locked=X.Y.Z, installed=A.B.C
     Run the documented pre-review/pre-PR sync command from the repository root:
       uv sync --frozen
     This restores the environment to match uv.lock without re-resolving the graph.
     See docs/development/review-gates.md for context.
     ```
4. Ensure the test completes in <5s (NFR-001) — no shelling out, just `tomllib.load()` + `importlib.metadata.version()`.
5. Use `tomllib` (stdlib in Python 3.11+) for TOML parsing.
6. If `importlib.metadata.version(pkg)` raises `PackageNotFoundError`, treat that as drift (locked but not installed) and include it in the failure message.

**Files**: `tests/architectural/test_uv_lock_pin_drift.py` (new, ~80–120 lines including docstring).

**Validation**:
- [ ] Test passes locally on a clean `uv sync --frozen` environment.
- [ ] Test fails locally when an off-version `spec-kitty-events` is force-installed; failure message names the package AND prints `uv sync --frozen`.
- [ ] Test runs in under 5 seconds (NFR-001).
- [ ] `mypy --strict` is clean on the new file.

### Subtask T002 [P] — Author/extend `docs/development/review-gates.md`

**Purpose**: Single canonical place that documents the pre-review/pre-PR sync command.

**Steps**:

1. Check whether `docs/development/review-gates.md` already exists. If yes, extend it; if no, create it.
2. Add a section titled "Environment hygiene before review/PR" (or similar) that says:
   - Run `uv sync --frozen` from the repository root before requesting review or opening a PR.
   - Why: keeps your installed `spec-kitty-events` and `spec-kitty-tracker` in lockstep with `uv.lock`. Drift surfaces as confusing review-gate failures unrelated to your changes.
   - What it does: installs the exact resolved versions from `uv.lock` without re-resolving the dependency graph.
   - When to run: any time you pull main, switch branches, or change `pyproject.toml`/`uv.lock`.
3. Cross-reference the architectural test (`tests/architectural/test_uv_lock_pin_drift.py`) so a developer reading the test failure can find the explanation.
4. Keep the doc terse — one tight section, not a full guide.

**Files**: `docs/development/review-gates.md` (new or modified, ~20–40 added lines).

**Validation**:
- [ ] Doc names `uv sync --frozen` literally.
- [ ] Doc cross-references `tests/architectural/test_uv_lock_pin_drift.py`.
- [ ] No reference to deprecated/alternative sync commands.

### Subtask T003 [P] — Audit and correct issue-matrix rows

**Purpose**: Correct any `kitty-specs/**/issue-matrix.md` row that says #848 is "verified-already-fixed" when the underlying risk still exists, per FR-003.

`kitty-specs/**/issue-matrix.md` is in this WP's `owned_files`, so editing those rows when the audit finds stale claims is in scope (and required by FR-003).

**Steps**:

1. Search: `grep -RInl "848" kitty-specs/**/issue-matrix.md 2>/dev/null` (and variants like `848 `, `#848`, `Issue 848`).
2. For each match, inspect the row text. If the row asserts "verified-already-fixed" or equivalent for environment/pin-drift hygiene AND that risk is still present (i.e., this WP is still required), correct the row to reflect actual status — e.g., "in progress: WP01 of charter-e2e-827-followups adds drift detector".
3. Do not invent rows or restructure unrelated content. Only correct misrepresentations specifically related to #848 hygiene.

**Files**: `kitty-specs/**/issue-matrix.md` (edit-allowed, scope depends on audit findings; may be zero edits).

**Validation**:
- [ ] No remaining row claims #848 hygiene is already-fixed if the drift detector is not yet on main.
- [ ] No unrelated changes to issue-matrix files (no #844/#845/#846/#847/#822/etc. row touched).

> **Note**: this subtask may produce zero edits if no stale rows exist. That is a legitimate outcome — record "audit clean: 0 edits" in the WP completion notes if so.

### Subtask T004 — Validate green-path AND red-path

**Purpose**: Prove the test is meaningful in both directions.

**Steps**:

1. Green path:
   ```bash
   uv sync --frozen
   uv run pytest tests/architectural/test_uv_lock_pin_drift.py -q
   ```
   Expected: PASS.
2. Red path:
   ```bash
   # In a throwaway shell — DO NOT COMMIT THE PIN CHANGE.
   uv pip install spec-kitty-events==<intentionally-wrong-version>
   uv run pytest tests/architectural/test_uv_lock_pin_drift.py -q
   ```
   Expected: FAIL. The failure message must name `spec-kitty-events` AND include the literal string `uv sync --frozen`.
3. Restore:
   ```bash
   uv sync --frozen
   uv run pytest tests/architectural/test_uv_lock_pin_drift.py -q
   ```
   Expected: PASS.
4. Capture the red-path failure message in your WP completion notes (paste the relevant lines) so reviewers can see the actionable error wording.

**Validation**:
- [ ] Green path passes.
- [ ] Red path fails with the expected wording.
- [ ] Restore returns to green.

## Branch strategy

- **Planning/base branch**: `main` (deterministic from `branch_context`).
- **Final merge target**: `main`.
- **Execution worktree**: assigned per lane by `finalize-tasks`. You will receive an absolute path under `.worktrees/charter-e2e-827-followups-<mid8>-lane-a/` (or similar) when `spec-kitty next` issues this WP. Work inside that path; do NOT manually create branches or worktrees.

## Definition of Done

- [ ] `tests/architectural/test_uv_lock_pin_drift.py` exists, passes on a clean install, and fails actionably on synthetic drift.
- [ ] `docs/development/review-gates.md` exists and documents `uv sync --frozen` as the canonical pre-review/pre-PR sync command.
- [ ] Issue-matrix audit performed; any misleading "verified-already-fixed" rows for #848 hygiene corrected (or recorded as "audit clean: 0 edits").
- [ ] `uv run pytest tests/architectural -q` runs clean (this WP's test plus all existing architectural tests). This is part of the NFR-003 verification matrix.
- [ ] `mypy --strict` is clean on the new file.
- [ ] No edits to `pyproject.toml`, `uv.lock`, or `[tool.uv.sources]` (scope guardrail C-004).
- [ ] Edits limited to this WP's `owned_files`: the new test, the doc page, and possibly issue-matrix.md rows for #848.
- [ ] Issue-matrix changes (if any) only touch rows about #848; no other issue's row is modified.

## Implementation command

This WP has no upstream dependencies. Issue it with:

```bash
spec-kitty agent action implement WP01 --agent claude --mission charter-e2e-827-followups-01KQAJA0
```

## Reviewer guidance

- Verify the diff is exactly two source-tree files (the new test, the doc page) plus optionally a small set of issue-matrix corrections. Anything else is scope creep — reject.
- Verify the test failure message **names the offending package(s) AND prints `uv sync --frozen`** literally.
- Verify the test runs in under 5 seconds.
- Verify nothing in `pyproject.toml`, `uv.lock`, or `.github/workflows/` was touched.
- Verify the doc page does not invent alternative sync commands.

## Requirement references

This WP satisfies the following spec requirements (mapped via `agent tasks map-requirements`):

- **FR-001**: drift check in review-gate path.
- **FR-002**: documented pre-review sync command.
- **FR-003**: correct stale "verified-already-fixed" rows.

It also contributes to:

- **NFR-001** (drift check < 5s on clean install).
- **NFR-002** (failure output names package + sync command).
- **NFR-003** (the new test is part of the verification matrix).
- **C-004** (hygiene-only; no dependency-management redesign).

PR-body language for **FR-016** is owned by the merging step but the operator's preferred order has WP01 landing first.
