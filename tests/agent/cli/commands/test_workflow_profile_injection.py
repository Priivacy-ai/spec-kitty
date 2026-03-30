"""ATDD acceptance tests for WP06 – Workflow Profile Injection.

5 scenarios from US-3:
  1. implementer profile injected when agent_profile=implementer
  2. architect profile injected when agent_profile=architect
  3. absent agent_profile defaults to generic-agent (or warns if missing)
  4. human-in-charge sentinel skips injection
  5. unresolvable profile → exit 1 without --allow-missing-profile, exit 0 with it

Tests are written against _render_profile_context() (unit style), analogous to
test_workflow_constitution_context.py testing _render_constitution_context().
"""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

from specify_cli.cli.commands.agent.workflow import _render_profile_context

pytestmark = pytest.mark.fast

# Path to the _proposed/ directory — only needed when placing HiC profile in project dir
# parents[4] = worktree root (.worktrees/057-doctrine-stack-init-and-profile-integration-WP06/)
_PROPOSED_DIR = Path(__file__).parents[4] / "src" / "doctrine" / "agent_profiles" / "_proposed"


def _make_hic_project_dir(base: Path) -> Path:
    """Write human-in-charge profile to a tmp project agents dir and return it."""
    agents_dir = base / ".kittify" / "constitution" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    hic_src = _PROPOSED_DIR / "human-in-charge.agent.yaml"
    (agents_dir / "human-in-charge.agent.yaml").write_bytes(hic_src.read_bytes())
    return base


class TestImplementerProfileInjected:
    """agent_profile: implementer → identity fragment present in output."""

    def test_implementer_profile_injected(self, tmp_path: Path) -> None:
        wp_frontmatter = 'agent_profile: "implementer"\n'
        result = _render_profile_context(tmp_path, wp_frontmatter)
        assert "## Agent Identity" in result
        assert "implementer" in result.lower()


class TestArchitectProfileInjected:
    """agent_profile: architect → architect identity fragment present."""

    def test_architect_profile_injected(self, tmp_path: Path) -> None:
        wp_frontmatter = 'agent_profile: "architect"\n'
        result = _render_profile_context(tmp_path, wp_frontmatter)
        assert "## Agent Identity" in result
        assert "architect" in result.lower()


class TestNoAgentProfileDefaultsToGenericAgent:
    """No agent_profile field → defaults to generic-agent profile (or warns if absent)."""

    def test_no_agent_profile_defaults_to_generic_agent(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        wp_frontmatter = "title: Some WP\n"  # no agent_profile field
        # generic-agent is not in shipped/ — expect either content (if profile exists)
        # or a graceful warning with empty return (profile not found → warn, no injection)
        result = _render_profile_context(tmp_path, wp_frontmatter)
        captured = capsys.readouterr()
        # Either generic-agent content was injected, OR a warning was emitted
        has_content = "## Agent Identity" in result and "generic-agent" in result.lower()
        has_warning = "not found" in captured.err or "Profile" in captured.err
        assert has_content or has_warning, (
            "Expected either generic-agent identity injection or a 'not found' warning. "
            f"result={result!r}, stderr={captured.err!r}"
        )


class TestHumanInChargeSkipsInjection:
    """agent_profile: human-in-charge → no injection, HiC log message emitted."""

    def test_human_in_charge_skips_injection(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        _make_hic_project_dir(tmp_path)
        wp_frontmatter = 'agent_profile: "human-in-charge"\n'
        result = _render_profile_context(tmp_path, wp_frontmatter)
        captured = capsys.readouterr()
        assert "## Agent Identity" not in result, "HiC WP must NOT inject an Agent Identity section"
        assert result == "", "Return value must be empty string for sentinel profile"
        assert "Human-in-charge" in captured.err, (
            "Expected 'Human-in-charge WP: no agent identity injected.' on stderr"
        )


class TestUnresolvableProfileBlockingError:
    """Unresolvable agent_profile → exit 1 without --allow-missing-profile; warn + continue with it."""

    def test_unresolvable_profile_exits_without_flag(self, tmp_path: Path) -> None:
        wp_frontmatter = 'agent_profile: "nonexistent-profile-zzz"\n'
        with pytest.raises(typer.Exit) as exc_info:
            _render_profile_context(tmp_path, wp_frontmatter, allow_missing=False)
        assert exc_info.value.exit_code == 1

    def test_unresolvable_profile_warns_with_flag(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        wp_frontmatter = 'agent_profile: "nonexistent-profile-zzz"\n'
        result = _render_profile_context(tmp_path, wp_frontmatter, allow_missing=True)
        captured = capsys.readouterr()
        assert result == "", "allow_missing=True must return empty string for unresolvable profile"
        assert "not found" in captured.err.lower() or "Profile" in captured.err, (
            "Expected a warning on stderr when allow_missing=True"
        )
