"""Tests for the docsite PlantUML render post-processor (WP02).

Pure-logic tests (fence recovery, caption derivation, accessible-SVG wrapping,
fail-closed on an unrendered fence) run everywhere. The real network-isolated
render round-trip is docker-gated (mirrors the WP01 spike); it downloads +
sha256-verifies the pinned jar, then renders through the isolated container.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOCS_DIR = _REPO_ROOT / "scripts" / "docs"
if str(_DOCS_DIR) not in sys.path:
    sys.path.insert(0, str(_DOCS_DIR))

import plantuml_invoke  # noqa: E402
import plantuml_render  # noqa: E402


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True, check=False).returncode == 0


def _ensure_jar() -> Path:
    jar = _REPO_ROOT / "plantuml.jar"
    pins = plantuml_invoke.load_pins()
    if not jar.exists():
        urllib.request.urlretrieve(pins.plantuml_jar_url, jar)  # noqa: S310 - pinned https URL
    plantuml_invoke.verify_jar_sha256(jar, pins.plantuml_jar_sha256)
    return jar


_docker = pytest.mark.skipif(not _docker_available(), reason="docker unavailable")


def _page(fence_class: str, title: str) -> str:
    body = f"@startyaml&#10;title {title}&#10;profile_id: &quot;x&quot;&#10;@endyaml&#10;"
    return f'<html><body><pre><code class="{fence_class}">{body}</code></pre></body></html>'


# ---- pure-logic (no docker) ----------------------------------------------------


def test_fence_regex_matches_both_class_conventions() -> None:
    for cls in ("lang-plantuml", "language-plantuml"):
        assert plantuml_render._FENCE_RE.search(_page(cls, "T"))


def test_derive_caption_rejects_trivial() -> None:
    assert plantuml_render.derive_caption("@startyaml\ntitle Real Title\nx: 1\n") == "Real Title"
    with pytest.raises(plantuml_render.PlantumlRenderPageError):
        plantuml_render.derive_caption("@startyaml\ntitle diagram\nx: 1\n")
    with pytest.raises(plantuml_render.PlantumlRenderPageError):
        plantuml_render.derive_caption("@startyaml\nx: 1\n")  # no title at all


def test_accessible_svg_sets_role_aria_and_title() -> None:
    out = plantuml_render._accessible_svg(b'<svg width="10"><g/></svg>', "Agent Profile Schema")
    assert 'role="img"' in out
    assert 'aria-label="Agent Profile Schema"' in out
    assert "<title>Agent Profile Schema</title>" in out
    assert out.startswith("<figure")


def test_unrendered_fence_fails_closed() -> None:
    # A plantuml fence under an unmatched class: the regex won't sub it, the @start
    # survives, and the page must fail closed rather than ship an empty diagram.
    bad = '<pre><code class="lang-puml">@startyaml&#10;title X&#10;@endyaml</code></pre>'
    with pytest.raises(plantuml_render.PlantumlRenderPageError):
        plantuml_render.render_html(bad, workdir=_REPO_ROOT)


def test_mermaid_block_is_untouched() -> None:
    mermaid = '<pre><code class="lang-mermaid">graph TD; A--&gt;B;</code></pre>'
    assert plantuml_render.render_html(mermaid, workdir=_REPO_ROOT) == mermaid


# ---- docker-gated render round-trip -------------------------------------------


@_docker
def test_round_trip_renders_svg_with_exact_literal_alt(tmp_path: Path) -> None:
    _ensure_jar()
    for cls in ("lang-plantuml", "language-plantuml"):
        out = plantuml_render.render_html(_page(cls, "Round Trip Alpha"), workdir=tmp_path)
        assert "<svg" in out and 'role="img"' in out
        assert 'aria-label="Round Trip Alpha"' in out  # exact literal title, not generic
        assert "@startyaml" not in out  # fence fully consumed
        assert not plantuml_invoke.svg_is_error(out.encode("utf-8"))


@_docker
def test_two_diagrams_get_distinct_alt(tmp_path: Path) -> None:
    _ensure_jar()
    two = _page("lang-plantuml", "Alpha One") + _page("language-plantuml", "Beta Two")
    out = plantuml_render.render_html(two, workdir=tmp_path)
    assert 'aria-label="Alpha One"' in out
    assert 'aria-label="Beta Two"' in out
