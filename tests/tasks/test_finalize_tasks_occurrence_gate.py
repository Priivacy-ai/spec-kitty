"""Integration tests for the finalize-tasks occurrence-map gate (#2345 WP01).

Locks the bulk-edit occurrence-map gate contract at the `finalize-tasks`
command boundary (ATDD red-first, T001). The gate reuses the existing,
unchanged `ensure_occurrence_classification_ready` enforcement in
`specify_cli.bulk_edit.gate` (C-001) — these are command-integration tests
that assert the CLI surfaces the SAME canonical error, not that the gate
logic itself is correct (that unit coverage already exists in
tests/specify_cli/bulk_edit/test_gate.py).

Observable contract (per WP01 prompt guidance): `finalize_tasks` runs other
`typer.Exit(1)` validators after the gate (requirement mapping, dependency
graph, ownership, the commit pipeline). A minimal bulk-edit fixture will not
satisfy those, so:
  - Fail cases assert the gate's error string is PRESENT and exit_code == 1.
  - Pass cases assert the gate's error string is ABSENT — NOT exit_code == 0
    (that would false-red on unrelated downstream validators the minimal
    fixture doesn't satisfy).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import Result
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.mission import app

pytestmark = pytest.mark.fast

runner = CliRunner()

GATE_ERROR_SNIPPET = "Occurrence map required"
GATE_PANEL_TITLE = "Bulk Edit Gate: BLOCKED"
# The gate's JSON error message (from _validate_occurrence_map_ready). Its
# presence — or the "gate_errors" key — is the unambiguous signal that the
# occurrence gate itself blocked (vs. an unrelated downstream validator).
GATE_BLOCK_MSG = "occurrence-map gate blocked"

# Genuinely admissible: all 8 STANDARD_CATEGORIES classified (check_admissibility,
# occurrence_map.py — FR-004 requires every standard category, not merely >=3).
# Mirrors the proven-admissible fixture in tests/next/test_occurrence_gate_next_loop.py.
VALID_ADMISSIBLE_OCCURRENCE_MAP = """\
target:
  term: oldName
  replacement: newName
  operation: rename
categories:
  code_symbols:
    action: rename
  import_paths:
    action: rename
  filesystem_paths:
    action: manual_review
  serialized_keys:
    action: do_not_change
  cli_commands:
    action: do_not_change
  user_facing_strings:
    action: rename_if_user_visible
  tests_fixtures:
    action: rename
  logs_telemetry:
    action: do_not_change
"""

INADMISSIBLE_OCCURRENCE_MAP_FEW_CATEGORIES = """\
target:
  term: oldName
  replacement: newName
  operation: rename
categories:
  code_symbols:
    action: rename
  import_paths:
    action: rename
"""

INVALID_OCCURRENCE_MAP_MISSING_TARGET = """\
categories:
  code_symbols:
    action: rename
"""


def _write_meta(feature_dir: Path, *, change_mode: str | None) -> None:
    meta: dict[str, object] = {"target_branch": "main"}
    if change_mode is not None:
        meta["change_mode"] = change_mode
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


def _write_occurrence_map(feature_dir: Path, content: str) -> None:
    (feature_dir / "occurrence_map.yaml").write_text(content, encoding="utf-8")


def _build_feature_dir(tmp_path: Path, *, change_mode: str | None) -> Path:
    """Minimal feature dir: meta.json only.

    Deliberately does not populate tasks/ or spec.md: the gate must fire (or
    no-op) before any downstream validator runs, so a minimal fixture is
    sufficient to prove the gate's own behavior in isolation.
    """
    feature_dir = tmp_path / "kitty-specs" / "001-test"
    feature_dir.mkdir(parents=True)
    _write_meta(feature_dir, change_mode=change_mode)
    return feature_dir


def _invoke(tmp_path: Path, feature_dir: Path, *, extra_args: list[str] | None = None) -> Result:
    args = ["finalize-tasks", "--json", *(extra_args or [])]
    with (
        patch(
            "specify_cli.cli.commands.agent.mission.locate_project_root",
            return_value=tmp_path,
        ),
        patch(
            "specify_cli.cli.commands.agent.mission._find_feature_directory",
            return_value=feature_dir,
        ),
    ):
        return runner.invoke(app, args)


def _invoke_human(tmp_path: Path, feature_dir: Path, *, extra_args: list[str] | None = None) -> Result:
    args = ["finalize-tasks", *(extra_args or [])]
    with (
        patch(
            "specify_cli.cli.commands.agent.mission.locate_project_root",
            return_value=tmp_path,
        ),
        patch(
            "specify_cli.cli.commands.agent.mission._find_feature_directory",
            return_value=feature_dir,
        ),
    ):
        return runner.invoke(app, args)


class TestFinalizeGateBlocksMissingMap:
    """change_mode=bulk_edit + no occurrence_map.yaml → gate error PRESENT, exit 1."""

    def test_json_mode(self, tmp_path: Path) -> None:
        feature_dir = _build_feature_dir(tmp_path, change_mode="bulk_edit")
        result = _invoke(tmp_path, feature_dir)
        assert result.exit_code == 1, result.stdout
        assert GATE_ERROR_SNIPPET in result.stdout

    def test_human_mode(self, tmp_path: Path) -> None:
        feature_dir = _build_feature_dir(tmp_path, change_mode="bulk_edit")
        result = _invoke_human(tmp_path, feature_dir)
        assert result.exit_code == 1, result.stdout
        assert GATE_PANEL_TITLE in result.stdout


class TestFinalizeGateBlocksSchemaInvalidMap:
    """change_mode=bulk_edit + schema-invalid map → gate error PRESENT, exit 1."""

    def test_json_mode(self, tmp_path: Path) -> None:
        feature_dir = _build_feature_dir(tmp_path, change_mode="bulk_edit")
        _write_occurrence_map(feature_dir, INVALID_OCCURRENCE_MAP_MISSING_TARGET)
        result = _invoke(tmp_path, feature_dir)
        assert result.exit_code == 1, result.stdout
        payload_line = next(
            line for line in result.stdout.splitlines() if line.strip().startswith("{")
        )
        payload = json.loads(payload_line)
        assert any("target" in err.lower() for err in payload["gate_errors"])


class TestFinalizeGateBlocksInadmissibleMap:
    """change_mode=bulk_edit + <3 categories (inadmissible) → gate error PRESENT, exit 1."""

    def test_json_mode(self, tmp_path: Path) -> None:
        feature_dir = _build_feature_dir(tmp_path, change_mode="bulk_edit")
        _write_occurrence_map(feature_dir, INADMISSIBLE_OCCURRENCE_MAP_FEW_CATEGORIES)
        result = _invoke(tmp_path, feature_dir)
        assert result.exit_code == 1, result.stdout
        payload_line = next(
            line for line in result.stdout.splitlines() if line.strip().startswith("{")
        )
        payload = json.loads(payload_line)
        assert any(
            "at least" in err.lower() or "categories" in err.lower()
            for err in payload["gate_errors"]
        )


def _assert_gate_did_not_fire(result: Result) -> None:
    """The occurrence gate must NOT be the failure.

    The minimal fixture still trips a DOWNSTREAM validator (exit 1), so we do
    NOT assert exit_code == 0. Instead we prove the occurrence gate itself
    passed: none of its error markers appear, and any JSON error payload
    present belongs to a different validator (no ``gate_errors`` key).
    """
    assert GATE_ERROR_SNIPPET not in result.stdout
    assert GATE_PANEL_TITLE not in result.stdout
    assert GATE_BLOCK_MSG not in result.stdout.lower()
    payload_line = next(
        (line for line in result.stdout.splitlines() if line.strip().startswith("{")),
        None,
    )
    if payload_line is not None:
        payload = json.loads(payload_line)
        assert "gate_errors" not in payload, payload
        assert "occurrence-map gate" not in str(payload.get("error", "")).lower()


class TestFinalizeGatePassesValidAdmissibleMap:
    """change_mode=bulk_edit + valid, admissible map → occurrence gate does NOT fire."""

    def test_json_mode(self, tmp_path: Path) -> None:
        feature_dir = _build_feature_dir(tmp_path, change_mode="bulk_edit")
        _write_occurrence_map(feature_dir, VALID_ADMISSIBLE_OCCURRENCE_MAP)
        result = _invoke(tmp_path, feature_dir)
        _assert_gate_did_not_fire(result)


class TestFinalizeGateNoOpForNonBulkEdit:
    """change_mode absent/standard → gate error ABSENT (gate is a no-op)."""

    def test_change_mode_absent(self, tmp_path: Path) -> None:
        feature_dir = _build_feature_dir(tmp_path, change_mode=None)
        result = _invoke(tmp_path, feature_dir)
        _assert_gate_did_not_fire(result)

    def test_change_mode_standard(self, tmp_path: Path) -> None:
        feature_dir = _build_feature_dir(tmp_path, change_mode="standard")
        result = _invoke(tmp_path, feature_dir)
        _assert_gate_did_not_fire(result)


class TestFinalizeGateBlocksInValidateOnlyMode:
    """--validate-only must also be blocked by the gate (proves it fires in both modes)."""

    def test_validate_only_blocks_missing_map(self, tmp_path: Path) -> None:
        feature_dir = _build_feature_dir(tmp_path, change_mode="bulk_edit")
        result = _invoke(tmp_path, feature_dir, extra_args=["--validate-only"])
        assert result.exit_code == 1, result.stdout
        assert GATE_ERROR_SNIPPET in result.stdout
