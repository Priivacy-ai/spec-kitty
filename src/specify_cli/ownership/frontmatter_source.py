"""Frontmatter-source port for ownership resolve→validate (FR-031, epic #1666).

The pure seam :func:`specify_cli.ownership.validation.build_wp_manifests` turns a
``Mapping[str, WPMetadata]`` into ownership manifests. Historically the finalize
caller owned the *acquisition* of that mapping inline — disk reads via
``read_wp_frontmatter`` plus the in-memory (``_inmemory_frontmatter``)
substitution that validate-only mode requires — so the whole resolve→validate
path could only be exercised by stubbing the reader or writing temp files.

This module introduces a single owning port: a :class:`FrontmatterSource`
supplies WP frontmatter, and :func:`resolve_wp_manifests` drives it through the
pure seam. Tests can construct an :class:`InMemoryFrontmatterSource` from plain
``WPMetadata`` stubs and run the full overlap/exemption decision with no reader
mocking and no filesystem. The finalize command routes through
:class:`FinalizeFrontmatterSource`, which preserves the existing
prefer-in-memory-then-disk behavior (behavior-preserving refactor, NFR-003).
"""

from __future__ import annotations

import contextlib
import re
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from specify_cli.ownership.models import OwnershipManifest
from specify_cli.ownership.validation import build_wp_manifests

if TYPE_CHECKING:
    from collections.abc import Mapping

    from specify_cli.status import WPMetadata

__all__ = [
    "FrontmatterSource",
    "InMemoryFrontmatterSource",
    "FinalizeFrontmatterSource",
    "resolve_wp_manifests",
]

_WP_ID_RE = re.compile(r"^(WP\d{2})(?:[-_.]|$)")


class FrontmatterSource(Protocol):
    """Supplies WP frontmatter keyed by WP id, ready for manifest resolution."""

    def frontmatters(self) -> Mapping[str, WPMetadata]:
        """Return a mapping of WP id (e.g. ``"WP01"``) to its ``WPMetadata``."""
        ...


class InMemoryFrontmatterSource:
    """Frontmatter source backed entirely by an in-memory mapping.

    Intended for tests and any caller that already holds resolved
    ``WPMetadata`` — no disk access, no reader stubbing.
    """

    def __init__(self, frontmatters: Mapping[str, WPMetadata]) -> None:
        self._frontmatters: dict[str, WPMetadata] = dict(frontmatters)

    def frontmatters(self) -> Mapping[str, WPMetadata]:
        return self._frontmatters


class FinalizeFrontmatterSource:
    """Finalize-time source: in-memory snapshots win, disk is the fallback.

    Mirrors the finalize-tasks ownership block: validate-only mode bootstraps
    frontmatter in memory without writing to disk, so any WP present in
    ``inmemory`` must use that snapshot; WPs absent from it are read from disk
    via ``read_wp_frontmatter``. WPs with unreadable frontmatter are skipped,
    preserving the existing ``contextlib.suppress(Exception)`` behavior.
    """

    def __init__(
        self,
        wp_files: list[Path],
        inmemory: Mapping[str, WPMetadata],
    ) -> None:
        self._wp_files = list(wp_files)
        self._inmemory: dict[str, WPMetadata] = dict(inmemory)

    def frontmatters(self) -> Mapping[str, WPMetadata]:
        from specify_cli.status import read_wp_frontmatter

        resolved: dict[str, WPMetadata] = {}
        for wp_file in self._wp_files:
            match = _WP_ID_RE.match(wp_file.name)
            if not match:
                continue
            wp_id = match.group(1)
            with contextlib.suppress(Exception):  # Skip unreadable frontmatter
                if wp_id in self._inmemory:
                    resolved[wp_id] = self._inmemory[wp_id]
                else:
                    meta, _body = read_wp_frontmatter(wp_file)
                    resolved[wp_id] = meta
        return resolved


def resolve_wp_manifests(source: FrontmatterSource) -> dict[str, OwnershipManifest]:
    """Resolve ownership manifests from a frontmatter source.

    This is the one entry point that joins frontmatter acquisition (the port)
    to the pure validation seam, so the full resolve→validate path is testable
    end-to-end with a plain stub source.

    Args:
        source: A :class:`FrontmatterSource` supplying WP frontmatter.

    Returns:
        Mapping of WP id to ``OwnershipManifest`` for WPs that declare ownership.
    """
    return build_wp_manifests(source.frontmatters())
