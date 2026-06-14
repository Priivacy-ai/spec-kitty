"""Unit tests for ``tool_surface.profiles.manifest``."""

from __future__ import annotations

from pathlib import Path

from specify_cli.skills.manifest_store import fingerprint
from specify_cli.tool_surface.model import NativeAgentProfile
from specify_cli.tool_surface.profiles.manifest import (
    MANIFEST_FILENAME,
    ProfileManifest,
    hash_content,
    hash_file,
    manifest_path_for,
)


def _entry(slug: str, file_hash: str | None = "deadbeef") -> NativeAgentProfile:
    return NativeAgentProfile(
        profile_urn=f"agent_profile:{slug}",
        source_layer="builtin",
        tool_key="claude",
        output_path=Path(f"/project/.claude/agents/{slug}.md"),
        format="claude-agent",
        file_hash=file_hash,
    )


def test_manifest_filename_is_agent_profiles_manifest() -> None:
    assert MANIFEST_FILENAME == "agent-profiles-manifest.json"


def test_manifest_path_is_under_kittify(tmp_path: Path) -> None:
    path = manifest_path_for(tmp_path)
    assert path == tmp_path / ".kittify" / "agent-profiles-manifest.json"


def test_hash_content_matches_canonical_fingerprint() -> None:
    # The manifest must use the project's canonical SHA-256 routine, not a
    # reimplementation, so its digests interoperate with the installer/renderer.
    assert hash_content("hello") == fingerprint(b"hello")


def test_hash_file_matches_canonical_fingerprint(tmp_path: Path) -> None:
    f = tmp_path / "x.md"
    f.write_text("hello", encoding="utf-8")
    assert hash_file(f) == fingerprint(b"hello")


def test_record_and_get_hash(tmp_path: Path) -> None:
    manifest = ProfileManifest(manifest_path_for(tmp_path))
    entry = _entry("architect-alphonso", file_hash="abc123")
    manifest.record(entry)
    assert manifest.get_hash(entry.output_path) == "abc123"
    assert manifest.get_hash(Path("/nope.md")) is None


def test_remove_drops_entry(tmp_path: Path) -> None:
    manifest = ProfileManifest(manifest_path_for(tmp_path))
    entry = _entry("planner-priti")
    manifest.record(entry)
    manifest.remove(entry.output_path)
    assert manifest.get_hash(entry.output_path) is None
    # Removing an absent path is a no-op.
    manifest.remove(Path("/missing.md"))


def test_manifest_roundtrip(tmp_path: Path) -> None:
    manifest = ProfileManifest.load(tmp_path)
    manifest.record(_entry("architect-alphonso", file_hash="h1"))
    manifest.record(_entry("planner-priti", file_hash=None))
    manifest.save()

    reloaded = ProfileManifest.load(tmp_path)
    entries = reloaded.all_entries()
    assert [e.profile_urn for e in entries] == [
        "agent_profile:architect-alphonso",
        "agent_profile:planner-priti",
    ]
    assert reloaded.get_hash(Path("/project/.claude/agents/architect-alphonso.md")) == "h1"
    assert reloaded.get_hash(Path("/project/.claude/agents/planner-priti.md")) is None
    assert entries[0].format == "claude-agent"
    assert entries[0].tool_key == "claude"


def test_load_absent_manifest_is_empty(tmp_path: Path) -> None:
    manifest = ProfileManifest.load(tmp_path)
    assert manifest.all_entries() == []
