"""The single identity/ref grammar, re-homed from zeitgeist.

Literal transcription of ``zeitgeist/editor.py:146-192`` (Z1.md §3.2 item 2).
Z1 cannot import the ``zeitgeist`` distribution — ``integrations/`` (where
this grammar lives upstream) ships to no package index (Z1.md §2.5) — so
parity is a committed-string / ported-logic copy, asserted by
``tests/zeitgeist_client/test_grammar.py`` (Z1.md §4 row N19) rather than by
import. Do not "improve" this file independently of its upstream twin: a
divergence here is exactly the failure mode Z1.md §4 N19 exists to catch.

Identity fields are VALIDATED, never repaired. A value that is not already a
well-formed, non-prose-shaped identifier is replaced with an opaque,
per-input-stable label — never coerced into a conforming shape (coercion can
manufacture something just as legible as the hostile input it started from).
"""

from __future__ import annotations

import hashlib
import re

# fullmatch, not match/search: "$" also matches before a trailing newline, so
# a caller who used match/search could accept a value with a trailing "\n".
# Callers of `ident()` below use `.fullmatch()`.
IDENT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._@+-]{0,63}")
REF_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._@+/-]{0,119}")

# There is deliberately no scope pattern (see zeitgeist/editor.py:143-152):
# nothing in Z1's surface renders a scope value, so it is out of grammar's
# remit here too.

MAX_SEGMENTS = {"ident": 4, "ref": 6}

_SEGMENT_SPLIT_RE = re.compile(r"[-._@+/]")


def _too_many_segments(value: str, limit: int) -> bool:
    return len([s for s in _SEGMENT_SPLIT_RE.split(value) if s]) > limit


def ident(value: str, pattern: re.Pattern[str] = IDENT_RE) -> str:
    """Return ``value`` if it is a well-formed identifier, else an opaque label.

    The label is ``unknown-<digest>``: stable per distinct input, so a caller
    can still correlate "the same malformed identity" across calls, while no
    part of the original text is reachable.
    """
    if not value:
        return ""
    kind = "ref" if pattern is REF_RE else "ident"
    hard_max = 64 if kind == "ref" else 32
    if (
        pattern.fullmatch(value)
        and len(value) <= hard_max
        and not _too_many_segments(value, MAX_SEGMENTS[kind])
    ):
        return value
    # Non-cryptographic use: a short, stable, non-reversible correlation
    # label for a rejected identifier, not a security boundary — identical
    # to zeitgeist/editor.py:192's own choice, ported unchanged (N19 parity).
    return "unknown-" + hashlib.sha1(value.encode()).hexdigest()[:8]  # noqa: S324
