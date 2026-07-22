---
work_package_id: WP05
title: reconcile second-source unions + correct NFR-001 spy
dependencies:
- WP03
requirement_refs:
- C-002
- FR-006
- NFR-001
- NFR-002
tracker_refs:
- '2651'
planning_base_branch: feat/2651-resolver-seam-completion
merge_target_branch: feat/2651-resolver-seam-completion
branch_strategy: Planning artifacts for this mission were generated on feat/2651-resolver-seam-completion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/2651-resolver-seam-completion unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3085214"
shell_pid_created_at: "1784134854.77"
history:
- at: '2026-07-15T12:00:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (IC-08/IC-09, test lane — after WP03)
agent_profile: python-pedro
authoritative_surface: tests/doctrine/test_mission_type_governance_isolation.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/doctrine/test_mission_type_governance_isolation.py
- tests/integration/test_mission_type_resolution_integration.py
- tests/specify_cli/next/test_runtime_bridge_dispatch.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [plan.md](../plan.md) §IC-08/§IC-09 and
[research.md](../research.md) §R5. Depends on WP03 (the resolver now folds the action-grain into `.governance`).
Always `uv run`.

## Objective

Remove the **second source** of the type⊕action union that now lives in two enduring tests (they would
double-union once WP03 lands), and correct the **NFR-001** threshold so it measures the real hot path.

## Context (grounded)

- `tests/doctrine/test_mission_type_governance_isolation.py:157-170` (`_resolve_union`) and
  `tests/integration/test_mission_type_resolution_integration.py:149-156` (`_resolve_union_from_mission`) each
  do `bundle.governance ∪ manual load_action_index`. They are a live **second implementation** of the union
  (C-002 / DIRECTIVE_044) — that is the reason to reconcile, not a value bug.
- **Post-task squad note:** set-union is idempotent, so after WP03 the values do **not** silently corrupt (WP03
  won't leave these red). BUT the manual loops union only a **probe-action subset**, whereas post-WP03
  `bundle.governance` carries **all** actions' grain — so the reconciled value may **widen to a superset**.
  Update exact-value assertions to the all-actions union where they previously reflected the probe subset.
- `tests/specify_cli/next/test_runtime_bridge_dispatch.py:303` (`test_pack_context_from_config_p99`) is the
  **mis-targeted** NFR gate — `PackContext.from_config` never invokes the resolver or `load_action_index`. `:262`
  hits the resolver but **mocks** `action_sequence` (`:267`).

### T014 — Reconcile the two union sites to `bundle.governance`
- Rewrite `_resolve_union` and `_resolve_union_from_mission` to read the resolved `bundle.governance` **directly**
  (no external `load_action_index` loop). Delete the private union loops. Assertions must still hold against
  production's single unioned source (adjust expected values if the previous double-union masked anything).

### T015 — NFR-001 spy on the real hot path
- Replace the `from_config` p99 citation as the NFR-001 gate with a **spy** (monkeypatch/mock of
  `load_action_index`) asserting it is **NOT called** during `resolve_mission_type_context(..., mission_type=X)`
  when only `.action_sequence` is read (the real hot path — not the `:262` mock). Optionally assert it **IS**
  called on first `.governance` access (proving the lazy boundary).

## Branch Strategy

Base = WP03's tip; final merge target `feat/2651-resolver-seam-completion`. Test-only lane after WP03.

## Definition of Done

- Neither `_resolve_union` nor `_resolve_union_from_mission` performs its own `load_action_index` union; both read `bundle.governance`.
- A spy proves the hot `.action_sequence` path calls no `load_action_index`; the `from_config` p99 citation no longer stands in for NFR-001.
- The three suites pass; `ruff` + `mypy --strict` clean.

## Risks / Reviewer guidance

- **Risk:** silently accepting double-union values — verify assertions reflect the single source, not the doubled one.
- **Reviewer:** grep the two test files for any surviving `load_action_index(` union loop → reject (second-source).

## Activity Log

- 2026-07-15T16:52:15Z – claude:sonnet:python-pedro:implementer – shell_pid=3071884 – Assigned agent via action command
- 2026-07-15T17:01:05Z – claude:sonnet:python-pedro:implementer – shell_pid=3071884 – WP05 done: killed both _resolve_union second-source loops (read bundle.governance); NFR-001 spy proves no load_action_index on .action_sequence, called on .governance; 52 passed, ruff clean, owned files mypy-clean (5 pre-existing errors in untouched helpers) (666118774)
- 2026-07-15T17:01:13Z – claude:opus:reviewer-renata:reviewer – shell_pid=3085214 – Started review via action command
- 2026-07-15T17:11:25Z – user – shell_pid=3085214 – Done override: Mission merged to feat/2651-resolver-seam-completion (298d0d4)
