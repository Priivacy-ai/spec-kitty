---
work_package_id: WP04
title: create-feature Core Extraction
dependencies: []
requirement_refs:
- FR-006
planning_base_branch: feat/implement-review-skill
merge_target_branch: feat/implement-review-skill
branch_strategy: Planning artifacts for this feature were generated on feat/implement-review-skill. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/implement-review-skill unless the human explicitly redirects the landing branch.
subtasks: [T018, T019, T020, T021, T022, T023]
history:
- date: '2026-04-01'
  action: created
  by: spec-kitty.tasks
authoritative_surface: src/specify_cli/core/feature_creation.py
execution_mode: code_change
owned_files:
- src/specify_cli/core/feature_creation.py
- src/specify_cli/cli/commands/agent/feature.py
- tests/specify_cli/core/test_feature_creation.py
---

# WP04: create-feature Core Extraction

## Objective

Extract the core feature-creation logic from the `create_feature()` typer command in `src/specify_cli/cli/commands/agent/feature.py` into a reusable public function in a new neutral module `src/specify_cli/core/feature_creation.py`. Refactor the existing CLI command to a thin wrapper. Verify no regression in CLI behavior.

This WP is a prerequisite for WP05 — the orchestration layer calls `create_feature_core()` from `tracker/origin.py`.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Implementation command**: `spec-kitty implement WP04`
- No dependencies — can run in parallel with WP01, WP02, WP03.

## Context

- **Plan**: `kitty-specs/061-ticket-first-mission-origin-binding/plan.md` — D2 (extraction rationale)
- **Research**: `kitty-specs/061-ticket-first-mission-origin-binding/research.md` — R1 (create-feature analysis)
- **Source**: `src/specify_cli/cli/commands/agent/feature.py` — `create_feature()` function (line 512, ~300 lines)
- **Existing usage**: `src/specify_cli/cli/commands/lifecycle.py` imports from `agent.feature`

## Subtasks

### T018: Create `core/feature_creation.py` with `FeatureCreationResult`

**File**: `src/specify_cli/core/feature_creation.py` (new file)

```python
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class FeatureCreationError(RuntimeError):
    """Raised when feature creation fails."""


@dataclass(slots=True)
class FeatureCreationResult:
    """Structured result from create_feature_core()."""
    feature_dir: Path
    feature_slug: str
    feature_number: str
    meta: dict[str, Any]
    target_branch: str
    created_files: list[Path]
```

### T019: Create `FeatureCreationError` exception class

Already included in T018. Ensure it inherits from `RuntimeError` (consistent with `TrackerServiceError`, `SaaSTrackerClientError`).

### T020: Extract core logic from `create_feature()` into `create_feature_core()`

**Source file**: `src/specify_cli/cli/commands/agent/feature.py`
**Target file**: `src/specify_cli/core/feature_creation.py`

**What to extract** (from `create_feature()` lines 518–833):
1. Input validation (kebab-case slug check)
2. Feature number allocation (`get_next_feature_number()`)
3. Directory creation (`kitty-specs/###-slug/` with subdirectories)
4. Template copying (spec.md from mission template if available)
5. `meta.json` scaffolding
6. `status.events.jsonl` initialization
7. Git commit (`_commit_to_branch()` helper)
8. Event emission (fire-and-forget `emit_feature_created()`)

**Function signature**:
```python
def create_feature_core(
    repo_root: Path,
    feature_slug: str,
    *,
    mission: str | None = None,
    target_branch: str | None = None,
) -> FeatureCreationResult:
    """Create a new feature with all scaffolding.

    Raises FeatureCreationError on any failure.
    """
```

**Critical rules**:
- Replace all `typer.Exit(1)` with `raise FeatureCreationError(...)`
- Replace all `typer.echo()` / `console.print()` with either logging or nothing (the caller controls output)
- The function must return `FeatureCreationResult`, not print JSON
- Git commit behavior is preserved (the function commits to the target branch)
- Event emission is preserved (fire-and-forget)
- The `_commit_to_branch()` helper can stay in `feature.py` or move to `core/` — implementer's choice based on what's cleanest. If it stays, `create_feature_core()` imports it from the CLI module (acceptable since it's a git utility, not a CLI command).

**Important**: The extraction must preserve ALL side effects (directory creation, git commit, event emission). This is not a simplification — it's a module boundary change.

### T021: Refactor `create_feature()` typer command to thin wrapper

**File**: `src/specify_cli/cli/commands/agent/feature.py`

After extraction, `create_feature()` becomes:
```python
@app.command(name="create-feature")
def create_feature(
    feature_slug: ...,
    mission: ...,
    json_output: ...,
    target_branch: ...,
) -> None:
    try:
        result = create_feature_core(
            repo_root=repo_root,
            feature_slug=feature_slug,
            mission=mission,
            target_branch=target_branch,
        )
    except FeatureCreationError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    if json_output:
        # Format and print JSON from result
        ...
    else:
        # Format and print human-readable output from result
        ...
```

**Key**: All output formatting stays in the typer command. All logic moves to `create_feature_core()`.

### T022: Write tests for `create_feature_core()`

**File**: `tests/specify_cli/core/test_feature_creation.py` (new file)

**Test cases**:
1. **Happy path**: Creates directory, meta.json, spec.md; returns `FeatureCreationResult` with correct fields
2. **Invalid slug** (non-kebab-case): Raises `FeatureCreationError`
3. **Feature already exists**: Raises `FeatureCreationError`
4. **Git commit**: Verify files are committed (mock or check git status)
5. **Return type**: `FeatureCreationResult` has correct `feature_dir`, `feature_slug`, `feature_number`
6. **Target branch**: Uses provided target_branch or defaults to current branch

**Fixture**: Use `tmp_path` with git repo initialization (`.kittify/` directory, `kitty-specs/` directory, git init).

### T023: Verify existing `create_feature` CLI behavior unchanged

Run the existing test suite for the CLI command to verify no regression:

```bash
pytest tests/agent/cli/commands/test_feature.py -v -k create
```

If existing tests break, fix the thin wrapper — not the core function. The core function is the new contract; the wrapper adapts.

## Definition of Done

- [ ] `core/feature_creation.py` exists with `FeatureCreationResult`, `FeatureCreationError`, `create_feature_core()`
- [ ] `create_feature()` in `feature.py` is a thin wrapper calling `create_feature_core()`
- [ ] All new unit tests pass
- [ ] All existing `create_feature` CLI tests pass (regression-free)
- [ ] `mypy --strict` passes
- [ ] `ruff check` passes

## Risks

- **High**: This is the largest refactor in the feature (300+ lines of logic to move). Careful extraction is needed to preserve all side effects.
- **Mitigation**: The function has clear boundaries (validation → allocation → filesystem → git → events). Extract in that order. Test after each step.
- **Risk**: `_commit_to_branch()` helper may need to be accessible from `core/`. If so, move it or make it importable.

## Reviewer Guidance

- Compare the extracted `create_feature_core()` against the original `create_feature()` line by line — no behavior should be lost
- Verify the thin wrapper catches `FeatureCreationError` and translates to `typer.Exit(1)`
- Verify JSON output format is identical before and after refactor
- Check that `lifecycle.py` (which imports from `agent.feature`) still works
