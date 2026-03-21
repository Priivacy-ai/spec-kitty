"""Tests for ManagedSkillManifest dataclass and persistence."""

from __future__ import annotations

from pathlib import Path

from specify_cli.skills.manifest import (
    MANIFEST_FILENAME,
    ManagedFileEntry,
    ManagedSkillManifest,
    clear_manifest,
    compute_content_hash,
    load_manifest,
    save_manifest,
)


def _make_entry(
    skill_name: str = "test-skill",
    source_file: str = "SKILL.md",
    installed_path: str = ".claude/skills/test-skill/SKILL.md",
    installation_class: str = "shared-root-capable",
    agent_key: str = "claude",
    content_hash: str = "sha256:abc123",
    installed_at: str = "2026-01-01T00:00:00+00:00",
) -> ManagedFileEntry:
    return ManagedFileEntry(
        skill_name=skill_name,
        source_file=source_file,
        installed_path=installed_path,
        installation_class=installation_class,
        agent_key=agent_key,
        content_hash=content_hash,
        installed_at=installed_at,
    )


def test_create_manifest_with_defaults() -> None:
    m = ManagedSkillManifest()
    assert m.version == 1
    assert m.created_at == ""
    assert m.updated_at == ""
    assert m.spec_kitty_version == ""
    assert m.entries == []


def test_add_entry() -> None:
    m = ManagedSkillManifest()
    entry = _make_entry()
    m.add_entry(entry)
    assert len(m.entries) == 1
    assert m.entries[0] is entry


def test_add_entry_replaces_duplicate_path_and_agent() -> None:
    m = ManagedSkillManifest()
    entry1 = _make_entry(content_hash="sha256:old")
    entry2 = _make_entry(content_hash="sha256:new")
    m.add_entry(entry1)
    m.add_entry(entry2)
    assert len(m.entries) == 1
    assert m.entries[0].content_hash == "sha256:new"


def test_add_entry_preserves_shared_root_entries() -> None:
    """Shared-root agents share installed_path but have different agent_keys."""
    m = ManagedSkillManifest()
    shared_path = ".agents/skills/test-skill/SKILL.md"
    entry_copilot = _make_entry(installed_path=shared_path, agent_key="copilot")
    entry_codex = _make_entry(installed_path=shared_path, agent_key="codex")
    m.add_entry(entry_copilot)
    m.add_entry(entry_codex)
    assert len(m.entries) == 2
    agents = {e.agent_key for e in m.entries}
    assert agents == {"copilot", "codex"}


def test_remove_entries_for_agent() -> None:
    m = ManagedSkillManifest()
    e1 = _make_entry(agent_key="claude", installed_path="a")
    e2 = _make_entry(agent_key="codex", installed_path="b")
    e3 = _make_entry(agent_key="claude", installed_path="c")
    m.add_entry(e1)
    m.add_entry(e2)
    m.add_entry(e3)

    removed = m.remove_entries_for_agent("claude")
    assert len(removed) == 2
    assert all(e.agent_key == "claude" for e in removed)
    assert len(m.entries) == 1
    assert m.entries[0].agent_key == "codex"


def test_find_by_skill() -> None:
    m = ManagedSkillManifest()
    e1 = _make_entry(skill_name="alpha", installed_path="a")
    e2 = _make_entry(skill_name="beta", installed_path="b")
    e3 = _make_entry(skill_name="alpha", installed_path="c")
    m.add_entry(e1)
    m.add_entry(e2)
    m.add_entry(e3)

    results = m.find_by_skill("alpha")
    assert len(results) == 2
    assert all(e.skill_name == "alpha" for e in results)


def test_find_by_installed_path() -> None:
    m = ManagedSkillManifest()
    e1 = _make_entry(installed_path="path/a")
    m.add_entry(e1)

    assert m.find_by_installed_path("path/a") is e1
    assert m.find_by_installed_path("path/missing") is None


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    original = ManagedSkillManifest(
        version=1,
        created_at="2026-01-01T00:00:00+00:00",
        spec_kitty_version="2.0.11",
        entries=[
            _make_entry(skill_name="s1", installed_path="p1"),
            _make_entry(skill_name="s2", installed_path="p2", agent_key="codex"),
        ],
    )

    save_manifest(original, tmp_path)
    loaded = load_manifest(tmp_path)

    assert loaded is not None
    assert loaded.version == original.version
    assert loaded.created_at == original.created_at
    assert loaded.spec_kitty_version == original.spec_kitty_version
    assert len(loaded.entries) == 2
    assert loaded.entries[0].skill_name == "s1"
    assert loaded.entries[1].agent_key == "codex"
    # updated_at should have been set by save_manifest
    assert loaded.updated_at != ""


def test_load_missing_file_returns_none(tmp_path: Path) -> None:
    result = load_manifest(tmp_path)
    assert result is None


def test_load_malformed_json_returns_none(tmp_path: Path) -> None:
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / MANIFEST_FILENAME).write_text("NOT VALID JSON {{{", encoding="utf-8")
    result = load_manifest(tmp_path)
    assert result is None


def test_clear_manifest_removes_file(tmp_path: Path) -> None:
    m = ManagedSkillManifest()
    m.add_entry(_make_entry())
    save_manifest(m, tmp_path)

    manifest_file = tmp_path / ".kittify" / MANIFEST_FILENAME
    assert manifest_file.exists()

    clear_manifest(tmp_path)
    assert not manifest_file.exists()


def test_compute_content_hash(tmp_path: Path) -> None:
    test_file = tmp_path / "hello.txt"
    test_file.write_text("hello world", encoding="utf-8")

    result = compute_content_hash(test_file)
    assert result.startswith("sha256:")
    # sha256 hex digest is 64 chars
    hex_part = result.split(":", 1)[1]
    assert len(hex_part) == 64


def test_compute_content_hash_deterministic(tmp_path: Path) -> None:
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    content = "identical content\n"
    f1.write_text(content, encoding="utf-8")
    f2.write_text(content, encoding="utf-8")

    assert compute_content_hash(f1) == compute_content_hash(f2)
