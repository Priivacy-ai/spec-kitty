---
work_package_id: WP04
title: Profile Defaults + Composition Resolution Test
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-009
- FR-011
- FR-014
planning_base_branch: main
merge_target_branch: main
branch_strategy: Current branch main; planning base main; merge target main; lane-based execution worktree per finalize-tasks. Depends on WP01, WP02, WP03 — all must be merged or available in lane base.
subtasks:
- T016
- T017
- T018
- T019
history:
- timestamp: '2026-04-26T11:46:43Z'
  actor: claude
  note: Created during /spec-kitty.tasks for mission research-mission-composition-rewrite-v2-01KQ4QVV
authoritative_surface: src/specify_cli/mission_step_contracts/
execution_mode: code_change
mission_id: 01KQ4QVVZ4DC6CXA1XCZZAQ8AG
mission_slug: research-mission-composition-rewrite-v2-01KQ4QVV
owned_files:
- src/specify_cli/mission_step_contracts/executor.py
- tests/specify_cli/mission_step_contracts/test_research_composition.py
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

# WP04 — Profile Defaults + Composition Resolution Test

## Objective

Add 5 `("research", action)` entries to `_ACTION_PROFILE_DEFAULTS` in `executor.py`. Author the unit test that proves contracts (WP02), action doctrine bundles (WP02), DRG nodes (WP03), and profile defaults all resolve correctly. Software-dev sentinel test confirms no regression.

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Execution worktree: lane-based, allocated by `spec-kitty implement WP04`. Depends on WP01, WP02, WP03 — all must be in the lane base.

## Implementation Command

```bash
spec-kitty agent action implement WP04 --agent <name>
```

## Authoritative References

- `kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/plan.md` — D2 (profile names) and D5 (re-author)
- `src/specify_cli/mission_step_contracts/executor.py:39-45` — `_ACTION_PROFILE_DEFAULTS` (the additive map edit)
- `tests/specify_cli/mission_step_contracts/test_software_dev_composition.py` — test pattern to mirror

## Subtask T016 — Verify profile names exist

**Steps**:
1. Run `rg -n "researcher-robbie" src/doctrine/agent_profiles/shipped/`. Expect a hit at `researcher-robbie.agent.yaml`.
2. Run `rg -n "reviewer-renata" src/doctrine/agent_profiles/shipped/`. Expect a hit at `reviewer-renata.agent.yaml`.
3. Both profile names confirmed in the audit. If either is missing or renamed, halt the WP and escalate.
4. Record paths in your commit message.

**Files**: read-only.

## Subtask T017 — Add 5 entries to `_ACTION_PROFILE_DEFAULTS`

**Steps**:
1. Open `src/specify_cli/mission_step_contracts/executor.py`. Locate `_ACTION_PROFILE_DEFAULTS` (lines 39-45 on baseline).
2. Add 5 entries directly below the existing software-dev entries:
   ```python
   ("research", "scoping"): "researcher-robbie",
   ("research", "methodology"): "researcher-robbie",
   ("research", "gathering"): "researcher-robbie",
   ("research", "synthesis"): "researcher-robbie",
   ("research", "output"): "reviewer-renata",
   ```
3. Do NOT modify any software-dev entry.
4. Do NOT add wildcard keys (C-003).
5. Do NOT modify any other code in `executor.py`. Map edit only.
6. Verify type: `uv run mypy --strict src/specify_cli/mission_step_contracts/executor.py`. Zero new errors.

**Files**: `src/specify_cli/mission_step_contracts/executor.py` (additive map only).

## Subtask T018 — Author `test_research_composition.py`

**Steps**:
1. Create `tests/specify_cli/mission_step_contracts/test_research_composition.py`.
2. Mirror `test_software_dev_composition.py` (read it first).
3. Tests:
   - `test_all_research_contracts_load` — parametrized over 5 actions; each `research-<action>.step-contract.yaml` loads via `MissionStepContractRepository`; mission == "research", action matches.
   - `test_research_profile_defaults_resolved` — parametrized; `_ACTION_PROFILE_DEFAULTS[("research", action)]` returns expected profile.
   - `test_research_doctrine_bundle_resolved` — parametrized; doctrine resolver returns non-empty content for each action.
   - `test_research_drg_node_resolves_non_empty_context` — parametrized; `load_validated_graph(repo).get_node('action:research/<action>')` truthy AND `resolve_context(...).artifact_urns` non-empty. (Overlaps with WP03's test but at the composition surface — this asserts what the composition path actually uses.)
   - `test_no_software_dev_regression` — sentinel; software-dev `_ACTION_PROFILE_DEFAULTS` entries unchanged.
4. **Do NOT mock the C-007 forbidden surfaces** in this file. The unit test layer can mock minor things, but `_ACTION_PROFILE_DEFAULTS` (the dict literal in executor.py) and `load_validated_graph` / `resolve_context` MUST be read live.
5. Run: `uv run pytest tests/specify_cli/mission_step_contracts/test_research_composition.py -v`. All tests pass.

**Files**: `tests/specify_cli/mission_step_contracts/test_research_composition.py` (new).

## Subtask T019 — Run focused + regression

**Steps**:
1. `uv run pytest tests/specify_cli/mission_step_contracts/`. Full subdirectory passes (existing + new).
2. `uv run pytest tests/specify_cli/next/test_runtime_bridge_composition.py`. Software-dev bridge regression green.
3. `uv run mypy --strict src/specify_cli/mission_step_contracts/executor.py tests/specify_cli/mission_step_contracts/test_research_composition.py`. Zero new errors.
4. `uv run ruff check <changed files>`. Zero new findings.

**Files**: no edits unless tooling requires.

## Definition of Done

- [ ] `_ACTION_PROFILE_DEFAULTS` carries 5 new `("research", action)` entries; software-dev unchanged.
- [ ] No other code in `executor.py` modified.
- [ ] `tests/specify_cli/mission_step_contracts/test_research_composition.py` exists with 5 test functions, all passing.
- [ ] `mission_step_contracts/` regression green; software-dev bridge regression green.
- [ ] mypy --strict + ruff zero new findings.
- [ ] No mocks of `load_validated_graph` / `resolve_context` in the test file.
- [ ] No edits outside `owned_files`.

## Test Strategy

This is the first integration-test gate after the foundation WPs. It proves all 4 substrate pieces (contract, doctrine bundle, DRG node, profile default) line up at the composition resolver layer. It does NOT prove dispatch or runtime advancement — that's WP05 + WP06.

## Risks

| Risk | Mitigation |
|---|---|
| Profile names drifted before this WP. | T016 verifies; halt if missing. |
| Software-dev sentinel fails because someone touched defaults elsewhere. | Test inspects the actual map; failure indicates a real regression elsewhere — escalate. |
| DRG node lookup test duplicates WP03's test. | Acceptable: WP03 asserts at the helper level; WP04 asserts at the composition layer (different surface). |

## Reviewer Guidance

- Diff `executor.py`: only the dict gains 5 entries.
- Test file mirrors `test_software_dev_composition.py` structure.
- Run all tests yourself.
- `grep -E "patch.*load_validated_graph|patch.*resolve_context|patch.*_dispatch_via_composition|patch.*StepContractExecutor.execute|patch.*ProfileInvocationExecutor.invoke|patch.*_load_frozen_template" tests/specify_cli/mission_step_contracts/test_research_composition.py` returns zero hits.
