"""Normalize directive IDs between slug and DIRECTIVE_NNN formats.

Reuses the same algorithm as ``src/charter/context.py:_normalize_directive_id``
but exposed as a standalone, importable module for the DRG migration pipeline.
"""

from __future__ import annotations

import re


def normalize_directive_id(raw: str) -> str:
    """Normalise a directive identifier to the canonical ``DIRECTIVE_NNN`` form.

    Accepted inputs:
    - ``"DIRECTIVE_024"`` -- returned as-is.
    - ``"024-locality-of-change"`` -- leading digits extracted, zero-padded to 3.
    - ``"3-short"`` -- single digit padded to ``DIRECTIVE_003``.
    - Anything else -- uppercased as a best-effort fallback.
    """
    if re.match(r"^DIRECTIVE_\d+$", raw):
        return raw
    match = re.match(r"^(\d+)", raw)
    if match:
        number = match.group(1).zfill(3)
        return f"DIRECTIVE_{number}"
    return raw.upper()


def directive_to_urn(raw: str) -> str:
    """Return a fully-qualified directive URN: ``directive:DIRECTIVE_NNN``."""
    return f"directive:{normalize_directive_id(raw)}"


def artifact_to_urn(kind: str, raw_id: str) -> str:
    """Build a URN for any artifact kind.

    For directives the ID is normalised; all other kinds pass through as-is.
    """
    if kind == "directive":
        return directive_to_urn(raw_id)
    return f"{kind}:{raw_id}"
