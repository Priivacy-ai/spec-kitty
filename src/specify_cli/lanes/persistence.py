"""Read and write lanes.json for a feature directory.

The lanes.json file lives at kitty-specs/{feature_slug}/lanes.json
and is the sole persistence location for lane assignments.

Read is fail-closed: a corrupt or malformed lanes.json raises
CorruptLanesError rather than silently falling back to no-lanes mode.
Write uses atomic rename to prevent truncated files.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from specify_cli.lanes.models import LanesManifest

LANES_FILENAME = "lanes.json"


class CorruptLanesError(Exception):
    """Raised when lanes.json exists but cannot be parsed."""


def write_lanes_json(feature_dir: Path, manifest: LanesManifest) -> Path:
    """Write lanes.json atomically to the feature directory.

    Uses write-to-temp + rename to prevent truncated files on crash.

    Args:
        feature_dir: Path to kitty-specs/{feature_slug}/.
        manifest: The LanesManifest to persist.

    Returns:
        Path to the written lanes.json file.
    """
    lanes_path = feature_dir / LANES_FILENAME
    content = json.dumps(manifest.to_dict(), indent=2, sort_keys=False) + "\n"

    fd, tmp_path = tempfile.mkstemp(
        dir=str(feature_dir), prefix=".lanes-", suffix=".tmp"
    )
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        os.replace(tmp_path, str(lanes_path))
    except BaseException:
        os.close(fd) if not os.get_inheritable(fd) else None  # noqa: E501
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return lanes_path


def read_lanes_json(feature_dir: Path) -> LanesManifest | None:
    """Read lanes.json from the feature directory.

    Returns None only when the file does not exist (no lanes computed).
    Raises CorruptLanesError if the file exists but is malformed — this
    prevents silent fallback to legacy no-lanes mode.

    Args:
        feature_dir: Path to kitty-specs/{feature_slug}/.

    Returns:
        A LanesManifest if the file exists, None if absent.

    Raises:
        CorruptLanesError: If the file exists but cannot be parsed.
    """
    lanes_path = feature_dir / LANES_FILENAME
    if not lanes_path.exists():
        return None
    try:
        data = json.loads(lanes_path.read_text(encoding="utf-8"))
        return LanesManifest.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise CorruptLanesError(
            f"lanes.json at {lanes_path} is corrupt or malformed: {exc}"
        ) from exc
