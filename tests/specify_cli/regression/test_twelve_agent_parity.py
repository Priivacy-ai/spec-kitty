"""Regression parity test: twelve non-migrated agents produce stable output.

Asserts that the command-file renderer produces byte-identical output to the
committed baseline under ``_twelve_agent_baseline/`` for every agent in
``AGENT_COMMAND_CONFIG`` (the twelve agents whose command-delivery mechanism
was not changed by mission 083-agent-skills-codex-vibe).

Codex, Vibe, Pi, and Letta are intentionally excluded — they use the Agent
Skills pipeline (``tests/specify_cli/skills/__snapshots__/`` covers them).

Baseline note
-------------
This baseline was captured post-mission-083 (after WP01–WP06), not from a
pre-mission checkout.  Pre-vs-post byte-identity is infeasible because WP02
edited source templates, changing rendered output for all agents.  The
baseline locks in post-mission state; future unintended drift is caught here.

Regenerating
------------
When a template change is intentional::

    PYTEST_UPDATE_SNAPSHOTS=1 pytest tests/specify_cli/regression/ -v

Commit the updated baseline files alongside the template change.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.core.config import AGENT_COMMAND_CONFIG
from specify_cli.skills.command_installer import PROMPT_BACKED_COMMANDS
from specify_cli.template.asset_generator import render_command_template

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.unit, pytest.mark.fast]

TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "src" / "doctrine" / "missions" / "mission-steps" / "software-dev"

BASELINE_DIR = Path(__file__).parent / "_twelve_agent_baseline"

# Agents covered by this regression suite — all keys in AGENT_COMMAND_CONFIG.
# Command-skill agents are absent: they use the Agent Skills pipeline.
NON_MIGRATED_AGENTS: tuple[str, ...] = tuple(AGENT_COMMAND_CONFIG.keys())

# Canonical prompt-backed command templates to test (one prompt.md source file per command).
#
# ``command_installer.CANONICAL_COMMANDS`` also includes thin CLI-wrapper
# Agent Skills such as ``dashboard``, ``merge``, and ``status``. Those do not
# have software-dev prompt templates and are covered by command-skill tests,
# not by this non-migrated command-file renderer regression.
CANONICAL_COMMANDS: tuple[str, ...] = PROMPT_BACKED_COMMANDS

# Fixed version for rendering (must match what was used when capturing the
# baseline; see _twelve_agent_baseline/__init__.py).
_BASELINE_VERSION = "3.1.2a3"

# Whether to update baselines instead of asserting.
_UPDATE = os.environ.get("PYTEST_UPDATE_SNAPSHOTS", "0") not in ("", "0", "false", "False")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _baseline_path(agent: str, command: str) -> Path:
    """Return the committed baseline file path for *agent* / *command*."""
    config = AGENT_COMMAND_CONFIG[agent]
    ext = config["ext"]
    return BASELINE_DIR / agent / f"{command}.{ext}"


def _render_for_agent(agent: str, command: str) -> str:
    """Render *command* for *agent* using the production render path.

    Patches ``_get_cli_version`` in the asset generator so the version
    marker in the output is stable across CLI upgrades and matches the
    committed baseline exactly.
    """
    template_path = TEMPLATES_DIR / command / "prompt.md"
    if not template_path.exists():
        pytest.skip(f"Template file missing: {template_path}")

    config = AGENT_COMMAND_CONFIG[agent]
    with patch(
        "specify_cli.template.asset_generator._get_cli_version",
        return_value=_BASELINE_VERSION,
    ):
        return render_command_template(
            template_path=template_path,
            script_type="sh",
            agent_key=agent,
            arg_format=config["arg_format"],
            extension=config["ext"],
        )


# ---------------------------------------------------------------------------
# Parametrized regression test
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("agent", NON_MIGRATED_AGENTS)
@pytest.mark.parametrize("command", CANONICAL_COMMANDS)
def test_command_output_unchanged(agent: str, command: str) -> None:
    """Rendered output must be byte-identical to the committed baseline.

    Failure means a source template changed in a way that affects the
    twelve non-migrated agents.  If the change is intentional, regenerate
    the baseline with ``PYTEST_UPDATE_SNAPSHOTS=1 pytest`` and commit the
    updated files alongside the template change.
    """
    snap = _baseline_path(agent, command)

    produced = _render_for_agent(agent, command)

    if _UPDATE:
        snap.parent.mkdir(parents=True, exist_ok=True)
        snap.write_text(produced, encoding="utf-8")
        return

    if not snap.exists():
        pytest.fail(f"Baseline missing for {agent}/{command} at {snap}.\nRegenerate with: PYTEST_UPDATE_SNAPSHOTS=1 pytest tests/specify_cli/regression/ -v")

    expected = snap.read_text(encoding="utf-8")
    assert produced == expected, (
        f"Command-file output for {agent}/{command} changed.\n"
        f"This mission must not modify the twelve non-migrated agents.\n"
        f"If the change is intentional (e.g. a cross-agent template edit),\n"
        f"regenerate the baseline with:\n"
        f"  PYTEST_UPDATE_SNAPSHOTS=1 pytest tests/specify_cli/regression/ -v\n"
        f"then commit the updated baseline files alongside the template change."
    )


@pytest.mark.parametrize(
    "agent",
    tuple(agent for agent in NON_MIGRATED_AGENTS if AGENT_COMMAND_CONFIG[agent]["ext"] == "toml"),
)
@pytest.mark.parametrize("command", CANONICAL_COMMANDS)
def test_toml_command_output_is_parseable(agent: str, command: str) -> None:
    """Rendered TOML command files must remain valid TOML."""
    produced = _render_for_agent(agent, command)
    try:
        tomllib.loads(produced)
    except tomllib.TOMLDecodeError as exc:
        raise AssertionError(f"Rendered TOML for {agent}/{command} is invalid: {exc}") from exc


# ---------------------------------------------------------------------------
# Structural invariants
# ---------------------------------------------------------------------------


def test_non_migrated_agents_count() -> None:
    """Exactly 12 agents are in AGENT_COMMAND_CONFIG.

    Count rose to 13 when PR #626 registered Kiro as a first-class slash-command
    agent, then fell back to 12 when Mission #136 deprecated Roo (Roo Code shut
    down 2026-05-15, constraint C-007 — see ``specify_cli.core.config``). Command-skill
    agents remain absent (they use the Agent Skills pipeline — see AGENT_SKILL_CONFIG).
    """
    assert len(NON_MIGRATED_AGENTS) == 12, f"Expected 12 non-migrated agents, got {len(NON_MIGRATED_AGENTS)}: {NON_MIGRATED_AGENTS}"


def test_codex_not_in_agent_command_config() -> None:
    """codex must NOT be in AGENT_COMMAND_CONFIG (migrated to Agent Skills)."""
    assert "codex" not in AGENT_COMMAND_CONFIG, (
        "codex was found in AGENT_COMMAND_CONFIG. Mission 083 migrated codex to the Agent Skills pipeline; it must not appear in the command-file registry."
    )


def test_vibe_not_in_agent_command_config() -> None:
    """vibe must NOT be in AGENT_COMMAND_CONFIG (uses Agent Skills pipeline)."""
    assert "vibe" not in AGENT_COMMAND_CONFIG, "vibe was found in AGENT_COMMAND_CONFIG. Vibe uses the Agent Skills pipeline, not the command-file pipeline."


def test_pi_and_letta_not_in_agent_command_config() -> None:
    """pi and letta must NOT be in AGENT_COMMAND_CONFIG."""
    assert "pi" not in AGENT_COMMAND_CONFIG
    assert "letta" not in AGENT_COMMAND_CONFIG


@pytest.mark.parametrize("agent", NON_MIGRATED_AGENTS)
def test_agent_baseline_directory_exists(agent: str) -> None:
    """Each non-migrated agent must have a baseline directory."""
    agent_dir = BASELINE_DIR / agent
    assert agent_dir.is_dir(), (
        f"Baseline directory missing for agent '{agent}' at {agent_dir}.\nRegenerate with: PYTEST_UPDATE_SNAPSHOTS=1 pytest tests/specify_cli/regression/ -v"
    )


def test_no_orphan_baseline_directories() -> None:
    """The baseline tree holds exactly the non-migrated agents — no more, no less.

    Guards against a migrated agent (e.g. ``roo``, which moved to the Agent
    Skills / shim delivery path and is absent from ``AGENT_COMMAND_CONFIG``)
    leaving behind an ungated baseline directory that silently drifts because
    no parametrized test ever renders or asserts it.
    """
    baseline_dirs = {
        d.name for d in BASELINE_DIR.iterdir() if d.is_dir() and not d.name.startswith("__")
    }
    expected = set(NON_MIGRATED_AGENTS)
    orphans = baseline_dirs - expected
    missing = expected - baseline_dirs
    assert not orphans and not missing, (
        f"Baseline directories must match NON_MIGRATED_AGENTS exactly.\n"
        f"  Orphan dirs (present but not a non-migrated agent — prune them): {sorted(orphans)}\n"
        f"  Missing dirs (expected but absent — regenerate them): {sorted(missing)}"
    )


@pytest.mark.parametrize("agent", NON_MIGRATED_AGENTS)
def test_agent_baseline_file_count(agent: str) -> None:
    """Each agent baseline directory must contain one file per prompt-backed command."""
    agent_dir = BASELINE_DIR / agent
    if not agent_dir.is_dir():
        pytest.skip(f"Baseline dir missing for {agent}")
    files = [f for f in agent_dir.iterdir() if f.is_file() and not f.name.startswith(".")]
    assert len(files) == len(CANONICAL_COMMANDS), (
        f"Agent '{agent}' baseline has {len(files)} files, "
        f"expected {len(CANONICAL_COMMANDS)} (one per canonical command).\n"
        f"Files found: {sorted(f.name for f in files)}"
    )


@pytest.mark.parametrize("agent", NON_MIGRATED_AGENTS)
def test_agent_outputs_contain_arg_placeholder(agent: str) -> None:
    """Non-migrated agents' outputs must preserve the agent's arg placeholder.

    Verifies that $ARGUMENTS or {{args}} is present in at least one rendered
    command for the agent (the skill-renderer transformation must NOT have
    been applied to these agents — that transformation is command-skill only).
    """
    config = AGENT_COMMAND_CONFIG[agent]
    expected_placeholder = config["arg_format"]
    # Only commands that forward user args will have the placeholder —
    # check every prompt-backed template and verify at least one contains it.
    found_any = False
    for command in CANONICAL_COMMANDS:
        snap = _baseline_path(agent, command)
        if snap.exists():
            content = snap.read_text(encoding="utf-8")
            if expected_placeholder in content:
                found_any = True
                break
    assert found_any, (
        f"Agent '{agent}' has arg_format '{expected_placeholder}' "
        f"but no baseline file contains that placeholder. "
        f"This suggests the skill-renderer transformation was incorrectly "
        f"applied to this non-migrated agent."
    )
