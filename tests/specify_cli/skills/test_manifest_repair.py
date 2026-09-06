"""Tests for manifest_store.repair_stale_manifest and remove_unsafe_symlinks.

Covers (PRIMARY WP04 T020 supersedes the unsafe legacy assertions):
- Canonical rendered content can acquire ownership for configured agents only
- Unknown/missing content cannot acquire arbitrary hash or placeholder ownership
- Adopt-only normalization retains orphan ownership for the pruning owner
- T028: repair_stale_manifest is idempotent (no-op on already-correct manifest)
- T028: repair_stale_manifest detects drifted files (reports, does not auto-repair)
- T028: repair_stale_manifest returns changed=False when nothing changed
- T029: drifted entries appear in result.drifted
- Exact ownership authorizes link removal; prefixes do not
- T030: remove_unsafe_symlinks ignores non-spec-kitty entries
- T030: remove_unsafe_symlinks is a no-op when skills dir absent
"""

from __future__ import annotations

from pathlib import Path
from dataclasses import replace

import pytest

from specify_cli.skills import command_installer
from specify_cli.tool_surface.operations import ApplyConsent, AssessmentInputs, OperationRoot
from tests.upgrade.preview_support.snapshot import assert_unchanged, net_delta, snapshot

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


def _configure(project: Path) -> None:
    (project / ".kittify").mkdir(exist_ok=True)
    (project / ".kittify/config.yaml").write_text("agents:\n  available: [vibe]\n", encoding="utf-8")


def _canonical_unowned(project: Path) -> bytes:
    """Real canonical setup, then remove only the specify ownership entry."""
    _configure(project)
    command_installer.install(project, "vibe")
    manifest = load(project)
    manifest.remove_path(_PATH_SPECIFY)
    save(project, manifest)
    return (project / _PATH_SPECIFY).read_bytes()


# ---------------------------------------------------------------------------
# T028 + T029 — repair_stale_manifest
# ---------------------------------------------------------------------------


class TestRepairStaleManifestAddsEntries:
    """Retained content requires canonical proof, not merely an on-disk hash."""

    @pytest.mark.parametrize("full_catalog", [False, True])
    def test_preserves_unknown_file_without_adopting_hash(self, tmp_path: Path, full_catalog: bool) -> None:
        """Retain the original arbitrary-byte fixture, including readonly mode."""
        # Write a skill file
        content = b"# spec-kitty.specify skill"
        victim = _write_skill_file(tmp_path, _PATH_SPECIFY, content)
        victim.chmod(0o400)
        _configure(tmp_path)

        # Manifest starts empty
        save(tmp_path, SkillsManifest())

        before = snapshot({"project": tmp_path})
        commands = list(command_installer.CANONICAL_COMMANDS) if full_catalog else [_CMD_SPECIFY]
        result = repair_stale_manifest(tmp_path, canonical_commands=commands)
        assert not result.changed and not result.added
        assert load(tmp_path).find(_PATH_SPECIFY) is None
        assert victim.read_bytes() == content
        assert_unchanged(before, snapshot({"project": tmp_path}))

    def test_missing_file_does_not_receive_placeholder_ownership(self, tmp_path: Path) -> None:
        """The absent-file fixture must remain absent, without a manifest rewrite."""
        _configure(tmp_path)
        save(tmp_path, SkillsManifest())
        before = snapshot({"project": tmp_path})
        result = repair_stale_manifest(tmp_path, canonical_commands=list(command_installer.CANONICAL_COMMANDS))
        assert not result.changed and not result.added
        assert load(tmp_path).find(_PATH_SPECIFY) is None
        assert_unchanged(before, snapshot({"project": tmp_path}))

    def test_adopts_real_canonical_bytes_for_configured_owner(self, tmp_path: Path) -> None:
        content = _canonical_unowned(tmp_path)
        before = snapshot({"project": tmp_path})
        result = repair_stale_manifest(tmp_path, canonical_commands=list(command_installer.CANONICAL_COMMANDS))
        assert result.added == [_PATH_SPECIFY] and result.changed
        entry = load(tmp_path).find(_PATH_SPECIFY)
        assert entry is not None and entry.content_hash == fingerprint(content)
        assert entry.agents == ("vibe",)
        assert {effect.path for effect in net_delta(before, snapshot({"project": tmp_path}))} == {".kittify/command-skills-manifest.json"}

    def test_does_not_add_already_present_entry(self, tmp_path: Path) -> None:
        """Entries already in the manifest are not re-added."""
        m = SkillsManifest()
        m.upsert(_make_entry(_PATH_SPECIFY))
        save(tmp_path, m)

        result = repair_stale_manifest(tmp_path, canonical_commands=[_CMD_SPECIFY])

        assert _PATH_SPECIFY not in result.added
        assert result.added == []


class TestRepairStaleManifestRemovesOrphans:
    """Normalization must retain proof until the pruning owner can assess it."""

    def test_retains_orphaned_entry_for_proven_pruning(self, tmp_path: Path) -> None:
        m = SkillsManifest()
        m.upsert(_make_entry(_PATH_SPECIFY))
        m.upsert(_make_entry(_PATH_ORPHAN))  # not in canonical set
        save(tmp_path, m)
        before = snapshot({"project": tmp_path})
        result = repair_stale_manifest(tmp_path, canonical_commands=[_CMD_SPECIFY])
        assert not result.removed and not result.changed
        manifest = load(tmp_path)
        assert manifest.find(_PATH_ORPHAN) == m.find(_PATH_ORPHAN)
        assert manifest.find(_PATH_SPECIFY) is not None
        assert_unchanged(before, snapshot({"project": tmp_path}))

    @pytest.mark.parametrize("edited", [False, True])
    def test_pruning_retains_shared_or_edited_candidates(self, tmp_path: Path, edited: bool) -> None:
        _configure(tmp_path)
        victim = _write_skill_file(tmp_path, _PATH_ORPHAN, b"owned retired command")
        entry = replace(_make_entry(_PATH_ORPHAN, fingerprint(victim.read_bytes())), agents=("codex", "vibe"))
        save(tmp_path, SkillsManifest(entries=[entry]))
        if edited:
            victim.write_bytes(b"edited retired command")
        before = snapshot({"project": tmp_path})
        inputs = AssessmentInputs(OperationRoot("project", "project", tmp_path), consent=ApplyConsent(automatic=True))
        assessment = command_installer.prepare_commands(inputs, (), remove_agents=("codex",))
        assert assessment.complete
        assert command_installer.apply_commands(assessment, inputs.consent).outcome == "applied"
        if edited:
            assert any(d.state == "consent_required" for d in assessment.dispositions)
            assert_unchanged(before, snapshot({"project": tmp_path}))
        else:
            retained = load(tmp_path).find(_PATH_ORPHAN)
            assert retained is not None and retained.agents == ("vibe",)
            assert victim.read_bytes() == b"owned retired command"
            assert {e.path for e in net_delta(before, snapshot({"project": tmp_path}))} == {".kittify/command-skills-manifest.json"}
            assert command_installer.prune_stale(tmp_path) == [_PATH_ORPHAN]
            assert not victim.exists() and not victim.parent.exists()
            assert load(tmp_path).find(_PATH_ORPHAN) is None

    def test_no_orphans_when_manifest_matches_canonical(self, tmp_path: Path) -> None:
        m = SkillsManifest()
        m.upsert(_make_entry(_PATH_SPECIFY))
        save(tmp_path, m)
        before = snapshot({"project": tmp_path})
        result = repair_stale_manifest(tmp_path, canonical_commands=[_CMD_SPECIFY])

        assert result.removed == []
        assert_unchanged(before, snapshot({"project": tmp_path}))


class TestRepairStaleManifestIdempotent:
    """Running repair on an already-correct manifest is a no-op."""

    def test_idempotent_no_changes_needed(self, tmp_path: Path) -> None:
        content = b"# skill content"
        _write_skill_file(tmp_path, _PATH_SPECIFY, content)

        m = SkillsManifest()
        m.upsert(_make_entry(_PATH_SPECIFY, content_hash=fingerprint(content)))
        save(tmp_path, m)
        before = snapshot({"project": tmp_path})
        result = repair_stale_manifest(tmp_path, canonical_commands=[_CMD_SPECIFY])

        assert result.added == []
        assert result.removed == []
        assert result.changed is False
        assert_unchanged(before, snapshot({"project": tmp_path}))


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
        # Preserve the arbitrary-byte edge case separately from canonical adoption.
        before = snapshot({"project": tmp_path})
        refused = repair_stale_manifest(tmp_path, canonical_commands=[_CMD_SPECIFY])
        assert not refused.added and not refused.drifted
        assert_unchanged(before, snapshot({"project": tmp_path}))
        (tmp_path / _PATH_SPECIFY).unlink()
        _canonical_unowned(tmp_path)
        result = repair_stale_manifest(tmp_path, canonical_commands=list(command_installer.CANONICAL_COMMANDS))
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
        before = snapshot({"project": tmp_path})
        absent = repair_stale_manifest(tmp_path, canonical_commands=[_CMD_SPECIFY])
        assert not absent.changed
        assert_unchanged(before, snapshot({"project": tmp_path}))
        _canonical_unowned(tmp_path)
        result = repair_stale_manifest(tmp_path, canonical_commands=list(command_installer.CANONICAL_COMMANDS))
        assert result.changed is True

    def test_changed_false_when_orphan_ownership_is_retained(self, tmp_path: Path) -> None:
        m = SkillsManifest()
        m.upsert(_make_entry(_PATH_ORPHAN))
        save(tmp_path, m)
        before = snapshot({"project": tmp_path})
        result = repair_stale_manifest(tmp_path, canonical_commands=[])
        assert not result.changed and not result.removed
        assert load(tmp_path).find(_PATH_ORPHAN) == m.find(_PATH_ORPHAN)
        assert_unchanged(before, snapshot({"project": tmp_path}))


# ---------------------------------------------------------------------------
# T030 — remove_unsafe_symlinks
# ---------------------------------------------------------------------------


class TestRemoveUnsafeSymlinks:
    """Exact manifest ownership, never the package prefix, permits unlinking."""

    @pytest.mark.parametrize("dangling", [False, True])
    def test_preserves_unowned_symlink_dir(self, tmp_path: Path, dangling: bool) -> None:
        skills_dir = tmp_path / ".agents" / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)

        # Create a symlink that looks like a skill package dir
        link = skills_dir / "spec-kitty"
        target = tmp_path / "elsewhere"
        target.mkdir()
        (target / "sentinel").write_bytes(b"target data")
        if dangling:
            target = target / "absent"
        link.symlink_to(target)
        before = snapshot({"project": tmp_path})
        target_text = link.readlink()
        result = remove_unsafe_symlinks(tmp_path)
        assert link.is_symlink() and link.readlink() == target_text
        assert not result.changed and not result.symlinks_removed
        assert_unchanged(before, snapshot({"project": tmp_path}))

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

    def test_preserves_multiple_unowned_symlinks(self, tmp_path: Path) -> None:
        skills_dir = tmp_path / ".agents" / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        target = tmp_path / "tgt"
        target.mkdir()
        (target / "sentinel").write_bytes(b"target data")

        links = ["spec-kitty", "spec-kitty.old-cmd"]
        for name in links:
            (skills_dir / name).symlink_to(target)

        before = snapshot({"project": tmp_path})
        result = remove_unsafe_symlinks(tmp_path)
        assert not result.changed and not result.symlinks_removed
        for name in links:
            link = skills_dir / name
            assert link.is_symlink() and link.readlink() == target
        assert_unchanged(before, snapshot({"project": tmp_path}))

    def test_removes_exact_owned_link_without_losing_shared_owners(self, tmp_path: Path) -> None:
        _configure(tmp_path)
        command_installer.install(tmp_path, "codex")
        command_installer.install(tmp_path, "vibe")
        package = (tmp_path / _PATH_SPECIFY).parent
        target = tmp_path / "retained-package"
        package.rename(target)
        package.symlink_to(target, target_is_directory=True)
        before = snapshot({"project": tmp_path})
        original_manifest = load(tmp_path)
        result = remove_unsafe_symlinks(tmp_path)
        assert result.symlinks_removed == [str(package)] and result.changed
        after = snapshot({"project": tmp_path})
        assert {(e.path, e.action) for e in net_delta(before, after)} == {(package.relative_to(tmp_path).as_posix(), "delete")}
        assert load(tmp_path) == original_manifest
        assert before[("project", "retained-package/SKILL.md")] == after[("project", "retained-package/SKILL.md")]
        command_installer.install(tmp_path, "vibe")
        entry = load(tmp_path).find(_PATH_SPECIFY)
        assert entry is not None and entry.agents == ("codex", "vibe")
        assert (package / "SKILL.md").read_bytes() == (target / "SKILL.md").read_bytes()

    def test_changed_false_when_no_symlinks(self, tmp_path: Path) -> None:
        skills_dir = tmp_path / ".agents" / "skills"
        real_dir = skills_dir / "spec-kitty.specify"
        real_dir.mkdir(parents=True, exist_ok=True)

        result = remove_unsafe_symlinks(tmp_path)
        assert result.changed is False
