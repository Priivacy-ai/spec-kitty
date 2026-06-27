"""WP18 — contract tests for the relative-link integrity fixer.

Mission B (*Common Docs Structural Move*, ``01KW3SBK``).  These tests drive the
real fixer (:mod:`scripts.docs.relative_link_fixer`) against synthetic repos so
the load-bearing invariants are pinned to observable behaviour:

#. a move-broken bare-relative body link **is** resolved to the correct new path
   through the ``moves:`` spine;
#. a coarse-spine-miss with a unique on-disk landing **is** healed by the
   unique-basename fallback (deterministic, not a guess);
#. an already-resolving link is **untouched** (idempotency);
#. a *frontmatter* link is **never** touched (WP12 territory);
#. an external / anchor-only / absolute link is **skipped**;
#. an unresolvable link is **reported, never guessed**;
#. the body-link-resolution gate goes **RED** on a planted broken link and
   **GREEN** on the clean tree.

A final real-tree gate (:class:`TestLiveTreeGate`) pins the assembled ``docs/``
to *zero* dead bare-relative body links bar the documented nav-stub gaps.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

import pytest

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.docs.relative_link_fixer import (  # noqa: E402  (sys.path bootstrap above)
    LinkTarget,
    Resolver,
    check_dead_body_links,
    is_bare_relative,
    parse_link_payload,
    rewrite_body,
    run,
)

pytestmark = pytest.mark.fast


# --------------------------------------------------------------------------- #
# Synthetic-repo builder                                                       #
# --------------------------------------------------------------------------- #

# Mirrors the real restructure: ``how-to`` → ``guides``, ``reference`` → ``api``.
_OCCURRENCE_MAP: Final[str] = """\
target:
  term: "docs/"
  replacement: "docs/"
moves:
  - from: ["docs/how-to"]
    to: docs/guides
    reason: "How-to pages -> guides."
  - from: ["docs/reference"]
    to: docs/api
    reason: "Reference pages -> api."
status: applied
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Stage a post-move synthetic ``docs/`` tree + occurrence map.

    Returns ``(repo_root, occurrence_map_path)``.  The links in the staged files
    are authored against the *pre-move* layout, so the cross-directory ones are
    broken on this post-move tree exactly as the real restructure left them.
    """

    repo = tmp_path / "repo"
    occ = repo / "occurrence_map.yaml"
    _write(occ, _OCCURRENCE_MAP)

    # Moved target lives at its new home; the link in ``install.md`` still points
    # at the pre-move ``../reference/cli.md`` and is therefore broken.
    _write(repo / "docs/api/cli.md", "# CLI\n")
    _write(
        repo / "docs/guides/install.md",
        "---\nrelated:\n  - ../reference/cli.md\n---\n"
        "# Install\n\nSee the [CLI reference](../reference/cli.md) and the\n"
        "[install guide](install.md) and an [external](https://example.com/x.md)\n"
        "and an [anchor](#section) and an [absolute](/docs/api/cli.md).\n",
    )
    return repo, occ


# --------------------------------------------------------------------------- #
# Link payload parsing (pure units)                                            #
# --------------------------------------------------------------------------- #


class TestLinkParsing:
    def test_plain_target(self) -> None:
        parsed = parse_link_payload("../a/b.md")
        assert parsed == LinkTarget(
            lead="", angle=False, path="../a/b.md", anchor="", tail=""
        )

    def test_anchor_preserved(self) -> None:
        parsed = parse_link_payload("../a/b.md#sec")
        assert parsed is not None
        assert parsed.path == "../a/b.md"
        assert parsed.anchor == "#sec"
        assert parsed.render("../x/b.md") == "../x/b.md#sec"

    def test_title_preserved(self) -> None:
        parsed = parse_link_payload('../a/b.md "Title here"')
        assert parsed is not None
        assert parsed.path == "../a/b.md"
        assert parsed.render("c.md") == 'c.md "Title here"'

    def test_angle_wrapped(self) -> None:
        parsed = parse_link_payload("<../a/b.md>")
        assert parsed is not None
        assert parsed.path == "../a/b.md"
        assert parsed.render("c.md") == "<c.md>"

    def test_empty_payload(self) -> None:
        assert parse_link_payload("") is None
        assert parse_link_payload("   ") is None

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("../a.md", True),
            ("a/b.md", True),
            ("https://x/a.md", False),
            ("http://x/a.md", False),
            ("mailto:x@y.z", False),
            ("#anchor", False),
            ("/abs/a.md", False),
            ("", False),
        ],
    )
    def test_is_bare_relative(self, path: str, expected: bool) -> None:
        assert is_bare_relative(path) is expected


# --------------------------------------------------------------------------- #
# Resolution + rewrite behaviour                                              #
# --------------------------------------------------------------------------- #


class TestSpineResolution:
    def test_broken_link_resolved_to_new_path_via_moves(self, tmp_path: Path) -> None:
        repo, occ = _build_repo(tmp_path)
        report = run(repo, occ)

        body = (repo / "docs/guides/install.md").read_text(encoding="utf-8")
        # The broken ``../reference/cli.md`` is rewritten to the real landing.
        assert "(../api/cli.md)" in body
        assert "../reference/cli.md" not in _strip_frontmatter(body)
        rewrites = {(r.old_link, r.new_link, r.tier) for r in report.rewrites}
        assert ("../reference/cli.md", "../api/cli.md", "spine") in rewrites

    def test_already_resolving_link_untouched(self, tmp_path: Path) -> None:
        repo, occ = _build_repo(tmp_path)
        run(repo, occ)
        body = (repo / "docs/guides/install.md").read_text(encoding="utf-8")
        # ``install.md`` is a same-dir sibling that already resolves — verbatim.
        assert "[install guide](install.md)" in body

    def test_external_anchor_absolute_skipped(self, tmp_path: Path) -> None:
        repo, occ = _build_repo(tmp_path)
        run(repo, occ)
        body = (repo / "docs/guides/install.md").read_text(encoding="utf-8")
        assert "(https://example.com/x.md)" in body
        assert "(#section)" in body
        assert "(/docs/api/cli.md)" in body

    def test_frontmatter_link_never_touched(self, tmp_path: Path) -> None:
        repo, occ = _build_repo(tmp_path)
        run(repo, occ)
        text = (repo / "docs/guides/install.md").read_text(encoding="utf-8")
        front = text.split("---\n", 2)[1]
        # The frontmatter ``related:`` edge (WP12's category) is left as-authored.
        assert "../reference/cli.md" in front

    def test_idempotent_second_run_is_noop(self, tmp_path: Path) -> None:
        repo, occ = _build_repo(tmp_path)
        run(repo, occ)
        after_first = (repo / "docs/guides/install.md").read_text(encoding="utf-8")
        second = run(repo, occ)
        after_second = (repo / "docs/guides/install.md").read_text(encoding="utf-8")
        assert second.total_rewrites == 0
        assert after_first == after_second


class TestOnDiskFallback:
    def test_unique_basename_landing_healed(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _write(repo / "occurrence_map.yaml", _OCCURRENCE_MAP)
        # ``a.md`` never moved; its sibling link to ``b.md`` is broken because
        # ``b.md`` actually landed under a different, unique directory.
        _write(repo / "docs/notes/a.md", "# A\n\nSee [B](b.md).\n")
        _write(repo / "docs/elsewhere/b.md", "# B\n")
        report = run(repo, repo / "occurrence_map.yaml")
        body = (repo / "docs/notes/a.md").read_text(encoding="utf-8")
        assert "(../elsewhere/b.md)" in body
        assert {r.tier for r in report.rewrites} == {"on-disk"}

    def test_ambiguous_basename_reported_not_guessed(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _write(repo / "occurrence_map.yaml", _OCCURRENCE_MAP)
        _write(repo / "docs/notes/a.md", "# A\n\nSee [dup](dup.md).\n")
        _write(repo / "docs/one/dup.md", "# one\n")
        _write(repo / "docs/two/dup.md", "# two\n")
        report = run(repo, repo / "occurrence_map.yaml")
        # Two ``dup.md`` candidates -> no deterministic target -> reported.
        assert report.total_rewrites == 0
        assert [(u.file, u.link) for u in report.unresolvable] == [
            ("docs/notes/a.md", "dup.md")
        ]


class TestReportNeverGuess:
    def test_unresolvable_link_reported(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _write(repo / "occurrence_map.yaml", _OCCURRENCE_MAP)
        _write(repo / "docs/notes/a.md", "# A\n\nSee [ghost](ghost.md).\n")
        report = run(repo, repo / "occurrence_map.yaml")
        body = (repo / "docs/notes/a.md").read_text(encoding="utf-8")
        # No target exists anywhere -> left verbatim, surfaced for the reviewer.
        assert "(ghost.md)" in body
        assert report.total_rewrites == 0
        assert [(u.file, u.link) for u in report.unresolvable] == [
            ("docs/notes/a.md", "ghost.md")
        ]


# --------------------------------------------------------------------------- #
# Body-link-resolution gate (T101)                                            #
# --------------------------------------------------------------------------- #


class TestGate:
    def test_gate_green_on_clean_tree(self, tmp_path: Path) -> None:
        repo, occ = _build_repo(tmp_path)
        run(repo, occ)  # heal the move-broken link
        assert check_dead_body_links(repo) == []

    def test_gate_red_on_planted_broken_link(self, tmp_path: Path) -> None:
        repo, occ = _build_repo(tmp_path)
        run(repo, occ)
        _write(
            repo / "docs/guides/planted.md",
            "# Planted\n\nA [dead](../does/not/exist.md) link.\n",
        )
        dead = check_dead_body_links(repo)
        assert [(u.file, u.link) for u in dead] == [
            ("docs/guides/planted.md", "../does/not/exist.md")
        ]

    def test_gate_excludes_immutable_subtrees(self, tmp_path: Path) -> None:
        repo, occ = _build_repo(tmp_path)
        run(repo, occ)
        # A dead link inside an immutable ADR body must NOT trip the gate.
        _write(
            repo / "docs/adr/3.x/x.md",
            "# ADR\n\nA [dead](../does/not/exist.md) link.\n",
        )
        assert check_dead_body_links(repo) == []


class TestRewriteBodyHelper:
    def test_rewrite_body_skips_frontmatter_region(self, tmp_path: Path) -> None:
        repo, occ = _build_repo(tmp_path)
        resolver = Resolver.build(repo, occ)
        body = "See [cli](../reference/cli.md).\n"
        new_body, rewrites, unresolved = rewrite_body(
            body, "docs/guides/install.md", resolver
        )
        assert "(../api/cli.md)" in new_body
        assert len(rewrites) == 1
        assert unresolved == []


# --------------------------------------------------------------------------- #
# Live assembled-tree gate                                                     #
# --------------------------------------------------------------------------- #


class TestLiveTreeGate:
    """Pin the real ``docs/`` to **zero** dead bare-relative body links.

    WP14 created the three section landing pages the ``docs/index.md`` cards
    pointed at (``adr/index.md``, ``integrations/index.md``, ``security/index.md``)
    as part of flipping the body-link gate to blocking, so the former nav-stub
    gaps are now resolved and the allowlist is empty: any dead bare-relative
    body link is a regression this gate catches.
    """

    _KNOWN_GAPS: Final[frozenset[tuple[str, str]]] = frozenset()

    def test_assembled_tree_has_no_unexpected_dead_links(self) -> None:
        dead = {
            (u.file, u.link) for u in check_dead_body_links(_REPO_ROOT)
        }
        unexpected = dead - self._KNOWN_GAPS
        assert unexpected == set(), (
            f"unexpected dead bare-relative body links: {sorted(unexpected)}"
        )


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        return text.split("---\n", 2)[-1]
    return text
