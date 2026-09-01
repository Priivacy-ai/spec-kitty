"""Pure detector for post-integration-only ("un-terminable") acceptance criteria.

Background (#3590, FR-007): a work package whose acceptance criteria can only be
satisfied *after* the change is merged/integrated cannot be terminated by looking
at its own diff. Authoring such a WP is a trap — the reviewer can never close it
from the lane. This module detects the shape at authoring time so the operator
can re-home the obligation to a tracked post-merge document.

There is no structured post-integration signal in the data model today
(``ownership/models.py`` carries only ``code_change`` / ``planning_artifact``; a
structured ``completion_kind`` is deferred to #3550, C-003). So the detector keys
on an **enumerable, versioned trigger-phrase set** and is measured against a
**fixed labeled corpus** (SC-003) rather than making an open-world claim.

Everything here is a pure function of its inputs: no filesystem, network, or
process I/O. The advisory CLI surface (``spec-kitty agent tasks
check-terminability``) owns the I/O and calls into this module.
"""

from __future__ import annotations

from dataclasses import dataclass

# Bump when the trigger set changes so corpus-measured claims stay pinned to a
# known set. The corpus (tests/.../fixtures/) is the oracle for this version.
TRIGGER_SET_VERSION = 1

# Longest excerpt we surface per match; criterion lines are truncated with an
# ellipsis so terminal/JSON output stays readable.
_MAX_EXCERPT_LENGTH = 200
_ELLIPSIS = "…"

# Characters stripped from the front of a matched line so a markdown bullet /
# checkbox / heading renders as a clean criterion excerpt.
_LEADING_MARKUP = " \t-*#>[]x"

# Enumerable trigger phrases (the versioned set). Each entry is the canonical
# display form; matching is performed against a normalized variant (see
# ``_normalize``) so hyphen/whitespace/case differences do not cause misses.
# These phrases denote completion that is only observable *after* integration —
# not ordinary mentions of CI or merge, which are near-misses the negative
# corpus guards against.
_TRIGGER_PHRASES: tuple[str, ...] = (
    "after merge",
    "post-merge",
    "once merged",
    "on a branch the forge will run",
    "in CI once enabled",
    "consecutive runs",
    "merge-blocked-when-absent",
)


def _normalize(text: str) -> str:
    """Fold case, treat hyphens/underscores as spaces, and collapse whitespace.

    Normalizing both the trigger phrases and the scanned text through the same
    function means ``post-merge``, ``post merge`` and ``POST_MERGE`` all match
    the single ``post-merge`` trigger without enumerating every spelling.
    """
    lowered = text.lower()
    folded = lowered.replace("-", " ").replace("_", " ")
    return " ".join(folded.split())


# Precompute (canonical, normalized) pairs once at import; the module is pure so
# this is a safe module-level constant.
_NORMALIZED_TRIGGERS: tuple[tuple[str, str], ...] = tuple((phrase, _normalize(phrase)) for phrase in _TRIGGER_PHRASES)


@dataclass(frozen=True)
class PostIntegrationWarning:
    """One advisory warning that a criterion is only satisfiable post-integration.

    Attributes:
        wp_id: The work package the criterion belongs to (e.g. ``"WP03"``).
        matched_phrase: The canonical trigger phrase that fired.
        criterion_excerpt: The (cleaned, truncated) source line that matched.
    """

    wp_id: str
    matched_phrase: str
    criterion_excerpt: str

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-serializable mapping of this warning."""
        return {
            "wp_id": self.wp_id,
            "matched_phrase": self.matched_phrase,
            "criterion_excerpt": self.criterion_excerpt,
        }


def trigger_phrases() -> tuple[str, ...]:
    """Return the enumerable trigger-phrase set (canonical display forms)."""
    return _TRIGGER_PHRASES


def _clean_excerpt(line: str) -> str:
    """Strip leading markdown markup and truncate a matched line for display."""
    cleaned = line.strip().lstrip(_LEADING_MARKUP).strip()
    if len(cleaned) > _MAX_EXCERPT_LENGTH:
        return cleaned[: _MAX_EXCERPT_LENGTH - 1].rstrip() + _ELLIPSIS
    return cleaned


def scan_work_package(wp_id: str, text: str) -> list[PostIntegrationWarning]:
    """Scan one work package's prose for post-integration-only criteria.

    Pure: depends only on ``wp_id`` and ``text``. Scans line-by-line so the
    surfaced excerpt is the criterion (bullet/line) that fired, and so a trigger
    phrase must appear within a single line to match (acceptance criteria are
    authored as single bullets, so this is the intended granularity).

    Args:
        wp_id: Work package identifier, echoed into each warning.
        text: The work package's acceptance-criteria / subtask prose.

    Returns:
        Zero or more warnings, in document order. Empty when no trigger phrase
        appears — the common, non-trapped case.
    """
    warnings: list[PostIntegrationWarning] = []
    for line in text.splitlines():
        normalized_line = _normalize(line)
        if not normalized_line:
            continue
        for canonical, normalized_trigger in _NORMALIZED_TRIGGERS:
            if normalized_trigger in normalized_line:
                warnings.append(
                    PostIntegrationWarning(
                        wp_id=wp_id,
                        matched_phrase=canonical,
                        criterion_excerpt=_clean_excerpt(line),
                    )
                )
    return warnings
