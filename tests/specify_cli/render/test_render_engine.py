"""Tests for the D2 narrow markdown renderer engine (specify_cli.render).

Fixture rows map to m1-contract-drafts/D2.md §4 (matrix IDs are noted per test).
Covers WP01: DOM (D1), unsafe-Markdown (D7-D8), public-redaction (D9-D10),
private-content (D11-D12), visual-parity (D13-D14), fault (D19-D20).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

from specify_cli.render import NarrowRenderError, RenderedDocument, render_markdown


def _render(source: str, asset_root: Path, **kwargs: Any) -> RenderedDocument:
    return render_markdown(source, asset_root=asset_root, **kwargs)


# --- D1: no raw HTML passthrough --------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        "<svg onload=alert(1)>",
        '<div onclick="alert(1)">x</div>',
        '<a onmouseover="alert(1)">x</a>',
        "<body onload=alert(1)>",
    ],
)
def test_d1_no_raw_html_passthrough(tmp_path: Path, payload: str) -> None:
    import re

    doc = _render(f"Hello {payload} world", tmp_path)
    lowered = doc.html.lower()
    # No LIVE (unescaped) tag or event-handler attribute may appear: the
    # source's literal `<` must always have been turned into `&lt;` before
    # any tag name, so no real DOM element/attribute is ever constructed.
    assert re.search(r"<(script|img|svg|div|a|body)[\s>]", lowered) is None
    assert re.search(r"<[a-z][^&]*\son[a-z]+\s*=", lowered) is None
    # The source text must survive as escaped literal text, not be silently
    # dropped — §3.2's "escaped as text, matching renderer #2's esc()-first
    # discipline" (D2.md §4 row D1).
    assert "&lt;" in doc.html
    assert "alert(1)" in doc.html


# --- D7: unsafe URL schemes rejected for link and image ---------------------------


@pytest.mark.parametrize(
    "scheme",
    ["javascript", "data", "vbscript", "file"],
)
def test_d7_unsafe_link_scheme_rejected(tmp_path: Path, scheme: str) -> None:
    payload = "javascript:alert(1)" if scheme == "javascript" else f"{scheme}:something"
    doc = _render(f"[link]({payload})", tmp_path)
    assert "href=" not in doc.html
    assert "link" in doc.html  # link text retained
    assert any(w.startswith(f"link_scheme_rejected:{scheme}") for w in doc.warnings), doc.warnings


@pytest.mark.parametrize(
    "scheme",
    ["javascript", "data", "vbscript", "file"],
)
def test_d7_unsafe_image_scheme_rejected(tmp_path: Path, scheme: str) -> None:
    payload = f"{scheme}:something"
    doc = _render(f"![img]({payload})", tmp_path)
    assert "src=" not in doc.html
    assert any(w.startswith(f"image_scheme_rejected:{scheme}") for w in doc.warnings), doc.warnings


def test_d7_javascript_alt_case_and_whitespace_rejected(tmp_path: Path) -> None:
    doc = _render("[link]( JaVaScRiPt:alert(1) )", tmp_path)
    assert "href=" not in doc.html
    assert any(w.startswith("link_scheme_rejected:javascript") for w in doc.warnings)


# --- D8: https accepted, case-insensitive/whitespace-tolerant ---------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://EXAMPLE.com/x",
        "HTTPS://example.com",
        " https://example.com ",
    ],
)
def test_d8_https_accepted_case_and_whitespace_tolerant(tmp_path: Path, url: str) -> None:
    doc = _render(f"[link]({url})", tmp_path)
    assert 'rel="noopener noreferrer nofollow"' in doc.html
    assert 'target="_blank"' in doc.html
    assert "href=" in doc.html


def test_d8_mailto_accepted_unmodified(tmp_path: Path) -> None:
    doc = _render("[email](mailto:person@example.com)", tmp_path)
    assert 'href="mailto:person@example.com"' in doc.html


# --- D9: HTML comments stripped entirely -------------------------------------------


def test_d9_html_comment_stripped(tmp_path: Path) -> None:
    doc = _render("before\n\n<!-- internal note: <secret> -->\n\nafter", tmp_path)
    assert "internal note" not in doc.html
    assert "secret" not in doc.html
    assert "<!--" not in doc.html
    assert "before" in doc.html
    assert "after" in doc.html


# --- D10: absolute paths in code blocks stay inert text -----------------------------


def test_d10_absolute_path_in_code_block_stays_inert(tmp_path: Path) -> None:
    error = "**Encoding Error**\n\n/Users/attacker/.ssh/id_rsa could not be decoded"
    doc = _render(f"```\n{error}\n```", tmp_path)
    assert "<a " not in doc.html
    assert "file://" not in doc.html
    assert "/Users/attacker/.ssh/id_rsa" in doc.html


# --- D11: image path traversal rejected, no out-of-root file opens ------------------


@pytest.mark.parametrize(
    "path",
    ["../../../etc/passwd", "/etc/passwd", "../outside-asset-root/secret.png"],
)
def test_d11_image_path_traversal_rejected(tmp_path: Path, path: str, monkeypatch: pytest.MonkeyPatch) -> None:
    asset_root = tmp_path / "assets"
    asset_root.mkdir()
    opened: list[Path] = []
    original_open = Path.open

    def spy_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        opened.append(self)
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", spy_open)

    doc = _render(f"![x]({path})", asset_root)
    assert "src=" not in doc.html
    assert "image_path_escaped" in doc.warnings
    for opened_path in opened:
        try:
            opened_path.resolve().relative_to(asset_root.resolve())
        except ValueError:
            pytest.fail(f"renderer opened a file outside asset_root: {opened_path}")


# --- D12: symlink escape rejected ---------------------------------------------------


def test_d12_symlink_escape_rejected(tmp_path: Path) -> None:
    asset_root = tmp_path / "assets"
    asset_root.mkdir()
    secret_dir = tmp_path / "outside"
    secret_dir.mkdir()
    (secret_dir / "secret.png").write_bytes(b"secret")
    link = asset_root / "escape.png"
    link.symlink_to(secret_dir / "secret.png")

    doc = _render("![x](escape.png)", asset_root)
    assert "src=" not in doc.html
    assert "image_path_escaped" in doc.warnings


def test_d12_in_root_image_accepted(tmp_path: Path) -> None:
    asset_root = tmp_path / "assets"
    asset_root.mkdir()
    (asset_root / "diagram.png").write_bytes(b"png-bytes")

    doc = _render("![x](diagram.png)", asset_root)
    assert 'src="diagram.png"' in doc.html
    assert "image_path_escaped" not in doc.warnings


# --- D13: visual parity - tag/class vocabulary matches dashboard.css --------------


def test_d13_block_and_inline_vocabulary(tmp_path: Path) -> None:
    source = (
        "# Heading1\n\n"
        "## Heading2\n\n"
        "A paragraph with `code`, **bold**, and *em*.\n\n"
        "- item one\n"
        "- item two\n\n"
        "1. first\n"
        "2. second\n\n"
        "> a quote\n\n"
        "---\n\n"
        "```python\nprint('hi')\n```\n\n"
        "| a | b |\n"
        "| --- | --- |\n"
        "| 1 | 2 |\n"
    )
    doc = _render(source, tmp_path)
    for tag in (
        "<h1",
        "<h2",
        "<p",
        "<ul",
        "<ol",
        "<li",
        "<code",
        "<strong",
        "<em",
        "<blockquote",
        "<hr",
        "<pre",
        "<table",
        "<thead",
        "<tbody",
        "<tr",
        "<th",
        "<td",
    ):
        assert tag in doc.html, f"missing {tag} in {doc.html}"
    assert 'class="language-python"' in doc.html


# --- D14: GFM task-list checkbox ----------------------------------------------------


def test_d14_task_list_checkbox_checked(tmp_path: Path) -> None:
    doc = _render("- [x] done\n- [ ] todo\n", tmp_path)
    assert 'type="checkbox"' in doc.html
    assert "checked" in doc.html
    assert "done" in doc.html
    assert "todo" in doc.html


# --- D19: bounded time/memory on pathological input ----------------------------------


def test_d19_pathological_input_bounded_time(tmp_path: Path) -> None:
    pathological = "- item\n" * 200_000  # deeply repeated flat list, ~1.6MB
    start = time.monotonic()
    doc = _render(pathological, tmp_path)
    elapsed = time.monotonic() - start
    assert elapsed < 10.0, f"render took too long: {elapsed}s"
    assert "<li>" in doc.html


def test_d19_deeply_nested_blockquote_no_recursion_error(tmp_path: Path) -> None:
    nested = "> " * 5000 + "text"
    # Must not raise RecursionError regardless of how it is handled.
    doc = _render(nested, tmp_path)
    assert isinstance(doc.html, str)


# --- D20: fault tolerance - never raises for content, only for asset_root misuse ----


def test_d20_repaired_non_utf8_string_renders(tmp_path: Path) -> None:
    # Simulates scanner.py's read_file_resilient(auto_fix=True) output: an
    # already-repaired str containing the Unicode replacement character.
    repaired = "before � after"
    doc = _render(repaired, tmp_path)
    assert "before" in doc.html
    assert "after" in doc.html


def test_d20_asset_root_not_a_directory_raises_programmer_error(tmp_path: Path) -> None:
    not_a_dir = tmp_path / "not-a-dir.txt"
    not_a_dir.write_text("x")
    with pytest.raises(NarrowRenderError):
        render_markdown("hello", asset_root=not_a_dir)


def test_d20_content_never_raises(tmp_path: Path) -> None:
    weird_inputs = [
        "",
        "\x00\x01\x02",
        "*" * 10000,
        "[" * 500 + "]" * 500,
        "```\nunterminated fence",
    ]
    for weird in weird_inputs:
        doc = render_markdown(weird, asset_root=tmp_path)
        assert isinstance(doc.html, str)


# --- link_rewrite_map: relative internal links are rewritten ------------------------


def test_relative_link_rewrite_map_applied(tmp_path: Path) -> None:
    doc = _render(
        "[spec](spec.md)",
        tmp_path,
        link_rewrite_map={"spec.md": "/artifact/spec"},
    )
    assert 'href="/artifact/spec"' in doc.html


def test_relative_link_without_map_kept_as_is(tmp_path: Path) -> None:
    doc = _render("[spec](spec.md)", tmp_path)
    assert 'href="spec.md"' in doc.html
