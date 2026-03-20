"""Tests for skills manifest CRUD operations (WP03, T017)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from specify_cli.skills.manifest import (
    MANIFEST_PATH,
    ManagedFile,
    SkillsManifest,
    compute_file_hash,
    load_manifest,
    write_manifest,
)


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------


def test_manifest_round_trip(tmp_path: Path) -> None:
    """write_manifest → load_manifest produces identical data."""
    manifest = SkillsManifest(
        spec_kitty_version="2.1.0",
        created_at="2026-03-20T16:00:00Z",
        updated_at="2026-03-20T16:00:00Z",
        skills_mode="auto",
        selected_agents=["claude", "codex"],
        installed_skill_roots=[".agents/skills/", ".claude/skills/"],
        managed_files=[
            ManagedFile(
                path=".agents/skills/.gitkeep",
                sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                file_type="skill_root_marker",
            ),
        ],
    )

    write_manifest(tmp_path, manifest)
    loaded = load_manifest(tmp_path)

    assert loaded is not None
    assert loaded.spec_kitty_version == manifest.spec_kitty_version
    assert loaded.created_at == manifest.created_at
    assert loaded.updated_at == manifest.updated_at
    assert loaded.skills_mode == manifest.skills_mode
    assert loaded.selected_agents == manifest.selected_agents
    assert loaded.installed_skill_roots == manifest.installed_skill_roots
    assert len(loaded.managed_files) == 1
    assert loaded.managed_files[0].path == ".agents/skills/.gitkeep"
    assert loaded.managed_files[0].sha256 == manifest.managed_files[0].sha256
    assert loaded.managed_files[0].file_type == "skill_root_marker"


def test_manifest_round_trip_empty_lists(tmp_path: Path) -> None:
    """Round-trip with no agents, no roots, no managed files."""
    manifest = SkillsManifest(
        spec_kitty_version="2.1.0",
        created_at="2026-03-20T16:00:00Z",
        updated_at="2026-03-20T16:00:00Z",
        skills_mode="manual",
    )

    write_manifest(tmp_path, manifest)
    loaded = load_manifest(tmp_path)

    assert loaded is not None
    assert loaded.selected_agents == []
    assert loaded.installed_skill_roots == []
    assert loaded.managed_files == []


def test_manifest_round_trip_multiple_managed_files(tmp_path: Path) -> None:
    """Round-trip preserves ordering of multiple managed files."""
    files = [
        ManagedFile(path=".agents/skills/.gitkeep", sha256="aaa", file_type="skill_root_marker"),
        ManagedFile(path=".claude/commands/spec-kitty.specify.md", sha256="bbb", file_type="wrapper"),
        ManagedFile(path=".codex/prompts/spec-kitty.specify.prompt.md", sha256="ccc", file_type="wrapper"),
    ]
    manifest = SkillsManifest(
        spec_kitty_version="2.1.0",
        created_at="t0",
        updated_at="t1",
        skills_mode="auto",
        managed_files=files,
    )

    write_manifest(tmp_path, manifest)
    loaded = load_manifest(tmp_path)

    assert loaded is not None
    assert len(loaded.managed_files) == 3
    for original, restored in zip(files, loaded.managed_files, strict=True):
        assert original.path == restored.path
        assert original.sha256 == restored.sha256
        assert original.file_type == restored.file_type


# ---------------------------------------------------------------------------
# load_manifest error paths
# ---------------------------------------------------------------------------


def test_load_missing_returns_none(tmp_path: Path) -> None:
    """Missing manifest file returns None."""
    assert load_manifest(tmp_path) is None


def test_load_corrupt_returns_none(tmp_path: Path) -> None:
    """Corrupt YAML returns None."""
    manifest_path = tmp_path / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text("{{invalid yaml", encoding="utf-8")
    assert load_manifest(tmp_path) is None


def test_load_empty_returns_none(tmp_path: Path) -> None:
    """Empty manifest file returns None."""
    manifest_path = tmp_path / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text("", encoding="utf-8")
    assert load_manifest(tmp_path) is None


def test_load_whitespace_only_returns_none(tmp_path: Path) -> None:
    """Whitespace-only manifest file returns None."""
    manifest_path = tmp_path / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text("   \n\n  ", encoding="utf-8")
    assert load_manifest(tmp_path) is None


def test_load_missing_required_field_returns_none(tmp_path: Path) -> None:
    """YAML with missing required field returns None."""
    manifest_path = tmp_path / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True)
    # Missing skills_mode and updated_at
    manifest_path.write_text(
        "spec_kitty_version: '1.0'\ncreated_at: '2026-01-01'\n",
        encoding="utf-8",
    )
    assert load_manifest(tmp_path) is None


def test_load_yaml_list_root_returns_none(tmp_path: Path) -> None:
    """YAML whose root is a list (not a mapping) returns None."""
    manifest_path = tmp_path / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text("- item1\n- item2\n", encoding="utf-8")
    assert load_manifest(tmp_path) is None


def test_load_managed_files_missing_key_returns_none(tmp_path: Path) -> None:
    """Managed file entry missing a required key returns None."""
    manifest_path = tmp_path / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        (
            "spec_kitty_version: '1.0'\n"
            "created_at: '2026-01-01'\n"
            "updated_at: '2026-01-01'\n"
            "skills_mode: auto\n"
            "selected_agents: []\n"
            "installed_skill_roots: []\n"
            "managed_files:\n"
            "  - path: foo\n"
            "    sha256: abc\n"
            # missing file_type
        ),
        encoding="utf-8",
    )
    assert load_manifest(tmp_path) is None


def test_load_wrong_type_version_returns_none(tmp_path: Path) -> None:
    """spec_kitty_version as list instead of string returns None."""
    manifest_path = tmp_path / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        (
            "spec_kitty_version: [2.1.0]\n"
            "created_at: '2026-01-01'\n"
            "updated_at: '2026-01-01'\n"
            "skills_mode: auto\n"
            "selected_agents: []\n"
            "installed_skill_roots: []\n"
            "managed_files: []\n"
        ),
        encoding="utf-8",
    )
    assert load_manifest(tmp_path) is None


def test_load_wrong_type_selected_agents_returns_none(tmp_path: Path) -> None:
    """selected_agents containing dicts instead of strings returns None."""
    manifest_path = tmp_path / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        (
            "spec_kitty_version: '2.1.0'\n"
            "created_at: '2026-01-01'\n"
            "updated_at: '2026-01-01'\n"
            "skills_mode: auto\n"
            "selected_agents:\n"
            "  - name: claude\n"
            "installed_skill_roots: []\n"
            "managed_files: []\n"
        ),
        encoding="utf-8",
    )
    assert load_manifest(tmp_path) is None


def test_load_wrong_type_managed_file_entry_returns_none(tmp_path: Path) -> None:
    """managed_files entry with non-string path returns None."""
    manifest_path = tmp_path / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        (
            "spec_kitty_version: '2.1.0'\n"
            "created_at: '2026-01-01'\n"
            "updated_at: '2026-01-01'\n"
            "skills_mode: auto\n"
            "selected_agents: []\n"
            "installed_skill_roots: []\n"
            "managed_files:\n"
            "  - path: 123\n"
            "    sha256: abc\n"
            "    file_type: wrapper\n"
        ),
        encoding="utf-8",
    )
    assert load_manifest(tmp_path) is None


def test_load_binary_garbage_returns_none(tmp_path: Path) -> None:
    """Manifest containing invalid UTF-8 bytes returns None (not UnicodeDecodeError)."""
    manifest_path = tmp_path / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_bytes(b"\x80\x81\x82")
    assert load_manifest(tmp_path) is None


def test_load_missing_selected_agents_returns_none(tmp_path: Path) -> None:
    """Manifest missing required 'selected_agents' field returns None."""
    manifest_path = tmp_path / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        (
            "spec_kitty_version: '1.0'\n"
            "created_at: '2026-01-01'\n"
            "updated_at: '2026-01-01'\n"
            "skills_mode: auto\n"
            # selected_agents missing
            "installed_skill_roots: []\n"
            "managed_files: []\n"
        ),
        encoding="utf-8",
    )
    assert load_manifest(tmp_path) is None


def test_load_missing_installed_skill_roots_returns_none(tmp_path: Path) -> None:
    """Manifest missing required 'installed_skill_roots' field returns None."""
    manifest_path = tmp_path / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        (
            "spec_kitty_version: '1.0'\n"
            "created_at: '2026-01-01'\n"
            "updated_at: '2026-01-01'\n"
            "skills_mode: auto\n"
            "selected_agents: []\n"
            # installed_skill_roots missing
            "managed_files: []\n"
        ),
        encoding="utf-8",
    )
    assert load_manifest(tmp_path) is None


def test_load_missing_managed_files_returns_none(tmp_path: Path) -> None:
    """Manifest missing required 'managed_files' field returns None."""
    manifest_path = tmp_path / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        (
            "spec_kitty_version: '1.0'\n"
            "created_at: '2026-01-01'\n"
            "updated_at: '2026-01-01'\n"
            "skills_mode: auto\n"
            "selected_agents: []\n"
            "installed_skill_roots: []\n"
            # managed_files missing
        ),
        encoding="utf-8",
    )
    assert load_manifest(tmp_path) is None


# ---------------------------------------------------------------------------
# write_manifest
# ---------------------------------------------------------------------------


def test_write_creates_parent_dir(tmp_path: Path) -> None:
    """write_manifest creates the parent directory tree when absent."""
    manifest = SkillsManifest(
        spec_kitty_version="2.1.0",
        created_at="",
        updated_at="",
        skills_mode="auto",
    )
    write_manifest(tmp_path, manifest)
    assert (tmp_path / MANIFEST_PATH).exists()


def test_write_overwrites_existing(tmp_path: Path) -> None:
    """write_manifest overwrites a pre-existing manifest file."""
    m1 = SkillsManifest(
        spec_kitty_version="1.0.0",
        created_at="t0",
        updated_at="t0",
        skills_mode="auto",
    )
    write_manifest(tmp_path, m1)

    m2 = SkillsManifest(
        spec_kitty_version="2.0.0",
        created_at="t0",
        updated_at="t1",
        skills_mode="manual",
    )
    write_manifest(tmp_path, m2)

    loaded = load_manifest(tmp_path)
    assert loaded is not None
    assert loaded.spec_kitty_version == "2.0.0"
    assert loaded.skills_mode == "manual"


# ---------------------------------------------------------------------------
# compute_file_hash
# ---------------------------------------------------------------------------


def test_compute_file_hash(tmp_path: Path) -> None:
    """compute_file_hash returns correct SHA-256 for known content."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world", encoding="utf-8")
    expected = hashlib.sha256(b"hello world").hexdigest()
    assert compute_file_hash(test_file) == expected


def test_compute_file_hash_empty(tmp_path: Path) -> None:
    """compute_file_hash returns correct SHA-256 for an empty file."""
    test_file = tmp_path / "empty.txt"
    test_file.write_bytes(b"")
    expected = hashlib.sha256(b"").hexdigest()
    assert compute_file_hash(test_file) == expected


def test_compute_file_hash_binary(tmp_path: Path) -> None:
    """compute_file_hash works correctly with binary content."""
    test_file = tmp_path / "binary.bin"
    content = bytes(range(256))
    test_file.write_bytes(content)
    expected = hashlib.sha256(content).hexdigest()
    assert compute_file_hash(test_file) == expected


def test_compute_file_hash_large(tmp_path: Path) -> None:
    """compute_file_hash handles files larger than the 8192-byte chunk size."""
    test_file = tmp_path / "large.txt"
    content = b"x" * 20000  # > 2 chunks
    test_file.write_bytes(content)
    expected = hashlib.sha256(content).hexdigest()
    assert compute_file_hash(test_file) == expected


# ---------------------------------------------------------------------------
# MANIFEST_PATH constant
# ---------------------------------------------------------------------------


def test_manifest_path_constant() -> None:
    """MANIFEST_PATH matches the documented location."""
    assert MANIFEST_PATH == ".kittify/agent-surfaces/skills-manifest.yaml"
