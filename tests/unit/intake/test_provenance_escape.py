"""Unit tests for ``specify_cli.intake.provenance.escape_for_comment`` (WP02 T007)."""

from __future__ import annotations

import secrets

import pytest

from specify_cli.intake.provenance import MAX_PROVENANCE_BYTES, escape_for_comment


pytestmark = [pytest.mark.fast]


# ---------------------------------------------------------------------------
# Rule 1 — control-character stripping
# ---------------------------------------------------------------------------


def test_strips_ascii_control_chars_except_tab():
    raw = "abc\x00\x01\x07\x1f\x7fdef"
    out = escape_for_comment(raw)
    assert out == "abcdef", f"expected control chars stripped, got {out!r}"


def test_preserves_tab_character():
    out = escape_for_comment("a\tb")
    assert out == "a\tb"


def test_strips_newline_and_carriage_return():
    # Newlines must not survive — they would let the input start a new
    # line in a markdown comment context.
    out = escape_for_comment("line1\nline2\r\nline3")
    assert "\n" not in out
    assert "\r" not in out
    assert out == "line1line2line3"


# ---------------------------------------------------------------------------
# Rule 2 — comment-terminator and markdown-injection escapes
# ---------------------------------------------------------------------------


def test_escapes_html_comment_close():
    raw = "before --> heading"
    out = escape_for_comment(raw)
    assert "-->" not in out
    assert "--&gt;" in out


def test_escapes_c_style_comment_close():
    raw = "value */ pwn"
    out = escape_for_comment(raw)
    assert "*/" not in out
    assert "*&#47;" in out


def test_escapes_leading_hash_for_markdown_heading():
    raw = "# Inject heading"
    out = escape_for_comment(raw)
    assert out.startswith("\\#"), f"expected leading \\#, got {out!r}"


def test_no_escape_when_hash_not_at_start():
    raw = "value with # mid-string"
    out = escape_for_comment(raw)
    # Mid-string ``#`` must remain unescaped — only line-starting ``#``
    # is dangerous in markdown.
    assert out == "value with # mid-string"


def test_combined_attack_payload_is_neutralised():
    """Adversarial input from the WP02 reviewer guidance must be safe."""
    raw = "\n# Inject heading\n--> visible\n*/ visible"
    out = escape_for_comment(raw)
    # Newlines stripped → mid-string content stays attached to the
    # original line; the heading marker is now mid-string, not line
    # start, so no leading ``\#`` escape.  But ``-->`` and ``*/`` must
    # both be neutralised regardless of position.
    assert "\n" not in out
    assert "-->" not in out
    assert "*/" not in out
    assert "--&gt;" in out
    assert "*&#47;" in out


# ---------------------------------------------------------------------------
# Rule 3 — UTF-8 safe truncation
# ---------------------------------------------------------------------------


def test_clips_to_max_bytes():
    raw = "x" * (MAX_PROVENANCE_BYTES + 100)
    out = escape_for_comment(raw)
    assert len(out.encode("utf-8")) <= MAX_PROVENANCE_BYTES


def test_truncation_does_not_split_multibyte_codepoints():
    # 4-byte emoji repeated: any naïve byte truncation would corrupt
    # UTF-8.  We require the helper produces a *valid* UTF-8 string.
    raw = "🐈" * 200  # 4 bytes per code point
    out = escape_for_comment(raw)
    assert len(out.encode("utf-8")) <= MAX_PROVENANCE_BYTES
    # The output must round-trip through UTF-8 cleanly.
    out.encode("utf-8").decode("utf-8")


# ---------------------------------------------------------------------------
# Property-style fuzz: random byte strings must always produce a safe string.
# ---------------------------------------------------------------------------


def test_fuzz_random_inputs_never_raise_and_always_safe():
    for _ in range(200):
        # Generate a random Latin-1 string of varying length.  Latin-1
        # decoding is total over arbitrary bytes so we cover the full
        # 0–255 range without UnicodeDecodeError noise.
        raw = secrets.token_bytes(secrets.choice([0, 1, 16, 64, 256, 1024])).decode("latin-1")
        out = escape_for_comment(raw)
        # Invariants: bounded size, no comment terminators, no leading
        # ``#``, no ASCII control chars (except tab).
        assert len(out.encode("utf-8")) <= MAX_PROVENANCE_BYTES
        assert "-->" not in out
        assert "*/" not in out
        if out:
            assert out[0] != "#"
        for ch in out:
            assert ch == "\t" or (ord(ch) >= 0x20 and ord(ch) != 0x7F)


def test_non_string_input_raises_typeerror():
    with pytest.raises(TypeError):
        escape_for_comment(123)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Empty / boundary conditions
# ---------------------------------------------------------------------------


def test_empty_string_passthrough():
    assert escape_for_comment("") == ""


def test_only_control_chars_collapses_to_empty():
    assert escape_for_comment("\x00\x01\x02\x03") == ""
