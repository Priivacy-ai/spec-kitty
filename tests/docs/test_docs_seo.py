"""SEO/GEO checks for the published DocFX documentation site."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
sys.path.insert(0, str(REPO_ROOT))

from scripts.docs import seo_postprocess  # noqa: E402
from scripts.docs._inventory import parse_frontmatter  # noqa: E402
from scripts.docs._published_pages import resolve_published_pages  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.fast]


FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


def _published_markdown_files() -> list[Path]:
    """Every published source page, per ``docs/docfx.json``.

    This used to be a hardcoded ten-pattern glob list maintained here. It
    predated the ``how-to/`` → ``guides/`` and ``reference/slash-commands`` →
    ``api/`` moves: the DocFX build followed those moves and this list did not,
    so the SEO gate silently shrank to 16 of 674 pages while reporting green.
    The list is gone rather than updated — an updated second list is the same
    bug with fresh paint. The build's own declaration is now the only authority,
    and it fails closed if it ever resolves a collapsed set.
    """
    resolved = resolve_published_pages(docs_root=DOCS_DIR)
    return sorted(REPO_ROOT / page for page in resolved.pages)


def _frontmatter(path: Path) -> dict[str, str]:
    """Parse ``path``'s front matter with the repository's canonical YAML reader.

    This used to be a hand-rolled ``split(":", 1)`` loop — a *second* front
    matter parser that disagreed with the one every other docs tool uses. It
    kept the surrounding quotes on ``description: '…'`` (two phantom characters,
    enough to push a valid 180-char description over the ceiling) and read past
    the ``#`` that starts a YAML comment in an unquoted scalar. Both disagreements
    are the same class of defect this module's page-set fix repairs: two answers
    to one question. DocFX parses real YAML, so the gate must too.
    """
    text = path.read_text(encoding="utf-8")
    assert FRONTMATTER_RE.match(text), (
        f"{path.relative_to(REPO_ROOT)} must start with YAML front matter"
    )
    return {
        key: value
        for key, value in parse_frontmatter(text).items()
        if isinstance(key, str) and isinstance(value, str)
    }


@pytest.mark.parametrize("path", _published_markdown_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_published_pages_have_title_and_description(path: Path) -> None:
    metadata = _frontmatter(path)
    assert metadata.get("title"), f"{path.relative_to(REPO_ROOT)} missing title"
    description = metadata.get("description")
    assert description, f"{path.relative_to(REPO_ROOT)} missing description"
    assert 50 <= len(description) <= 180, f"{path.relative_to(REPO_ROOT)} description length is off: {len(description)}"


def test_static_seo_files_exist() -> None:
    for relative_path in ["robots.txt", "CNAME", ".nojekyll", "llms.txt"]:
        assert (DOCS_DIR / relative_path).is_file(), f"Missing docs/{relative_path}"


def test_seo_postprocess_injects_static_metadata(tmp_path: Path) -> None:
    site = tmp_path / "_site"
    site.mkdir()
    html = """<!doctype html>
<html>
<head>
  <title>Getting Started | Spec Kitty Documentation </title>
  <meta name="description" content="Install Spec Kitty 3.2 and run a first mission.">
</head>
<body><h1>Getting Started</h1></body>
</html>
"""
    (site / "index.html").write_text(html, encoding="utf-8")
    nested = site / "how-to"
    nested.mkdir()
    (nested / "toc.html").write_text("<html><head><title>TOC</title></head><body></body></html>", encoding="utf-8")

    pages = seo_postprocess.process_html(site, "https://docs.spec-kitty.ai/", "assets/images/logo_small.webp")
    seo_postprocess.write_sitemap(site, pages)
    seo_postprocess.write_robots(site, "https://docs.spec-kitty.ai/")

    rendered = (site / "index.html").read_text(encoding="utf-8")
    assert '<link rel="canonical" href="https://docs.spec-kitty.ai/">' in rendered
    assert 'property="og:title"' in rendered
    assert 'name="twitter:card"' in rendered
    assert 'application/ld+json' in rendered

    toc_rendered = (nested / "toc.html").read_text(encoding="utf-8")
    assert 'name="robots" content="noindex, follow"' in toc_rendered

    sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
    assert "https://docs.spec-kitty.ai/" in sitemap
    assert "toc.html" not in sitemap

    robots = (site / "robots.txt").read_text(encoding="utf-8")
    assert "Sitemap: https://docs.spec-kitty.ai/sitemap.xml" in robots
