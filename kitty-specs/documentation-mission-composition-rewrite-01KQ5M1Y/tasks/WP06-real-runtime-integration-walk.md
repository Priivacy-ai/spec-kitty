---
work_package_id: WP06
title: Real-Runtime Integration Walk
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
requirement_refs:
- FR-007
- FR-008
- FR-009
- FR-011
- FR-012
- FR-013
- FR-017
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
history:
- action: created
  at: '2026-04-26T19:46:00Z'
  by: tasks
authoritative_surface: tests/integration/
execution_mode: code_change
owned_files:
- tests/integration/test_documentation_runtime_walk.py
tags: []
---

# WP06 — Real-Runtime Integration Walk

## Objective

Author `tests/integration/test_documentation_runtime_walk.py` mirroring `tests/integration/test_research_runtime_walk.py`. The file MUST drive the live runtime via `get_or_start_run` / `decide_next_via_runtime` and MUST NOT mock `_dispatch_via_composition`, `StepContractExecutor.execute`, `ProfileInvocationExecutor.invoke`, frozen-template loaders, `load_validated_graph`, or `resolve_context` (FR-013, C-007).

## Context

The integration walk is the gate test for SC-001 / SC-003 / SC-004 / FR-013. It consumes everything from WP01..WP05:

- WP01's runtime sidecar resolves under `mission_type='documentation'` (SC-007).
- WP02's contracts are loaded by composition.
- WP03's action bundles surface via `resolve_context()`.
- WP04's DRG nodes provide non-empty `artifact_urns`.
- WP05's `_COMPOSED_ACTIONS_BY_MISSION` entry routes through composition.
- WP05's guard branch fires on missing artifacts and on unknown actions.

The reference is `tests/integration/test_research_runtime_walk.py`. Read it end-to-end before authoring. Substitute `mission_type='documentation'`, the 6 documentation action verbs, and the documentation artifact paths (`spec.md`, `gap-analysis.md`, `plan.md`, `docs/index.md`, `audit-report.md`, `release.md`).

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution: `spec-kitty agent action implement WP06 --agent <name>`. Depends on WP01-WP05.

## Subtasks

### T024 — Scaffolding + C-007 docstring

**Steps**:
1. Create `tests/integration/test_documentation_runtime_walk.py` starting with the C-007 docstring (mirroring `test_research_runtime_walk.py:1-21`):

   ```python
   """Real-runtime integration walk for the documentation mission.

   C-007 enforcement (spec constraint, FINAL GATE):
       The following symbols MUST NOT appear in any unittest.mock.patch target
       in this file. Reviewer greps; any hit blocks approval and blocks the
       mission from merging.

           - _dispatch_via_composition
           - StepContractExecutor.execute
           - ProfileInvocationExecutor.invoke
           - _load_frozen_template (and any frozen-template loader)
           - load_validated_graph
           - resolve_context

   This file proves SC-001 / SC-003 / SC-004 for documentation mission composition (#502):
       `get_or_start_run('demo-docs-walk', tmp_repo, 'documentation')`
       succeeds end-to-end without raising MissionRuntimeError, the runtime
       advances at least one composed step via the real composition path, and
       structured guard failures fire on missing artifacts.
   """
   ```

2. Add fixtures and helpers (mirror research walk verbatim; substitute mission key and artifacts):

   ```python
   from __future__ import annotations

   import json
   import subprocess
   from collections.abc import Iterator
   from pathlib import Path

   import pytest

   from specify_cli.next._internal_runtime.engine import _read_snapshot
   from specify_cli.next.runtime_bridge import (
       _check_composed_action_guard,
       _resolve_runtime_template_in_root,
       decide_next_via_runtime,
       get_or_start_run,
   )


   def _init_min_repo(repo_root: Path) -> None:
       repo_root.mkdir(parents=True, exist_ok=True)
       subprocess.run(["git", "init", "--initial-branch=main"], cwd=repo_root, capture_output=True, check=True)
       subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_root, capture_output=True, check=True)
       subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_root, capture_output=True, check=True)
       (repo_root / "README.md").write_text("# test", encoding="utf-8")
       subprocess.run(["git", "add", "README.md"], cwd=repo_root, capture_output=True, check=True)
       subprocess.run(["git", "commit", "-m", "init"], cwd=repo_root, capture_output=True, check=True)


   def _scaffold_documentation_feature(
       repo_root: Path,
       mission_slug: str,
       *,
       happy_path: bool = False,
   ) -> Path:
       feature_dir = repo_root / "kitty-specs" / mission_slug
       feature_dir.mkdir(parents=True)
       (feature_dir / "meta.json").write_text(
           json.dumps({"mission_type": "documentation"}),
           encoding="utf-8",
       )
       if happy_path:
           # Author every documentation gate artifact so guards pass.
           (feature_dir / "spec.md").write_text("# spec", encoding="utf-8")
           (feature_dir / "gap-analysis.md").write_text("# gap analysis", encoding="utf-8")
           (feature_dir / "plan.md").write_text("# plan", encoding="utf-8")
           (feature_dir / "docs").mkdir()
           (feature_dir / "docs" / "index.md").write_text("# docs", encoding="utf-8")
           (feature_dir / "audit-report.md").write_text("# audit report", encoding="utf-8")
           (feature_dir / "release.md").write_text("# release", encoding="utf-8")
       return feature_dir


   @pytest.fixture
   def isolated_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
       repo_root = tmp_path / "repo"
       _init_min_repo(repo_root)
       monkeypatch.delenv("SPEC_KITTY_MISSION_PATHS", raising=False)
       monkeypatch.delenv("KITTIFY_MISSION_PATHS", raising=False)
       yield repo_root
   ```

**Files**: scaffolding portion of `tests/integration/test_documentation_runtime_walk.py` (~70 lines).

**Validation**:
- [ ] Docstring lists the 6 forbidden patch targets.
- [ ] No `unittest.mock` import anywhere in the file.
- [ ] `_scaffold_documentation_feature` writes `meta.json` with `{"mission_type": "documentation"}`.

### T025 — Happy-path tests

**Purpose**: prove SC-001, SC-007, SC-002 baseline, FR-001, FR-002, FR-011, FR-012, NFR-006.

**Steps**:
1. Append four tests to the file:

   ```python
   def test_get_or_start_run_succeeds_for_documentation(isolated_repo: Path) -> None:
       """FR-001 / SC-001: a fresh documentation mission starts without MissionRuntimeError."""
       _scaffold_documentation_feature(isolated_repo, "demo-docs-walk", happy_path=True)
       run_ref = get_or_start_run("demo-docs-walk", isolated_repo, "documentation")
       run_dir = Path(run_ref.run_dir)
       assert run_dir.is_dir(), f"run_dir not created: {run_dir}"


   def test_documentation_template_resolves_runtime_sidecar() -> None:
       """SC-007: the loader resolves mission-runtime.yaml ahead of legacy mission.yaml."""
       package_root = Path(__file__).resolve().parents[1].parent / "src" / "specify_cli" / "missions"
       resolved = _resolve_runtime_template_in_root(package_root, "documentation")
       assert resolved is not None
       assert resolved.name == "mission-runtime.yaml"


   def test_composition_advances_one_documentation_step(isolated_repo: Path) -> None:
       """FR-002: composition advances the first documentation action via spec-kitty next."""
       _scaffold_documentation_feature(isolated_repo, "demo-docs-walk", happy_path=True)
       get_or_start_run("demo-docs-walk", isolated_repo, "documentation")
       decision = decide_next_via_runtime("demo-docs-walk", isolated_repo, "documentation")
       assert decision.mission == "documentation"
       assert decision.issued_step_id in {"discover", "audit", "design", "generate", "validate", "publish"}


   def test_paired_invocation_lifecycle_is_recorded(isolated_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
       """FR-011 + FR-012 + NFR-006: invocation trail records paired started/done with documentation-native action name."""
       trail_root = tmp_path / "kittify-events"
       monkeypatch.setenv("KITTIFY_HOME", str(tmp_path))
       _scaffold_documentation_feature(isolated_repo, "demo-docs-walk", happy_path=True)
       get_or_start_run("demo-docs-walk", isolated_repo, "documentation")
       decide_next_via_runtime("demo-docs-walk", isolated_repo, "documentation")

       # Inspect ~/.kittify/events/profile-invocations/ (or KITTIFY_HOME equivalent) for paired records.
       invocation_dir = tmp_path / ".kittify" / "events" / "profile-invocations"
       events = sorted(invocation_dir.rglob("*.jsonl")) if invocation_dir.exists() else []
       assert events, f"no invocation trail records under {invocation_dir}"
       # At least one event must mention a documentation-native action name.
       payloads = [json.loads(line) for path in events for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
       doc_actions = {"discover", "audit", "design", "generate", "validate", "publish"}
       assert any(p.get("action") in doc_actions for p in payloads), (
           f"no documentation-native action in {[p.get('action') for p in payloads]}"
       )
   ```

   *Note*: the `paired_invocation_lifecycle_is_recorded` test mirrors `test_research_runtime_walk.py`'s lifecycle test. The implementer should read the research version first to confirm the exact `KITTIFY_HOME` env var and event-path layout used by the runtime; substitute as needed.

**Validation**:
- [ ] All 4 tests pass.
- [ ] No mocks.

### T026 — Guard-failure tests

**Purpose**: prove SC-003 + FR-007 + FR-008 + FR-009 + FR-017.

**Steps**:
1. Append two more tests:

   ```python
   def test_missing_artifact_blocks_with_structured_failure(isolated_repo: Path) -> None:
       """FR-007 + FR-008 + SC-003: empty feature_dir produces a structured guard failure naming spec.md."""
       feature_dir = _scaffold_documentation_feature(isolated_repo, "demo-docs-walk", happy_path=False)
       failures = _check_composed_action_guard("discover", feature_dir, mission="documentation")
       assert any("spec.md" in f for f in failures), f"expected spec.md in failures; got {failures}"


   def test_unknown_documentation_action_fails_closed(isolated_repo: Path) -> None:
       """FR-017: unknown documentation actions fail closed."""
       feature_dir = _scaffold_documentation_feature(isolated_repo, "demo-docs-walk", happy_path=True)
       failures = _check_composed_action_guard("ghost", feature_dir, mission="documentation")
       assert failures == ["No guard registered for documentation action: ghost"]
   ```

2. Run the full file: `uv run --python 3.13 --extra test python -m pytest tests/integration/test_documentation_runtime_walk.py -v --timeout=120`.

**Validation**:
- [ ] All 6 tests pass.
- [ ] `grep -n 'unittest.mock\|mock.patch\|@patch\|with patch' tests/integration/test_documentation_runtime_walk.py` returns 0 matches.
- [ ] No mocks of `_dispatch_via_composition`, `StepContractExecutor.execute`, `ProfileInvocationExecutor.invoke`, frozen-template loaders, `load_validated_graph`, or `resolve_context`.

## Definition of Done

- [ ] T024 — scaffolding + C-007 docstring + fixtures present.
- [ ] T025 — 4 happy-path tests pass.
- [ ] T026 — 2 guard-failure tests pass.
- [ ] `grep` proves zero mock targets from the C-007 list.
- [ ] `ruff check tests/integration/test_documentation_runtime_walk.py` clean.
- [ ] `mypy --strict tests/integration/test_documentation_runtime_walk.py` clean.

## Risks

1. The exact API for `decide_next_via_runtime` may differ slightly from research (different signature, different return shape). Mitigation: read `tests/integration/test_research_runtime_walk.py` end-to-end and copy the call shape verbatim before substituting documentation values.
2. The invocation trail path (`tmp_path / ".kittify" / "events" / "profile-invocations"`) may not be the actual layout used by the runtime under `KITTIFY_HOME`. Mitigation: replicate the research walk's lifecycle test verbatim; if it uses a different env var or path, copy that.
3. The integration walk's first run may be slow (~5-10s) because it actually loads the validated DRG and walks composition. Mitigation: `--timeout=120` is sufficient.

## Reviewer Guidance

- **Final gate per FR-013 / C-007**: grep the file for `mock`, `patch`, `@patch`, `with patch`. Any hit blocks approval.
- Verify the C-007 docstring at the top is verbatim and lists all 6 forbidden symbols.
- Verify the file imports `_dispatch_via_composition` is NOT done (it should not be in the imports). The test consumes the live runtime, not internal helpers.
- Verify the unknown-action test expects exactly `"No guard registered for documentation action: ghost"`.
