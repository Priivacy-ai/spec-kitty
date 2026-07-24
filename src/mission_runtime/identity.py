"""Mid8 identity resolution (canonical surface, internal module).

This is an **internal** submodule of the :mod:`mission_runtime` umbrella. It is
import-forbidden from outside the package — consumers use the symbols
re-exported from :mod:`mission_runtime` only (see ADR
``2026-06-07-1-execution-state-canonical-surface`` and
``tests/architectural/test_mission_runtime_surface.py``).

coord-trust-2841 (layer-boundary follow-up): :func:`resolve_mid8` and its
heuristic sibling :func:`mid8_from_slug` are pure (regex-only, no filesystem or
``specify_cli`` dependency) and are relocated here from
``specify_cli.lanes.branch_naming`` so ``mission_runtime`` — the LOWER layer —
owns the identity primitive outright, instead of reaching upward into
``specify_cli`` for it (the layer inversion previously tolerated by an
allow-row in ``_MISSION_RUNTIME_ALLOWED_SPECIFY_CLI``,
``tests/architectural/test_layer_rules.py``). ``specify_cli.lanes.branch_naming``
re-exports both names verbatim so every existing importer keeps working.
"""

from __future__ import annotations

import re

__all__ = [
    "mid8_from_slug",
    "resolve_mid8",
]

# <human-slug>-<mid8>[-lane-<id>] tail check.
# Mid8 = exactly 8 uppercase alphanumeric characters (ULID character set)
_MID8_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{8}$")  # Crockford base32, exactly 8 chars


def mid8_from_slug(slug: str) -> str:
    """Best-effort HEURISTIC detector of a mid8 tail — NEVER authoritative (#1918).

    Recognises the 8-character Crockford base32 tail appended to mission slugs
    by the mission-identity system (e.g. ``my-feature-01KT3YBD`` → ``01KT3YBD``).

    .. warning::
        This is a *heuristic*: it cannot tell a genuine mid8 from a coincidental
        8-Crockford-char hyphen segment, because it has no ``mission_id`` to
        confirm against. It is retained ONLY as a final, best-effort fallback for
        topology consumers (``resolve_transaction_mid8`` /
        ``surface_resolver._coord_mid8``) that have already exhausted every
        declared source. For any correctness path, use the authoritative
        :func:`resolve_mid8`, which derives the mid8 from a declared ``mission_id``
        and declines a coincidental tail when none is available.

    The check is ``_MID8_RE`` (exactly 8 Crockford base32 chars) so that all-digit
    tails (valid in ULID base32) are accepted correctly.
    """
    if "-" not in slug:
        return ""
    tail = slug.rsplit("-", 1)[-1]
    if _MID8_RE.match(tail):
        return tail
    return ""


def resolve_mid8(mission_slug: str, *, mission_id: str | None) -> str:
    """Authoritative mid8 resolver for correctness paths (#1918, FR-004).

    Unlike the heuristic :func:`mid8_from_slug`, this derives the mid8 from the
    *declared* ``mission_id`` and trusts the slug's embedded tail only when it
    **provably matches** that declared identity. When no ``mission_id`` is
    available it DECLINES (returns ``""``) on an embedded 8-char tail rather than
    mis-resolving a coincidental segment — the name proposes, authority disposes.

    Resolution:
      - ``mission_id`` present (>= 8 chars), slug embeds NO tail or a *matching*
        tail → ``mission_id[:8]`` (authoritative, provable-match cross-checked).
      - ``mission_id`` present but the slug embeds a *divergent* tail → still
        ``mission_id[:8]``: the declared identity governs; the stale slug tail
        never wins (NFR-003).
      - ``mission_id`` absent → the embedded tail cannot be confirmed against a
        declared identity, so it is NOT trusted: DECLINE (``""``).

    Returns:
        The 8-char mid8 when it can be authoritatively derived, else ``""``.
    """
    embedded = mid8_from_slug(mission_slug)
    if mission_id is not None and len(mission_id) >= 8:
        declared = mission_id[:8]
        if embedded and embedded != declared:
            # Slug carries a stale/foreign mid8 tail; declared identity governs.
            return declared
        # No tail, or a tail that provably matches the declared identity.
        return declared
    # No declared identity to confirm a (possibly coincidental) 8-char tail
    # against: decline rather than mis-resolve (#1918).
    return ""
