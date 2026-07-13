"""Tests for specify_cli.sync.lint_report_staging.

Covers the scoped staging of the repo-global charter-lint decay report into a
mission dossier (issue #2481): matching feature_scope stages the file,
mismatched/null scope does not, and missing/corrupt reports are quiet no-ops.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.sync.lint_report_staging import (
    LINT_REPORT_FILENAME,
    stage_charter_lint_report,
)

pytestmark = pytest.mark.fast

MISSION_SLUG = "047-decay-watch"


def _make_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Create a repo root (with .kittify marker) and a feature dir under it."""
    repo_root = tmp_path / "repo"
    (repo_root / ".kittify").mkdir(parents=True)
    feature_dir = repo_root / "kitty-specs" / MISSION_SLUG
    feature_dir.mkdir(parents=True)
    return repo_root, feature_dir


def _write_report(repo_root: Path, *, feature_scope: str | None) -> str:
    report = {
        "scanned_at": "2026-07-13T00:00:00+00:00",
        "feature_scope": feature_scope,
        "duration_seconds": 0.5,
        "drg_node_count": 3,
        "drg_edge_count": 2,
        "graph_state": "merged",
        "finding_count": 1,
        "findings": [
            {
                "category": "orphan",
                "type": "orphaned_directive",
                "id": "urn:directive:x",
                "severity": "high",
                "message": "orphaned",
                "feature_id": feature_scope,
                "remediation_hint": "wire it up",
            },
        ],
    }
    raw = json.dumps(report, indent=2)
    (repo_root / ".kittify" / LINT_REPORT_FILENAME).write_text(raw, encoding="utf-8")
    return raw


def test_stages_when_feature_scope_matches(tmp_path: Path) -> None:
    repo_root, feature_dir = _make_repo(tmp_path)
    raw = _write_report(repo_root, feature_scope=MISSION_SLUG)

    staged = stage_charter_lint_report(feature_dir, MISSION_SLUG)

    assert staged is True
    dest = feature_dir / LINT_REPORT_FILENAME
    assert dest.exists()
    assert dest.read_text(encoding="utf-8") == raw
    # Non-hidden so the indexer scan picks it up.
    assert not dest.name.startswith(".")


def test_does_not_stage_when_feature_scope_mismatch(tmp_path: Path) -> None:
    repo_root, feature_dir = _make_repo(tmp_path)
    _write_report(repo_root, feature_scope="099-other-mission")

    staged = stage_charter_lint_report(feature_dir, MISSION_SLUG)

    assert staged is False
    assert not (feature_dir / LINT_REPORT_FILENAME).exists()


def test_does_not_stage_when_feature_scope_null(tmp_path: Path) -> None:
    repo_root, feature_dir = _make_repo(tmp_path)
    _write_report(repo_root, feature_scope=None)

    staged = stage_charter_lint_report(feature_dir, MISSION_SLUG)

    assert staged is False
    assert not (feature_dir / LINT_REPORT_FILENAME).exists()


def test_noop_when_report_missing(tmp_path: Path) -> None:
    _repo_root, feature_dir = _make_repo(tmp_path)

    staged = stage_charter_lint_report(feature_dir, MISSION_SLUG)

    assert staged is False
    assert not (feature_dir / LINT_REPORT_FILENAME).exists()


def test_noop_when_report_corrupt(tmp_path: Path) -> None:
    repo_root, feature_dir = _make_repo(tmp_path)
    (repo_root / ".kittify" / LINT_REPORT_FILENAME).write_text(
        "{not valid json", encoding="utf-8",
    )

    staged = stage_charter_lint_report(feature_dir, MISSION_SLUG)

    assert staged is False
    assert not (feature_dir / LINT_REPORT_FILENAME).exists()


def test_noop_when_report_is_json_but_not_object(tmp_path: Path) -> None:
    repo_root, feature_dir = _make_repo(tmp_path)
    (repo_root / ".kittify" / LINT_REPORT_FILENAME).write_text(
        "[1, 2, 3]", encoding="utf-8",
    )

    staged = stage_charter_lint_report(feature_dir, MISSION_SLUG)

    assert staged is False
    assert not (feature_dir / LINT_REPORT_FILENAME).exists()


def test_noop_when_repo_root_not_locatable(tmp_path: Path, monkeypatch) -> None:
    # A bare directory with no .kittify marker and SPECIFY_REPO_ROOT unset
    # resolves to no project root.
    monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)
    from specify_cli.sync import lint_report_staging

    monkeypatch.setattr(
        lint_report_staging, "locate_project_root", lambda _feature_dir: None,
    )
    feature_dir = tmp_path / "loose"
    feature_dir.mkdir()

    staged = stage_charter_lint_report(feature_dir, MISSION_SLUG)

    assert staged is False
    assert not (feature_dir / LINT_REPORT_FILENAME).exists()
