---
work_package_id: WP10
title: Workflow sequence YAML schema + registry + Pydantic model + `meta.json::workflow_id`
dependencies:
- WP09
requirement_refs:
- C-008
- FR-012
- FR-013
- FR-015
- NFR-005
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T050
- T051
- T052
- T053
- T054
- T055
agent: "claude:sonnet-4-6:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/next/_internal_runtime/workflow_registry.py
execution_mode: code_change
owned_files:
- src/specify_cli/next/_internal_runtime/workflow_registry.py
- src/specify_cli/next/_internal_runtime/workflow_schema.py
- src/doctrine/workflows/software-dev-default.workflow.yaml
- src/doctrine/workflows/_fixtures/our-team-design-first.workflow.yaml
- tests/specify_cli/next/test_workflow_registry.py
role: implementer
tags: []
shell_pid: "2855827"
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Scope governance context to Python implementation before reading anything else.

---

## Objective

Land **Axis 3 of Slice F** (composable workflow sequencing, per #682): promote the mission action sequence (`specify → plan → tasks → implement → review → merge`) from hardcoded constant to a first-class artifact at `src/doctrine/workflows/<id>.workflow.yaml`. Ship `WorkflowSequence` + `ActionStep` Pydantic v2 models, the workflow registry (`get_workflow(workflow_id) -> WorkflowSequence`), the `software-dev-default.workflow.yaml` (byte-stable to today), and a test fixture workflow (`our-team-design-first.workflow.yaml` with an extra `design-review` step).

Per **FR-015** (binding): unknown workflow IDs hard-fail with a message naming the unknown id and listing available workflows. **No silent fallback** to `software-dev-default`.

WP11 then wires the registry into `prompt_builder` + `planner.plan_next` so missions actually use the YAML-declared sequence.

---

## Context

Today's action sequence is hardcoded inside `prompt_builder.py` / `_internal_runtime/planner.py`. Slice F promotes it to a first-class artifact parallel to how agent profiles, tactics, and step contracts already work.

- **Artifact location:** `src/doctrine/workflows/<id>.workflow.yaml` (new directory).
- **Schema:** `WorkflowSequence` Pydantic v2 model with `workflow_id`, `description`, `actions: list[ActionStep]`, `initial`, `version`.
- **Registry:** `src/specify_cli/next/_internal_runtime/workflow_registry.py` with `get_workflow(workflow_id) -> WorkflowSequence`. Search precedence: `src/doctrine/workflows/<id>.workflow.yaml`, then `_fixtures/<id>.workflow.yaml`, then operator override at `.kittify/workflows/<id>.workflow.yaml` (extension-ready, not load-bearing this mission).
- **Default:** `software-dev-default` produces a byte-identical action sequence to today's hardcoded sequence (C-008 binding).
- **Unknown id:** hard-fails per FR-015. No silent fallback.

References:
- [spec.md §"Scenario 3 — Composable workflow"](../spec.md)
- [spec.md FR-012, FR-013, FR-014, FR-015](../spec.md)
- [plan.md §1.3, §2.7, §2.8](../plan.md)
- [contracts/workflow-sequence-schema.md](../contracts/workflow-sequence-schema.md)
- [data-model.md §5 WorkflowSequence, §6 ActionStep](../data-model.md)
- [atdd-coverage.md Scenario 3 exception (FR-015)](../atdd-coverage.md)

**Dependency on WP09:** Lane D is sequential within itself; WP10 depends on WP09's completion via the lane workspace contract.

**Layer rule (C-001 / NFR-003):** workflow YAMLs live under `src/doctrine/workflows/` (doctrine layer); the registry lives under `src/specify_cli/next/_internal_runtime/` (runtime, the right consumer layer). `charter` does NOT depend on the workflow registry — the registry is consumed by the runtime, not the charter resolver.

---

## ATDD Discipline

Per **C-011** WP10 lands its failing-first test as its FIRST commit:

1. **Commit A (RED, T050):** `tests/specify_cli/next/test_workflow_registry.py` with `test_unknown_workflow_id_hard_fails_with_available_list` (Scenario 3 exception per atdd-coverage.md). RED on planning base because the registry doesn't exist. Commit message: `covers: Scenario 3 exception, FR-015 — expected GREEN at: WP10 final commit`.
2. **Commits B..F (GREEN progression, T051-T055):** schema, registry, default workflow YAML, fixture workflow YAML, regression verification.

ATDD anchor per [atdd-coverage.md](../atdd-coverage.md):
- Scenario 3 exception: `tests/specify_cli/next/test_workflow_registry.py::test_unknown_workflow_id_hard_fails_with_available_list`

---

## Subtasks

### T050 — Land failing-first `tests/specify_cli/next/test_workflow_registry.py`

**File:** `tests/specify_cli/next/test_workflow_registry.py` (new)

```python
"""Workflow registry tests (FR-012, FR-015)."""
from __future__ import annotations

import pytest


def test_get_workflow_loads_software_dev_default():
    from specify_cli.next._internal_runtime.workflow_registry import get_workflow
    wf = get_workflow("software-dev-default")
    assert wf.workflow_id == "software-dev-default"
    assert wf.initial == "specify"
    action_names = [a.action_name for a in wf.actions]
    assert action_names == ["specify", "plan", "tasks", "implement", "review", "merge"]


def test_unknown_workflow_id_hard_fails_with_available_list():
    """FR-015 binding: no silent fallback to software-dev-default."""
    from specify_cli.next._internal_runtime.workflow_registry import (
        get_workflow,
        UnknownWorkflowError,
    )
    with pytest.raises(UnknownWorkflowError) as exc_info:
        get_workflow("does-not-exist")
    msg = str(exc_info.value)
    assert "does-not-exist" in msg
    assert "software-dev-default" in msg  # available list mentioned


def test_get_workflow_loads_fixture_workflow():
    from specify_cli.next._internal_runtime.workflow_registry import get_workflow
    wf = get_workflow("our-team-design-first")
    action_names = [a.action_name for a in wf.actions]
    assert "design-review" in action_names


def test_workflow_sequence_actions_form_dag():
    """Invariant: no cycles; every `next` references an existing action."""
    from specify_cli.next._internal_runtime.workflow_registry import get_workflow
    wf = get_workflow("software-dev-default")
    names = {a.action_name for a in wf.actions}
    for a in wf.actions:
        for n in a.next:
            assert n in names, f"action {a.action_name} references unknown next {n}"
```

**Validation:** `pytest tests/specify_cli/next/test_workflow_registry.py -v` MUST FAIL on planning base. Commit RED.

### T051 — Create `WorkflowSequence` + `ActionStep` Pydantic v2 models

**File:** `src/specify_cli/next/_internal_runtime/workflow_schema.py` (new)

Per data-model §5 + §6:

```python
"""Workflow sequence schema (FR-012)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

__all__ = ["WorkflowSequence", "ActionStep"]


class ActionStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_name: str
    next: list[str] = Field(default_factory=list)
    description: str
    terminal: bool = False

    @model_validator(mode="after")
    def _validate_terminal_has_no_next(self) -> "ActionStep":
        if self.terminal and self.next:
            raise ValueError(
                f"action {self.action_name!r}: terminal=True forbids non-empty `next`"
            )
        return self


class WorkflowSequence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str
    description: str
    actions: list[ActionStep]
    initial: str
    version: int = Field(ge=1)

    @model_validator(mode="after")
    def _validate_invariants(self) -> "WorkflowSequence":
        names = [a.action_name for a in self.actions]
        if len(names) != len(set(names)):
            raise ValueError("action_name values must be unique within a workflow")
        if self.initial not in names:
            raise ValueError(f"initial={self.initial!r} not in actions")
        # all `next` references resolve
        names_set = set(names)
        for a in self.actions:
            for n in a.next:
                if n not in names_set:
                    raise ValueError(
                        f"action {a.action_name!r} references unknown next: {n}"
                    )
        # DAG check: BFS from initial; ensure no cycle
        _check_acyclic(self.actions, self.initial)
        return self


def _check_acyclic(actions: list[ActionStep], start: str) -> None:
    by_name = {a.action_name: a for a in actions}
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            raise ValueError(f"cycle detected at action {node!r}")
        visiting.add(node)
        for n in by_name[node].next:
            dfs(n)
        visiting.remove(node)
        visited.add(node)

    dfs(start)
```

### T052 — Create `workflow_registry.get_workflow`

**File:** `src/specify_cli/next/_internal_runtime/workflow_registry.py` (new)

```python
"""Workflow registry (FR-012, FR-015)."""
from __future__ import annotations

import functools
from pathlib import Path

import yaml

from .workflow_schema import WorkflowSequence

__all__ = ["get_workflow", "list_available_workflows", "UnknownWorkflowError"]


class UnknownWorkflowError(Exception):
    pass


_SEARCH_ROOTS: tuple[Path, ...] = (
    Path(__file__).resolve().parents[4] / "src" / "doctrine" / "workflows",
    Path(__file__).resolve().parents[4] / "src" / "doctrine" / "workflows" / "_fixtures",
)


@functools.lru_cache(maxsize=None)
def get_workflow(workflow_id: str) -> WorkflowSequence:
    for root in _SEARCH_ROOTS:
        candidate = root / f"{workflow_id}.workflow.yaml"
        if candidate.exists():
            data = yaml.safe_load(candidate.read_text())
            return WorkflowSequence.model_validate(data)
    available = list_available_workflows()
    raise UnknownWorkflowError(
        f"Unknown workflow_id={workflow_id!r}. "
        f"Available: {available}. "
        f"Searched: {[str(r) for r in _SEARCH_ROOTS]}."
    )


def list_available_workflows() -> list[str]:
    available: list[str] = []
    for root in _SEARCH_ROOTS:
        if root.exists():
            for p in root.glob("*.workflow.yaml"):
                available.append(p.stem.replace(".workflow", ""))
    return sorted(set(available))
```

### T053 — Create `src/doctrine/workflows/software-dev-default.workflow.yaml`

**File:** `src/doctrine/workflows/software-dev-default.workflow.yaml` (new directory + file)

Declare the existing six-step sequence byte-stable per C-008:

```yaml
# pydantic_model: specify_cli.next._internal_runtime.workflow_schema.WorkflowSequence
# expect: valid
workflow_id: software-dev-default
description: |
  Default software-dev mission workflow. Byte-stable to spec-kitty's
  pre-Slice-F hardcoded sequence (C-008 binding).
version: 1
initial: specify
actions:
  - action_name: specify
    description: Create a mission specification
    next: [plan]
  - action_name: plan
    description: Create an implementation plan
    next: [tasks]
  - action_name: tasks
    description: Decompose plan into work packages
    next: [implement]
  - action_name: implement
    description: Execute a work package implementation
    next: [review]
  - action_name: review
    description: Review a work package implementation
    next: [merge]
  - action_name: merge
    description: Merge a completed mission
    next: []
    terminal: true
```

**Byte-stability verification (C-008):** WP11 will land `test_workflow_software_dev_default_is_byte_stable.py` that pins this against the current hardcoded sequence's `(current_action, next_action)` pairs. WP10's job here is ONLY to land the YAML; WP11 lands the byte-stability test and the runtime integration.

### T054 — Create `src/doctrine/workflows/_fixtures/our-team-design-first.workflow.yaml`

**File:** `src/doctrine/workflows/_fixtures/our-team-design-first.workflow.yaml` (new)

```yaml
# pydantic_model: specify_cli.next._internal_runtime.workflow_schema.WorkflowSequence
# expect: valid
workflow_id: our-team-design-first
description: |
  Test fixture workflow with an extra design-review step between plan and tasks.
  Used by Scenario 3 / AC-4 to prove composable workflow sequencing works.
version: 1
initial: specify
actions:
  - action_name: specify
    description: Create a mission specification
    next: [plan]
  - action_name: plan
    description: Create an implementation plan
    next: [design-review]
  - action_name: design-review
    description: Review the design before decomposing into tasks
    next: [tasks]
  - action_name: tasks
    description: Decompose plan into work packages
    next: [implement]
  - action_name: implement
    description: Execute a work package implementation
    next: [review]
  - action_name: review
    description: Review a work package implementation
    next: [merge]
  - action_name: merge
    description: Merge a completed mission
    next: []
    terminal: true
```

### T055 — Confirm registry tests GREEN; unknown-id hard-fails

```bash
pytest tests/specify_cli/next/test_workflow_registry.py -v
# EXPECTED: GREEN (FR-015 hard-fail asserted; default + fixture loadable)

# Also verify the WP03 round-trip gate accepts both workflow YAMLs:
pytest tests/contract/test_example_round_trip.py -v
# EXPECTED: GREEN (the two .workflow.yaml files have frontmatter)

PWHEADLESS=1 pytest tests/architectural/ -v
# EXPECTED: exit 0 (NFR-005)
```

---

## Definition of Done

The following tests turn GREEN with this WP:

- ✅ `tests/specify_cli/next/test_workflow_registry.py::test_get_workflow_loads_software_dev_default`
- ✅ `tests/specify_cli/next/test_workflow_registry.py::test_unknown_workflow_id_hard_fails_with_available_list` (was RED; FR-015 binding)
- ✅ `tests/specify_cli/next/test_workflow_registry.py::test_get_workflow_loads_fixture_workflow`
- ✅ `tests/specify_cli/next/test_workflow_registry.py::test_workflow_sequence_actions_form_dag`
- ✅ WP03 round-trip gate accepts both workflow YAMLs (they carry `pydantic_model:` + `expect: valid` frontmatter)
- ✅ Full architectural sweep exit 0 (NFR-005)
- ✅ **`tests/contract/test_example_round_trip.py` case `specify_cli.next._internal_runtime.workflow_schema.WorkflowSequence` flips from SKIPPED to PASSED** — WP03 cycle-2 remediation left this case skip-decorated pending the WP10 model. Landing `WorkflowSequence` + `ActionStep` (with their real field shape + validators) MUST turn the case green. This is a binding pre-approval acceptance criterion: the reviewer rejects if the case still shows `SKIPPED` after WP10 lands.

FR coverage:

- ✅ FR-012 — `WorkflowSequence` artifact exists; Pydantic v2 schema validates
- ✅ FR-013 (partial) — registry can resolve a workflow id (runtime integration in WP11)
- ✅ FR-015 — unknown workflow id hard-fails with available-list message

AC coverage:

- ✅ Partial AC-4 — non-default workflow YAML exists (the runtime-side fixture mission demo lands in WP11)

---

## Risks

1. **Layer rule violation** — registry under `src/specify_cli/next/_internal_runtime/` imports doctrine YAML files. Mitigation: this is a runtime consumer of a doctrine artifact (allowed direction per the layer rule). `workflow_schema.py` doesn't import `charter` or `doctrine`; the registry loads YAML from disk, doesn't import doctrine modules. NFR-003 sweep verifies.
2. **`_SEARCH_ROOTS` computed at module load time** binds to package install path. Mitigation: use `importlib.resources` if needed for shipped distribution; for source-checkout development, `Path(__file__).parents[4]` is stable.
3. **`functools.lru_cache` caches across test runs** — a test that mutates a workflow YAML would see stale data. Mitigation: tests use distinct workflow_ids; `lru_cache` is per-process and not shared across pytest sessions.
4. **`our-team-design-first.workflow.yaml` lives under `_fixtures/`** — would WP01's `test_no_dead_modules` flag it as orphaned? Mitigation: workflow YAMLs are doctrine artifacts (not Python modules); they aren't tracked by the dead-modules gate. They MUST be referenced by at least one test (WP11's runtime integration uses this fixture).
5. **DAG check with multi-element `next`** — current implementation traverses all `next` entries. Mitigation: per data-model §6 invariant, Mission C treats `next` as linear (first element wins); the DAG check still works for multi-element lists, just enforces no cycle reachable from `initial`.

---

## Reviewer Guidance

**ATDD red→green verification (mandatory per C-011):**

```bash
# 1. RED on planning base:
git checkout feat/org-doctrine-layer
pytest tests/specify_cli/next/test_workflow_registry.py -v
# EXPECTED: ImportError (workflow_registry doesn't exist)

# 2. GREEN on WP final commit:
git checkout <wp_branch>
pytest tests/specify_cli/next/test_workflow_registry.py -v
# EXPECTED: GREEN (all 4 tests)
```

**Substantive review checks:**

- Confirm `src/doctrine/workflows/software-dev-default.workflow.yaml` declares the exact same six-action sequence as today's hardcoded sequence (`specify → plan → tasks → implement → review → merge`) — REJECT if any action name differs from `ALLOWED_ACTIONS` in Mission B's activation registry (cross-check against `src/charter/activations.py::ALLOWED_ACTIONS`).
- Confirm `merge` has `terminal: true` and empty `next`.
- Confirm `UnknownWorkflowError` message NAMES the unknown id AND lists available workflows (FR-015 binding — REJECT silent fallback).
- Confirm `workflow_schema.py` declares `__all__` per WP02's convention.
- Confirm WP03 round-trip gate accepts both YAMLs (frontmatter present).
- Confirm layer-rule unchanged (NFR-003) — `workflow_registry.py` doesn't import `charter.*`.
- Confirm full architectural sweep exit 0 (NFR-005).

**FR-304 commit-message check:** T050 RED commit cites `covers: Scenario 3 exception, FR-015 — expected GREEN at: WP10 final commit`.

## Activity Log

- 2026-05-18T19:36:31Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=2814171 – Started implementation via action command
- 2026-05-18T19:56:44Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=2814171 – WP10: workflow schema + registry + default workflow YAML; ATDD red→green; WorkflowSchema round-trip flipped SKIPPED→PASSED (3 contract blocks); NFR-001 23/23; no regressions (34 failures, pre-existing); layer rule clean; ruff clean; Category C: 4 workflow registry symbols + 1 module in dead-modules allowlist, removal trigger WP11 get_workflow() call site.
- 2026-05-18T19:57:10Z – claude:sonnet-4-6:reviewer-renata:reviewer – shell_pid=2855827 – Started review via action command
