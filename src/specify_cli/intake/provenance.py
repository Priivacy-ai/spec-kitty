"""Provenance escape helpers (FR-007 / WP02 T007).

Provenance lines (``source_file: ...``) are written into HTML / Markdown
comments and into a YAML sidecar.  The raw input is operator-controlled
file-system data, but we treat it as untrusted: anything that lets the
input break out of a comment context (``-->``), simulate a C-style
comment terminator (``*/``), inject markdown headings (leading ``#``),
or smuggle ASCII control characters into downstream prompts is
forbidden.

The contract for :func:`escape_for_comment` lives in
``kitty-specs/<mission>/contracts/intake-source-provenance.md`` and the
behaviour is pinned by ``tests/unit/intake/test_provenance_escape.py``.
"""

from __future__ import annotations

# Hard cap on the cleaned string size (UTF-8 bytes).  Keeping provenance
# lines short prevents adversarial inputs from bloating the brief header
# and lets us print the source file in a single terminal line.
MAX_PROVENANCE_BYTES: int = 256


def _strip_control_chars(s: str) -> str:
    """Remove ASCII control characters (0x00–0x1F, 0x7F) except ``\\t``."""
    return "".join(
        ch for ch in s if ch == "\t" or (ord(ch) >= 0x20 and ord(ch) != 0x7F)
    )


def _truncate_utf8_safe(s: str, max_bytes: int) -> str:
    """Clip ``s`` so its UTF-8 encoding does not exceed ``max_bytes``.

    Splits on a code-point boundary so the output is always valid UTF-8.
    """
    encoded = s.encode("utf-8")
    if len(encoded) <= max_bytes:
        return s
    # Walk back from max_bytes until we land on a UTF-8 leading byte.
    cut = max_bytes
    while cut > 0 and (encoded[cut] & 0xC0) == 0x80:
        cut -= 1
    return encoded[:cut].decode("utf-8", errors="ignore")


def escape_for_comment(s: str) -> str:
    """Escape a provenance string for safe embedding in markdown / comments.

    Rules (in order):

    1. Strip ASCII control characters (0x00–0x1F, 0x7F) except ``\\t``.
    2. Replace comment-terminator-like sequences:
       - ``-->`` → ``--&gt;``
       - ``*/``  → ``*&#47;``
       - Leading ``#`` (line start, after newline collapsing) → ``\\#``.
    3. Clip to :data:`MAX_PROVENANCE_BYTES` bytes (UTF-8 safe truncation).

    The function is total: it never raises and always returns a string
    that is safe to drop into ``<!-- ... -->`` or a single-line YAML
    value.
    """
    if not isinstance(s, str):  # defensive: reject non-strings loudly
        raise TypeError(
            f"escape_for_comment requires str, got {type(s).__name__}"
        )

    # Step 1: strip control chars (newlines included → provenance lines
    # are single-line by construction; any embedded newline is dropped).
    cleaned = _strip_control_chars(s)

    # Step 2a: comment-terminator escapes.
    cleaned = cleaned.replace("-->", "--&gt;")
    cleaned = cleaned.replace("*/", "*&#47;")

    # Step 2b: leading-# escape.  After step 1 there are no embedded
    # newlines, so "leading" simply means index 0.
    if cleaned.startswith("#"):
        cleaned = "\\" + cleaned

    # Step 3: clip to the byte cap.
    return _truncate_utf8_safe(cleaned, MAX_PROVENANCE_BYTES)


__all__ = ["MAX_PROVENANCE_BYTES", "escape_for_comment"]
