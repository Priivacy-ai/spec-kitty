"""Compact charter view (FR-034, WP07/T041).

Bootstrap mode renders the whole charter governance bundle: paradigms,
directives, tactics, tools, plus the long-form prose body of each
section. Compact mode is what we hand to agents on subsequent action
loads to keep the context window cheap, but until WP07 it dropped the
*identifiers* — directive IDs, tactic IDs, and section anchors — which
agents key on. Issue #790 traced bad agent behaviour to that loss.

The contract this module enforces (and the contract test asserts): for
any charter, the set of directive IDs, tactic IDs, and section anchors
emitted by ``render_compact_view`` is exactly the set emitted by the
bootstrap view. Only long-form prose may be elided in compact mode.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from charter._doctrine_paths import resolve_project_root
from charter.language_scope import infer_repo_languages
from charter.resolver import GovernanceResolutionError, resolve_governance


__all__ = [
    "CompactView",
    "extract_section_anchors",
    "render_compact_view",
]

NONE_LABEL = "(none)"
KITTIFY_DIRNAME = ".kittify"

# Markdown headings start with one or more `#` plus a space; we
# capture everything after the leading hashes as the anchor text.
_SECTION_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class CompactView:
    """Structured payload for the compact charter view.

    Tests treat the four ID/anchor sets as the contract surface.
    ``text`` is the rendered string suitable for direct inclusion in
    agent context, and ``token_estimate`` is a coarse character-based
    proxy used by smoke checks to verify compact stays meaningfully
    smaller than bootstrap.
    """

    text: str
    directive_ids: tuple[str, ...] = field(default_factory=tuple)
    tactic_ids: tuple[str, ...] = field(default_factory=tuple)
    section_anchors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def token_estimate(self) -> int:
        """Rough proxy for token count (4 chars/token heuristic)."""
        return max(1, len(self.text) // 4)


def extract_section_anchors(charter_text: str) -> list[str]:
    """Return ordered, de-duplicated section anchor strings.

    A "section anchor" is the heading text from any ``#``-style
    Markdown heading. We preserve insertion order so anchors line up
    with the bootstrap reading order, and deduplicate so repeated
    headings (rare, but possible) only contribute once to the contract.
    """
    seen: set[str] = set()
    anchors: list[str] = []
    for line in charter_text.splitlines():
        match = _SECTION_HEADING_RE.match(line.rstrip())
        if not match:
            continue
        anchor = match.group(2).strip()
        if not anchor or anchor in seen:
            continue
        seen.add(anchor)
        anchors.append(anchor)
    return anchors


def render_compact_view(
    repo_root: Path,
    *,
    directive_ids: Iterable[str] = (),
    tactic_ids: Iterable[str] = (),
    section_anchors: Iterable[str] | None = None,
    charter_text: str | None = None,
) -> CompactView:
    """Render the compact governance block with IDs + anchors preserved.

    Args:
        repo_root: The mission repo root used to resolve governance.
        directive_ids: Directive IDs the bootstrap view would surface.
            Each ID is emitted verbatim in the compact output.
        tactic_ids: Tactic IDs the bootstrap view would surface.
        section_anchors: Optional pre-computed anchor list. When omitted
            the helper extracts anchors from ``charter_text`` (or, if
            both are omitted, from ``<repo_root>/.kittify/charter/charter.md``
            when present).
        charter_text: Optional charter body text used for anchor
            extraction; convenient for tests.

    Returns:
        :class:`CompactView` carrying the rendered text and the four
        ID/anchor tuples that form the contract surface.
    """
    directive_tuple = tuple(dict.fromkeys(directive_ids))
    tactic_tuple = tuple(dict.fromkeys(tactic_ids))

    if section_anchors is not None:
        anchor_tuple = tuple(dict.fromkeys(section_anchors))
    else:
        if charter_text is None:
            charter_path = repo_root / KITTIFY_DIRNAME / "charter" / "charter.md"
            charter_text = ""
            if charter_path.exists():
                try:
                    charter_text = charter_path.read_text(encoding="utf-8")
                except OSError:
                    charter_text = ""
        anchor_tuple = tuple(extract_section_anchors(charter_text))

    text = _render_text(repo_root, directive_tuple, tactic_tuple, anchor_tuple)

    return CompactView(
        text=text,
        directive_ids=directive_tuple,
        tactic_ids=tactic_tuple,
        section_anchors=anchor_tuple,
    )


def _render_text(
    repo_root: Path,
    directive_ids: tuple[str, ...],
    tactic_ids: tuple[str, ...],
    section_anchors: tuple[str, ...],
) -> str:
    """Render the human-readable compact governance block.

    The format is intentionally line-oriented and stable so downstream
    diffs in agent context stay reviewable. Long-form prose is replaced
    by ID lists and an anchor index. When governance cannot be resolved
    (e.g., the repo lacks ``.kittify`` config) the renderer still emits
    every supplied directive ID, tactic ID, and section anchor — the
    FR-034 contract is "no IDs are silently dropped", so a degraded
    governance block must not erase the IDs the caller already knows.
    """
    paradigms = NONE_LABEL
    tools = NONE_LABEL
    template_set = NONE_LABEL
    diagnostics: list[str] = []
    resolver_directives: list[str] = []

    try:
        resolution = resolve_governance(repo_root)
    except GovernanceResolutionError as exc:
        diagnostics.append(f"governance unresolved ({exc})")
        resolution = None
    except Exception as exc:  # pragma: no cover - defensive degrade
        diagnostics.append(f"governance unavailable ({exc})")
        resolution = None

    if resolution is not None:
        paradigms = ", ".join(resolution.paradigms) if resolution.paradigms else NONE_LABEL
        tools = ", ".join(resolution.tools) if resolution.tools else NONE_LABEL
        template_set = resolution.template_set
        diagnostics.extend(list(resolution.diagnostics))
        resolver_directives = list(resolution.directives)

    merged_directive_ids = tuple(
        dict.fromkeys(list(directive_ids) + resolver_directives)
    )

    lines: list[str] = [
        "Governance:",
        f"  - Template set: {template_set}",
        f"  - Paradigms: {paradigms}",
        f"  - Tools: {tools}",
    ]

    lines.append("Directive IDs:")
    if merged_directive_ids:
        for did in merged_directive_ids:
            lines.append(f"  - {did}")
    else:
        lines.append(f"  - {NONE_LABEL}")

    lines.append("Tactic IDs:")
    if tactic_ids:
        for tid in tactic_ids:
            lines.append(f"  - {tid}")
    else:
        lines.append(f"  - {NONE_LABEL}")

    lines.append("Section Anchors:")
    if section_anchors:
        for anchor in section_anchors:
            lines.append(f"  - {anchor}")
    else:
        lines.append(f"  - {NONE_LABEL}")

    if diagnostics:
        lines.append(f"  - Diagnostics: {' | '.join(diagnostics)}")

    # Reference repo languages / project root only as a footnote so the
    # compact view stays one-screen even on big charters.
    try:
        languages = infer_repo_languages(repo_root)
        if languages:
            lines.append(f"  - Languages: {', '.join(sorted(languages))}")
    except Exception:  # pragma: no cover - defensive
        pass

    try:
        project_root = resolve_project_root(repo_root)
        if project_root != repo_root:
            lines.append(f"  - Project root: {project_root}")
    except Exception:  # pragma: no cover - defensive
        pass

    return "\n".join(lines)
