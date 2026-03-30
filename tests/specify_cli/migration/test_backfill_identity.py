"""Tests for migration/backfill_identity.py — Subtask T060.

Covers:
- T060-1: backfill_project_uuid assigns a ULID to metadata.yaml
- T060-2: backfill_project_uuid is idempotent (existing UUID not overwritten)
- T060-3: backfill_mission_ids assigns ULIDs to feature meta.json files
- T060-4: backfill_mission_ids is idempotent (existing IDs not overwritten)
- T060-5: backfill_wp_ids assigns work_package_id, wp_code, mission_id
- T060-6: backfill_wp_ids is idempotent (existing work_package_id not overwritten)
- T060-7: IDs are valid ULIDs (26-char Crockford base32 uppercase)
- T060-8: backfill_project_uuid raises FileNotFoundError if metadata.yaml missing
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from specify_cli.migration.backfill_identity import (
    backfill_mission_ids,
    backfill_project_uuid,
    backfill_wp_ids,
)

# ULID pattern: 26 chars, Crockford base32 (0-9A-HJKMNP-TV-Z), case-insensitive at read
_ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$", re.IGNORECASE)


def _is_ulid(value: str) -> bool:
    return bool(_ULID_RE.match(value))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_metadata(tmp_path: Path, extra: dict | None = None) -> Path:
    """Write a minimal .kittify/metadata.yaml."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    data: dict = {
        "spec_kitty": {
            "version": "2.1.0",
            "initialized_at": "2026-01-01T00:00:00",
        }
    }
    if extra:
        data["spec_kitty"].update(extra)
    path = kittify / "metadata.yaml"
    with open(path, "w") as fh:
        yaml.dump(data, fh)
    return path


def _make_feature(tmp_path: Path, slug: str, wps: list[str] | None = None) -> Path:
    """Create a feature directory with meta.json and optional WP files."""
    feature_dir = tmp_path / "kitty-specs" / slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    meta = {"feature_slug": slug, "title": f"Feature {slug}"}
    with open(feature_dir / "meta.json", "w") as fh:
        json.dump(meta, fh, indent=2)

    for wp_name in (wps or []):
        wp_file = tasks_dir / f"{wp_name}.md"
        wp_file.write_text(
            f"---\ntitle: {wp_name} Title\ndependencies: []\n---\n\n# {wp_name} body\n"
        )

    return feature_dir


# ---------------------------------------------------------------------------
# backfill_project_uuid
# ---------------------------------------------------------------------------


class TestBackfillProjectUuid:
    def test_assigns_ulid(self, tmp_path: Path) -> None:
        """T060-1: A new project_uuid is written to metadata.yaml."""
        _write_metadata(tmp_path)
        uuid = backfill_project_uuid(tmp_path)
        assert _is_ulid(uuid), f"Expected ULID, got: {uuid!r}"

        # Verify it is persisted
        path = tmp_path / ".kittify" / "metadata.yaml"
        with open(path) as fh:
            data = yaml.safe_load(fh)
        assert data["spec_kitty"]["project_uuid"] == uuid

    def test_idempotent(self, tmp_path: Path) -> None:
        """T060-2: Calling backfill_project_uuid twice returns the same value."""
        _write_metadata(tmp_path)
        uuid1 = backfill_project_uuid(tmp_path)
        uuid2 = backfill_project_uuid(tmp_path)
        assert uuid1 == uuid2

    def test_preserves_existing_uuid(self, tmp_path: Path) -> None:
        """T060-2: An existing project_uuid is never overwritten."""
        existing = "01KMRDJQG1Q6CYS7XTTWRHZS3Z"  # fake but valid-looking ULID
        _write_metadata(tmp_path, extra={"project_uuid": existing})
        returned = backfill_project_uuid(tmp_path)
        assert returned == existing

        path = tmp_path / ".kittify" / "metadata.yaml"
        with open(path) as fh:
            data = yaml.safe_load(fh)
        assert data["spec_kitty"]["project_uuid"] == existing

    def test_raises_if_metadata_missing(self, tmp_path: Path) -> None:
        """T060-8: FileNotFoundError when metadata.yaml does not exist."""
        with pytest.raises(FileNotFoundError, match="metadata.yaml not found"):
            backfill_project_uuid(tmp_path)


# ---------------------------------------------------------------------------
# backfill_mission_ids
# ---------------------------------------------------------------------------


class TestBackfillMissionIds:
    def test_assigns_mission_id(self, tmp_path: Path) -> None:
        """T060-3: mission_id is written to each feature's meta.json."""
        _make_feature(tmp_path, "001-alpha")
        _make_feature(tmp_path, "002-beta")

        mapping = backfill_mission_ids(tmp_path)

        assert "001-alpha" in mapping
        assert "002-beta" in mapping
        assert _is_ulid(mapping["001-alpha"]), f"Not a ULID: {mapping['001-alpha']}"
        assert _is_ulid(mapping["002-beta"]), f"Not a ULID: {mapping['002-beta']}"

    def test_persisted_to_disk(self, tmp_path: Path) -> None:
        """T060-3: mission_id is persisted to meta.json."""
        _make_feature(tmp_path, "001-alpha")
        mapping = backfill_mission_ids(tmp_path)

        with open(tmp_path / "kitty-specs" / "001-alpha" / "meta.json") as fh:
            meta = json.load(fh)
        assert meta["mission_id"] == mapping["001-alpha"]

    def test_idempotent(self, tmp_path: Path) -> None:
        """T060-4: Existing mission_ids are never overwritten."""
        _make_feature(tmp_path, "001-alpha")
        mapping1 = backfill_mission_ids(tmp_path)
        mapping2 = backfill_mission_ids(tmp_path)
        assert mapping1["001-alpha"] == mapping2["001-alpha"]

    def test_preserves_existing_mission_id(self, tmp_path: Path) -> None:
        """T060-4: Pre-existing mission_id is returned unchanged."""
        feature_dir = _make_feature(tmp_path, "001-alpha")
        existing_id = "01EXISTING00000000000000000"
        with open(feature_dir / "meta.json") as fh:
            meta = json.load(fh)
        meta["mission_id"] = existing_id
        with open(feature_dir / "meta.json", "w") as fh:
            json.dump(meta, fh, indent=2)

        mapping = backfill_mission_ids(tmp_path)
        assert mapping["001-alpha"] == existing_id

    def test_no_kitty_specs(self, tmp_path: Path) -> None:
        """Returns empty dict when kitty-specs/ does not exist."""
        mapping = backfill_mission_ids(tmp_path)
        assert mapping == {}

    def test_skips_dirs_without_meta_json(self, tmp_path: Path) -> None:
        """Directories without meta.json are silently skipped."""
        # Create a dir without meta.json
        (tmp_path / "kitty-specs" / "no-meta").mkdir(parents=True)
        mapping = backfill_mission_ids(tmp_path)
        assert "no-meta" not in mapping


# ---------------------------------------------------------------------------
# backfill_wp_ids
# ---------------------------------------------------------------------------


class TestBackfillWpIds:
    def test_assigns_wp_ids(self, tmp_path: Path) -> None:
        """T060-5: work_package_id, wp_code, mission_id are written to each WP."""
        feature_dir = _make_feature(
            tmp_path, "001-alpha", wps=["WP01-core", "WP02-extras"]
        )
        mission_id = "01MISSION000000000000000000"

        mapping = backfill_wp_ids(feature_dir, mission_id)

        assert "WP01" in mapping
        assert "WP02" in mapping
        assert _is_ulid(mapping["WP01"]), f"Not a ULID: {mapping['WP01']}"
        assert _is_ulid(mapping["WP02"]), f"Not a ULID: {mapping['WP02']}"

    def test_wp_code_and_mission_id_written(self, tmp_path: Path) -> None:
        """T060-5: wp_code and mission_id appear in frontmatter."""
        feature_dir = _make_feature(tmp_path, "001-alpha", wps=["WP01-core"])
        mission_id = "01MISSION000000000000000000"
        backfill_wp_ids(feature_dir, mission_id)

        from specify_cli.frontmatter import FrontmatterManager
        fm = FrontmatterManager()
        frontmatter, _ = fm.read(feature_dir / "tasks" / "WP01-core.md")
        assert frontmatter["wp_code"] == "WP01"
        assert frontmatter["mission_id"] == mission_id
        assert _is_ulid(frontmatter["work_package_id"])

    def test_idempotent_work_package_id(self, tmp_path: Path) -> None:
        """T060-6: Existing work_package_id is not overwritten."""
        feature_dir = _make_feature(tmp_path, "001-alpha", wps=["WP01-core"])
        mission_id = "01MISSION000000000000000000"
        mapping1 = backfill_wp_ids(feature_dir, mission_id)
        mapping2 = backfill_wp_ids(feature_dir, mission_id)
        assert mapping1["WP01"] == mapping2["WP01"]

    def test_no_tasks_dir(self, tmp_path: Path) -> None:
        """Returns empty dict when tasks/ does not exist."""
        feature_dir = tmp_path / "kitty-specs" / "001-alpha"
        feature_dir.mkdir(parents=True)
        mapping = backfill_wp_ids(feature_dir, "01MISSION000000000000000000")
        assert mapping == {}

    def test_body_preserved(self, tmp_path: Path) -> None:
        """Body content after frontmatter is preserved byte-for-byte."""
        feature_dir = _make_feature(tmp_path, "001-alpha", wps=["WP01-core"])
        wp_file = feature_dir / "tasks" / "WP01-core.md"

        # Read original body
        original_content = wp_file.read_text()
        # The body is after the closing ---
        parts = original_content.split("---\n", 2)
        original_body = parts[2] if len(parts) == 3 else ""

        backfill_wp_ids(feature_dir, "01MISSION000000000000000000")

        # Read new content
        new_content = wp_file.read_text()
        new_parts = new_content.split("---\n", 2)
        new_body = new_parts[2] if len(new_parts) == 3 else ""

        assert new_body == original_body

    def test_ids_are_unique(self, tmp_path: Path) -> None:
        """T060-7: Each WP receives a distinct ULID."""
        feature_dir = _make_feature(
            tmp_path, "001-alpha", wps=["WP01", "WP02", "WP03"]
        )
        mapping = backfill_wp_ids(feature_dir, "01MISSION000000000000000000")
        ids = list(mapping.values())
        assert len(set(ids)) == len(ids), "Duplicate ULIDs assigned"
