"""ATDD CLI tests for ``spec-kitty migrate backfill-mission-type`` (WP02).

Drives the real command via ``typer.testing.CliRunner`` over real fixture
corpora, wrapping WP01's ``backfill_mission_type_repo``. Covers:

* AC-7 (FR-006) — ``--dry-run --json`` and live ``--json`` payloads carry
  identical keys/schema.
* AC-8 (FR-007) — exit-code contract: live non-zero iff ``error > 0``;
  ``--dry-run`` always ``0``; clean live ``0``.
* AC-9 (FR-008) — an unknown ``--mission`` slug exits non-zero with a
  structured error (never a silent ``wrote=0`` / exit-0).
* M3/FR-007 — a ``needs_manual_resolution``-only run exits ``0`` and prints
  the actionable diagnostic (a valid mission type / profile, not necessarily
  a typo).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import Result
from typer.testing import CliRunner

from specify_cli.cli.commands.migrate_cmd import app as migrate_app

pytestmark = [pytest.mark.unit, pytest.mark.fast]

runner = CliRunner()

_LOCATE = "specify_cli.cli.commands.migrate_cmd.locate_project_root"


def _invoke(repo_root: Path, args: list[str]) -> Result:
    with patch(_LOCATE, return_value=repo_root):
        return runner.invoke(migrate_app, ["backfill-mission-type", *args])


def _write_meta(repo_root: Path, slug: str, meta: dict[str, object]) -> Path:
    feature_dir = repo_root / "kitty-specs" / slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )
    return feature_dir


def _write_corrupt_meta(repo_root: Path, slug: str) -> Path:
    feature_dir = repo_root / "kitty-specs" / slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text("{not valid json", encoding="utf-8")
    return feature_dir


def test_command_registered_in_help() -> None:
    result = runner.invoke(migrate_app, ["--help"])
    assert result.exit_code == 0
    assert "backfill-mission-type" in result.stdout


def test_missing_project_root_errors() -> None:
    with patch(_LOCATE, return_value=None):
        result = runner.invoke(migrate_app, ["backfill-mission-type"])
    assert result.exit_code == 1


# --- AC-7: JSON shape identical between dry-run and live --------------------


def test_json_shape_identical_dry_run_and_live(tmp_path: Path) -> None:
    repo_a = tmp_path / "repo-a"
    repo_b = tmp_path / "repo-b"
    _write_meta(repo_a, "001-alpha", {"mission": "software-dev"})
    _write_meta(repo_b, "001-alpha", {"mission": "software-dev"})

    dry_result = _invoke(repo_a, ["--dry-run", "--json"])
    live_result = _invoke(repo_b, ["--json"])

    assert dry_result.exit_code == 0
    assert live_result.exit_code == 0

    dry_payload = json.loads(dry_result.stdout)
    live_payload = json.loads(live_result.stdout)

    assert dry_payload["dry_run"] is True
    assert live_payload["dry_run"] is False
    assert set(dry_payload.keys()) == set(live_payload.keys())
    assert set(dry_payload["summary"].keys()) == set(live_payload["summary"].keys())
    assert dry_payload["summary"].keys() >= {
        "total",
        "wrote",
        "skip",
        "needs_manual_resolution",
        "error",
    }
    assert len(dry_payload["results"]) == len(live_payload["results"]) == 1
    assert set(dry_payload["results"][0].keys()) == set(live_payload["results"][0].keys())
    assert set(dry_payload["results"][0].keys()) == {
        "slug",
        "action",
        "mission_type",
        "legacy_value",
        "reason",
        "dossier_warning",
    }


# --- AC-8: exit codes (error / dry-run / clean) ------------------------------


def test_exit_codes_error_dryrun_clean(tmp_path: Path) -> None:
    # A --dry-run over an error mission must still exit 0 (m3).
    repo_dry = tmp_path / "repo-dry"
    _write_corrupt_meta(repo_dry, "001-corrupt")
    dry_result = _invoke(repo_dry, ["--dry-run", "--json"])
    assert dry_result.exit_code == 0, "dry-run is always 0, even when error > 0"
    dry_payload = json.loads(dry_result.stdout)
    assert dry_payload["summary"]["error"] == 1

    # A live run over the same error mission must exit non-zero.
    repo_live_error = tmp_path / "repo-live-error"
    _write_corrupt_meta(repo_live_error, "001-corrupt")
    live_error_result = _invoke(repo_live_error, ["--json"])
    assert live_error_result.exit_code != 0
    live_error_payload = json.loads(live_error_result.stdout)
    assert live_error_payload["summary"]["error"] == 1

    # A clean live run exits 0.
    repo_clean = tmp_path / "repo-clean"
    _write_meta(repo_clean, "002-clean", {"mission": "software-dev"})
    clean_result = _invoke(repo_clean, ["--json"])
    assert clean_result.exit_code == 0
    clean_payload = json.loads(clean_result.stdout)
    assert clean_payload["summary"]["error"] == 0


# --- AC-9: unknown --mission slug --------------------------------------------


def test_unknown_mission_slug_structured_error(tmp_path: Path) -> None:
    (tmp_path / "kitty-specs").mkdir()

    result = _invoke(tmp_path, ["--mission", "nope"])

    assert result.exit_code != 0
    assert "nope" in result.output
    assert "No mission directory found" in result.output


# --- M3/FR-007: needs_manual-only run exits 0 with actionable diagnostic ----


def test_needs_manual_only_exits_zero_with_diagnostic(tmp_path: Path) -> None:
    _write_meta(tmp_path, "001-typo", {"mission": "sofware-dev"})

    result = _invoke(tmp_path, [])

    assert result.exit_code == 0
    assert "001-typo" in result.output
    assert "governance profile resolves" in result.output
    assert "not necessarily a typo" in result.output.lower()
