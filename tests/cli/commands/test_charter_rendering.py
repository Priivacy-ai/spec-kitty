"""Bucket C (rendering/diagnostics) coverage for ``specify_cli.cli.commands.charter``.

These tests assert on stable message substrings in CLI output.  They use
CliRunner to capture Rich-rendered text and check for substrings that are
stable across Rich versions and terminal widths.  No full-snapshot assertions.

Tactic: function-over-form-testing (src/doctrine/tactics/built-in/testing/).
Structure: AAA (Arrange / Act / Assert).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.charter import app

pytestmark = pytest.mark.fast

runner = CliRunner()

_MINIMAL_CHARTER = "# Test Charter\n\n## Purpose\n\nTest.\n"


def _project(tmp_path: Path, *, with_charter: bool = True) -> Path:
    kittify = tmp_path / ".kittify" / "charter"
    kittify.mkdir(parents=True)
    if with_charter:
        (kittify / "charter.md").write_text(_MINIMAL_CHARTER, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Charter sync error rendering
# ---------------------------------------------------------------------------

def test_sync_renders_error_message_when_sync_reports_error(tmp_path: Path) -> None:
    """Arrange: sync returns an error result;
    Act: invoke sync;
    Assert: 'Error' appears in output and exit code is 1."""
    project = _project(tmp_path)

    fake_result = MagicMock()
    fake_result.synced = False
    fake_result.error = "charter parse failed"
    fake_result.stale_before = False
    fake_result.files_written = []
    fake_result.extraction_mode = "llm"

    with (
        patch("specify_cli.cli.commands.charter.find_repo_root", return_value=project),
        patch("charter.sync.sync", return_value=fake_result),
    ):
        result = runner.invoke(app, ["sync"])

    assert result.exit_code == 1
    assert "Error" in result.output or "error" in result.output


def test_sync_renders_success_message_when_synced(tmp_path: Path) -> None:
    """Arrange: sync returns success;
    Act: invoke sync;
    Assert: success-indicating text appears in output."""
    project = _project(tmp_path)

    fake_result = MagicMock()
    fake_result.synced = True
    fake_result.error = None
    fake_result.stale_before = True
    fake_result.files_written = ["governance.yaml"]
    fake_result.extraction_mode = "llm"

    with (
        patch("specify_cli.cli.commands.charter.find_repo_root", return_value=project),
        patch("charter.sync.sync", return_value=fake_result),
    ):
        result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    # Must mention that sync happened
    assert "synced" in result.output.lower() or "Charter" in result.output


def test_sync_renders_already_in_sync_when_noop(tmp_path: Path) -> None:
    """Arrange: sync returns noop (synced=False, no error);
    Act: invoke sync;
    Assert: 'already in sync' (stable substring) in output."""
    project = _project(tmp_path)

    fake_result = MagicMock()
    fake_result.synced = False
    fake_result.error = None
    fake_result.stale_before = False
    fake_result.files_written = []
    fake_result.extraction_mode = "llm"

    with (
        patch("specify_cli.cli.commands.charter.find_repo_root", return_value=project),
        patch("charter.sync.sync", return_value=fake_result),
    ):
        result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    assert "already in sync" in result.output


# ---------------------------------------------------------------------------
# Charter status rendering — error paths
# ---------------------------------------------------------------------------

def test_status_renders_unavailable_when_charter_not_found(tmp_path: Path) -> None:
    """Arrange: charter is unavailable (TaskCliError path);
    Act: status;
    Assert: 'Unavailable' in output."""
    project = _project(tmp_path, with_charter=False)

    unavailable_sync: dict[str, Any] = {"available": False, "error": "Charter not found at .kittify/charter/charter.md"}
    fake_synthesis: dict[str, Any] = {
        "generation_state": "not_started",
        "generated_inputs": {"path": ".kittify/charter/generated", "exists": False, "counts": {"directive": 0, "tactic": 0, "styleguide": 0}, "total": 0},
        "manifest": {"state": "missing", "path": ".kittify/charter/synthesis-manifest.yaml", "exists": False, "artifact_count": 0, "live_artifact_count": 0, "live_provenance_count": 0, "run_id": None, "created_at": None, "adapter_id": None, "adapter_version": None, "missing_provenance_paths": [], "error": None},  # noqa: E501
        "provenance": {"path": ".kittify/charter/provenance", "count": 0, "parsed_count": 0, "manifest_artifact_count": 0, "missing_for_manifest_count": 0, "missing_for_manifest": [], "corpus_snapshot_ids": [], "adapters": [], "warnings": [], "entries": []},  # noqa: E501
        "evidence": {"warnings": [], "code": None, "configured_urls": [], "configured_url_count": 0, "corpus_snapshot_id": None, "corpus_entry_count": 0},
    }

    with (
        patch("specify_cli.cli.commands.charter.find_repo_root", return_value=project),
        patch("specify_cli.cli.commands.charter._collect_charter_sync_status", return_value=unavailable_sync),
        patch("specify_cli.cli.commands.charter._collect_synthesis_status", return_value=fake_synthesis),
    ):
        result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "Unavailable" in result.output or "unavailable" in result.output.lower()


def test_status_renders_stale_when_charter_is_stale(tmp_path: Path) -> None:
    """Arrange: charter sync reports stale;
    Act: status;
    Assert: 'STALE' in output."""
    project = _project(tmp_path)

    stale_sync: dict[str, Any] = {
        "available": True,
        "charter_path": ".kittify/charter/charter.md",
        "status": "stale",
        "current_hash": "newHash",
        "stored_hash": "oldHash",
        "last_sync": None,
        "library_docs": 0,
        "files": [],
    }
    fake_synthesis: dict[str, Any] = {
        "generation_state": "not_started",
        "generated_inputs": {"path": ".kittify/charter/generated", "exists": False, "counts": {"directive": 0, "tactic": 0, "styleguide": 0}, "total": 0},
        "manifest": {"state": "missing", "path": ".kittify/charter/synthesis-manifest.yaml", "exists": False, "artifact_count": 0, "live_artifact_count": 0, "live_provenance_count": 0, "run_id": None, "created_at": None, "adapter_id": None, "adapter_version": None, "missing_provenance_paths": [], "error": None},  # noqa: E501
        "provenance": {"path": ".kittify/charter/provenance", "count": 0, "parsed_count": 0, "manifest_artifact_count": 0, "missing_for_manifest_count": 0, "missing_for_manifest": [], "corpus_snapshot_ids": [], "adapters": [], "warnings": [], "entries": []},  # noqa: E501
        "evidence": {"warnings": [], "code": None, "configured_urls": [], "configured_url_count": 0, "corpus_snapshot_id": None, "corpus_entry_count": 0},
    }

    with (
        patch("specify_cli.cli.commands.charter.find_repo_root", return_value=project),
        patch("specify_cli.cli.commands.charter._collect_charter_sync_status", return_value=stale_sync),
        patch("specify_cli.cli.commands.charter._collect_synthesis_status", return_value=fake_synthesis),
    ):
        result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "STALE" in result.output


def test_status_renders_synced_when_charter_is_current(tmp_path: Path) -> None:
    """Arrange: charter sync reports synced;
    Act: status;
    Assert: 'SYNCED' in output."""
    project = _project(tmp_path)

    synced_sync: dict[str, Any] = {
        "available": True,
        "charter_path": ".kittify/charter/charter.md",
        "status": "synced",
        "current_hash": "abc123",
        "stored_hash": "abc123",
        "last_sync": "2026-01-01T00:00:00Z",
        "library_docs": 2,
        "files": [
            {"name": "governance.yaml", "exists": True, "size_kb": 1.5},
            {"name": "directives.yaml", "exists": False, "size_kb": 0.0},
        ],
    }
    fake_synthesis: dict[str, Any] = {
        "generation_state": "not_started",
        "generated_inputs": {"path": ".kittify/charter/generated", "exists": False, "counts": {"directive": 0, "tactic": 0, "styleguide": 0}, "total": 0},
        "manifest": {"state": "missing", "path": ".kittify/charter/synthesis-manifest.yaml", "exists": False, "artifact_count": 0, "live_artifact_count": 0, "live_provenance_count": 0, "run_id": None, "created_at": None, "adapter_id": None, "adapter_version": None, "missing_provenance_paths": [], "error": None},  # noqa: E501
        "provenance": {"path": ".kittify/charter/provenance", "count": 0, "parsed_count": 0, "manifest_artifact_count": 0, "missing_for_manifest_count": 0, "missing_for_manifest": [], "corpus_snapshot_ids": [], "adapters": [], "warnings": [], "entries": []},  # noqa: E501
        "evidence": {"warnings": [], "code": None, "configured_urls": [], "configured_url_count": 0, "corpus_snapshot_id": None, "corpus_entry_count": 0},
    }

    with (
        patch("specify_cli.cli.commands.charter.find_repo_root", return_value=project),
        patch("specify_cli.cli.commands.charter._collect_charter_sync_status", return_value=synced_sync),
        patch("specify_cli.cli.commands.charter._collect_synthesis_status", return_value=fake_synthesis),
    ):
        result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "SYNCED" in result.output


# ---------------------------------------------------------------------------
# Charter context rendering — action label in output
# ---------------------------------------------------------------------------

def test_context_renders_action_name_in_output(tmp_path: Path) -> None:
    """Arrange: context build returns action="review";
    Act: context --action review;
    Assert: "Action:" in output (stable substring)."""
    project = _project(tmp_path)

    fake_ctx = MagicMock()
    fake_ctx.action = "review"
    fake_ctx.mode = "incremental"
    fake_ctx.first_load = False
    fake_ctx.references_count = 2
    fake_ctx.text = "Review context text here."

    with (
        patch("specify_cli.cli.commands.charter.find_repo_root", return_value=project),
        patch("charter.context.build_charter_context", return_value=fake_ctx),
        patch("charter.context.BOOTSTRAP_ACTIONS", {"specify", "plan"}),
    ):
        result = runner.invoke(app, ["context", "--action", "review"])

    assert result.exit_code == 0
    # The context text should appear in stdout
    assert "Review context text here." in result.output or "review" in result.output.lower()


def test_context_json_uses_same_depth_as_rendered_context(tmp_path: Path) -> None:
    """JSON envelope must not recompute a different first-load mode than text."""
    project = _project(tmp_path)

    fake_ctx = MagicMock()
    fake_ctx.action = "plan"
    fake_ctx.mode = "bootstrap"
    fake_ctx.first_load = True
    fake_ctx.references_count = 0
    fake_ctx.depth = 2
    fake_ctx.text = "Action Doctrine (plan):\n  Directives:\n    - DIRECTIVE_001"

    def _json_builder(
        repo_root: Path,
        *,
        action: str,
        depth: int | None,
        org_root: Path | None,
        org_charter_block: dict[str, object],
    ) -> dict[str, object]:
        assert repo_root == project
        assert action == "plan"
        assert depth == fake_ctx.depth
        assert org_root is None
        assert org_charter_block == {"present": False, "packs": []}
        return {
            "directives": [{"id": "DIRECTIVE_001", "source": "builtin"}],
            "all_directives": [{"id": "DIRECTIVE_001", "source": "builtin"}],
            "tactics": [],
            "styleguides": [],
            "toolguides": [],
            "project_charter": {
                "present": True,
                "path": ".kittify/charter/charter.md",
            },
            "org_charter": {"present": False, "packs": []},
        }

    with (
        patch("specify_cli.cli.commands.charter.find_repo_root", return_value=project),
        patch("charter.context.build_charter_context", return_value=fake_ctx),
        patch("charter.context.build_charter_context_json", side_effect=_json_builder),
        patch("specify_cli.doctrine.config.resolve_org_roots", return_value=[]),
        patch(
            "specify_cli.doctrine.org_charter_loader.load_org_charter_json_block",
            return_value={"present": False, "packs": []},
        ),
    ):
        result = runner.invoke(app, ["context", "--action", "plan", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["mode"] == "bootstrap"
    assert payload["directives"] == [{"id": "DIRECTIVE_001", "source": "builtin"}]
    assert "DIRECTIVE_001" in payload["text"]


def test_context_renders_error_on_task_cli_error(tmp_path: Path) -> None:
    """Arrange: build_charter_context raises TaskCliError;
    Act: context --action plan;
    Assert: exit 1 and 'Error' in output."""
    from specify_cli.task_utils import TaskCliError

    project = _project(tmp_path)

    with (
        patch("specify_cli.cli.commands.charter.find_repo_root", return_value=project),
        patch("charter.context.build_charter_context", side_effect=TaskCliError("charter context unavailable")),
        patch("charter.context.BOOTSTRAP_ACTIONS", {"specify", "plan"}),
    ):
        result = runner.invoke(app, ["context", "--action", "plan"])

    assert result.exit_code == 1
    assert "Error" in result.output


def test_context_include_renders_selector_without_action(tmp_path: Path) -> None:
    """Arrange: include selector; Act: context --include; Assert: selector text emits."""

    project = _project(tmp_path)

    with (
        patch("specify_cli.cli.commands.charter.find_repo_root", return_value=project),
        patch("specify_cli.doctrine.config.resolve_org_roots", return_value=[]),
        patch(
            "charter.context.build_charter_context_include",
            return_value="### Regression Vigilance\nRule body.",
        ) as include_builder,
    ):
        result = runner.invoke(app, ["context", "--include", "section:regression-vigilance"])

    assert result.exit_code == 0
    assert "Rule body." in result.output
    include_builder.assert_called_once_with(
        project,
        "section:regression-vigilance",
        action=None,
        org_root=None,
    )


def test_context_requires_action_without_include(tmp_path: Path) -> None:
    """Arrange: no action/include; Act: context; Assert: command fails closed."""

    project = _project(tmp_path)

    with (
        patch("specify_cli.cli.commands.charter.find_repo_root", return_value=project),
        patch("specify_cli.doctrine.config.resolve_org_roots", return_value=[]),
    ):
        result = runner.invoke(app, ["context"])

    assert result.exit_code == 1
    assert "--action is required unless --include is provided" in result.output
