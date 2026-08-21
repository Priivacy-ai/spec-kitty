"""Tests for specify_cli.team_projection.write (D1-T1).

Covers §4 N16 (partial-write atomicity — manifest written last, so an
incomplete run never leaves a manifest claiming files it did not write) and
the end-to-end file layout of §3.5.
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


def _commit_all(repo: Path, message: str = "fixture") -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)


def test_write_team_projection_layout_public_disabled(temp_repo: Path) -> None:
    from specify_cli.team_projection.write import write_team_projection

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)

    manifest = write_team_projection(temp_repo)

    derived = temp_repo / ".kittify" / "derived"
    assert (derived / "team-index.json").exists()
    assert (derived / slug / "team-snapshot.json").exists()
    assert (derived / "attestation-manifest.json").exists()
    assert not (derived / "public").exists()
    assert not (derived / slug / "public").exists()

    on_disk_manifest = json.loads((derived / "attestation-manifest.json").read_text())
    assert on_disk_manifest["schema"] == "attestation_manifest/v1"
    assert on_disk_manifest == manifest.model_dump(mode="json", by_alias=True)


def test_write_team_projection_layout_public_enabled(temp_repo: Path) -> None:
    from specify_cli.team_projection.write import write_team_projection

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    kittify = temp_repo / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text(
        "public_projection:\n  enabled: true\n", encoding="utf-8"
    )
    _commit_all(temp_repo)

    write_team_projection(temp_repo)

    derived = temp_repo / ".kittify" / "derived"
    assert (derived / "public" / "index.json").exists()
    assert (derived / slug / "public" / "mission.json").exists()


def test_write_team_projection_dirty_tree_writes_nothing(temp_repo: Path) -> None:
    from specify_cli.team_projection.provenance import DirtyTreeError
    from specify_cli.team_projection.write import write_team_projection

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)
    (temp_repo / "kitty-specs" / "untracked.txt").write_text("x", encoding="utf-8")

    with pytest.raises(DirtyTreeError):
        write_team_projection(temp_repo)

    derived = temp_repo / ".kittify" / "derived"
    assert not derived.exists() or not any(derived.rglob("*"))


# --- N16: partial-write atomicity — manifest is written last -----------------


def test_manifest_absent_when_run_fails_before_completion(
    temp_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from specify_cli.team_projection import write as write_mod

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)

    class _InjectedFailure(RuntimeError):
        pass

    real_build_team_mission_snapshot = write_mod.build_team_mission_snapshot

    def _fail_after_index(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise _InjectedFailure("simulated failure after team-index.json write")

    monkeypatch.setattr(write_mod, "build_team_mission_snapshot", _fail_after_index)

    with pytest.raises(_InjectedFailure):
        write_mod.write_team_projection(temp_repo)

    derived = temp_repo / ".kittify" / "derived"
    manifest_path = derived / "attestation-manifest.json"
    assert not manifest_path.exists()

    # Retry (fault removed) completes and leaves every file consistent with
    # the same commit_sha.
    monkeypatch.setattr(write_mod, "build_team_mission_snapshot", real_build_team_mission_snapshot)
    manifest = write_mod.write_team_projection(temp_repo)

    assert manifest_path.exists()
    on_disk_index = json.loads((derived / "team-index.json").read_text())
    on_disk_snapshot = json.loads((derived / slug / "team-snapshot.json").read_text())
    assert (
        on_disk_index["provenance"]["commit_sha"]
        == on_disk_snapshot["provenance"]["commit_sha"]
        == manifest.provenance.commit_sha
    )


# --- Renata review (D1-T1 APPROVE w/ findings), MEDIUM: mission_slug path-
# segment guard reachable end-to-end through write_team_projection. ----------


def test_write_team_projection_rejects_hostile_mission_dir_name(temp_repo: Path) -> None:
    """A mission directory whose name (mission_slug) fails the safe-segment
    grammar (here: non-ASCII) must be rejected cleanly by the publish path
    instead of being silently joined into ``.kittify/derived/<slug>/...``.
    No attestation manifest is written for a run that fails partway."""
    from specify_cli.team_projection.write import write_team_projection

    write_wp(temp_repo, "café-mission", "planned", "WP01")
    _commit_all(temp_repo)

    with pytest.raises(ValueError, match="safe path segment"):
        write_team_projection(temp_repo)

    derived = temp_repo / ".kittify" / "derived"
    manifest_path = derived / "attestation-manifest.json"
    assert not manifest_path.exists()


def test_write_uses_atomic_write_json_pattern(temp_repo: Path) -> None:
    """No stray ``.tmp`` file survives a successful run (temp-file +
    os.replace, reusing ``status/views.py``'s existing primitive)."""
    from specify_cli.team_projection.write import write_team_projection

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)

    write_team_projection(temp_repo)

    derived = temp_repo / ".kittify" / "derived"
    tmp_files = list(derived.rglob("*.tmp"))
    assert tmp_files == []
