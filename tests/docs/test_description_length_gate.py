"""Boundary self-test for the net-new ``description`` length gate (NFR-003).

The gate did not exist before WP11: ``seo_postprocess.py`` only *emits* a
description, it never *validates* its length. A length gate that cannot go RED
is fake, so the Definition of Done is the boundary proof — **49 and 181
characters RED, 50 and 180 green** — plus the report-only/``--strict`` exit
contract it shares with :mod:`scripts.docs.related_validator`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.docs.description_length_check import (
    MAX_DESCRIPTION_LENGTH,
    MIN_DESCRIPTION_LENGTH,
    check_description_length,
    main,
    validate_descriptions,
)

pytestmark = pytest.mark.architectural


def _desc(length: int) -> str:
    """A description string of exactly ``length`` characters."""
    return "x" * length


def _write_page(path: Path, description: str | None) -> None:
    """Write a docs page with an optional ``description`` frontmatter value."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", 'title: "Configuring the lane allocator"']
    if description is not None:
        lines.append(f'description: "{description}"')
    lines += ["doc_status: active", "---", "", "# Body", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


# --- check_description_length: the boundary contract -----------------------


def test_band_boundaries_are_inclusive_50_and_180_green() -> None:
    """The 50 and 180 boundaries are valid (inclusive band)."""
    assert MIN_DESCRIPTION_LENGTH == 50
    assert MAX_DESCRIPTION_LENGTH == 180
    assert check_description_length(_desc(50)) is None
    assert check_description_length(_desc(180)) is None
    assert check_description_length(_desc(120)) is None


def test_49_chars_is_too_short_red() -> None:
    """One char below the floor is a RED ``too_short`` violation."""
    assert check_description_length(_desc(49)) == "too_short"


def test_181_chars_is_too_long_red() -> None:
    """One char above the ceiling is a RED ``too_long`` violation."""
    assert check_description_length(_desc(181)) == "too_long"


def test_missing_and_blank_description_is_red() -> None:
    """A missing or whitespace-only description is a RED ``missing`` violation."""
    assert check_description_length(None) == "missing"
    assert check_description_length("") == "missing"
    assert check_description_length("   ") == "missing"


# --- validate_descriptions: tree walk + checked_count ----------------------


def test_validate_flags_out_of_band_pages_and_counts_checks(tmp_path: Path) -> None:
    """The walk flags each out-of-band page and never reports 0/0 silently."""
    docs = tmp_path / "docs"
    _write_page(docs / "good.md", _desc(120))
    _write_page(docs / "short.md", _desc(49))
    _write_page(docs / "long.md", _desc(181))
    _write_page(docs / "absent.md", None)

    report = validate_descriptions(docs_root=docs, repo_root=tmp_path)

    assert report.checked_count == 4
    reasons = {v.path: v.reason for v in report.violations}
    assert reasons == {
        "docs/absent.md": "missing",
        "docs/long.md": "too_long",
        "docs/short.md": "too_short",
    }
    # The valid page produced no violation, but it WAS checked.
    assert "docs/good.md" not in reasons


def test_clean_tree_reports_zero_violations(tmp_path: Path) -> None:
    """A tree whose descriptions are all in-band reports zero violations."""
    docs = tmp_path / "docs"
    _write_page(docs / "a.md", _desc(50))
    _write_page(docs / "b.md", _desc(180))

    report = validate_descriptions(docs_root=docs, repo_root=tmp_path)

    assert report.checked_count == 2
    assert report.violations == []


# --- main: the report-only / --strict exit contract ------------------------


def test_report_only_exit_zero_even_with_violations(tmp_path: Path) -> None:
    """Default invocation is report-only: violations still exit 0 (C-002)."""
    docs = tmp_path / "docs"
    _write_page(docs / "short.md", _desc(49))

    exit_code = main(["--docs-root", str(docs), "--repo-root", str(tmp_path)])

    assert exit_code == 0


def test_strict_reds_on_violation(tmp_path: Path) -> None:
    """The wired ``--strict`` flag turns an out-of-band description non-zero."""
    docs = tmp_path / "docs"
    _write_page(docs / "long.md", _desc(181))

    exit_code = main(
        ["--docs-root", str(docs), "--repo-root", str(tmp_path), "--strict"]
    )

    assert exit_code == 1


def test_strict_stays_green_on_clean_tree(tmp_path: Path) -> None:
    """``--strict`` does not red a tree whose descriptions are all in-band."""
    docs = tmp_path / "docs"
    _write_page(docs / "a.md", _desc(100))

    exit_code = main(
        ["--docs-root", str(docs), "--repo-root", str(tmp_path), "--strict"]
    )

    assert exit_code == 0
