"""Tests for ``scripts/docs/freshen_adr_inventory.py``.

The tool freshens BOTH ADR indexes the docs-freshness gate enforces:
1. the generated page-inventory lockfile (regenerated from frontmatter), and
2. the era ``README.md`` ADR table (a date-ordered, idempotent row insert).

Fixtures are production-shaped: a real ``docs/adr/3.x/`` tree with genuine
ADR frontmatter, a real era README carrying a ``| Date | Title |`` index
table, and a real committed inventory lockfile rendered by the canonical
generator — so a run exercises the same code path CI does.
"""

from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.docs.freshen_adr_inventory import (  # noqa: E402
    DEFAULT_INVENTORY_PATH,
    detect_missing_adrs,
    freshen,
    main,
)
from scripts.docs.inventory_lockfile import (  # noqa: E402
    generate_inventory,
    render_lockfile,
)

pytestmark = [pytest.mark.fast]


# --------------------------------------------------------------------------- #
# Fixture builders
# --------------------------------------------------------------------------- #

_README_TEMPLATE = dedent(
    """\
    # 3.x ADRs

    Architectural Decision Records for the 3.x track.

    ## Index

    | Date | Title |
    |---|---|
    | 2026-04-03 | [Execution lanes own worktrees](2026-04-03-1-execution-lanes.md) |
    | 2026-05-16 | [Doctrine layer merge semantics](2026-05-16-1-doctrine-merge.md) |
    | 2026-06-26 | [Single-authority seam](2026-06-26-1-single-authority-seam.md) |
    """
)


def _adr(title: str, date: str, *, body: str = "Decision body.") -> str:
    return dedent(
        f"""\
        ---
        title: {title}
        status: Accepted
        date: '{date}'
        ---

        ## Context

        {body}
        """
    )


def _write_docs_tree(repo_root: Path) -> Path:
    """Stage a realistic docs tree; return the docs root."""
    docs_root = repo_root / "docs"
    era = docs_root / "adr" / "3.x"
    era.mkdir(parents=True)

    (era / "README.md").write_text(_README_TEMPLATE, encoding="utf-8")

    # Pre-existing ADRs that already have README rows.
    (era / "2026-04-03-1-execution-lanes.md").write_text(
        _adr("Execution lanes own worktrees", "2026-04-03"), encoding="utf-8"
    )
    (era / "2026-05-16-1-doctrine-merge.md").write_text(
        _adr("Doctrine layer merge semantics", "2026-05-16"), encoding="utf-8"
    )
    (era / "2026-06-26-1-single-authority-seam.md").write_text(
        _adr("Single-authority seam", "2026-06-26"), encoding="utf-8"
    )

    # A non-ADR doc so the inventory has more than ADRs in it.
    (docs_root / "index.md").write_text(
        _adr("Docs home", "2026-01-01"), encoding="utf-8"
    )

    _write_inventory(repo_root, docs_root)
    return docs_root


def _write_inventory(repo_root: Path, docs_root: Path) -> None:
    """Render + commit an inventory matching the current tree (no drift)."""
    inv = repo_root / DEFAULT_INVENTORY_PATH
    inv.parent.mkdir(parents=True, exist_ok=True)
    inv.write_text(
        render_lockfile(generate_inventory(docs_root, repo_root=repo_root)),
        encoding="utf-8",
    )


def _read_readme(docs_root: Path) -> str:
    return (docs_root / "adr" / "3.x" / "README.md").read_text(encoding="utf-8")


def _table_rows(readme_text: str) -> list[str]:
    """Return the ADR table's data rows (between separator and blank/EOF)."""
    rows: list[str] = []
    in_table = False
    for line in readme_text.splitlines():
        if line.startswith("|---"):
            in_table = True
            continue
        if in_table:
            if line.startswith("|"):
                rows.append(line)
            else:
                break
    return rows


# --------------------------------------------------------------------------- #
# 1. Adding a new ADR surfaces both rows
# --------------------------------------------------------------------------- #


def test_new_adr_gets_inventory_and_readme_rows(tmp_path: Path) -> None:
    repo_root = tmp_path
    docs_root = _write_docs_tree(repo_root)
    new_adr = docs_root / "adr" / "3.x" / "2026-06-30-1-new-thing.md"
    new_adr.write_text(_adr("A Brand New Thing", "2026-06-30"), encoding="utf-8")

    result = freshen(
        [new_adr], docs_root=docs_root, repo_root=repo_root, check=False
    )

    # README row present with the right date/title/link.
    readme = _read_readme(docs_root)
    assert (
        "| 2026-06-30 | [A Brand New Thing](2026-06-30-1-new-thing.md) |" in readme
    )
    assert "2026-06-30-1-new-thing.md" in result.readme_rows_added

    # Inventory row present (path appears in the regenerated lockfile).
    inv = (repo_root / DEFAULT_INVENTORY_PATH).read_text(encoding="utf-8")
    assert "docs/adr/3.x/2026-06-30-1-new-thing.md" in inv
    assert result.inventory_written is True


# --------------------------------------------------------------------------- #
# 2. Idempotency
# --------------------------------------------------------------------------- #


def test_running_twice_is_idempotent(tmp_path: Path) -> None:
    repo_root = tmp_path
    docs_root = _write_docs_tree(repo_root)
    new_adr = docs_root / "adr" / "3.x" / "2026-06-30-1-new-thing.md"
    new_adr.write_text(_adr("A Brand New Thing", "2026-06-30"), encoding="utf-8")

    freshen([new_adr], docs_root=docs_root, repo_root=repo_root, check=False)
    first = _read_readme(docs_root)

    second_result = freshen(
        [new_adr], docs_root=docs_root, repo_root=repo_root, check=False
    )
    second = _read_readme(docs_root)

    assert first == second  # no duplicate row / no second change
    assert second_result.readme_rows_added == ()
    assert second_result.inventory_written is False
    # Exactly one row references the basename.
    assert second.count("](2026-06-30-1-new-thing.md)") == 1


# --------------------------------------------------------------------------- #
# 3. --check exit codes
# --------------------------------------------------------------------------- #


def test_check_nonzero_when_readme_row_missing(tmp_path: Path) -> None:
    repo_root = tmp_path
    docs_root = _write_docs_tree(repo_root)
    new_adr = docs_root / "adr" / "3.x" / "2026-06-30-1-new-thing.md"
    new_adr.write_text(_adr("A Brand New Thing", "2026-06-30"), encoding="utf-8")
    # Regenerate inventory so ONLY the README row is missing (isolate the cause).
    _write_inventory(repo_root, docs_root)

    exit_code = main(
        [
            str(new_adr),
            "--check",
            "--repo-root",
            str(repo_root),
            "--docs-root",
            str(docs_root),
        ]
    )
    assert exit_code == 1


def test_check_nonzero_when_inventory_stale(tmp_path: Path) -> None:
    repo_root = tmp_path
    docs_root = _write_docs_tree(repo_root)
    # Add an ADR + its README row but leave the inventory stale.
    new_adr = docs_root / "adr" / "3.x" / "2026-06-30-1-new-thing.md"
    new_adr.write_text(_adr("A Brand New Thing", "2026-06-30"), encoding="utf-8")
    freshen([new_adr], docs_root=docs_root, repo_root=repo_root, check=False)
    # Now dirty the tree with another doc so the committed inventory is stale.
    (docs_root / "extra.md").write_text(_adr("Extra", "2026-02-02"), encoding="utf-8")

    exit_code = main(
        [
            str(new_adr),
            "--check",
            "--repo-root",
            str(repo_root),
            "--docs-root",
            str(docs_root),
        ]
    )
    assert exit_code == 1


def test_check_zero_when_clean(tmp_path: Path) -> None:
    repo_root = tmp_path
    docs_root = _write_docs_tree(repo_root)

    exit_code = main(
        [
            "--check",
            "--repo-root",
            str(repo_root),
            "--docs-root",
            str(docs_root),
        ]
    )
    assert exit_code == 0


# --------------------------------------------------------------------------- #
# 4. --all auto-detects README-missing ADRs
# --------------------------------------------------------------------------- #


def test_all_detects_and_adds_missing_row(tmp_path: Path) -> None:
    repo_root = tmp_path
    docs_root = _write_docs_tree(repo_root)
    orphan = docs_root / "adr" / "3.x" / "2026-06-29-1-orphan.md"
    orphan.write_text(_adr("Orphan ADR", "2026-06-29"), encoding="utf-8")

    assert orphan in detect_missing_adrs(docs_root)

    exit_code = main(
        ["--all", "--repo-root", str(repo_root), "--docs-root", str(docs_root)]
    )
    assert exit_code == 0

    readme = _read_readme(docs_root)
    assert "| 2026-06-29 | [Orphan ADR](2026-06-29-1-orphan.md) |" in readme
    assert detect_missing_adrs(docs_root) == []


# --------------------------------------------------------------------------- #
# 5. Title normalization
# --------------------------------------------------------------------------- #


def test_adr_prefix_stripped_from_title(tmp_path: Path) -> None:
    repo_root = tmp_path
    docs_root = _write_docs_tree(repo_root)
    adr = docs_root / "adr" / "3.x" / "2026-06-30-1-prefixed.md"
    adr.write_text(_adr("'ADR: Foo Bar'", "2026-06-30"), encoding="utf-8")

    freshen([adr], docs_root=docs_root, repo_root=repo_root, check=False)

    readme = _read_readme(docs_root)
    assert "| 2026-06-30 | [Foo Bar](2026-06-30-1-prefixed.md) |" in readme
    assert "ADR: Foo Bar" not in readme


def test_folded_multiline_title_collapses(tmp_path: Path) -> None:
    repo_root = tmp_path
    docs_root = _write_docs_tree(repo_root)
    adr = docs_root / "adr" / "3.x" / "2026-06-30-1-folded.md"
    # A single-quoted YAML scalar folded across two lines (real ADR shape).
    adr.write_text(
        "---\n"
        "title: 'ADR: Single-Authority Seam + Call-Site Gate for Resolution\n"
        "  Boundaries (Phase 1)'\n"
        "status: Accepted\n"
        "date: '2026-06-30'\n"
        "---\n\n## Context\n\nBody.\n",
        encoding="utf-8",
    )

    freshen([adr], docs_root=docs_root, repo_root=repo_root, check=False)

    readme = _read_readme(docs_root)
    assert (
        "| 2026-06-30 | [Single-Authority Seam + Call-Site Gate for "
        "Resolution Boundaries (Phase 1)](2026-06-30-1-folded.md) |" in readme
    )


# --------------------------------------------------------------------------- #
# 6. Date-ordered insertion
# --------------------------------------------------------------------------- #


def test_midrange_date_inserts_between_neighbours(tmp_path: Path) -> None:
    repo_root = tmp_path
    docs_root = _write_docs_tree(repo_root)
    # Existing dates: 2026-04-03, 2026-05-16, 2026-06-26. Insert 2026-05-20.
    adr = docs_root / "adr" / "3.x" / "2026-05-20-1-midrange.md"
    adr.write_text(_adr("Midrange Decision", "2026-05-20"), encoding="utf-8")

    freshen([adr], docs_root=docs_root, repo_root=repo_root, check=False)

    rows = _table_rows(_read_readme(docs_root))
    dates = [row.split("|")[1].strip() for row in rows]
    assert dates == sorted(dates)  # table stays ascending
    idx = dates.index("2026-05-20")
    assert dates[idx - 1] == "2026-05-16"
    assert dates[idx + 1] == "2026-06-26"
