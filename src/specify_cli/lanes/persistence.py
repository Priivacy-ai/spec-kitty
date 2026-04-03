"""Read and write lanes.json for a feature directory.

The lanes.json file lives at kitty-specs/{feature_slug}/lanes.json
and is the sole persistence location for lane assignments.
"""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.lanes.models import LanesManifest

LANES_FILENAME = "lanes.json"


def write_lanes_json(feature_dir: Path, manifest: LanesManifest) -> Path:
    """Write lanes.json to the feature directory.

    Args:
        feature_dir: Path to kitty-specs/{feature_slug}/.
        manifest: The LanesManifest to persist.

    Returns:
        Path to the written lanes.json file.
    """
    lanes_path = feature_dir / LANES_FILENAME
    lanes_path.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return lanes_path


def read_lanes_json(feature_dir: Path) -> LanesManifest | None:
    """Read lanes.json from the feature directory.

    Args:
        feature_dir: Path to kitty-specs/{feature_slug}/.

    Returns:
        A LanesManifest if the file exists and is valid, None otherwise.
    """
    lanes_path = feature_dir / LANES_FILENAME
    if not lanes_path.exists():
        return None
    try:
        data = json.loads(lanes_path.read_text(encoding="utf-8"))
        return LanesManifest.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
