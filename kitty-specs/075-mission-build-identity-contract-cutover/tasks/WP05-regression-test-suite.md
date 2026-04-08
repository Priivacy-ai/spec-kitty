---
work_package_id: WP05
title: Regression and Non-Regression Test Suite
dependencies:
- WP02
- WP04
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-005
- FR-006
- FR-010
- FR-011
- FR-014
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
- T032
- T033
shell_pid: '19150'
history:
- date: '2026-04-08'
  actor: planner
  action: created
authoritative_surface: tests/
execution_mode: code_change
mission_slug: 075-mission-build-identity-contract-cutover
owned_files:
- tests/specify_cli/cli/test_mission_create_regression.py
- tests/contract/test_orchestrator_api_regression.py
- tests/sync/test_body_sync_regression.py
- tests/specify_cli/tracker/test_bind_no_feature_slug.py
tags: []
---

# WP05 — Regression and Non-Regression Test Suite

## Branch Strategy

- **Planning base**: `main`
- **Merge target**: `main`
- **Workspace**: allocated by `spec-kitty implement WP05` (lane-based worktree)
- **Command**: `spec-kitty implement WP05 --mission 075-mission-build-identity-contract-cutover`
- **PREREQUISITES**: WP02 and WP04 must both be merged to `main` before starting WP05. The regression tests depend on the cleanups in WP01-WP02 and the tracker bind change in WP04.

## Objective

Write end-to-end and contract-level tests that guard the already-clean surfaces against regression. These tests assert the absence of legacy artifacts across all live machine-facing outputs:

- Event log (`status.events.jsonl`) produced by `spec-kitty agent mission create`
- Orchestrator API command/error-code contract
- Body sync outbound SaaS payload
- Tracker bind outbound SaaS payload

All tests are **new files** — this WP adds no production code changes. It is a pure test-addition WP.

## Context

The prior cutover cleaned these surfaces. This WP locks them down. If any future change accidentally re-introduces `feature_slug`, `FeatureCreated`, `FeatureCompleted`, or `aggregate_type=Feature` into any of these outputs, these tests will fail and block the merge.

**Already-clean surfaces being guarded** (must not regress):
- FR-003: `MissionCreated`/`MissionClosed` event types only
- FR-005: `mission_slug`, `mission_number`, `mission_type` in payloads; no `aggregate_type=Feature`
- FR-006: no `feature_slug` in any live outbound JSON/API
- FR-010: orchestrator API uses mission-era command names only
- FR-011: body sync sends `mission_slug` + `mission_type`; no `mission_key` or `feature_slug`
- FR-014: contract gate validates all outbound calls before side effects

## Subtask Guidance

### T029 — CLI integration test: mission create → events.jsonl clean (Scenario 6a)

**File**: `tests/specify_cli/cli/test_mission_create_regression.py`

Use `typer.testing.CliRunner` to invoke `spec-kitty agent mission create` against a minimal fixture project and assert no legacy fields appear in the emitted `status.events.jsonl`.

```python
import json
from pathlib import Path
from typer.testing import CliRunner
from specify_cli.cli.app import app  # adjust to the actual Typer app entrypoint

LEGACY_FIELDS = ["feature_slug", "FeatureCreated", "FeatureCompleted"]

def test_mission_create_emits_no_legacy_fields(tmp_path):
    """spec-kitty agent mission create must emit no legacy fields in status.events.jsonl."""
    # Set up a minimal spec-kitty project fixture
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text(
        "vcs:\n  type: git\nproject:\n  uuid: test-uuid\n  slug: test-slug\n  node_id: abc123456def\n"
    )

    runner = CliRunner()
    result = runner.invoke(app, ["agent", "mission", "create", "regression-test-mission"])

    # Find the emitted events file (the runner may write to tmp_path or the invocation cwd)
    events_files = list(tmp_path.rglob("status.events.jsonl"))
    # If no events file was written (e.g., unauthenticated), check CLI output for legacy fields
    output = result.output

    for field in LEGACY_FIELDS:
        assert field not in output, (
            f"Legacy field '{field}' found in CLI output: {output}"
        )

    for events_file in events_files:
        events = events_file.read_text()
        for field in LEGACY_FIELDS:
            assert field not in events, (
                f"Legacy field '{field}' found in {events_file}: {events}"
            )
```

**Note on test setup**: Check existing CLI tests in `tests/specify_cli/cli/` for patterns used to set up fixture projects and mock authentication. Do not block on SaaS auth — the test should work offline by mocking or using `--dry-run` if available.

Specifically also assert `aggregate_type=Feature` does not appear in any output:
```python
assert "aggregate_type=Feature" not in output
assert all("aggregate_type=Feature" not in events_file.read_text() for events_file in events_files)
```

---

### T030 — Orchestrator API contract test (Scenario 6b)

**File**: `tests/contract/test_orchestrator_api_regression.py`

Test two things:
1. The `upstream_contract.json["orchestrator_api"]` section does not list any legacy command names
2. The Typer CLI does not register any legacy subcommand names

```python
import json
from importlib.resources import files

LEGACY_COMMAND_NAMES = {"accept-feature", "merge-feature", "feature-state", "create-feature"}
LEGACY_ERROR_CODES = {"FEATURE_NOT_FOUND", "FEATURE_NOT_READY", "FEATURE_NOT_STARTED"}

def test_upstream_contract_orchestrator_api_has_no_legacy_commands():
    """orchestrator_api section of upstream_contract.json must not list legacy command names."""
    contract = json.loads(
        files("specify_cli.core").joinpath("upstream_contract.json").read_text()
    )
    api_section = contract.get("orchestrator_api", {})

    allowed = set(api_section.get("allowed_commands", []))
    forbidden = set(api_section.get("forbidden_commands", []))

    # No legacy name should appear as an allowed command
    leaked = allowed & LEGACY_COMMAND_NAMES
    assert not leaked, f"Legacy command names in allowed_commands: {leaked}"

    # Legacy names should be in the forbidden list
    for legacy in LEGACY_COMMAND_NAMES:
        assert legacy in forbidden, (
            f"Legacy command '{legacy}' is not in forbidden_commands — it should be explicitly banned"
        )


def test_typer_app_has_no_legacy_subcommands():
    """The Typer CLI must not expose any legacy feature-era subcommand names."""
    from specify_cli.cli.app import app  # adjust to actual Typer app
    import typer

    def collect_commands(group, prefix=""):
        names = []
        for cmd_name, cmd in (group.registered_commands or {}).items():
            full_name = f"{prefix} {cmd_name}".strip()
            names.append(full_name)
            if hasattr(cmd, "registered_commands"):
                names.extend(collect_commands(cmd, full_name))
        return names

    all_commands = collect_commands(app)
    for command_name in all_commands:
        for legacy in LEGACY_COMMAND_NAMES:
            assert legacy not in command_name.lower(), (
                f"Legacy command name '{legacy}' found in registered command: '{command_name}'"
            )
```

**Note on Typer introspection**: The exact API for iterating Typer subcommands depends on the Typer version. Check existing CLI test helpers in `tests/specify_cli/cli/` for patterns. An alternative approach: run the CLI help output through CliRunner and grep the output for legacy command names.

---

### T031 — Body sync test: mock SaaSBodyClient; assert canonical namespace

**File**: `tests/sync/test_body_sync_regression.py`

```python
from unittest.mock import MagicMock, patch

FORBIDDEN_NAMESPACE_FIELDS = {"feature_slug", "mission_key"}
REQUIRED_NAMESPACE_FIELDS = {"mission_slug", "mission_type"}

def test_body_sync_sends_canonical_namespace(tmp_path):
    """Outbound body sync payload must use mission_slug + mission_type; no legacy namespace fields."""
    from specify_cli.sync.body_transport import push_artifact_body  # adjust to actual function

    captured_payload = {}

    def mock_push(payload, **kwargs):
        captured_payload.update(payload)

    with patch("specify_cli.sync.body_transport.SaaSBodyClient.push", side_effect=mock_push):
        push_artifact_body(
            mission_slug="075-test-mission",
            mission_type="software-dev",
            target_branch="main",
            manifest_version="1.0",
            project_uuid="test-uuid",
            artifact_path=tmp_path / "artifact.md",
        )

    # Required fields must be present
    for field in REQUIRED_NAMESPACE_FIELDS:
        assert field in captured_payload, (
            f"Required namespace field '{field}' missing from body sync payload: {captured_payload}"
        )

    # Forbidden fields must be absent
    for field in FORBIDDEN_NAMESPACE_FIELDS:
        assert field not in captured_payload, (
            f"Forbidden namespace field '{field}' found in body sync payload: {captured_payload}"
        )
```

**Adjust the import and function signature** to match the actual body sync API in `src/specify_cli/sync/`. Check `src/specify_cli/sync/body_transport.py` and `src/specify_cli/sync/namespace.py` for the public surface.

---

### T032 — Tracker bind non-regression: no feature_slug in bind kwargs

**File**: `tests/specify_cli/tracker/test_bind_no_feature_slug.py`

```python
from unittest.mock import MagicMock, patch
from pathlib import Path
from specify_cli.tracker.origin import bind_mission_origin
from specify_cli.tracker.origin_models import OriginCandidate

def test_bind_mission_origin_sends_no_feature_slug(tmp_path):
    """bind_mission_origin must not send feature_slug in the SaaS call (non-regression)."""
    feature_dir = tmp_path / "kitty-specs" / "075-test"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text('{"mission_slug": "075-test"}')

    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text(
        "project:\n  uuid: test-uuid\n  slug: test-slug\n  node_id: abc123\n"
    )
    (kittify / "tracker.yaml").write_text("provider: linear\nproject_slug: test-slug\n")

    mock_client = MagicMock()
    candidate = OriginCandidate(
        external_issue_id="LIN-456",
        external_issue_key="LIN-456",
        url="https://linear.app/test/LIN-456",
        title="Non-regression Test Issue",
        status="Todo",
    )

    with patch(
        "specify_cli.sync.project_identity._build_id_path",
        return_value=tmp_path / ".git" / "spec-kitty-build-id",
    ):
        (tmp_path / ".git").mkdir(exist_ok=True)
        (tmp_path / ".git" / "spec-kitty-build-id").write_text("non-regression-build-id\n")

        bind_mission_origin(
            feature_dir=feature_dir,
            candidate=candidate,
            provider="linear",
            resource_type="linear_team",
            resource_id="team-456",
            client=mock_client,
        )

    call_kwargs = mock_client.bind_mission_origin.call_args.kwargs
    assert "feature_slug" not in call_kwargs, (
        f"feature_slug must not appear in bind call kwargs, got: {call_kwargs}"
    )
    # Also assert mission_slug IS present
    assert "mission_slug" in call_kwargs
```

---

### T033 — Full test suite gate

This is a gate task, not a code change.

**Steps**:

1. Ensure the branch is up to date with `main` (WP02 and WP04 must be merged):
   ```bash
   git fetch origin && git rebase origin/main
   ```

2. Run the full test suite with coverage:
   ```bash
   pytest tests/ --cov=src/specify_cli --cov-report=term-missing -x
   ```
   Required: all tests green.

3. Check coverage on modified modules. The following must meet ≥90%:
   - `src/specify_cli/status/models.py`
   - `src/specify_cli/status/validate.py`
   - `src/specify_cli/status/wp_metadata.py`
   - `src/specify_cli/status/progress.py`
   - `src/specify_cli/core/worktree.py`
   - `src/specify_cli/sync/project_identity.py`
   - `src/specify_cli/tracker/origin.py`
   - `src/specify_cli/tracker/saas_client.py`

4. Run type check:
   ```bash
   mypy --strict src/specify_cli/
   ```
   Required: zero errors.

5. Verify legacy field absence across all test outputs:
   ```bash
   grep -r "feature_slug\|FeatureCreated\|FeatureCompleted\|aggregate_type.*Feature" \
     src/specify_cli/ --include="*.py" \
     | grep -v "migration\|rebuild_state\|upgrade/feature_meta\|\.pyc"
   ```
   Expected: zero hits.

Do not mark WP05 done until all five steps pass.

## Definition of Done

- [ ] CliRunner test: `spec-kitty agent mission create` produces output with no `feature_slug`, `FeatureCreated`, `FeatureCompleted`, `aggregate_type=Feature` (Scenario 6a)
- [ ] Orchestrator API test: `upstream_contract.json["orchestrator_api"]` contains no legacy command names; Typer CLI has no legacy subcommands (Scenario 6b)
- [ ] Body sync test: outbound payload contains `mission_slug` + `mission_type`; no `mission_key` or `feature_slug` (Scenario 5 equivalent)
- [ ] Tracker bind test: `bind_mission_origin` call kwargs contain no `feature_slug`
- [ ] Full test suite green; ≥90% coverage on all modified modules; `mypy --strict` zero errors
- [ ] `grep -r "feature_slug" src/specify_cli/ --include="*.py" | grep -v "migration\|rebuild_state\|upgrade"` returns zero hits

## Risks

| Risk | Mitigation |
|------|-----------|
| CliRunner test requires SaaS auth to emit events | Mock the SaaS client at the HTTP layer or use an existing offline test mode; check existing CLI test helpers |
| Typer command introspection API differs by version | Use CliRunner `--help` output parsing as a fallback; grep the output for legacy names |
| Body sync test requires knowing the exact function signature | Read `src/specify_cli/sync/body_transport.py` header before writing the test; adjust imports |

## Reviewer Guidance

- Four new test files — each should be independently runnable with `pytest <file> -v`
- T033 must be verified with the real test runner output, not just the check passing locally
- The `grep` in T033 step 5 is the definitive proof of the cutover being complete — include its output in the PR description
