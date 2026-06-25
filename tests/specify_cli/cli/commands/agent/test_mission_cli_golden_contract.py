"""Golden CLI characterization harness for ``agent mission`` (#2056 WP01).

This is the **load-bearing safety net** for the entire decomposition of
``src/specify_cli/cli/commands/agent/mission.py``. It pins the byte-for-byte
``agent mission`` CLI surface — command names, per-command flag names and
defaults, positional arguments, and representative JSON success/error envelope
key sets — so every later WP can prove the extraction was behavior-preserving.

Source of truth: ``kitty-specs/decompose-mission-god-module-01KVXHF8/contracts/
cli-surface-contract.md`` (the frozen contract) and research.md §1 / §5.

NO production code is touched by this WP — test only (C-005).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import click
import pytest
from typer.main import get_command
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.mission import app as mission_app


def _resolve_subcommand(command_name: str) -> click.Command:
    """Resolve a registered ``agent mission`` subcommand from the Click tree.

    Introspects the resolved Click command tree directly (rather than the
    rendered ``--help`` text) so wrapped/truncated help output cannot mask a
    surface regression.
    """
    group = get_command(mission_app)
    assert isinstance(group, click.Group), "mission app must resolve to a Click Group"
    ctx = click.Context(group)
    sub = group.get_command(ctx, command_name)
    assert sub is not None, f"subcommand {command_name!r} not registered"
    return sub


def _command_flag_tokens(command_name: str) -> set[str]:
    """Return the exact option-flag token set for ``command_name``."""
    sub = _resolve_subcommand(command_name)
    tokens: set[str] = set()
    for param in sub.params:
        if isinstance(param, click.Option):
            tokens.update(param.opts)
            tokens.update(param.secondary_opts)
    return tokens


def _command_positional_names(command_name: str) -> set[str]:
    """Return the positional-argument parameter names for ``command_name``."""
    sub = _resolve_subcommand(command_name)
    return {
        p.name
        for p in sub.params
        if isinstance(p, click.Argument) and p.name is not None
    }


pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


# ---------------------------------------------------------------------------
# Frozen contract data (cli-surface-contract.md)
# ---------------------------------------------------------------------------


# The exact 8 subcommands `app` exposes, in alphabetical (Typer help) order.
_EXPECTED_COMMANDS: frozenset[str] = frozenset(
    {
        "branch-context",
        "create",
        "check-prerequisites",
        "record-analysis",
        "setup-plan",
        "accept",
        "merge",
        "finalize-tasks",
    }
)


# Per-command flag surface. Each entry maps a subcommand name to the set of
# option flag *tokens* that MUST appear in its ``--help``. ``--no-*`` halves of
# boolean-pair flags are listed explicitly. A positional argument is recorded
# separately in ``_EXPECTED_POSITIONALS``.
_EXPECTED_FLAGS: dict[str, frozenset[str]] = {
    "branch-context": frozenset({"--json", "--target-branch"}),
    "create": frozenset(
        {
            "--mission-type",
            "--mission",
            "--json",
            "--target-branch",
            "--friendly-name",
            "--purpose-tldr",
            "--purpose-context",
            "--pr-bound",
            "--no-pr-bound",
            "--branch-strategy",
            "--start-branch",
            "--force-recreate-coordination-branch",
        }
    ),
    "check-prerequisites": frozenset(
        {"--mission", "--json", "--paths-only", "--include-tasks", "--require-tasks"}
    ),
    "record-analysis": frozenset({"--mission", "--input-file", "--agent", "--json"}),
    "setup-plan": frozenset({"--mission", "--json"}),
    "accept": frozenset(
        {"--mission", "--mode", "--json", "--lenient", "--no-commit", "--diagnose"}
    ),
    "merge": frozenset(
        {
            "--mission",
            "--target",
            "--strategy",
            "--push",
            "--dry-run",
            "--keep-branch",
            "--keep-worktree",
            "--auto-retry",
            "--no-auto-retry",
        }
    ),
    "finalize-tasks": frozenset(
        {"--mission", "--json", "--validate-only", "--target-branch"}
    ),
}


# Subcommands that take a positional argument (Click parameter name).
_EXPECTED_POSITIONALS: dict[str, str] = {
    "create": "mission_slug",
}


# The ``--input-file`` default for record-analysis is the stdin sentinel ``-``.
_RECORD_ANALYSIS_INPUT_FILE_DEFAULT = "-"


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=True,
    )


def _init_repo(repo: Path) -> None:
    (repo / ".kittify").mkdir(exist_ok=True)
    (repo / "kitty-specs").mkdir(exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, capture_output=True, check=True)
    _git(repo, "config", "user.email", "test@test.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "commit", "-m", "init", "--allow-empty")


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Typer CliRunner (typer >=0.13 separates stdout/stderr)."""
    return CliRunner()


# ---------------------------------------------------------------------------
# T001 — the command set is exactly the 8 frozen commands
# ---------------------------------------------------------------------------


def test_app_exposes_exactly_eight_frozen_commands(runner: CliRunner) -> None:
    """``app --help`` lists exactly the 8 contracted commands — no more, no fewer."""
    result = runner.invoke(mission_app, ["--help"], catch_exceptions=False)
    assert result.exit_code == 0, result.stdout

    registered = {cmd.name for cmd in mission_app.registered_commands}
    assert registered == set(_EXPECTED_COMMANDS), (
        "Mission CLI command set drifted from the frozen contract.\n"
        f"  expected: {sorted(_EXPECTED_COMMANDS)}\n"
        f"  actual:   {sorted(registered)}"
    )

    # The help text must also surface every command name to the operator.
    for name in _EXPECTED_COMMANDS:
        assert name in result.stdout, f"command {name!r} missing from --help"


# ---------------------------------------------------------------------------
# T002 — per-command flags (names + key defaults) and positionals
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", sorted(_EXPECTED_FLAGS))
def test_command_exposes_exact_flag_surface(command: str) -> None:
    """Each subcommand exposes exactly the contracted flag token set.

    Introspects the resolved Click command (not rendered help) so the
    assertion is exact in both directions: no flag may be dropped AND no flag
    may be silently added during the decomposition.
    """
    actual = _command_flag_tokens(command)
    # `--help` is always present and not part of the domain contract.
    actual.discard("--help")
    expected = set(_EXPECTED_FLAGS[command])
    assert actual == expected, (
        f"`{command}` flag surface drifted from the frozen contract.\n"
        f"  missing: {sorted(expected - actual)}\n"
        f"  extra:   {sorted(actual - expected)}"
    )


@pytest.mark.parametrize("command,name", sorted(_EXPECTED_POSITIONALS.items()))
def test_command_exposes_positional_argument(command: str, name: str) -> None:
    """Commands with a positional argument expose it as a Click argument."""
    assert name in _command_positional_names(command), (
        f"positional {name!r} missing from `{command}` parameters"
    )


def test_record_analysis_input_file_default_is_stdin_sentinel() -> None:
    """``record-analysis --input-file`` defaults to the stdin sentinel ``-``."""
    sub = _resolve_subcommand("record-analysis")
    option = next(
        p
        for p in sub.params
        if isinstance(p, click.Option) and "--input-file" in p.opts
    )
    assert option.default == _RECORD_ANALYSIS_INPUT_FILE_DEFAULT


def test_create_mission_flag_is_hidden_deprecation() -> None:
    """``create``'s ``--mission`` flag is the hidden deprecated alias.

    The flag is registered (so the parser accepts it) but marked hidden, while
    the canonical ``--mission-type`` flag is visible.
    """
    sub = _resolve_subcommand("create")
    by_flag = {
        flag: p
        for p in sub.params
        if isinstance(p, click.Option)
        for flag in p.opts
    }
    assert "--mission" in by_flag, "deprecated --mission alias must remain registered"
    assert by_flag["--mission"].hidden is True, "--mission must stay hidden"
    assert "--mission-type" in by_flag
    assert by_flag["--mission-type"].hidden is False


# ---------------------------------------------------------------------------
# T003 — representative success JSON envelopes
# ---------------------------------------------------------------------------


# Keys the branch-context success envelope MUST carry. Includes the
# CLI-version injection (`_with_cli_version`) and the branch contract.
_BRANCH_CONTEXT_SUCCESS_KEYS: frozenset[str] = frozenset(
    {
        "result",
        "repo_root",
        "target_branch_source",
        "next_step",
        "current_branch",
        "planning_base_branch",
        "merge_target_branch",
        "branch_matches_target",
        "primary_branch",
        "current_is_primary",
        "recommended_strategy",
        "branch_recommendation_reason",
        "spec_kitty_version",
    }
)


def test_branch_context_success_envelope_keys(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``branch-context --json`` on a clean branch carries the frozen key set."""
    _init_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        mission_app, ["branch-context", "--json"], catch_exceptions=False
    )
    assert result.exit_code == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"

    envelope = json.loads(result.stdout)
    assert isinstance(envelope, dict)
    missing = _BRANCH_CONTEXT_SUCCESS_KEYS - set(envelope)
    assert not missing, (
        f"branch-context success envelope dropped keys: {sorted(missing)}\n"
        f"envelope keys: {sorted(envelope)}"
    )
    assert envelope["result"] == "success"
    # Version-injection invariant (_with_cli_version): the version key is a str.
    assert isinstance(envelope["spec_kitty_version"], str)


def test_check_prerequisites_success_envelope_carries_paths_and_version(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``check-prerequisites --json --paths-only`` carries the path + version keys.

    Drives the command against a minimal valid mission fixture so the success
    envelope (rather than a detection error) is produced.
    """
    _init_repo(tmp_path)
    feature_dir = tmp_path / "kitty-specs" / "001-golden-fixture"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "fixture mission")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        mission_app,
        ["check-prerequisites", "--mission", "001-golden-fixture", "--paths-only", "--json"],
        catch_exceptions=False,
    )
    # paths-only emits the legacy paths payload + branch contract + version.
    assert result.stdout, f"stderr={result.stderr!r}"
    envelope = json.loads(result.stdout)
    assert isinstance(envelope, dict)
    # Version injection and a representative path alias key are present.
    for key in ("spec_kitty_version", "FEATURE_DIR"):
        assert key in envelope, (
            f"check-prerequisites paths-only envelope missing {key!r}; "
            f"keys={sorted(envelope)}"
        )


# ---------------------------------------------------------------------------
# T004 — representative error JSON envelope (PLAN_CONTEXT_UNRESOLVED)
# ---------------------------------------------------------------------------


def test_setup_plan_unresolved_error_envelope_keys(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``setup-plan --json`` with multiple missions emits PLAN_CONTEXT_UNRESOLVED.

    With >=2 candidate missions and no ``--mission`` selector the command cannot
    disambiguate and returns the frozen detection-error envelope. Cross-checks
    the contract keys ``error_code``, ``error``, ``spec_kitty_version``,
    ``available_missions``, ``remediation``, ``example_command``.
    """
    _init_repo(tmp_path)
    specs = tmp_path / "kitty-specs"
    for slug in ("001-alpha-mission", "002-beta-mission"):
        d = specs / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "spec.md").write_text("# Spec\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "two missions")
    # The SaaS-auth FR-011 guard fires first when sync is opt-in; the mission
    # detection (PLAN_CONTEXT_UNRESOLVED) is the surface under test here.
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        mission_app, ["setup-plan", "--json"], catch_exceptions=False
    )
    assert result.stdout, f"stderr={result.stderr!r}"
    envelope = json.loads(result.stdout)
    assert isinstance(envelope, dict)

    assert envelope.get("error_code") == "PLAN_CONTEXT_UNRESOLVED", envelope
    for key in (
        "error_code",
        "error",
        "spec_kitty_version",
        "available_missions",
        "remediation",
        "example_command",
    ):
        assert key in envelope, (
            f"PLAN_CONTEXT_UNRESOLVED envelope missing {key!r}; keys={sorted(envelope)}"
        )
    assert isinstance(envelope["available_missions"], list)
    assert "001-alpha-mission" in envelope["available_missions"]


def test_setup_plan_no_missions_error_envelope_keys(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With zero candidate missions the envelope still carries the core keys.

    Pins the second (no-candidates) branch of the detection-error builder:
    ``error_code``, ``error``, ``spec_kitty_version``, ``remediation``.
    """
    _init_repo(tmp_path)
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        mission_app, ["setup-plan", "--json"], catch_exceptions=False
    )
    assert result.stdout, f"stderr={result.stderr!r}"
    envelope = json.loads(result.stdout)
    assert isinstance(envelope, dict)
    assert envelope.get("error_code") == "PLAN_CONTEXT_UNRESOLVED", envelope
    for key in ("error_code", "error", "spec_kitty_version", "remediation"):
        assert key in envelope, (
            f"no-mission envelope missing {key!r}; keys={sorted(envelope)}"
        )
