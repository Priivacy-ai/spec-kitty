"""Shared helpers for optional doctrine artifact scoping."""

from __future__ import annotations

from typing import Iterable

#: Sentinel strings that should never appear as real language tokens.
#: ``doctrine validate`` rejects artifacts that carry these at authoring time
#: (T020 guard in ``_validate_single_artifact``).  At runtime, reaching
#: ``applies_to_languages_match`` with one of these sentinels means the
#: artifact bypassed validation (e.g. hand-edited or loaded without the CLI
#: guard).  Defense-in-depth: treat them as unscoped so the artifact loads
#: rather than silently disappearing — the validator is the authoring-time
#: signal; the runtime must never silently drop content.
_SENTINEL_TOKENS: frozenset[str] = frozenset({"any", "all"})


def normalize_languages(values: Iterable[str] | None) -> tuple[str, ...]:
    """Return lowercase, de-duplicated language identifiers."""
    if values is None:
        return ()

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value).strip().lower()
        if not item or item in seen:
            continue
        seen.add(item)
        normalized.append(item)
    return tuple(normalized)


def applies_to_languages_match(
    artifact_languages: Iterable[str] | None,
    active_languages: Iterable[str] | None,
) -> bool:
    """Return whether an artifact should load for the active language set.

    Rules:
    - Unscoped artifacts always load.
    - When no active language filter is provided, scoped artifacts still load.
    - When active languages are explicitly empty/unknown, scoped artifacts do not load.
    - Otherwise any overlap between artifact and active languages is sufficient.

    Defense-in-depth (T021): if ``artifact_languages`` contains a sentinel
    token (``any`` / ``all``) the artifact is treated as unscoped (always
    loads).  These tokens are rejected at authoring time by the
    ``doctrine validate`` guard; reaching this function with them means the
    artifact bypassed validation.  Treating them as unscoped is the correct
    fallback — silently filtering the artifact would cause harder-to-diagnose
    missing-content failures at runtime.
    """
    artifact_scope = set(normalize_languages(artifact_languages))
    if not artifact_scope:
        return True

    # Defense-in-depth: sentinel tokens bypass scope filtering — see docstring.
    if artifact_scope <= _SENTINEL_TOKENS:
        return True

    if active_languages is None:
        return True

    active_scope = set(normalize_languages(active_languages))
    if not active_scope:
        return False

    return bool(artifact_scope & active_scope)
