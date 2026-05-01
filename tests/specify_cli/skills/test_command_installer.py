"""Tests for command_installer.py (WP03).

Covers:
- Happy path install (12 SKILL.md files, manifest has 12 entries)
- Idempotent install (second call: already_installed == 12, zero disk writes)
- Reused-shared add (install codex then vibe; agents == ("codex", "vibe"))
- Three-tenant coexistence (NFR-002 load-bearing test)
- Parent-dir preservation (third-party file alongside SKILL.md)
- Collision error (stale manifest entry, on-disk hash mismatch)
- File mutation on remove (InstallerError("file_mutation_detected"))
- verify() drift / orphans / gaps
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

import pytest

from specify_cli.skills.command_installer import (
    CANONICAL_COMMANDS,
    SUPPORTED_AGENTS,
    InstallerError,
    install,
    remove,
    verify,
)
from specify_cli.skills import manifest_store
from specify_cli.skills.manifest_store import ManifestEntry, SkillsManifest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEMPLATE_REPO_ROOT = Path(__file__).parent.parent.parent.parent  # tests/specify_cli/skills/../../.. → repo root


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256(path.read_bytes())


def _write_config(repo_root: Path) -> None:
    """Write a minimal .kittify/config.yaml so agent config checks pass."""
    kittify = repo_root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "config.yaml").write_text(
        "agents:\n  available:\n    - codex\n    - vibe\n",
        encoding="utf-8",
    )


def _skill_path(repo_root: Path, command: str) -> Path:
    return repo_root / ".agents" / "skills" / f"spec-kitty.{command}" / "SKILL.md"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A minimal project root with .kittify/ ready.

    Templates are located inside the installed ``specify_cli`` package via
    ``_package_templates_dir()``; a real user project never contains
    ``src/specify_cli/missions/`` under its own root, so we deliberately
    do **not** seed that path here. If a test fails because templates cannot
    be located, the production code — not the fixture — is the suspect.
    """
    _write_config(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Happy path install
# ---------------------------------------------------------------------------


class TestHappyPathInstall:
    def test_creates_all_skill_md_files(self, repo: Path) -> None:
        install(repo, "vibe")

        for command in CANONICAL_COMMANDS:
            path = _skill_path(repo, command)
            assert path.exists(), f"Expected SKILL.md for command {command!r}"

    def test_install_report_has_11_added(self, repo: Path) -> None:
        report = install(repo, "vibe")

        assert len(report.added) == len(CANONICAL_COMMANDS)
        assert report.already_installed == []
        assert report.reused_shared == []
        assert report.errors == []

    def test_manifest_has_11_entries(self, repo: Path) -> None:
        install(repo, "vibe")

        manifest = manifest_store.load(repo)
        assert len(manifest.entries) == len(CANONICAL_COMMANDS)

    def test_manifest_entries_have_correct_agent(self, repo: Path) -> None:
        install(repo, "vibe")

        manifest = manifest_store.load(repo)
        for entry in manifest.entries:
            assert entry.agents == ("vibe",), f"Entry {entry.path!r} has unexpected agents {entry.agents!r}"

    def test_manifest_entries_have_correct_paths(self, repo: Path) -> None:
        install(repo, "vibe")

        manifest = manifest_store.load(repo)
        paths = {e.path for e in manifest.entries}
        expected = {f".agents/skills/spec-kitty.{cmd}/SKILL.md" for cmd in CANONICAL_COMMANDS}
        assert paths == expected

    def test_content_hash_matches_disk(self, repo: Path) -> None:
        install(repo, "vibe")

        manifest = manifest_store.load(repo)
        for entry in manifest.entries:
            disk_hash = _sha256_file(repo / entry.path)
            assert disk_hash == entry.content_hash, f"Hash mismatch for {entry.path!r}"

    def test_skill_md_has_frontmatter(self, repo: Path) -> None:
        install(repo, "vibe")

        skill_path = _skill_path(repo, "specify")
        content = skill_path.read_text(encoding="utf-8")
        assert content.startswith("---\n"), "SKILL.md should start with YAML frontmatter"
        assert "name: spec-kitty.specify" in content


# ---------------------------------------------------------------------------
# Idempotent install
# ---------------------------------------------------------------------------


class TestIdempotentInstall:
    def test_second_call_reports_already_installed(self, repo: Path) -> None:
        install(repo, "vibe")
        report2 = install(repo, "vibe")

        assert len(report2.already_installed) == len(CANONICAL_COMMANDS)
        assert report2.added == []
        assert report2.reused_shared == []

    def test_second_call_does_not_change_file_content(self, repo: Path) -> None:
        install(repo, "vibe")

        # Capture file hashes after first install.
        hashes_before: dict[str, str] = {}
        for cmd in CANONICAL_COMMANDS:
            p = _skill_path(repo, cmd)
            hashes_before[cmd] = _sha256_file(p)

        install(repo, "vibe")

        for cmd in CANONICAL_COMMANDS:
            p = _skill_path(repo, cmd)
            assert _sha256_file(p) == hashes_before[cmd], f"File content changed on second install for {cmd!r}"

    def test_second_call_does_not_change_manifest(self, repo: Path) -> None:
        install(repo, "vibe")
        manifest_path = repo / ".kittify" / "command-skills-manifest.json"
        content_after_first = manifest_path.read_bytes()

        install(repo, "vibe")
        content_after_second = manifest_path.read_bytes()

        assert content_after_first == content_after_second, "Manifest changed on idempotent install"

    def test_second_call_no_disk_writes(self, repo: Path) -> None:
        install(repo, "vibe")

        # Capture mtimes.
        mtimes_before: dict[str, float] = {}
        for cmd in CANONICAL_COMMANDS:
            p = _skill_path(repo, cmd)
            mtimes_before[cmd] = p.stat().st_mtime

        # Small delay to make mtime changes detectable on coarse-resolution FSes.
        time.sleep(0.01)
        install(repo, "vibe")

        for cmd in CANONICAL_COMMANDS:
            p = _skill_path(repo, cmd)
            assert p.stat().st_mtime == mtimes_before[cmd], f"File mtime changed (unexpected write) for {cmd!r}"


# ---------------------------------------------------------------------------
# Reused-shared (two agents, one set of files)
# ---------------------------------------------------------------------------


class TestReusedShared:
    def test_second_agent_reported_as_reused_shared(self, repo: Path) -> None:
        install(repo, "codex")
        report2 = install(repo, "vibe")

        assert len(report2.reused_shared) == len(CANONICAL_COMMANDS)
        assert report2.added == []
        assert report2.already_installed == []

    def test_manifest_entries_have_both_agents(self, repo: Path) -> None:
        install(repo, "codex")
        install(repo, "vibe")

        manifest = manifest_store.load(repo)
        for entry in manifest.entries:
            assert entry.agents == ("codex", "vibe"), f"Entry {entry.path!r} has unexpected agents {entry.agents!r}"

    def test_file_bytes_unchanged_after_second_agent(self, repo: Path) -> None:
        install(repo, "codex")

        hashes_after_codex: dict[str, str] = {}
        for cmd in CANONICAL_COMMANDS:
            hashes_after_codex[cmd] = _sha256_file(_skill_path(repo, cmd))

        install(repo, "vibe")

        for cmd in CANONICAL_COMMANDS:
            assert _sha256_file(_skill_path(repo, cmd)) == hashes_after_codex[cmd], f"File bytes changed when adding vibe to {cmd!r}"


# ---------------------------------------------------------------------------
# Three-tenant coexistence (NFR-002 — the load-bearing test)
# ---------------------------------------------------------------------------


class TestThreeTenantCoexistence:
    """Third-party dirs under .agents/skills/ must survive the full
    install(codex) + install(vibe) + remove(codex) + remove(vibe) lifecycle
    byte-for-byte unchanged."""

    def _setup_third_party_files(self, repo: Path) -> dict[str, str]:
        """Seed three third-party entries and return {rel_path: sha256}."""
        skills_root = repo / ".agents" / "skills"
        skills_root.mkdir(parents=True, exist_ok=True)

        files: dict[Path, bytes] = {
            skills_root / "handwritten-review" / "SKILL.md": (b"# handwritten review\nThis is a hand-crafted review skill.\nContents: detailed review steps.\n"),
            skills_root / "another-tool.lint" / "SKILL.md": (b"# another-tool lint\nLinting workflow from another tool.\nDo not delete me!\n"),
            skills_root / "my-stuff" / "other-file.txt": (b"This is my personal notes file.\nKeep it here forever.\n"),
        }

        result: dict[str, str] = {}
        for path, content in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            rel = str(path.relative_to(repo)).replace("\\", "/")
            result[rel] = _sha256(content)

        return result

    def _assert_third_party_unchanged(self, repo: Path, expected: dict[str, str], step: str) -> None:
        for rel_path, expected_hash in expected.items():
            abs_path = repo / rel_path
            assert abs_path.exists(), f"[{step}] Third-party file missing: {rel_path!r}"
            actual_hash = _sha256_file(abs_path)
            assert actual_hash == expected_hash, (
                f"[{step}] Third-party file mutated: {rel_path!r}\n  expected SHA-256: {expected_hash}\n  actual  SHA-256: {actual_hash}"
            )

    def test_full_lifecycle_preserves_third_party_files(self, repo: Path) -> None:
        third_party_hashes = self._setup_third_party_files(repo)

        # Step 1: install codex
        install(repo, "codex")
        self._assert_third_party_unchanged(repo, third_party_hashes, "after install(codex)")

        # Step 2: install vibe
        install(repo, "vibe")
        self._assert_third_party_unchanged(repo, third_party_hashes, "after install(vibe)")

        # Step 3: remove codex
        remove(repo, "codex")
        self._assert_third_party_unchanged(repo, third_party_hashes, "after remove(codex)")

        # Step 4: remove vibe
        remove(repo, "vibe")
        self._assert_third_party_unchanged(repo, third_party_hashes, "after remove(vibe)")

    def test_spec_kitty_files_gone_after_full_remove(self, repo: Path) -> None:
        self._setup_third_party_files(repo)
        install(repo, "codex")
        install(repo, "vibe")
        remove(repo, "codex")
        remove(repo, "vibe")

        for cmd in CANONICAL_COMMANDS:
            path = _skill_path(repo, cmd)
            assert not path.exists(), f"spec-kitty skill file should be deleted: {path}"

    def test_manifest_empty_after_full_remove(self, repo: Path) -> None:
        self._setup_third_party_files(repo)
        install(repo, "codex")
        install(repo, "vibe")
        remove(repo, "codex")
        remove(repo, "vibe")

        manifest = manifest_store.load(repo)
        assert manifest.entries == [], f"Manifest should be empty after full remove, got: {manifest.entries!r}"

    def test_spec_kitty_dirs_gone_after_full_remove(self, repo: Path) -> None:
        self._setup_third_party_files(repo)
        install(repo, "codex")
        install(repo, "vibe")
        remove(repo, "codex")
        remove(repo, "vibe")

        skills_root = repo / ".agents" / "skills"
        if skills_root.exists():
            remaining = [d.name for d in skills_root.iterdir() if d.is_dir() and d.name.startswith("spec-kitty.")]
            assert remaining == [], f"spec-kitty.* directories should be gone, found: {remaining!r}"

    def test_third_party_dirs_still_present_after_full_remove(self, repo: Path) -> None:
        self._setup_third_party_files(repo)
        install(repo, "codex")
        install(repo, "vibe")
        remove(repo, "codex")
        remove(repo, "vibe")

        skills_root = repo / ".agents" / "skills"
        assert (skills_root / "handwritten-review" / "SKILL.md").exists()
        assert (skills_root / "another-tool.lint" / "SKILL.md").exists()
        assert (skills_root / "my-stuff" / "other-file.txt").exists()


# ---------------------------------------------------------------------------
# Parent-dir preservation
# ---------------------------------------------------------------------------


class TestParentDirPreservation:
    """When a third-party file exists inside a spec-kitty.* dir, remove()
    must delete SKILL.md (if agents empties) but leave the dir and the
    third-party file intact."""

    def test_remove_deletes_skill_md_but_keeps_extra_file(self, repo: Path) -> None:
        install(repo, "vibe")

        # Place a third-party file inside a spec-kitty.specify dir.
        specify_dir = repo / ".agents" / "skills" / "spec-kitty.specify"
        extra_file = specify_dir / "extra.txt"
        extra_file.write_bytes(b"User-authored content.\n")
        extra_hash = _sha256_file(extra_file)

        remove(repo, "vibe")

        # SKILL.md should be gone.
        skill_path = specify_dir / "SKILL.md"
        assert not skill_path.exists(), "SKILL.md should have been deleted"

        # extra.txt must survive byte-identical.
        assert extra_file.exists(), "Third-party extra.txt must not be deleted"
        assert _sha256_file(extra_file) == extra_hash, "extra.txt was mutated"

        # The parent dir must stay (it contains extra.txt).
        assert specify_dir.exists(), "Parent dir must be preserved when non-empty"

    def test_remove_deletes_empty_parent_dir(self, repo: Path) -> None:
        """When no third-party files exist, the parent dir should be removed."""
        install(repo, "vibe")

        # Verify SKILL.md and its parent exist before remove.
        specify_dir = repo / ".agents" / "skills" / "spec-kitty.specify"
        assert specify_dir.exists()

        remove(repo, "vibe")

        # The parent dir should be gone (it was empty after SKILL.md deletion).
        assert not specify_dir.exists(), "Empty spec-kitty.specify/ dir should be removed"


# ---------------------------------------------------------------------------
# Collision error
# ---------------------------------------------------------------------------


class TestCollisionError:
    def test_unexpected_collision_raised_when_disk_hash_differs(self, repo: Path) -> None:
        """Seed a stale manifest entry; install() should raise unexpected_collision."""
        # Build a manifest with a stale entry (wrong hash) pointing to a real path.
        kittify = repo / ".kittify"
        kittify.mkdir(parents=True, exist_ok=True)
        rel_path = ".agents/skills/spec-kitty.specify/SKILL.md"
        abs_path = repo / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_bytes(b"# stale content\n")

        stale_hash = "a" * 64  # obviously wrong SHA-256
        stale_entry = ManifestEntry(
            path=rel_path,
            content_hash=stale_hash,
            agents=("vibe",),
            installed_at="2024-01-01T00:00:00+00:00",
            spec_kitty_version="0.0.1",
        )
        manifest = SkillsManifest(entries=[stale_entry])
        manifest_store.save(repo, manifest)

        with pytest.raises(InstallerError) as exc_info:
            install(repo, "vibe")

        assert exc_info.value.code == "unexpected_collision"
        assert exc_info.value.context.get("path") == rel_path


# ---------------------------------------------------------------------------
# File mutation on remove
# ---------------------------------------------------------------------------


class TestFileMutationOnRemove:
    def test_file_mutation_detected_error_raised(self, repo: Path) -> None:
        install(repo, "vibe")

        # Edit the SKILL.md by hand to simulate drift.
        skill_path = _skill_path(repo, "specify")
        original_content = skill_path.read_bytes()
        skill_path.write_bytes(original_content + b"\n# injected line\n")

        with pytest.raises(InstallerError) as exc_info:
            remove(repo, "vibe")

        assert exc_info.value.code == "file_mutation_detected"
        assert ".agents/skills/spec-kitty.specify/SKILL.md" in (exc_info.value.context.get("path", ""))

    def test_manifest_unchanged_when_mutation_detected(self, repo: Path) -> None:
        install(repo, "vibe")

        manifest_path = repo / ".kittify" / "command-skills-manifest.json"
        manifest_before = manifest_path.read_bytes()

        # Mutate the first command's SKILL.md.
        first_cmd = CANONICAL_COMMANDS[0]
        skill_path = _skill_path(repo, first_cmd)
        skill_path.write_bytes(skill_path.read_bytes() + b"\n# mutated\n")

        with pytest.raises(InstallerError):
            remove(repo, "vibe")

        assert manifest_path.read_bytes() == manifest_before, "Manifest must not be modified when file_mutation_detected is raised"


# ---------------------------------------------------------------------------
# verify() — drift, gaps, orphans (T017)
# ---------------------------------------------------------------------------


class TestVerifyDrift:
    def test_clean_install_has_no_drift(self, repo: Path) -> None:
        install(repo, "vibe")
        report = verify(repo)

        assert report.drift == []
        assert report.orphans == []
        assert report.gaps == []

    def test_mutated_file_reported_as_drift(self, repo: Path) -> None:
        install(repo, "vibe")

        # Mutate one SKILL.md.
        skill_path = _skill_path(repo, "specify")
        skill_path.write_bytes(skill_path.read_bytes() + b"\n# drifted\n")

        report = verify(repo)

        assert ".agents/skills/spec-kitty.specify/SKILL.md" in report.drift
        assert report.gaps == []
        assert report.orphans == []

    def test_verify_does_not_modify_disk(self, repo: Path) -> None:
        install(repo, "vibe")
        skill_path = _skill_path(repo, "specify")
        skill_path.write_bytes(skill_path.read_bytes() + b"\n# drifted\n")
        content_before = skill_path.read_bytes()

        verify(repo)

        assert skill_path.read_bytes() == content_before, "verify() must not modify files on disk"


class TestVerifyGaps:
    def test_deleted_file_reported_as_gap(self, repo: Path) -> None:
        install(repo, "vibe")

        # Delete one SKILL.md.
        skill_path = _skill_path(repo, "tasks")
        skill_path.unlink()

        report = verify(repo)

        assert ".agents/skills/spec-kitty.tasks/SKILL.md" in report.gaps
        assert report.drift == []
        assert report.orphans == []

    def test_verify_does_not_recreate_missing_file(self, repo: Path) -> None:
        install(repo, "vibe")
        skill_path = _skill_path(repo, "tasks")
        skill_path.unlink()

        verify(repo)

        assert not skill_path.exists(), "verify() must not write missing files"


class TestVerifyOrphans:
    def test_unregistered_spec_kitty_file_is_orphan(self, repo: Path) -> None:
        # Write a spec-kitty.* file without registering it in the manifest.
        orphan_path = repo / ".agents" / "skills" / "spec-kitty.unknown" / "SKILL.md"
        orphan_path.parent.mkdir(parents=True, exist_ok=True)
        orphan_path.write_bytes(b"# unknown skill\n")

        report = verify(repo)

        assert ".agents/skills/spec-kitty.unknown/SKILL.md" in report.orphans

    def test_third_party_file_is_not_an_orphan(self, repo: Path) -> None:
        """Files in non-spec-kitty dirs must not appear in orphans."""
        third_party = repo / ".agents" / "skills" / "handwritten-review" / "SKILL.md"
        third_party.parent.mkdir(parents=True, exist_ok=True)
        third_party.write_bytes(b"# handwritten\n")

        report = verify(repo)

        assert report.orphans == [], f"Third-party file wrongly flagged as orphan: {report.orphans!r}"

    def test_installed_skill_is_not_orphan(self, repo: Path) -> None:
        install(repo, "vibe")
        report = verify(repo)

        assert report.orphans == []


# ---------------------------------------------------------------------------
# SUPPORTED_AGENTS and CANONICAL_COMMANDS shape
# ---------------------------------------------------------------------------


class TestConstants:
    def test_supported_agents_contains_codex_and_vibe(self) -> None:
        assert "codex" in SUPPORTED_AGENTS
        assert "vibe" in SUPPORTED_AGENTS

    def test_canonical_commands_count(self) -> None:
        # Was 12 before 3.2.0a5; checklist retired (FR-003 / FR-004 / #815).
        assert len(CANONICAL_COMMANDS) == 11

    def test_canonical_commands_excludes_checklist(self) -> None:
        # /spec-kitty.checklist was retired in 3.2.0a5 (#815, supersedes #635).
        assert "checklist" not in CANONICAL_COMMANDS

    def test_canonical_commands_no_duplicates(self) -> None:
        assert len(set(CANONICAL_COMMANDS)) == len(CANONICAL_COMMANDS)


# ---------------------------------------------------------------------------
# InstallerError unsupported_agent
# ---------------------------------------------------------------------------


class TestUnsupportedAgent:
    def test_install_raises_for_unknown_agent(self, repo: Path) -> None:
        with pytest.raises(InstallerError) as exc_info:
            install(repo, "unknown-agent")
        assert exc_info.value.code == "unsupported_agent"

    def test_install_raises_for_claude_agent(self, repo: Path) -> None:
        with pytest.raises(InstallerError) as exc_info:
            install(repo, "claude")
        assert exc_info.value.code == "unsupported_agent"


# ---------------------------------------------------------------------------
# Selective remove (FR-008) — intermediate state checks
# ---------------------------------------------------------------------------


class TestSelectiveRemove:
    def test_remove_codex_leaves_vibe_files_intact(self, repo: Path) -> None:
        install(repo, "codex")
        install(repo, "vibe")

        # Capture hashes before removing codex.
        hashes_before: dict[str, str] = {cmd: _sha256_file(_skill_path(repo, cmd)) for cmd in CANONICAL_COMMANDS}

        remove(repo, "codex")

        # Files must still exist and be byte-identical.
        for cmd in CANONICAL_COMMANDS:
            path = _skill_path(repo, cmd)
            assert path.exists(), f"File missing after remove(codex): {cmd}"
            assert _sha256_file(path) == hashes_before[cmd], f"File mutated during remove(codex): {cmd}"

    def test_remove_codex_updates_agents_in_manifest(self, repo: Path) -> None:
        install(repo, "codex")
        install(repo, "vibe")
        remove(repo, "codex")

        manifest = manifest_store.load(repo)
        for entry in manifest.entries:
            assert entry.agents == ("vibe",), f"Entry {entry.path!r}: expected agents==('vibe',), got {entry.agents!r}"

    def test_remove_report_deref_and_kept(self, repo: Path) -> None:
        install(repo, "codex")
        install(repo, "vibe")

        report = remove(repo, "codex")

        assert len(report.deref) == len(CANONICAL_COMMANDS)
        assert len(report.kept) == len(CANONICAL_COMMANDS)
        assert report.deleted == []

    def test_remove_last_agent_clears_all_entries(self, repo: Path) -> None:
        install(repo, "vibe")
        report = remove(repo, "vibe")

        assert len(report.deleted) == len(CANONICAL_COMMANDS)
        assert report.kept == []

        manifest = manifest_store.load(repo)
        assert manifest.entries == []
