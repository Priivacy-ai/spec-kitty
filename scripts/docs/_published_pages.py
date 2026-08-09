"""Single authority for "which documentation source pages are published".

That question used to have *two* answers: ``docs/docfx.json`` — which the DocFX
build follows — and a hardcoded glob list inside ``tests/docs/test_docs_seo.py``
— which the SEO gate followed. When ``how-to/`` became ``guides/`` and
``reference/slash-commands`` became ``api/``, the build followed the move and
the gate did not. The gate kept reporting green while resolving **16 of 674**
pages.

This module removes the possibility of a second list. It reads
``docs/docfx.json`` **at call time** and returns a :class:`PublishedPageSet`
that carries its own provenance (:attr:`PublishedPageSet.source_globs`) and its
own exclusion rationale (:attr:`PublishedPageSet.exclusions`), so a consuming
gate can explain *why* a page is absent instead of silently omitting it.

Two properties are load-bearing:

* **Fail-closed.** Every degraded resolution raises. There is no code path on
  which this function returns a partial set, because a silently-partial set is
  precisely the defect under repair (I-01, I-02).
* **DocFX glob semantics, not ``pathlib`` semantics.** DocFX's ``context/**.md``
  matches ``context/foo.md``; the naive translation ``context/**/*.md`` does
  not. Getting that wrong under-collects silently — the same bug wearing a new
  hat — so :func:`_docfx_glob_to_regex` is validated by membership assertions
  against known live pages rather than by reasoning (C-R5).

The leading underscore matches the existing convention for shared internal
helpers in this package (``_inventory.py``, ``_render.py``): this is a library,
not an entry point.

Depends only on the standard library.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

__all__ = [
    "DEFAULT_DOCFX_CONFIG_NAME",
    "DEFAULT_EXCLUSIONS",
    "MINIMUM_EXPECTED_PAGES",
    "Exclusion",
    "PublishedPageSet",
    "resolve_published_pages",
]

DEFAULT_DOCFX_CONFIG_NAME: Final[str] = "docfx.json"

#: Non-vacuity floor (I-02). The published set measured 674 pages when this
#: gate was built, and the broken gate it replaces resolved 16. 500 sits far
#: enough below 674 that ordinary page churn — even a sizeable deletion sweep —
#: cannot false-fail, and far enough above 16 that today's defect trips it
#: immediately.
#:
#: Deliberately a **floor**, not an exact census. This repository already
#: retired a hardcoded exact ADR census constant on the grounds that it "guards
#: little and merely fails on every legitimate add/remove — pure future
#: friction". A floor captures the real invariant (the set must not collapse)
#: without that friction. Raising it is a deliberate act; lowering it requires a
#: written justification.
MINIMUM_EXPECTED_PAGES: Final[int] = 500

_MARKDOWN_SUFFIX: Final[str] = ".md"
_CURRENT_DIR: Final[str] = "."


@dataclass(frozen=True, slots=True)
class Exclusion:
    """A path pattern deliberately held out of the published set, with a reason.

    An exclusion without a stated reason is indistinguishable from an oversight,
    which is the failure mode FR-013 exists to prevent — so an empty ``reason``
    is rejected at construction time (I-05) rather than merely asserted about
    later.
    """

    pattern: str
    reason: str

    def __post_init__(self) -> None:
        """Reject patternless or reasonless exclusions (I-05)."""
        if not self.pattern.strip():
            raise ValueError("Exclusion.pattern must be a non-empty glob")
        if not self.reason.strip():
            raise ValueError(f"Exclusion({self.pattern!r}) must state a non-empty reason (I-05)")


@dataclass(frozen=True, slots=True)
class PublishedPageSet:
    """The authoritative answer to "which source pages are published".

    Attributes
    ----------
    pages:
        Repo-relative paths of published Markdown source pages, rendered
        relative to ``docs_root.parent`` — i.e. ``docs/api/slash-commands.md``
        for the canonical ``<repo>/docs`` tree. This matches the repo-relative
        convention already used by ``description_length_check``.
    source_globs:
        The ``build.content[].files`` Markdown patterns read from
        ``docfx.json``, retained purely for diagnostics: a gate reporting a
        coverage failure must be able to say which globs produced the set.
    exclusions:
        Exclusions applied on top of DocFX's own ``exclude`` list, each with a
        reason (FR-013, I-04/I-05).
    """

    pages: frozenset[Path]
    source_globs: tuple[str, ...]
    exclusions: tuple[Exclusion, ...]


#: Exclusions applied on top of the ``exclude`` list ``docfx.json`` declares for
#: itself. Every entry states why (I-05); an unstated drop would be exactly the
#: unattributed gap I-04 forbids.
DEFAULT_EXCLUSIONS: Final[tuple[Exclusion, ...]] = (
    Exclusion(
        pattern="archive/**",
        reason="Immutable legacy snapshot; not rewritten for search (C-005)",
    ),
    Exclusion(
        pattern="kitty-specs/**",
        reason="Generated mission-run pages; no human author for a description",
    ),
)


@dataclass(frozen=True, slots=True)
class _ContentEntry:
    """One resolved ``build.content[]`` entry, ready to walk."""

    base: Path
    rel_prefix: str
    includes: tuple[re.Pattern[str], ...]
    excludes: tuple[re.Pattern[str], ...]
    globs: tuple[str, ...]


def resolve_published_pages(
    *,
    docs_root: Path,
    docfx_config: Path | None = None,
) -> PublishedPageSet:
    """Resolve the published page set from the build's own declaration.

    Parameters
    ----------
    docs_root:
        Directory containing the documentation tree. Content globs are resolved
        relative to it, and returned pages are rendered relative to its parent.
    docfx_config:
        Path to ``docfx.json``; defaults to ``docs_root / "docfx.json"``.

    Returns
    -------
    PublishedPageSet
        The fully validated set. This function never returns a partial one.

    Raises
    ------
    FileNotFoundError
        ``docfx.json`` is absent. A missing authority must fail loud rather than
        degrade to "assume everything" or "assume nothing".
    ValueError
        ``docfx.json`` is unparseable or structurally wrong; or the resolved set
        is empty (I-01); or it falls below :data:`MINIMUM_EXPECTED_PAGES`
        (I-02), in which case the message names both the observed and the
        expected count.
    """
    config_path = docfx_config if docfx_config is not None else docs_root / DEFAULT_DOCFX_CONFIG_NAME
    entries = tuple(
        _build_content_entry(raw, docs_root=docs_root)
        for raw in _load_content_entries(config_path)
    )

    candidates: set[Path] = set()
    for entry in entries:
        candidates |= _collect_entry_pages(entry)

    # Per-glob pre-exclusion guard (FR-003): every declared include glob must match
    # at least one file *before* any exclusion is applied. The aggregate floor below
    # only sees the union, so a dropped subtree hides behind the other globs; this
    # guard restores per-glob attribution the union collapses. Raw counts here — a
    # glob whose matches are all later excluded (e.g. ``archive/**``) is legitimate.
    _assert_each_glob_nonvacuous(entries, config_path=config_path)

    source_globs = _dedupe(glob for entry in entries for glob in entry.globs)
    kept = _apply_exclusions(candidates, DEFAULT_EXCLUSIONS)
    _assert_non_vacuous(kept, config_path=config_path, source_globs=source_globs)

    prefix = docs_root.name
    pages = frozenset(Path(prefix, relative) if prefix else relative for relative in kept)
    return PublishedPageSet(pages=pages, source_globs=source_globs, exclusions=DEFAULT_EXCLUSIONS)


def _load_content_entries(config_path: Path) -> list[Mapping[str, Any]]:
    """Read ``build.content[]`` from ``config_path``. Never falls back."""
    if not config_path.is_file():
        raise FileNotFoundError(
            f"DocFX configuration {config_path} not found; the published page set has no authority to read"
        )
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"DocFX configuration {config_path} is unparseable: {exc}") from exc

    build = payload.get("build") if isinstance(payload, Mapping) else None
    content = build.get("content") if isinstance(build, Mapping) else None
    if not isinstance(content, Sequence) or isinstance(content, str | bytes):
        raise ValueError(f"DocFX configuration {config_path} has no 'build.content' list")

    entries = [entry for entry in content if isinstance(entry, Mapping)]
    if not entries:
        raise ValueError(f"DocFX configuration {config_path} declares no usable 'build.content' entries")
    return entries


def _build_content_entry(raw: Mapping[str, Any], *, docs_root: Path) -> _ContentEntry:
    """Compile one ``build.content[]`` entry into matchers rooted at its ``src``.

    Only ``.md`` patterns are page candidates — ``toc.yml`` appears in the
    content list but is navigation, not a page.
    """
    src = str(raw.get("src") or _CURRENT_DIR).strip("/") or _CURRENT_DIR
    markdown_globs = tuple(
        pattern for pattern in _string_list(raw.get("files")) if pattern.endswith(_MARKDOWN_SUFFIX)
    )
    return _ContentEntry(
        base=docs_root if src == _CURRENT_DIR else docs_root / src,
        rel_prefix="" if src == _CURRENT_DIR else f"{src}/",
        includes=tuple(_docfx_glob_to_regex(pattern) for pattern in markdown_globs),
        excludes=tuple(_docfx_glob_to_regex(pattern) for pattern in _string_list(raw.get("exclude"))),
        globs=tuple(
            pattern if src == _CURRENT_DIR else f"{src}/{pattern}" for pattern in markdown_globs
        ),
    )


def _collect_entry_pages(entry: _ContentEntry) -> set[Path]:
    """Walk ``entry.base`` once and return the matching ``docs_root``-relative pages."""
    if not entry.includes or not entry.base.is_dir():
        return set()
    found: set[Path] = set()
    for path in entry.base.rglob(f"*{_MARKDOWN_SUFFIX}"):
        if not path.is_file():
            continue
        relative = path.relative_to(entry.base).as_posix()
        if not _matches_any(relative, entry.includes):
            continue
        if _matches_any(relative, entry.excludes):
            continue
        found.add(Path(f"{entry.rel_prefix}{relative}"))
    return found


def _apply_exclusions(pages: set[Path], exclusions: tuple[Exclusion, ...]) -> set[Path]:
    """Drop pages attributable to an enumerated :class:`Exclusion` (I-04)."""
    patterns = tuple(_docfx_glob_to_regex(exclusion.pattern) for exclusion in exclusions)
    return {page for page in pages if not _matches_any(page.as_posix(), patterns)}


def _vacuity_error(
    *,
    config_path: Path,
    source_globs: tuple[str, ...],
    detail: str,
) -> ValueError:
    """Build the canonical non-vacuity :class:`ValueError` shared by every raise site.

    ``detail`` carries the load-bearing rationale substrings the gate's tests assert
    on verbatim (``violates I-01``, ``collapsed (violates I-02)``, ``expected at
    least``); the surrounding sentence and the ``globs were`` provenance are constant
    so a third raise site (the per-glob guard) cannot drift the message shape.
    """
    return ValueError(
        f"Published page set resolved from {config_path} {detail}; "
        f"globs were {list(source_globs)}"
    )


def _assert_each_glob_nonvacuous(
    entries: tuple[_ContentEntry, ...],
    *,
    config_path: Path,
) -> None:
    """Raise unless every declared include glob matches at least one file (I-01, FR-003).

    Operates on the in-scope ``entries`` — NOT the deduped/union ``candidates`` — so a
    dropped subtree is attributed to the specific glob and content entry that produced
    it. Each glob is counted with a **raw** pass that ignores both the entry-level
    ``exclude`` and :data:`DEFAULT_EXCLUSIONS`, because a glob whose matches are wholly
    excluded downstream (e.g. ``archive/**``) is legitimate and must not false-fail.
    """
    for entry in entries:
        for include, human_glob in zip(entry.includes, entry.globs, strict=True):
            if _count_raw_matches(entry, include) < 1:
                raise _vacuity_error(
                    config_path=config_path,
                    source_globs=(human_glob,),
                    detail=(
                        f"declared glob {human_glob!r} in content entry rooted at "
                        f"{entry.rel_prefix.rstrip('/') or _CURRENT_DIR!r} is empty "
                        "(violates I-01): it matched no files pre-exclusion"
                    ),
                )


def _count_raw_matches(entry: _ContentEntry, include: re.Pattern[str]) -> int:
    """Count files under ``entry.base`` matching ``include``, ignoring every exclusion."""
    if not entry.base.is_dir():
        return 0
    count = 0
    for path in entry.base.rglob(f"*{_MARKDOWN_SUFFIX}"):
        if path.is_file() and include.match(path.relative_to(entry.base).as_posix()):
            count += 1
    return count


def _assert_non_vacuous(
    pages: set[Path],
    *,
    config_path: Path,
    source_globs: tuple[str, ...],
) -> None:
    """Raise unless the resolved set is non-empty (I-01) and above the floor (I-02)."""
    observed = len(pages)
    if observed == 0:
        raise _vacuity_error(
            config_path=config_path,
            source_globs=source_globs,
            detail="is empty (violates I-01)",
        )
    if observed < MINIMUM_EXPECTED_PAGES:
        raise _vacuity_error(
            config_path=config_path,
            source_globs=source_globs,
            detail=(
                f"collapsed (violates I-02): observed {observed} page(s), "
                f"expected at least {MINIMUM_EXPECTED_PAGES}"
            ),
        )


def _docfx_glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Compile a DocFX content glob into an anchored regex over POSIX paths.

    DocFX glob semantics are **not** ``pathlib`` semantics:

    ==========================  ==========================================
    Pattern                     Matches
    ==========================  ==========================================
    ``context/**.md``           ``context/foo.md`` *and* ``context/a/b.md``
    ``**/_*.md``                ``_draft.md`` *and* ``a/_draft.md``
    ``how-to/*.md``             ``how-to/foo.md`` only
    ==========================  ==========================================

    So ``**`` crosses directory separators and ``**/`` also matches *zero*
    directories, while a single ``*`` never crosses one.
    """
    parts: list[str] = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            parts.append("(?:.*/)?")  # ``**/`` spans zero or more directories
            index += 3
        elif pattern.startswith("**", index):
            parts.append(".*")  # bare ``**`` crosses separators
            index += 2
        elif pattern[index] == "*":
            parts.append("[^/]*")  # a single ``*`` stays within one segment
            index += 1
        elif pattern[index] == "?":
            parts.append("[^/]")
            index += 1
        else:
            parts.append(re.escape(pattern[index]))
            index += 1
    return re.compile(f"^{''.join(parts)}$")


def _matches_any(relative: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    """Return whether ``relative`` matches any compiled pattern."""
    return any(pattern.match(relative) for pattern in patterns)


def _string_list(value: Any) -> tuple[str, ...]:
    """Coerce a DocFX ``files``/``exclude`` field into a tuple of strings."""
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Sequence):
        return tuple(item for item in value if isinstance(item, str))
    return ()


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    """Return ``values`` without duplicates, preserving first-seen order."""
    return tuple(dict.fromkeys(values))
