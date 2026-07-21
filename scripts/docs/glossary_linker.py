"""Auto-link the first mention of every glossary term across rendered doc pages.

**Requirement**: FR-011, NFR-004. **Contract**: ``contracts/glossary-linker-contract.md``
in the ``docs-ia-onboarding-overhaul-01KY02JB`` mission.

What this does
---------------
Walks every rendered HTML page under the DocFX build output (``docs/_site`` by
default — see ``docs/docfx.json``'s ``build.dest``), excluding
``kitty-specs/glossary.html`` itself, and wraps the **first** case-insensitive
occurrence of each glossary term's ``surface`` string in a link to its anchor on
the glossary page:

    <a href="/kitty-specs/glossary.html#term-{anchor_id}"
       class="glossary-link" title="{definition}">{original matched text}</a>

Every later occurrence of the same term on the same page is left untouched
(NFR-004). Text inside ``<code>``, ``<pre>``, ``<script>``, ``<style>``, and the
inner text of existing ``<a>`` tags is never linked. Longer term surfaces win
over surfaces that are a substring of them (longest-match-first). This is a
pure **HTML post-processing** pass — no markdown source file is ever read or
written (Decision Moment ``01KY03YGX7GQEBKV45Q2Q8FXK3``).

``anchor_id`` is computed by :func:`scripts.docs.generate_kitty_specs_docs.assign_anchor_ids`
— the same function ``glossary_page()`` uses to render ``id="term-{anchor_id}"``
on each glossary card — so this module never re-derives the slugify/collision
algorithm; it imports the single source of truth instead.

Where this runs in the pipeline (T037 — documented, not wired; see below)
---------------------------------------------------------------------------
Per this mission's ``C-001`` ("Deployment/build tooling ... is out of scope;
only content, structure, and DocFX TOC/file-list configuration change") this WP
does **not** edit ``.github/workflows/docs-pages.yml``. The docs build also only
runs in CI (``redirect_stub_generator.py``'s own docstring notes there is no
local DocFX build), so this module cannot be exercised end-to-end locally
either. Both are documented here for whoever wires it in:

Today ``.github/workflows/docs-pages.yml``'s ``build`` job runs, in order::

    python3 scripts/docs/generate_kitty_specs_docs.py
    docfx docfx.json                              # (from docs/) -> docs/_site
    python3 scripts/docs/seo_postprocess.py
    python3 scripts/docs/redirect_stub_generator.py generate --site-dir docs/_site
    python3 scripts/docs/redirect_stub_generator.py coverage --site-dir docs/_site

This linker belongs **after** the DocFX render step (it needs rendered HTML,
not markdown) and **alongside** ``seo_postprocess.py`` — i.e. it should run
right after (or right before) the ``seo_postprocess.py`` invocation, and
**before** the redirect-stub generation step (redirect stubs are meta-refresh
placeholder pages; they should not have glossary links injected, and running
the linker first keeps the no-404 stub-coverage check operating on the final
page set). The added step would be::

    python3 scripts/docs/glossary_linker.py --site-dir docs/_site

with no other arguments required (it defaults to the same ``docs/_site`` and
``.kittify/glossaries/spec_kitty_core.yaml`` paths the rest of the pipeline
already uses). A future WP or the pipeline owner can add that single line to
``docs-pages.yml`` without re-deriving this design.

Failure mode
------------
If the glossary seed fails to load, or produces zero usable terms, or an
individual term is missing its ``surface``/``anchor_id``, this module logs a
warning to stderr and skips linking (that term, or the whole pass) rather than
failing the build — a broken glossary link is a UX bug, not a publish blocker.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

# ``scripts.docs`` is a namespace-package module; when this file is invoked as a
# bare script (``python scripts/docs/glossary_linker.py``) the repo root is not
# on ``sys.path``. Anchor it so the shared anchor-id algorithm resolves to the
# canonical implementation in ``generate_kitty_specs_docs`` rather than a forked
# copy — mirrors the bootstrap used by ``scripts/docs/adr_converter.py``.
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.docs.generate_kitty_specs_docs import (  # noqa: E402  (sys.path bootstrap above)
    GLOSSARY_SEED,
    assign_anchor_ids,
    parse_glossary_seed,
)


DEFAULT_SITE_DIR = Path("docs/_site")
GLOSSARY_PAGE_RELATIVE = "kitty-specs/glossary.html"
GLOSSARY_HREF_PREFIX = "/kitty-specs/glossary.html#term-"
GLOSSARY_LINK_CLASS = "glossary-link"

SKIP_TAG_NAMES: Final[frozenset[str]] = frozenset({"code", "pre", "script", "style", "a"})
VOID_ELEMENTS: Final[frozenset[str]] = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
)

_TAG_SPLIT_RE = re.compile(r"(<[^>]+>)")
_TAG_NAME_RE = re.compile(r"^</?\s*([a-zA-Z][a-zA-Z0-9:_-]*)")


@dataclass(frozen=True)
class LinkTerm:
    """A glossary term ready to be matched/linked in rendered HTML."""

    surface: str
    anchor_id: str
    definition: str


def load_link_terms(seed_path: Path = GLOSSARY_SEED) -> list[LinkTerm]:
    """Load glossary terms and compute their anchor ids.

    Per the contract's failure mode: a seed that cannot be read, or an
    individual term missing ``surface``/``anchor_id``, is logged and skipped
    rather than raised — this function never lets a bad glossary entry crash
    the whole docs build.
    """
    try:
        raw_terms = parse_glossary_seed(seed_path)
    except OSError as exc:
        print(f"WARNING: glossary_linker: could not read glossary seed {seed_path}: {exc}", file=sys.stderr)
        return []

    if not raw_terms:
        print(f"WARNING: glossary_linker: glossary seed {seed_path} produced no terms", file=sys.stderr)
        return []

    link_terms: list[LinkTerm] = []
    for term in assign_anchor_ids(raw_terms):
        surface = str(term.get("surface") or "").strip()
        anchor_id = str(term.get("anchor_id") or "").strip()
        definition = str(term.get("definition") or "").strip()
        if not surface or not anchor_id:
            print(f"WARNING: glossary_linker: skipping term with missing surface/anchor_id: {term!r}", file=sys.stderr)
            continue
        link_terms.append(LinkTerm(surface=surface, anchor_id=anchor_id, definition=definition))
    return link_terms


def build_pattern(terms: list[LinkTerm]) -> re.Pattern[str] | None:
    """Compile a single alternation regex, longest surface first.

    Python's ``re`` alternation tries branches left-to-right and takes the
    first one that matches at a given position, so sorting the alternatives by
    descending ``surface`` length (a stable sort, so ties keep seed-file order)
    makes the compiled pattern prefer the longest possible term at every
    position — exactly the longest-match-first rule in the contract.
    """
    if not terms:
        return None
    ordered = sorted(terms, key=lambda term: -len(term.surface))
    alternation = "|".join(re.escape(term.surface) for term in ordered)
    return re.compile(rf"(?<![A-Za-z0-9_])(?:{alternation})(?![A-Za-z0-9_])", re.IGNORECASE)


def _tag_name(token: str) -> str | None:
    match = _TAG_NAME_RE.match(token)
    return match.group(1).lower() if match else None


def _is_closing_tag(token: str) -> bool:
    return token.lstrip().startswith("</")


def _is_self_closing_tag(token: str, name: str | None) -> bool:
    return token.rstrip().endswith("/>") or name in VOID_ELEMENTS


def _replace_first_mentions(
    text: str, pattern: re.Pattern[str], term_by_key: dict[str, LinkTerm], linked: set[str]
) -> tuple[str, int]:
    """Link the first not-yet-linked term match in ``text``; leave the rest untouched."""
    added = 0

    def _replace(match: re.Match[str]) -> str:
        nonlocal added
        matched_text = match.group(0)
        term = term_by_key.get(matched_text.lower())
        if term is None or term.anchor_id in linked:
            return matched_text
        linked.add(term.anchor_id)
        added += 1
        href = f"{GLOSSARY_HREF_PREFIX}{term.anchor_id}"
        title = html.escape(term.definition, quote=True)
        return f'<a href="{href}" class="{GLOSSARY_LINK_CLASS}" title="{title}">{matched_text}</a>'

    return pattern.sub(_replace, text), added


def link_page_html(markup: str, pattern: re.Pattern[str], term_by_key: dict[str, LinkTerm]) -> tuple[str, int]:
    """Walk ``markup``'s text nodes and link the first mention of each term.

    Tags (and their attribute text) are never scanned — only the text runs
    between tags are candidates. A small stack of currently-open
    ``SKIP_TAG_NAMES`` tracks whether the current text run is inside
    ``<code>``/``<pre>``/``<script>``/``<style>``/``<a>``, which must never be
    linked into (and, for ``<a>``, never linked *again*).
    """
    linked: set[str] = set()
    total_added = 0
    skip_stack: list[str] = []
    output: list[str] = []

    for token in _TAG_SPLIT_RE.split(markup):
        if not token:
            continue
        if token.startswith("<") and token.endswith(">"):
            name = _tag_name(token)
            if name in SKIP_TAG_NAMES:
                if _is_closing_tag(token):
                    if skip_stack and skip_stack[-1] == name:
                        skip_stack.pop()
                elif not _is_self_closing_tag(token, name):
                    skip_stack.append(name)
            output.append(token)
            continue
        if skip_stack:
            output.append(token)
            continue
        new_text, added = _replace_first_mentions(token, pattern, term_by_key, linked)
        total_added += added
        output.append(new_text)

    return "".join(output), total_added


def process_directory(site_dir: Path, terms: list[LinkTerm]) -> int:
    """Link every rendered HTML page under ``site_dir`` (except the glossary itself).

    Returns the total number of term links inserted across all pages.
    """
    pattern = build_pattern(terms)
    if pattern is None:
        print("WARNING: glossary_linker: no glossary terms available, skipping linking pass", file=sys.stderr)
        return 0

    term_by_key = {term.surface.lower(): term for term in terms}
    total_links = 0
    pages_touched = 0
    for path in sorted(site_dir.rglob("*.html")):
        relative_path = path.relative_to(site_dir).as_posix()
        if relative_path == GLOSSARY_PAGE_RELATIVE:
            continue
        markup = path.read_text(encoding="utf-8")
        new_markup, added = link_page_html(markup, pattern, term_by_key)
        if added:
            path.write_text(new_markup, encoding="utf-8")
            total_links += added
            pages_touched += 1

    print(f"glossary_linker: inserted {total_links} glossary link(s) across {pages_touched} page(s)")
    return total_links


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", type=Path, default=DEFAULT_SITE_DIR)
    parser.add_argument("--glossary-seed", type=Path, default=GLOSSARY_SEED)
    args = parser.parse_args(argv)

    site_dir = args.site_dir.resolve()
    if not site_dir.is_dir():
        raise SystemExit(f"Site directory not found: {site_dir}")

    terms = load_link_terms(args.glossary_seed)
    process_directory(site_dir, terms)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
