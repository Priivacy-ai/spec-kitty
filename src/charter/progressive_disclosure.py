"""Progressive disclosure of doctrine context (WP15, ADR 2026-07-28-1).

Complete delivery made *affordable*: everything reachable is either delivered
inline (``requires`` — eager) or **named with the guidance that says when to
fetch it** (``suggests`` — a link carrying ``when``). Never silently absent.

This is the **default cadence**, not an opt-in mode. A link is not a truncation
(NFR-003): the artefact stays named and addressable, which is the property the
carrying mission exists to protect. Completeness is satisfied by the **union of
inlined and linked ids** equalling the delivered set — there is no cap on that
union.

The functions here are pure over a resolved :class:`~doctrine.drg.models.DRGGraph`
so the delivery cadence is testable without loading the whole doctrine tree, and
so ``charter.context`` does not grow to carry them (context.py is single-owned by
WP10 and held near-flat).
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from doctrine.drg.models import Relation

if TYPE_CHECKING:
    from doctrine.drg.models import DRGEdge, DRGGraph

#: The stated default rendered for an *uncovered* ``suggests`` edge — one of the
#: 118 (of 337) that carry no authored ``when`` (ADR 2026-07-28-1). A link with
#: this text is still a link: the artefact is named and fetchable. The default
#: makes the authoring gap **visible**, never blank (T081) — an empty string
#: would read as "no guidance intended" rather than "guidance not yet written".
STATED_DEFAULT_WHEN: str = (
    "Fetch when this artefact's guidance applies to the work at hand "
    "(no specific trigger authored yet)."
)

#: Delivery cadence markers attached to each delivered artefact DTO (T082).
DELIVERY_INLINE: str = "inline"
DELIVERY_LINK: str = "link"


def bare_id(urn: str) -> str:
    """Return the artefact id from a DRG URN (``directive:DIRECTIVE_010`` -> ``DIRECTIVE_010``).

    The delivered arrays key on the bare id, so references key on it too — that
    is what makes the union-of-ids completeness check (T084) well defined.
    """
    return urn.split(":", 1)[1] if ":" in urn else urn


def edge_to_reference(edge: DRGEdge) -> dict[str, str | None]:
    """Project one DRG edge into a ``{id, relation, when, reason}`` reference (T081).

    ``relation``/``reason`` are the edge's own fields, unmodified. ``when`` is the
    edge's own field for a covered ``suggests`` edge; an *uncovered* ``suggests``
    edge renders :data:`STATED_DEFAULT_WHEN` rather than an empty string so the
    authoring gap stays visible.
    """
    when = edge.when
    if not when and edge.relation is Relation.SUGGESTS:
        when = STATED_DEFAULT_WHEN
    return {
        "id": bare_id(edge.target),
        "relation": edge.relation.value,
        "when": when,
        "reason": edge.reason,
    }


def outbound_references(merged: DRGGraph, urn: str) -> list[dict[str, str | None]]:
    """Every outbound edge of *urn* as a reference entry (the DTO's ``references[]``)."""
    return [edge_to_reference(edge) for edge in merged.edges_from(urn)]


def requires_closure(merged: DRGGraph, roots: Iterable[str]) -> set[str]:
    """Transitive closure of *roots* over ``requires`` edges only (the eager set).

    ``requires`` is unconditional — a required artefact is delivered inline with
    no ``when`` to evaluate (ADR: cadence follows the relation, C-011).
    """
    seen: set[str] = set(roots)
    stack: list[str] = list(seen)
    while stack:
        node = stack.pop()
        for edge in merged.edges_from(node, Relation.REQUIRES):
            if edge.target not in seen:
                seen.add(edge.target)
                stack.append(edge.target)
    return seen


def partition_delivery(
    merged: DRGGraph,
    roots: Iterable[str],
    delivered_urns: Iterable[str],
) -> tuple[set[str], set[str]]:
    """Split the delivered set into ``(inline_urns, link_urns)`` by cadence (T082).

    ``inline`` = the ``requires`` closure of *roots* intersected with the
    delivered set (eager). ``link`` = everything else delivered (the
    ``suggests``-reached artefacts, emitted as links). The union is the whole
    delivered set — nothing is dropped.
    """
    delivered = set(delivered_urns)
    inline = requires_closure(merged, roots) & delivered
    return inline, delivered - inline


def link_references(
    merged: DRGGraph,
    roots: Iterable[str],
    delivered_urns: Iterable[str],
) -> list[dict[str, str | None]]:
    """The complete link set naming every delivered artefact (completeness, T084).

    Emits one reference per ``(target-id, relation)`` for every edge whose source
    is a root **or** a delivered artefact and whose target is delivered. Computed
    over ``roots ∪ delivered`` — not only the inline DTOs — so a ``suggests``
    chain (``root ~> a ~> b ~> c`` where ``b`` is itself only linked) still names
    its deep members: every delivered artefact has an inbound edge from within
    ``roots ∪ delivered`` by construction of the reachable closure, so it is named
    here. This is the "completeness by naming" guarantee: the union of inlined and
    referenced ids equals the delivered set, with no cap.
    """
    delivered = set(delivered_urns)
    sources = set(roots) | delivered
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, str | None]] = []
    for source in sorted(sources):
        for edge in merged.edges_from(source):
            if edge.target not in delivered:
                continue
            key = (bare_id(edge.target), edge.relation.value)
            if key in seen:
                continue
            seen.add(key)
            out.append(edge_to_reference(edge))
    return out


def artifact_to_dict(artifact: object, source: str) -> dict[str, object]:
    """Render one doctrine artefact as a JSON DTO (id + provenance + best-effort fields).

    Relocated verbatim from ``charter.context`` (single-owner, no-net-growth) so
    the DTO shape and its progressive-disclosure decoration live together.
    """
    item_id = getattr(artifact, "id", None)
    title = getattr(artifact, "title", None) or getattr(artifact, "name", None)
    summary = getattr(artifact, "intent", None) or getattr(artifact, "purpose", None)
    out: dict[str, object] = {
        "id": item_id if isinstance(item_id, str) else "",
        "source": source if source in {"builtin", "org", "project"} else "builtin",
    }
    if isinstance(title, str) and title:
        out["title"] = title
    if isinstance(summary, str) and summary:
        out["summary"] = summary
    return out


def reconstruct_urns(ids_by_kind: dict[str, Iterable[str]]) -> tuple[str, ...]:
    """Rebuild DRG URNs from a ``{kind: [id, ...]}`` mapping (delivered-set input)."""
    return tuple(
        f"{kind}:{artifact_id}"
        for kind, ids in ids_by_kind.items()
        for artifact_id in ids
    )


def _decorate_entry(
    entry: dict[str, object],
    *,
    kind: str,
    artifact: object,
    merged: DRGGraph | None,
    inline_urns: frozenset[str],
    include_all: bool,
    body_of: Callable[[object], object] | None,
) -> None:
    """Attach ``references``, ``delivery`` and (for inline) ``body`` to a DTO in place.

    A ``None`` graph means the DRG could not be resolved on this path; the entry
    is left undecorated (plain provenance DTO) rather than carrying an empty,
    misleading cadence — the non-action ``all_directives`` list flows through
    here with no graph and must stay a plain list.
    """
    if merged is None:
        return
    urn = f"{kind}:{entry.get('id', '')}"
    entry["references"] = outbound_references(merged, urn)
    is_inline = include_all or urn in inline_urns
    entry["delivery"] = DELIVERY_INLINE if is_inline else DELIVERY_LINK
    if is_inline and artifact is not None and body_of is not None:
        body = body_of(artifact)
        if body:
            entry["body"] = body


def collect_typed_artifacts(
    repository: object,
    artifact_ids: list[str],
    *,
    kind: str,
    merged: DRGGraph | None = None,
    inline_urns: frozenset[str] = frozenset(),
    include_all: bool = False,
    body_of: Callable[[object], object] | None = None,
) -> list[dict[str, object]]:
    """Look up *artifact_ids* in *repository*, emit DTOs decorated for progressive disclosure.

    Each entry carries provenance (relocated from ``charter.context``) plus the
    WP15 additions: ``references[]`` (T081), a ``delivery`` marker (T082), and,
    for inline artefacts, a ``body`` when *body_of* is supplied. Under
    *include_all* every artefact is delivered inline — a strict superset of the
    progressive render for the same grain (T083).
    """
    entries: list[dict[str, object]] = []
    for artifact_id in artifact_ids:
        try:
            artifact = repository.get(artifact_id)  # type: ignore[attr-defined]
            source = repository.get_provenance(artifact_id) or "builtin"  # type: ignore[attr-defined]
        except (AttributeError, KeyError):
            artifact, source = None, "builtin"
        entry = (
            {"id": artifact_id, "source": source}
            if artifact is None
            else artifact_to_dict(artifact, source)
        )
        _decorate_entry(
            entry,
            kind=kind,
            artifact=artifact,
            merged=merged,
            inline_urns=inline_urns,
            include_all=include_all,
            body_of=body_of,
        )
        entries.append(entry)
    return entries


#: Action-scoped JSON payload array name for each delivered kind.
_ARRAY_BY_KIND: dict[str, str] = {
    "directive": "directives",
    "tactic": "tactics",
    "styleguide": "styleguides",
    "toolguide": "toolguides",
}


def build_disclosure_payload(
    *,
    repos_by_kind: dict[str, tuple[object, list[str]]],
    extra_delivered: dict[str, list[str]],
    merged: DRGGraph | None,
    roots: Iterable[str],
    include_all: bool,
    body_of: Callable[[object], object] | None,
) -> dict[str, object]:
    """Render the progressive-disclosure slice of the JSON payload (WP15).

    Returns the four typed artefact arrays — each entry decorated with
    ``references[]`` and a ``delivery`` cadence marker — plus the top-level
    ``references`` link set that names every delivered artefact (including the
    ``procedure``/``asset`` kinds in *extra_delivered*, which are delivered but
    not surfaced as their own arrays). Kept here so ``charter.context`` stays
    flat (single-owner, no-net-growth) while owning only the call.
    """
    inline_urns = (
        frozenset(requires_closure(merged, roots)) if merged is not None else frozenset()
    )
    out: dict[str, object] = {}
    delivered: dict[str, Iterable[str]] = {}
    for kind, (repository, ids) in repos_by_kind.items():
        out[_ARRAY_BY_KIND[kind]] = collect_typed_artifacts(
            repository,
            list(ids),
            kind=kind,
            merged=merged,
            inline_urns=inline_urns,
            include_all=include_all,
            body_of=body_of,
        )
        delivered[kind] = ids
    delivered.update(extra_delivered)
    out["references"] = (
        link_references(merged, roots, reconstruct_urns(delivered))
        if merged is not None
        else []
    )
    return out


__all__ = [
    "DELIVERY_INLINE",
    "DELIVERY_LINK",
    "STATED_DEFAULT_WHEN",
    "artifact_to_dict",
    "build_disclosure_payload",
    "bare_id",
    "collect_typed_artifacts",
    "edge_to_reference",
    "link_references",
    "outbound_references",
    "partition_delivery",
    "reconstruct_urns",
    "requires_closure",
]
