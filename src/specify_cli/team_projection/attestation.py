"""Per-commit attestation manifest (§3.3 of the D1 contract draft).

The producer half of a two-repo protocol: D1 (this package, spec-kitty, no
provider credentials, no network) only names every artifact it wrote for the
current commit and that artifact's content hash. D4 (a different repo) is the
exclusive consumer that verifies a provider-native attestation against a
provider — D1 asserts nothing about a provider and calls no network endpoint
(§2.4, §3.6).

:func:`build_attestation_manifest` is a PURE builder — no filesystem writes.
``write.py`` is the package's sole file-writing entry point.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .mission_view import build_team_mission_snapshot
from .provenance import ExactCommitProvenance, capture_provenance
from .public_view import (
    is_public_projection_enabled,
    project_public_index,
    project_public_mission_snapshot,
)
from .team_index import build_team_index, resolve_feature_dir_for_mission_slug

_ArtifactKind = Literal[
    "team_index", "team_mission_snapshot", "public_index", "public_mission_snapshot"
]


class AttestationManifestEntry(BaseModel):
    """One row of the attestation manifest: one artifact D1 wrote (or, for a
    public row on an opted-out project, one artifact D1 deliberately did not
    write)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact: _ArtifactKind
    mission_slug: str | None  # None for the two index rows
    path: str  # repo-relative path, forward slashes
    present: bool  # False only for public_* rows when opt-out
    content_sha256: str | None  # None iff present is False


class AttestationManifest(BaseModel):
    """The closed per-commit manifest of artifact digests."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_: Literal["attestation_manifest/v1"] = Field(alias="schema")
    provenance: ExactCommitProvenance  # require_clean is forced True (§3.4)
    entries: tuple[AttestationManifestEntry, ...]


def _team_index_path() -> str:
    return ".kittify/derived/team-index.json"


def _team_snapshot_path(mission_slug: str) -> str:
    return f".kittify/derived/{mission_slug}/team-snapshot.json"


def _public_index_path() -> str:
    return ".kittify/derived/public/index.json"


def _public_snapshot_path(mission_slug: str) -> str:
    return f".kittify/derived/{mission_slug}/public/mission.json"


def build_attestation_manifest(project_dir: Path) -> AttestationManifest:
    """Build the closed, referentially-complete attestation manifest.

    Every ``build_*`` call this function makes uses ``require_clean=True``,
    so ``DirtyTreeError`` propagates from the FIRST such call
    (:func:`~specify_cli.team_projection.team_index.build_team_index`) before
    any other work happens — the manifest is the one artifact D1 refuses to
    produce on a dirty tree, and is all-or-nothing: never partially built
    (§3.4, §4 N10, N16). No filesystem write happens anywhere in this
    function; ``write.py`` is the sole writer.
    """
    team_index = build_team_index(project_dir, require_clean=True)

    entries: list[AttestationManifestEntry] = [
        AttestationManifestEntry(
            artifact="team_index",
            mission_slug=None,
            path=_team_index_path(),
            present=True,
            content_sha256=team_index.content_sha256,
        )
    ]

    team_snapshots = {}
    for entry in team_index.missions:
        feature_dir = resolve_feature_dir_for_mission_slug(project_dir, entry.mission_slug)
        snapshot = build_team_mission_snapshot(
            feature_dir, project_dir, require_clean=True
        )
        team_snapshots[entry.mission_slug] = snapshot
        entries.append(
            AttestationManifestEntry(
                artifact="team_mission_snapshot",
                mission_slug=entry.mission_slug,
                path=_team_snapshot_path(entry.mission_slug),
                present=True,
                content_sha256=snapshot.content_sha256,
            )
        )

    public_enabled = is_public_projection_enabled(project_dir)
    if public_enabled:
        public_index = project_public_index(team_index)
        entries.append(
            AttestationManifestEntry(
                artifact="public_index",
                mission_slug=None,
                path=_public_index_path(),
                present=True,
                content_sha256=public_index.content_sha256,
            )
        )
        for e in team_index.missions:
            public_snapshot = project_public_mission_snapshot(team_snapshots[e.mission_slug])
            entries.append(
                AttestationManifestEntry(
                    artifact="public_mission_snapshot",
                    mission_slug=e.mission_slug,
                    path=_public_snapshot_path(e.mission_slug),
                    present=True,
                    content_sha256=public_snapshot.content_sha256,
                )
            )
    else:
        entries.append(
            AttestationManifestEntry(
                artifact="public_index",
                mission_slug=None,
                path=_public_index_path(),
                present=False,
                content_sha256=None,
            )
        )
        for e in team_index.missions:
            entries.append(
                AttestationManifestEntry(
                    artifact="public_mission_snapshot",
                    mission_slug=e.mission_slug,
                    path=_public_snapshot_path(e.mission_slug),
                    present=False,
                    content_sha256=None,
                )
            )

    entries.sort(key=lambda e: (e.artifact, e.mission_slug or ""))

    provenance = capture_provenance(project_dir, require_clean=True)

    return AttestationManifest(
        schema="attestation_manifest/v1",
        provenance=provenance,
        entries=tuple(entries),
    )
