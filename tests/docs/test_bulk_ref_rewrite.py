"""WP08 — contract tests for the occurrence-map-driven bulk reference rewriter.

Mission B (*Common Docs Structural Move*, ``01KW3SBK``), IC-05b.  These tests
drive the real rewriter (``scripts/docs/bulk_ref_rewrite.py``) against a
synthetic repo so the four load-bearing invariants are pinned to observable
behaviour, not implementation details:

1. a ``moves:`` prefix **is** rewritten (and to the *real* landed destination);
2. a ``kitty-specs/`` reference is **left untouched** (immutable snapshot);
3. a ``do_not_change``-category literal (import path, serialized ``toc.yml``
   href, markdown frontmatter field) is **left untouched**;
4. the run is **idempotent** — a second pass rewrites nothing.

Plus the incremental-safety guard (a move whose ``from`` still exists on disk is
skipped) and the subdir/rename landing-resolution that the coarse map ``to:``
cannot express.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.docs.bulk_ref_rewrite import (  # noqa: E402
    build_substitutions,
    load_moves,
    resolve_destination,
    run,
    split_frontmatter,
)

pytestmark = pytest.mark.fast


_OCCURRENCE_MAP = """\
target:
  term: "architecture/"
  replacement: "docs/"
  operation: rename
moves:
  - from: ["architecture/3.x/adr"]
    to: docs/adr/3.x
    reason: "Era ADRs -> docs/adr/3.x (flattened landing)."
  - from: ["architecture/audits"]
    to: docs/architecture
    reason: "Audits -> docs/architecture (subdir preserved on landing)."
  - from: ["glossary/contexts"]
    to: docs/context
    reason: "Glossary -> docs/context (flattened)."
  - from: ["docs/engineering_notes"]
    to: docs/plans
    reason: "Engineering notes -> docs/plans/engineering-notes (renamed)."
  - from: ["architecture/2.x/README.md"]
    to: docs/architecture
    reason: "Per-era README -> README-<era>.md (disambiguated)."
  - from: ["docs/development"]
    to: docs/operations
    reason: "Re-section NOT yet landed in this fixture (from still exists)."
  - from: ["CHANGELOG.md"]
    to: docs/changelog
    kind: relocate-with-alias
    reason: "Root alias persists -> skipped by SKIP_MOVE_FROMS."
"""


def _build_fixture_repo(root: Path) -> Path:
    """Lay out a synthetic post-move tree + the occurrence map; return map path."""

    occ_map = root / "kitty-specs" / "mission" / "occurrence_map.yaml"
    occ_map.parent.mkdir(parents=True, exist_ok=True)
    occ_map.write_text(_OCCURRENCE_MAP, encoding="utf-8")

    # New (landed) homes — `from`-exists guard relies on the OLD dirs being gone.
    for landed in (
        "docs/adr/3.x",
        "docs/architecture/audits",  # subdir preserved
        "docs/context",
        "docs/plans/engineering-notes",  # renamed _ -> -
        "docs/development",  # OLD home still present -> move NOT landed -> skip
    ):
        (root / landed).mkdir(parents=True, exist_ok=True)
    (root / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    (root / "docs/architecture/README-2.x.md").write_text("era readme\n", encoding="utf-8")

    return occ_map


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------- #
# (1) a moves: prefix IS rewritten — to the real landed destination
# --------------------------------------------------------------------------- #


class TestMovesPrefixRewritten:
    def test_flattened_dir_prefix_rewritten(self, tmp_path: Path) -> None:
        occ = _build_fixture_repo(tmp_path)
        src = tmp_path / "src" / "mod.py"
        _write(src, 'DOC = "architecture/3.x/adr/2026-01-01-1-x.md"\n')
        run(tmp_path, occ, roots=("src",), include_root_md=False)
        assert 'docs/adr/3.x/2026-01-01-1-x.md' in src.read_text()
        assert "architecture/3.x/adr" not in src.read_text()

    def test_subdir_preserving_landing_resolved(self, tmp_path: Path) -> None:
        """architecture/audits -> docs/architecture/audits (subdir kept), not flattened."""
        occ = _build_fixture_repo(tmp_path)
        page = tmp_path / "docs" / "guide.md"
        _write(page, "See [audit](architecture/audits/2026-05-x.md).\n")
        run(tmp_path, occ, roots=("docs",), include_root_md=False)
        assert "docs/architecture/audits/2026-05-x.md" in page.read_text()

    def test_relative_parent_reference_rewritten(self, tmp_path: Path) -> None:
        occ = _build_fixture_repo(tmp_path)
        page = tmp_path / "docs" / "sub" / "p.md"
        _write(page, "[x](../../architecture/3.x/adr/y.md)\n")
        run(tmp_path, occ, roots=("docs",), include_root_md=False)
        assert "../../docs/adr/3.x/y.md" in page.read_text()

    def test_renamed_landing_underscore_to_dash(self, tmp_path: Path) -> None:
        occ = _build_fixture_repo(tmp_path)
        page = tmp_path / "docs" / "p.md"
        _write(page, "see docs/engineering_notes/note.md\n")
        run(tmp_path, occ, roots=("docs",), include_root_md=False)
        assert "docs/plans/engineering-notes/note.md" in page.read_text()

    def test_per_era_readme_disambiguation_override(self, tmp_path: Path) -> None:
        occ = _build_fixture_repo(tmp_path)
        page = tmp_path / "docs" / "p.md"
        _write(page, "old root: architecture/2.x/README.md\n")
        run(tmp_path, occ, roots=("docs",), include_root_md=False)
        assert "docs/architecture/README-2.x.md" in page.read_text()


# --------------------------------------------------------------------------- #
# (2) a kitty-specs/ reference is left untouched
# --------------------------------------------------------------------------- #


def test_kitty_specs_reference_untouched(tmp_path: Path) -> None:
    occ = _build_fixture_repo(tmp_path)
    snapshot = tmp_path / "kitty-specs" / "old-mission" / "notes.md"
    body = "Historical: architecture/3.x/adr/2026-01-01-1-x.md\n"
    _write(snapshot, body)
    # kitty-specs is outside the swept roots AND excluded; prove both by sweeping all.
    run(tmp_path, occ, roots=("src", "tests", "docs", "kitty-specs"))
    assert snapshot.read_text() == body


# --------------------------------------------------------------------------- #
# (3) do_not_change-category literals are left untouched
# --------------------------------------------------------------------------- #


class TestDoNotChangeCategoriesUntouched:
    def test_import_path_literal_untouched(self, tmp_path: Path) -> None:
        """Dotted import paths carry no slash doc-path, so are never matched."""
        occ = _build_fixture_repo(tmp_path)
        src = tmp_path / "src" / "m.py"
        body = "from specify_cli.compat.registry import load_registry\n"
        _write(src, body)
        run(tmp_path, occ, roots=("src",), include_root_md=False)
        assert src.read_text() == body

    def test_serialized_toc_href_untouched(self, tmp_path: Path) -> None:
        occ = _build_fixture_repo(tmp_path)
        toc = tmp_path / "docs" / "toc.yml"
        body = "- href: architecture/3.x/adr/x.md\n"
        _write(toc, body)
        run(tmp_path, occ, roots=("docs",), include_root_md=False)
        assert toc.read_text() == body

    def test_markdown_frontmatter_field_untouched(self, tmp_path: Path) -> None:
        occ = _build_fixture_repo(tmp_path)
        page = tmp_path / "docs" / "p.md"
        _write(
            page,
            "---\n"
            "related: [architecture/3.x/adr/x.md]\n"
            "---\n"
            "Body link architecture/3.x/adr/x.md here.\n",
        )
        run(tmp_path, occ, roots=("docs",), include_root_md=False)
        text = page.read_text()
        # Frontmatter field preserved (WP12 territory) ...
        assert "related: [architecture/3.x/adr/x.md]" in text
        # ... but the BODY reference is rewritten.
        assert "Body link docs/adr/3.x/x.md here." in text

    def test_inventory_lockfile_untouched(self, tmp_path: Path) -> None:
        occ = _build_fixture_repo(tmp_path)
        lock = tmp_path / "docs" / "development" / "3-2-page-inventory.yaml"
        body = "- path: architecture/3.x/adr/x.md\n"
        _write(lock, body)
        run(tmp_path, occ, roots=("docs",), include_root_md=False)
        assert lock.read_text() == body


# --------------------------------------------------------------------------- #
# (4) idempotency
# --------------------------------------------------------------------------- #


def test_rewrite_is_idempotent(tmp_path: Path) -> None:
    occ = _build_fixture_repo(tmp_path)
    page = tmp_path / "docs" / "p.md"
    _write(page, "a architecture/3.x/adr/x.md and architecture/audits/y.md\n")
    first = run(tmp_path, occ, roots=("docs",), include_root_md=False)
    after_first = page.read_text()
    second = run(tmp_path, occ, roots=("docs",), include_root_md=False)
    assert first.total_rewrites >= 2
    assert second.total_rewrites == 0
    assert page.read_text() == after_first


# --------------------------------------------------------------------------- #
# incremental-safety guard + dry-run + unit helpers
# --------------------------------------------------------------------------- #


def test_unlanded_move_is_skipped(tmp_path: Path) -> None:
    """docs/development still exists in the fixture -> its refs are NOT rewritten."""
    occ = _build_fixture_repo(tmp_path)
    page = tmp_path / "docs" / "p.md"
    body = "guide at docs/development/ssh-deploy-keys.md\n"
    _write(page, body)
    run(tmp_path, occ, roots=("docs",), include_root_md=False)
    assert page.read_text() == body


def test_changelog_alias_skipped(tmp_path: Path) -> None:
    occ = _build_fixture_repo(tmp_path)
    subs = build_substitutions(load_moves(occ), tmp_path)
    assert all(s.old != "CHANGELOG.md" for s in subs)


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    occ = _build_fixture_repo(tmp_path)
    page = tmp_path / "docs" / "p.md"
    body = "x architecture/3.x/adr/x.md\n"
    _write(page, body)
    report = run(tmp_path, occ, roots=("docs",), include_root_md=False, dry_run=True)
    assert report.total_rewrites == 1
    assert page.read_text() == body  # unchanged on disk


def test_resolve_destination_variants(tmp_path: Path) -> None:
    (tmp_path / "docs/architecture/audits").mkdir(parents=True)
    (tmp_path / "docs/plans/engineering-notes").mkdir(parents=True)
    # subdir preserved
    assert (
        resolve_destination("architecture/audits", "docs/architecture", tmp_path)
        == "docs/architecture/audits"
    )
    # flattened (no docs/adr/3.x/adr subdir)
    (tmp_path / "docs/adr/3.x").mkdir(parents=True)
    assert (
        resolve_destination("architecture/3.x/adr", "docs/adr/3.x", tmp_path)
        == "docs/adr/3.x"
    )
    # underscore -> dash rename
    assert (
        resolve_destination("docs/engineering_notes", "docs/plans", tmp_path)
        == "docs/plans/engineering-notes"
    )
    # file move -> to/basename
    assert (
        resolve_destination("architecture/2.x/shim-registry.yaml", "docs/migrations", tmp_path)
        == "docs/migrations/shim-registry.yaml"
    )


def test_split_frontmatter() -> None:
    fm, body = split_frontmatter("---\na: 1\n---\nbody\n")
    assert fm == "---\na: 1\n---\n"
    assert body == "body\n"
    assert split_frontmatter("no frontmatter\n") == ("", "no frontmatter\n")
