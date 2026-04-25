---
work_package_id: WP06
title: ERP Reference Fixture + Integration Tests
dependencies:
- WP05
requirement_refs:
- C-008
- FR-001
- FR-005
- FR-006
- FR-007
- FR-009
- FR-010
- FR-011
- FR-013
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
- T032
- T033
- T034
phase: Phase 4 - End-to-end fidelity
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "48051"
history:
- at: '2026-04-25T17:54:43Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: tests/integration/
execution_mode: code_change
owned_files:
- tests/fixtures/missions/erp-integration/mission.yaml
- tests/fixtures/missions/missing-retrospective/mission.yaml
- tests/fixtures/missions/reserved-shadow/mission.yaml
- tests/integration/test_mission_run_command.py
- tests/integration/test_custom_mission_runtime_walk.py
role: implementer
tags: []
---

# Work Package Prompt: WP06 – ERP Reference Fixture + Integration Tests

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`
- **Actual execution workspace is resolved later** by `/spec-kitty.implement`. Trust the printed lane workspace.

## Objectives & Success Criteria

Land the canonical ERP custom mission fixture (FR-009) and the integration test suite that proves the loader, validator, CLI, composition gate, and decision_required flow all work end-to-end.

Success criteria:
1. `tests/fixtures/missions/erp-integration/mission.yaml` defines the seven-step ERP flow per [quickstart.md](../quickstart.md).
2. `test_mission_run_command.py` covers the CLI happy path + JSON envelope shape lock + validation error envelopes.
3. `test_custom_mission_runtime_walk.py` walks the full ERP runtime: composed step → composed step → decision_required → composed step → … → retrospective marker.
4. Built-in software-dev composition path remains byte-identical (FR-010 regression trap re-asserted at integration level).
5. Suite runs in < 10 s wall-clock locally (NFR-004).

## Context & Constraints

- Fixtures are real YAML files; tests copy them into `tmp_path/.kittify/missions/<key>/mission.yaml` for isolation.
- Tests mock `StepContractExecutor.execute` to avoid invoking model APIs; pattern mirrors existing tests in `tests/specify_cli/next/test_runtime_bridge_composition.py`.
- See [contracts/mission-run-cli.md](../contracts/mission-run-cli.md) for the JSON envelope shape.
- See [research.md](../research.md) §R-005 / §R-006 for composition + decision_required behavior expected.
- Charter constraint: integration tests for CLI commands.

## Subtasks & Detailed Guidance

### Subtask T029 — Author the ERP reference fixture

- **Purpose**: One canonical fixture used by every integration test in this WP and by the perf test in WP07.
- **Steps**:
  1. Create `tests/fixtures/missions/erp-integration/mission.yaml`:
     ```yaml
     mission:
       key: erp-integration
       name: ERP Integration
       version: 0.1.0
       description: Lookup an ERP record, ask the operator a question, and emit a JS adapter.

     steps:
       - id: query-erp
         title: Query the ERP system
         description: Pull the active record set from the ERP integration endpoint.
         agent_profile: researcher-robbie

       - id: lookup-provider
         title: Look up the matching provider
         agent_profile: researcher-robbie
         depends_on: [query-erp]

       - id: ask-user
         title: Confirm the export shape
         description: Ask the operator which export shape to emit.
         requires_inputs: [export_shape]
         depends_on: [lookup-provider]

       - id: create-js
         title: Generate the JS adapter
         agent_profile: implementer-ivan
         depends_on: [ask-user]

       - id: refactor-function
         title: Refactor the legacy function
         agent_profile: implementer-ivan
         depends_on: [create-js]

       - id: write-report
         title: Summarize the run
         agent_profile: researcher-robbie
         depends_on: [refactor-function]

       - id: retrospective
         title: Mission retrospective marker
         description: Reserved structural marker; execution lands in #506-#511.
         depends_on: [write-report]
     ```
  2. Create two failure-mode fixtures:
     - `tests/fixtures/missions/missing-retrospective/mission.yaml` — same as ERP but without the retrospective step.
     - `tests/fixtures/missions/reserved-shadow/mission.yaml` — `mission.key: software-dev` to trigger `MISSION_KEY_RESERVED`.
- **Files**: as listed.
- **Notes**: Keep fixtures minimal; readability matters because they're cited in docs.

### Subtask T030 — Integration test: CLI happy path with `--json`

- **Purpose**: FR-001, FR-013 — JSON envelope shape locked.
- **Steps**:
  1. Create `tests/integration/test_mission_run_command.py`.
  2. Test:
     ```python
     def test_run_command_starts_runtime_with_json_output(tmp_path: Path):
         # Set up: copy fixture into tmp_path/.kittify/missions/erp-integration/
         # Use typer.testing.CliRunner against the mission_type.app, OR
         # call run_custom_mission() and assert against the result envelope.
         from typer.testing import CliRunner
         from specify_cli.cli.commands.mission_type import app
         _setup_project(tmp_path, fixture="erp-integration")

         runner = CliRunner()
         result = runner.invoke(
             app,
             ["run", "erp-integration", "--mission", "erp-q3-rollout", "--json"],
             env={"PWD": str(tmp_path)},
         )

         assert result.exit_code == 0, result.stdout
         envelope = json.loads(result.stdout)
         assert envelope["result"] == "success"
         assert envelope["mission_key"] == "erp-integration"
         assert envelope["mission_slug"] == "erp-q3-rollout"
         assert "mission_id" in envelope
         assert "feature_dir" in envelope
         assert "run_dir" in envelope
         assert envelope["warnings"] == []
     ```
  3. The `_setup_project(tmp_path, fixture)` helper: copies the named fixture from `tests/fixtures/missions/<fixture>/` to `tmp_path/.kittify/missions/<fixture>/` and `chdir`s.
- **Files**: `tests/integration/test_mission_run_command.py`.

### Subtask T031 — Integration test: validation error envelope shape locked

- **Purpose**: FR-005, FR-011, FR-013, NFR-002.
- **Steps**:
  1. Add to `test_mission_run_command.py`:
     ```python
     def test_missing_retrospective_returns_error_envelope(tmp_path):
         _setup_project(tmp_path, fixture="missing-retrospective")
         result = runner.invoke(app, ["run", "missing-retrospective", "--mission", "x", "--json"])
         assert result.exit_code == 2
         envelope = json.loads(result.stdout)
         assert envelope["result"] == "error"
         assert envelope["error_code"] == "MISSION_RETROSPECTIVE_MISSING"
         assert "actual_last_step_id" in envelope["details"]

     def test_reserved_key_shadow_returns_error_envelope(tmp_path):
         _setup_project(tmp_path, fixture="reserved-shadow")
         result = runner.invoke(app, ["run", "software-dev", "--mission", "x", "--json"])
         assert result.exit_code == 2
         envelope = json.loads(result.stdout)
         assert envelope["error_code"] == "MISSION_KEY_RESERVED"

     def test_unknown_mission_key_returns_error_envelope(tmp_path):
         _setup_project(tmp_path, fixture="erp-integration")
         result = runner.invoke(app, ["run", "no-such-key", "--mission", "x", "--json"])
         assert result.exit_code == 2
         envelope = json.loads(result.stdout)
         assert envelope["error_code"] == "MISSION_KEY_UNKNOWN"
     ```
- **Files**: `tests/integration/test_mission_run_command.py`.

### Subtask T032 — Integration test: full ERP runtime walk

- **Purpose**: FR-006, FR-007, FR-009 — end-to-end composition + decision_required.
- **Steps**:
  1. Create `tests/integration/test_custom_mission_runtime_walk.py`.
  2. Test outline:
     ```python
     def test_erp_full_walk(tmp_path: Path):
         _setup_project(tmp_path, fixture="erp-integration")
         # Start the run via the CLI core (not Typer) for direct return values.
         result = run_custom_mission("erp-integration", "erp-walk", tmp_path)
         assert result.exit_code == 0
         run_dir = Path(result.envelope["run_dir"])

         with patch(
             "specify_cli.mission_step_contracts.executor.StepContractExecutor.execute",
             return_value=_fake_execution_result(),
         ):
             # Walk through composed steps until ask-user pauses the runtime.
             for expected_step in ["query-erp", "lookup-provider"]:
                 decision = decide_next_via_runtime(...)
                 assert decision.kind == DecisionKind.step
                 # ... advance

             # ask-user must surface as decision_required
             decision = decide_next_via_runtime(...)
             assert decision.kind == DecisionKind.decision_required

             # Resolve the decision via the engine's API
             provide_decision_answer(run_dir, decision_id, answer="per-record")

             # Continue through composed steps and the retrospective marker
             for expected_step in ["create-js", "refactor-function", "write-report", "retrospective"]:
                 ...

             # Final state: terminal
             final = decide_next_via_runtime(...)
             assert final.kind == DecisionKind.terminal
     ```
  3. The `_fake_execution_result()` returns a `StepContractExecutionResult` with `invocation_ids=("inv-001",)` (mirror what `test_runtime_bridge_composition.py` does).
- **Files**: `tests/integration/test_custom_mission_runtime_walk.py`.

### Subtask T033 — Paired invocation records carry contract action

- **Purpose**: FR-006 invariant from PR #797.
- **Steps**:
  1. Add to `test_custom_mission_runtime_walk.py`:
     ```python
     def test_paired_invocation_records_carry_contract_action(tmp_path):
         # Same setup as test_erp_full_walk.
         # After advancing through the first composed step, read the invocation
         # ledger (existing pattern: file under run_dir or similar) and assert:
         # - exactly one started + one completed record for the step
         # - both records have action == "query-erp" (the step.id, which is also
         #   the contract action under R-004's synthesis convention)
     ```
  2. If the invocation ledger location is non-obvious, look at how PR #797's tests in `test_runtime_bridge_composition.py` read it (search for `invocations`).
- **Files**: `tests/integration/test_custom_mission_runtime_walk.py`.

### Subtask T034 — Built-in dispatch unchanged after widening

- **Purpose**: FR-010 regression trap at integration level.
- **Steps**:
  1. Add to `test_custom_mission_runtime_walk.py` (or a separate `test_builtin_unchanged.py` if cleaner):
     ```python
     def test_software_dev_specify_dispatch_unchanged(composed_software_dev_project):
         # Re-use the existing fixture from test_runtime_bridge_composition.py.
         # Walk one composed step. Assert:
         # - StepContractExecutor.execute called with profile_hint=None
         # - The returned Decision.kind matches the parametrized expectation
         #   from test_composition_success_skips_legacy_dispatch.
     ```
  2. If WP04's tests already cover this, this subtask becomes redundant — verify against WP04's test file before duplicating, and downsize this subtask's body if so.
- **Files**: `tests/integration/test_custom_mission_runtime_walk.py`.
- **Parallel?**: [P].

## Test Strategy (charter required)

```bash
UV_PYTHON=3.13.9 uv run --no-sync pytest tests/integration/test_mission_run_command.py tests/integration/test_custom_mission_runtime_walk.py -q
UV_PYTHON=3.13.9 uv run --no-sync ruff check tests/integration tests/fixtures/missions
UV_PYTHON=3.13.9 uv run --no-sync mypy --strict tests/integration/test_mission_run_command.py tests/integration/test_custom_mission_runtime_walk.py
```

Wall-clock target: < 10 s for the full suite (NFR-004). If it exceeds, profile and reduce.

## Risks & Mitigations

- **Risk**: `provide_decision_answer` API signature differs from what the test assumes.
  - **Mitigation**: Read `_internal_runtime/engine.py::provide_decision_answer` before writing the decision-resume test; mirror its real signature.
- **Risk**: Typer's `CliRunner` doesn't propagate `chdir`-style state cleanly between invocations.
  - **Mitigation**: Use `monkeypatch.chdir(tmp_path)` per test rather than env vars.
- **Risk**: Mocking `StepContractExecutor.execute` at the wrong import path.
  - **Mitigation**: Mirror exactly what `test_runtime_bridge_composition.py` does (`patch("specify_cli.mission_step_contracts.executor.StepContractExecutor.execute", ...)`).

## Review Guidance

- Reviewer runs the full suite and confirms wall-clock < 10 s.
- Reviewer reads the ERP fixture and confirms it matches `quickstart.md` byte-for-byte (modulo whitespace).
- Reviewer confirms test_software_dev_specify_dispatch_unchanged passes (no regression in built-ins).

## Activity Log

- 2026-04-25T17:54:43Z -- system -- Prompt created.
- 2026-04-25T19:04:09Z – claude:sonnet:implementer-ivan:implementer – shell_pid=44631 – Started implementation via action command
- 2026-04-25T19:14:00Z – claude:sonnet:implementer-ivan:implementer – shell_pid=44631 – ERP fixture + integration suite covers FR-001/005/006/007/009/010/011/013; built-in parity preserved
- 2026-04-25T19:14:54Z – claude:opus:reviewer-renata:reviewer – shell_pid=48051 – Started review via action command
