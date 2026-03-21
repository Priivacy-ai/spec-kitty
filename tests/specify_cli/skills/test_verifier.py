"""Tests for skill verification and repair."""

from __future__ import annotations

from pathlib import Path

from specify_cli.skills.manifest import (
    ManagedFileEntry,
    ManagedSkillManifest,
    compute_content_hash,
    load_manifest,
    save_manifest,
)
from specify_cli.skills.registry import SkillRegistry
from specify_cli.skills.verifier import VerifyResult, repair_skills, verify_installed_skills


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


def _setup_manifest_and_file(
    tmp_path: Path,
    installed_path: str,
    content: str,
    skill_name: str = "test-skill",
    source_file: str = "SKILL.md",
) -> ManagedFileEntry:
    """Helper: create a file on disk, compute its hash, save a manifest entry."""
    full = tmp_path / installed_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    h = compute_content_hash(full)
    entry = _make_entry(
        skill_name=skill_name,
        source_file=source_file,
        installed_path=installed_path,
        content_hash=h,
    )
    return entry


def _create_registry(tmp_path: Path, skill_name: str, files: dict[str, str]) -> SkillRegistry:
    """Helper: create a fake registry with a skill containing given files."""
    registry_root = tmp_path / "_registry"
    skill_dir = registry_root / skill_name
    for rel_path, content in files.items():
        fp = skill_dir / rel_path
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")
    return SkillRegistry(registry_root)


# ── verify_installed_skills ──────────────────────────────────────────


def test_verify_no_manifest_returns_ok(tmp_path: Path) -> None:
    """No manifest file → ok=True, no issues."""
    result = verify_installed_skills(tmp_path)
    assert result.ok is True
    assert result.missing == []
    assert result.drifted == []
    assert result.errors == []
    assert result.total_issues == 0


def test_verify_all_files_present_and_matching(tmp_path: Path) -> None:
    """All manifest entries match on disk → ok=True."""
    entry = _setup_manifest_and_file(
        tmp_path,
        installed_path=".claude/skills/test-skill/SKILL.md",
        content="# Test Skill\nHello world.\n",
    )
    manifest = ManagedSkillManifest(entries=[entry])
    save_manifest(manifest, tmp_path)

    result = verify_installed_skills(tmp_path)
    assert result.ok is True
    assert result.missing == []
    assert result.drifted == []
    assert result.total_issues == 0


def test_verify_detects_missing_file(tmp_path: Path) -> None:
    """File referenced in manifest does not exist on disk → missing."""
    entry = _make_entry(
        installed_path=".claude/skills/test-skill/SKILL.md",
        content_hash="sha256:deadbeef",
    )
    manifest = ManagedSkillManifest(entries=[entry])
    save_manifest(manifest, tmp_path)

    result = verify_installed_skills(tmp_path)
    assert result.ok is False
    assert len(result.missing) == 1
    assert result.missing[0].installed_path == ".claude/skills/test-skill/SKILL.md"
    assert result.drifted == []


def test_verify_detects_drifted_file(tmp_path: Path) -> None:
    """File exists but content hash differs → drifted."""
    entry = _setup_manifest_and_file(
        tmp_path,
        installed_path=".claude/skills/test-skill/SKILL.md",
        content="original content",
    )
    manifest = ManagedSkillManifest(entries=[entry])
    save_manifest(manifest, tmp_path)

    # Modify the file after manifest was saved
    modified = tmp_path / ".claude/skills/test-skill/SKILL.md"
    modified.write_text("modified content", encoding="utf-8")

    result = verify_installed_skills(tmp_path)
    assert result.ok is False
    assert result.missing == []
    assert len(result.drifted) == 1
    drifted_entry, actual_hash = result.drifted[0]
    assert drifted_entry.installed_path == ".claude/skills/test-skill/SKILL.md"
    assert actual_hash == compute_content_hash(modified)
    assert actual_hash != entry.content_hash


def test_verify_multiple_issues(tmp_path: Path) -> None:
    """Mix of missing and drifted entries."""
    # Entry 1: will be present and matching
    good_entry = _setup_manifest_and_file(
        tmp_path,
        installed_path=".claude/skills/skill-a/SKILL.md",
        content="good content",
        skill_name="skill-a",
    )
    # Entry 2: will be missing
    missing_entry = _make_entry(
        skill_name="skill-b",
        installed_path=".claude/skills/skill-b/SKILL.md",
        content_hash="sha256:missing",
    )
    # Entry 3: will be drifted
    drifted_entry = _setup_manifest_and_file(
        tmp_path,
        installed_path=".claude/skills/skill-c/SKILL.md",
        content="original",
        skill_name="skill-c",
    )

    manifest = ManagedSkillManifest(entries=[good_entry, missing_entry, drifted_entry])
    save_manifest(manifest, tmp_path)

    # Drift entry 3
    (tmp_path / ".claude/skills/skill-c/SKILL.md").write_text("changed", encoding="utf-8")

    result = verify_installed_skills(tmp_path)
    assert result.ok is False
    assert len(result.missing) == 1
    assert result.missing[0].skill_name == "skill-b"
    assert len(result.drifted) == 1
    assert result.drifted[0][0].skill_name == "skill-c"
    assert result.total_issues == 2


# ── repair_skills ────────────────────────────────────────────────────


def test_repair_restores_missing_file(tmp_path: Path) -> None:
    """Repair copies a missing file from the registry."""
    skill_content = "# Test Skill\nCanonical content.\n"
    registry = _create_registry(tmp_path, "test-skill", {"SKILL.md": skill_content})

    # Create manifest entry pointing to a file that doesn't exist
    entry = _make_entry(
        skill_name="test-skill",
        source_file="SKILL.md",
        installed_path=".claude/skills/test-skill/SKILL.md",
        content_hash="sha256:stale",
    )
    manifest = ManagedSkillManifest(entries=[entry])
    save_manifest(manifest, tmp_path)

    verify_result = VerifyResult(ok=False, missing=[entry])

    repaired, failed = repair_skills(tmp_path, verify_result, registry)
    assert repaired == 1
    assert failed == 0

    restored = tmp_path / ".claude/skills/test-skill/SKILL.md"
    assert restored.exists()
    assert restored.read_text(encoding="utf-8") == skill_content


def test_repair_restores_drifted_file(tmp_path: Path) -> None:
    """Repair overwrites a drifted file with canonical content."""
    canonical = "# Canonical\nCorrect content.\n"
    registry = _create_registry(tmp_path, "test-skill", {"SKILL.md": canonical})

    installed_path = ".claude/skills/test-skill/SKILL.md"
    entry = _setup_manifest_and_file(
        tmp_path,
        installed_path=installed_path,
        content="old content before drift",
    )
    manifest = ManagedSkillManifest(entries=[entry])
    save_manifest(manifest, tmp_path)

    # Simulate drift
    (tmp_path / installed_path).write_text("user edited this", encoding="utf-8")
    actual_hash = compute_content_hash(tmp_path / installed_path)

    verify_result = VerifyResult(ok=False, drifted=[(entry, actual_hash)])

    repaired, failed = repair_skills(tmp_path, verify_result, registry)
    assert repaired == 1
    assert failed == 0

    restored = tmp_path / installed_path
    assert restored.read_text(encoding="utf-8") == canonical


def test_repair_handles_missing_source(tmp_path: Path) -> None:
    """Registry cannot find the skill → counted as failed, not repaired."""
    # Empty registry (no skills)
    registry = SkillRegistry(tmp_path / "_empty_registry")

    entry = _make_entry(
        skill_name="nonexistent-skill",
        installed_path=".claude/skills/nonexistent-skill/SKILL.md",
    )
    manifest = ManagedSkillManifest(entries=[entry])
    save_manifest(manifest, tmp_path)

    verify_result = VerifyResult(ok=False, missing=[entry])

    repaired, failed = repair_skills(tmp_path, verify_result, registry)
    assert repaired == 0
    assert failed == 1


def test_repair_updates_manifest(tmp_path: Path) -> None:
    """After repair, manifest entries have updated content hashes."""
    canonical = "# Canonical\nFresh content.\n"
    registry = _create_registry(tmp_path, "test-skill", {"SKILL.md": canonical})

    entry = _make_entry(
        skill_name="test-skill",
        source_file="SKILL.md",
        installed_path=".claude/skills/test-skill/SKILL.md",
        content_hash="sha256:old-stale-hash",
    )
    manifest = ManagedSkillManifest(entries=[entry])
    save_manifest(manifest, tmp_path)

    verify_result = VerifyResult(ok=False, missing=[entry])

    repair_skills(tmp_path, verify_result, registry)

    # Reload manifest and check hash was updated
    reloaded = load_manifest(tmp_path)
    assert reloaded is not None
    assert len(reloaded.entries) == 1

    # Hash should match the canonical file
    expected_hash = compute_content_hash(tmp_path / ".claude/skills/test-skill/SKILL.md")
    assert reloaded.entries[0].content_hash == expected_hash
    assert reloaded.entries[0].content_hash != "sha256:old-stale-hash"


def test_verify_rejects_path_traversal(tmp_path: Path) -> None:
    """Manifest entries with path traversal are reported as errors, not followed."""
    (tmp_path / ".kittify").mkdir(parents=True, exist_ok=True)
    entry = _make_entry(installed_path="../../../etc/passwd")
    manifest = ManagedSkillManifest(entries=[entry])
    save_manifest(manifest, tmp_path)

    result = verify_installed_skills(tmp_path)
    assert not result.ok
    assert len(result.errors) == 1
    assert "Unsafe path" in result.errors[0]


def test_repair_rejects_path_traversal(tmp_path: Path) -> None:
    """Repair refuses to write to paths that escape the project root."""
    registry = SkillRegistry(tmp_path / "_empty_registry")
    entry = _make_entry(installed_path="../../../tmp/evil")
    verify_result = VerifyResult(ok=False, missing=[entry])

    repaired, failed = repair_skills(tmp_path, verify_result, registry)
    assert repaired == 0
    assert failed == 1
