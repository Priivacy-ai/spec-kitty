"""Tests for specify_cli.team_projection.provenance (D1-T1).

Covers §4 rows N10-N13 of the D1 contract draft (clean-tree/exact-commit
behavior) plus the basic byte-determinism/no-timestamp guarantee that every
other module's provenance envelope depends on.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )


def test_capture_provenance_clean_tree(temp_repo: Path) -> None:
    from specify_cli.team_projection.provenance import capture_provenance

    prov = capture_provenance(temp_repo, require_clean=False)

    assert prov.schema_ == "exact_commit_provenance/v1"
    assert prov.repo == "spec-kitty"
    assert len(prov.commit_sha) == 40
    assert prov.commit_sha == _git(temp_repo, "rev-parse", "HEAD").stdout.strip()
    assert prov.tree_clean is True
    assert prov.generator == "spec-kitty"
    assert isinstance(prov.generator_version, str) and prov.generator_version


def test_capture_provenance_has_no_wall_clock_field() -> None:
    """§3.3 decision 4: no generated_at/timestamp field anywhere on the envelope."""
    from specify_cli.team_projection.provenance import ExactCommitProvenance

    fields = set(ExactCommitProvenance.model_fields.keys())
    for forbidden in ("generated_at", "timestamp", "created_at", "now"):
        assert forbidden not in fields


def test_capture_provenance_frozen_and_closed() -> None:
    from specify_cli.team_projection.provenance import ExactCommitProvenance

    assert ExactCommitProvenance.model_config.get("frozen") is True
    assert ExactCommitProvenance.model_config.get("extra") == "forbid"


# --- N11: dirty tree, local mode (require_clean=False) ---------------------


def test_dirty_tree_local_mode_succeeds_and_reports_dirty(temp_repo: Path) -> None:
    from specify_cli.team_projection.provenance import capture_provenance

    (temp_repo / "kitty-specs").mkdir(exist_ok=True)
    (temp_repo / "kitty-specs" / "untracked.txt").write_text("x", encoding="utf-8")

    prov = capture_provenance(temp_repo, require_clean=False)

    assert prov.tree_clean is False
    # commit_sha is still HEAD, never a hash of the dirty content.
    assert prov.commit_sha == _git(temp_repo, "rev-parse", "HEAD").stdout.strip()


# --- N10: dirty tree, manifest mode (require_clean=True) -------------------


def test_dirty_tree_require_clean_raises(temp_repo: Path) -> None:
    from specify_cli.team_projection.provenance import (
        DirtyTreeError,
        capture_provenance,
    )

    (temp_repo / "kitty-specs").mkdir(exist_ok=True)
    (temp_repo / "kitty-specs" / "untracked.txt").write_text("x", encoding="utf-8")

    with pytest.raises(DirtyTreeError):
        capture_provenance(temp_repo, require_clean=True)


def test_clean_tree_require_clean_succeeds(temp_repo: Path) -> None:
    from specify_cli.team_projection.provenance import capture_provenance

    prov = capture_provenance(temp_repo, require_clean=True)
    assert prov.tree_clean is True


# --- N12: git operation in progress (MERGE_HEAD marker) ---------------------


def test_merge_head_marker_reports_dirty(temp_repo: Path) -> None:
    """A MERGE_HEAD marker always shows up as porcelain output too — no
    special-case handling is needed in capture_provenance (§4 N12)."""
    from specify_cli.team_projection.provenance import capture_provenance

    (temp_repo / "kitty-specs").mkdir(exist_ok=True)
    (temp_repo / "kitty-specs" / "conflicted.txt").write_text("<<<<<<<\n", encoding="utf-8")
    (temp_repo / ".git" / "MERGE_HEAD").write_text(
        _git(temp_repo, "rev-parse", "HEAD").stdout, encoding="utf-8"
    )

    prov = capture_provenance(temp_repo, require_clean=False)
    assert prov.tree_clean is False


# --- N13: exact-commit truthfulness across two commits ----------------------


def test_commit_sha_changes_across_commits(temp_repo: Path) -> None:
    from specify_cli.team_projection.provenance import capture_provenance

    prov_a = capture_provenance(temp_repo, require_clean=True)

    (temp_repo / "kitty-specs").mkdir(exist_ok=True)
    (temp_repo / "kitty-specs" / "new.txt").write_text("hello", encoding="utf-8")
    _git(temp_repo, "add", "-A")
    _git(temp_repo, "commit", "-m", "second commit")

    prov_b = capture_provenance(temp_repo, require_clean=True)

    assert prov_a.commit_sha != prov_b.commit_sha


# --- Fault handling: git missing / timeout degrade to tree_clean=False -----


def test_git_not_available_degrades_to_dirty(monkeypatch, temp_repo: Path) -> None:
    from specify_cli.team_projection import provenance as provenance_mod

    real_run = subprocess.run

    def _fake_run(cmd, *args, **kwargs):  # noqa: ANN001
        if cmd and cmd[0] == "git" and "status" in cmd:
            raise FileNotFoundError("git not found")
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(provenance_mod.subprocess, "run", _fake_run)

    prov = provenance_mod.capture_provenance(temp_repo, require_clean=False)
    assert prov.tree_clean is False


def test_git_not_available_with_require_clean_raises(monkeypatch, temp_repo: Path) -> None:
    from specify_cli.team_projection import provenance as provenance_mod

    real_run = subprocess.run

    def _fake_run(cmd, *args, **kwargs):  # noqa: ANN001
        if cmd and cmd[0] == "git" and "status" in cmd:
            raise FileNotFoundError("git not found")
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(provenance_mod.subprocess, "run", _fake_run)

    with pytest.raises(provenance_mod.DirtyTreeError):
        provenance_mod.capture_provenance(temp_repo, require_clean=True)
