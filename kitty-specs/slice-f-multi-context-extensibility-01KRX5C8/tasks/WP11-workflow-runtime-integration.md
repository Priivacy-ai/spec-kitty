---
work_package_id: WP11
title: Workflow runtime integration — `spec-kitty next` consumes workflow + back-compat + unknown-id hard-fail
dependencies:
- WP10
requirement_refs:
- C-008
- FR-013
- FR-014
- FR-015
- NFR-001
- NFR-005
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T056
- T057
- T058
- T059
- T060
agent: "claude:sonnet-4-6:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/next/_internal_runtime/planner.py
execution_mode: code_change
owned_files:
- src/specify_cli/next/_internal_runtime/planner.py
- src/specify_cli/next/prompt_builder.py
- tests/integration/test_workflow_sequence_runtime.py
- tests/specify_cli/next/test_workflow_software_dev_default_is_byte_stable.py
role: implementer
tags: []
shell_pid: "2921415"
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Scope governance context to Python implementation before reading anything else.

---

## Objective

Wire WP10's workflow registry into the runtime: extend `_internal_runtime/planner.py` to consume `meta.json::workflow_id`; extend `prompt_builder.py` to look up the workflow once per mission run (cached) and resolve next-action via the workflow graph instead of the hardcoded sequence. The default workflow `software-dev-default` produces a byte-identical sequence to today's hardcoded behaviour (C-008 binding). Pre-Slice-F missions (no `workflow_id` in `meta.json`) get the default — **permanent default per NEW-2 resolution** (opt-in, not migration-required).

This closes Scenario 3 (composable workflow operational), AC-4 (non-default workflow YAML produces documented step diff in `spec-kitty next`), and the byte-stability contract.

---

## Context

After WP10, the workflow registry exists. WP11 makes the runtime actually CONSUME workflows. Two surfaces change:

1. **`_internal_runtime/planner.py::plan_next`** — currently uses a hardcoded action sequence. Slice F adds a workflow-resolver shim: when the mission's `meta.json` carries `workflow_id`, the planner consults the workflow registry to determine the action graph; when absent, it falls back to `software-dev-default`. Unknown `workflow_id` hard-fails via WP10's `UnknownWorkflowError` (no silent fallback).
2. **`prompt_builder.py`** — looks up the workflow once at mission start (cached per mission run) and resolves next-action via the workflow's action graph.

Byte-stability contract (C-008):

> `software-dev-default` MUST produce a byte-identical action sequence to today's hardcoded behaviour. Pinned by a contract test that asserts: for every `(current_action, next_action)` pair the hardcoded sequence produced, the loaded default workflow produces the same pair.

References:
- [spec.md §"Scenario 3 — Composable workflow"](../spec.md)
- [spec.md FR-013, FR-014, FR-015, C-008](../spec.md)
- [plan.md §1.3, §2.9, §2.10](../plan.md)
- [data-model.md §9 Mission.meta_json.workflow_id](../data-model.md#9-missionmeta_jsonworkflow_id--metajson-extension-fr-013)
- [atdd-coverage.md Scenario 3, AC-4](../atdd-coverage.md)

**Dependency on WP10:** WP11 sequentially depends on WP10 (registry must exist before runtime can consume it).

---

## ATDD Discipline

Per **C-011** WP11 lands two failing-first tests as its FIRST two commits:

1. **Commit A (RED, T056):** `tests/integration/test_workflow_sequence_runtime.py` with Scenario 3 happy path + AC-4 step-diff assertion. RED on planning base. Commit message: `covers: Scenario 3, AC-4 — expected GREEN at: WP11 final commit`.
2. **Commit B (RED, T057):** `tests/specify_cli/next/test_workflow_software_dev_default_is_byte_stable.py`. RED on planning base because the workflow lookup is not yet wired into the runtime. Commit message: `covers: FR-014, C-008 — expected GREEN at: WP11 final commit`.
3. **Commits C..E (GREEN progression, T058-T060):** wire planner, wire prompt_builder, verify regression.

ATDD anchors per [atdd-coverage.md](../atdd-coverage.md):
- Scenario 3: `test_non_default_workflow_id_produces_extra_design_review_step`
- AC-4: `test_fixture_mission_with_workflow_id_produces_documented_step_diff`
- FR-014 / C-008: `test_workflow_software_dev_default_is_byte_stable`

---

## Subtasks

### T056 — Land failing-first runtime integration tests

**File:** `tests/integration/test_workflow_sequence_runtime.py` (new)

```python
"""Workflow runtime integration tests (FR-013, FR-014, FR-015, Scenario 3, AC-4)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def fixture_mission_with_workflow_id(tmp_path: Path) -> Path:
    """Scaffold a mission with meta.json::workflow_id = our-team-design-first."""
    mission_dir = tmp_path / "kitty-specs" / "demo-mission-01ABCDEF"
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text(json.dumps({
        "mission_id": "01ABCDEF000000000000000000",
        "mission_slug": "demo-mission",
        "mission_number": None,
        "friendly_name": "Demo",
        "workflow_id": "our-team-design-first",
    }))
    return mission_dir


def test_non_default_workflow_id_produces_extra_design_review_step(
    fixture_mission_with_workflow_id: Path,
) -> None:
    """Scenario 3: spec-kitty next returns commands per the new sequence."""
    from specify_cli.next._internal_runtime.planner import plan_next
    # Assume the mission is at action=plan; expected next=design-review
    result = plan_next(
        mission_dir=fixture_mission_with_workflow_id,
        current_action="plan",
    )
    assert result.next_action == "design-review"


def test_fixture_mission_with_workflow_id_produces_documented_step_diff(
    fixture_mission_with_workflow_id: Path,
) -> None:
    """AC-4: documented step diff from default."""
    from specify_cli.next._internal_runtime.planner import plan_next
    # default would be tasks; with our-team-design-first, plan -> design-review -> tasks
    result_with_id = plan_next(
        mission_dir=fixture_mission_with_workflow_id, current_action="plan",
    )
    assert result_with_id.next_action == "design-review", (
        "Expected non-default workflow to insert design-review between plan and tasks"
    )


def test_mission_without_workflow_id_uses_software_dev_default(tmp_path: Path) -> None:
    """NEW-2 permanent default: pre-Slice-F missions work unchanged."""
    mission_dir = tmp_path / "kitty-specs" / "legacy-mission-01XXXXXX"
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text(json.dumps({
        "mission_id": "01XXXXXX000000000000000000",
        "mission_slug": "legacy",
        "mission_number": None,
    }))  # no workflow_id
    from specify_cli.next._internal_runtime.planner import plan_next
    result = plan_next(mission_dir=mission_dir, current_action="plan")
    assert result.next_action == "tasks"  # byte-stable default


def test_unknown_workflow_id_in_meta_json_hard_fails(tmp_path: Path) -> None:
    """FR-015 binding: no silent fallback."""
    mission_dir = tmp_path / "kitty-specs" / "broken-mission-01ZZZZZZ"
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text(json.dumps({
        "mission_id": "01ZZZZZZ000000000000000000",
        "mission_slug": "broken",
        "mission_number": None,
        "workflow_id": "does-not-exist",
    }))
    from specify_cli.next._internal_runtime.planner import plan_next
    from specify_cli.next._internal_runtime.workflow_registry import UnknownWorkflowError
    with pytest.raises(UnknownWorkflowError):
        plan_next(mission_dir=mission_dir, current_action="plan")
```

**Validation:** RED on planning base. Commit RED.

### T057 — Land failing-first byte-stability test

**File:** `tests/specify_cli/next/test_workflow_software_dev_default_is_byte_stable.py` (new)

```python
"""C-008: software-dev-default workflow is byte-stable to hardcoded sequence."""
from __future__ import annotations


# The pre-Slice-F hardcoded sequence the new YAML must match:
_HARDCODED_SEQUENCE: list[tuple[str, str | None]] = [
    ("specify", "plan"),
    ("plan", "tasks"),
    ("tasks", "implement"),
    ("implement", "review"),
    ("review", "merge"),
    ("merge", None),
]


def test_default_workflow_produces_byte_stable_pairs() -> None:
    """For every (current, next) pair the hardcoded sequence produced,
    the loaded software-dev-default workflow MUST produce the same pair."""
    from specify_cli.next._internal_runtime.workflow_registry import get_workflow
    wf = get_workflow("software-dev-default")
    by_name = {a.action_name: a for a in wf.actions}
    for current, expected_next in _HARDCODED_SEQUENCE:
        action = by_name[current]
        actual_next = action.next[0] if action.next else None
        assert actual_next == expected_next, (
            f"byte-stability violation: from {current!r} expected next={expected_next!r}, "
            f"got {actual_next!r}"
        )
```

**Validation:** RED on planning base — `get_workflow` may exist (WP10) but the integration test still fails because either (a) the workflow YAML wasn't deployed yet, OR (b) the registry isn't wired to the runtime (the test only exercises the registry directly so it should pass on WP10's HEAD; this test is more of a contract pin than a runtime gate). If RED needs to be guaranteed, gate the assertion on a runtime call: `plan_next(...).next_action` for each pair.

**Reviewer note:** if the byte-stability test passes on WP10's HEAD because it only consults the registry, treat it as a contract pin rather than a red→green ATDD test, and document this in the commit message.

### T058 — Extend `planner.py` to consume `meta.json::workflow_id`

**File:** `src/specify_cli/next/_internal_runtime/planner.py`

Locate the existing `plan_next` function. Add the workflow-resolver shim:

```python
import json
from pathlib import Path

from .workflow_registry import get_workflow, UnknownWorkflowError
from .workflow_schema import WorkflowSequence


def _resolve_workflow_for_mission(mission_dir: Path) -> WorkflowSequence:
    meta_path = mission_dir / "meta.json"
    if not meta_path.exists():
        return get_workflow("software-dev-default")
    meta = json.loads(meta_path.read_text())
    workflow_id = meta.get("workflow_id")
    if workflow_id is None:
        return get_workflow("software-dev-default")
    # Unknown ids propagate UnknownWorkflowError -- no silent fallback (FR-015 binding).
    return get_workflow(workflow_id)


def plan_next(mission_dir: Path, current_action: str, **kwargs):
    workflow = _resolve_workflow_for_mission(mission_dir)
    by_name = {a.action_name: a for a in workflow.actions}
    action = by_name.get(current_action)
    if action is None:
        raise ValueError(
            f"action {current_action!r} not in workflow {workflow.workflow_id!r}. "
            f"Available: {sorted(by_name)}"
        )
    next_action = action.next[0] if action.next else None
    return PlanResult(
        current_action=current_action,
        next_action=next_action,
        workflow_id=workflow.workflow_id,
    )
```

The existing `PlanResult` dataclass may need extension to carry `workflow_id`. If `plan_next` currently has a different signature, adapt the integration to be minimally invasive while preserving the public surface.

### T059 — Extend `prompt_builder.py` to look up workflow once per mission run (cached)

**File:** `src/specify_cli/next/prompt_builder.py`

Add a per-mission cache so the workflow YAML is loaded once per mission run:

```python
import functools

@functools.lru_cache(maxsize=128)
def _cached_workflow_for(mission_dir_str: str):
    from ._internal_runtime.planner import _resolve_workflow_for_mission
    return _resolve_workflow_for_mission(Path(mission_dir_str))


def build_prompt(mission_dir, current_action, **kwargs):
    workflow = _cached_workflow_for(str(mission_dir))
    # ... use workflow.actions to render next-step guidance
    ...
```

For single-process runtime invocations, `lru_cache(maxsize=128)` is sufficient; for long-lived processes mutating mission state, a cache invalidation hook may be needed. NEW-2 resolution (permanent default) means cache invalidation is rare — operators don't typically swap workflow_id mid-mission.

### T060 — Confirm Scenario 3 + AC-4 GREEN; byte-stability + permanent default verified

```bash
pytest tests/integration/test_workflow_sequence_runtime.py -v
# EXPECTED: GREEN (Scenario 3 + AC-4 + permanent default + FR-015 hard-fail)

pytest tests/specify_cli/next/test_workflow_software_dev_default_is_byte_stable.py -v
# EXPECTED: GREEN (C-008 byte-stability)

pytest tests/specify_cli/next/test_wp_prompt_governance_contract.py -v
# EXPECTED: 23/23 unchanged (NFR-001 — pre-Slice-F missions get default workflow)

PWHEADLESS=1 pytest tests/architectural/ -v
# EXPECTED: exit 0 (NFR-005)
```

---

## Definition of Done

The following tests turn GREEN with this WP:

- ✅ `tests/integration/test_workflow_sequence_runtime.py::test_non_default_workflow_id_produces_extra_design_review_step` (was RED)
- ✅ `tests/integration/test_workflow_sequence_runtime.py::test_fixture_mission_with_workflow_id_produces_documented_step_diff` (was RED)
- ✅ `tests/integration/test_workflow_sequence_runtime.py::test_mission_without_workflow_id_uses_software_dev_default` (NEW-2 permanent default)
- ✅ `tests/integration/test_workflow_sequence_runtime.py::test_unknown_workflow_id_in_meta_json_hard_fails` (FR-015)
- ✅ `tests/specify_cli/next/test_workflow_software_dev_default_is_byte_stable.py::test_default_workflow_produces_byte_stable_pairs` (C-008)
- ✅ 23 governance-contract fixtures pass unchanged (NFR-001)
- ✅ Full architectural sweep exit 0 (NFR-005)

FR coverage:

- ✅ FR-013 — `meta.json::workflow_id` field consumed by runtime; absent ⇒ default
- ✅ FR-014 — `software-dev-default` workflow produces byte-identical action sequence
- ✅ FR-015 — unknown `workflow_id` hard-fails; no silent fallback
- ✅ C-008 — byte-stability pinned by contract test

AC coverage:

- ✅ AC-4 — fixture mission with `workflow_id` produces a `spec-kitty next` flow that differs from default at the documented step (`design-review` between `plan` and `tasks`)

---

## Risks

1. **Caching causes stale workflow lookup** when an operator edits a workflow YAML mid-session. Mitigation: `lru_cache` is per-process; restart the CLI to pick up changes. Document this in the runtime quickstart.
2. **`plan_next`'s existing signature is incompatible with the new resolver** (e.g. it takes a `MissionTemplate` rather than a `mission_dir`). Mitigation: T058 keeps the existing signature backward-compat and extracts `mission_dir` from the template; the new behaviour layers on top.
3. **Byte-stability test fails because `_HARDCODED_SEQUENCE` was already different from the YAML** — surfaces a pre-existing inconsistency. Mitigation: T057's hardcoded sequence is read from the architect's spec (specify → plan → tasks → implement → review → merge); if the runtime's actual sequence differs, the discrepancy is a Slice F finding, not a regression.
4. **NEW-2 permanent default surfaces a missed migration** — some downstream code path expects `workflow_id` to be present. Mitigation: T058's `_resolve_workflow_for_mission` returns the default workflow when `workflow_id` is None; the rest of the code path operates on a `WorkflowSequence` regardless. Test `test_mission_without_workflow_id_uses_software_dev_default` covers this.
5. **`prompt_builder` change is too invasive** — touches a hot path; risk of breaking existing tests. Mitigation: T059 minimally adds the workflow lookup; existing `build_prompt` logic is preserved. Run the 23-fixture suite after each commit.

---

## Reviewer Guidance

**ATDD red→green verification (mandatory per C-011):**

```bash
# 1. RED on planning base:
git checkout feat/org-doctrine-layer
pytest tests/integration/test_workflow_sequence_runtime.py \
       tests/specify_cli/next/test_workflow_software_dev_default_is_byte_stable.py -v
# EXPECTED: failures (runtime doesn't consume workflow_id yet)

# 2. GREEN on WP final commit:
git checkout <wp_branch>
pytest tests/integration/test_workflow_sequence_runtime.py \
       tests/specify_cli/next/test_workflow_software_dev_default_is_byte_stable.py -v
# EXPECTED: GREEN
```

**Substantive review checks:**

- Confirm `planner.py::_resolve_workflow_for_mission` returns `software-dev-default` when `workflow_id` is absent (NEW-2 permanent default).
- Confirm unknown `workflow_id` propagates `UnknownWorkflowError` — REJECT if any silent fallback path is added (FR-015 binding).
- Confirm `prompt_builder.py` calls the workflow registry through the cached lookup; cache is per-process; no global mutable state.
- Confirm 23 governance-contract fixtures pass unchanged (NFR-001 — pre-Slice-F missions don't have `workflow_id`, so they get the default which is byte-stable).
- Confirm full architectural sweep exit 0 (NFR-005).
- Confirm byte-stability test pins the same `(current, next)` pairs the hardcoded sequence produced (C-008 binding — REJECT if any pair differs).

**FR-304 commit-message check:** T056 RED commit cites `covers: Scenario 3, AC-4`. T057 RED commit cites `covers: FR-014, C-008`.

## Activity Log

- 2026-05-18T20:08:49Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=2879721 – Started implementation via action command
- 2026-05-18T20:28:45Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=2879721 – WP11: workflow registry wired into planner/prompt_builder; WP10 Category C allowlist removed (4 symbols + 1 module); byte-stability test landed; NFR-001 23/23 unchanged (behavioral parity preserved); no regressions.
- 2026-05-18T20:29:29Z – claude:sonnet-4-6:reviewer-renata:reviewer – shell_pid=2921415 – Started review via action command
- 2026-05-18T20:40:43Z – claude:sonnet-4-6:reviewer-renata:reviewer – shell_pid=2921415 – WP11 approved: workflow registry wired into planner/prompt_builder; NFR-001 23/23 preserved (behavioral parity verified); WP10 Cat-C/Cat-5 allowlist deleted with dead-code gates still passing; UnknownWorkflowError raises (no silent fallback per FR-015); layer rule + no C2 clean; byte-stability test landed. No regressions.
