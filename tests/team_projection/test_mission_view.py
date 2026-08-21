"""Tests for specify_cli.team_projection.mission_view (D1-T1).

Covers §4 N1 (byte determinism), N7/N8 (no orchestration-state laundering /
closed WP allowlist), and C1 (reuse of status.reducer.materialize_snapshot,
not reimplementation).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tests.utils import write_wp

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )


def _commit_all(repo: Path, message: str = "wp fixture") -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)


def test_build_team_mission_snapshot_shape(temp_repo: Path) -> None:
    from specify_cli.team_projection.mission_view import build_team_mission_snapshot

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)

    feature_dir = temp_repo / "kitty-specs" / slug
    snap = build_team_mission_snapshot(feature_dir, temp_repo, require_clean=True)

    assert snap.schema_ == "team_mission_snapshot/v1"
    assert snap.provenance.tree_clean is True
    assert snap.content_sha256.startswith("sha256:")
    assert len(snap.content_sha256) == len("sha256:") + 64
    assert "WP01" in snap.mission["work_packages"]


def test_content_sha256_covers_mission_body_only(temp_repo: Path) -> None:
    """The digest must be stable under an envelope-only schema bump — i.e. it
    hashes ``mission``, never ``provenance`` (§3.3)."""
    import hashlib

    from specify_cli.team_projection.mission_view import build_team_mission_snapshot

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)
    feature_dir = temp_repo / "kitty-specs" / slug

    snap = build_team_mission_snapshot(feature_dir, temp_repo, require_clean=True)

    canonical = json.dumps(snap.mission, sort_keys=True, separators=(",", ":"))
    expected = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert snap.content_sha256 == expected


# --- N1: byte determinism ----------------------------------------------------


def test_byte_determinism_two_builds_same_commit(temp_repo: Path) -> None:
    from specify_cli.team_projection.mission_view import build_team_mission_snapshot

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)
    feature_dir = temp_repo / "kitty-specs" / slug

    snap_a = build_team_mission_snapshot(feature_dir, temp_repo, require_clean=True)
    snap_b = build_team_mission_snapshot(feature_dir, temp_repo, require_clean=True)

    json_a = snap_a.model_dump_json(by_alias=True)
    json_b = snap_b.model_dump_json(by_alias=True)
    assert json_a == json_b


# --- N7: no orchestration-state laundering (shell_pid / shell_pid_created_at) ----


def test_shell_pid_present_locally_absent_from_team_snapshot(temp_repo: Path) -> None:
    from specify_cli.status.reducer import materialize
    from specify_cli.team_projection.mission_view import build_team_mission_snapshot

    slug = "001-demo-feature"
    # write_wp seeds shell_pid=1234 via an InnerStateChanged annotation.
    write_wp(temp_repo, slug, "planned", "WP01", shell_pid="4242")
    _commit_all(temp_repo)
    feature_dir = temp_repo / "kitty-specs" / slug

    local_snapshot = materialize(feature_dir)
    assert local_snapshot.work_packages["WP01"].get("shell_pid") == 4242

    snap = build_team_mission_snapshot(feature_dir, temp_repo, require_clean=True)
    rendered = snap.model_dump_json(by_alias=True)
    assert "shell_pid" not in rendered
    assert "notes" not in rendered
    assert "shell_pid" not in snap.mission["work_packages"]["WP01"]


# --- N8: closed WP filter raises on an unrecognized key ----------------------


def test_unknown_wp_state_key_raises(temp_repo: Path, monkeypatch) -> None:
    from specify_cli.status import reducer as reducer_mod
    from specify_cli.team_projection import mission_view as mission_view_mod

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)
    feature_dir = temp_repo / "kitty-specs" / slug

    real_materialize_snapshot = reducer_mod.materialize_snapshot

    def _poisoned(feature_dir_arg: Path):  # noqa: ANN001, ANN202
        snapshot = real_materialize_snapshot(feature_dir_arg)
        snapshot.work_packages["WP01"]["totally_new_future_slot"] = "surprise"
        return snapshot

    monkeypatch.setattr(mission_view_mod, "materialize_snapshot", _poisoned)

    with pytest.raises(mission_view_mod.UnknownWPStateFieldError):
        mission_view_mod.build_team_mission_snapshot(
            feature_dir, temp_repo, require_clean=True
        )


# --- C1: reuse, not reimplementation -----------------------------------------


def test_reuses_materialize_snapshot_exactly_once(temp_repo: Path, monkeypatch) -> None:
    from specify_cli.status import reducer as reducer_mod
    from specify_cli.team_projection import mission_view as mission_view_mod

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)
    feature_dir = temp_repo / "kitty-specs" / slug

    calls = {"n": 0}
    real_materialize_snapshot = reducer_mod.materialize_snapshot

    def _spy(feature_dir_arg: Path):  # noqa: ANN001, ANN202
        calls["n"] += 1
        return real_materialize_snapshot(feature_dir_arg)

    monkeypatch.setattr(mission_view_mod, "materialize_snapshot", _spy)

    mission_view_mod.build_team_mission_snapshot(feature_dir, temp_repo, require_clean=True)

    assert calls["n"] == 1


# --- Local/dashboard mode (require_clean=False default) ---------------------


def test_local_mode_default_require_clean_false(temp_repo: Path) -> None:
    from specify_cli.team_projection.mission_view import build_team_mission_snapshot

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)
    feature_dir = temp_repo / "kitty-specs" / slug

    (feature_dir / "untracked.txt").write_text("x", encoding="utf-8")

    snap = build_team_mission_snapshot(feature_dir, temp_repo)
    assert snap.provenance.tree_clean is False
