"""Tests for ``specify_cli.tasks.issue_matrix`` (WP09, FR-009, closes #1163)."""

from __future__ import annotations

from pathlib import Path

from specify_cli.tasks.issue_matrix import (
    detect_issue_references,
    scaffold_issue_matrix,
)


def _write_spec(tmp_path: Path, body: str) -> tuple[Path, Path]:
    feature_dir = tmp_path / "kitty-specs" / "099-demo"
    feature_dir.mkdir(parents=True)
    spec_md = feature_dir / "spec.md"
    spec_md.write_text(body, encoding="utf-8")
    return feature_dir, spec_md


def test_scaffold_creates_matrix_with_multiple_unique_refs(tmp_path: Path) -> None:
    """spec.md with several ``#NNN`` refs scaffolds a matrix containing each ref exactly once."""
    body = (
        "# Spec\n"
        "\n"
        "This mission closes #1163 and partially addresses #1298. "
        "It also references #42 in a sentence.\n"
        "\n"
        "See also (#1298) for the related discussion (duplicate ref).\n"
    )
    feature_dir, spec_md = _write_spec(tmp_path, body)

    out_path = scaffold_issue_matrix(feature_dir, spec_md)

    assert out_path is not None
    assert out_path == feature_dir / "issue-matrix.md"
    assert out_path.exists()

    content = out_path.read_text(encoding="utf-8")
    # Header row + columns
    assert "| Issue | Title | Verdict | Evidence ref |" in content
    # Each unique ref appears exactly once
    assert content.count("| #1163 |") == 1
    assert content.count("| #1298 |") == 1
    assert content.count("| #42 |") == 1
    # Verdict enum referenced in trailer
    assert "fixed" in content
    assert "verified-already-fixed" in content
    assert "deferred-with-followup" in content


def test_scaffold_returns_none_when_no_refs(tmp_path: Path) -> None:
    """spec.md without GH issue refs returns ``None`` and creates no file."""
    body = (
        "# Spec\n"
        "\n"
        "## Section\n"
        "\n"
        "Pure prose with no references. A markdown heading uses # but is "
        "not an issue ref. URLs like https://example.com/page#frag are "
        "fragments, not issues.\n"
    )
    feature_dir, spec_md = _write_spec(tmp_path, body)

    out_path = scaffold_issue_matrix(feature_dir, spec_md)

    assert out_path is None
    assert not (feature_dir / "issue-matrix.md").exists()


def test_scaffold_does_not_overwrite_existing_file(tmp_path: Path) -> None:
    """Existing ``issue-matrix.md`` is preserved (idempotent re-run)."""
    body = "Mission closes #1163.\n"
    feature_dir, spec_md = _write_spec(tmp_path, body)

    existing = feature_dir / "issue-matrix.md"
    existing.write_text("# Operator-curated content\n\nDo not overwrite.\n", encoding="utf-8")

    out_path = scaffold_issue_matrix(feature_dir, spec_md)

    assert out_path == existing
    # Content is unchanged
    assert "Operator-curated content" in existing.read_text(encoding="utf-8")
    assert "Do not overwrite." in existing.read_text(encoding="utf-8")


def test_scaffold_does_not_match_section_anchor_links(tmp_path: Path) -> None:
    """``#section-name`` anchor-style markdown refs are not treated as GH issues."""
    body = (
        "# Spec\n"
        "\n"
        "See the [overview](#overview) and [#section-name](other.md) for context.\n"
        "Markdown anchor (#anchor-text) should not match. "
        "Inline #notanumber and #abc123 also should not match.\n"
    )
    feature_dir, spec_md = _write_spec(tmp_path, body)

    refs = detect_issue_references(spec_md)
    assert refs == []

    out_path = scaffold_issue_matrix(feature_dir, spec_md)
    assert out_path is None
    assert not (feature_dir / "issue-matrix.md").exists()
