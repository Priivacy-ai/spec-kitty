---
work_package_id: WP02
title: Root CLI Integration Tests
lane: "doing"
dependencies:
- WP01
base_branch: 053-orchestrator-api-json-contract-fidelity-WP01
base_commit: 7708b81c62d62488da9bfbed3873576d901b1771
created_at: '2026-03-20T12:44:50.117054+00:00'
subtasks:
- T005
- T006
- T007
phase: Phase 2 - Verification
assignee: ''
agent: "codex"
shell_pid: "57980"
review_status: ''
reviewed_by: ''
review_feedback: ''
history:
- timestamp: '2026-03-20T12:31:02Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-003
- NFR-003
- C-002
---

# Work Package Prompt: WP02 – Root CLI Integration Tests

## Objectives & Success Criteria

- A new `TestRootCLIPath` test class exists in `tests/agent/test_json_envelope_contract_integration.py`.
- Tests invoke through the **root CLI app** (`specify_cli.app`), not the orchestrator-api sub-app.
- All test cases produce valid JSON envelopes on stdout.
- All existing tests in the file continue to pass (regression).

## Context & Constraints

**Why this matters**: The existing tests all invoke `specify_cli.orchestrator_api.commands.app` directly. This exercises `_JSONErrorGroup.main()` but NEVER exercises the nested dispatch path through the root CLI. That's exactly the path that was broken (Issue #304, GH issue #3).

**The fix from WP01**: `_JSONErrorGroup.invoke()` now catches errors at the dispatch level. These tests PROVE it works.

**Key files**:
- `tests/agent/test_json_envelope_contract_integration.py` — add tests here
- `src/specify_cli/__init__.py` — root `app` to import for testing
- `src/specify_cli/orchestrator_api/commands.py` — the fixed `_JSONErrorGroup`

**Constraints**:
- C-002: All changes target the 2.x branch.
- Reuse existing test helpers (`_parse_envelope`, `_assert_usage_error`).
- Minimize mocking — the point is testing the REAL command path.

## Subtasks & Detailed Guidance

### Subtask T005 – Add TestRootCLIPath success tests

- **Purpose**: Verify that orchestrator-api commands produce correct JSON envelopes when invoked through the root CLI.

- **Steps**:
  1. At the top of `tests/agent/test_json_envelope_contract_integration.py`, add an import for the root app:
     ```python
     from specify_cli import app as root_app
     ```
  2. Create a new `CliRunner` instance or reuse the existing `runner`.
  3. Add a new test class `TestRootCLIPath` at the end of the file.
  4. Add test method `test_contract_version_success_through_root`:
     ```python
     def test_contract_version_success_through_root(self):
         """contract-version through root CLI produces valid JSON envelope."""
         result = runner.invoke(root_app, ["orchestrator-api", "contract-version"])
         assert result.exit_code == 0, result.output
         data = json.loads(result.output)
         assert data["success"] is True
         assert data["error_code"] is None
         assert data["data"]["api_version"] is not None
     ```
  5. Add test method `test_contract_version_with_provider_through_root`:
     ```python
     def test_contract_version_with_provider_through_root(self):
         """contract-version with --provider-version through root CLI."""
         result = runner.invoke(root_app, [
             "orchestrator-api", "contract-version",
             "--provider-version", "0.1.0",
         ])
         assert result.exit_code == 0, result.output
         data = json.loads(result.output)
         assert data["success"] is True
     ```

- **Files**: `tests/agent/test_json_envelope_contract_integration.py`

- **Parallel?**: Yes — independent of T006.

- **Notes**:
  - The root CLI callback runs `ensure_runtime()` and `check_version_pin()`. These may need to be mocked if they fail in test environments. If so, mock minimally — only `ensure_runtime` and `check_version_pin`, not the command itself.
  - Look at how other tests handle the root CLI callback. If `SPEC_KITTY_TEST_MODE=1` env var is set by conftest, this may already be handled.

### Subtask T006 – Add TestRootCLIPath error tests

- **Purpose**: Verify that parse/usage errors through the root CLI path produce JSON envelopes, not prose. This is the specific regression test for Issue #304.

- **Steps**:
  1. Add test method `test_unknown_flag_through_root`:
     ```python
     def test_unknown_flag_through_root(self):
         """Unknown flag through root CLI must return USAGE_ERROR JSON, not prose."""
         result = runner.invoke(root_app, [
             "orchestrator-api", "contract-version", "--bogus",
         ])
         assert result.exit_code != 0
         _assert_usage_error(result.output, substring="--bogus")
     ```
  2. Add test method `test_unknown_subcommand_through_root`:
     ```python
     def test_unknown_subcommand_through_root(self):
         """Unknown subcommand through root CLI must return USAGE_ERROR JSON."""
         result = runner.invoke(root_app, [
             "orchestrator-api", "nonexistent-command",
         ])
         assert result.exit_code != 0
         _assert_usage_error(result.output, substring="nonexistent-command")
     ```
  3. Add test method `test_missing_required_args_through_root`:
     ```python
     def test_missing_required_args_through_root(self):
         """Missing required args through root CLI must return USAGE_ERROR JSON."""
         result = runner.invoke(root_app, [
             "orchestrator-api", "feature-state",
         ])
         assert result.exit_code != 0
         _assert_usage_error(result.output, substring="--feature")
     ```
  4. Add test method `test_json_flag_rejected_through_root`:
     ```python
     def test_json_flag_rejected_through_root(self):
         """--json flag through root CLI must return USAGE_ERROR (no such flag)."""
         result = runner.invoke(root_app, [
             "orchestrator-api", "contract-version", "--json",
         ])
         assert result.exit_code != 0
         _assert_usage_error(result.output, substring="--json")
     ```

- **Files**: `tests/agent/test_json_envelope_contract_integration.py`

- **Parallel?**: Yes — independent of T005.

- **Notes**:
  - `test_json_flag_rejected_through_root` is the definitive regression test for Issue #304. It exercises the exact path that external orchestrators use and verifies JSON output.
  - If `_parse_envelope` fails to find JSON in the output, the test will fail with a clear assertion error showing what stdout actually contained (prose vs JSON).

### Subtask T007 – Verify existing sub-app tests still pass

- **Purpose**: Regression check. The `invoke()` override must not break the existing direct-invocation test path.

- **Steps**:
  1. Run the full existing test suite:
     ```bash
     pytest tests/agent/test_json_envelope_contract_integration.py tests/agent/test_orchestrator_commands_integration.py -v
     ```
  2. Verify all existing tests pass.
  3. If any failures, diagnose whether they are caused by the `invoke()` override or pre-existing issues.

- **Files**: No files modified — this is a verification step.

- **Parallel?**: No — run after T005 and T006 are written.

- **Notes**: ~50 pre-existing failures exist in the full suite (cross-test pollution, per CLAUDE.md). Only check the two orchestrator test files, not the full suite.

## Test Strategy

**Test commands**:
```bash
# Run just the new tests
pytest tests/agent/test_json_envelope_contract_integration.py -v -k TestRootCLIPath

# Run all orchestrator tests (regression)
pytest tests/agent/test_json_envelope_contract_integration.py tests/agent/test_orchestrator_commands_integration.py -v
```

**Expected results**:
- New `TestRootCLIPath` tests: all pass (6 tests)
- Existing `TestParserErrorsReturnJSON`: all pass (9 tests)
- Existing `TestUsageErrorEnvelopeShape`: all pass (3 tests)
- Existing `TestNoJsonFlagRemoved`: all pass (4 tests)
- Existing `TestValidCommandsStillWork`: all pass (2 tests)
- Existing `TestContractVersion` etc.: all pass

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Root CLI callback (`ensure_runtime`) fails in test env | Mock `ensure_runtime` and `check_version_pin` only. Or check if conftest already handles this. |
| Root app import triggers side effects | Import `app` only, don't call `main()`. CliRunner handles invocation cleanly. |
| Root CLI adds extra output (banner, version warnings) | Set `SPEC_KITTY_NO_BANNER=1` env in test, or parse JSON from last non-empty line (existing `_parse_envelope` already does this). |

## Review Guidance

- **Critical check**: All `TestRootCLIPath` tests pass and exercise the REAL root CLI path.
- **Regression check**: All pre-existing orchestrator test classes still pass.
- **No mocking of the orchestrator-api itself**: Tests must invoke through the root CLI to prove the contract. Only mock root CLI infrastructure if needed.
- **Output validation**: Every error test should produce valid JSON with `error_code: "USAGE_ERROR"` on stdout.

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

## Activity Log

- 2026-03-20T12:31:02Z – system – lane=planned – Prompt created.
- 2026-03-20T12:44:50Z – coordinator – shell_pid=55395 – lane=doing – Assigned agent via workflow command
- 2026-03-20T12:47:46Z – coordinator – shell_pid=55395 – lane=for_review – Root CLI integration tests complete. All 24 contract tests and 58 total orchestrator tests pass.
- 2026-03-20T12:48:03Z – codex – shell_pid=57980 – lane=doing – Started review via workflow command
