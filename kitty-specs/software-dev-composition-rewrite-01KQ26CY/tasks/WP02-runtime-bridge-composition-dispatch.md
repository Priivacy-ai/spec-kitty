---
work_package_id: WP02
title: Runtime Bridge Composition Dispatch + Collapsed Tasks Guard
dependencies:
- WP01
requirement_refs:
- C-001
- C-002
- C-003
- C-007
- C-008
- FR-001
- FR-003
- FR-004
- FR-005
- FR-007
- FR-008
- FR-009
- NFR-001
- NFR-002
- NFR-003
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
created_at: '2026-04-25T11:39:00+00:00'
subtasks:
- T005
- T006
- T007
- T008
- T009
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "71454"
history:
- at: '2026-04-25T11:39:00Z'
  actor: claude
  action: created
authoritative_surface: src/specify_cli/next/runtime_bridge.py
execution_mode: code_change
mission_slug: software-dev-composition-rewrite-01KQ26CY
owned_files:
- src/specify_cli/next/runtime_bridge.py
- tests/specify_cli/next/test_runtime_bridge_composition.py
priority: P1
tags: []
---

# WP02 — Runtime Bridge Composition Dispatch + Collapsed Tasks Guard

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target branch**: `main`
- During `/spec-kitty.implement` this WP runs in the lane workspace allocated by `lanes.json`; completed changes merge back to `main` unless the human redirects.
- WP02 depends on WP01. Its lane base will be the WP01 head (per spec-kitty's lane chaining), so the WP01 contract + profile default are already on disk when WP02 starts.

## Objective

Wire the runtime bridge so the live path for `software-dev`'s five public actions runs through `StepContractExecutor.execute`. Collapse the legacy `tasks_outline` / `tasks_packages` / `tasks_finalize` post-step guards into one composed `tasks` guard with equivalent semantics. Preserve fall-through to the legacy DAG for any other mission or step ID. After this WP, the live runtime path for `software-dev` is composition-driven; the legacy DAG is only entered for fall-through.

## Context

Read first:
- `kitty-specs/software-dev-composition-rewrite-01KQ26CY/contracts/runtime-bridge-composition-api.md` — binding handoff contract
- `kitty-specs/software-dev-composition-rewrite-01KQ26CY/data-model.md` §Entity 3 — integration seam contract
- `src/specify_cli/next/runtime_bridge.py` — full file, especially:
  - lines 180–225: `_check_step_guards` (the model for the post-action guard)
  - lines 254–360: discovery-context construction (do NOT change; preserved for fall-through)
- `src/specify_cli/mission_step_contracts/executor.py` — `StepContractExecutor`, `StepContractExecutionContext`, `StepContractExecutionError`
- `tests/specify_cli/next/test_runtime_bridge.py` — existing test patterns
- `tests/specify_cli/runtime/test_agent_commands_routing.py` — existing test patterns

Constraints active for this WP:
- **C-001**: Bridge MUST NOT call `ProfileInvocationExecutor` directly for composed actions. Only via `StepContractExecutor.execute`.
- **C-002**: Bridge MUST NOT generate text or call models.
- **C-003 / FR-007**: Lane-state writes inside any composed step MUST go through `emit_status_transition`. No raw lane string writes anywhere this WP touches.
- **C-007**: DO NOT touch any file under `src/spec_kitty_events/` or `.kittify/charter/`. Concurrent agent owns that.
- **C-008**: Composition dispatch MUST be guarded on `mission == "software-dev"`. No other missions.

## Subtasks

### T005 — Add composition dispatch helper

**Purpose**: Insert the single decision point where the bridge stops dispatching legacy DAG step IDs for `software-dev` and routes through composition instead.

**File**: `src/specify_cli/next/runtime_bridge.py` (modify)

**Approach**:
1. Add a small helper function (top-level, near `_check_step_guards`):

```python
_COMPOSED_ACTIONS_BY_MISSION: dict[str, frozenset[str]] = {
    "software-dev": frozenset({"specify", "plan", "tasks", "implement", "review"}),
}

_LEGACY_TASKS_STEP_IDS = frozenset({"tasks_outline", "tasks_packages", "tasks_finalize"})


def _normalize_action_for_composition(step_id: str) -> str:
    """Map legacy DAG step IDs to composed action IDs.

    The legacy mission-runtime.yaml splits ``tasks`` into three steps; the
    composition layer exposes a single ``tasks`` action whose contract
    holds the substructure internally. All other step IDs pass through
    unchanged.
    """
    if step_id in _LEGACY_TASKS_STEP_IDS:
        return "tasks"
    return step_id


def _should_dispatch_via_composition(mission: str, step_id: str) -> bool:
    """Return True if (mission, step_id) routes through StepContractExecutor."""
    composed = _COMPOSED_ACTIONS_BY_MISSION.get(mission)
    if composed is None:
        return False
    return _normalize_action_for_composition(step_id) in composed
```

2. At the existing dispatch site (where the bridge currently calls into the legacy DAG handler after `_check_step_guards`), insert a branch:

```python
if _should_dispatch_via_composition(mission_type, step_id):
    action = _normalize_action_for_composition(step_id)
    return _dispatch_via_composition(
        repo_root=repo_root,
        mission=mission_type,
        action=action,
        actor=actor,
        profile_hint=profile_hint,
        request_text=request_text,
        mode_of_work=mode_of_work,
        feature_dir=feature_dir,
    )
# else: existing legacy DAG path (unchanged)
```

3. Implement `_dispatch_via_composition`:

```python
def _dispatch_via_composition(
    *,
    repo_root: Path,
    mission: str,
    action: str,
    actor: str,
    profile_hint: str | None,
    request_text: str | None,
    mode_of_work: ModeOfWork | None,
    feature_dir: Path,
) -> int:
    """Run a composed action; then fire the post-action guard."""
    from specify_cli.mission_step_contracts.executor import (
        StepContractExecutionContext,
        StepContractExecutionError,
        StepContractExecutor,
    )

    context = StepContractExecutionContext(
        repo_root=repo_root,
        mission=mission,
        action=action,
        actor=actor or "unknown",
        profile_hint=profile_hint,
        request_text=request_text,
        mode_of_work=mode_of_work,
    )
    try:
        StepContractExecutor(repo_root=repo_root).execute(context)
    except StepContractExecutionError as exc:
        # Structured CLI failure, not a Python traceback (FR-009).
        return _emit_cli_error(f"composition failed for {mission}/{action}: {exc}")

    failures = _check_composed_action_guard(action, feature_dir)
    if failures:
        return _emit_cli_error("; ".join(failures))
    return 0
```

(`_emit_cli_error` may need to be a thin wrapper around the bridge's existing error-emission pattern. Use whatever the file already uses; do not invent a new mechanism.)

**Validation**: Branch only fires for `software-dev` + composed actions; everything else falls through. Covered by T008.

### T006 — Implement collapsed `tasks` post-action guard

**Purpose**: Replace the three legacy `_check_step_guards` branches for `tasks_outline` / `tasks_packages` / `tasks_finalize` with one composed `tasks` guard that asserts the union of their conditions, so guard semantics are preserved exactly.

**File**: `src/specify_cli/next/runtime_bridge.py` (modify — extend `_check_step_guards` AND add a sibling for the composed path)

**Approach**:

Add `_check_composed_action_guard(action, feature_dir) -> list[str]`:

```python
def _check_composed_action_guard(action: str, feature_dir: Path) -> list[str]:
    """CLI-level guards that fire AFTER a composed action completes.

    Mirrors `_check_step_guards` semantics for the five composed actions.
    For ``tasks``, collapses the three legacy ``tasks_*`` checks into one.
    """
    failures: list[str] = []

    if action == "specify":
        if not (feature_dir / "spec.md").exists():
            failures.append("Required artifact missing: spec.md")

    elif action == "plan":
        if not (feature_dir / "plan.md").exists():
            failures.append("Required artifact missing: plan.md")

    elif action == "tasks":
        if not (feature_dir / "tasks.md").exists():
            failures.append("Required artifact missing: tasks.md")
        tasks_dir = feature_dir / "tasks"
        if not tasks_dir.is_dir() or not list(tasks_dir.glob("WP*.md")):
            failures.append("Required: at least one tasks/WP*.md file")
        else:
            for wp_file in sorted(tasks_dir.glob("WP*.md")):
                if not _has_raw_dependencies_field(wp_file):
                    failures.append(
                        f"WP {wp_file.stem} missing 'dependencies' in frontmatter "
                        "(run 'spec-kitty agent mission finalize-tasks')"
                    )
                    break

    elif action == "implement":
        if not _should_advance_wp_step("implement", feature_dir):
            failures.append("Not all work packages have required status (for_review, approved, or done)")

    elif action == "review":
        if not _should_advance_wp_step("review", feature_dir):
            failures.append("Not all work packages are approved or done")

    return failures
```

**Validation**: Each negative case still produces a failure. Covered by T008.

### T007 — Wire post-action guard semantics for the other four composed actions

**Purpose**: Ensure parity with legacy `_check_step_guards` for `specify`, `plan`, `implement`, `review` when those actions are dispatched through composition.

**Approach**: This is mostly already handled by T006's `_check_composed_action_guard` for those four actions. Verify:

- `specify` guard: same as legacy `_check_step_guards("specify")`.
- `plan` guard: same as legacy `_check_step_guards("plan")`.
- `implement` guard: same as legacy (`_should_advance_wp_step("implement", ...)`).
- `review` guard: same as legacy (`_should_advance_wp_step("review", ...)`).

**Validation**: T008 asserts each guard's negative case still fires.

### T008 — Write `test_runtime_bridge_composition.py`

**Purpose**: Lock in the integration semantics of the bridge ↔ executor handoff with positive, fall-through, error, and guard-parity coverage.

**File**: `tests/specify_cli/next/test_runtime_bridge_composition.py` (new)

**Test functions** (one per scenario, kept small):

1. `test_dispatch_via_composition_fires_for_software_dev_specify` — call the bridge for `(software-dev, specify)`, mock `StepContractExecutor.execute` to record the call, assert it was called once with the right context, assert legacy DAG handler was NOT called.
2. `test_dispatch_via_composition_fires_for_collapsed_tasks` — call the bridge for legacy step IDs `tasks_outline`, `tasks_packages`, `tasks_finalize`; assert each routes to composed `tasks` (single executor call per invocation).
3. `test_dispatch_falls_through_for_unknown_mission` — call the bridge for `(other-mission, specify)`; assert composition is NOT entered; legacy handler is.
4. `test_dispatch_falls_through_for_unknown_step_id` — call the bridge for `(software-dev, accept)` (legacy step ID outside composed set); assert composition is NOT entered.
5. `test_missing_contract_surfaces_structured_cli_error` — make the executor raise `StepContractExecutionError`; assert a non-zero return code with a clear message; assert no Python traceback escapes.
6. `test_tasks_guard_requires_tasks_md` — invoke composed `tasks` with `tasks.md` missing on a synthetic feature dir; assert guard failure.
7. `test_tasks_guard_requires_wp_files` — `tasks.md` present, `tasks/` empty; assert guard failure.
8. `test_tasks_guard_requires_dependencies_frontmatter` — `tasks.md` and one `WP*.md` present but WP missing `dependencies:` frontmatter; assert guard failure.
9. `test_specify_guard_requires_spec_md` — composed `specify` with no `spec.md`; assert guard failure.
10. `test_plan_guard_requires_plan_md` — composed `plan` with no `plan.md`; assert guard failure.

Use mocking patterns from existing `tests/specify_cli/next/test_runtime_bridge.py`. Do NOT spin up a real `ProfileInvocationExecutor` — use a fake.

**Validation**: All 10 tests pass.

### T009 — Confirm existing bridge / agent-commands tests still pass

**Purpose**: Regression guard.

**Command**:

```bash
cd src && pytest tests/specify_cli/next/test_runtime_bridge.py tests/specify_cli/runtime/test_agent_commands_routing.py -v
```

**Validation**: 100% green.

## Definition of Done

- [ ] `runtime_bridge.py` contains `_should_dispatch_via_composition`, `_normalize_action_for_composition`, `_dispatch_via_composition`, `_check_composed_action_guard`.
- [ ] Composition branch is reachable on the live path for `software-dev`'s five public actions (collapsed `tasks` from any of the three legacy step IDs).
- [ ] `tests/specify_cli/next/test_runtime_bridge_composition.py` exists with the 10 tests listed.
- [ ] `pytest tests/specify_cli/next/ tests/specify_cli/runtime/ tests/specify_cli/mission_step_contracts/` all green.
- [ ] `mypy --strict src/specify_cli/next/runtime_bridge.py` passes.
- [ ] No file under `src/spec_kitty_events/` or `.kittify/charter/` was modified.
- [ ] `mission.yaml` and `mission-runtime.yaml` are NOT modified in this WP (those are WP03's surface).

## Reviewer Guidance

- Confirm composition branch is `mission == "software-dev"` AND action-membership-checked. Any pathway that fires composition for another mission is a bug.
- Confirm the collapsed `tasks` guard asserts the **union** of the three legacy `tasks_*` checks. Read both versions side-by-side.
- Confirm `StepContractExecutionError` translates to a non-zero CLI exit with a clear message — not a Python traceback.
- Confirm `mypy --strict` passes — `runtime_bridge.py` should remain strict-clean.
- Confirm no raw lane string writes added (search for any literal lane name written outside `emit_status_transition`).

## Risks

| Risk | Mitigation |
|------|------------|
| Composition fires for a non-software-dev mission | T008 test #3 asserts negative case. |
| Collapsed `tasks` guard silently weakens validation | T008 tests #6/#7/#8 enumerate each legacy negative case. |
| Composition error escapes as Python traceback | T008 test #5 asserts structured CLI surface. |
| Changes to lane-state writes that bypass typed substrate | Reviewer search for raw lane strings; constraint C-003. |
| `_dispatch_via_composition` accidentally calls `ProfileInvocationExecutor` directly | C-001 violation; reviewer to verify only `StepContractExecutor.execute` is called. |

## Implementation command

`spec-kitty agent action implement WP02 --agent <your-agent-name>`

## Activity Log

- 2026-04-25T11:56:23Z – claude:opus:implementer-ivan:implementer – shell_pid=67398 – Started implementation via action command
- 2026-04-25T12:04:17Z – claude:opus:implementer-ivan:implementer – shell_pid=67398 – Composition dispatch wired with strict mission/action guard; 14 new + 44 legacy bridge + 5 routing + 9 step-contract tests all green; C-001/C-003/C-007/C-008 boundaries respected; tasks_* legacy step IDs normalize to single composed tasks guard with equivalent assertions; mypy --strict clean on runtime_bridge.py.
- 2026-04-25T12:05:07Z – claude:opus:reviewer-renata:reviewer – shell_pid=71454 – Started review via action command
- 2026-04-25T12:08:51Z – claude:opus:reviewer-renata:reviewer – shell_pid=71454 – Review passed: composition dispatch correctly guarded (mission == software-dev + composed action set); collapsed tasks guard preserves legacy semantics; StepContractExecutionError surfaces as Decision(blocked, guard_failures); 4 deviations (function name, return type, insertion site, +4 helper tests) verified as necessary adaptations to actual bridge structure with identical semantic contract; 46+ tests green; mypy --strict clean; C-001/C-003/C-007/C-008 boundaries respected. --force used only because dossier-snapshot blocker would otherwise block move.
