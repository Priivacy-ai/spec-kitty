"""Integration tests for spec-kitty advise, ask, and profile-invocation complete CLI surfaces."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli import app as cli_app
from glossary.chokepoint import GlossaryObservationBundle
from glossary.models import (
    ConflictType,
    SemanticConflict,
    SenseRef,
    Severity,
    TermSurface,
)
from specify_cli.invocation.writer import EVENTS_DIR

# Marked for mutmut sandbox skip — subprocess CLI invocation.
pytestmark = pytest.mark.non_sandbox


class ArgvCliRunner(CliRunner):
    def invoke(self, app, args=None, **kwargs):  # type: ignore[no-untyped-def]
        argv = ["spec-kitty", *(list(args) if args is not None and not isinstance(args, str) else [])]
        with patch.object(sys, "argv", argv):
            return super().invoke(app, args, **kwargs)


runner = ArgvCliRunner()

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


# ---------------------------------------------------------------------------
# advise tests
# ---------------------------------------------------------------------------


class TestAdviseWithExplicitProfile:
    def test_exits_zero_and_returns_json_payload(self, tmp_path: Path) -> None:
        """advise --profile implementer-fixture returns valid JSON InvocationPayload."""
        project = _setup_project(tmp_path)
        with (
            patch("specify_cli.cli.commands.advise.find_repo_root", return_value=project),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["advise", "implement the feature", "--profile", "implementer-fixture", "--json"],
            )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "invocation_id" in data
        assert data["profile_id"] == "implementer-fixture"
        assert data["action"] is not None
        # WP06 carry-over from WP02 review: ask/advise JSON also carries the
        # close contract (the Op stays open until the agent closes it).
        assert data["status"] == "open" and "close_contract" in data

    def test_advisory_close_contract_omits_evidence_flag(self, tmp_path: Path) -> None:
        """Advisory mode refuses --evidence (InvalidModeForEvidenceError), so the
        close contract must not advertise evidence_flag (contracts/cli-do-output.md)."""
        project = _setup_project(tmp_path)
        with (
            patch("specify_cli.cli.commands.advise.find_repo_root", return_value=project),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["advise", "implement the feature", "--profile", "implementer-fixture", "--json"],
            )
        assert result.exit_code == 0, result.output
        contract = json.loads(result.output)["close_contract"]
        assert "evidence_flag" not in contract, "advisory-mode close contract must omit evidence_flag"
        assert contract["artifact_flag"] == "--artifact"
        assert contract["commit_flag"] == "--commit"

    def test_creates_jsonl_file(self, tmp_path: Path) -> None:
        """A JSONL file is written before the response is output."""
        project = _setup_project(tmp_path)
        with (
            patch("specify_cli.cli.commands.advise.find_repo_root", return_value=project),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["advise", "implement the feature", "--profile", "implementer-fixture", "--json"],
            )
        assert result.exit_code == 0, result.output
        jsonl_files = [path for path in (project / EVENTS_DIR).glob("*.jsonl") if path.name != "ops-index.jsonl"]
        assert len(jsonl_files) == 1

    def test_rich_output_exits_zero(self, tmp_path: Path) -> None:
        """Without --json, rich output is produced with exit 0."""
        project = _setup_project(tmp_path)
        with (
            patch("specify_cli.cli.commands.advise.find_repo_root", return_value=project),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["advise", "implement the feature", "--profile", "implementer-fixture"],
            )
        assert result.exit_code == 0, result.output

    def test_rich_output_close_hint_includes_required_outcome(self, tmp_path: Path) -> None:
        """Rich close hint must stay executable now that --outcome is required."""
        project = _setup_project(tmp_path)
        with (
            patch("specify_cli.cli.commands.advise.find_repo_root", return_value=project),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["advise", "implement the feature", "--profile", "implementer-fixture"],
            )
        assert result.exit_code == 0, result.output
        flat = result.output.replace("\n", " ")
        assert "profile-invocation complete" in flat
        assert "--outcome <done|failed|abandoned>" in flat

    def test_rich_output_surfaces_high_severity_glossary_warning(self, tmp_path: Path) -> None:
        """High-severity glossary conflicts should be shown inline before governance context."""
        project = _setup_project(tmp_path)
        with (
            patch("specify_cli.cli.commands.advise.find_repo_root", return_value=project),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
            patch(
                "glossary.chokepoint.GlossaryChokepoint.run",
                return_value=_high_severity_bundle(),
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["advise", "implement the feature", "--profile", "implementer-fixture"],
            )
        assert result.exit_code == 0, result.output
        assert "High-severity terminology conflicts detected before this invocation." in result.output
        assert "lane (ambiguous)" in result.output
        assert result.output.index("lane (ambiguous)") < result.output.index("compact governance context")

    def test_rich_output_includes_op_record_commit_hint(self, tmp_path: Path) -> None:
        """Rich output prints a git add hint for the op record file."""
        project = _setup_project(tmp_path)
        with (
            patch("specify_cli.cli.commands.advise.find_repo_root", return_value=project),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["advise", "implement the feature", "--profile", "implementer-fixture"],
            )
        assert result.exit_code == 0, result.output
        assert "git add kitty-ops/" in result.output
        assert ".jsonl" in result.output

    def test_json_output_omits_op_record_commit_hint(self, tmp_path: Path) -> None:
        """--json output does not include the commit hint (machine-readable path)."""
        project = _setup_project(tmp_path)
        with (
            patch("specify_cli.cli.commands.advise.find_repo_root", return_value=project),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["advise", "--json", "implement the feature", "--profile", "implementer-fixture"],
            )
        assert result.exit_code == 0, result.output
        assert "git add kitty-ops/" not in result.output

    def test_json_output_does_not_render_inline_glossary_notices(self, tmp_path: Path) -> None:
        """--json output must stay a single parseable JSON document."""
        project = _setup_project(tmp_path)
        with (
            patch("specify_cli.cli.commands.advise.find_repo_root", return_value=project),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
            patch("glossary.observation.ObservationSurface.collect_notices") as collect,
            patch("glossary.observation.ObservationSurface.render_notices") as render,
        ):
            result = runner.invoke(
                cli_app,
                ["advise", "--json", "implement the feature", "--profile", "implementer-fixture"],
            )
        assert result.exit_code == 0, result.output
        json.loads(result.output)
        collect.assert_not_called()
        render.assert_not_called()


class TestAdviseMissingProfile:
    def test_missing_profile_exits_1(self, tmp_path: Path) -> None:
        """Requesting a non-existent profile returns exit 1 with structured error."""
        project = _setup_project(tmp_path)
        with (
            patch("specify_cli.cli.commands.advise.find_repo_root", return_value=project),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["advise", "implement", "--profile", "nonexistent-profile", "--json"],
            )
        assert result.exit_code == 1
        # Error JSON is written to stderr; CliRunner merges streams into .output by default
        out = result.output.strip()
        assert out, "Expected error output"
        err_data = json.loads(out)
        assert "profile_not_found" in err_data.get("error", "")


class TestAdviseNoCharter:
    def test_no_charter_governance_context_unavailable_exits_zero(self, tmp_path: Path) -> None:
        """When charter is missing, governance_context_available=False but exit is still 0."""
        project = _setup_project(tmp_path)
        with (
            patch("specify_cli.cli.commands.advise.find_repo_root", return_value=project),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_MISSING_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["advise", "implement the feature", "--profile", "implementer-fixture", "--json"],
            )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["governance_context_available"] is False
        assert data["invocation_id"]  # record still written

    def test_no_charter_jsonl_still_created(self, tmp_path: Path) -> None:
        """JSONL record is written even when charter context is unavailable."""
        project = _setup_project(tmp_path)
        with (
            patch("specify_cli.cli.commands.advise.find_repo_root", return_value=project),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_MISSING_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["advise", "implement the feature", "--profile", "implementer-fixture", "--json"],
            )
        assert result.exit_code == 0
        jsonl_files = [path for path in (project / EVENTS_DIR).glob("*.jsonl") if path.name != "ops-index.jsonl"]
        assert len(jsonl_files) == 1


# ---------------------------------------------------------------------------
# ask shim tests
# ---------------------------------------------------------------------------


class TestAskShim:
    def test_ask_delegates_to_advise(self, tmp_path: Path) -> None:
        """ask <profile> <request> is equivalent to advise --profile <profile> <request>."""
        project = _setup_project(tmp_path)
        with (
            patch("specify_cli.cli.commands.advise.find_repo_root", return_value=project),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["ask", "implementer-fixture", "implement the feature", "--json"],
            )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["profile_id"] == "implementer-fixture"
        assert "invocation_id" in data

    def test_ask_missing_profile_exits_1(self, tmp_path: Path) -> None:
        """ask with unknown profile exits 1."""
        project = _setup_project(tmp_path)
        with (
            patch("specify_cli.cli.commands.advise.find_repo_root", return_value=project),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["ask", "no-such-profile", "implement something", "--json"],
            )
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# profile-invocation complete tests
# ---------------------------------------------------------------------------


class TestProfileInvocationComplete:
    def _invoke_and_get_id(self, project: Path) -> str:
        """Helper: run advise and return the invocation_id."""
        with (
            patch("specify_cli.cli.commands.advise.find_repo_root", return_value=project),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["advise", "implement the feature", "--profile", "implementer-fixture", "--json"],
            )
        assert result.exit_code == 0, result.output
        return json.loads(result.output)["invocation_id"]

    def test_complete_closes_record(self, tmp_path: Path) -> None:
        """profile-invocation complete --invocation-id <id> appends completed event."""
        project = _setup_project(tmp_path)
        invocation_id = self._invoke_and_get_id(project)

        with patch("specify_cli.cli.commands.advise.find_repo_root", return_value=project):
            result2 = runner.invoke(
                cli_app,
                [
                    "profile-invocation",
                    "complete",
                    "--invocation-id",
                    invocation_id,
                    "--outcome",
                    "done",
                    "--json",
                ],
            )
        assert result2.exit_code == 0, result2.output
        data2 = json.loads(result2.output)
        assert data2["result"] == "success"
        assert data2["outcome"] == "done"

    def test_complete_requires_outcome(self, tmp_path: Path) -> None:
        """WP03: --outcome is required — a missing outcome is a usage error,
        never silently coerced to "done"."""
        project = _setup_project(tmp_path)
        invocation_id = self._invoke_and_get_id(project)

        with patch("specify_cli.cli.commands.advise.find_repo_root", return_value=project):
            result = runner.invoke(
                cli_app,
                [
                    "profile-invocation",
                    "complete",
                    "--invocation-id",
                    invocation_id,
                    "--json",
                ],
            )
        assert result.exit_code == 2, result.output

    def test_complete_already_closed_exits_one_with_error(self, tmp_path: Path) -> None:
        """WP03: calling complete twice exits 1 with the structured already-closed
        error — no duplicate write."""
        project = _setup_project(tmp_path)
        invocation_id = self._invoke_and_get_id(project)

        # First complete — succeeds
        with patch("specify_cli.cli.commands.advise.find_repo_root", return_value=project):
            runner.invoke(
                cli_app,
                [
                    "profile-invocation",
                    "complete",
                    "--invocation-id",
                    invocation_id,
                    "--outcome",
                    "done",
                    "--json",
                ],
            )

        # Second complete — structured error, exit 1
        with patch("specify_cli.cli.commands.advise.find_repo_root", return_value=project):
            result3 = runner.invoke(
                cli_app,
                [
                    "profile-invocation",
                    "complete",
                    "--invocation-id",
                    invocation_id,
                    "--outcome",
                    "done",
                    "--json",
                ],
            )
        assert result3.exit_code == 1, result3.output
        data3 = json.loads(result3.output)
        assert data3.get("error") == "already_closed"
        assert data3.get("invocation_id") == invocation_id

    def test_complete_unknown_invocation_exits_1(self, tmp_path: Path) -> None:
        """Completing a non-existent invocation_id exits 1."""
        project = _setup_project(tmp_path)
        (project / ".kittify").mkdir(parents=True, exist_ok=True)

        with patch("specify_cli.cli.commands.advise.find_repo_root", return_value=project):
            result = runner.invoke(
                cli_app,
                [
                    "profile-invocation",
                    "complete",
                    "--invocation-id",
                    "01AAAAAAAAAAAAAAAAAAAAAAA0",
                    "--outcome",
                    "done",
                    "--json",
                ],
            )
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Help / discoverability tests
# ---------------------------------------------------------------------------


class TestHelpDiscoverability:
    def test_advise_help_exits_zero(self) -> None:
        result = runner.invoke(cli_app, ["advise", "--help"])
        assert result.exit_code == 0
        assert "advise" in result.output.lower()

    def test_ask_help_exits_zero(self) -> None:
        result = runner.invoke(cli_app, ["ask", "--help"])
        assert result.exit_code == 0
        assert "ask" in result.output.lower()

    def test_profile_invocation_help_exits_zero(self) -> None:
        result = runner.invoke(cli_app, ["profile-invocation", "--help"])
        assert result.exit_code == 0
        assert "complete" in result.output.lower()
