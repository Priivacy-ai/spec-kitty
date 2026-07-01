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

pytestmark = [pytest.mark.unit, pytest.mark.fast]


FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)


def _published_markdown_files() -> list[Path]:
    patterns = [
        "index.md",
        "tutorials/*.md",
        "how-to/*.md",
        "how-to/harnesses/*.md",
        "reference/*.md",
        "explanation/*.md",
        "recovery/*.md",
        "3x/**/*.md",
        "archive/**/*.md",
        "migration/**/*.md",
    ]
    files: set[Path] = set()
    for pattern in patterns:
        files.update(path for path in DOCS_DIR.glob(pattern) if path.is_file() and not path.name.startswith("_"))
    return sorted(files)


def _frontmatter(path: Path) -> dict[str, str]:
    match = FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
    assert match, f"{path.relative_to(REPO_ROOT)} must start with YAML front matter"
    result: dict[str, str] = {}
    for line in match.group("body").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip('"')
    return result


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
