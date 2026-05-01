"""Shared helpers for optional doctrine artifact scoping."""

from __future__ import annotations

from typing import Iterable


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
    """
    artifact_scope = set(normalize_languages(artifact_languages))
    if not artifact_scope:
        return True

    if active_languages is None:
        return True

    active_scope = set(normalize_languages(active_languages))
    if not active_scope:
        return False

    return bool(artifact_scope & active_scope)
