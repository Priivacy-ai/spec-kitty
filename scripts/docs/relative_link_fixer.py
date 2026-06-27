#!/usr/bin/env python3
"""Relative-link integrity fixer (Mission B, WP18).

Mission B (*Common Docs Structural Move*, ``01KW3SBK``) folds ``architecture/``
into ``docs/`` and re-sections the Divio dirs.  WP08's
:mod:`scripts.docs.bulk_ref_rewrite` rewrote every *prefix-anchored* doc-path
reference (``docs/…`` / ``architecture/…``) through the ``occurrence_map.yaml``
``moves:`` spine.  It deliberately did **not** own the *bare-relative* body
links (``](../00_landscape/README.md)``, ``](../../3.x/adr/foo.md)``): those
carry no anchor and resolve from each file's own location, so the move silently
broke hundreds of them and no existing gate catches them (``related_validator``
only checks frontmatter ``related:`` edges, never body links).

This tool is the relative-link complement.  For every ``docs/**/*.md`` body
markdown link that does **not** resolve on disk from the file's current
location it heals the target deterministically:

#. **Pre-move resolution (the moves spine).**  The file came from a ``moves:``
   source; resolve the broken link against the file's *pre-move* directory to
   get the **old absolute target**, map that target forward through the same
   ``moves:`` spine (reusing WP08's :func:`resolve_adr_era_twin` for deduped
   ADRs), and recompute the **new relative path** from the file's current
   location.  This heals the move-broken class.
#. **Unique-on-disk landing (fallback).**  When the coarse directory-granular
   spine diverges from the *actual* per-file landing (e.g. WP04 re-sectioned
   ``docs/development`` into both ``docs/operations`` *and* ``docs/guides``), the
   ground truth is the on-disk tree: a target whose basename resolves to
   **exactly one** file under ``docs/`` is that file.  A non-unique basename is
   **not** resolved — it is reported, never guessed.
#. **Report, never guess.**  A link with no deterministic target (a genuine
   pre-existing dead link, a nav stub to a section that does not exist) is
   surfaced for the reviewer / issue-matrix, never rewritten to a wrong target.

**Scope discipline.**  Only *bare-relative* body link **targets** are touched —
never frontmatter (WP12's ``related:``), never prose, never anchored refs
(WP08).  External ``http(s)``/``mailto``/anchor-only/absolute links are skipped.
Two content-invariant records are excluded entirely: the ``docs/adr/`` decision
bodies (C-002 byte-for-byte content-invariance, enforced by
``test_adr_content_invariance``) and the ``docs/changelog/`` historical mirror
of the root ``CHANGELOG.md`` (whose entries reference repo-root doc paths, not
``../``-relative links).  The archived ``docs/archive/`` ``1x``/``2x`` tracks are
**in scope**: their bodies are re-authored at the new depth (so the spine
resolves them as unmoved) and ``test_versioned_docs_integrity`` actively guards
their link integrity.

``occurrence_map.yaml`` is **read-only** here (the orchestrator owns it).  The
``--check`` mode is the report-only body-link-resolution gate WP14 can flip
blocking, so the broken-relative-link class cannot silently recur.
"""

from __future__ import annotations

import argparse
import os
import posixpath
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

# ``scripts.docs`` is a namespace-package module; when this file is imported as
# a bare script (``python scripts/docs/relative_link_fixer.py``) the repo root is
# not on ``sys.path``. Anchor it so the shared move-spine helpers resolve to the
# canonical WP08 rewriter — mirrors the bootstrap in ``adr_converter.py``.
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.docs.bulk_ref_rewrite import (  # noqa: E402  (sys.path bootstrap above)
    DEFAULT_OCCURRENCE_MAP,
    SKIP_MOVE_FROMS,
    Substitution,
    build_substitutions,
    load_moves,
    resolve_adr_era_twin,
    resolve_destination,
    split_frontmatter,
)

# --------------------------------------------------------------------------- #
# Scope                                                                        #
# --------------------------------------------------------------------------- #

DOCS_ROOT = "docs"

#: Content-invariant doc subtrees — never rewritten and excluded from the gate.
#: ADR bodies are byte-identical to their pre-move originals (C-002, enforced by
#: ``test_adr_content_invariance``); the changelog mirror replays the historical
#: root ``CHANGELOG.md`` whose entries cite repo-root doc paths, not ``../``
#: links.  The ``docs/archive/`` tracks are *not* here — their links are live.
EXCLUDE_PREFIXES: tuple[str, ...] = (
    "docs/adr/",
    "docs/changelog/",
)

#: Era tokens (``1.x``/``2.x``/``3.x``) used to disambiguate which era-specific
#: source directory a per-era landing (``README-2.x.md``) came from.
_ERA = re.compile(r"(?<![\w.])([123]\.x)(?![\w])")

#: A markdown inline link's ``](target)`` payload — the parenthesised content
#: between the ``](`` and the closing ``)``.  Reference-style and HTML ``href``
#: links are intentionally out of scope (the spec says *body markdown links*).
_LINK = re.compile(r"\]\(([^)]*)\)")


# --------------------------------------------------------------------------- #
# Link payload parsing                                                         #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class LinkTarget:
    """A parsed ``](…)`` payload split into its rewritable pieces.

    ``](  <path>#anchor  "title")`` decomposes into the leading whitespace, an
    optional ``<``/``>`` angle wrapper, the path, the ``#anchor`` fragment, and
    the trailing title/whitespace.  Reassembling with a new *path* preserves
    every byte except the link target itself.
    """

    lead: str
    angle: bool
    path: str
    anchor: str
    tail: str

    def render(self, new_path: str) -> str:
        """Re-emit the payload with *new_path*, preserving anchor/title/spacing."""

        wrapped = f"<{new_path}>" if self.angle else new_path
        return f"{self.lead}{wrapped}{self.anchor}{self.tail}"


def parse_link_payload(inner: str) -> LinkTarget | None:
    """Split a ``](…)`` payload into a :class:`LinkTarget`; ``None`` if empty."""

    lead = inner[: len(inner) - len(inner.lstrip())]
    body = inner.lstrip()
    if not body:
        return None
    angle = body.startswith("<")
    if angle:
        end = body.find(">")
        if end == -1:
            return None
        token, tail = body[1:end], body[end + 1 :]
    else:
        token, sep, rest = body.partition(" ")
        tail = f"{sep}{rest}" if sep else ""
    path, hashsep, frag = token.partition("#")
    anchor = f"{hashsep}{frag}" if hashsep else ""
    return LinkTarget(lead=lead, angle=angle, path=path, anchor=anchor, tail=tail)


def is_bare_relative(path: str) -> bool:
    """True when *path* is an intra-repo relative link this tool may rewrite.

    Skips external (``http(s)``/``mailto``), anchor-only (``#…``), and
    root-absolute (``/…``) targets — none are bare-relative intra-doc links.
    """

    if not path:
        return False
    return not path.startswith(("http://", "https://", "mailto:", "#", "/"))


# --------------------------------------------------------------------------- #
# Resolver                                                                     #
# --------------------------------------------------------------------------- #


@dataclass
class Resolver:
    """Deterministic broken-relative-link → new-target resolver.

    Precomputes the move substitution table, the reverse landing map (new-dir →
    pre-move source dirs), and the ``docs/`` basename index once, so resolution
    of a single link is a pure lookup over that state.
    """

    repo_root: Path
    subs: list[Substitution]
    reverse_landing: list[tuple[str, list[str]]]
    basename_index: dict[str, list[str]]

    @classmethod
    def build(cls, repo_root: Path, occurrence_map_path: Path) -> Resolver:
        pairs = load_moves(occurrence_map_path)
        subs = build_substitutions(pairs, repo_root)
        landing: dict[str, list[str]] = {}
        for old, to in pairs:
            if old in SKIP_MOVE_FROMS:
                continue
            landing.setdefault(resolve_destination(old, to, repo_root), []).append(old)
        reverse = sorted(landing.items(), key=lambda kv: len(kv[0]), reverse=True)
        index: dict[str, list[str]] = {}
        docs = repo_root / DOCS_ROOT
        if docs.is_dir():
            for path in sorted(docs.rglob("*")):
                if path.is_file():
                    rel = path.relative_to(repo_root).as_posix()
                    index.setdefault(path.name, []).append(rel)
        return cls(repo_root, subs, reverse, index)

    # -- pre-move resolution (the moves spine) ----------------------------- #

    def premove_candidates(self, rel_path: str) -> list[str]:
        """Candidate pre-move paths for the current ``docs/`` file *rel_path*.

        A file that landed under a ``moves:`` destination maps back to one (or,
        for many-source landings, several) pre-move source paths; a file that
        never moved is its own pre-move path.
        """

        for new_dir, sources in self.reverse_landing:
            if rel_path == new_dir:
                return list(sources)
            if rel_path.startswith(new_dir + "/"):
                remainder = rel_path[len(new_dir) + 1 :]
                return [posixpath.join(src, remainder) for src in sources]
        return [rel_path]

    def map_forward(self, old_target: str) -> str:
        """Map a pre-move absolute target forward through the moves spine."""

        out = old_target
        for sub in self.subs:
            if out == sub.old:
                out = sub.new
                break
            if out.startswith(sub.old + "/"):
                out = sub.new + out[len(sub.old) :]
                break
        match = re.fullmatch(r"docs/adr/([^/]+)/(.+)", out)
        if match:
            twin = resolve_adr_era_twin(match.group(1), match.group(2), self.repo_root)
            if twin:
                out = f"docs/adr/{twin}/{match.group(2)}"
        return out

    def _exists(self, target_rel: str) -> bool:
        return (self.repo_root / target_rel).exists()

    def resolve_via_spine(self, rel_path: str, link_path: str) -> str | None:
        """Resolve *link_path* (bare-relative) via the pre-move → moves spine.

        Returns the new repo-relative target when every viable pre-move
        candidate agrees on a single existing target; ``None`` when the spine is
        ambiguous (multiple distinct existing targets) or yields nothing.
        """

        candidates = self._era_narrowed(rel_path, self.premove_candidates(rel_path))
        targets: dict[str, str] = {}
        for premove in candidates:
            old_target = posixpath.normpath(
                posixpath.join(posixpath.dirname(premove), link_path)
            )
            new_target = self.map_forward(old_target)
            if self._exists(new_target):
                targets.setdefault(
                    str((self.repo_root / new_target).resolve()), new_target
                )
        if len(targets) == 1:
            return next(iter(targets.values()))
        return None

    def _era_narrowed(self, rel_path: str, candidates: list[str]) -> list[str]:
        """Keep only era-matching candidates when the file carries an era suffix.

        ``docs/architecture/vision/README-2.x.md`` came from the ``2.x`` era
        directory; without this narrowing the depth-1 ``architecture/vision``
        sibling source is a spurious second candidate.
        """

        era_match = _ERA.search(posixpath.basename(rel_path))
        if era_match is None:
            return candidates
        era = era_match.group(1)
        narrowed = [
            cand for cand in candidates if era in _ERA.findall(posixpath.dirname(cand))
        ]
        return narrowed or candidates

    # -- unique-on-disk landing (fallback) --------------------------------- #

    def resolve_unique_on_disk(self, link_path: str) -> str | None:
        """Resolve a broken link by its basename when exactly one file matches.

        The deterministic ground truth for a per-file landing the coarse spine
        missed.  A non-unique basename returns ``None`` (reported, not guessed).
        """

        hits = self.basename_index.get(posixpath.basename(link_path), [])
        return hits[0] if len(hits) == 1 else None

    # -- public single-link entry point ------------------------------------ #

    def resolve(self, rel_path: str, link_path: str) -> tuple[str | None, str]:
        """Resolve a broken bare-relative *link_path* found in file *rel_path*.

        Returns ``(new_relative_link, tier)`` where *tier* is ``"spine"``,
        ``"on-disk"``, or ``"unresolvable"`` (with ``new_relative_link`` ``None``).
        """

        target = self.resolve_via_spine(rel_path, link_path)
        tier = "spine"
        if target is None:
            target = self.resolve_unique_on_disk(link_path)
            tier = "on-disk"
        if target is None:
            return None, "unresolvable"
        new_link = _relative_link(rel_path, target)
        return new_link, tier


def _relative_link(from_file_rel: str, to_target_rel: str) -> str:
    """POSIX relative path from *from_file_rel*'s directory to *to_target_rel*."""

    rel = os.path.relpath(to_target_rel, posixpath.dirname(from_file_rel))
    return Path(rel).as_posix()


# --------------------------------------------------------------------------- #
# File rewriting                                                               #
# --------------------------------------------------------------------------- #


@dataclass
class LinkRewrite:
    file: str
    old_link: str
    new_link: str
    tier: str


@dataclass
class Unresolvable:
    file: str
    link: str


def iter_doc_files(repo_root: Path) -> Iterator[Path]:
    """Yield rewritable ``docs/**/*.md`` files (immutable subtrees excluded)."""

    docs = repo_root / DOCS_ROOT
    if not docs.is_dir():
        return
    for path in sorted(docs.rglob("*.md")):
        rel = path.relative_to(repo_root).as_posix()
        if not rel.startswith(EXCLUDE_PREFIXES):
            yield path


def rewrite_body(
    body: str, rel_path: str, resolver: Resolver
) -> tuple[str, list[LinkRewrite], list[Unresolvable]]:
    """Rewrite broken bare-relative links in *body*; collect outcomes.

    Already-resolving links are left untouched (idempotency); unresolvable ones
    are recorded, never rewritten.
    """

    rewrites: list[LinkRewrite] = []
    unresolved: list[Unresolvable] = []
    file_dir = posixpath.dirname(rel_path)

    def _sub(match: re.Match[str]) -> str:
        parsed = parse_link_payload(match.group(1))
        if parsed is None or not is_bare_relative(parsed.path):
            return match.group(0)
        current = posixpath.normpath(posixpath.join(file_dir, parsed.path))
        if (resolver.repo_root / current).exists():
            return match.group(0)
        new_link, tier = resolver.resolve(rel_path, parsed.path)
        if new_link is None:
            unresolved.append(Unresolvable(file=rel_path, link=parsed.path))
            return match.group(0)
        rewrites.append(
            LinkRewrite(
                file=rel_path, old_link=parsed.path, new_link=new_link, tier=tier
            )
        )
        return "](" + parsed.render(new_link) + ")"

    return _LINK.sub(_sub, body), rewrites, unresolved


@dataclass
class FixReport:
    rewrites: list[LinkRewrite] = field(default_factory=list)
    unresolvable: list[Unresolvable] = field(default_factory=list)
    changed_files: int = 0

    @property
    def total_rewrites(self) -> int:
        return len(self.rewrites)


def run(
    repo_root: Path, occurrence_map_path: Path, *, dry_run: bool = False
) -> FixReport:
    """Fix (or, when *dry_run*, plan) broken bare-relative body links in ``docs/``."""

    resolver = Resolver.build(repo_root, occurrence_map_path)
    report = FixReport()
    for path in iter_doc_files(repo_root):
        rel = path.relative_to(repo_root).as_posix()
        text = path.read_text(encoding="utf-8")
        frontmatter, body = split_frontmatter(text)
        new_body, rewrites, unresolved = rewrite_body(body, rel, resolver)
        report.unresolvable.extend(unresolved)
        if not rewrites or new_body == body:
            continue
        report.rewrites.extend(rewrites)
        report.changed_files += 1
        if not dry_run:
            path.write_text(frontmatter + new_body, encoding="utf-8")
    return report


def check_dead_body_links(repo_root: Path) -> list[Unresolvable]:
    """Report every bare-relative body link in ``docs/`` that fails to resolve.

    The body-link-resolution gate (T101): report-only here, WP14 flips it
    blocking.  Complements WP08's anchored-ADR :func:`find_dead_twinned_adr_links`
    by covering the bare-relative link class.  Pure on-disk resolution — it asks
    only "does this link resolve from where it now lives", independent of how the
    fixer healed it.
    """

    dead: list[Unresolvable] = []
    for path in iter_doc_files(repo_root):
        rel = path.relative_to(repo_root).as_posix()
        _, body = split_frontmatter(path.read_text(encoding="utf-8"))
        file_dir = posixpath.dirname(rel)
        for match in _LINK.finditer(body):
            parsed = parse_link_payload(match.group(1))
            if parsed is None or not is_bare_relative(parsed.path):
                continue
            current = posixpath.normpath(posixpath.join(file_dir, parsed.path))
            if not (repo_root / current).exists():
                dead.append(Unresolvable(file=rel, link=parsed.path))
    return dead


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--occurrence-map", type=Path, default=None)
    parser.add_argument(
        "--dry-run", action="store_true", help="Print planned rewrites; write nothing."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Body-link-resolution gate: report dead bare-relative links (report-only).",
    )
    return parser.parse_args(argv)


def _print_report(report: FixReport, mode: str) -> None:
    print(f"[relative_link_fixer] {mode}: {report.total_rewrites} rewrites "
          f"across {report.changed_files} files")
    for rw in report.rewrites:
        print(f"  [{rw.tier:7s}] {rw.file}: {rw.old_link}  ->  {rw.new_link}")
    if report.unresolvable:
        print(f"[relative_link_fixer] UNRESOLVABLE ({len(report.unresolvable)}) "
              "— reported, never guessed:")
        for un in report.unresolvable:
            print(f"  {un.file}: {un.link}")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root: Path = args.repo_root.resolve()
    occ = args.occurrence_map or (repo_root / DEFAULT_OCCURRENCE_MAP)

    if args.check:
        dead = check_dead_body_links(repo_root)
        print(f"[relative_link_fixer] CHECK: {len(dead)} dead bare-relative body links")
        for un in dead:
            print(f"  {un.file}: {un.link}")
        # Mission B / WP14 flips this body-link-resolution gate to blocking: any
        # dead bare-relative body link reds CI (was report-only in WP18).
        return 1 if dead else 0

    report = run(repo_root, occ, dry_run=args.dry_run)
    _print_report(report, "DRY-RUN" if args.dry_run else "APPLIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
