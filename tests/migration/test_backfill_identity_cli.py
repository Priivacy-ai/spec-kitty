"""Tests for the mission_id backfill command (WP04 / T018-T022).

Covers:
- T018: idempotent ULID write (backfill_mission / backfill_repo)
- T019: CLI surface via typer.testing.CliRunner
- T020: legacy mission_number string coercion
- T021: dossier rehash (fire-and-forget; errors don't abort)
- T022: all six test cases (idempotency, preservation, coercion, orphan,
        dry-run, NFR-001 timing)

Do NOT add ``# type: ignore`` to this file — it must pass ``mypy --strict``
where possible.  (typer.testing imports require some flexibility.)
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.migrate_cmd import app as migrate_app
from specify_cli.migration.backfill_identity import backfill_repo


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_ULID_EXISTING = "01KNXQS9ATWWFXS3K5ZJ9E5008"


def _base_meta(slug: str) -> dict[str, Any]:
    """Return a minimal valid meta.json dict."""
    return {
        "slug": slug,
        "mission_slug": slug,
        "friendly_name": slug,
        "mission_type": "software-dev",
        "target_branch": "main",
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def _write_meta(feature_dir: Path, meta: dict[str, Any]) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_meta(feature_dir: Path) -> dict[str, Any]:
    result: dict[str, Any] = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
    return result


@pytest.fixture()
def specs_root(tmp_path: Path) -> Path:
    """Provide a tmp_path with a kitty-specs/ dir and .kittify/ marker."""
    specs = tmp_path / "kitty-specs"
    specs.mkdir()
    (tmp_path / ".kittify").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# T018 / T022-idempotency: second run must be all-skip
# ---------------------------------------------------------------------------


class TestIdempotency:
    """T022 — Idempotency: run twice, second run is all-skip."""

    def test_second_run_all_skip(self, specs_root: Path) -> None:
        slug = "001-alpha"
        d = specs_root / "kitty-specs" / slug
        _write_meta(d, _base_meta(slug))

        # First run: should write
        results1 = backfill_repo(specs_root)
        assert len(results1) == 1
        assert results1[0].action == "wrote"
        assert results1[0].mission_id is not None

        # Second run: must skip
        results2 = backfill_repo(specs_root)
        assert len(results2) == 1
        assert results2[0].action == "skip"
        assert results2[0].mission_id == results1[0].mission_id


# ---------------------------------------------------------------------------
# T022-preservation: existing mission_id is byte-identical after two runs
# ---------------------------------------------------------------------------


class TestPreservation:
    """T022 — Preservation: existing mission_id unchanged after both runs."""

    def test_existing_id_preserved(self, specs_root: Path) -> None:
        slug = "002-beta"
        d = specs_root / "kitty-specs" / slug
        meta = _base_meta(slug)
        meta["mission_id"] = _ULID_EXISTING
        meta["mission_number"] = 2
        _write_meta(d, meta)

        for _ in range(2):
            results = backfill_repo(specs_root)
            assert len(results) == 1
            assert results[0].action == "skip"
            assert results[0].mission_id == _ULID_EXISTING

        # File content untouched (mission_id byte-identical)
        loaded = _read_meta(d)
        assert loaded["mission_id"] == _ULID_EXISTING


# ---------------------------------------------------------------------------
# T020 / T022-coercion: "042" becomes 42 after first run
# ---------------------------------------------------------------------------


class TestCoercion:
    """T022 — Coercion: string mission_number becomes int after backfill."""

    def test_string_number_coerced(self, specs_root: Path) -> None:
        slug = "042-gamma"
        d = specs_root / "kitty-specs" / slug
        meta = _base_meta(slug)
        meta["mission_number"] = "042"
        _write_meta(d, meta)

        results = backfill_repo(specs_root)
        assert len(results) == 1
        r = results[0]
        assert r.number_coerced is True
        # mission_id was missing, so it was also written
        assert r.action == "wrote"

        loaded = _read_meta(d)
        assert loaded["mission_number"] == 42
        assert isinstance(loaded["mission_number"], int)
        assert "mission_id" in loaded

    def test_integer_number_unchanged(self, specs_root: Path) -> None:
        slug = "007-delta"
        d = specs_root / "kitty-specs" / slug
        meta = _base_meta(slug)
        meta["mission_number"] = 7
        _write_meta(d, meta)

        results = backfill_repo(specs_root)
        assert len(results) == 1
        assert results[0].number_coerced is False

        loaded = _read_meta(d)
        assert loaded["mission_number"] == 7

    def test_none_number_unchanged(self, specs_root: Path) -> None:
        slug = "003-epsilon"
        d = specs_root / "kitty-specs" / slug
        meta = _base_meta(slug)
        meta["mission_number"] = None
        _write_meta(d, meta)

        results = backfill_repo(specs_root)
        assert len(results) == 1
        assert results[0].number_coerced is False

    def test_sentinel_string_raises(self, specs_root: Path) -> None:
        slug = "004-zeta"
        d = specs_root / "kitty-specs" / slug
        meta = _base_meta(slug)
        meta["mission_number"] = "pending"
        _write_meta(d, meta)

        with pytest.raises(ValueError, match="pending"):
            backfill_repo(specs_root)

    def test_already_has_id_but_string_number_coerced(self, specs_root: Path) -> None:
        slug = "099-eta"
        d = specs_root / "kitty-specs" / slug
        meta = _base_meta(slug)
        meta["mission_id"] = _ULID_EXISTING
        meta["mission_number"] = "099"
        _write_meta(d, meta)

        results = backfill_repo(specs_root)
        assert len(results) == 1
        r = results[0]
        assert r.number_coerced is True
        assert r.mission_id == _ULID_EXISTING

        loaded = _read_meta(d)
        assert loaded["mission_number"] == 99
        assert loaded["mission_id"] == _ULID_EXISTING


# ---------------------------------------------------------------------------
# T022-orphan: corrupt JSON returns error, doesn't crash
# ---------------------------------------------------------------------------


class TestOrphanHandling:
    """T022 — Orphan: corrupt JSON produces error result, doesn't crash."""

    def test_corrupt_json_returns_error(self, specs_root: Path) -> None:
        slug = "005-theta"
        d = specs_root / "kitty-specs" / slug
        d.mkdir(parents=True)
        (d / "meta.json").write_text("{ this is not valid json }", encoding="utf-8")

        results = backfill_repo(specs_root)
        assert len(results) == 1
        r = results[0]
        assert r.action == "error"
        assert r.reason is not None
        assert "corrupt json" in r.reason.lower()

    def test_corrupt_json_doesnt_stop_other_missions(self, specs_root: Path) -> None:
        slug_bad = "005-iota"
        d_bad = specs_root / "kitty-specs" / slug_bad
        d_bad.mkdir(parents=True)
        (d_bad / "meta.json").write_text("NOT JSON", encoding="utf-8")

        slug_ok = "006-kappa"
        d_ok = specs_root / "kitty-specs" / slug_ok
        _write_meta(d_ok, _base_meta(slug_ok))

        results = backfill_repo(specs_root)
        assert len(results) == 2
        actions = {r.slug: r.action for r in results}
        assert actions[slug_bad] == "error"
        assert actions[slug_ok] == "wrote"

    def test_missing_meta_json_skipped(self, specs_root: Path) -> None:
        slug = "007-lambda"
        d = specs_root / "kitty-specs" / slug
        d.mkdir(parents=True)
        # no meta.json

        results = backfill_repo(specs_root)
        assert len(results) == 1
        assert results[0].action == "skip"
        assert results[0].reason is not None
        assert "not found" in results[0].reason


# ---------------------------------------------------------------------------
# T022-dry-run: --dry-run produces same shape, zero filesystem diffs
# ---------------------------------------------------------------------------


class TestDryRun:
    """T022 — Dry-run: same result shape, no filesystem writes."""

    def test_dry_run_no_writes(self, specs_root: Path) -> None:
        slug = "008-mu"
        d = specs_root / "kitty-specs" / slug
        _write_meta(d, _base_meta(slug))

        original_text = (d / "meta.json").read_text(encoding="utf-8")

        results = backfill_repo(specs_root, dry_run=True)
        assert len(results) == 1
        # Result shape: action indicates what would happen
        assert results[0].action == "wrote"
        assert results[0].mission_id is not None

        # File unchanged
        assert (d / "meta.json").read_text(encoding="utf-8") == original_text

    def test_dry_run_skip_already_set(self, specs_root: Path) -> None:
        slug = "009-nu"
        d = specs_root / "kitty-specs" / slug
        meta = _base_meta(slug)
        meta["mission_id"] = _ULID_EXISTING
        _write_meta(d, meta)

        results = backfill_repo(specs_root, dry_run=True)
        assert len(results) == 1
        assert results[0].action == "skip"


# ---------------------------------------------------------------------------
# T022-timing (NFR-001): 200 missions in < 5 seconds
# ---------------------------------------------------------------------------


class TestNFR001Timing:
    """T022 — NFR-001: 200-mission synthetic fixture completes in < 5 seconds.

    The dossier rehash step is mocked because it touches the SaaS network and
    heavy import chains — those are outside the scope of the pure-Python
    backfill budget defined by NFR-001.  The timing assertion covers the I/O
    path: 200 meta.json reads, ULID minting for missing ones, and 200 writes.
    """

    def test_200_missions_under_5s(self, tmp_path: Path) -> None:
        specs = tmp_path / "kitty-specs"
        specs.mkdir()
        (tmp_path / ".kittify").mkdir()

        # Create 200 missions, half with existing mission_id, half without
        for i in range(200):
            slug = f"{i:03d}-mission-{i}"
            d = specs / slug
            meta = _base_meta(slug)
            meta["mission_number"] = i
            if i % 2 == 0:
                meta["mission_id"] = _ULID_EXISTING
            _write_meta(d, meta)

        import specify_cli.migration.backfill_identity as _bi_mod

        start = time.monotonic()
        with patch.object(_bi_mod, "trigger_feature_dossier_sync_if_enabled", return_value=None):
            results = backfill_repo(tmp_path)
        elapsed = time.monotonic() - start

        assert len(results) == 200
        assert elapsed < 5.0, f"NFR-001 violated: {elapsed:.2f}s >= 5.0s for 200 missions"


# ---------------------------------------------------------------------------
# T019: CLI surface tests using typer.testing.CliRunner
# ---------------------------------------------------------------------------


class TestCLISurface:
    """T019 — CLI subcommand tests."""

    def _make_repo(self, tmp_path: Path) -> Path:
        """Create a minimal repo with one legacy and one complete mission."""
        specs = tmp_path / "kitty-specs"
        specs.mkdir()
        (tmp_path / ".kittify").mkdir()

        # legacy mission (no mission_id)
        slug_legacy = "010-xi"
        d_legacy = specs / slug_legacy
        _write_meta(d_legacy, _base_meta(slug_legacy))

        # complete mission (has mission_id)
        slug_complete = "011-omicron"
        d_complete = specs / slug_complete
        meta = _base_meta(slug_complete)
        meta["mission_id"] = _ULID_EXISTING
        _write_meta(d_complete, meta)

        return tmp_path

    def test_help_flag(self) -> None:
        runner = CliRunner()
        result = runner.invoke(migrate_app, ["backfill-identity", "--help"])
        assert result.exit_code == 0
        # Strip ANSI escape codes before checking — Rich markup can split
        # flag names across escape sequences (e.g. \x1b[…]-\x1b[…]-dry…).
        import re

        plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
        assert "mission_id" in plain
        assert "--dry-run" in plain
        assert "--json" in plain
        assert "--mission" in plain

    def test_dry_run_json_output_shape(self, tmp_path: Path) -> None:
        repo = self._make_repo(tmp_path)
        runner = CliRunner()
        with patch(
            "specify_cli.cli.commands.migrate_cmd.locate_project_root",
            return_value=repo,
        ):
            result = runner.invoke(migrate_app, ["backfill-identity", "--dry-run", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["dry_run"] is True
        assert "summary" in payload
        assert "results" in payload
        summary = payload["summary"]
        assert summary["total"] == 2
        assert summary["wrote"] == 1  # legacy mission would-write
        assert summary["skip"] == 1  # complete mission

    def test_exit_code_0_on_success(self, tmp_path: Path) -> None:
        repo = self._make_repo(tmp_path)
        runner = CliRunner()
        with patch(
            "specify_cli.cli.commands.migrate_cmd.locate_project_root",
            return_value=repo,
        ):
            result = runner.invoke(migrate_app, ["backfill-identity", "--dry-run", "--json"])
        assert result.exit_code == 0

    def test_exit_code_1_on_errors(self, tmp_path: Path) -> None:
        specs = tmp_path / "kitty-specs"
        specs.mkdir()
        (tmp_path / ".kittify").mkdir()
        slug = "012-pi"
        d = specs / slug
        d.mkdir()
        (d / "meta.json").write_text("INVALID", encoding="utf-8")

        runner = CliRunner()
        with patch(
            "specify_cli.cli.commands.migrate_cmd.locate_project_root",
            return_value=tmp_path,
        ):
            result = runner.invoke(migrate_app, ["backfill-identity", "--json"])
        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["summary"]["error"] == 1

    def test_mission_flag_scopes_to_one(self, tmp_path: Path) -> None:
        repo = self._make_repo(tmp_path)
        runner = CliRunner()
        with patch(
            "specify_cli.cli.commands.migrate_cmd.locate_project_root",
            return_value=repo,
        ):
            result = runner.invoke(
                migrate_app,
                ["backfill-identity", "--dry-run", "--json", "--mission", "010-xi"],
            )
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["summary"]["total"] == 1
        assert payload["results"][0]["slug"] == "010-xi"

    def test_json_result_fields(self, tmp_path: Path) -> None:
        repo = self._make_repo(tmp_path)
        runner = CliRunner()
        with patch(
            "specify_cli.cli.commands.migrate_cmd.locate_project_root",
            return_value=repo,
        ):
            result = runner.invoke(migrate_app, ["backfill-identity", "--dry-run", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        for item in payload["results"]:
            assert "slug" in item
            assert "action" in item
            assert "mission_id" in item
            assert "number_coerced" in item
            assert "reason" in item
            assert "dossier_warning" in item

    def test_summary_counts_coercions(self, tmp_path: Path) -> None:
        specs = tmp_path / "kitty-specs"
        specs.mkdir()
        (tmp_path / ".kittify").mkdir()
        slug = "013-rho"
        d = specs / slug
        meta = _base_meta(slug)
        meta["mission_number"] = "013"
        _write_meta(d, meta)

        runner = CliRunner()
        with patch(
            "specify_cli.cli.commands.migrate_cmd.locate_project_root",
            return_value=tmp_path,
        ):
            result = runner.invoke(migrate_app, ["backfill-identity", "--dry-run", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["summary"]["number_coerced"] == 1


# ---------------------------------------------------------------------------
# T021: dossier rehash — fire-and-forget, failures don't abort
# ---------------------------------------------------------------------------


class TestDossierRehash:
    """T021 — Dossier rehash warnings don't fail the run."""

    def test_dossier_failure_captured_as_warning(self, specs_root: Path) -> None:
        slug = "014-sigma"
        d = specs_root / "kitty-specs" / slug
        _write_meta(d, _base_meta(slug))

        import specify_cli.migration.backfill_identity as _bi_mod

        with patch.object(
            _bi_mod,
            "trigger_feature_dossier_sync_if_enabled",
            side_effect=RuntimeError("dossier exploded"),
        ):
            results = backfill_repo(specs_root)

        assert len(results) == 1
        r = results[0]
        assert r.action == "wrote"
        assert r.dossier_warning is not None
        assert "dossier rehash failed" in r.dossier_warning

    def test_dossier_not_called_for_skipped(self, specs_root: Path) -> None:
        slug = "015-tau"
        d = specs_root / "kitty-specs" / slug
        meta = _base_meta(slug)
        meta["mission_id"] = _ULID_EXISTING
        meta["mission_number"] = 15
        _write_meta(d, meta)

        import specify_cli.migration.backfill_identity as _bi_mod

        mock_fn = MagicMock()
        with patch.object(_bi_mod, "trigger_feature_dossier_sync_if_enabled", mock_fn):
            results = backfill_repo(specs_root)

        assert len(results) == 1
        assert results[0].action == "skip"
        mock_fn.assert_not_called()

    def test_dossier_called_for_wrote(self, specs_root: Path) -> None:
        slug = "016-upsilon"
        d = specs_root / "kitty-specs" / slug
        _write_meta(d, _base_meta(slug))

        import specify_cli.migration.backfill_identity as _bi_mod

        mock_fn = MagicMock(return_value=None)
        with patch.object(_bi_mod, "trigger_feature_dossier_sync_if_enabled", mock_fn):
            results = backfill_repo(specs_root)

        assert len(results) == 1
        assert results[0].action == "wrote"
        mock_fn.assert_called_once()
