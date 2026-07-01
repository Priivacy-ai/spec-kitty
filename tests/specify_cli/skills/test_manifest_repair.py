"""Tests for manifest_store.repair_stale_manifest and remove_unsafe_symlinks.

Covers:
- T028: repair_stale_manifest adds missing canonical entries
- T028: repair_stale_manifest removes orphaned entries
- T028: repair_stale_manifest is idempotent (no-op on already-correct manifest)
- T028: repair_stale_manifest detects drifted files (reports, does not auto-repair)
- T028: repair_stale_manifest returns changed=False when nothing changed
- T029: drifted entries appear in result.drifted
- T030: remove_unsafe_symlinks removes symlink directories, leaves real dirs
- T030: remove_unsafe_symlinks ignores non-spec-kitty entries
- T030: remove_unsafe_symlinks is a no-op when skills dir absent
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.skills.manifest_store import (
    ManifestEntry,
    SkillsManifest,
    fingerprint,
    load,
    remove_unsafe_symlinks,
    repair_stale_manifest,
    save,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VALID_HASH = "a" * 64
_VALID_TS = "2026-01-01T00:00:00+00:00"
_VALID_VERSION = "3.2.0"

_CMD_SPECIFY = "specify"
_CMD_PLAN = "plan"
_CMD_TASKS = "tasks"

_PATH_SPECIFY = ".agents/skills/spec-kitty.specify/SKILL.md"
_PATH_PLAN = ".agents/skills/spec-kitty.plan/SKILL.md"
_PATH_TASKS = ".agents/skills/spec-kitty.tasks/SKILL.md"
_PATH_ORPHAN = ".agents/skills/spec-kitty.legacy-opener/SKILL.md"


def _make_entry(path: str, content_hash: str = _VALID_HASH) -> ManifestEntry:
    return ManifestEntry(
        path=path,
        content_hash=content_hash,
        agents=("codex",),
        installed_at=_VALID_TS,
        spec_kitty_version=_VALID_VERSION,
    )


def _write_skill_file(project_root: Path, rel_path: str, content: bytes = b"hello") -> Path:
    """Create the skill file at rel_path under project_root."""
    abs_path = project_root / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(content)
    return abs_path


# ---------------------------------------------------------------------------
# T028 + T029 — repair_stale_manifest
# ---------------------------------------------------------------------------


class TestRepairStaleManifestAddsEntries:
    """Missing canonical entries are added to the manifest."""

    def test_adds_missing_entry_when_file_exists(self, tmp_path: Path) -> None:
        """A missing entry is synthesized from the on-disk file hash."""
        # Write a skill file
        content = b"# spec-kitty.specify skill"
        _write_skill_file(tmp_path, _PATH_SPECIFY, content)

        # Manifest starts empty
        save(tmp_path, SkillsManifest())

        result = repair_stale_manifest(tmp_path, canonical_commands=[_CMD_SPECIFY])

        assert _PATH_SPECIFY in result.added
        assert result.changed is True

        # Verify the entry was persisted with the correct hash and a non-empty agents tuple
        manifest = load(tmp_path)
        entry = manifest.find(_PATH_SPECIFY)
        assert entry is not None
        assert entry.content_hash == fingerprint(content)
        assert len(entry.agents) > 0  # schema requires non-empty agents

    def test_adds_missing_entry_with_placeholder_when_file_absent(self, tmp_path: Path) -> None:
        """A missing entry is added with empty-bytes placeholder hash when file does not exist."""
        save(tmp_path, SkillsManifest())

        result = repair_stale_manifest(tmp_path, canonical_commands=[_CMD_SPECIFY])

        assert _PATH_SPECIFY in result.added
        manifest = load(tmp_path)
        entry = manifest.find(_PATH_SPECIFY)
        assert entry is not None
        assert entry.content_hash == fingerprint(b"")
        assert len(entry.agents) > 0  # schema requires non-empty agents

    def test_does_not_add_already_present_entry(self, tmp_path: Path) -> None:
        """Entries already in the manifest are not re-added."""
        m = SkillsManifest()
        m.upsert(_make_entry(_PATH_SPECIFY))
        save(tmp_path, m)

        result = repair_stale_manifest(tmp_path, canonical_commands=[_CMD_SPECIFY])

        assert _PATH_SPECIFY not in result.added
        assert result.added == []


class TestRepairStaleManifestRemovesOrphans:
    """Orphaned entries (not in canonical_commands) are removed."""

    def test_removes_orphaned_entry(self, tmp_path: Path) -> None:
        m = SkillsManifest()
        m.upsert(_make_entry(_PATH_SPECIFY))
        m.upsert(_make_entry(_PATH_ORPHAN))  # not in canonical set
        save(tmp_path, m)

        result = repair_stale_manifest(tmp_path, canonical_commands=[_CMD_SPECIFY])

        assert _PATH_ORPHAN in result.removed
        assert result.changed is True

        manifest = load(tmp_path)
        assert manifest.find(_PATH_ORPHAN) is None
        assert manifest.find(_PATH_SPECIFY) is not None

    def test_no_orphans_when_manifest_matches_canonical(self, tmp_path: Path) -> None:
        m = SkillsManifest()
        m.upsert(_make_entry(_PATH_SPECIFY))
        save(tmp_path, m)

        result = repair_stale_manifest(tmp_path, canonical_commands=[_CMD_SPECIFY])

        assert result.removed == []


class TestRepairStaleManifestIdempotent:
    """Running repair on an already-correct manifest is a no-op."""

    def test_idempotent_no_changes_needed(self, tmp_path: Path) -> None:
        content = b"# skill content"
        _write_skill_file(tmp_path, _PATH_SPECIFY, content)

        m = SkillsManifest()
        m.upsert(_make_entry(_PATH_SPECIFY, content_hash=fingerprint(content)))
        save(tmp_path, m)

        result = repair_stale_manifest(tmp_path, canonical_commands=[_CMD_SPECIFY])

        assert result.added == []
        assert result.removed == []
        assert result.changed is False


class TestRepairStaleManifestDriftDetection:
    """T029 — drifted files are reported but not auto-repaired."""

    def test_detects_drifted_content(self, tmp_path: Path) -> None:
        original_content = b"# original"
        _write_skill_file(tmp_path, _PATH_SPECIFY, b"# modified content")

        m = SkillsManifest()
        m.upsert(_make_entry(_PATH_SPECIFY, content_hash=fingerprint(original_content)))
        save(tmp_path, m)

        result = repair_stale_manifest(tmp_path, canonical_commands=[_CMD_SPECIFY])

        # Drifted file is reported
        assert _PATH_SPECIFY in result.drifted
        # But the manifest entry is NOT overwritten (no auto-repair)
        manifest = load(tmp_path)
        entry = manifest.find(_PATH_SPECIFY)
        assert entry is not None
        assert entry.content_hash == fingerprint(original_content)

    def test_newly_added_entry_not_reported_as_drifted(self, tmp_path: Path) -> None:
        """Entries added in this repair pass are not reported as drifted."""
        content = b"# new skill"
        _write_skill_file(tmp_path, _PATH_SPECIFY, content)

        save(tmp_path, SkillsManifest())  # empty manifest — entry is missing

        result = repair_stale_manifest(tmp_path, canonical_commands=[_CMD_SPECIFY])

        assert _PATH_SPECIFY in result.added
        # The newly-added entry must NOT also appear in drifted
        assert _PATH_SPECIFY not in result.drifted

    def test_symlink_not_reported_as_drifted(self, tmp_path: Path) -> None:
        """Symlink targets are not fingerprinted and not reported as drifted."""
        skill_dir = tmp_path / ".agents" / "skills" / "spec-kitty.specify"
        skill_dir.mkdir(parents=True, exist_ok=True)
        target = tmp_path / "real_file.md"
        target.write_bytes(b"real")
        (skill_dir / "SKILL.md").symlink_to(target)

        m = SkillsManifest()
        m.upsert(_make_entry(_PATH_SPECIFY, content_hash=_VALID_HASH))
        save(tmp_path, m)

        result = repair_stale_manifest(tmp_path, canonical_commands=[_CMD_SPECIFY])

        assert _PATH_SPECIFY not in result.drifted


class TestRepairStaleManifestChangedFlag:
    """ManifestRepairResult.changed reflects whether mutations occurred."""

    def test_changed_false_when_nothing_to_repair(self, tmp_path: Path) -> None:
        content = b"data"
        _write_skill_file(tmp_path, _PATH_SPECIFY, content)

        m = SkillsManifest()
        m.upsert(_make_entry(_PATH_SPECIFY, content_hash=fingerprint(content)))
        save(tmp_path, m)

        result = repair_stale_manifest(tmp_path, canonical_commands=[_CMD_SPECIFY])
        assert result.changed is False

    def test_changed_true_when_entry_added(self, tmp_path: Path) -> None:
        save(tmp_path, SkillsManifest())
        result = repair_stale_manifest(tmp_path, canonical_commands=[_CMD_SPECIFY])
        assert result.changed is True

    def test_changed_true_when_entry_removed(self, tmp_path: Path) -> None:
        m = SkillsManifest()
        m.upsert(_make_entry(_PATH_ORPHAN))
        save(tmp_path, m)

        result = repair_stale_manifest(tmp_path, canonical_commands=[])
        assert result.changed is True


# ---------------------------------------------------------------------------
# T030 — remove_unsafe_symlinks
# ---------------------------------------------------------------------------


class TestRemoveUnsafeSymlinks:
    """Unsafe symlink artifacts in .agents/skills/ are detected and removed."""

    def test_removes_symlink_dir(self, tmp_path: Path) -> None:
        skills_dir = tmp_path / ".agents" / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)

        # Create a symlink that looks like a skill package dir
        link = skills_dir / "spec-kitty"
        target = tmp_path / "elsewhere"
        target.mkdir()
        link.symlink_to(target)

        result = remove_unsafe_symlinks(tmp_path)

        assert not link.exists()
        assert str(link) in result.symlinks_removed

    def test_leaves_real_skill_dirs_untouched(self, tmp_path: Path) -> None:
        skills_dir = tmp_path / ".agents" / "skills"
        real_dir = skills_dir / "spec-kitty.specify"
        real_dir.mkdir(parents=True, exist_ok=True)
        (real_dir / "SKILL.md").write_text("# skill")

        result = remove_unsafe_symlinks(tmp_path)

        assert real_dir.exists()
        assert result.symlinks_removed == []

    def test_ignores_non_spec_kitty_entries(self, tmp_path: Path) -> None:
        skills_dir = tmp_path / ".agents" / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)

        # A symlink NOT starting with spec-kitty. — must be left alone
        other_link = skills_dir / "third-party.tool"
        target = tmp_path / "other"
        target.mkdir()
        other_link.symlink_to(target)

        result = remove_unsafe_symlinks(tmp_path)

        assert other_link.exists()
        assert result.symlinks_removed == []

    def test_noop_when_skills_dir_absent(self, tmp_path: Path) -> None:
        result = remove_unsafe_symlinks(tmp_path)

        assert result.symlinks_removed == []
        assert result.changed is False

    def test_removes_multiple_symlinks(self, tmp_path: Path) -> None:
        skills_dir = tmp_path / ".agents" / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        target = tmp_path / "tgt"
        target.mkdir()

        links = ["spec-kitty", "spec-kitty.old-cmd"]
        for name in links:
            (skills_dir / name).symlink_to(target)

        result = remove_unsafe_symlinks(tmp_path)

        assert len(result.symlinks_removed) == 2
        for name in links:
            assert not (skills_dir / name).exists()

    def test_changed_false_when_no_symlinks(self, tmp_path: Path) -> None:
        skills_dir = tmp_path / ".agents" / "skills"
        real_dir = skills_dir / "spec-kitty.specify"
        real_dir.mkdir(parents=True, exist_ok=True)

        result = remove_unsafe_symlinks(tmp_path)
        assert result.changed is False
