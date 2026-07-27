---
work_package_id: WP06
title: CI flake + workflow filter-guard (#2812)
dependencies: []
requirement_refs:
- FR-006
- NFR-001
- NFR-002
tracker_refs:
- '#2812'
planning_base_branch: fix/loop-reliability-ci-red-burndown
merge_target_branch: fix/loop-reliability-ci-red-burndown
branch_strategy: Planning artifacts for this mission were generated on fix/loop-reliability-ci-red-burndown. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/loop-reliability-ci-red-burndown unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
history: []
agent_profile: python-pedro
authoritative_surface: tests/runtime/
create_intent: []
execution_mode: code_change
owned_files:
- tests/runtime/test_resolve_by_urn.py
- .github/workflows/ci-quality.yml
role: implementer
tags: []
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2458157"
shell_pid_created_at: "1784458323.2"
---

## ⚡ Do This First: Load Agent Profile
Load `python-pedro` via `/ad-hoc-profile-load`. Load the YAML.

## Objective
Root-fix two CI reds: a warnings-registry parallel flake (`test_resolve_by_urn`) and a workflow filter/guard
mismatch that lets the mission-loader-coverage job skip the code it protects.

**Authoritative grounding**: [`research.md` §3](../research.md), [`data-model.md` LM-5, LM-10](../data-model.md).

## Context / grounding (verified on main)
- **Flake**: `test_legacy_tier_also_wins_over_package_default_on_urn_lane`
  (`tests/runtime/test_resolve_by_urn.py`) uses `catch_warnings(record=True)` + `simplefilter("always")` and
  asserts exactly 1 captured `DeprecationWarning` from `resolver.py:_warn_legacy_asset`. A prior same-worker
  emission populates `resolver.__warningregistry__`; `catch_warnings` filter-restore can leave a later
  same-location `warn()` deduped → 0 captured → red. Passes in isolation; order/worker-dependent (category-2 flake).
- **Workflow anomaly**: `.github/workflows/ci-quality.yml` gates the mission-loader-coverage job `if:` on
  `needs.changes.outputs.next == 'true' || core_misc == 'true'`, but `src/specify_cli/mission_loader/**` maps to
  the **`platform`** filter group — so a `mission_loader/**`-only change skips the gate that protects it.

## Subtasks
### T011 — Root-fix the warnings flake (test-side)
Clear the resolver's warning registry inside the `catch_warnings` block before the `resolve_template_by_urn` call:
`getattr(resolver, "__warningregistry__", {}).clear()` (or an autouse fixture that clears it).
`simplefilter("always")` alone is insufficient (the registry version bump is undone on `catch_warnings` exit).
Resolve by symbol (LM-10).

### T012 — Add `platform` to the loader-coverage gate — BOTH bound sites (LM-5)
The gating decision has **two canonical representations** in `.github/workflows/ci-quality.yml`, bound by an
enforced parity gate (`tests/architectural/test_workflow_coherence.py::test_job_groups_table_equals_parsed_if_gating_live`,
FR-011). You MUST update **both** or that gate reds (a self-inflicted CI red — the opposite of this mission):
1. The job `if:` (~`:1292`): add `|| needs.changes.outputs.platform == 'true'`.
2. The SSOT `JOB_GROUPS["mission-loader-coverage"]` (~`:3958`): add `"platform"` to the list.
Resolve by symbol (LM-10). Confirm the job is self-sufficient (own `uv sync` + coverage run; no `fast-tests-next`
artifact dependency). `platform` already exists as a filter output — no changes-job edit needed. Do NOT split (LM-5).
**Post-merge caveat (gate-unmask-cannot-self-validate):** the runtime effect ("job runs on a `mission_loader/**`-only
change") is NOT observable pre-merge — confirm it via the parity gate + YAML validity here, and note it must be
verified on the first post-merge `mission_loader/**` change.

### Verify
- `PWHEADLESS=1 uv run --extra test pytest tests/runtime/test_resolve_by_urn.py tests/runtime/test_resolver_unit.py -q`
  (run together, to exercise the same-worker registry interaction) → green.
- YAML: confirm the workflow parses (`python -c "import yaml; yaml.safe_load(open('.github/workflows/ci-quality.yml'))"`).
- **Parity gate (MANDATORY — this is what catches the whack-a-field trap):**
  `PWHEADLESS=1 uv run --extra test pytest tests/architectural/test_workflow_coherence.py -q` → green
  (proves the `if:` and `JOB_GROUPS` sites agree).
- ruff on the test file → clean.

## Definition of Done
The registry-clear lands (flake gone across parallel/in-order runs — deterministic root fix, not a retry); BOTH
the loader-coverage `if:` and `JOB_GROUPS` sites carry `platform` and `test_workflow_coherence.py` is green; ruff
clean; workflow YAML valid. (The job-actually-runs runtime effect is post-merge-only verifiable.)

## Reviewer guidance
Confirm the registry-clear is the root fix (not a retry); confirm the `if:` change is 1-line and doesn't perturb
`platform`'s other consumers; confirm the flake is gone when the two runtime test files run in the same worker.

## Activity Log

- 2026-07-19T10:45:27Z – claude:sonnet:python-pedro:implementer – shell_pid=2410645 – Assigned agent via action command
- 2026-07-19T10:51:40Z – claude:sonnet:python-pedro:implementer – shell_pid=2410645 – Ready for review: T011 root-fixed the urn-lane warnings flake by clearing resolver.__warningregistry__ inside catch_warnings before resolve; T012 added platform to both bound sites (job if: + JOB_GROUPS SSOT) for the mission-loader-coverage gate. Parity gate + YAML valid + ruff clean.
- 2026-07-19T10:52:05Z – claude:opus:reviewer-renata:reviewer – shell_pid=2458157 – Started review via action command
