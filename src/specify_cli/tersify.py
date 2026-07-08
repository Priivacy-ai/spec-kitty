"""Tersifier: serve LLMs a compressed rendering of prose-heavy markdown.

RESEARCH PROTOTYPE (not wired into any default behavior). Sources — command
templates, skills, prompts — stay authored in full prose; when the
``SPEC_KITTY_TERSIFY`` environment variable is truthy, the three LLM-delivery
choke points (slash-command rendering, Agent-Skills rendering, ``spec-kitty
next`` prompt assembly) pass template text through :func:`tersify_for_llm`
before it reaches an agent.

Two layers:

1. **Hand-tersified cache** (preferred): a human- or LLM-authored terse
   rewrite of an entire source file, stored at
   ``<source dir>/terse/<name>.terse.md`` and keyed by the SHA-256 of the
   prose original. Deterministic at runtime like a dictionary, with
   hand-abbreviation quality (~40-50% token savings on prose, measured with
   o200k_base). A stale hash (prose edited, terse copy not regenerated) falls
   through to layer 2, so a forgotten regeneration can never serve outdated
   instructions.

2. **Deterministic dictionary pass** (fallback): multi-word phrase collapses
   and filler deletions. Every entry was vetted with a real tokenizer and
   kept only if it saves >= 1 token per application; character-level
   shorthand ("meeting" -> "mtg") is deliberately absent because it measured
   at zero or *negative* token savings. Expect roughly 5-15% on prose.

Safety model — nothing spec-kitty's machinery depends on is ever rewritten.
Both layers protect byte-for-byte (mechanically here; by authoring convention
plus the same verifier in the hand layer):

- fenced code blocks and inline code
- markdown tables
- YAML frontmatter
- ``{SCRIPT}`` / ``{{jinja}}`` placeholders, ``$ARGUMENTS``-style variables,
  ``__AGENT__`` markers, ``<angle-bracket>`` markers
- HTML comments (SPDD block markers, version markers)
- headings (section anchors like ``## User Input`` that downstream code
  locates by exact text)
- lines invoking ``spec-kitty`` / ``uv run`` / ``python``

The invariant test suite (``tests/specify_cli/test_tersify.py``) enforces all
of the above over every bundled mission-step prompt and doctrine skill.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

ENV_FLAG = "SPEC_KITTY_TERSIFY"

# Unicode private-use sentinels cannot collide with sanitized input, and
# single-pass restoration over them is provably terminating.
_S0 = ""
_S1 = ""

_CODE_RE = re.compile(r"(```[\s\S]*?```|`[^`\n]+`)")
_TABLE_RE = re.compile(r"((?:^[ \t]*\|.*(?:\r?\n|$))+)", re.MULTILINE)
_WORD_RE = re.compile(r"\b[a-zA-Z0-9_'-]+\b")
_FRONTMATTER_RE = re.compile(r"\A---\r?\n[\s\S]*?\r?\n---\r?\n")

# Structural elements spec-kitty's machinery (or the agent harness) depends
# on: never rewritten, protected byte-for-byte before any prose pass.
_STRUCTURAL_RES = [
    _FRONTMATTER_RE,  # YAML frontmatter
    re.compile(r"<!--[\s\S]*?-->"),  # HTML comments (SPDD/version markers)
    re.compile(r"\{\{[^{}\n]*\}\}|\{[A-Z_]+\}"),  # {{jinja}} / {PLACEHOLDER}
    re.compile(r"\$[A-Z_][A-Z0-9_]*"),  # $ARGUMENTS-style variables
    re.compile(r"<[a-zA-Z][^<>\n]*>"),  # <angle-bracket markers>
    re.compile(r"__[A-Z_]+__"),  # __AGENT__-style markers
    re.compile(r"^#{1,6} .*$", re.MULTILINE),  # headings (section anchors)
    re.compile(r"^ {0,3}(?:spec-kitty|uv run|python3?)\b.*$", re.MULTILINE),
    # Indented code blocks (4-space/tab). Deliberately overprotective: nested
    # list continuations match too, trading compression for safety.
    re.compile(r"(?:^(?: {4}|\t).*(?:\r?\n|$))+", re.MULTILINE),
]

# Token-audited dictionary (o200k_base deltas measured per application; see
# the research PR). Only entries with a strictly positive delta are kept.
# Legend text is attached where the replacement is not self-explanatory.
PHRASES: dict[str, tuple[str, str | None]] = {
    "due to the fact that": ("because", None),
    "in order to": ("to", None),
    "pay particular attention to": ("focus on", None),
    "it is important to": ("", None),
    "please note that": ("note:", None),
    "make sure that you": ("", None),
    "make sure to": ("", None),
    "you will need to": ("", None),
    "if and only if": ("iff", "iff = if and only if"),
    # NOTE: "for example" -> "e.g." was audited at -1 token and rejected.
    "that is to say": ("i.e.", None),
    "as well as": ("and", None),
    "in addition to": ("plus", None),
    "with respect to": ("re:", "re: = regarding"),
    "prior to": ("before", None),
    "subsequent to": ("after", None),
    "in the event that": ("if", None),
    "at this point in time": ("now", None),
    "on a regular basis": ("regularly", None),
}

FILLER_BLACKLIST: list[str] = [
    "please",
    "kindly",
    "very",
    "really",
    "merely",
    "simply",
    "basically",
    "essentially",
    "it is worth noting that",
    "as you can see",
]

_HAND_CACHE_HEADER_RE = re.compile(r"<!-- tersifier:source-sha256=([0-9a-f]{64}) -->\r?\n")


@dataclass
class TersifyResult:
    text: str
    source: str  # "hand" | "dictionary" | "passthrough"
    legend: list[str] = field(default_factory=list)


def tersify_enabled() -> bool:
    """Whether the research flag is on. Defaults to off: zero behavior change."""
    return os.environ.get(ENV_FLAG, "").strip().lower() in {"1", "true", "yes", "on"}


def _sha256(text: str) -> str:
    # noqa justification: file-integrity check (hand-cache staleness), not charter hashing.
    return hashlib.sha256(text.encode("utf-8")).hexdigest()  # noqa: TID251


def hand_cache_path(source_path: Path) -> Path:
    """Cache location: a ``terse/`` sibling directory, deliberately OUTSIDE
    the ``*.md`` globs used by template discovery so a cache file can never be
    picked up as a command template of its own."""
    return source_path.parent / "terse" / f"{source_path.name}.terse.md"


class Tersifier:
    """Compress prose-heavy LLM-facing markdown, protecting structure."""

    def __init__(self) -> None:
        self._phrases = sorted(PHRASES.items(), key=lambda kv: -len(kv[0]))
        self._blacklist_multi = [e for e in FILLER_BLACKLIST if " " in e]
        self._blacklist_single = {e for e in FILLER_BLACKLIST if " " not in e}

    # -- layer 1: hand-tersified cache ------------------------------------

    def _hand_lookup(self, text: str, source_path: Path | None) -> str | None:
        """Return the hand-tersified body iff its recorded hash matches the
        current source text; anything stale or malformed is ignored."""
        if source_path is None:
            return None
        cache_file = hand_cache_path(source_path)
        try:
            raw = cache_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
        match = _HAND_CACHE_HEADER_RE.match(raw)
        if not match or match.group(1) != _sha256(text):
            return None
        return raw[match.end() :]

    # -- layer 2: deterministic dictionary pass ---------------------------

    def _dictionary_pass(self, text: str) -> tuple[str, list[str]]:
        text = text.replace(_S0, "").replace(_S1, "")
        protected: list[str] = []
        legend: list[str] = []

        def protect(content: str) -> str:
            protected.append(content)
            return f"{_S0}{len(protected) - 1}{_S1}"

        text = _CODE_RE.sub(lambda m: protect(m.group(0)), text)
        text = _TABLE_RE.sub(lambda m: protect(m.group(0)), text)
        for structural in _STRUCTURAL_RES:
            text = structural.sub(lambda m: protect(m.group(0)), text)

        for entry in self._blacklist_multi:
            text = re.sub(rf"\b{re.escape(entry)}\b", " ", text, flags=re.IGNORECASE)

        for phrase, (replacement, note) in self._phrases:
            pattern = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)

            def _sub(_m: re.Match, replacement: str = replacement, note: str | None = note) -> str:
                if note and note not in legend:
                    legend.append(note)
                if not replacement.strip():
                    return " "
                return protect(replacement)

            text = pattern.sub(_sub, text)

        parts = re.split(r"(\b[a-zA-Z0-9_'-]+\b)", text)
        for i, part in enumerate(parts):
            if not _WORD_RE.fullmatch(part):
                continue
            if i > 0 and parts[i - 1].endswith(_S0):
                continue  # placeholder index, not prose
            if part.lower() in self._blacklist_single:
                parts[i] = ""
        text = "".join(parts)

        # Last whitespace pass runs while placeholders still hide protected
        # content; nothing is normalized after restoration. Line-leading
        # indentation is never touched (markdown nesting is significant);
        # only intra-line runs collapse and trailing spaces are trimmed.
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"(?<=\S)[^\S\n]+(?=\S)", " ", text)
        text = re.sub(r"(?<=\S) ([.,?!;:])", r"\1", text)
        text = re.sub(r"[^\S\n]+$", "", text, flags=re.MULTILINE).strip()

        for i in range(len(protected) - 1, -1, -1):
            text = protected[i].join(text.split(f"{_S0}{i}{_S1}"))
        return text.strip() + "\n", legend

    # -- public API --------------------------------------------------------

    def tersify(self, text: str, source_path: Path | None = None) -> TersifyResult:
        hand = self._hand_lookup(text, source_path)
        if hand is not None:
            return TersifyResult(text=hand, source="hand")
        compressed, legend = self._dictionary_pass(text)
        return TersifyResult(text=compressed, source="dictionary", legend=legend)


_DEFAULT = Tersifier()


def tersify_for_llm(text: str, *, source_path: Path | None = None) -> str:
    """Entry point for the delivery pipelines. No-op unless ``SPEC_KITTY_TERSIFY``
    is set, so default behavior is byte-for-byte unchanged."""
    if not tersify_enabled():
        return text
    result = _DEFAULT.tersify(text, source_path=source_path)
    out = result.text
    if result.legend:
        legend_line = f"Legend: {'; '.join(result.legend)}\n\n"
        fm = _FRONTMATTER_RE.match(out)
        # Never push frontmatter off line 1 — legend goes after it.
        out = out[: fm.end()] + legend_line + out[fm.end() :] if fm else legend_line + out
    return out


__all__ = [
    "ENV_FLAG",
    "Tersifier",
    "TersifyResult",
    "hand_cache_path",
    "tersify_enabled",
    "tersify_for_llm",
]
