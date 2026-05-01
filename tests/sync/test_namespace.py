"""Tests for specify_cli.sync.namespace module."""

from __future__ import annotations

import dataclasses
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from specify_cli.sync.namespace import (
    SUPPORTED_EXTENSIONS,
    NamespaceRef,
    SupportedInlineFormat,
    UploadOutcome,
    UploadStatus,
    is_supported_format,
    resolve_manifest_version,
)

pytestmark = pytest.mark.fast

# --- NamespaceRef ---


class TestNamespaceRef:
    def test_valid_construction(self) -> None:
        ns = NamespaceRef(
            project_uuid="abc-123",
            mission_slug="047-feature",
            target_branch="main",
            mission_type="software-dev",
            manifest_version="1",
        )
        assert ns.project_uuid == "abc-123"
        assert ns.mission_slug == "047-feature"
        assert ns.target_branch == "main"
        assert ns.mission_type == "software-dev"
        assert ns.manifest_version == "1"

    @pytest.mark.parametrize(
        "field",
        [
            "project_uuid",
            "mission_slug",
            "target_branch",
            "mission_type",
            "manifest_version",
        ],
    )
    def test_empty_field_raises(self, field: str) -> None:
        kwargs = {
            "project_uuid": "uuid",
            "mission_slug": "slug",
            "target_branch": "main",
            "mission_type": "software-dev",
            "manifest_version": "1",
        }
        kwargs[field] = ""
        with pytest.raises(ValueError, match=field):
            NamespaceRef(**kwargs)

    @pytest.mark.parametrize(
        "field",
        [
            "project_uuid",
            "mission_slug",
            "target_branch",
            "mission_type",
            "manifest_version",
        ],
    )
    def test_whitespace_only_field_raises(self, field: str) -> None:
        kwargs = {
            "project_uuid": "uuid",
            "mission_slug": "slug",
            "target_branch": "main",
            "mission_type": "software-dev",
            "manifest_version": "1",
        }
        kwargs[field] = "   "
        with pytest.raises(ValueError, match=field):
            NamespaceRef(**kwargs)

    def test_to_dict(self) -> None:
        ns = NamespaceRef(
            project_uuid="abc-123",
            mission_slug="047-feature",
            target_branch="2.x",
            mission_type="software-dev",
            manifest_version="2",
        )
        assert ns.to_dict() == {
            "project_uuid": "abc-123",
            "mission_slug": "047-feature",
            "target_branch": "2.x",
            "mission_type": "software-dev",
            "manifest_version": "2",
        }

    def test_dedupe_key(self) -> None:
        ns = NamespaceRef(
            project_uuid="uuid-1",
            mission_slug="feat",
            target_branch="main",
            mission_type="sw",
            manifest_version="1",
        )
        key = ns.dedupe_key("spec.md", "sha256abc")
        assert key == "uuid-1|feat|main|sw|1|spec.md|sha256abc"

    def test_dedupe_key_deterministic(self) -> None:
        ns = NamespaceRef(
            project_uuid="u",
            mission_slug="f",
            target_branch="b",
            mission_type="m",
            manifest_version="v",
        )
        assert ns.dedupe_key("a.md", "h1") == ns.dedupe_key("a.md", "h1")

    def test_frozen(self) -> None:
        ns = NamespaceRef(
            project_uuid="u",
            mission_slug="f",
            target_branch="b",
            mission_type="m",
            manifest_version="v",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            ns.project_uuid = "other"  # type: ignore[misc]


class TestNamespaceRefFromContext:
    def _make_identity(self, uuid_val: UUID | None = None) -> MagicMock:
        identity = MagicMock()
        identity.project_uuid = uuid_val
        return identity

    def test_valid_construction(self) -> None:
        identity = self._make_identity(UUID("12345678-1234-5678-1234-567812345678"))
        ns = NamespaceRef.from_context(
            identity=identity,
            mission_slug="047-feat",
            target_branch="main",
            mission_type="software-dev",
            manifest_version="1",
        )
        assert ns.project_uuid == "12345678-1234-5678-1234-567812345678"
        assert ns.mission_slug == "047-feat"

    def test_none_uuid_raises(self) -> None:
        identity = self._make_identity(None)
        with pytest.raises(ValueError, match="project_uuid is required"):
            NamespaceRef.from_context(
                identity=identity,
                mission_slug="feat",
                target_branch="main",
                mission_type="sw",
                manifest_version="1",
            )


class TestResolveManifestVersion:
    @patch("specify_cli.dossier.manifest.ManifestRegistry.load_manifest")
    def test_returns_manifest_version(self, mock_load: MagicMock) -> None:
        mock_manifest = MagicMock()
        mock_manifest.manifest_version = "3"
        mock_load.return_value = mock_manifest
        assert resolve_manifest_version("software-dev") == "3"
        mock_load.assert_called_once_with("software-dev")

    @patch("specify_cli.dossier.manifest.ManifestRegistry.load_manifest")
    def test_returns_default_when_none(self, mock_load: MagicMock) -> None:
        mock_load.return_value = None
        assert resolve_manifest_version("unknown-mission") == "1"


# --- SupportedInlineFormat ---


class TestSupportedInlineFormat:
    def test_supported_extensions_frozenset(self) -> None:
        assert isinstance(SUPPORTED_EXTENSIONS, frozenset)
        assert ".md" in SUPPORTED_EXTENSIONS
        assert ".json" in SUPPORTED_EXTENSIONS
        assert ".yaml" in SUPPORTED_EXTENSIONS
        assert ".yml" in SUPPORTED_EXTENSIONS
        assert ".csv" in SUPPORTED_EXTENSIONS

    def test_enum_values(self) -> None:
        assert SupportedInlineFormat.MARKDOWN == ".md"
        assert SupportedInlineFormat.JSON == ".json"
        assert SupportedInlineFormat.YAML == ".yaml"
        assert SupportedInlineFormat.YML == ".yml"
        assert SupportedInlineFormat.CSV == ".csv"

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("spec.md", True),
            ("data.json", True),
            ("config.yaml", True),
            ("config.yml", True),
            ("report.csv", True),
            ("image.png", False),
            ("binary.exe", False),
            ("archive.zip", False),
            ("README.MD", True),
            ("DATA.JSON", True),
        ],
    )
    def test_is_supported_format(self, path: str, expected: bool) -> None:
        assert is_supported_format(path) == expected

    def test_is_supported_format_with_path_object(self) -> None:
        from pathlib import Path

        assert is_supported_format(Path("docs/spec.md")) is True
        assert is_supported_format(Path("images/logo.png")) is False


# --- UploadOutcome ---


class TestUploadOutcome:
    def test_construction(self) -> None:
        outcome = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.UPLOADED,
            reason="201 stored",
            content_hash="sha256abc",
        )
        assert outcome.artifact_path == "spec.md"
        assert outcome.status == UploadStatus.UPLOADED
        assert outcome.reason == "201 stored"
        assert outcome.content_hash == "sha256abc"
        assert outcome.retryable is False

    @pytest.mark.parametrize("status", list(UploadStatus))
    def test_all_status_codes(self, status: UploadStatus) -> None:
        outcome = UploadOutcome(
            artifact_path="file.md",
            status=status,
            reason="test",
        )
        assert outcome.status == status

    def test_str_format(self) -> None:
        outcome = UploadOutcome(
            artifact_path="plan.md",
            status=UploadStatus.SKIPPED,
            reason="binary file",
        )
        assert str(outcome) == "plan.md: skipped (binary file)"

    def test_frozen(self) -> None:
        outcome = UploadOutcome(
            artifact_path="a.md",
            status=UploadStatus.FAILED,
            reason="err",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            outcome.artifact_path = "b.md"  # type: ignore[misc]

    def test_retryable_flag(self) -> None:
        outcome = UploadOutcome(
            artifact_path="a.md",
            status=UploadStatus.FAILED,
            reason="timeout",
            retryable=True,
        )
        assert outcome.retryable is True

    def test_content_hash_default_none(self) -> None:
        outcome = UploadOutcome(
            artifact_path="a.md",
            status=UploadStatus.QUEUED,
            reason="offline",
        )
        assert outcome.content_hash is None


class TestUploadStatus:
    def test_enum_values(self) -> None:
        assert UploadStatus.UPLOADED == "uploaded"
        assert UploadStatus.ALREADY_EXISTS == "already_exists"
        assert UploadStatus.QUEUED == "queued"
        assert UploadStatus.SKIPPED == "skipped"
        assert UploadStatus.FAILED == "failed"

    def test_five_members(self) -> None:
        assert len(UploadStatus) == 5
