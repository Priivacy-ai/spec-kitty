"""The team/public projection package's sole file-writing entry point (§3.2).

Every other module in this package returns in-memory frozen Pydantic models
and touches no path under ``.kittify/derived/`` (``provenance.py`` shells to
``git`` but writes no file). This module backs the CLI command
``spec-kitty team-projection publish``.

Every build call this function makes uses ``require_clean=True`` — unlike
the default ``require_clean=False`` local/dashboard mode, a ``publish`` run
is always all-or-nothing on a clean tree (§3.4), because §4 N10 requires zero
files touched when the tree is dirty.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .attestation import AttestationManifest, build_attestation_manifest
from .mission_view import build_team_mission_snapshot
from .public_view import (
    is_public_projection_enabled,
    project_public_index,
    project_public_mission_snapshot,
)
from .team_index import build_team_index, resolve_feature_dir_for_mission_slug


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Write a JSON file atomically using a temp-file + os.replace.

    Reuses the exact primitive already reviewed at
    ``status/views.py:_atomic_write_json`` — ``sort_keys=True`` for
    byte-determinism, temp-file + ``os.replace`` so the file is always either
    the old version or the new version, never a partial write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    json_str = json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json_str, encoding="utf-8")
    os.replace(str(tmp_path), str(path))


def write_team_projection(project_dir: Path) -> AttestationManifest:
    """Build and write every D1 artifact for the current commit.

    Write order (each file atomic, per :func:`_atomic_write_json`):

    1. ``build_team_index(project_dir, require_clean=True)`` ->
       ``.kittify/derived/team-index.json``.
    2. ``build_team_mission_snapshot(feature_dir, ..., require_clean=True)``
       per mission, in ``sort_missions_for_display`` order (the order
       :meth:`TeamIndex.missions` is already in) ->
       ``.kittify/derived/<mission_slug>/team-snapshot.json``.
    3. ``is_public_projection_enabled(project_dir)`` is the one opt-in check
       point (§2.3, §3.3): if ``True``, project each team artifact to its
       public counterpart -> ``.kittify/derived/public/index.json`` +
       ``.kittify/derived/<mission_slug>/public/mission.json``; if ``False``,
       nothing under ``public/`` is written (§4 N4).
    4. ``build_attestation_manifest(project_dir)`` LAST, only after (1)-(3)
       completed without raising -> ``.kittify/derived/attestation-manifest.json``.
       A manifest that reaches disk is therefore proof every file it names
       was actually written by this same run (§4 N16).

    Any exception raised in (1)-(3) — including ``DirtyTreeError`` from the
    ``require_clean=True`` gate — propagates before (4) runs, so no manifest
    is ever written naming a file this run failed to produce. This function
    performs no rollback of a partially-written ``team-index.json``/
    ``team-snapshot.json`` from a failed attempt: none of those files is
    authoritative, and a retry simply overwrites them atomically (§3.5).
    """
    derived_dir = project_dir / ".kittify" / "derived"

    # (1) team index
    team_index = build_team_index(project_dir, require_clean=True)
    _atomic_write_json(
        derived_dir / "team-index.json",
        team_index.model_dump(mode="json", by_alias=True),
    )

    # (2) per-mission team snapshots, same order as the index.
    team_snapshots = {}
    for entry in team_index.missions:
        feature_dir = resolve_feature_dir_for_mission_slug(project_dir, entry.mission_slug)
        snapshot = build_team_mission_snapshot(
            feature_dir, project_dir, require_clean=True
        )
        team_snapshots[entry.mission_slug] = snapshot
        _atomic_write_json(
            derived_dir / entry.mission_slug / "team-snapshot.json",
            snapshot.model_dump(mode="json", by_alias=True),
        )

    # (3) public artifacts, iff explicitly opted in.
    if is_public_projection_enabled(project_dir):
        public_index = project_public_index(team_index)
        _atomic_write_json(
            derived_dir / "public" / "index.json",
            public_index.model_dump(mode="json", by_alias=True),
        )
        for entry in team_index.missions:
            public_snapshot = project_public_mission_snapshot(
                team_snapshots[entry.mission_slug]
            )
            _atomic_write_json(
                derived_dir / entry.mission_slug / "public" / "mission.json",
                public_snapshot.model_dump(mode="json", by_alias=True),
            )

    # (4) attestation manifest, LAST.
    manifest = build_attestation_manifest(project_dir)
    _atomic_write_json(
        derived_dir / "attestation-manifest.json",
        manifest.model_dump(mode="json", by_alias=True),
    )

    return manifest


__all__ = ["write_team_projection"]
