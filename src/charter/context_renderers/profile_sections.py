"""Profile-channel render sections (WP12).

A loaded agent profile is a first-class governance entry vector: the implement
loop loads it on every work package. Before WP12 only ``_render_profile_directives``
/ ``_render_profile_tactics`` existed in :mod:`charter.context`, so a profile that
resolved a procedure, styleguide, or toolguide reached its agent with none of them.

This module houses the shared selector-section renderer and the render paths for
the kinds a profile *attests*:

* **styleguide / toolguide** — schema-attested inline reference kinds
  (``styleguide-references`` / ``toolguide-references``).
* **procedure** — reached through the profile *channel*: WP08's
  ``walk_edges({requires, specializes_from})`` traversal
  (:meth:`AgentProfileRepository.profile_channel_procedure_ids`), **not** a
  ``resolve_context`` seed set (profiles carry no outbound ``scope`` edge, so a
  ``resolve_context`` seed would measure zero at any depth — R-3). This is the
  mechanism that carries the PR #3007 exemplar
  ``procedure:onboard-external-agent-to-pack`` — reached from
  ``agent_profile:doctrine-daphne`` by a ``requires`` edge — to the agent.

Unattested kinds (asset / anti-pattern / paradigm) are **not** invented into a
profile section; deciding a profile delivers them is a doctrine question the schema
does not answer, so they are deferred under C-007.

The renderer lives here rather than in :mod:`charter.context` so the shared,
WP-contended ``context.py`` does not grow: ``context.py`` imports these functions
and keeps only its directive/tactic paths. The catalog-miss + fetch-stanza + budget
primitives are re-used from ``context.py`` via a function-local import to avoid a
module-load cycle (``context`` imports this module at top level).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Protocol

from charter.progressive_disclosure import (
    STATED_DEFAULT_WHEN,
    profile_channel_references,
)
from doctrine.drg.models import NodeKind

if TYPE_CHECKING:
    from doctrine.agent_profiles import AgentProfile

__all__ = [
    "format_inline_named_body",
    "render_profile_procedures",
    "render_profile_selector_refs",
    "render_profile_styleguides",
    "render_profile_suggested_doctrine",
    "render_profile_toolguides",
]


_PROFILE_STYLEGUIDES_HEADER_TPL = "Profile-Cited Styleguides ({profile_id}):"
_PROFILE_TOOLGUIDES_HEADER_TPL = "Profile-Cited Toolguides ({profile_id}):"
# Procedures arrive through the profile *channel* (a ``requires`` DRG edge), not an
# inline citation list, so the header reads "Resolved" rather than "Cited".
_PROFILE_PROCEDURES_HEADER_TPL = "Profile-Resolved Procedures ({profile_id}):"
_PROFILE_CODE_CHANGE_WHEN = "are about to apply a code change"

# --- WP01: suggests-delivery render policy (C4) -----------------------------
# The NodeKind values the profile channel delivers when it reaches an artefact
# via a ``suggests`` edge. Deliberately EXCLUDES ``asset`` / ``anti_pattern``
# (non-activatable kinds, C-004 — keeping anti_pattern topology validation-tier
# only, never accidentally delivered) and ``agent_profile`` (a lineage
# pass-through hop, never delivered as doctrine to itself).
_PROFILE_SUGGESTS_DELIVERED_KINDS: frozenset[str] = frozenset(
    {
        NodeKind.PARADIGM.value,
        NodeKind.DIRECTIVE.value,
        NodeKind.TACTIC.value,
        NodeKind.STYLEGUIDE.value,
        NodeKind.TOOLGUIDE.value,
        NodeKind.PROCEDURE.value,
    }
)

# Deterministic render order and, per kind, the ``DoctrineService`` catalog-repo
# attribute plus the human section title.
_SUGGESTS_KIND_RENDER: tuple[tuple[str, str, str], ...] = (
    (NodeKind.PARADIGM.value, "paradigms", "Paradigms"),
    (NodeKind.DIRECTIVE.value, "directives", "Directives"),
    (NodeKind.TACTIC.value, "tactics", "Tactics"),
    (NodeKind.STYLEGUIDE.value, "styleguides", "Styleguides"),
    (NodeKind.TOOLGUIDE.value, "toolguides", "Toolguides"),
    (NodeKind.PROCEDURE.value, "procedures", "Procedures"),
)

_PROFILE_SUGGESTED_HEADER_TPL = "Profile-Suggested {title} ({profile_id}):"
_URN_SEP = ":"


class _CatalogRepoLike(Protocol):
    """Minimal catalog-repository shape the profile renderers look up against."""

    def get(self, item_id: str) -> object | None: ...


def format_inline_named_body(artifact: object) -> list[str]:
    """Render an artifact's ``Name`` / ``Purpose`` / ``Steps`` inline body.

    Shared by the tactic and procedure renderers — both carry a
    ``name`` / ``purpose`` / ``steps`` shape. Procedure steps expose
    ``description`` rather than ``title``; the lookup falls through so either
    shape renders a step line.
    """
    body: list[str] = []
    name = getattr(artifact, "name", None)
    if isinstance(name, str) and name:
        body.append(f"    Name: {name}")
    purpose = getattr(artifact, "purpose", None)
    if isinstance(purpose, str) and purpose.strip():
        body.append(f"    Purpose: {purpose.strip()}")
    steps = getattr(artifact, "steps", None)
    if isinstance(steps, list) and steps:
        body.append("    Steps:")
        for step in steps:
            step_title = (
                getattr(step, "title", None)
                or getattr(step, "description", None)
                or str(step)
            )
            body.append(f"      - {step_title}")
    return body


def render_profile_selector_refs(
    *,
    header: str,
    entries: list[tuple[str, str]],
    repo: _CatalogRepoLike | None,
    selector_kind: str,
    profile_id: str,
    when_clause: str,
    body_fn: Callable[[object], list[str]] | None,
    when_by_id: dict[str, str | None] | None = None,
) -> list[str]:
    """Render one profile section (header + per-entry bodies).

    Each entry emits a ``  - <id>`` header line (optionally ``: <rationale>``),
    then either the inline body (when ``body_fn`` yields one under the per-entry
    budget) or the canonical fetch stanza. A catalog miss degrades to the
    structured miss stanza + warning rather than crashing the resolver (FR-013).
    ``body_fn=None`` always emits the fetch stanza — used for styleguide/toolguide,
    whose bodies vary and are pulled on demand.

    ``when_by_id`` supplies a *per-entry* when-clause override (WP01): the
    suggests-delivery renderer carries each artefact's own edge ``when`` rather
    than a single static clause for the whole section. When an id is absent from
    the mapping (or maps to a falsy value) the section-wide ``when_clause`` is the
    fallback — so the existing static-clause callers (styleguide/toolguide/
    procedure) are unaffected when they pass no mapping.
    """
    per_entry_when = when_by_id or {}
    # Deferred to avoid a module-load cycle: ``charter.context`` imports this
    # module at top level, so these primitives cannot be imported there.
    from charter.context import (  # noqa: PLC0415 — cycle-avoidance
        _PROFILE_INLINE_BODY_LIMIT_CHARS,
        _budget_estimate,
        _diagnose_catalog_miss,
        _render_fetch_stanza,
    )
    from charter._catalog_miss import (  # noqa: PLC0415 — cycle-avoidance
        emit_catalog_miss_warning,
        format_catalog_miss_stanza,
    )

    lines: list[str] = [header]
    for raw_id, rationale in entries:
        artifact_id = str(raw_id).strip()
        header_line = f"  - {artifact_id}"
        if rationale:
            header_line = f"{header_line}: {rationale}"
        lines.append(header_line)

        artifact = None
        if repo is not None:
            try:
                artifact = repo.get(artifact_id)
            except Exception:  # noqa: BLE001 — best-effort catalog lookup
                artifact = None

        if artifact is None:
            diagnosis = _diagnose_catalog_miss(artifact_id, repo)
            lines.extend(
                format_catalog_miss_stanza(
                    selector_kind=selector_kind,
                    artifact_id=artifact_id,
                    diagnosis=diagnosis,
                    indent="    ",
                )
            )
            emit_catalog_miss_warning(
                selector_kind=selector_kind,
                artifact_id=artifact_id,
                diagnosis=diagnosis,
                context=f"profile:{profile_id}",
            )
            continue

        body_lines = body_fn(artifact) if body_fn is not None else []
        if body_lines and _budget_estimate(body_lines) <= _PROFILE_INLINE_BODY_LIMIT_CHARS:
            lines.extend(body_lines)
        else:
            lines.extend(
                _render_fetch_stanza(
                    selector=f"{selector_kind}:{artifact_id}",
                    when_clause=per_entry_when.get(artifact_id) or when_clause,
                )
            )

    return lines


def _ref_entries(refs: Iterable[object]) -> list[tuple[str, str]]:
    """Map a profile reference list to ``(id, rationale)`` entry tuples."""
    return [
        (getattr(ref, "id", ""), getattr(ref, "rationale", "") or "")
        for ref in refs
    ]


def render_profile_styleguides(profile: AgentProfile, service: object) -> list[str]:
    """Render the ``Profile-Cited Styleguides (<profile-id>):`` section (T067).

    Styleguides are a schema-attested profile reference kind. Bodies vary in
    shape and are pulled on demand, so each entry renders as a header line plus
    the ``--include styleguide:<id>`` fetch stanza. Empty when none are cited.
    """
    refs = list(profile.styleguide_references)
    if not refs:
        return []
    return render_profile_selector_refs(
        header=_PROFILE_STYLEGUIDES_HEADER_TPL.format(profile_id=profile.profile_id),
        entries=_ref_entries(refs),
        repo=getattr(service, "styleguides", None),
        selector_kind="styleguide",
        profile_id=profile.profile_id,
        when_clause=_PROFILE_CODE_CHANGE_WHEN,
        body_fn=None,
    )


def render_profile_toolguides(profile: AgentProfile, service: object) -> list[str]:
    """Render the ``Profile-Cited Toolguides (<profile-id>):`` section (T067).

    Toolguides are a schema-attested profile reference kind, rendered as a header
    line plus the ``--include toolguide:<id>`` fetch stanza. Empty when none.
    """
    refs = list(profile.toolguide_references)
    if not refs:
        return []
    return render_profile_selector_refs(
        header=_PROFILE_TOOLGUIDES_HEADER_TPL.format(profile_id=profile.profile_id),
        entries=_ref_entries(refs),
        repo=getattr(service, "toolguides", None),
        selector_kind="toolguide",
        profile_id=profile.profile_id,
        when_clause=_PROFILE_CODE_CHANGE_WHEN,
        body_fn=None,
    )


def render_profile_procedures(profile: AgentProfile, service: object) -> list[str]:
    """Render the ``Profile-Resolved Procedures (<profile-id>):`` section (T068).

    Procedures reach a profile through the profile *channel* — the
    ``walk_edges({requires, specializes_from})`` traversal surfaced by
    :meth:`AgentProfileRepository.profile_channel_procedure_ids` — not through an
    inline citation list. Empty when the profile requires no procedures (a
    fail-closed channel: an absent/unknown profile reaches nothing rather than
    falling open to the whole graph — T069).
    """
    repo = getattr(service, "agent_profiles", None)
    if repo is None:
        return []
    try:
        procedure_ids = repo.profile_channel_procedure_ids(profile.profile_id)
    except Exception:  # noqa: BLE001 — best-effort channel lookup
        procedure_ids = []
    if not procedure_ids:
        return []
    return render_profile_selector_refs(
        header=_PROFILE_PROCEDURES_HEADER_TPL.format(profile_id=profile.profile_id),
        entries=[(pid, "") for pid in procedure_ids],
        repo=getattr(service, "procedures", None),
        selector_kind="procedure",
        profile_id=profile.profile_id,
        when_clause="are about to run this procedure",
        body_fn=format_inline_named_body,
    )


def _bare_id(urn: str) -> str:
    """The artefact id from a DRG URN (``tactic:refactoring-move-method`` -> id)."""
    return urn.split(_URN_SEP, 1)[1] if _URN_SEP in urn else urn


def _kind_of(urn: str) -> str:
    """The kind prefix of a DRG URN (``tactic:foo`` -> ``tactic``)."""
    return urn.split(_URN_SEP, 1)[0] if _URN_SEP in urn else ""


def _consolidate_kind_entries(
    references: list[dict[str, str | None]],
    delivered_ids: set[str],
) -> tuple[list[tuple[str, str]], dict[str, str | None]]:
    """Collapse a kind's reference rows to ``(entries, when_by_id)`` for rendering.

    :func:`~charter.progressive_disclosure.link_references` may emit more than one
    row for the same target id (one per ``(id, relation)`` — e.g. an artefact
    reached both by a ``requires`` and a ``suggests`` edge). For a link section we
    render each id once, preferring the first non-empty ``when`` so an authored
    ``suggests`` applicability wins over a ``requires`` row's absent one. Ordering
    is the deterministic order :func:`link_references` already produced.
    """
    entries: list[tuple[str, str]] = []
    when_by_id: dict[str, str | None] = {}
    seen: set[str] = set()
    for ref in references:
        artifact_id = ref["id"] or ""
        if artifact_id not in delivered_ids:
            continue
        if artifact_id not in seen:
            seen.add(artifact_id)
            entries.append((artifact_id, ref["reason"] or ""))
        if not when_by_id.get(artifact_id):
            when_by_id[artifact_id] = ref["when"]
    return entries, when_by_id


def render_profile_suggested_doctrine(
    profile: AgentProfile, service: object
) -> list[str]:
    """Render the profile channel's ``suggests``-delivered doctrine (WP01, C2–C5).

    The profile channel now follows ``suggests`` edges
    (``PROFILE_CHANNEL_RELATIONS``), so a loaded profile reaches the #3063 A–E
    families (Family A: ``paradigm:domain-driven-design``; Family B: the
    ``refactoring-*`` tactics; …). This renderer surfaces each reached-by-suggests
    artefact as a ``when``-labelled **link** (the canonical fetch stanza), never an
    inlined body (NFR-003) — the ``when`` is the reaching edge's own clause
    (``STATED_DEFAULT_WHEN`` when the edge is ``when``-less), projected by
    :func:`~charter.progressive_disclosure.profile_channel_references`.

    Requires-precedence (C3/A4) is handled inside that projection: an artefact in
    the seed's ``requires``-closure delivers eager and is excluded here, so a
    diamond never double-delivers.

    Fail-closed (like :func:`render_profile_procedures`): an absent/empty channel
    contributes no section rather than falling open to the whole graph.
    """
    repo = getattr(service, "agent_profiles", None)
    if repo is None:
        return []
    try:
        reached = repo.profile_channel_reached(profile.profile_id)
    except Exception:  # noqa: BLE001 — best-effort channel lookup
        return []
    delivered = {u for u in reached if _kind_of(u) in _PROFILE_SUGGESTS_DELIVERED_KINDS}
    if not delivered:
        return []

    seeds = {f"{NodeKind.AGENT_PROFILE.value}{_URN_SEP}{profile.profile_id}"}
    references = profile_channel_references(repo.drg, seeds, reached, delivered)

    lines: list[str] = []
    for kind, repo_attr, title in _SUGGESTS_KIND_RENDER:
        delivered_ids = {_bare_id(u) for u in delivered if _kind_of(u) == kind}
        if not delivered_ids:
            continue
        entries, when_by_id = _consolidate_kind_entries(references, delivered_ids)
        if not entries:
            continue
        lines.extend(
            render_profile_selector_refs(
                header=_PROFILE_SUGGESTED_HEADER_TPL.format(
                    title=title, profile_id=profile.profile_id
                ),
                entries=entries,
                repo=getattr(service, repo_attr, None),
                selector_kind=kind,
                profile_id=profile.profile_id,
                when_clause=STATED_DEFAULT_WHEN,
                body_fn=None,
                when_by_id=when_by_id,
            )
        )
    return lines
