"""Contract tests for the atomic-write snapshot helper."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml

from specify_cli.doctrine.snapshot import write_pack_manifest, write_snapshot
from specify_cli.doctrine.sources.protocol import FetchResult


import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]

@dataclass
class _ScriptedSource:
    """Test double implementing the OrgDoctrineSource protocol structurally."""

    layout: Callable[[Path], None]
    result: FetchResult
    url: str = "https://example.com/pack.tar.gz"

    def fetch(self, target_dir: Path) -> FetchResult:
        target_dir.mkdir(parents=True, exist_ok=True)
        self.layout(target_dir)
        return self.result


def _populate_valid_pack(target_dir: Path) -> None:
    directives = target_dir / "directives"
    directives.mkdir(parents=True, exist_ok=True)
    (directives / "sec-001.directive.yaml").write_text("id: sec-001\n")
    agents = target_dir / "agent_profiles"
    agents.mkdir(parents=True, exist_ok=True)
    (agents / "eng.agent.yaml").write_text("id: eng\n")


class TestWriteSnapshot:
    def test_atomic_write_success(self, tmp_path: Path) -> None:
        local_path = tmp_path / "doctrine"
        source = _ScriptedSource(
            layout=_populate_valid_pack,
            result=FetchResult(
                ok=True, artifacts_written=2, pack_version="v1.0.0"
            ),
        )

        result = write_snapshot(source, local_path)

        assert result.ok is True
        assert (local_path / "directives" / "sec-001.directive.yaml").is_file()
        # No leftover staging directory.
        leftover = list(tmp_path.glob(".tmp-*"))
        assert leftover == []
        # Manifest written.
        assert (local_path / "pack-manifest.yaml").is_file()

    def test_atomic_write_fetch_failure_preserves_existing(
        self, tmp_path: Path
    ) -> None:
        local_path = tmp_path / "doctrine"
        # Pre-existing snapshot must remain unchanged on failure.
        _populate_valid_pack(local_path)
        (local_path / "marker").write_text("keep-me\n")

        def _broken_layout(target_dir: Path) -> None:
            # Source writes nothing useful before declaring failure.
            target_dir.mkdir(parents=True, exist_ok=True)

        source = _ScriptedSource(
            layout=_broken_layout,
            result=FetchResult(
                ok=False,
                artifacts_written=0,
                pack_version=None,
                errors=["network down"],
            ),
        )

        result = write_snapshot(source, local_path)

        assert result.ok is False
        assert (local_path / "marker").read_text() == "keep-me\n"
        # Staging dir cleaned up.
        leftover = list(tmp_path.glob(".tmp-*"))
        assert leftover == []

    def test_atomic_write_replaces_existing(self, tmp_path: Path) -> None:
        local_path = tmp_path / "doctrine"
        _populate_valid_pack(local_path)
        # Stale file from the previous snapshot must not survive replace.
        (local_path / "stale.txt").write_text("old\n")

        def _new_layout(target_dir: Path) -> None:
            directives = target_dir / "directives"
            directives.mkdir(parents=True, exist_ok=True)
            (directives / "new.directive.yaml").write_text("id: new\n")

        source = _ScriptedSource(
            layout=_new_layout,
            result=FetchResult(ok=True, artifacts_written=1, pack_version="v2"),
        )

        result = write_snapshot(source, local_path)

        assert result.ok is True
        assert (local_path / "directives" / "new.directive.yaml").is_file()
        assert not (local_path / "stale.txt").exists()

    def test_replace_failure_restores_existing_snapshot(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        local_path = tmp_path / "doctrine"
        _populate_valid_pack(local_path)
        (local_path / "marker").write_text("keep-me\n")

        source = _ScriptedSource(
            layout=_populate_valid_pack,
            result=FetchResult(ok=True, artifacts_written=2, pack_version="v2"),
        )

        original_replace = Path.replace

        def _flaky_replace(self: Path, target: Path) -> Path:
            if self.name.startswith(".tmp-"):
                raise OSError("promote failed")
            return original_replace(self, target)

        monkeypatch.setattr(Path, "replace", _flaky_replace)

        result = write_snapshot(source, local_path)

        assert result.ok is False
        assert "promote failed" in " ".join(result.errors)
        assert (local_path / "marker").read_text() == "keep-me\n"
        assert not list(tmp_path.glob(".tmp-*"))
        assert not list(tmp_path.glob(".old-*"))

    def test_empty_snapshot_rejected(self, tmp_path: Path) -> None:
        local_path = tmp_path / "doctrine"

        def _empty_layout(target_dir: Path) -> None:
            # Source claims success but writes no recognised artifact dirs.
            (target_dir / "random.txt").write_text("noise\n")

        source = _ScriptedSource(
            layout=_empty_layout,
            result=FetchResult(ok=True, artifacts_written=0, pack_version=None),
        )

        result = write_snapshot(source, local_path)

        assert result.ok is False
        assert any("No artifact directories" in err for err in result.errors)
        # local_path was never populated.
        assert not local_path.exists()


class TestPackManifest:
    def test_manifest_contains_required_fields(self, tmp_path: Path) -> None:
        local_path = tmp_path / "doctrine"
        _populate_valid_pack(local_path)

        write_pack_manifest(
            local_path,
            FetchResult(ok=True, artifacts_written=2, pack_version="v1.2.0"),
            source_url="https://example.com/pack.tar.gz",
            source_type="https",
        )

        manifest = yaml.safe_load(
            (local_path / "pack-manifest.yaml").read_text()
        )
        assert manifest["pack_version"] == "v1.2.0"
        assert manifest["source_type"] == "https"
        assert manifest["source_url"] == "https://example.com/pack.tar.gz"
        assert manifest["artifact_counts"]["directives"] == 1
        assert manifest["artifact_counts"]["agent_profiles"] == 1
        # fetched_at is a Z-suffixed UTC timestamp.
        assert manifest["fetched_at"].endswith("Z")

    def test_manifest_strips_credentials(self, tmp_path: Path) -> None:
        local_path = tmp_path / "doctrine"
        _populate_valid_pack(local_path)

        write_pack_manifest(
            local_path,
            FetchResult(ok=True, artifacts_written=2, pack_version="v1"),
            source_url="https://oauth2:secret@example.com/pack.tar.gz",
            source_type="https",
        )

        manifest = yaml.safe_load(
            (local_path / "pack-manifest.yaml").read_text()
        )
        assert "secret" not in manifest["source_url"]
        assert manifest["source_url"] == "https://example.com/pack.tar.gz"
