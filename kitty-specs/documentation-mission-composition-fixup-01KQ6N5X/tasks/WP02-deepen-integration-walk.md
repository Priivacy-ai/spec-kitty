---
work_package_id: WP02
title: Deepen integration walk
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T09
- T10
- T11
agent: "claude:opus-4.7:implementer-ivan:implementer"
shell_pid: "34764"
history:
- action: created
  at: '2026-04-27T05:05:00Z'
  by: tasks
authoritative_surface: tests/integration/
execution_mode: code_change
owned_files:
- tests/integration/test_documentation_runtime_walk.py
tags: []
---

# WP-FIX-2 — Deepen Integration Walk

## Objective

Close findings F-3 and F-4. Extend `tests/integration/test_documentation_runtime_walk.py` with: a full-advancement test that drives all 6 actions via `decide_next_via_runtime`, per-action paired-trail-record assertions, and a refactored guard test that asserts via the dispatch path (not the helper directly).

## Context

The current integration walk advances `discover` once and then only previews the next step. It also calls `_check_composed_action_guard()` directly for the missing-artifact assertion. Both gaps weaken the FR-013 / SC-003 / SC-004 contract.

Read first:
- `tests/integration/test_documentation_runtime_walk.py` (current state)
- `tests/integration/test_research_runtime_walk.py` (reference — does it advance multiple actions?)
- `src/specify_cli/next/runtime_bridge.py` `decide_next_via_runtime` signature and `Decision` shape

C-007 (forbidden symbol grep) STILL applies. The new tests MUST NOT mock `_dispatch_via_composition`, `StepContractExecutor.execute`, `ProfileInvocationExecutor.invoke`, frozen-template loaders, `load_validated_graph`, or `resolve_context`.

## Subtasks

### T09 — `test_full_advancement_through_six_actions`

Drive 6 sequential advances. Before each advance, write the gate artifact required for that action:

| Action | Gate artifact to author before advancing |
|---|---|
| discover | `spec.md` |
| audit | `gap-analysis.md` |
| design | `plan.md` |
| generate | `docs/index.md` (or any `docs/*.md`) |
| validate | `audit-report.md` |
| publish | `release.md` |

Pseudocode:

```python
def test_full_advancement_through_six_actions(isolated_repo: Path) -> None:
    """FR-002 / FR-003 / SC-003: dispatch advances every documentation action."""
    feature_dir = _scaffold_documentation_feature(isolated_repo, "demo-docs-walk")
    get_or_start_run("demo-docs-walk", isolated_repo, "documentation")

    actions_in_order = [
        ("discover", "spec.md"),
        ("audit", "gap-analysis.md"),
        ("design", "plan.md"),
        ("generate", "docs/index.md"),  # mkdir docs first
        ("validate", "audit-report.md"),
        ("publish", "release.md"),
    ]

    advanced_actions: list[str] = []
    for action, artifact in actions_in_order:
        # Author the gate artifact for THIS action before advancing.
        path = feature_dir / artifact
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {action}", encoding="utf-8")

        decision = decide_next_via_runtime("demo-docs-walk", isolated_repo, "documentation")
        assert decision.mission == "documentation"
        # Issue / advance — the exact verb depends on the runtime API.
        # Read existing tests for the issuance pattern.
        # ...
        advanced_actions.append(action)

    assert advanced_actions == [a for a, _ in actions_in_order]
```

The implementer must read the existing walk and `decide_next_via_runtime` to find the correct API to actually issue an action (vs preview/query). If the API only previews, find the issuance entry point (likely a separate function or a flag on the same call).

### T10 — Per-action paired-trail-record assertions

After T09's full walk, inspect `<isolated_repo>/.kittify/events/profile-invocations/` and assert:
- 6 directories or filename groupings, one per advancing action.
- Each grouping contains a `started`+`done` (or `started`+`failed`) paired record.
- Each record's `action` field is one of the documentation verbs.

This may live in the same test as T09 (after the loop) or a separate test that reads the trail dir scaffolded by T09.

### T11 — Refactor guard test

Replace the existing `test_missing_artifact_blocks_with_structured_failure` body so it:

1. Scaffolds a feature_dir with `meta.json` only (no spec.md).
2. Calls `decide_next_via_runtime("demo-docs-walk", isolated_repo, "documentation")`.
3. Asserts `Decision.kind == "blocked"` (or whichever field name the schema uses for a guarded outcome).
4. Asserts the failure list / message contains "spec.md".
5. Reads the run snapshot before and after, asserts equal (no advancement).

If the existing `_check_composed_action_guard()` direct call provides coverage that `decide_next_via_runtime` cannot (e.g. testing the helper in isolation), keep it as a SEPARATE helper-level test with a docstring explaining why both exist.

## Verification

- `uv run --python 3.13 --extra test python -m pytest tests/integration/test_documentation_runtime_walk.py -v --timeout=180` — all tests PASS, including T09/T10/T11.
- `grep -nE "import unittest\.mock|@patch\b|mock\.patch|with patch" tests/integration/test_documentation_runtime_walk.py` — must remain 0 substantive matches (only the C-007 docstring listing is allowed).
- `ruff check tests/integration/test_documentation_runtime_walk.py` — clean.
- `mypy --strict tests/integration/test_documentation_runtime_walk.py` — clean.
- Predecessor regression suites (NFR-002): `uv run --python 3.13 --extra test python -m pytest tests/specify_cli/next/test_runtime_bridge_composition.py tests/specify_cli/next/test_runtime_bridge_research_composition.py tests/integration/test_research_runtime_walk.py -q --timeout=120` — green.

## After Implementation

1. `git add tests/integration/test_documentation_runtime_walk.py`
2. `git commit -m "feat(WP-FIX-2): full-walk + dispatch-level guard tests (#502 F-3, F-4)"`
3. `spec-kitty agent tasks mark-status T09 T10 T11 --status done --mission documentation-mission-composition-fixup-01KQ6N5X`
4. `spec-kitty agent tasks move-task WP-FIX-2 --to for_review --mission documentation-mission-composition-fixup-01KQ6N5X --note "T09-T11 complete; 6-action walk + dispatch-level guard; regression green"`

## Reviewer Guidance

- Verify the full walk actually issues 6 actions (not previews); inspect the test to confirm `decide_next_via_runtime` returns a `kind: success` (or equivalent issued-step indicator) on each call, not `kind: query`.
- Verify per-action trail records: 6 paired `started`/`done` records, each with documentation-native action name.
- Verify T11 uses dispatch path (`decide_next_via_runtime`) not the helper directly.
- C-007 grep must remain clean.

## Activity Log

- 2026-04-27T05:21:39Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=34764 – Started implementation via action command
- 2026-04-27T05:26:27Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=34764 – T09-T11 complete; 6-action walk via dispatch + paired trail records + dispatch-level guard
