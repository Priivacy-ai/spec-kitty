---
work_package_id: WP05
title: Composition Dispatch + Guard + Profile Defaults
dependencies:
- WP01
- WP02
- WP04
requirement_refs:
- FR-007
- FR-008
- FR-009
- FR-011
- FR-012
- FR-015
- FR-016
- FR-017
planning_base_branch: main
merge_target_branch: main
branch_strategy: lane-per-WP-from-finalize-tasks
subtasks:
- T020
- T021
- T022
- T023
history:
- action: created
  at: '2026-04-26T19:46:00Z'
  by: tasks
authoritative_surface: src/specify_cli/next/
execution_mode: code_change
owned_files:
- src/specify_cli/next/runtime_bridge.py
- src/specify_cli/mission_step_contracts/executor.py
- tests/specify_cli/next/test_runtime_bridge_documentation_composition.py
tags: []
---

# WP05 — Composition Dispatch + Guard + Profile Defaults

## Objective

Wire the documentation mission into the composition substrate. This WP makes three coordinated edits to two source files, plus a unit test:

1. `runtime_bridge.py` — add `"documentation"` entry to `_COMPOSED_ACTIONS_BY_MISSION` so the dispatch fast-path activates for documentation actions.
2. `runtime_bridge.py` — add `_has_generated_docs` helper + a documentation branch in `_check_composed_action_guard()` with hardcoded artifact gates and a fail-closed default for unknown actions.
3. `executor.py` — add 6 entries to `_ACTION_PROFILE_DEFAULTS` mapping `(mission, action)` to a shipped profile per FR-016.
4. Author `tests/specify_cli/next/test_runtime_bridge_documentation_composition.py` covering dispatch entry, per-action guard pass/fail, unknown-action fail-closed, and profile defaults.

## Context

Reference:
- [data-model.md → Guard branch shape](../data-model.md#guard-branch-shape) — the exact code skeleton for the documentation branch in `_check_composed_action_guard()`.
- [research.md → R-003](../research.md#r-003--guard-data-source) — the verbatim research branch this mirrors (`runtime_bridge.py:560-589`).
- [research.md → R-001](../research.md#r-001--loader-resolution-path) — sidecar precedence is already in code; no loader change.

This WP depends on WP01 (sidecar template must exist for the integration walk to verify start), WP02 (contracts must exist so composition can synthesize them), and WP04 (DRG nodes must exist so `resolve_context` returns non-empty artifact_urns inside composition).

**Architectural invariants** (DO NOT VIOLATE):
- C-002: composition chokepoint is `StepContractExecutor`. Do NOT call `ProfileInvocationExecutor` directly for documentation actions.
- C-003: `_ACTION_PROFILE_DEFAULTS` additions are only the 6 documentation entries. No wildcard keys, no custom-mission generalization.
- FR-017: unknown documentation actions MUST fail closed with `"No guard registered for documentation action: <name>"`.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution: `spec-kitty agent action implement WP05 --agent <name>`. Depends on WP01, WP02, WP04.

## Subtasks

### T020 — `_COMPOSED_ACTIONS_BY_MISSION` entry

**Steps**:
1. Open `src/specify_cli/next/runtime_bridge.py`. Locate `_COMPOSED_ACTIONS_BY_MISSION` (currently at ~line 272-275).
2. Add the documentation entry alongside software-dev and research:
   ```python
   _COMPOSED_ACTIONS_BY_MISSION: dict[str, frozenset[str]] = {
       "software-dev": frozenset({"specify", "plan", "tasks", "implement", "review"}),
       "research": frozenset({"scoping", "methodology", "gathering", "synthesis", "output"}),
       "documentation": frozenset({"discover", "audit", "design", "generate", "validate", "publish"}),
   }
   ```
3. Verify mypy: `uv run --python 3.13 --extra lint mypy --strict src/specify_cli/next/runtime_bridge.py`.

**Files**: `src/specify_cli/next/runtime_bridge.py` (edit only).

**Validation**:
- [ ] Documentation entry contains exactly 6 verbs: `discover, audit, design, generate, validate, publish`.
- [ ] `accept` is NOT in the set (per spec FR-005 + plan D5).

### T021 — `_ACTION_PROFILE_DEFAULTS` entries

**Steps**:
1. Open `src/specify_cli/mission_step_contracts/executor.py`. Locate `_ACTION_PROFILE_DEFAULTS` (currently at ~line 39-49).
2. Add 6 documentation entries below the research entries (preserve existing software-dev / research entries unchanged):
   ```python
   _ACTION_PROFILE_DEFAULTS: dict[tuple[str, str], str] = {
       ("software-dev", "specify"): "researcher-robbie",
       # ...existing software-dev + research entries...
       ("research", "output"): "reviewer-renata",
       ("documentation", "discover"): "researcher-robbie",
       ("documentation", "audit"): "researcher-robbie",
       ("documentation", "design"): "architect-alphonso",
       ("documentation", "generate"): "implementer-ivan",
       ("documentation", "validate"): "reviewer-renata",
       ("documentation", "publish"): "reviewer-renata",
   }
   ```
3. Verify mypy + ruff on the file.

**Files**: `src/specify_cli/mission_step_contracts/executor.py` (edit only).

**Validation**:
- [ ] All 6 entries present with exact profile names from FR-016.
- [ ] No edits to research or software-dev entries.

### T022 — `_has_generated_docs` helper + documentation guard branch

**Steps**:
1. Open `src/specify_cli/next/runtime_bridge.py`. Locate `_check_composed_action_guard()` (currently at ~line 515; signature at line 515-522).
2. Add a new module-level private helper above `_check_composed_action_guard()`:
   ```python
   def _has_generated_docs(feature_dir: Path) -> bool:
       """Return True iff at least one *.md file exists under feature_dir / 'docs'.

       Used by the documentation `generate` guard branch (D6 of plan.md).
       """
       docs_root = feature_dir / "docs"
       if not docs_root.is_dir():
           return False
       return next(docs_root.rglob("*.md"), None) is not None
   ```
3. Inside `_check_composed_action_guard()`, add the documentation branch immediately after the research branch's `return failures` (currently around line 588):
   ```python
   if mission == "documentation":
       if action == "discover":
           if not (feature_dir / "spec.md").is_file():
               failures.append("Required artifact missing: spec.md")
       elif action == "audit":
           if not (feature_dir / "gap-analysis.md").is_file():
               failures.append("Required artifact missing: gap-analysis.md")
       elif action == "design":
           if not (feature_dir / "plan.md").is_file():
               failures.append("Required artifact missing: plan.md")
       elif action == "generate":
           if not _has_generated_docs(feature_dir):
               failures.append(
                   "Required artifact missing: docs/**/*.md "
                   "(no Markdown files found under docs/)"
               )
       elif action == "validate":
           if not (feature_dir / "audit-report.md").is_file():
               failures.append("Required artifact missing: audit-report.md")
       elif action == "publish":
           if not (feature_dir / "release.md").is_file():
               failures.append("Required artifact missing: release.md")
       else:
           failures.append(
               f"No guard registered for documentation action: {action}"
           )
       return failures
   ```
4. Preserve the existing `# noqa: C901` on `_check_composed_action_guard()` (the function is already marked because of cyclomatic complexity; adding the documentation branch increases it further but does not change the noqa).
5. Verify ruff + mypy: `uv run --python 3.13 --extra lint ruff check src/specify_cli/next/runtime_bridge.py` and `mypy --strict`.

**Files**: `src/specify_cli/next/runtime_bridge.py` (edit only).

**Validation**:
- [ ] `_has_generated_docs` is module-level (not nested).
- [ ] Documentation branch appears AFTER research branch's `return failures` (so research handling is unchanged).
- [ ] Fail-closed default emits exactly `"No guard registered for documentation action: <name>"`.
- [ ] Each known action has at least one `feature_dir / "<artifact>.md"` (or `.csv` / glob) check.
- [ ] No edits to research or software-dev branches (regression contract).

### T023 — Author `test_runtime_bridge_documentation_composition.py`

**Purpose**: pin dispatch entry, per-action guard cases, and unknown-action fail-closed (FR-007, FR-008, FR-009, FR-016, FR-017).

**Steps**:
1. Create `tests/specify_cli/next/test_runtime_bridge_documentation_composition.py`:

   ```python
   """Unit tests for documentation composition wiring (#502)."""

   from __future__ import annotations

   from pathlib import Path

   import pytest

   from specify_cli.mission_step_contracts.executor import _ACTION_PROFILE_DEFAULTS
   from specify_cli.next.runtime_bridge import (
       _COMPOSED_ACTIONS_BY_MISSION,
       _check_composed_action_guard,
   )

   _DOC_ACTIONS = ("discover", "audit", "design", "generate", "validate", "publish")
   _PROFILE_DEFAULTS = {
       "discover": "researcher-robbie",
       "audit": "researcher-robbie",
       "design": "architect-alphonso",
       "generate": "implementer-ivan",
       "validate": "reviewer-renata",
       "publish": "reviewer-renata",
   }
   _GATE_ARTIFACT = {
       "discover": "spec.md",
       "audit": "gap-analysis.md",
       "design": "plan.md",
       "validate": "audit-report.md",
       "publish": "release.md",
   }


   def test_documentation_in_composed_actions() -> None:
       """FR-002 + FR-015: documentation entry present with the 6 expected verbs."""
       assert "documentation" in _COMPOSED_ACTIONS_BY_MISSION
       assert _COMPOSED_ACTIONS_BY_MISSION["documentation"] == frozenset(_DOC_ACTIONS)
       assert "accept" not in _COMPOSED_ACTIONS_BY_MISSION["documentation"], (
           "FR-005 / plan D5 — accept must not be in the composed set"
       )


   @pytest.mark.parametrize("action,profile", list(_PROFILE_DEFAULTS.items()))
   def test_profile_defaults_per_action(action: str, profile: str) -> None:
       """FR-016: documentation profile defaults wired in executor._ACTION_PROFILE_DEFAULTS."""
       assert _ACTION_PROFILE_DEFAULTS[("documentation", action)] == profile


   @pytest.mark.parametrize("action,artifact", list(_GATE_ARTIFACT.items()))
   def test_guard_fails_when_artifact_missing(tmp_path: Path, action: str, artifact: str) -> None:
       """FR-007 + FR-008: each documentation action's guard names the missing artifact."""
       failures = _check_composed_action_guard(action, tmp_path, mission="documentation")
       assert any(artifact in msg for msg in failures), (
           f"expected '{artifact}' in failures for action {action}; got {failures}"
       )


   def test_generate_guard_fails_with_empty_docs_root(tmp_path: Path) -> None:
       """FR-008(d): generate gate is 'any *.md under docs/'; empty feature_dir fails."""
       failures = _check_composed_action_guard("generate", tmp_path, mission="documentation")
       assert any("docs" in msg.lower() for msg in failures), failures


   def test_generate_guard_passes_with_one_md_under_docs(tmp_path: Path) -> None:
       (tmp_path / "docs").mkdir()
       (tmp_path / "docs" / "intro.md").write_text("# intro\n", encoding="utf-8")
       failures = _check_composed_action_guard("generate", tmp_path, mission="documentation")
       assert not any("docs" in msg.lower() for msg in failures), failures


   def test_unknown_documentation_action_fails_closed(tmp_path: Path) -> None:
       """FR-017: unknown actions emit a structured failure rather than silently passing."""
       failures = _check_composed_action_guard("ghost", tmp_path, mission="documentation")
       assert failures == ["No guard registered for documentation action: ghost"]


   @pytest.mark.parametrize("action", _DOC_ACTIONS)
   def test_known_action_passes_when_artifact_present(tmp_path: Path, action: str) -> None:
       """FR-007 happy path: each guard returns no failures when its artifact exists."""
       # Author the artifact required by this action.
       if action == "generate":
           (tmp_path / "docs").mkdir()
           (tmp_path / "docs" / "intro.md").write_text("# intro", encoding="utf-8")
       else:
           (tmp_path / _GATE_ARTIFACT[action]).write_text(f"# {action}", encoding="utf-8")

       failures = _check_composed_action_guard(action, tmp_path, mission="documentation")
       assert failures == [], f"expected no failures; got {failures}"
   ```

2. Run: `uv run --python 3.13 --extra test python -m pytest tests/specify_cli/next/test_runtime_bridge_documentation_composition.py -v`.

**Files**: `tests/specify_cli/next/test_runtime_bridge_documentation_composition.py` (new, ~110 lines).

**Validation**:
- [ ] All tests pass (1 + 6 + 5 + 1 + 1 + 1 + 6 = 21 cases).
- [ ] No mocks of any forbidden surface.
- [ ] Test imports `_check_composed_action_guard` (the public-by-convention internal); no patching.

## Definition of Done

- [ ] T020 — `_COMPOSED_ACTIONS_BY_MISSION["documentation"]` present with 6 verbs.
- [ ] T021 — 6 entries in `_ACTION_PROFILE_DEFAULTS`.
- [ ] T022 — `_has_generated_docs` helper + documentation branch + fail-closed default in `_check_composed_action_guard`.
- [ ] T023 — `test_runtime_bridge_documentation_composition.py` passes 21+ cases.
- [ ] `mypy --strict` on `runtime_bridge.py` + `executor.py` — zero new findings.
- [ ] `ruff check` on `runtime_bridge.py` + `executor.py` + the new test — clean.
- [ ] No edits to research or software-dev branches in `_check_composed_action_guard`.

## Risks

1. mypy --strict may flag the new branch if a type narrowing is lost. Mitigation: copy the research branch's type-narrowing pattern verbatim. If a strict-mypy cast is needed (#805), add a narrow `# type: ignore` only on the specific line — do not generalize.
2. The `_has_generated_docs` glob call (`Path.rglob`) returns an iterator; using `next(..., None)` short-circuits on first hit. Verify this is the documented behavior and not a Python-version pitfall.
3. The fail-closed default may regress if a future refactor reorders branches. Mitigation: T023's `test_unknown_documentation_action_fails_closed` is the regression gate; reviewers must keep it green.

## Reviewer Guidance

- Diff `_check_composed_action_guard` and verify the documentation branch is appended AFTER research, never inside research.
- Verify the fail-closed default emits the exact message FR-017 / data-model.md specifies.
- Verify no new top-level branches in `_check_composed_action_guard` other than the documentation branch.
- Verify the test file is at `tests/specify_cli/next/` (matches the existing research test path).
