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

from scripts.docs._guards import GitDiffError
from scripts.docs.related_validator import (
    DanglingEdge,
    main,
    validate_related,
    validate_related_diff_scoped,
)
from tests.docs.conftest import commit_all_changes, init_git_repo_with_base

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
    assert DanglingEdge(from_path="docs/source.md", to_path="docs/missing.md") in report.dangling_edges


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

    exit_code = main(["--repo-root", str(repo), "--docs-root", str(repo / "docs"), "--strict"])

    assert exit_code != 0


def test_strict_flag_stays_green_on_clean_tree(tmp_path: Path) -> None:
    """``--strict`` does not red a tree whose edges all resolve."""
    repo = _stage_repo(tmp_path, dangling=False)

    exit_code = main(["--repo-root", str(repo), "--docs-root", str(repo / "docs"), "--strict"])

    assert exit_code == 0


def test_zero_edge_walk_raises(tmp_path: Path) -> None:
    """A walk that examines no ``related:`` edges reds instead of passing vacuously.

    Mirrors ``relative_link_fixer.check_dead_body_links``' floor (#3264 / FR-008):
    a scope-narrowing regression that walks an empty or markdown-free tree must go
    RED, not report "0 dangling" over 0 checked.
    """
    empty_tree = tmp_path / "docs"
    empty_tree.mkdir()

    with pytest.raises(RuntimeError, match="expected at least"):
        validate_related(docs_root=empty_tree, repo_root=tmp_path)


def test_missing_docs_root_raises(tmp_path: Path) -> None:
    """A non-existent docs tree trips the same non-vacuity floor rather than returning empty."""
    with pytest.raises(RuntimeError, match="expected at least"):
        validate_related(docs_root=tmp_path / "absent", repo_root=tmp_path)


def test_populated_tree_still_returns_report(tmp_path: Path) -> None:
    """A tree with at least one ``related:`` edge still returns a report — the floor is non-vacuity only."""
    repo = _stage_repo(tmp_path, dangling=False)

    report = validate_related(docs_root=repo / "docs", repo_root=repo)

    assert report.checked_count > 0
    assert report.dangling_edges == []


# --------------------------------------------------------------------------- #
# T009 — Diff-scope mode (#3147, B-WP02)                                      #
# --------------------------------------------------------------------------- #


class TestDiffScopeValidatorPureFunction:
    """:func:`validate_related_diff_scoped` unit tests (no git involved)."""

    def test_in_scope_dangling_edge_is_reported(self, tmp_path: Path) -> None:
        repo = _stage_repo(tmp_path, dangling=True)
        report = validate_related_diff_scoped(docs_root=repo / "docs", repo_root=repo, changed_files=["docs/source.md"])
        assert DanglingEdge(from_path="docs/source.md", to_path="docs/missing.md") in report.dangling_edges

    def test_out_of_scope_dangling_edge_is_not_reported(self, tmp_path: Path) -> None:
        # source.md carries the dangling edge but is NOT in the changed set —
        # diff-scope must not surface it.
        repo = _stage_repo(tmp_path, dangling=True)
        report = validate_related_diff_scoped(docs_root=repo / "docs", repo_root=repo, changed_files=["docs/target.md"])
        assert report.dangling_edges == []
        assert report.checked_count == 0

    def test_resolved_zero_in_scope_docs_returns_empty_not_raise(self, tmp_path: Path) -> None:
        # B-WP02: a changed set with no docs_root files (e.g. a
        # src/specify_cli/**-only PR) must be a clean pass, never RuntimeError.
        repo = _stage_repo(tmp_path, dangling=True)
        report = validate_related_diff_scoped(
            docs_root=repo / "docs",
            repo_root=repo,
            changed_files=["src/specify_cli/foo.py"],
        )
        assert report.checked_count == 0
        assert report.dangling_edges == []

    def test_empty_changed_set_returns_empty_not_raise(self, tmp_path: Path) -> None:
        repo = _stage_repo(tmp_path, dangling=True)
        report = validate_related_diff_scoped(docs_root=repo / "docs", repo_root=repo, changed_files=[])
        assert report.checked_count == 0
        assert report.dangling_edges == []

    def test_deleted_changed_file_is_skipped(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        (repo / "docs").mkdir(parents=True)
        report = validate_related_diff_scoped(
            docs_root=repo / "docs",
            repo_root=repo,
            changed_files=["docs/gone-now.md"],
        )
        assert report.checked_count == 0
        assert report.dangling_edges == []


class TestDiffScopeValidatorCLI:
    """``--changed-from`` end-to-end through :func:`main`, over real git repos."""

    def test_in_scope_dangling_edge_reds(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _write(repo / "docs" / "target.md", None, body="target")
        base_sha = init_git_repo_with_base(repo)
        _write(repo / "docs" / "source.md", ["docs/missing.md"], body="source")
        commit_all_changes(repo, "add dangling related edge")

        rc = main(
            [
                "--repo-root",
                str(repo),
                "--docs-root",
                str(repo / "docs"),
                "--strict",
                "--changed-from",
                base_sha,
            ]
        )

        assert rc == 1

    def test_out_of_scope_preexisting_dangling_edge_passes(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        # Pre-existing dangling edge, committed as part of the base state.
        _write(repo / "docs" / "source.md", ["docs/missing.md"], body="source")
        base_sha = init_git_repo_with_base(repo)
        _write(repo / "docs" / "other.md", None, body="other")
        commit_all_changes(repo, "add unrelated doc")

        rc = main(
            [
                "--repo-root",
                str(repo),
                "--docs-root",
                str(repo / "docs"),
                "--strict",
                "--changed-from",
                base_sha,
            ]
        )

        assert rc == 0

    def test_resolved_zero_docs_passes(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _write(repo / "docs" / "target.md", None, body="target")
        base_sha = init_git_repo_with_base(repo)
        (repo / "README.md").write_text("# readme change\n", encoding="utf-8")
        commit_all_changes(repo, "non-docs change")

        rc = main(
            [
                "--repo-root",
                str(repo),
                "--docs-root",
                str(repo / "docs"),
                "--strict",
                "--changed-from",
                base_sha,
            ]
        )

        assert rc == 0

    def test_base_unresolvable_errors_non_zero(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _write(repo / "docs" / "target.md", None, body="target")
        init_git_repo_with_base(repo)

        rc = main(
            [
                "--repo-root",
                str(repo),
                "--docs-root",
                str(repo / "docs"),
                "--strict",
                "--changed-from",
                "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
            ]
        )

        assert rc not in (0, 1)

    def test_base_unresolvable_does_not_raise_out_of_main(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        repo = tmp_path / "repo"
        _write(repo / "docs" / "target.md", None, body="target")
        init_git_repo_with_base(repo)

        def _boom(*_args: object, **_kwargs: object) -> list[str]:
            raise GitDiffError("synthetic failure")

        monkeypatch.setattr("scripts.docs.related_validator.resolve_changed_files", _boom)
        rc = main(
            [
                "--repo-root",
                str(repo),
                "--docs-root",
                str(repo / "docs"),
                "--strict",
                "--changed-from",
                "whatever",
            ]
        )
        assert rc not in (0, 1)
