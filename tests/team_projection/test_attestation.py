"""Tests for specify_cli.team_projection.attestation (D1-T1).

Covers §4 N10 (dirty tree, manifest mode: pure builder, no I/O either way),
N14 (referential closure), N15 (independently re-derived digest), and N17
(no network import).
"""

from __future__ import annotations

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


def test_build_attestation_manifest_shape_public_disabled(temp_repo: Path) -> None:
    from specify_cli.team_projection.attestation import build_attestation_manifest

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)

    manifest = build_attestation_manifest(temp_repo)

    assert manifest.schema_ == "attestation_manifest/v1"
    assert manifest.provenance.tree_clean is True
    kinds = {(e.artifact, e.mission_slug) for e in manifest.entries}
    assert ("team_index", None) in kinds
    assert ("team_mission_snapshot", slug) in kinds
    assert ("public_index", None) in kinds
    assert ("public_mission_snapshot", slug) in kinds

    public_rows = [e for e in manifest.entries if e.artifact.startswith("public")]
    assert public_rows and all(row.present is False for row in public_rows)
    assert all(row.content_sha256 is None for row in public_rows)

    team_rows = [e for e in manifest.entries if not e.artifact.startswith("public")]
    assert all(row.present is True for row in team_rows)
    assert all(row.content_sha256 is not None for row in team_rows)


def test_build_attestation_manifest_public_enabled(temp_repo: Path) -> None:
    from specify_cli.team_projection.attestation import build_attestation_manifest

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    kittify = temp_repo / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text(
        "public_projection:\n  enabled: true\n", encoding="utf-8"
    )
    _commit_all(temp_repo)

    manifest = build_attestation_manifest(temp_repo)

    public_rows = [e for e in manifest.entries if e.artifact.startswith("public")]
    assert public_rows and all(row.present is True for row in public_rows)
    assert all(row.content_sha256 is not None for row in public_rows)


# --- N10: dirty tree, manifest mode (pure builder, no I/O either way) --------


def test_dirty_tree_raises_and_writes_nothing(tmp_path: Path, temp_repo: Path) -> None:
    from specify_cli.team_projection.attestation import build_attestation_manifest
    from specify_cli.team_projection.provenance import DirtyTreeError

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)
    (temp_repo / "kitty-specs" / "untracked.txt").write_text("x", encoding="utf-8")

    before = sorted((temp_repo / ".kittify").rglob("*")) if (temp_repo / ".kittify").exists() else []

    with pytest.raises(DirtyTreeError):
        build_attestation_manifest(temp_repo)

    after = sorted((temp_repo / ".kittify").rglob("*")) if (temp_repo / ".kittify").exists() else []
    assert before == after


# --- N14: referential closure -------------------------------------------------


def test_manifest_never_references_unknown_mission(temp_repo: Path) -> None:
    from specify_cli.dashboard.scanner import build_mission_registry
    from specify_cli.team_projection.attestation import build_attestation_manifest

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)

    manifest = build_attestation_manifest(temp_repo)
    registry = build_mission_registry(temp_repo)
    known_slugs = {record["mission_slug"] for record in registry.values()}

    for entry in manifest.entries:
        if entry.mission_slug is not None:
            assert entry.mission_slug in known_slugs


# --- N15: digest matches file, independently re-derived ---------------------


def test_manifest_digest_matches_independent_hash(temp_repo: Path) -> None:
    import hashlib
    import json

    from specify_cli.team_projection.attestation import build_attestation_manifest
    from specify_cli.team_projection.mission_view import build_team_mission_snapshot
    from specify_cli.team_projection.team_index import build_team_index

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)
    feature_dir = temp_repo / "kitty-specs" / slug

    manifest = build_attestation_manifest(temp_repo)

    team_index = build_team_index(temp_repo, require_clean=True)
    expected_index_digest = "sha256:" + hashlib.sha256(  # noqa: TID251
        json.dumps(
            [m.model_dump(mode="json") for m in team_index.missions],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    index_row = next(e for e in manifest.entries if e.artifact == "team_index")
    assert index_row.content_sha256 == team_index.content_sha256 == expected_index_digest

    team_snapshot = build_team_mission_snapshot(feature_dir, temp_repo, require_clean=True)
    expected_snapshot_digest = "sha256:" + hashlib.sha256(  # noqa: TID251
        json.dumps(team_snapshot.mission, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    snapshot_row = next(
        e for e in manifest.entries if e.artifact == "team_mission_snapshot" and e.mission_slug == slug
    )
    assert snapshot_row.content_sha256 == expected_snapshot_digest


# --- N17: no network import ---------------------------------------------------


def test_no_network_import(temp_repo: Path) -> None:
    import subprocess as sp
    import sys

    result = sp.run(
        [
            sys.executable,
            "-c",
            "import sys\n"
            "class _Blocked(Exception):\n"
            "    pass\n"
            "import socket\n"
            "def _no_connect(*a, **k):\n"
            "    raise _Blocked('network blocked')\n"
            "socket.socket.connect = _no_connect\n"
            "import specify_cli.team_projection\n"
            "import specify_cli.team_projection.provenance\n"
            "import specify_cli.team_projection.mission_view\n"
            "import specify_cli.team_projection.team_index\n"
            "import specify_cli.team_projection.public_view\n"
            "import specify_cli.team_projection.attestation\n"
            "import specify_cli.team_projection.write\n"
            "print('OK')\n",
        ],
        cwd=temp_repo,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


# --- C2: no dossier / saas_sync_config import --------------------------------


def test_no_dossier_or_saas_sync_config_import() -> None:
    import ast
    from pathlib import Path as _Path

    package_dir = (
        _Path(__file__).resolve().parents[2] / "src" / "specify_cli" / "team_projection"
    )
    forbidden_modules = ("specify_cli.dossier", "specify_cli.core.saas_sync_config")

    for py_file in package_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for forbidden in forbidden_modules:
                    assert not node.module.startswith(forbidden), (
                        f"{py_file} imports {node.module}"
                    )
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_modules:
                        assert not alias.name.startswith(forbidden), (
                            f"{py_file} imports {alias.name}"
                        )
