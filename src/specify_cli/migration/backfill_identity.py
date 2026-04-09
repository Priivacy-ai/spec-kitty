"""Assign immutable identity fields to all entities in a legacy project.

Three entry points:

- :func:`backfill_project_uuid` – write ``spec_kitty.project_uuid`` to
  ``.kittify/metadata.yaml``.
- :func:`backfill_mission_ids` – write ``mission_id`` to every feature
  ``meta.json`` under ``kitty-specs/``.
- :func:`backfill_wp_ids` – write ``work_package_id``, ``wp_code``, and
  ``mission_id`` to each WP frontmatter file under ``tasks/``.

All three functions are *idempotent*: if an ID already exists it is never
overwritten.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import ulid as _ulid_mod
from ruamel.yaml import YAML

logger = logging.getLogger(__name__)

# Pattern that matches WP filenames like "WP01-some-title.md" or "WP01.md"
_WP_CODE_RE = re.compile(r"^(WP\d{2,})")


def _generate_ulid() -> str:
    """Return a new ULID string, compatible with both ulid and python-ulid packages."""
    if hasattr(_ulid_mod, "new"):
        return str(_ulid_mod.new().str)
    return str(_ulid_mod.ULID())


def _make_yaml() -> YAML:
    """Return a ruamel.yaml instance configured for round-trip editing."""
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=2, sequence=2, offset=0)
    return y


def backfill_project_uuid(repo_root: Path) -> str:
    """Assign ``spec_kitty.project_uuid`` to ``.kittify/metadata.yaml``.

    If the field already exists the existing value is returned unchanged.

    Args:
        repo_root: Absolute path to the project root.

    Returns:
        The project UUID (ULID string), whether newly generated or pre-existing.

    Raises:
        FileNotFoundError: If ``.kittify/metadata.yaml`` does not exist.
    """
    metadata_path = repo_root / ".kittify" / "metadata.yaml"
    if not metadata_path.exists():
        raise FileNotFoundError(f"metadata.yaml not found: {metadata_path}")

    y = _make_yaml()
    with open(metadata_path, encoding="utf-8") as fh:
        data = y.load(fh)

    if data is None:
        data = {}

    spec_kitty: dict[str, Any] = data.setdefault("spec_kitty", {})

    if "project_uuid" in spec_kitty:
        existing: str = spec_kitty["project_uuid"]
        logger.debug("project_uuid already set: %s (skipping)", existing)
        return existing

    new_uuid = _generate_ulid()
    spec_kitty["project_uuid"] = new_uuid
    logger.info("Assigned project_uuid=%s", new_uuid)

    with open(metadata_path, "w", encoding="utf-8") as fh:
        y.dump(data, fh)

    return new_uuid


def backfill_mission_ids(repo_root: Path) -> dict[str, str]:
    """Assign ``mission_id`` to every feature ``meta.json`` under ``kitty-specs/``.

    Scans ``<repo_root>/kitty-specs/`` for directories that contain a
    ``meta.json`` file.  Each feature directory whose ``meta.json`` does not
    yet have a ``mission_id`` key receives a freshly generated ULID.

    Args:
        repo_root: Absolute path to the project root.

    Returns:
        Mapping of ``feature_slug → mission_id`` for every feature processed.
        Features that already had a ``mission_id`` appear in the mapping with
        their existing value.
    """
    kitty_specs = repo_root / "kitty-specs"
    mapping: dict[str, str] = {}

    if not kitty_specs.is_dir():
        logger.warning("kitty-specs/ not found at %s — no mission IDs backfilled", repo_root)
        return mapping

    for feature_dir in sorted(kitty_specs.iterdir()):
        if not feature_dir.is_dir():
            continue

        meta_path = feature_dir / "meta.json"
        if not meta_path.exists():
            logger.debug("Skipping %s (no meta.json)", feature_dir.name)
            continue

        with open(meta_path, encoding="utf-8") as fh:
            meta: dict[str, Any] = json.load(fh)

        if "mission_id" in meta:
            mapping[feature_dir.name] = meta["mission_id"]
            logger.debug("mission_id already set for %s: %s", feature_dir.name, meta["mission_id"])
            continue

        new_id = _generate_ulid()
        meta["mission_id"] = new_id
        mapping[feature_dir.name] = new_id
        logger.info("Assigned mission_id=%s to feature %s", new_id, feature_dir.name)

        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

    return mapping


def backfill_wp_ids(feature_dir: Path, mission_id: str) -> dict[str, str]:
    """Assign ``work_package_id``, ``wp_code``, and ``mission_id`` to each WP.

    Scans ``<feature_dir>/tasks/WP*.md`` for work-package frontmatter files.
    For each WP that does not already have a ``work_package_id``, a ULID is
    generated and written.  ``wp_code`` is derived from the filename (e.g.
    ``WP01-foo.md → "WP01"``).  ``mission_id`` is always written (it may
    already be correct but we set it explicitly for consistency).

    Uses the existing :class:`~specify_cli.frontmatter.FrontmatterManager` for
    round-trip-safe reading and writing.

    Args:
        feature_dir: Path to the feature directory (e.g. ``kitty-specs/057-…``).
        mission_id:  ULID string for the parent feature's ``mission_id``.

    Returns:
        Mapping of ``wp_code → work_package_id`` for every WP file found.
    """
    from specify_cli.frontmatter import FrontmatterManager

    tasks_dir = feature_dir / "tasks"
    mapping: dict[str, str] = {}

    if not tasks_dir.is_dir():
        logger.debug("No tasks/ directory in %s — skipping WP ID backfill", feature_dir.name)
        return mapping

    manager = FrontmatterManager()

    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        # Derive wp_code from filename
        m = _WP_CODE_RE.match(wp_file.stem)
        if not m:
            logger.warning("Cannot derive wp_code from filename %s — skipping", wp_file.name)
            continue
        wp_code = m.group(1)

        try:
            frontmatter, body = manager.read(wp_file)
        except Exception as exc:
            logger.warning("Cannot read frontmatter from %s: %s — skipping", wp_file.name, exc)
            continue

        updates: dict[str, Any] = {}

        # mission_id — always propagate
        if frontmatter.get("mission_id") != mission_id:  # MIGRATION-ONLY: raw dict read-mutate-write
            updates["mission_id"] = mission_id

        # wp_code — set if missing
        if "wp_code" not in frontmatter:
            updates["wp_code"] = wp_code

        # work_package_id — only generate if absent
        if "work_package_id" not in frontmatter:
            new_wp_id = _generate_ulid()
            updates["work_package_id"] = new_wp_id
            logger.info("Assigned work_package_id=%s to %s", new_wp_id, wp_file.name)
        else:
            logger.debug(
                "work_package_id already set for %s: %s",
                wp_file.name,
                frontmatter["work_package_id"],
            )

        if updates:
            frontmatter.update(updates)
            manager.write(wp_file, frontmatter, body)

        mapping[wp_code] = frontmatter.get("work_package_id") or updates.get("work_package_id", "")  # MIGRATION-ONLY: raw dict read-mutate-write

    return mapping
