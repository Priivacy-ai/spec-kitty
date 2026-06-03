"""Post-process generated DocFX output with static SEO metadata."""

from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import quote


DEFAULT_BASE_URL = "https://docs.spec-kitty.ai/"
DEFAULT_IMAGE = "assets/images/logo_small.webp"

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
DESCRIPTION_RE = re.compile(
    r'<meta\s+name="description"\s+content="(.*?)"\s*/?>',
    re.IGNORECASE | re.DOTALL,
)
HEAD_CLOSE_RE = re.compile(r"</head>", re.IGNORECASE)
SEO_BLOCK_RE = re.compile(
    r"\n?\s*<!-- spec-kitty-seo:start -->.*?<!-- spec-kitty-seo:end -->\n?",
    re.IGNORECASE | re.DOTALL,
)
ROBOTS_RE = re.compile(r'<meta\s+name="robots"\s+content="([^"]+)"', re.IGNORECASE)


@dataclass(frozen=True)
class Page:
    path: Path
    relative_path: str
    title: str
    description: str
    url: str


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/") + "/"


def canonical_url(base_url: str, relative_path: str) -> str:
    base = normalize_base_url(base_url)
    rel = relative_path.replace("\\", "/")
    if rel == "index.html":
        return base
    if rel.endswith("/index.html"):
        rel = rel[: -len("index.html")]
    return base + quote(rel, safe="/.-_~")


def should_index(relative_path: str, markup: str) -> bool:
    rel = relative_path.replace("\\", "/")
    if rel.endswith("/toc.html") or rel == "toc.html":
        return False
    if rel.startswith("assets/"):
        return False
    if 'http-equiv="refresh"' in markup.lower():
        return False
    robots = ROBOTS_RE.search(markup)
    if robots and "noindex" in robots.group(1).lower():
        return False
    return True


def extract_title(markup: str) -> str:
    match = TITLE_RE.search(markup)
    if not match:
        return "Spec Kitty Documentation"
    title = html.unescape(re.sub(r"\s+", " ", match.group(1))).strip()
    return title.replace(" | Spec Kitty Documentation", "").strip() or "Spec Kitty Documentation"


def extract_description(markup: str) -> str:
    match = DESCRIPTION_RE.search(markup)
    if not match:
        return "Spec Kitty documentation for CLI workflows, governed missions, AI harnesses, and 3.2 upgrades."
    return html.unescape(re.sub(r"\s+", " ", match.group(1))).strip()


def breadcrumb_items(page: Page, base_url: str) -> list[dict[str, object]]:
    parts = page.relative_path.replace("\\", "/").split("/")
    crumbs: list[dict[str, object]] = [
        {"@type": "ListItem", "position": 1, "name": "Spec Kitty Docs", "item": normalize_base_url(base_url)}
    ]
    running: list[str] = []
    for part in parts[:-1]:
        running.append(part)
        name = part.replace("-", " ").replace("_", " ").title()
        crumbs.append(
            {
                "@type": "ListItem",
                "position": len(crumbs) + 1,
                "name": name,
                "item": canonical_url(base_url, "/".join(running + ["index.html"])),
            }
        )
    if page.relative_path != "index.html":
        crumbs.append(
            {"@type": "ListItem", "position": len(crumbs) + 1, "name": page.title, "item": page.url}
        )
    return crumbs


def seo_block(page: Page, base_url: str, image_path: str) -> str:
    image_url = normalize_base_url(base_url) + quote(image_path.lstrip("/"), safe="/.-_~")
    json_ld = [
        {
            "@context": "https://schema.org",
            "@type": "TechArticle" if page.relative_path != "index.html" else "WebPage",
            "headline": page.title,
            "description": page.description,
            "url": page.url,
            "inLanguage": "en",
            "isPartOf": {
                "@type": "WebSite",
                "name": "Spec Kitty Documentation",
                "url": normalize_base_url(base_url),
            },
            "publisher": {
                "@type": "Organization",
                "name": "Spec Kitty",
                "url": "https://github.com/Priivacy-ai/spec-kitty",
            },
            "about": ["Spec Kitty", "AI coding agents", "spec-driven development", "CLI documentation"],
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": breadcrumb_items(page, base_url),
        },
    ]
    escaped_title = html.escape(page.title, quote=True)
    escaped_desc = html.escape(page.description, quote=True)
    escaped_url = html.escape(page.url, quote=True)
    escaped_image = html.escape(image_url, quote=True)
    return f"""
      <!-- spec-kitty-seo:start -->
      <link rel="canonical" href="{escaped_url}">
      <meta property="og:site_name" content="Spec Kitty Documentation">
      <meta property="og:type" content="article">
      <meta property="og:title" content="{escaped_title}">
      <meta property="og:description" content="{escaped_desc}">
      <meta property="og:url" content="{escaped_url}">
      <meta property="og:image" content="{escaped_image}">
      <meta name="twitter:card" content="summary">
      <meta name="twitter:title" content="{escaped_title}">
      <meta name="twitter:description" content="{escaped_desc}">
      <meta name="twitter:image" content="{escaped_image}">
      <script type="application/ld+json">{json.dumps(json_ld, ensure_ascii=False, separators=(",", ":"))}</script>
      <!-- spec-kitty-seo:end -->
"""


def noindex_block() -> str:
    return """
      <!-- spec-kitty-seo:start -->
      <meta name="robots" content="noindex, follow">
      <!-- spec-kitty-seo:end -->
"""


def process_html(site_dir: Path, base_url: str, image_path: str) -> list[Page]:
    pages: list[Page] = []
    for path in sorted(site_dir.rglob("*.html")):
        relative_path = path.relative_to(site_dir).as_posix()
        markup = path.read_text(encoding="utf-8")
        markup = SEO_BLOCK_RE.sub("", markup)
        if should_index(relative_path, markup):
            page = Page(
                path=path,
                relative_path=relative_path,
                title=extract_title(markup),
                description=extract_description(markup),
                url=canonical_url(base_url, relative_path),
            )
            block = seo_block(page, base_url, image_path)
            pages.append(page)
        else:
            block = noindex_block()
        markup = HEAD_CLOSE_RE.sub(block + "  </head>", markup, count=1)
        path.write_text(markup, encoding="utf-8")
    return pages


def write_sitemap(site_dir: Path, pages: list[Page]) -> None:
    today = date.today().isoformat()
    urls = "\n".join(
        f"  <url><loc>{html.escape(page.url)}</loc><lastmod>{today}</lastmod></url>" for page in pages
    )
    site_dir.joinpath("sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n"
        "</urlset>\n",
        encoding="utf-8",
    )


def write_robots(site_dir: Path, base_url: str) -> None:
    site_dir.joinpath("robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /toc.html\n"
        "Disallow: /*/toc.html\n"
        f"Sitemap: {normalize_base_url(base_url)}sitemap.xml\n",
        encoding="utf-8",
    )


def write_cname(site_dir: Path, base_url: str) -> None:
    host = normalize_base_url(base_url).removeprefix("https://").removeprefix("http://").strip("/")
    if host:
        site_dir.joinpath("CNAME").write_text(host + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", type=Path, default=Path("docs/_site"))
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    args = parser.parse_args(argv)

    site_dir = args.site_dir.resolve()
    if not site_dir.is_dir():
        raise SystemExit(f"Site directory not found: {site_dir}")

    pages = process_html(site_dir, args.base_url, args.image)
    write_sitemap(site_dir, pages)
    write_robots(site_dir, args.base_url)
    write_cname(site_dir, args.base_url)
    site_dir.joinpath(".nojekyll").write_text("", encoding="utf-8")
    print(f"SEO postprocess complete: {len(pages)} indexed HTML pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
