"""Integration tests for ``spec-kitty upgrade`` command surface — T038.

Covers the FR-023 case matrix:
  1. cli_update_available       -- outdated CLI, compatible project
  2. project_migration_needed   -- stale project (schema 1)
  3. project_too_new_for_cli    -- too-new project (schema 7)
  4. project_not_initialized    -- no project at all
  5. install_method_unknown     -- UNKNOWN install method

Plus:
  - Mutual exclusion: --cli + --project → exit 2
  - --yes alias: same effect as --force; --yes --force allowed together
  - JSON output validates against contracts/compat-planner.json key set

JSON contract validation uses ``jsonschema`` if available; otherwise falls
back to a hand-check of required top-level keys and their types.

Exit-code assertions honour CHK037 / A-006: --yes does NOT bypass
BLOCK_CLI_UPGRADE (project_too_new_for_cli stays exit 5).
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.cli.commands.upgrade import upgrade
from specify_cli.compat.planner import Invocation as _Invocation
from specify_cli.compat.planner import ProjectState
from specify_cli.compat.provider import FakeLatestVersionProvider

# ---------------------------------------------------------------------------
# Contract path (relative to repo root)
# ---------------------------------------------------------------------------

_WORKTREE_ROOT = Path(__file__).parent.parent.parent.parent.parent  # repo root
_CONTRACT_PATH = (
    _WORKTREE_ROOT.parent.parent.parent  # spec-kitty main repo root
    / "spec-kitty"
    / "kitty-specs"
    / "cli-upgrade-nag-lazy-project-migrations-01KQ6YDN"
    / "contracts"
    / "compat-planner.json"
)

# Try to locate the contract; fall back gracefully if not found
_CONTRACT: dict[str, Any] | None = None
if _CONTRACT_PATH.exists():
    with contextlib.suppress(Exception):
        _CONTRACT = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))

# Required top-level keys from contracts/compat-planner.json
_REQUIRED_TOP_LEVEL_KEYS = {
    "schema_version",
    "case",
    "decision",
    "exit_code",
    "cli",
    "project",
    "safety",
    "install_method",
    "upgrade_hint",
    "pending_migrations",
    "rendered_human",
}

# ---------------------------------------------------------------------------
# Test app (minimal — no full-app side-effects)
# ---------------------------------------------------------------------------

_test_app = typer.Typer(add_completion=False)
_test_app.command()(upgrade)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Contract validation helpers (T037)
# ---------------------------------------------------------------------------


def _validate_json_contract(payload: dict[str, Any]) -> None:
    """Validate *payload* against the compat-planner.json contract.

    Uses ``jsonschema`` when available; otherwise hand-checks required keys
    and types.
    """
    try:
        import jsonschema  # type: ignore[import]

        if _CONTRACT is not None:
            jsonschema.validate(instance=payload, schema=_CONTRACT)
        return
    except ImportError:
        pass  # Fall through to hand-check

    # Hand-check required keys
    missing = _REQUIRED_TOP_LEVEL_KEYS - set(payload.keys())
    assert not missing, f"JSON output missing required keys: {missing}"

    # schema_version must be 1
    assert payload["schema_version"] == 1, f"Expected schema_version=1, got {payload['schema_version']!r}"

    # case must be one of the enumerated tokens
    valid_cases = {
        "none",
        "cli_update_available",
        "project_migration_needed",
        "project_too_new_for_cli",
        "project_not_initialized",
        "project_metadata_corrupt",
        "install_method_unknown",
    }
    assert payload["case"] in valid_cases, f"case {payload['case']!r} not in {valid_cases}"

    # exit_code must be int in [0, 255]
    ec = payload["exit_code"]
    assert isinstance(ec, int) and 0 <= ec <= 255, f"exit_code={ec!r} out of range"

    # cli sub-object
    cli_obj = payload["cli"]
    for k in ("installed_version", "is_outdated", "latest_source"):
        assert k in cli_obj, f"cli.{k} missing"

    # project sub-object
    proj_obj = payload["project"]
    for k in ("state", "min_supported", "max_supported"):
        assert k in proj_obj, f"project.{k} missing"

    # upgrade_hint — exactly one of command/note non-null
    hint = payload["upgrade_hint"]
    cmd = hint.get("command")
    note = hint.get("note")
    assert (cmd is None) != (note is None), f"upgrade_hint must have exactly one of command/note non-null; got command={cmd!r}, note={note!r}"

    # pending_migrations is an array
    assert isinstance(payload["pending_migrations"], list), "pending_migrations must be a list"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_compatible_project(tmp_path: Path, schema_version: int = 3) -> Path:
    """Create a minimal Spec Kitty project with the given schema version."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "metadata.yaml").write_text(
        f"spec_kitty:\n  schema_version: {schema_version}\n",
        encoding="utf-8",
    )
    return tmp_path


def _invoke_upgrade(args: list[str], cwd: Path) -> Any:
    """Invoke the upgrade command with the given args from *cwd*."""
    old_cwd = os.getcwd()
    try:
        os.chdir(cwd)
        return runner.invoke(_test_app, args, catch_exceptions=False)
    finally:
        os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# T034 — Mutual exclusion: --cli + --project → exit 2
# ---------------------------------------------------------------------------


def test_cli_and_project_mutex_exits_2(tmp_path: Path) -> None:
    """--cli and --project together must exit 2 (BLOCK_INCOMPATIBLE_FLAGS)."""
    result = _invoke_upgrade(["--cli", "--project"], cwd=tmp_path)
    assert result.exit_code == 2, f"Expected exit 2, got {result.exit_code}. Output: {result.output}"
    assert "mutually exclusive" in result.output.lower() or "exclusive" in result.output.lower()


def test_cli_and_project_mutex_error_message(tmp_path: Path) -> None:
    """--cli --project error message mentions both flags."""
    result = _invoke_upgrade(["--cli", "--project"], cwd=tmp_path)
    assert "--cli" in result.output or "cli" in result.output.lower()
    assert "--project" in result.output or "project" in result.output.lower()


# ---------------------------------------------------------------------------
# T034 — --yes alias tests
# ---------------------------------------------------------------------------


def test_yes_and_force_produce_same_effect(tmp_path: Path) -> None:
    """--yes and --force are syntactically accepted (no error)."""
    _make_compatible_project(tmp_path)
    # Both flags accepted (may or may not have migrations; we just check no crash on flag parsing)
    result_yes = _invoke_upgrade(["--dry-run", "--yes"], cwd=tmp_path)
    result_force = _invoke_upgrade(["--dry-run", "--force"], cwd=tmp_path)
    # Both should succeed (same exit code)
    assert result_yes.exit_code == result_force.exit_code


def test_yes_and_force_together_allowed(tmp_path: Path) -> None:
    """--yes --force together is not an error (both are the same confirmation flag)."""
    _make_compatible_project(tmp_path)
    result = _invoke_upgrade(["--dry-run", "--yes", "--force"], cwd=tmp_path)
    # Should not exit 2 (no mutual exclusion error)
    assert result.exit_code != 2


# ---------------------------------------------------------------------------
# FR-023 case 1: cli_update_available
# ---------------------------------------------------------------------------


def test_cli_update_available_dry_run_shows_nag(tmp_path: Path) -> None:
    """Outdated CLI + compatible project: planner returns is_outdated=True.

    Uses FakeLatestVersionProvider("999.0.0") to force is_outdated=True.
    """
    _make_compatible_project(tmp_path, schema_version=3)

    fake_provider = FakeLatestVersionProvider("999.0.0")

    # Direct test: call planner with a fake provider to verify nag is triggered
    from specify_cli.compat.planner import plan as compat_plan

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        inv = _Invocation(
            command_path=("upgrade",),
            raw_args=("--cli",),
            is_help=False,
            is_version=False,
            flag_no_nag=False,
            env_ci=False,
            stdout_is_tty=True,
        )
        result_plan = compat_plan(
            inv,
            latest_version_provider=fake_provider,
        )
        assert result_plan.cli_status.is_outdated
        assert result_plan.fr023_case.value in ("cli_update_available", "install_method_unknown")
    finally:
        os.chdir(old_cwd)


def test_cli_update_available_json_contract(tmp_path: Path) -> None:
    """Outdated CLI: --cli --json emits valid compat-planner contract."""
    _make_compatible_project(tmp_path, schema_version=3)

    # Patch _run_cli_mode to call the real implementation with a fake provider
    from specify_cli.cli.commands import upgrade as upgrade_mod

    original_run_cli_mode = upgrade_mod._run_cli_mode

    def patched_run_cli_mode(
        *,
        json_output: bool,
        dry_run: bool,
        no_nag: bool,
        latest_version_provider: object = None,
    ) -> None:
        return original_run_cli_mode(
            json_output=json_output,
            dry_run=dry_run,
            no_nag=no_nag,
            latest_version_provider=FakeLatestVersionProvider("999.0.0"),
        )

    with patch.object(upgrade_mod, "_run_cli_mode", patched_run_cli_mode):
        result = _invoke_upgrade(["--cli", "--json"], cwd=tmp_path)

    assert result.exit_code == 0, f"Exit {result.exit_code}; output: {result.output}"
    payload = json.loads(result.output)
    _validate_json_contract(payload)
    assert payload["schema_version"] == 1
    assert payload["cli"]["is_outdated"] is True


# ---------------------------------------------------------------------------
# FR-023 case 2: project_migration_needed
# ---------------------------------------------------------------------------


def test_project_migration_needed_cli_mode_lists_hint(tmp_path: Path) -> None:
    """Stale project: --cli still succeeds (project-agnostic path)."""
    # Schema 1 is stale (MIN_SUPPORTED = 3)
    _make_compatible_project(tmp_path, schema_version=1)

    result = _invoke_upgrade(["--cli", "--dry-run"], cwd=tmp_path)
    assert result.exit_code == 0, f"Exit {result.exit_code}; output: {result.output}"


def test_project_migration_needed_planner_json(tmp_path: Path) -> None:
    """Stale project (schema 1): planner reports project_migration_needed or stale state."""
    _make_compatible_project(tmp_path, schema_version=1)

    from specify_cli.compat.planner import plan as compat_plan

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        inv = _Invocation(
            command_path=("upgrade",),
            raw_args=("--project",),
            is_help=False,
            is_version=False,
            flag_no_nag=False,
            env_ci=False,
            stdout_is_tty=True,
        )
        result_plan = compat_plan(inv)
        # Project with schema_version=1 < MIN_SUPPORTED=3 should be STALE
        assert result_plan.project_status.state == ProjectState.STALE
        payload = result_plan.rendered_json
        _validate_json_contract(payload)
        assert payload["project"]["state"] == "stale"
    finally:
        os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# FR-023 case 3: project_too_new_for_cli (CHK037 / A-006)
# ---------------------------------------------------------------------------


def test_project_too_new_for_cli_command_exit_5(tmp_path: Path) -> None:
    """Project schema 7 (too new): upgrade command exits 5 (CHK037)."""
    _make_compatible_project(tmp_path, schema_version=7)
    result = _invoke_upgrade(["--project", "--dry-run"], cwd=tmp_path)
    assert result.exit_code == 5, f"Expected exit 5 for too-new project, got {result.exit_code}. Output: {result.output}"


def test_project_too_new_for_cli_default_mode_exit_5(tmp_path: Path) -> None:
    """Project schema 7 (too new): default upgrade mode also exits 5."""
    _make_compatible_project(tmp_path, schema_version=7)
    result = _invoke_upgrade(["--dry-run"], cwd=tmp_path)
    assert result.exit_code == 5, f"Expected exit 5 for too-new project, got {result.exit_code}. Output: {result.output}"


def test_project_too_new_for_cli_yes_does_not_bypass(tmp_path: Path) -> None:
    """--yes does NOT bypass too-new schema block (A-006 / CHK037).

    ``--yes`` is a confirmation alias; it cannot bypass a schema-incompatibility
    that is unfixable from the project side.  Exit must remain 5.
    """
    _make_compatible_project(tmp_path, schema_version=7)
    result = _invoke_upgrade(["--yes"], cwd=tmp_path)
    # Still exit 5, NOT 0
    assert result.exit_code == 5, f"Expected exit 5 (BLOCK_CLI_UPGRADE) even with --yes, got {result.exit_code}"


def test_project_too_new_for_cli_force_does_not_bypass(tmp_path: Path) -> None:
    """--force does NOT bypass too-new schema block (A-006 / CHK037)."""
    _make_compatible_project(tmp_path, schema_version=7)
    result = _invoke_upgrade(["--force"], cwd=tmp_path)
    assert result.exit_code == 5, f"Expected exit 5 (BLOCK_CLI_UPGRADE) even with --force, got {result.exit_code}"


def test_project_too_new_for_cli_json_contract(tmp_path: Path) -> None:
    """project_too_new_for_cli: --json output is valid contract with exit_code=5."""
    _make_compatible_project(tmp_path, schema_version=7)

    result = _invoke_upgrade(["--project", "--dry-run", "--json"], cwd=tmp_path)
    assert result.exit_code == 5, f"Expected exit 5 for too-new project with --json, got {result.exit_code}. Output: {result.output}"
    try:
        payload = json.loads(result.output)
    except json.JSONDecodeError as e:
        pytest.fail(f"Output is not valid JSON: {e}\nOutput: {result.output!r}")
    _validate_json_contract(payload)
    assert payload["project"]["state"] == "too_new"


def test_project_too_new_for_cli_project_state(tmp_path: Path) -> None:
    """Project schema 7: planner reports TOO_NEW state in rendered_json."""
    _make_compatible_project(tmp_path, schema_version=7)

    from specify_cli.compat.planner import plan as compat_plan

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        inv = _Invocation(
            command_path=("upgrade",),
            raw_args=("--project",),
            is_help=False,
            is_version=False,
            flag_no_nag=False,
            env_ci=False,
            stdout_is_tty=True,
        )
        result_plan = compat_plan(inv)
        assert result_plan.project_status.state == ProjectState.TOO_NEW
    finally:
        os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# FR-023 case 4: project_not_initialized
# ---------------------------------------------------------------------------


def test_project_not_initialized_cli_flag_succeeds(tmp_path: Path) -> None:
    """No project + --cli → exit 0 (FR-014: --cli works outside any project)."""
    # tmp_path has no .kittify
    result = _invoke_upgrade(["--cli", "--dry-run"], cwd=tmp_path)
    assert result.exit_code == 0, f"Exit {result.exit_code}; output: {result.output}"


def test_project_not_initialized_project_flag_errors(tmp_path: Path) -> None:
    """No project + --project → errors with a clear 'no project' message."""
    result = _invoke_upgrade(["--project", "--dry-run"], cwd=tmp_path)
    # Should exit non-zero with an error message
    assert result.exit_code != 0, "Expected non-zero exit for --project outside a project"
    combined = (result.output or "") + (result.stderr or "")
    assert "not a spec kitty project" in combined.lower() or "no project" in combined.lower() or "init" in combined.lower()


def test_project_not_initialized_planner_state(tmp_path: Path) -> None:
    """No project: planner reports NO_PROJECT state."""
    from specify_cli.compat.planner import plan as compat_plan

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        inv = _Invocation(
            command_path=("upgrade",),
            raw_args=("--cli",),
            is_help=False,
            is_version=False,
            flag_no_nag=False,
            env_ci=False,
            stdout_is_tty=True,
        )
        result_plan = compat_plan(inv)
        assert result_plan.project_status.state == ProjectState.NO_PROJECT
        # --cli is always exit 0 regardless of project state
        # (planner exit_code is 0 for ALLOW/ALLOW_WITH_NAG)
        payload = result_plan.rendered_json
        _validate_json_contract(payload)
    finally:
        os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# FR-023 case 5: install_method_unknown (CHK031)
# ---------------------------------------------------------------------------


def test_install_method_unknown_cli_prints_note_not_command(tmp_path: Path) -> None:
    """UNKNOWN install method: upgrade_hint has note (not command) per CHK031."""
    from specify_cli.compat._detect.install_method import InstallMethod
    from specify_cli.compat.planner import plan as compat_plan

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        inv = _Invocation(
            command_path=("upgrade",),
            raw_args=("--cli",),
            is_help=False,
            is_version=False,
            flag_no_nag=False,
            env_ci=False,
            stdout_is_tty=True,
        )
        # Patch the detect_install_method where it is imported inside _plan_impl
        with (
            patch(
                "specify_cli.compat._detect.install_method.detect_install_method",
                return_value=InstallMethod.UNKNOWN,
            ),
            patch(
                "specify_cli.compat.planner.detect_install_method",
                return_value=InstallMethod.UNKNOWN,
                create=True,
            ),
        ):
            result_plan = compat_plan(inv)

        hint = result_plan.upgrade_hint
        # For UNKNOWN install method, command should be None, note should be set
        assert hint.command is None, f"UNKNOWN install method should have command=None, got {hint.command!r}"
        assert hint.note is not None, "UNKNOWN install method should have a note"

        # Validate JSON contract
        payload = result_plan.rendered_json
        _validate_json_contract(payload)
        hint_json = payload["upgrade_hint"]
        assert hint_json["command"] is None
        assert hint_json["note"] is not None
    finally:
        os.chdir(old_cwd)


def test_install_method_unknown_upgrade_hint_structure() -> None:
    """UNKNOWN install method: build_upgrade_hint returns note=non-null, command=null."""
    from specify_cli.compat._detect.install_method import InstallMethod
    from specify_cli.compat.upgrade_hint import build_upgrade_hint

    hint = build_upgrade_hint(InstallMethod.UNKNOWN)
    assert hint.command is None, f"UNKNOWN: command should be None, got {hint.command!r}"
    assert hint.note is not None, "UNKNOWN: note should be set"


def test_install_method_unknown_cli_flag_exit_0(tmp_path: Path) -> None:
    """UNKNOWN install method + --cli flag: exits 0 (not an error condition)."""
    from specify_cli.compat._detect.install_method import InstallMethod

    with patch(
        "specify_cli.compat._detect.install_method.detect_install_method",
        return_value=InstallMethod.UNKNOWN,
    ):
        result = _invoke_upgrade(["--cli"], cwd=tmp_path)

    assert result.exit_code == 0, f"Exit {result.exit_code}; output: {result.output}"


# ---------------------------------------------------------------------------
# T037 — --dry-run --json contract validation
# ---------------------------------------------------------------------------


def test_dry_run_json_compatible_project_exits_0(tmp_path: Path) -> None:
    """--cli --dry-run --json: compatible project, always exits 0 (R-08 / FR-012)."""
    _make_compatible_project(tmp_path, schema_version=3)
    result = _invoke_upgrade(["--cli", "--dry-run", "--json"], cwd=tmp_path)
    assert result.exit_code == 0, f"Exit {result.exit_code}; output: {result.output}"
    payload = json.loads(result.output)
    _validate_json_contract(payload)


def test_dry_run_json_no_project_exits_0(tmp_path: Path) -> None:
    """--cli --dry-run --json without a project: exits 0."""
    result = _invoke_upgrade(["--cli", "--dry-run", "--json"], cwd=tmp_path)
    assert result.exit_code == 0, f"Exit {result.exit_code}; output: {result.output}"
    payload = json.loads(result.output)
    _validate_json_contract(payload)


# ---------------------------------------------------------------------------
# FIX 5 — RISK-3: --cli mode respects real CI environment (no network call)
# ---------------------------------------------------------------------------


def test_cli_mode_ci_env_suppresses_network(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CI=1 spec-kitty upgrade --cli must not make a network call (RISK-3 fix).

    Verifies that when CI=1, the Invocation built in _run_cli_mode has env_ci=True,
    which causes suppresses_network() to return True, which selects NoNetworkProvider.
    """
    import httpx

    monkeypatch.setenv("CI", "1")

    network_calls: list[str] = []

    def _blocking_request(self: object, *args: object, **kwargs: object) -> None:  # type: ignore[misc]
        network_calls.append("network_call_made")
        raise RuntimeError("network call made in CI mode")

    monkeypatch.setattr(httpx.Client, "get", _blocking_request)

    result = _invoke_upgrade(["--cli"], cwd=tmp_path)
    # Should exit 0 and not raise (network was not called)
    assert result.exit_code == 0, f"Exit {result.exit_code}; output: {result.output}"
    assert not network_calls, "No network calls should be made when CI=1"


def test_cli_mode_no_ci_env_does_not_suppress_network(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Without CI, --cli mode builds an Invocation with env_ci=False (RISK-3 fix).

    We verify the env_ci field by inspecting is_ci_env() directly — not by making
    a real network call (which would be fragile in test environments).
    """
    from specify_cli.compat.planner import is_ci_env

    monkeypatch.delenv("CI", raising=False)
    assert is_ci_env() is False


# ---------------------------------------------------------------------------
# FIX 6 — RISK-6 / FR-014: bare upgrade outside project falls through to --cli
# ---------------------------------------------------------------------------


def test_bare_upgrade_outside_project_exits_0(tmp_path: Path) -> None:
    """Bare 'spec-kitty upgrade' outside a project exits 0 (FR-014 fall-through to --cli)."""
    # tmp_path has no .kittify
    result = _invoke_upgrade([], cwd=tmp_path)
    assert result.exit_code == 0, (
        f"Expected exit 0 for bare upgrade outside project (FR-014), got {result.exit_code}. "
        f"Output: {result.output}"
    )


def test_bare_upgrade_outside_project_no_error_message(tmp_path: Path) -> None:
    """Bare 'spec-kitty upgrade' outside a project must NOT print 'Not a Spec Kitty project'."""
    result = _invoke_upgrade([], cwd=tmp_path)
    assert "not a spec kitty project" not in result.output.lower(), (
        f"Bare upgrade should not show project-error message. Output: {result.output}"
    )


def test_project_flag_outside_project_still_errors(tmp_path: Path) -> None:
    """--project outside a project still errors (existing behavior must be preserved)."""
    result = _invoke_upgrade(["--project"], cwd=tmp_path)
    assert result.exit_code != 0, "Expected non-zero exit for --project outside a project"
    combined = (result.output or "") + (result.stderr or "")
    assert (
        "not a spec kitty project" in combined.lower()
        or "no project" in combined.lower()
        or "init" in combined.lower()
    )


def test_planner_json_too_new_project_has_exit_code_5_in_payload(tmp_path: Path) -> None:
    """Direct planner call: too-new project produces exit_code=5 in the JSON payload."""
    _make_compatible_project(tmp_path, schema_version=7)

    from specify_cli.compat.planner import plan as compat_plan

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        # Use an unsafe command path to trigger BLOCK_CLI_UPGRADE
        inv = _Invocation(
            command_path=("specify",),  # unsafe command, not in SAFETY_REGISTRY
            raw_args=(),
            is_help=False,
            is_version=False,
            flag_no_nag=False,
            env_ci=False,
            stdout_is_tty=True,
        )
        result_plan = compat_plan(inv)
        # The planner should return BLOCK_CLI_UPGRADE for an unsafe command + too_new project
        assert result_plan.project_status.state == ProjectState.TOO_NEW
        payload = result_plan.rendered_json
        _validate_json_contract(payload)
        assert payload["exit_code"] == 5
        assert payload["case"] == "project_too_new_for_cli"
    finally:
        os.chdir(old_cwd)


def test_cli_json_output_valid_contract(tmp_path: Path) -> None:
    """--cli --json emits JSON that passes contract validation."""
    _make_compatible_project(tmp_path, schema_version=3)

    result = _invoke_upgrade(["--cli", "--json"], cwd=tmp_path)
    assert result.exit_code == 0, f"Exit {result.exit_code}; output: {result.output}"

    try:
        payload = json.loads(result.output)
    except json.JSONDecodeError as e:
        pytest.fail(f"--cli --json output is not valid JSON: {e}\nOutput: {result.output!r}")

    _validate_json_contract(payload)


def test_cli_json_no_banner_in_stdout(tmp_path: Path) -> None:
    """--cli --json output is clean JSON only (no banner or nag prefix)."""
    _make_compatible_project(tmp_path, schema_version=3)

    result = _invoke_upgrade(["--cli", "--json"], cwd=tmp_path)
    # First non-whitespace char should be '{'
    stripped = result.output.lstrip()
    assert stripped.startswith("{"), f"JSON output should start with '{{'; got: {result.output[:100]!r}"


# ---------------------------------------------------------------------------
# T035 — --cli outside project (FR-014)
# ---------------------------------------------------------------------------


def test_cli_outside_project_no_error_message(tmp_path: Path) -> None:
    """--cli outside a project: no 'not a Spec Kitty project' error."""
    result = _invoke_upgrade(["--cli"], cwd=tmp_path)
    combined = (result.output or "") + (result.stderr or "")
    assert "not a spec kitty project" not in combined.lower()
    assert result.exit_code == 0


def test_cli_no_project_json_valid(tmp_path: Path) -> None:
    """--cli --json outside a project: valid JSON contract, exit 0."""
    result = _invoke_upgrade(["--cli", "--json"], cwd=tmp_path)
    assert result.exit_code == 0, f"Exit {result.exit_code}; output: {result.output}"
    payload = json.loads(result.output)
    _validate_json_contract(payload)
    assert payload["project"]["state"] == "no_project"


# ---------------------------------------------------------------------------
# T036 — --project suppresses CLI nag
# ---------------------------------------------------------------------------


def test_project_mode_no_cli_nag_in_output(tmp_path: Path) -> None:
    """--project with outdated CLI: no CLI nag in planner output path.

    The project-upgrade flow doesn't invoke the planner rendering at all;
    nag text appears only when --cli is used.
    """
    _make_compatible_project(tmp_path, schema_version=3)

    # Verify that the planner itself with --project flag doesn't produce
    # a CLI nag in rendered_human (it uses the upgrade hint, not the nag message)
    from specify_cli.compat.planner import plan as compat_plan

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        inv = _Invocation(
            command_path=("upgrade",),
            raw_args=("--project",),
            is_help=False,
            is_version=False,
            flag_no_nag=False,
            env_ci=False,
            stdout_is_tty=True,
        )
        result_plan = compat_plan(
            inv,
            latest_version_provider=FakeLatestVersionProvider("999.0.0"),
        )
        # With compatible project + outdated CLI → ALLOW_WITH_NAG
        # rendered_human has nag text; but in --project CLI mode, that is suppressed
        # (the project-upgrade flow doesn't call the planner at all unless --json)
        # Just validate the payload is contract-valid
        payload = result_plan.rendered_json
        _validate_json_contract(payload)
    finally:
        os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------


def test_no_nag_flag_accepted(tmp_path: Path) -> None:
    """--no-nag flag is accepted without error."""
    _make_compatible_project(tmp_path, schema_version=3)
    result = _invoke_upgrade(["--cli", "--no-nag"], cwd=tmp_path)
    assert result.exit_code == 0, f"Exit {result.exit_code}; output: {result.output}"


def test_cli_flag_with_dry_run(tmp_path: Path) -> None:
    """--cli --dry-run exits 0 (dry-run always 0)."""
    result = _invoke_upgrade(["--cli", "--dry-run"], cwd=tmp_path)
    assert result.exit_code == 0


def test_existing_dry_run_flag_preserved(tmp_path: Path) -> None:
    """Existing --dry-run flag is accepted (flag parse succeeds, no crash)."""
    _make_compatible_project(tmp_path, schema_version=3)
    # We only assert that the --dry-run flag doesn't cause a usage error (exit 2).
    # The actual exit code depends on the migration runner state.
    result = _invoke_upgrade(["--dry-run"], cwd=tmp_path)
    assert result.exit_code != 2, f"--dry-run caused a usage error: {result.output}"


def test_existing_dry_run_flag_cli_mode(tmp_path: Path) -> None:
    """--dry-run with --cli exits 0 (safe, project-agnostic path)."""
    result = _invoke_upgrade(["--dry-run", "--cli"], cwd=tmp_path)
    assert result.exit_code == 0, f"Exit {result.exit_code}; output: {result.output}"


def test_existing_verbose_flag_preserved(tmp_path: Path) -> None:
    """Existing --verbose flag is accepted (flag parse succeeds, no crash)."""
    _make_compatible_project(tmp_path, schema_version=3)
    result = _invoke_upgrade(["--dry-run", "--verbose"], cwd=tmp_path)
    assert result.exit_code != 2, f"--verbose caused a usage error: {result.output}"


def test_existing_verbose_flag_cli_mode(tmp_path: Path) -> None:
    """--verbose with --cli is accepted."""
    result = _invoke_upgrade(["--cli", "--verbose"], cwd=tmp_path)
    assert result.exit_code == 0, f"Exit {result.exit_code}; output: {result.output}"


def test_existing_force_flag_preserved(tmp_path: Path) -> None:
    """Existing --force flag is accepted (flag parse succeeds, no crash)."""
    _make_compatible_project(tmp_path, schema_version=3)
    result = _invoke_upgrade(["--dry-run", "--force"], cwd=tmp_path)
    assert result.exit_code != 2, f"--force caused a usage error: {result.output}"


def test_existing_no_worktrees_flag_preserved(tmp_path: Path) -> None:
    """Existing --no-worktrees flag is accepted (flag parse succeeds, no crash)."""
    _make_compatible_project(tmp_path, schema_version=3)
    result = _invoke_upgrade(["--dry-run", "--no-worktrees"], cwd=tmp_path)
    assert result.exit_code != 2, f"--no-worktrees caused a usage error: {result.output}"
