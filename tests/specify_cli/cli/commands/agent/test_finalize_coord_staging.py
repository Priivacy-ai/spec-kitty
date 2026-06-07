"""Regression (#1589): finalize must not clobber the coordination event log.

On coordination-topology missions the canonical ``status.events.jsonl`` +
``status.json`` are owned by the transactional status emitter, which commits the
bootstrap's lane-state events into the coordination worktree. Finalize used to
copy the primary checkout's stale copies over them before committing, wiping the
seeded lane state. These tests pin the corrected staging behaviour.
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.cli.commands.agent.mission import (
    _COORD_OWNED_STATUS_FILES,
    _stage_finalize_artifacts_in_coord_worktree,
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_canonical_status_files_excluded_from_coord_staging(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    feature_dir = repo_root / "kitty-specs" / "060-test"

    primary_events = _write(feature_dir / "status.events.jsonl", "STALE-PRIMARY\n")
    primary_snapshot = _write(feature_dir / "status.json", "{}\n")
    tasks_md = _write(feature_dir / "tasks.md", "# tasks\n")
    lanes = _write(feature_dir / "lanes.json", '{"lanes": []}\n')
    files_to_commit = [primary_events, primary_snapshot, tasks_md, lanes]

    coord_wt = tmp_path / "coord"
    coord_feature = coord_wt / "kitty-specs" / "060-test"
    # The seeded lane-state log the transactional emitter already wrote.
    seeded = _write(coord_feature / "status.events.jsonl", "SEEDED-LANE-EVENTS\n")

    staged = _stage_finalize_artifacts_in_coord_worktree(
        files_to_commit, coord_wt, repo_root
    )

    staged_names = {p.name for p in staged}
    # The canonical status log + snapshot are NOT staged from the primary copy.
    assert _COORD_OWNED_STATUS_FILES == {"status.events.jsonl", "status.json"}
    assert staged_names == {"tasks.md", "lanes.json"}
    # Planning artifacts are copied into the coord worktree for the commit.
    assert (coord_feature / "tasks.md").read_text(encoding="utf-8") == "# tasks\n"
    # The seeded coordination event log is left intact (not clobbered).
    assert seeded.read_text(encoding="utf-8") == "SEEDED-LANE-EVENTS\n"


def test_staging_copies_only_existing_non_status_artifacts(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    feature_dir = repo_root / "kitty-specs" / "060-test"
    tasks_md = _write(feature_dir / "tasks.md", "# tasks\n")
    missing = feature_dir / "acceptance-matrix.json"  # not created on disk
    files_to_commit = [tasks_md, missing]

    coord_wt = tmp_path / "coord"

    staged = _stage_finalize_artifacts_in_coord_worktree(
        files_to_commit, coord_wt, repo_root
    )

    # Both non-status paths are returned (for staging); only the existing one is
    # physically copied into the coord worktree.
    assert {p.name for p in staged} == {"tasks.md", "acceptance-matrix.json"}
    assert (coord_wt / "kitty-specs" / "060-test" / "tasks.md").exists()
    assert not (coord_wt / "kitty-specs" / "060-test" / "acceptance-matrix.json").exists()
