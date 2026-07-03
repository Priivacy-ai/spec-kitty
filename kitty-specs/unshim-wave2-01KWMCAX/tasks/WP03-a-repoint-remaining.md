---
work_package_id: WP03
title: 'A-repoint cluster 2: remaining next surface'
dependencies:
- WP01
requirement_refs:
- FR-002
tracker_refs:
- '#'
- '2'
- '2'
- '9'
- '1'
planning_base_branch: tidy/unshim-wave2
merge_target_branch: tidy/unshim-wave2
branch_strategy: Planning artifacts for this mission were generated on tidy/unshim-wave2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/unshim-wave2 unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
phase: Phase 1 - Sequential DAG
assignee: ''
agent: ''
history:
- at: '2026-07-03T17:18:34Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/agent/test_implement_command.py
- tests/agent/test_workflow_charter_context.py
- tests/contract/test_machine_facing_canonical_fields.py
- tests/contract/test_next_no_implicit_success.py
- tests/contract/test_next_no_unknown_state.py
- tests/contract/test_plan_mission_yaml_validates.py
- tests/fixtures/runtime_parity/_capture_baselines.py
- tests/integration/retrospective/test_autonomous_terminus_e2e.py
- tests/integration/retrospective/test_default_flow_generator_failure.py
- tests/integration/retrospective/test_default_flow_healthy.py
- tests/integration/retrospective/test_hic_terminus_e2e.py
- tests/integration/retrospective/test_latency_budget.py
- tests/integration/retrospective/test_lifecycle_hook.py
- tests/integration/retrospective/test_next_mission_sees_change.py
- tests/integration/retrospective/test_opt_out.py
- tests/integration/retrospective/test_policy_source_attribution.py
- tests/integration/retrospective/test_strict_flow_block.py
- tests/integration/retrospective/test_wp04_coverage_branches.py
- tests/integration/test_coord_loop_workflow.py
- tests/integration/test_custom_mission_runtime_walk.py
- tests/integration/test_dashboard_counters.py
- tests/integration/test_documentation_runtime_walk.py
- tests/integration/test_implement_review_retrospect_smoke.py
- tests/integration/test_internal_runtime_engine.py
- tests/integration/test_mission_run_command.py
- tests/integration/test_mission_type_profile_live_wiring.py
- tests/integration/test_planning_artifact_wp.py
- tests/integration/test_research_runtime_walk.py
- tests/integration/test_slice_f_cross_axis.py
- tests/integration/test_workflow_sequence_runtime.py
- tests/perf/test_loader_perf.py
- tests/retrospective/test_gate_decision.py
- tests/specify_cli/events/test_decision_log.py
- tests/specify_cli/missions/test_mission_template_consistency.py
- tests/specify_cli/next/test_decision_dispatch.py
- tests/specify_cli/next/test_decision_validation.py
- tests/specify_cli/next/test_runtime_bridge.py
- tests/specify_cli/next/test_runtime_bridge_composition.py
- tests/specify_cli/next/test_runtime_bridge_dispatch.py
- tests/specify_cli/next/test_runtime_bridge_documentation_composition.py
- tests/specify_cli/next/test_runtime_bridge_research_composition.py
- tests/specify_cli/next/test_workflow_registry.py
- tests/specify_cli/next/test_workflow_software_dev_default_is_byte_stable.py
- tests/specify_cli/next/test_wp_prompt_governance_contract.py
- tests/specify_cli/status/test_progress_integration.py
- tests/specify_cli/test_documentation_template_resolution.py
- tests/specify_cli/test_operational_context_wiring.py
- tests/unit/mission_loader/test_command.py
- tests/unit/mission_loader/test_contract_synthesis.py
- tests/unit/mission_loader/test_loader_facade.py
- tests/unit/mission_loader/test_registry.py
- tests/unit/mission_loader/test_retrospective_marker.py
- tests/unit/mission_loader/test_validator_errors.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – A-repoint cluster 2: remaining next surface

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

Spec FR-002 (IC-02, cluster 2): re-point the remaining **53 files / 173 plain refs /
36 next patch-string sites** (the 2 `test_selector_resolution.py` injectors are WP01's — do not touch that file) **+ 3 unledgered charter refs in the special-case file** (tests/integration, tests/specify_cli, tests/unit, tests/contract,
tests/agent, tests/perf, tests/fixtures, tests/retrospective) from `specify_cli.next*`
to `runtime.next*`. Your owned_files list IS the authoritative file set (derived from the
occurrence-map). Success = zero legacy next refs in your files, all 38 ledger rows proven,
suites green.

SPECIAL CASE: `tests/contract/test_next_no_implicit_success.py` carries BOTH namespaces.
Its charter refs are **monkeypatch.setattr string targets NOT in the ledger** (the AST
census excluded setattr): re-point ALL THREE — the plain import `:38` and both setattr
strings `:46`/`:49` (`specify_cli.charter_preflight.hook.*` →
`specify_cli.charter_runtime.preflight.hook.*`) — then
`grep -n "specify_cli.charter_" tests/contract/test_next_no_implicit_success.py` must
return zero (paste it: the WP06 delete pre-check and the NFR-002 sweep CANNOT see
continuation-line setattr strings; this grep is the only gate). WP05 excludes this file;
log the cross-stream rationale. It is also a CI-only shard — run it locally.

## Subtasks & Detailed Guidance

### Subtask T007 – Plain-import re-points (173 refs across your files)
- Mechanical; run each file after editing. `tests/fixtures/` content may be fixture data — re-point only actual import statements per the ledger.

### Subtask T008 – 36 next patch-site proofs + the 3 unledgered charter refs
- Same protocol as WP02 for the 36 ledgered next sites. The 2 setattr re-points in the special-case file get proofs too (red-first flip works: bogus setattr target → the test's preflight stub stops intercepting → red) and are logged as EXTRA ledger rows (the orchestrator adds them to the map). **Ledger protocol (FR-002)**: every patch-string site you rewrite gets its proof recorded TWICE: (a) a row in this WP file's Activity Log table `file:line → new target → proof form (assertion file::test | red-first flip) → outcome`, and (b) the orchestrator syncs your table into `occurrence_map.yaml`'s `interception_proof` fields on the planning branch at approval (the lane guard blocks kitty-specs edits on lanes — do NOT edit the map yourself from the lane). A site without a proof row is a review reject; bulk sed is a review reject.

### Subtask T009 – Gates
- Run every touched file's tests (the CI-only ones too: `tests/integration/…`, `tests/contract/test_next_no_implicit_success.py`); `grep -rn "specify_cli\.next" <your files>` empty (paste); ruff; commit.

## Test Strategy
```bash
export PATH="$PWD/.venv/bin:$PATH"
PWHEADLESS=1 pytest tests/integration/ tests/unit/ tests/contract/ -q -p no:cacheprovider
grep -rln "specify_cli.next" tests/ | grep -v tests/next/ || echo CLEAN
```

## Risks & Mitigations
- Your file set spans 8 directories — work strictly from owned_files, never glob-edit `tests/specify_cli/**` (WP01's injector file and WP05's charter files live there).

## Review Guidance
- Sample ≥8 ledger rows; verify the special-case file handled BOTH namespaces; confirm zero edits outside owned_files without logged rationale.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-03T17:18:34Z – system – Prompt created.
