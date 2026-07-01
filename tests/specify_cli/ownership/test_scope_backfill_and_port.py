"""WP12 / #1757 acceptance tests — ATDD-first (charter C-011).

These prove the end-to-end #1757 scenario and the three sub-fixes:

  (T046-1, FR-028) Re-running ``backfill_ownership`` on an *already
      fully-backfilled* WP that has since gained ``scope: codebase-wide``
      persists the ``scope`` field instead of silently dropping it.

  (T046-2, FR-030) ``OwnershipManifest.from_frontmatter`` is symmetric for a
      present-but-``None`` ``authoritative_surface`` across the ``WPMetadata``
      and raw-``dict`` input shapes — both coerce to ``""``.

  (T046-3, FR-031) The resolve→validate path runs through the frontmatter-source
      port with plain stubs, with no mocking of ``read_wp_frontmatter`` and no
      temp files.

Authored RED on ``planning_base_branch`` (feat/execution-state-strangler)
before the T042–T045 implementation; the reviewer verifies red→green.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.frontmatter import FrontmatterManager
from specify_cli.migration.backfill_ownership import backfill_ownership
from specify_cli.ownership.models import (
    SCOPE_CODEBASE_WIDE,
    OwnershipManifest,
)
from specify_cli.status.wp_metadata import WPMetadata

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _read_frontmatter(wp_file: Path) -> dict:
    fm = FrontmatterManager()
    frontmatter, _ = fm.read(wp_file)
    return frontmatter


# ---------------------------------------------------------------------------
# T046-1 / FR-028 — backfill re-run persists scope on already-backfilled WP
# ---------------------------------------------------------------------------


class TestBackfillScopeAwareness:
    def test_rerun_persists_codebase_wide_scope(self, tmp_path: Path) -> None:
        """A WP that is already fully backfilled, then gains scope on disk,
        must have that scope preserved (not stripped) on the next run."""
        feature_dir = tmp_path / "kitty-specs" / "001-alpha"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        wp_file = tasks_dir / "WP01-audit.md"
        # Already fully backfilled (execution_mode + owned_files +
        # authoritative_surface present) AND a human has now added
        # scope: codebase-wide.
        wp_file.write_text(
            "---\n"
            "title: WP01 Audit\n"
            "dependencies: []\n"
            "execution_mode: code_change\n"
            "owned_files:\n"
            "- src/**\n"
            "authoritative_surface: src/\n"
            "scope: codebase-wide\n"
            "---\n\n"
            "Audit src/ across the whole tree.\n"
        )

        backfill_ownership(feature_dir, "001-alpha")

        frontmatter = _read_frontmatter(wp_file)
        assert frontmatter.get("scope") == SCOPE_CODEBASE_WIDE

    def test_rerun_does_not_invent_scope(self, tmp_path: Path) -> None:
        """Scope is human-authored only — backfill must never synthesise it."""
        feature_dir = tmp_path / "kitty-specs" / "001-alpha"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        wp_file = tasks_dir / "WP02-narrow.md"
        wp_file.write_text(
            "---\n"
            "title: WP02 Narrow\n"
            "dependencies: []\n"
            "---\n\n"
            "Implement src/specify_cli/foo.py\n"
        )

        backfill_ownership(feature_dir, "001-alpha")

        frontmatter = _read_frontmatter(wp_file)
        assert "scope" not in frontmatter


# ---------------------------------------------------------------------------
# T046-2 / FR-030 — from_frontmatter symmetry for authoritative_surface=None
# ---------------------------------------------------------------------------


class TestFromFrontmatterSymmetry:
    def test_none_authoritative_surface_symmetric(self) -> None:
        """``authoritative_surface: None`` must coerce to ``""`` for both the
        WPMetadata branch and the raw-dict branch."""
        meta = WPMetadata(
            work_package_id="WP01",
            title="t",
            execution_mode="code_change",
            owned_files=["src/foo/**"],
            authoritative_surface=None,
        )
        raw = {
            "execution_mode": "code_change",
            "owned_files": ["src/foo/**"],
            "authoritative_surface": None,
        }

        from_meta = OwnershipManifest.from_frontmatter(meta)
        from_dict = OwnershipManifest.from_frontmatter(raw)

        assert from_meta.authoritative_surface == ""
        assert from_dict.authoritative_surface == ""
        assert from_meta == from_dict


# ---------------------------------------------------------------------------
# T046-3 / FR-031 — resolve→validate runs through the port without reader mocks
# ---------------------------------------------------------------------------


class TestFrontmatterSourcePort:
    def test_resolve_then_validate_through_port(self) -> None:
        """The whole resolve→validate path is drivable with a plain in-memory
        source — no read_wp_frontmatter stubbing, no temp files."""
        from specify_cli.ownership.frontmatter_source import (
            InMemoryFrontmatterSource,
            resolve_wp_manifests,
        )
        from specify_cli.ownership.validation import validate_ownership

        meta_a = WPMetadata(
            work_package_id="WP01",
            title="a",
            execution_mode="code_change",
            owned_files=["src/foo/**"],
            authoritative_surface="src/foo/",
        )
        meta_b = WPMetadata(
            work_package_id="WP02",
            title="b",
            execution_mode="code_change",
            owned_files=["src/bar/**"],
            authoritative_surface="src/bar/",
        )
        source = InMemoryFrontmatterSource({"WP01": meta_a, "WP02": meta_b})

        manifests = resolve_wp_manifests(source)
        result = validate_ownership(manifests)

        assert set(manifests) == {"WP01", "WP02"}
        assert result.passed

    def test_codebase_wide_exemption_flows_through_port(self) -> None:
        """A codebase-wide WP carried through the port is exempt from overlap."""
        from specify_cli.ownership.frontmatter_source import (
            InMemoryFrontmatterSource,
            resolve_wp_manifests,
        )
        from specify_cli.ownership.validation import validate_ownership

        narrow = WPMetadata(
            work_package_id="WP01",
            title="narrow",
            execution_mode="code_change",
            owned_files=["src/foo/**"],
            authoritative_surface="src/foo/",
        )
        wide = WPMetadata(
            work_package_id="WP99",
            title="audit",
            execution_mode="code_change",
            owned_files=["src/**"],
            authoritative_surface="src/",
            scope=SCOPE_CODEBASE_WIDE,
        )
        source = InMemoryFrontmatterSource({"WP01": narrow, "WP99": wide})

        manifests = resolve_wp_manifests(source)

        assert manifests["WP99"].is_codebase_wide
        # Without the exemption these two would overlap (src/** ⊃ src/foo/**).
        assert validate_ownership(manifests).passed

    def test_disk_substitution_source_prefers_inmemory(self, tmp_path: Path) -> None:
        """The finalize source prefers an in-memory snapshot over disk, falling
        back to the reader only for WPs not held in memory."""
        from specify_cli.ownership.frontmatter_source import (
            FinalizeFrontmatterSource,
            resolve_wp_manifests,
        )

        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        # On disk WP01 declares a *stale* narrow surface; the in-memory snapshot
        # is authoritative and must win.
        disk_wp01 = tasks_dir / "WP01-foo.md"
        disk_wp01.write_text(
            "---\n"
            "work_package_id: WP01\n"
            "title: WP01\n"
            "dependencies: []\n"
            "execution_mode: code_change\n"
            "owned_files:\n"
            "- src/STALE/**\n"
            "authoritative_surface: src/STALE/\n"
            "---\n\nbody\n"
        )
        disk_wp02 = tasks_dir / "WP02-bar.md"
        disk_wp02.write_text(
            "---\n"
            "work_package_id: WP02\n"
            "title: WP02\n"
            "dependencies: []\n"
            "execution_mode: code_change\n"
            "owned_files:\n"
            "- src/bar/**\n"
            "authoritative_surface: src/bar/\n"
            "---\n\nbody\n"
        )

        fresh_wp01 = WPMetadata(
            work_package_id="WP01",
            title="WP01",
            execution_mode="code_change",
            owned_files=["src/foo/**"],
            authoritative_surface="src/foo/",
        )
        source = FinalizeFrontmatterSource(
            wp_files=[disk_wp01, disk_wp02],
            inmemory={"WP01": fresh_wp01},
        )

        manifests = resolve_wp_manifests(source)

        assert manifests["WP01"].owned_files == ("src/foo/**",)  # in-memory wins
        assert manifests["WP02"].owned_files == ("src/bar/**",)  # disk fallback
