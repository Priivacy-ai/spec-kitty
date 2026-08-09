"""Shared non-vacuity examined-floor guard (#3273).

``related_validator.validate_related`` and
``relative_link_fixer.check_dead_body_links`` each implement the same
"examined-count floor" shape: walk a tree, count how many things were
examined, and raise :class:`RuntimeError` when that count falls short of a
caller-supplied minimum — a scope-narrowing regression (a missing tree, an
empty tree, or a parsing change that stops matching entries) must go **red**
immediately rather than silently reporting "0 findings" over 0 examined.
``related_validator.py`` even carried a comment self-acknowledging the two
call sites were mirrors of one another. This module is the single source for
that guard so the two modules stop drifting independently.

This is a distinct contract from ``redirect_stub_generator.assert_non_vacuous``
(raises ``ValueError``) and the ``_published_pages`` census floor (also
``ValueError`` / ``CoverageError``) — those are a different exception family
and are intentionally left alone.
"""

from __future__ import annotations


def assert_examined_floor(
    count: int,
    minimum: int,
    *,
    gate: str,
    noun: str,
    fr_id: str,
    extra: str | None = None,
) -> None:
    """Raise ``RuntimeError`` when ``count`` falls below the non-vacuity ``minimum``.

    Parameters
    ----------
    count:
        The number of items actually examined by the walk (e.g. files visited,
        edges resolved, links matched).
    minimum:
        The non-vacuity floor: the walk must examine at least this many items.
    gate:
        Name of the calling gate/function, prefixed to the message (e.g.
        ``"related_validator"`` or ``"check_dead_body_links"``).
    noun:
        Description of what was counted, including any scope context (e.g.
        ``"related edge(s) examined under {docs_root}"`` or ``"doc file(s)
        found under docs/"``).
    fr_id:
        The functional-requirement id this floor traces to (e.g. ``"FR-004"``
        or ``"FR-008"``), used to compose the trailing ``"(<fr_id>
        non-vacuity guard)"`` phrase every caller's tests match on.
    extra:
        Optional additional detail appended inside the trailing parenthetical
        (e.g. ``"possible misconfiguration"``), for callers whose original
        message carried a caller-specific caveat.

    Raises
    ------
    RuntimeError
        When ``count < minimum``.
    """
    if count < minimum:
        detail = f", {extra}" if extra else ""
        raise RuntimeError(
            f"{gate}: only {count} {noun} — expected at least {minimum} "
            f"({fr_id} non-vacuity guard{detail})"
        )
