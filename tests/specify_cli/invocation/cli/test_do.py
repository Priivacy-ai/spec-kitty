"""Integration tests for spec-kitty do CLI surface.

The 'do' command always routes via ActionRouter (profile_hint=None).
It never accepts an explicit --profile option.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli import app as cli_app
from specify_cli.glossary.chokepoint import GlossaryObservationBundle
from specify_cli.glossary.models import (
    ConflictType,
    SemanticConflict,
    SenseRef,
    Severity,
    TermSurface,
)
from specify_cli.invocation.writer import EVENTS_DIR

# Marked for mutmut sandbox skip — subprocess CLI invocation.
pytestmark = pytest.mark.non_sandbox

runner = CliRunner()

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "profiles"

# ---------------------------------------------------------------------------
# Shared context mocks
# ---------------------------------------------------------------------------

_COMPACT_CTX = MagicMock()
_COMPACT_CTX.mode = "compact"
_COMPACT_CTX.text = "compact governance context"

_MISSING_CTX = MagicMock()
_MISSING_CTX.mode = "missing"
_MISSING_CTX.text = ""


def _setup_project(tmp_path: Path) -> Path:
    """Create minimal project structure with fixture profiles."""
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir(parents=True)
    profiles_dir = kittify_dir / "profiles"
    profiles_dir.mkdir()
    for yaml_file in FIXTURES_DIR.glob("*.agent.yaml"):
        shutil.copy(yaml_file, profiles_dir / yaml_file.name)
    return tmp_path


def _high_severity_bundle() -> GlossaryObservationBundle:
    conflict = SemanticConflict(
        term=TermSurface("lane"),
        conflict_type=ConflictType.AMBIGUOUS,
        severity=Severity.HIGH,
        confidence=1.0,
        candidate_senses=[
            SenseRef(
                surface="lane",
                scope="spec_kitty_core",
                definition="Execution lane",
                confidence=1.0,
            ),
            SenseRef(
                surface="lane",
                scope="team_domain",
                definition="Worktree lane",
                confidence=1.0,
            ),
        ],
        context="request_text",
    )
    return GlossaryObservationBundle(
        matched_urns=("glossary:d93244e7",),
        high_severity=(conflict,),
        all_conflicts=(conflict,),
        tokens_checked=3,
        duration_ms=1.5,
        error_msg=None,
    )


def _make_mock_registry(profile_specs: list[dict]) -> MagicMock:
    """Build a lightweight mock ProfileRegistry with controlled profiles.

    Uses MagicMock to avoid shipped-profile interference.
    """
    from doctrine.agent_profiles.profile import Role

    mock_profiles = []
    for spec in profile_specs:
        p = MagicMock()
        p.profile_id = spec["profile_id"]
        p.role = Role(spec["role_value"])
        p.routing_priority = spec.get("routing_priority", 50)
        p.name = spec.get("name", spec["profile_id"])

        sc = MagicMock()
        sc.domain_keywords = spec.get("domain_keywords", [])
        p.specialization_context = sc

        collab = MagicMock()
        collab.canonical_verbs = spec.get("collab_verbs", [])
        p.collaboration = collab

        mock_profiles.append(p)

    registry = MagicMock()
    registry.list_all.return_value = mock_profiles

    def _get(pid: str) -> object:
        return next((p for p in mock_profiles if p.profile_id == pid), None)

    def _resolve(pid: str) -> object:
        from specify_cli.invocation.errors import ProfileNotFoundError  # noqa: PLC0415

        profile = _get(pid)
        if profile is None:
            raise ProfileNotFoundError(pid, [p.profile_id for p in mock_profiles])
        return profile

    registry.get.side_effect = _get
    registry.resolve.side_effect = _resolve
    return registry


_IMPLEMENTER_REGISTRY = lambda: _make_mock_registry(
    [  # noqa: E731
        {
            "profile_id": "implementer-fixture",
            "role_value": "implementer",
            "routing_priority": 50,
            "name": "Implementer (fixture)",
            "domain_keywords": ["implement", "build", "code"],
        },
    ]
)

_REVIEWER_REGISTRY = lambda: _make_mock_registry(
    [  # noqa: E731
        {
            "profile_id": "reviewer-fixture",
            "role_value": "reviewer",
            "routing_priority": 50,
            "name": "Reviewer (fixture)",
            "domain_keywords": ["review", "audit"],
        },
    ]
)


# ---------------------------------------------------------------------------
# Successful routing tests
# ---------------------------------------------------------------------------


class TestDoSuccessfulRouting:
    def test_implement_request_routes_to_implementer(self, tmp_path: Path) -> None:
        """'implement the feature' routes to implementer-fixture via CANONICAL_VERB_MAP."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "implement the feature", "--json"],
            )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["profile_id"] == "implementer-fixture"
        assert data["action"] == "implement"
        assert data["router_confidence"] == "canonical_verb"
        assert data["invocation_id"]

    def test_returns_valid_invocation_payload_shape(self, tmp_path: Path) -> None:
        """JSON output has all required InvocationPayload fields."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "implement the payment module", "--json"],
            )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "invocation_id" in data
        assert "profile_id" in data
        assert "action" in data
        assert "router_confidence" in data
        assert "governance_context_available" in data

    def test_creates_jsonl_record_on_successful_routing(self, tmp_path: Path) -> None:
        """Successful routing creates a JSONL invocation record."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "implement the payment module", "--json"],
            )
        assert result.exit_code == 0, result.output
        events_dir = project / EVENTS_DIR
        jsonl_files = list(events_dir.glob("*.jsonl")) if events_dir.exists() else []
        assert len(jsonl_files) == 1

    def test_rich_output_exits_zero(self, tmp_path: Path) -> None:
        """Without --json, rich output is produced with exit 0."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "implement the feature"],
            )
        assert result.exit_code == 0, result.output

    def test_rich_output_surfaces_high_severity_glossary_warning(self, tmp_path: Path) -> None:
        """High-severity glossary conflicts should be shown inline before governance context."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
            patch(
                "specify_cli.glossary.chokepoint.GlossaryChokepoint.run",
                return_value=_high_severity_bundle(),
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "implement the feature"],
            )
        assert result.exit_code == 0, result.output
        assert "High-severity terminology conflicts detected before this invocation." in result.output
        assert "lane (ambiguous)" in result.output
        assert result.output.index("lane (ambiguous)") < result.output.index("compact governance context")


# ---------------------------------------------------------------------------
# Routing failure / error tests
# ---------------------------------------------------------------------------


class TestDoRoutingFailures:
    def test_ambiguous_request_exits_1(self, tmp_path: Path) -> None:
        """Vague request 'help me' — no canonical verb match — exits 1."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "help me", "--json"],
            )
        assert result.exit_code == 1

    def test_no_match_request_exits_1(self, tmp_path: Path) -> None:
        """Request with no recognizable verbs exits 1 (ROUTER_NO_MATCH)."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "the quick brown fox", "--json"],
            )
        assert result.exit_code == 1

    def test_no_match_writes_error_to_stderr(self, tmp_path: Path) -> None:
        """ROUTER_NO_MATCH or ROUTER_AMBIGUOUS error is reported (CliRunner merges streams)."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "the quick brown fox", "--json"],
                catch_exceptions=False,
            )
        # CliRunner merges stderr into output by default
        assert result.exit_code == 1
        out = result.output.strip()
        assert out, "Expected error output on failure"
        err_data = json.loads(out)
        assert err_data.get("error") == "routing_failed"
        assert err_data.get("error_code") in ("ROUTER_NO_MATCH", "ROUTER_AMBIGUOUS")

    def test_no_profiles_exits_1(self, tmp_path: Path) -> None:
        """When no profiles are registered, router raises RouterAmbiguityError → exit 1."""
        project = _setup_project(tmp_path)
        # Empty mock registry — no profiles
        empty_registry = _make_mock_registry([])
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=empty_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "implement the feature", "--json"],
            )
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Profile-hint guarantee: do never passes profile_hint
# ---------------------------------------------------------------------------


class TestDoNeverUsesProfileHint:
    def test_executor_always_called_with_none_profile_hint(self, tmp_path: Path) -> None:
        """The do command always passes profile_hint=None to executor.invoke()."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        captured_hints: list[object] = []

        from specify_cli.invocation.executor import ProfileInvocationExecutor

        original_invoke = ProfileInvocationExecutor.invoke

        def _spy_invoke(self: object, request_text: str, profile_hint: object = None, actor: str = "unknown") -> object:  # type: ignore[misc]
            captured_hints.append(profile_hint)
            return original_invoke(self, request_text, profile_hint=profile_hint, actor=actor)  # type: ignore[misc]

        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
            patch.object(ProfileInvocationExecutor, "invoke", _spy_invoke),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "implement the feature", "--json"],
            )
        assert result.exit_code == 0, result.output
        assert len(captured_hints) == 1
        assert captured_hints[0] is None, f"do command must always pass profile_hint=None, got: {captured_hints[0]!r}"


# ---------------------------------------------------------------------------
# Help / discoverability tests
# ---------------------------------------------------------------------------


class TestDoHelp:
    def test_do_help_exits_zero(self) -> None:
        result = runner.invoke(cli_app, ["do", "--help"])
        assert result.exit_code == 0
        assert "do" in result.output.lower()

    def test_do_help_mentions_router(self) -> None:
        result = runner.invoke(cli_app, ["do", "--help"])
        assert result.exit_code == 0
        # Should mention routing / ActionRouter concept
        assert any(keyword in result.output.lower() for keyword in ("route", "router", "profile", "dispatch"))
