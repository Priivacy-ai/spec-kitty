"""D2 narrow markdown renderer engine.

Converts markdown text into a deliberately narrow, self-contained HTML
subset. Pure-Python, stdlib-only, extending the escaping discipline already
proven in ``scripts/docs/generate_kitty_specs_docs.py``'s ``esc()``/
``markdown_to_html()`` (m1-contract-drafts/D2.md §2.2, §6.1) rather than
adopting a third-party CommonMark library.

Fail-open-to-text, fail-closed-to-HTML: any markdown *content* the parser
cannot make safe sense of is rendered as escaped, inert text (never raises).
``NarrowRenderError`` is reserved for programmer error only (a malformed
``asset_root``), never for attacker-controlled markdown (see D2.md §3.3,
§4 row D20).
"""

from __future__ import annotations

import html
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "RENDERER_CONTRACT_VERSION",
    "NarrowRenderError",
    "RenderedDocument",
    "render_markdown",
]

# Bumped only with a deliberate contract-change commit (D2.md §4 row D17):
# this is the literal string D5's cache key names for its `renderer`
# dimension and D1's provenance records.
RENDERER_CONTRACT_VERSION: str = "1.0.0"

# --- URL scheme allow-list (D2.md §3.2, §4 rows D7-D8) ---------------------

_ALLOWED_LINK_SCHEMES = frozenset({"https", "mailto"})

_SCHEME_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")

# --- block-level grammar -----------------------------------------------------

_FENCE_RE = re.compile(r"^```([a-zA-Z0-9_+\-]*)\s*$")
_ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_HR_RE = re.compile(r"^(?:-{3,}|\*{3,}|_{3,})\s*$")
_UL_ITEM_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
_OL_ITEM_RE = re.compile(r"^\s*\d+\.\s+(.*)$")
_TASK_RE = re.compile(r"^\[([ xX])\]\s+(.*)$")
_BLOCKQUOTE_LINE_RE = re.compile(r"^>\s?(.*)$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?\s*$")

# --- inline grammar -----------------------------------------------------------

_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_STRONG_RE = re.compile(r"\*\*([^*]+)\*\*")
_EM_STAR_RE = re.compile(r"\*([^*]+)\*")
_EM_UNDER_RE = re.compile(r"(?<![A-Za-z0-9_])_([^_]+)_(?![A-Za-z0-9_])")
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]*)\)")
_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")

_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


class NarrowRenderError(Exception):
    """Raised only for programmer error (e.g. ``asset_root`` not a directory).

    Never raised for attacker-controlled markdown content, which is always
    degraded to escaped text instead (fail-open-to-text, fail-closed-to-HTML).
    """


@dataclass(frozen=True)
class RenderedDocument:
    """The narrow HTML fragment produced by :func:`render_markdown`."""

    html: str
    warnings: tuple[str, ...]
    renderer_contract_version: str = RENDERER_CONTRACT_VERSION


def render_markdown(
    source: str,
    *,
    asset_root: Path,
    link_rewrite_map: Mapping[str, str] | None = None,
) -> RenderedDocument:
    """Render ``source`` into the narrow, self-contained HTML grammar.

    ``asset_root`` confines relative image resolution (D2.md §4 rows
    D11-D12): only image paths that resolve *under* ``asset_root`` after
    normalization are ever accepted; everything else is dropped with a
    ``image_path_escaped``/``image_scheme_rejected:*`` warning. No file is
    ever opened by this function — the confinement check is a pure path
    computation, so it structurally cannot read outside ``asset_root``.
    """
    if not isinstance(asset_root, Path):
        raise NarrowRenderError(f"asset_root must be a pathlib.Path, got {type(asset_root)!r}")
    if not asset_root.is_dir():
        raise NarrowRenderError(f"asset_root does not exist or is not a directory: {asset_root}")

    warnings: list[str] = []
    stripped_source = _strip_html_comments(source)
    body = _render_blocks(stripped_source, asset_root=asset_root, link_rewrite_map=link_rewrite_map, warnings=warnings)
    return RenderedDocument(html=body, warnings=tuple(warnings))


def _strip_html_comments(source: str) -> str:
    """Drop HTML comments entirely (D2.md §4 row D9) — never shown, never a DOM comment node."""
    return _COMMENT_RE.sub("", source)


def _is_block_start(line: str) -> bool:
    """True when ``line`` begins a new non-paragraph block (used to end paragraph accumulation)."""
    stripped = line.strip()
    if stripped == "":
        return True
    if _FENCE_RE.match(stripped):
        return True
    if _ATX_HEADING_RE.match(stripped):
        return True
    if _HR_RE.match(stripped):
        return True
    if stripped.startswith(">"):
        return True
    if _UL_ITEM_RE.match(line) or _OL_ITEM_RE.match(line):
        return True
    return "|" in stripped


def _split_table_row(line: str) -> list[str]:
    trimmed = line.strip()
    if trimmed.startswith("|"):
        trimmed = trimmed[1:]
    if trimmed.endswith("|"):
        trimmed = trimmed[:-1]
    return [cell.strip() for cell in trimmed.split("|")]


def _consume_fence(lines: list[str], i: int, n: int, lang: str) -> tuple[int, str]:
    i += 1
    code_lines: list[str] = []
    while i < n and lines[i].strip() != "```":
        code_lines.append(lines[i])
        i += 1
    if i < n:
        i += 1  # consume the closing fence; unterminated fences just hit EOF
    code_text = html.escape("\n".join(code_lines), quote=True)
    cls = f' class="language-{lang}"' if lang else ""
    return i, f"<pre><code{cls}>{code_text}</code></pre>"


def _consume_blockquote(
    lines: list[str],
    i: int,
    n: int,
    asset_root: Path,
    link_rewrite_map: Mapping[str, str] | None,
    warnings: list[str],
) -> tuple[int, str]:
    quote_texts: list[str] = []
    while i < n and lines[i].strip().startswith(">"):
        match = _BLOCKQUOTE_LINE_RE.match(lines[i].strip())
        quote_texts.append(match.group(1) if match else "")
        i += 1
    inner = " ".join(text for text in quote_texts if text.strip())
    rendered = _render_inline(inner, asset_root, link_rewrite_map, warnings)
    return i, f"<blockquote><p>{rendered}</p></blockquote>"


def _consume_list(
    lines: list[str],
    i: int,
    n: int,
    ordered: bool,
    asset_root: Path,
    link_rewrite_map: Mapping[str, str] | None,
    warnings: list[str],
) -> tuple[int, str]:
    item_re = _OL_ITEM_RE if ordered else _UL_ITEM_RE
    items: list[str] = []
    while i < n:
        match = item_re.match(lines[i])
        if not match:
            break
        item_text = match.group(1)
        task_match = _TASK_RE.match(item_text)
        if task_match:
            checked = task_match.group(1).lower() == "x"
            label = task_match.group(2)
            checked_attr = " checked" if checked else ""
            checkbox = f'<input type="checkbox" disabled{checked_attr} /> '
            rendered_label = _render_inline(label, asset_root, link_rewrite_map, warnings)
            items.append(f"<li>{checkbox}{rendered_label}</li>")
        else:
            rendered_item = _render_inline(item_text, asset_root, link_rewrite_map, warnings)
            items.append(f"<li>{rendered_item}</li>")
        i += 1
    tag = "ol" if ordered else "ul"
    return i, f"<{tag}>" + "".join(items) + f"</{tag}>"


def _consume_table(
    lines: list[str],
    i: int,
    n: int,
    asset_root: Path,
    link_rewrite_map: Mapping[str, str] | None,
    warnings: list[str],
) -> tuple[int, str]:
    header_cells = _split_table_row(lines[i])
    i += 2  # header + separator row
    body_rows: list[list[str]] = []
    while i < n and "|" in lines[i] and lines[i].strip() != "":
        body_rows.append(_split_table_row(lines[i]))
        i += 1
    thead_cells = "".join(f"<th>{_render_inline(cell, asset_root, link_rewrite_map, warnings)}</th>" for cell in header_cells)
    body_html = "".join("<tr>" + "".join(f"<td>{_render_inline(cell, asset_root, link_rewrite_map, warnings)}</td>" for cell in row) + "</tr>" for row in body_rows)
    return i, f"<table><thead><tr>{thead_cells}</tr></thead><tbody>{body_html}</tbody></table>"


def _consume_paragraph(
    lines: list[str],
    i: int,
    n: int,
    asset_root: Path,
    link_rewrite_map: Mapping[str, str] | None,
    warnings: list[str],
) -> tuple[int, str]:
    para_lines = [lines[i].strip()]
    i += 1
    while i < n and not _is_block_start(lines[i]):
        para_lines.append(lines[i].strip())
        i += 1
    text = " ".join(para_lines)
    rendered = _render_inline(text, asset_root, link_rewrite_map, warnings)
    return i, f"<p>{rendered}</p>"


def _render_blocks(
    source: str,
    *,
    asset_root: Path,
    link_rewrite_map: Mapping[str, str] | None,
    warnings: list[str],
) -> str:
    # Line-driven, single flat loop delegating to one helper per block type
    # — no recursion over nesting depth, so pathological input (deep
    # blockquote-prefix repetition, huge flat lists) is bounded by input
    # length, not stack depth (D2.md §4 row D19).
    lines = source.split("\n")
    n = len(lines)
    i = 0
    out: list[str] = []

    while i < n:
        line = lines[i]
        stripped = line.strip()
        fragment: str

        if stripped == "":
            i += 1
            continue
        elif (fence_match := _FENCE_RE.match(stripped)) is not None:
            i, fragment = _consume_fence(lines, i, n, fence_match.group(1))
        elif (heading_match := _ATX_HEADING_RE.match(stripped)) is not None:
            level = len(heading_match.group(1))
            rendered = _render_inline(heading_match.group(2), asset_root, link_rewrite_map, warnings)
            fragment = f"<h{level}>{rendered}</h{level}>"
            i += 1
        elif _HR_RE.match(stripped):
            fragment = "<hr />"
            i += 1
        elif stripped.startswith(">"):
            i, fragment = _consume_blockquote(lines, i, n, asset_root, link_rewrite_map, warnings)
        elif _UL_ITEM_RE.match(line) or _OL_ITEM_RE.match(line):
            ordered = _OL_ITEM_RE.match(line) is not None
            i, fragment = _consume_list(lines, i, n, ordered, asset_root, link_rewrite_map, warnings)
        elif "|" in line and i + 1 < n and _TABLE_SEP_RE.match(lines[i + 1].strip()):
            i, fragment = _consume_table(lines, i, n, asset_root, link_rewrite_map, warnings)
        else:
            i, fragment = _consume_paragraph(lines, i, n, asset_root, link_rewrite_map, warnings)

        out.append(fragment)

    return "".join(out)


def _resolve_href(
    url: str,
    link_rewrite_map: Mapping[str, str] | None,
    warnings: list[str],
) -> tuple[str | None, bool]:
    """Return ``(href, is_external)`` or ``(None, False)`` if the scheme is rejected."""
    stripped = url.strip()
    if not stripped:
        return None, False
    if stripped.startswith("//"):
        warnings.append("link_scheme_rejected:protocol-relative")
        return None, False
    scheme_match = _SCHEME_RE.match(stripped)
    if scheme_match:
        scheme = scheme_match.group(1).lower()
        if scheme not in _ALLOWED_LINK_SCHEMES:
            warnings.append(f"link_scheme_rejected:{scheme}")
            return None, False
        if scheme == "mailto":
            return stripped, False
        return stripped, True  # https:// -> external, rel="noopener noreferrer nofollow" target="_blank"
    rewritten = (link_rewrite_map or {}).get(stripped, stripped)
    return rewritten, False


def _resolve_image_src(src: str, asset_root: Path, warnings: list[str]) -> str | None:
    """Return the confined relative ``src`` or ``None`` if rejected.

    Never opens a file handle: confinement is a pure ``Path.resolve()`` +
    ``relative_to()`` check, matching ``handlers/static.py``'s existing
    ``StaticHandler`` confinement pattern (D2.md §4 rows D11-D12).
    """
    stripped = src.strip()
    if not stripped:
        return None
    if stripped.startswith("//"):
        warnings.append("image_scheme_rejected:protocol-relative")
        return None
    scheme_match = _SCHEME_RE.match(stripped)
    if scheme_match:
        warnings.append(f"image_scheme_rejected:{scheme_match.group(1).lower()}")
        return None
    try:
        root_resolved = asset_root.resolve()
        candidate = (asset_root / stripped).resolve()
    except OSError:
        warnings.append("image_path_escaped")
        return None
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        warnings.append("image_path_escaped")
        return None
    return stripped


def _render_inline(
    text: str,
    asset_root: Path,
    link_rewrite_map: Mapping[str, str] | None,
    warnings: list[str],
) -> str:
    """Render one line/paragraph of inline markdown.

    Escapes the *entire* input first (matching renderer #2's ``esc()``-first
    discipline, D2.md §2.2/§3.2) so raw HTML in the source is never passed
    through — it can only ever appear as inert, escaped text. Markdown
    syntax characters (``` ` ```, ``*``, ``_``, ``[``, ``]``, ``(``, ``)``)
    are untouched by ``html.escape`` so the subsequent substitutions are
    still able to find them.
    """
    escaped = html.escape(text, quote=True)
    protected: dict[str, str] = {}
    counter = 0

    def protect(fragment: str) -> str:
        nonlocal counter
        counter += 1
        token = f"\x00PROT{counter}\x00"
        protected[token] = fragment
        return token

    # Inline code spans first: their content must never be re-parsed as
    # further markdown (bold/italic/links inside `code` stay literal).
    escaped = _INLINE_CODE_RE.sub(lambda m: protect(f"<code>{m.group(1)}</code>"), escaped)

    def image_sub(match: re.Match[str]) -> str:
        alt, raw_src = match.group(1), match.group(2)
        resolved = _resolve_image_src(html.unescape(raw_src), asset_root, warnings)
        if resolved is None:
            return alt
        return protect(f'<img src="{html.escape(resolved, quote=True)}" alt="{alt}" />')

    escaped = _IMAGE_RE.sub(image_sub, escaped)

    def link_sub(match: re.Match[str]) -> str:
        label, raw_href = match.group(1), match.group(2)
        resolved, external = _resolve_href(html.unescape(raw_href), link_rewrite_map, warnings)
        if resolved is None:
            return label
        rel_attr = ' rel="noopener noreferrer nofollow" target="_blank"' if external else ""
        return protect(f'<a href="{html.escape(resolved, quote=True)}"{rel_attr}>{label}</a>')

    escaped = _LINK_RE.sub(link_sub, escaped)

    escaped = _STRONG_RE.sub(lambda m: protect(f"<strong>{m.group(1)}</strong>"), escaped)
    escaped = _EM_STAR_RE.sub(lambda m: protect(f"<em>{m.group(1)}</em>"), escaped)
    escaped = _EM_UNDER_RE.sub(lambda m: protect(f"<em>{m.group(1)}</em>"), escaped)

    for token, fragment in protected.items():
        escaped = escaped.replace(token, fragment)

    return escaped
