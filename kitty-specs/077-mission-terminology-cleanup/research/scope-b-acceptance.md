# Scope B Acceptance Evidence

**Mission**: `077-mission-terminology-cleanup`  
**Scope**: Scope B (`#543`)  
**Acceptance date**: 2026-04-08  
**Working tree base commit**: `d90a6465f801a160a75c812c404c5936d260eac8`  
**Scope A acceptance**: [`scope-a-acceptance.md`](/private/tmp/241/spec-kitty/kitty-specs/077-mission-terminology-cleanup/research/scope-a-acceptance.md)

## Gate Results

| Gate | Description | Result | Evidence |
|---|---|---|---|
| 1 | Every first-party machine-facing payload identifying a tracked mission carries `mission_slug`, `mission_number`, `mission_type` | PASS | `PYTHONPATH=src .venv/bin/python -m pytest tests/contract/test_machine_facing_canonical_fields.py -q` passed. The contract file now covers status snapshot JSON, board summary JSON, progress JSON, context payloads, acceptance matrix JSON, merge gate evaluation JSON, next decision payloads, orchestrator query payloads, acceptance checklist JSON, kanban/status JSON, worktree topology JSON, enhanced verify payloads, and agent task/implement JSON emitters. |
| 2 | Any remaining `feature_*` field is removed, gated, or marked deprecated | PASS | Code inventory in [`scope-b-inventory.md`](/private/tmp/241/spec-kitty/kitty-specs/077-mission-terminology-cleanup/research/scope-b-inventory.md) was updated during the reroll to capture the residual active JSON emitters that still used raw `"feature"` mission identity. Those emitters now emit canonical mission fields. Historical read-compat remains limited to `status.models.from_dict()` and `status.validate`. Active reference docs now describe only canonical mission fields. |
| 3 | No `mission_run_slug` anywhere in first-party payload codepaths | PASS | `tests/contract/test_machine_facing_canonical_fields.py::test_no_mission_run_slug_in_first_party_payloads` passed. Manual check: `git diff --name-only main -- . | rg "mission_run_slug|MissionRunCreated|MissionRunClosed|aggregate_type=\"MissionRun\"|aggregate_type='MissionRun'"` returned no matches. |
| 4 | `MissionCreated` / `MissionClosed` event names unchanged | PASS | `tests/contract/test_machine_facing_canonical_fields.py::test_mission_created_and_closed_event_names_unchanged` passed. No `MissionRunCreated` or `MissionRunClosed` string exists under `src/specify_cli/**/*.py`. |
| 5 | `aggregate_type="Mission"` unchanged | PASS | `tests/contract/test_machine_facing_canonical_fields.py::test_aggregate_type_mission_unchanged` passed. No `aggregate_type="MissionRun"` or `aggregate_type='MissionRun'` string exists under `src/specify_cli/**/*.py`. |
| 6 | First-party machine-facing surfaces match `spec-kitty-events 3.0.0` field naming | PASS | The combined regression slice `PYTHONPATH=src .venv/bin/python -m pytest tests/contract/test_terminology_guards.py tests/contract/test_machine_facing_canonical_fields.py tests/specify_cli/cli/commands/test_selector_resolution.py tests/specify_cli/cli/commands/agent/test_workflow_canonical_cleanup.py tests/specify_cli/cli/commands/agent/test_tasks_canonical_cleanup.py tests/specify_cli/test_active_mission_removal.py tests/specify_cli/cli/commands/agent/test_wrapper_delegation.py tests/specify_cli/cli/commands/agent/test_json_selector_errors.py tests/contract/test_orchestrator_api.py tests/agent/test_orchestrator_commands_integration.py tests/specify_cli/context/test_models.py tests/specify_cli/context/test_store.py tests/specify_cli/context/test_middleware.py tests/status/test_models.py tests/status/test_views.py tests/specify_cli/status/test_progress.py tests/policy/test_merge_gates.py tests/next/test_decision_unit.py -q` passed with `315 passed in 2.62s`. |
| 7 | Compatibility alias window is documented in one place | PASS | [`orchestrator-api.md`](/private/tmp/241/spec-kitty/docs/reference/orchestrator-api.md) now documents the asymmetric policy explicitly: human CLI migration docs live in [`feature-flag-deprecation.md`](/private/tmp/241/spec-kitty/docs/migration/feature-flag-deprecation.md), while the orchestrator API itself remains canonical-only on `--mission`. [`event-envelope.md`](/private/tmp/241/spec-kitty/docs/reference/event-envelope.md) now documents canonical mission payload identity and historical read-compat boundaries. |
| 8 | Cross-repo consumers show 0 breakages (NFR-006) | PASS | `PYTHONPATH=src .venv/bin/python -m pytest tests/contract/test_cross_repo_consumers.py -q` passed. The fixture imports pinned downstream dependency `spec-kitty-events==3.0.0`, loads its shipped `mission_created.json` and `mission_closed.json` conformance fixtures, and verifies they still use `mission_slug`, `mission_number`, and `mission_type` with no `feature_*` fallback fields. |
| 9 | None of the spec §3.3 non-goals appear in the diff | PASS | Manual check against the current diff returned no matches for `mission_run_slug`, `MissionRunCreated`, `MissionRunClosed`, or `aggregate_type="MissionRun"`. |

## Scope B Outputs

Implemented surfaces:
- `src/specify_cli/acceptance.py`
- `src/specify_cli/agent_utils/status.py`
- `src/specify_cli/cli/commands/agent/tasks.py`
- `src/specify_cli/cli/commands/implement.py`
- `src/specify_cli/core/worktree_topology.py`
- `src/specify_cli/status/models.py`
- `src/specify_cli/status/reducer.py`
- `src/specify_cli/status/views.py`
- `src/specify_cli/status/progress.py`
- `src/specify_cli/context/models.py`
- `src/specify_cli/context/resolver.py`
- `src/specify_cli/acceptance_matrix.py`
- `src/specify_cli/policy/merge_gates.py`
- `src/specify_cli/next/decision.py`
- `src/specify_cli/orchestrator_api/commands.py`
- `src/specify_cli/verify_enhanced.py`
- `tests/contract/test_machine_facing_canonical_fields.py`
- `docs/reference/event-envelope.md`
- `docs/reference/orchestrator-api.md`

## Mission State

Scope B is implementation-complete at the code/doc/test level:
- machine-facing serializers now emit canonical mission identity fields
- orchestrator query, transition, and preflight/error payloads emit canonical mission identity fields
- contract docs are aligned to the current canonical surface
- locked non-goals are covered by tests

Remaining operational work after this artifact:
- run final mission acceptance / merge flow on `main`
