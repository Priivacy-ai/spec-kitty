"""Canonical fetch + when-doing stanza formatter (WP05 T020).

This helper centralises the wire format used by every renderer that
emits the *verbatim-OR-fetch* pair pinned by the prompt-governance
ATDD contract:

* line 1 — ``Run: spec-kitty charter context --include <selector>``
* line 2 — ``When you <verb-clause>, run this command and apply the
  returned rule.``

The pair is matched by the ATDD helpers ``_FETCH_CMD_RE`` and
``_WHEN_DOING_RE`` in
``tests/specify_cli/next/test_wp_prompt_governance_contract.py``.  Drift
on either half is a contract violation — keep the strings here in sync
with the contract document
``kitty-specs/wp-prompt-governance-payload-01KRR8HS/contracts/charter-context-resolver.md``
(section 2 "Verbatim-OR-fetch stanza") if either ever needs to change.

The shared formatter is used by:

* WP03 profile-cited directive / tactic rendering (over-budget per-entry
  substitution),
* WP04 action-critical section rendering (missing-section fall-through),
* WP05 token-budget substitution (longest-body swap).
"""

from __future__ import annotations

__all__ = [
    "DEFAULT_WHEN_CLAUSE",
    "fetch_stanza",
    "fetch_stanza_lines",
    "format_selector",
]


DEFAULT_WHEN_CLAUSE: str = "are about to apply a code change"
"""Fallback when-doing clause when no domain-specific copy is available.

The clause matches the ``_WHEN_DOING_RE`` regex (anchor: ``are about
to``) so it always satisfies the prompt-governance contract — see
``tests/specify_cli/next/test_wp_prompt_governance_contract.py``.
"""


_VALID_SELECTOR_KINDS: frozenset[str] = frozenset({"directive", "tactic", "section"})


def format_selector(kind: str, identifier: str) -> str:
    """Return the canonical ``<kind>:<identifier>`` selector.

    ``kind`` is normalised to lowercase and validated against the set of
    selector kinds the ``spec-kitty charter context --include`` surface
    accepts (``directive``, ``tactic``, ``section``).  An unknown kind
    is permitted (returned as-is) so callers can extend the vocabulary
    without code changes here, but the canonical kinds are guaranteed
    to round-trip through the validator unchanged.
    """

    cleaned_kind = (kind or "").strip().lower()
    cleaned_id = (identifier or "").strip()
    if not cleaned_kind or not cleaned_id:
        return ""
    if cleaned_kind not in _VALID_SELECTOR_KINDS:
        # Permissive on unknown kinds — keep callers extensible.
        return f"{cleaned_kind}:{cleaned_id}"
    return f"{cleaned_kind}:{cleaned_id}"


def fetch_stanza(
    selector: str,
    when_doing_clause: str,
    *,
    indent: str = "",
) -> str:
    """Return the two-line fetch + when-doing stanza for *selector*.

    Parameters
    ----------
    selector:
        The canonical ``<kind>:<identifier>`` selector (see
        :func:`format_selector`).  Used verbatim in the rendered
        ``--include`` argument.
    when_doing_clause:
        The verb-phrase that completes the ``When you <clause>, ...``
        sentence.  When empty, falls back to :data:`DEFAULT_WHEN_CLAUSE`
        so the ATDD ``_WHEN_DOING_RE`` regex always matches.
    indent:
        Optional leading indentation applied to both lines.  The default
        of an empty string keeps the stanza top-level; callers nesting
        the stanza inside a list-item block typically pass ``"  "`` or
        ``"    "``.

    Returns
    -------
    str
        Newline-joined two-line stanza.
    """

    clause = (when_doing_clause or "").strip() or DEFAULT_WHEN_CLAUSE
    return "\n".join(fetch_stanza_lines(selector, clause, indent=indent))


def fetch_stanza_lines(
    selector: str,
    when_doing_clause: str,
    *,
    indent: str = "",
) -> list[str]:
    """List-form variant of :func:`fetch_stanza` for line-oriented callers.

    The list is always exactly two strings; callers that build the
    rendered payload as a ``list[str]`` (most of ``context.py``) extend
    their working list with this result instead of splitting the joined
    string.
    """

    clause = (when_doing_clause or "").strip() or DEFAULT_WHEN_CLAUSE
    return [
        f"{indent}Run: spec-kitty charter context --include {selector}",
        f"{indent}When you {clause}, run this command and apply the returned rule.",
    ]
