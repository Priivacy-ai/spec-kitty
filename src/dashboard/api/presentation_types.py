"""Dashboard-presentation-only API response types.

These TypedDicts are used exclusively by dashboard API routers for
presenting artifact directory listings to the frontend. They are
not part of any domain service and do not belong to the kernel or
specify_cli packages.

FR-016, FR-017.
"""
from __future__ import annotations

from typing import TypedDict


class ArtifactDirectoryFile(TypedDict):
    """Single file entry in an artifact directory listing."""

    name: str
    path: str
    icon: str


class ArtifactDirectoryResponse(TypedDict):
    """Response from ``/api/contracts/{id}`` and ``/api/checklists/{id}``."""

    files: list[ArtifactDirectoryFile]
