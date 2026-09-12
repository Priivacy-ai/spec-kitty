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

Deliberate divergence from the upstream twin (#138): the ``ref`` bound here is
WIDER than zeitgeist/editor.py's. The relay's own schema —
``managed_live.schema.json`` ``EventSample.ref`` — declares only
``"maxLength": 240`` (no pattern, no segment rule), and this program's real
mission slugs ride that field: 48 of the 395 slugs in this repo's
``kitty-specs/`` are over editor.py's 64-char/6-segment bound, so a client
keeping the upstream bound replaced them with ``unknown-<digest>`` and the
watcher saw the moment but not which mission it belonged to. The character
class is unchanged; the length cap follows the schema, and
``MAX_SEGMENTS["ref"]`` is one more than the slug grammar's own measured
maximum (9): ``transport.py``'s ``focus_ref = f"{mission_slug}.{wp_id}"``
appends a tenth ``.``-delimited segment, so the bound this module must pass
is the composed ``focus_ref`` a real caller sends, not just the bare slug
(controller-qa, #138 fix round). The cost is recorded, not hidden: the
canonical prose fixture ("IGNORE-PRIOR-INSTRUCTIONS-…", 9 segments) fits
inside the real slug envelope, so no shape rule can both admit every real
slug and reject it — ref-kind fields enforce charset + length (+ a
≥11-segment prose floor) only, while every ident-kind field (actor
``user``, ``session_ref``) keeps the full shape defense below.

A second deliberate divergence from the upstream twin (#170): the ``ident``
quantifier here is TIGHTER than zeitgeist/editor.py:146's. Upstream still
declares ``{0,63}`` against its own 32-char hard max (enforced by a separate
length check) — the same pattern/maxLength self-contradiction zeitgeist#41
fixed in the relay's schemas, where a consumer deriving the bound from the
pattern alone read 64 and shipped a value the relay then rejected as
``bound``. The quantifier here declares the bound the module enforces
(``_MAX_LENGTH["ident"]``, 32); the character class is unchanged and
``ident()``'s accept set is exactly what it was — a 33..64-char ident failed
the length check before this change and fails the pattern after it.
"""

from __future__ import annotations

import hashlib
import re

# fullmatch, not match/search: "$" also matches before a trailing newline, so
# a caller who used match/search could accept a value with a trailing "\n".
# Callers of `ident()` below use `.fullmatch()`.
#
# {0,31}, not upstream editor.py:146's {0,63} (#170): the enforced ceiling is
# _MAX_LENGTH["ident"] below (editor.py:181's 32, checked separately), so the
# quantifier now declares the bound the module actually enforces instead of
# advertising 64. Deliberate divergence from the twin, mirroring zeitgeist#41's
# schema fix upstream — see the module docstring.
IDENT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._@+-]{0,31}")
# {0,239}, not the upstream twin's {0,119} (zeitgeist/editor.py:147):
# managed_live.schema.json EventSample.ref declares "maxLength": 240 and this
# program's own mission slugs ride that field — see the module docstring's
# divergence note (#138). Character class unchanged.
REF_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._@+/-]{0,239}")

# There is deliberately no scope pattern (see zeitgeist/editor.py:143-152):
# nothing in Z1's surface renders a scope value, so it is out of grammar's
# remit here too.

# "ident" is upstream parity (zeitgeist/editor.py:170 _MAX_SEGMENTS). "ref"
# is deliberately wider than upstream's 6: 9 is the measured maximum segment
# count across kitty-specs/' 395 mission slugs (#138) — a client keeping 6
# dropped 48 of them to unknown-<digest>. The bound below is 10, not 9:
# transport.py's `focus_ref = f"{mission_slug}.{wp_id}"` appends a tenth
# segment, and that composed value — not the bare slug — is what actually
# crosses this grammar at focus_ref positions (controller-qa, #138 fix
# round; the one 9-segment slug plus a wp_id was the sole miss at 9).
MAX_SEGMENTS = {"ident": 4, "ref": 10}

# Per-kind total-length caps — each is the ceiling its pattern's quantifier
# encodes above ("ref": managed_live.schema.json EventSample.ref maxLength
# 240; "ident": editor.py:181's 32, tightened onto IDENT_RE in #170).
_MAX_LENGTH = {"ident": 32, "ref": 240}

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
    if (
        pattern.fullmatch(value)
        and len(value) <= _MAX_LENGTH[kind]
        and not _too_many_segments(value, MAX_SEGMENTS[kind])
    ):
        return value
    # Non-cryptographic use: a short, stable, non-reversible correlation
    # label for a rejected identifier, not a security boundary — identical
    # to zeitgeist/editor.py:192's own choice, ported unchanged (N19 parity).
    return "unknown-" + hashlib.sha1(value.encode()).hexdigest()[:8]  # noqa: S324
