---
work_package_id: WP05
title: 'Runtime Bridge: Dispatch + 5 Guard Branches + Fail-Closed + Bridge Test'
dependencies:
- WP04
requirement_refs:
- FR-007
- FR-008
- FR-009
- FR-012
- FR-013
- FR-014
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T024
history:
- timestamp: '2026-04-26T11:46:43Z'
  actor: claude
  note: Created during /spec-kitty.tasks for mission research-mission-composition-rewrite-v2-01KQ4QVV
authoritative_surface: src/specify_cli/next/
execution_mode: code_change
mission_id: 01KQ4QVVZ4DC6CXA1XCZZAQ8AG
mission_slug: research-mission-composition-rewrite-v2-01KQ4QVV
owned_files:
- src/specify_cli/next/runtime_bridge.py
- tests/specify_cli/next/test_runtime_bridge_research_composition.py
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

# WP05 — Runtime Bridge: Dispatch + 5 Guard Branches + Fail-Closed + Bridge Test

## Objective

Add the `"research"` entry to `_COMPOSED_ACTIONS_BY_MISSION`. Extend `_check_composed_action_guard()` with 5 research action branches (D3) and a **fail-closed default** for unknown research actions (closes the v1 P1 silent-pass finding). Author the bridge test that proves dispatch fires correctly, guards block missing artifacts, fail-closed default fires for unknown actions, and the C-007 forbidden surfaces are NOT mocked.

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Execution worktree: lane-based, allocated by `spec-kitty implement WP05`. Depends on WP04.

## Implementation Command

```bash
spec-kitty agent action implement WP05 --agent <name>
```

## C-007 Enforcement (CRITICAL)

The new test file `test_runtime_bridge_research_composition.py` MUST include this header comment block AS THE FIRST CONTENT OF THE FILE:

```python
"""Bridge-level test for research composition.

C-007 enforcement (spec constraint):
    The following symbols MUST NOT appear in any unittest.mock.patch target
    in this file. Reviewer greps; any hit blocks approval.

        - _dispatch_via_composition
        - StepContractExecutor.execute
        - ProfileInvocationExecutor.invoke
        - _load_frozen_template
        - load_validated_graph
        - resolve_context
"""
```

The reviewer greps the file for those exact identifiers in any patch target. Zero hits required.

## Authoritative References

- `kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/plan.md` — D3 (guard semantics with fail-closed)
- `src/specify_cli/next/runtime_bridge.py:272-274` — `_COMPOSED_ACTIONS_BY_MISSION`
- `src/specify_cli/next/runtime_bridge.py:444-528` — `_check_composed_action_guard()`
- `src/specify_cli/next/runtime_bridge.py:531` — `_dispatch_via_composition()`
- `tests/specify_cli/next/test_runtime_bridge_composition.py` — pattern reference

## Subtask T020 — Add `"research"` to `_COMPOSED_ACTIONS_BY_MISSION`

**Steps**:
1. Open `src/specify_cli/next/runtime_bridge.py`. Locate `_COMPOSED_ACTIONS_BY_MISSION`.
2. Add directly below software-dev's entry:
   ```python
   "research": frozenset({"scoping", "methodology", "gathering", "synthesis", "output"}),
   ```
3. Do NOT modify the software-dev entry, `_should_dispatch_via_composition`, `_normalize_action_for_composition`, or the custom-mission widening branch.

## Subtask T021 — Add 5 research-action branches to `_check_composed_action_guard()`

**Steps**:
1. Locate `_check_composed_action_guard()`. Read its full body to understand the existing branch shape (string-match on `action`, returns `failures` list).
2. Add 5 research branches BEFORE the function's final return. Each branch must check `mission == "research"` AND a specific `action` value:

   ```python
   if mission == "research":
       if action == "scoping":
           if not (feature_dir / "spec.md").is_file():
               failures.append("Required artifact missing: spec.md")
       elif action == "methodology":
           if not (feature_dir / "plan.md").is_file():
               failures.append("Required artifact missing: plan.md")
       elif action == "gathering":
           if not (feature_dir / "source-register.csv").is_file():
               failures.append("Required artifact missing: source-register.csv")
           # Status-event check: at least 3 source_documented events
           if _count_source_documented_events(feature_dir) < 3:
               failures.append("Insufficient sources documented (need >=3)")
       elif action == "synthesis":
           if not (feature_dir / "findings.md").is_file():
               failures.append("Required artifact missing: findings.md")
       elif action == "output":
           if not (feature_dir / "report.md").is_file():
               failures.append("Required artifact missing: report.md")
           if not _publication_approved(feature_dir):
               failures.append("Publication approval gate not passed")
       else:
           # T022 fail-closed default — see below
           ...
   ```

3. The signature of `_check_composed_action_guard()` may not currently take `mission` as a parameter. If it doesn't, you'll need to thread it through. Read the existing call sites in `_dispatch_via_composition()` to understand. Software-dev's existing branches don't need `mission` because they implicitly assume software-dev — but research's branches do. Discuss approach with reviewer if signature change is non-trivial; alternative is a sibling function `_check_research_action_guard()` invoked from `_check_composed_action_guard()` when the mission is research.
4. Helper functions `_count_source_documented_events(feature_dir)` and `_publication_approved(feature_dir)` may need to be authored (reading from `status.events.jsonl` or equivalent). Inspect existing software-dev guard helpers (`_should_advance_wp_step`) for the pattern.

## Subtask T022 — Add fail-closed default for unknown research actions

**Steps**:
1. In the `mission == "research"` branch, after the action-name `elif` chain, add:
   ```python
   else:
       failures.append(f"No guard registered for research action: {action}")
   ```
2. This is the closure of the v1 P1 silent-pass finding. Without this, an unknown research action falls through to the broader function-level fall-through (empty failures = silent pass).
3. Result: any `(mission="research", action=<unknown>)` produces a non-empty failures list, which `_dispatch_via_composition()` propagates as a structured error with no run-state advancement.

## Subtask T023 — Author bridge test with C-007 enforcement

**Steps**:
1. Create `tests/specify_cli/next/test_runtime_bridge_research_composition.py`.
2. **First content of the file MUST be the C-007 header docstring** (see C-007 Enforcement section above).
3. Tests:
   - `test_should_dispatch_via_composition_for_each_research_action` — parametrized over 5 actions; gate returns True.
   - `test_should_not_dispatch_for_unknown_research_action` — parametrized over `["foo", "bar", "init", "publish"]`; gate returns False.
   - `test_fast_path_does_not_load_frozen_template` — patch the frozen-template loader at the module-import level (not via patch target name); call `_should_dispatch_via_composition`; assert loader was not called. **NOTE**: this is the only place a frozen-template loader patch is permissible, because the test goal is precisely "verify no I/O on the fast path." Document that explicitly in a comment. The test asserts a structural invariant (PR #797), not the dispatch behavior.

   Actually — re-reading C-007: it forbids mocks of `_load_frozen_template`. Resolution: this test must use a different technique (e.g. monkeypatch with a recording stub at the import site, or tracing via a sentinel value, NOT `unittest.mock.patch` against the target). If that's not feasible, the test asserts via behavioral observation: time the call (a sub-millisecond `_should_dispatch_via_composition` call cannot have done frozen-template I/O). Choose the technique that demonstrates the invariant without using a patch on a forbidden target. Document the choice in test comments.

   - `test_action_hint_matches_step_id` — for each research action, call `_dispatch_via_composition()` against a real worktree fixture; assert the recorded action_hint == step_id. **MUST NOT** patch `StepContractExecutor.execute`. Use a fake mission feature_dir set up in `tmp_path` with the artifacts the guard requires.
   - `test_no_fallthrough_after_successful_composition` — same pattern; observe that `runtime_next_step` (legacy) is not invoked. Use a sentinel/spy at a non-forbidden boundary (e.g. patch `runtime_next_step` itself if it isn't on the forbidden list — verify against C-007).
   - `test_no_fallthrough_after_failed_composition` — set up feature_dir to make a guard fail; assert structured failure surfaces; assert no fall-through.
   - **5 guard tests** — parametrized over 5 research actions; for each, set up `feature_dir` with no artifacts; call `_check_composed_action_guard(...)`; assert the action's specific failure message appears in the returned list.
   - `test_unknown_research_action_fails_closed` — call `_check_composed_action_guard(mission="research", action="bogus", feature_dir=...)`; assert returned list contains `"No guard registered for research action: bogus"`.
4. Run: `uv run pytest tests/specify_cli/next/test_runtime_bridge_research_composition.py -v`. All tests pass.

## Subtask T024 — Run focused + regression + mypy/ruff

**Steps**:
1. `uv run pytest tests/specify_cli/next/`. Full subdirectory passes.
2. `uv run pytest tests/specify_cli/next/test_runtime_bridge_composition.py`. Software-dev bridge regression green.
3. `uv run mypy --strict src/specify_cli/next/runtime_bridge.py tests/specify_cli/next/test_runtime_bridge_research_composition.py`. Zero new errors.
4. `uv run ruff check <changed>`. Zero new findings.
5. `grep -E "patch\\(.*_dispatch_via_composition|patch\\(.*StepContractExecutor\\.execute|patch\\(.*ProfileInvocationExecutor\\.invoke|patch\\(.*_load_frozen_template|patch\\(.*load_validated_graph|patch\\(.*resolve_context" tests/specify_cli/next/test_runtime_bridge_research_composition.py` returns zero hits.

## Definition of Done

- [ ] `_COMPOSED_ACTIONS_BY_MISSION` carries the new `"research"` entry; software-dev unchanged.
- [ ] `_check_composed_action_guard()` carries 5 research branches + fail-closed default; software-dev branches unchanged.
- [ ] `tests/specify_cli/next/test_runtime_bridge_research_composition.py` exists with the C-007 header docstring + ~10 test functions, all passing.
- [ ] Software-dev bridge regression green.
- [ ] mypy --strict + ruff zero new findings.
- [ ] **Reviewer grep against the C-007 forbidden list returns zero hits.**

## Test Strategy

This WP is where the bridge contract is locked. The test file is the single most important deliverable — it asserts (a) dispatch fires, (b) guards block, (c) unknown actions fail closed, (d) C-007 is not violated. WP06 then proves the same behaviors at the runtime engine layer.

## Risks

| Risk | Mitigation |
|---|---|
| `_check_composed_action_guard` signature doesn't take `mission`. | T021 step 3 documents the alternative (sibling helper). Implementer chooses the lower-impact path. |
| `_count_source_documented_events` / `_publication_approved` helpers don't exist. | T021 step 4 inspects software-dev's analogous helpers; if missing, author them in the same module. |
| Fast-path test (test_fast_path_does_not_load_frozen_template) needs to verify "no I/O" without patching the loader. | T023 step 3 documents the alternative technique; reviewer judgment on acceptability. |

## Reviewer Guidance

- Diff `runtime_bridge.py`: only `_COMPOSED_ACTIONS_BY_MISSION` and `_check_composed_action_guard` modified. No other code touched.
- The new test file's first ~10 lines are the C-007 enforcement docstring.
- `grep` against the C-007 list returns zero hits.
- Run all tests yourself.
