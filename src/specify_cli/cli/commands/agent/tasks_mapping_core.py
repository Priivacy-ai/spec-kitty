"""Pure requirement-mapping decision core for ``agent tasks map-requirements`` (WP04).

This module lifts ``map_requirements``' FR↔WP **mapping + new-ref validation +
coverage** decision out of the interleaved command body into ONE pure function,
:func:`plan_mapping`. It is a behaviour-preserving (pure-parity) extraction
(FR-005 / FR-002 / NFR-001): it reproduces the live command's exact current
behaviour — no unification, no "improvement".

Design (functional core / imperative shell):

* The orchestrator (``map_requirements``) performs all filesystem / git reads
  (spec.md parse, per-WP frontmatter, tasks.md fallback) and freezes the results
  in a :class:`MappingRequest`.
* :func:`plan_mapping` is **PURE** (INV-4) — no filesystem, git, status-emission,
  rendering, or clock access — and returns a :class:`MappingPlan`:
  - ``to_write`` — the per-WP merged ``requirement_refs`` the shell writes to
    frontmatter (empty in ``tracker_only`` mode — that mode touches only
    ``tracker_refs``, a shell concern).
  - ``offenders`` — the PRE-write new-ref validation buckets (``malformed`` from
    the format check, ``unknown_spec_id`` from the spec-membership check). The
    shell gates on these BEFORE the write loop, so a bad new ref refuses with NO
    write, exactly as the un-refactored command did.
  - ``unmapped_fr`` — the functional FRs left uncovered after the projected
    write, i.e. ``compute_coverage``'s ``unmapped_functional`` over
    ``{**existing_all_refs, **to_write}``.

**Write-timing note (parity-critical, FR-002 / NFR-001).** The core deliberately
does NOT reproduce the command's *post-write* stale-refs gate (the hard-fail that
re-reads EVERY WP's raw frontmatter AFTER the write loop). That gate stays in the
imperative shell at its ORIGINAL sequence position — AFTER the frontmatter write —
so a pre-existing stale ref on an untouched WP still refuses (exit 1) with the OLD
partial write already on disk. The core owns only the PRE-write decision; the
shell owns the write side effect and the post-write gate, preserving the exact
partial-write-on-refusal behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass

from specify_cli.requirement_mapping import (
    compute_coverage,
    validate_ref_format,
    validate_refs,
)

# Operator-facing mode token (data-model §MappingRequest) whose merge arm writes
# no ``requirement_refs`` — only ``tracker_refs`` (persisted by the shell).
TRACKER_ONLY_MODE = "tracker_only"


@dataclass(frozen=True)
class MappingRequest:
    """Every fact :func:`plan_mapping` needs — all resolved by the shell.

    The shell (``map_requirements``) performs the I/O (spec.md parse, per-WP
    frontmatter reads, tasks.md fallback parse) and freezes the results here so
    the decision is pure.
    """

    # Parsed spec requirement ids (``parse_requirement_ids_from_spec_md``):
    spec_all_ids: frozenset[str]
    spec_functional_ids: frozenset[str]
    # New mappings the operator supplied, per WP, already upper-cased by the shell
    # (mode-specific building — batch JSON parse / individual comma-split — stays
    # in the shell because its error arms raise ``typer.Exit``).
    new_mappings: dict[str, list[str]]
    # Existing normalized ``requirement_refs`` for ALL WPs (pre-write), the single
    # read that feeds BOTH the union-merge base AND the coverage projection.
    existing_all_refs: dict[str, list[str]]
    # tasks.md-parsed refs per WP — the union-merge fallback when frontmatter empty.
    tasks_md_refs: dict[str, list[str]]
    mode: str
    replace: bool


@dataclass(frozen=True)
class MappingOffenders:
    """PRE-write new-ref validation buckets (raw, undeduped — shell renders them).

    ``malformed`` violates the ``FR-NNN`` / ``NFR-NNN`` / ``C-NNN`` shape;
    ``unknown_spec_id`` is well-formed but not declared in ``spec.md``. Both are
    upper-cased in the input order the format/membership checks produced, so the
    shell reproduces the live command's rendering byte-for-byte (``malformed`` is
    printed as-is; ``unknown_spec_id`` is ``sorted(set(...))`` at the print site).
    """

    malformed: tuple[str, ...]
    unknown_spec_id: tuple[str, ...]


@dataclass(frozen=True)
class MappingPlan:
    """The pure mapping decision the shell applies (write) + reports."""

    to_write: dict[str, list[str]]
    offenders: MappingOffenders
    unmapped_fr: list[str]


def _merge_refs(
    *,
    new_refs: list[str],
    existing: list[str],
    tasks_md_fallback: list[str],
    replace: bool,
) -> list[str]:
    """Reproduce ``map_requirements``' per-WP merge (verbatim, FR-005).

    ``replace`` overwrites with just the new refs; otherwise the new refs union
    with the existing frontmatter refs, falling back to the tasks.md refs when the
    frontmatter carries none. The result is ``sorted(set(...))`` exactly as the
    live loop computed ``merged_refs``.
    """
    if replace:
        return sorted(set(new_refs))
    base = list(existing)
    if not base:
        base = list(tasks_md_fallback)
    return sorted(set(base) | set(new_refs))


def plan_mapping(req: MappingRequest) -> MappingPlan:
    """Decide the requirement mapping purely (FR-005 / FR-002 / NFR-001).

    Computes the PRE-write offender buckets over the supplied new refs, the per-WP
    merged ``to_write`` (skipped entirely in ``tracker_only`` mode), and the
    projected ``unmapped_fr`` coverage — with NO side effects (INV-4). The shell
    applies the write and runs the post-write stale gate at their original
    positions.
    """
    all_new_refs = [ref for refs in req.new_mappings.values() for ref in refs]
    _, malformed = validate_ref_format(all_new_refs)
    _, unknown = validate_refs(all_new_refs, set(req.spec_all_ids))
    offenders = MappingOffenders(
        malformed=tuple(malformed),
        unknown_spec_id=tuple(unknown),
    )

    to_write: dict[str, list[str]] = {}
    if req.mode != TRACKER_ONLY_MODE:
        for wp_id, new_refs in req.new_mappings.items():
            to_write[wp_id] = _merge_refs(
                new_refs=new_refs,
                existing=req.existing_all_refs.get(wp_id, []),
                tasks_md_fallback=req.tasks_md_refs.get(wp_id, []),
                replace=req.replace,
            )

    projected: dict[str, list[str]] = {**req.existing_all_refs, **to_write}
    coverage = compute_coverage(projected, set(req.spec_functional_ids))
    return MappingPlan(
        to_write=to_write,
        offenders=offenders,
        unmapped_fr=list(coverage["unmapped_functional"]),
    )
