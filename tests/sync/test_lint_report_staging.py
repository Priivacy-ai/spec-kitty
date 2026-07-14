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


def test_noop_when_feature_dir_unwritable(tmp_path: Path, monkeypatch) -> None:
    """The OSError-on-write branch: an unwritable feature_dir is a quiet no-op."""
    repo_root, feature_dir = _make_repo(tmp_path)
    _write_report(repo_root, feature_scope=MISSION_SLUG)

    def _boom(*_args, **_kwargs):
        raise OSError("read-only file system")

    monkeypatch.setattr(Path, "write_text", _boom)

    staged = stage_charter_lint_report(feature_dir, MISSION_SLUG)

    assert staged is False


# ── #2628 fold: identity-form matching against the real DecayReport serializer ──

# mission_id is a 26-char ULID; mid8 is its first 8 chars (see Mission Identity
# Model). A mission scoped under any of these handles must still stage.
_MISSION_ID = "01KX3T12M7VMEV4JX1BZTDS6KQ"
_MID8 = _MISSION_ID[:8]
_META_SLUG = "decay-watch"


def _make_identified_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Repo + feature_dir carrying a real meta.json (mission_id + mission_slug).

    ``feature_dir.name`` (the canonical directory name the sync consumer keys by)
    deliberately differs from the meta ``mission_slug`` so the alias-set match is
    genuinely exercised rather than coincidentally passing on the directory name.
    """
    repo_root = tmp_path / "repo"
    (repo_root / ".kittify").mkdir(parents=True)
    feature_dir = repo_root / "kitty-specs" / f"{_META_SLUG}-{_MID8}"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_id": _MISSION_ID, "mission_slug": _META_SLUG}),
        encoding="utf-8",
    )
    return repo_root, feature_dir


def _write_real_report(repo_root: Path, *, feature_scope: str | None) -> str:
    """Serialize a genuine DecayReport so the staging gate stays coupled to the
    producer's real key names, not a hand-built dict."""
    from specify_cli.charter_runtime.lint.findings import DecayReport, LintFinding

    report = DecayReport(
        feature_scope=feature_scope,
        findings=[
            LintFinding(
                category="orphan",
                type="orphaned_directive",
                id="urn:directive:x",
                severity="high",
                message="orphaned",
                feature_id=feature_scope,
                remediation_hint="wire it up",
            ),
        ],
    )
    raw = report.to_json()
    (repo_root / ".kittify" / LINT_REPORT_FILENAME).write_text(raw, encoding="utf-8")
    return raw


@pytest.mark.parametrize(
    "handle",
    [_MISSION_ID, _MID8, _META_SLUG],
    ids=["mission_id", "mid8", "meta_slug"],
)
def test_stages_when_feature_scope_is_any_mission_handle(
    tmp_path: Path, handle: str,
) -> None:
    """A report scoped under mission_id / mid8 / slug all stage, even though the
    sync consumer keys by the (different) directory name."""
    repo_root, feature_dir = _make_identified_repo(tmp_path)
    # The consumer passes the canonical directory name as mission_slug — which is
    # NOT equal to any of the handles under test, proving the alias set is used.
    raw = _write_real_report(repo_root, feature_scope=handle)

    staged = stage_charter_lint_report(feature_dir, feature_dir.name)

    assert staged is True, f"report scoped under {handle!r} should stage"
    dest = feature_dir / LINT_REPORT_FILENAME
    assert dest.read_text(encoding="utf-8") == raw


def test_does_not_stage_when_scope_is_a_different_mission(tmp_path: Path) -> None:
    repo_root, feature_dir = _make_identified_repo(tmp_path)
    _write_real_report(repo_root, feature_scope="01JJJJJJJJJJJJJJJJJJJJJJJJ")

    staged = stage_charter_lint_report(feature_dir, feature_dir.name)

    assert staged is False
    assert not (feature_dir / LINT_REPORT_FILENAME).exists()


# ── #2628 fold: stale-copy lifecycle (reconcile downward) ──────────────────────


@pytest.mark.parametrize(
    "next_scope",
    [None, "099-someone-else"],
    ids=["global_rerun", "other_mission"],
)
def test_discards_stale_stage_when_source_rescoped(
    tmp_path: Path, next_scope: str | None,
) -> None:
    """A copy staged by an earlier scoped run is removed once the repo-global
    report is re-scoped away from this mission — no stale decay state lingers."""
    repo_root, feature_dir = _make_repo(tmp_path)
    _write_report(repo_root, feature_scope=MISSION_SLUG)
    assert stage_charter_lint_report(feature_dir, MISSION_SLUG) is True
    dest = feature_dir / LINT_REPORT_FILENAME
    assert dest.exists()  # staged by the scoped run

    # A later run overwrites the single repo-global report with a non-matching
    # scope; staging must reconcile the dossier by removing the stale copy.
    _write_report(repo_root, feature_scope=next_scope)

    assert stage_charter_lint_report(feature_dir, MISSION_SLUG) is False
    assert not dest.exists()


def test_preserves_stage_on_transient_unreadable_source(tmp_path: Path) -> None:
    """A transient corrupt/unreadable source must NOT wipe the last-known staged
    copy — only a positively-different valid scope reconciles downward."""
    repo_root, feature_dir = _make_repo(tmp_path)
    _write_report(repo_root, feature_scope=MISSION_SLUG)
    assert stage_charter_lint_report(feature_dir, MISSION_SLUG) is True
    dest = feature_dir / LINT_REPORT_FILENAME
    assert dest.exists()

    # Source goes briefly unparseable (mid-write / disk hiccup).
    (repo_root / ".kittify" / LINT_REPORT_FILENAME).write_text(
        "{corrupt", encoding="utf-8",
    )

    assert stage_charter_lint_report(feature_dir, MISSION_SLUG) is False
    assert dest.exists(), "transient read failure must preserve last-known copy"
