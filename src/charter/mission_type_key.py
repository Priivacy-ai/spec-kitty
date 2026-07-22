"""Single boundary-safe mission-type key canonicalizer (WP-CANON, FR-012).

This module is the *one* canonicalizer for the mission-type key that both the
``charter`` and ``specify_cli`` layers consume. It lives in ``charter/`` because
the layer rule permits ``specify_cli -> charter`` but forbids the reverse
(C-001, ``tests/architectural/test_layer_rules.py``): placing it here lets both
layers import it without either crossing the boundary the wrong way.

The canonicalizer is deliberately **pure and minimal**:

* no I/O — it operates on an already-read raw string, never a path or file;
* **no baked-in default** — a typeless / absent value maps to ``None`` so that
  callers can degrade neutrally (FR-003a) instead of silently loading the
  ``software-dev`` governance profile (FR-001, FR-012);
* strip-only normalization — it does not lowercase or otherwise rewrite the
  identifier, preserving existing exact-match semantics (NFR-001).
"""

from __future__ import annotations

__all__ = ["canonical_mission_type_key"]


def canonical_mission_type_key(raw: str | None) -> str | None:
    """Return the canonical mission-type key for a raw metadata value.

    Args:
        raw: The raw mission-type string as read from mission metadata (e.g. the
            ``mission_type`` or legacy ``mission`` field of ``meta.json``), or
            ``None`` when the field is absent.

    Returns:
        The whitespace-stripped canonical key, or ``None`` when the input is
        absent or blank. ``None`` is the *neutral / typeless* result — callers
        MUST treat it as "no mission type" and degrade accordingly (FR-003a);
        this function never substitutes a ``software-dev`` (or any) default.

    Examples:
        >>> canonical_mission_type_key("  research  ")
        'research'
        >>> canonical_mission_type_key("") is None
        True
        >>> canonical_mission_type_key(None) is None
        True
    """
    if raw is None:
        return None
    key = raw.strip()
    return key or None
