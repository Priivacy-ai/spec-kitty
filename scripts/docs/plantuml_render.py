"""Docsite PlantUML render post-processor (WP02).

Runs AFTER ``glossary_linker`` over ``docs/_site``: recovers ` ```plantuml `
fences that DocFX rendered to ``<pre><code class="lang-plantuml">…</code></pre>``
(markdig may emit ``lang-`` or ``language-``; both are matched), renders each to
an inline SVG via the network-isolated :mod:`plantuml_invoke` seam (WP01), and
replaces the fence with an accessible ``<figure>`` carrying derived alt/aria text.

Fail-closed: if a recognized ``@start*`` fence survives unrendered on a page, the
build fails (a class-name mismatch must red the build, never ship empty diagrams).
Stdlib-only (``docs-pages.yml`` has no ``pip install``); the only third-party work
is ``java -jar`` inside the isolated container, owned by :mod:`plantuml_invoke`.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path
from typing import Final

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.docs import plantuml_invoke  # noqa: E402  (sys.path bootstrap above; mirrors glossary_linker)

DEFAULT_SITE_DIR: Final[Path] = Path("docs/_site")
_JAR_PATH: Final[Path] = _REPO_ROOT / "plantuml.jar"

# DocFX/markdig renders a ```plantuml fence to <pre><code class="lang-plantuml">
# (or "language-plantuml"). Match both; capture the escaped payload.
_FENCE_RE: Final[re.Pattern[str]] = re.compile(
    r'<pre><code class="(?:lang|language)-plantuml">(?P<body>.*?)</code></pre>',
    re.DOTALL,
)
# Any surviving @start* after processing is a fence we failed to render.
_UNRENDERED_RE: Final[re.Pattern[str]] = re.compile(r"@start\w+", re.IGNORECASE)
_GENERIC_CAPTIONS: Final[frozenset[str]] = frozenset({"", "yaml", "diagram", "uml"})


class PlantumlRenderPageError(RuntimeError):
    """Raised (fail-closed) when a page cannot be rendered safely."""


def derive_caption(source_text: str) -> str:
    """Alt/aria caption from the PlantUML ``title`` line; reject trivial captions."""
    title = plantuml_invoke.extract_title(source_text)
    caption = (title or "").strip()
    if caption.lower() in _GENERIC_CAPTIONS:
        raise PlantumlRenderPageError(
            f"diagram has no descriptive title (got {caption!r}); every schema diagram "
            "must carry a `title` so its alt text is non-trivial (NFR-005)"
        )
    return caption


def _accessible_svg(svg: bytes, caption: str) -> str:
    """Wrap the SVG in a figure and set role/aria/title from the derived caption."""
    svg_text = svg.decode("utf-8")
    # Set role + aria-label on the root <svg …> and inject a <title> child.
    svg_text = re.sub(
        r"<svg\b",
        f'<svg role="img" aria-label="{html.escape(caption, quote=True)}"',
        svg_text,
        count=1,
    )
    svg_text = re.sub(
        r"(<svg[^>]*>)",
        rf"\1<title>{html.escape(caption)}</title>",
        svg_text,
        count=1,
    )
    return f'<figure class="plantuml-diagram">{svg_text}</figure>'


def render_html(page_html: str, *, workdir: Path) -> str:
    """Render every plantuml fence in one page's HTML; fail closed on leftovers."""
    pins = plantuml_invoke.load_pins()

    def _replace(match: re.Match[str]) -> str:
        source = html.unescape(match.group("body"))
        caption = derive_caption(source)
        svg = plantuml_invoke.render_startyaml(
            source, workdir=workdir, jar_path=_JAR_PATH, pins=pins
        )
        return _accessible_svg(svg, caption)

    rendered = _FENCE_RE.sub(_replace, page_html)
    if _UNRENDERED_RE.search(rendered):
        raise PlantumlRenderPageError(
            "an @start* fence survived unrendered — the emitted code class did not match "
            "`lang-plantuml`/`language-plantuml`; refusing to ship empty diagrams"
        )
    return rendered


def process_site(site_dir: Path, *, workdir: Path | None = None) -> int:
    """Render plantuml fences across the built site. Returns the pages changed."""
    work = workdir or _REPO_ROOT
    changed = 0
    for page in sorted(site_dir.rglob("*.html")):
        original = page.read_text(encoding="utf-8")
        if "plantuml" not in original:
            continue
        rendered = render_html(original, workdir=work)
        if rendered != original:
            page.write_text(rendered, encoding="utf-8")
            changed += 1
    return changed


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    site_dir = Path(args[0]) if args else DEFAULT_SITE_DIR
    changed = process_site(site_dir)
    print(f"plantuml_render: rendered diagrams on {changed} page(s) under {site_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
