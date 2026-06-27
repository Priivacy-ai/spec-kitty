"""Self-test for the ``related:`` frontmatter validator (WP03 / IC-03 / FR-005).

The validator is *report-only* (exit 0) in Mission A; Mission B flips the
``--strict`` default on to make it blocking. This self-test is the real
Definition of Done: a ruler that cannot go RED is fake. We therefore prove
that

* a deliberately-**dangling** ``related:`` edge is detected (and reds under
  ``--strict``);
* a clean tree reports **no** dangling edges; and
* ``checked_count > 0`` so "0 broken" can never silently mean "0 checked".
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.docs.related_validator import (
    DanglingEdge,
    main,
    validate_related,
)

pytestmark = pytest.mark.architectural


def _write(path: Path, frontmatter_related: list[str] | None, body: str = "x") -> None:
    """Write a markdown page with an optional ``related:`` frontmatter list."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", 'title: "page"']
    if frontmatter_related is not None:
        lines.append("related:")
        lines.extend(f"  - {entry}" for entry in frontmatter_related)
    lines += ["---", "", f"# {body}", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def _stage_repo(tmp_path: Path, *, dangling: bool) -> Path:
    """Stage a repo-shaped tree under ``tmp_path`` and return the repo root.

    The source page links to ``docs/target.md`` (which always exists) and,
    when ``dangling`` is true, also to ``docs/missing.md`` (which never does).
    """
    repo = tmp_path / "repo"
    docs = repo / "docs"
    _write(docs / "target.md", None, body="target")
    related = ["docs/target.md"]
    if dangling:
        related.append("docs/missing.md")
    _write(docs / "source.md", related, body="source")
    return repo


def test_dangling_edge_is_detected(tmp_path: Path) -> None:
    """A non-resolving ``related:`` entry surfaces as a dangling edge."""
    repo = _stage_repo(tmp_path, dangling=True)

    report = validate_related(docs_root=repo / "docs", repo_root=repo)

    assert report.checked_count > 0
    assert (
        DanglingEdge(from_path="docs/source.md", to_path="docs/missing.md")
        in report.dangling_edges
    )


def test_clean_tree_has_no_dangling_edges(tmp_path: Path) -> None:
    """A tree whose ``related:`` edges all resolve reports zero dangling."""
    repo = _stage_repo(tmp_path, dangling=False)

    report = validate_related(docs_root=repo / "docs", repo_root=repo)

    assert report.checked_count > 0
    assert report.dangling_edges == []


def test_report_only_exit_zero_even_when_dangling(tmp_path: Path) -> None:
    """Default invocation is report-only: dangling edges still exit 0 (C-002)."""
    repo = _stage_repo(tmp_path, dangling=True)

    exit_code = main(["--repo-root", str(repo), "--docs-root", str(repo / "docs")])

    assert exit_code == 0


def test_strict_flag_reds_on_dangling(tmp_path: Path) -> None:
    """The wired ``--strict`` flag turns a dangling edge into a non-zero exit."""
    repo = _stage_repo(tmp_path, dangling=True)

    exit_code = main(
        ["--repo-root", str(repo), "--docs-root", str(repo / "docs"), "--strict"]
    )

    assert exit_code != 0


def test_strict_flag_stays_green_on_clean_tree(tmp_path: Path) -> None:
    """``--strict`` does not red a tree whose edges all resolve."""
    repo = _stage_repo(tmp_path, dangling=False)

    exit_code = main(
        ["--repo-root", str(repo), "--docs-root", str(repo / "docs"), "--strict"]
    )

    assert exit_code == 0
