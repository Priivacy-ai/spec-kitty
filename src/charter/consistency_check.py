"""Charter pack consistency check — validates activated artifact IDs (FR-011)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ruamel.yaml import YAML

from charter.catalog import resolve_doctrine_root
from charter.invocation_context import ProjectContext
from charter.kind_vocabulary import (
    ArtifactKind,
    MissionTypeNotAnArtifactKind,
    UnknownArtifactIdError,
    resolve_artifact_urn,
)
from charter.pack_manager import YAML_KEY_MAP, CharterPackManager

__all__ = [
    "ConsistencyReport",
    "run_consistency_check",
]


# Internal-only (not exported): raised and caught within this module to route a
# corrupt/unreadable references.yaml into the fail-closed verification_errors
# path. Kept out of __all__ per the symbol-level dead-code gate — no external
# caller imports it (the fail-closed tests trigger it via corrupt input).
class ReferencesCorruptError(RuntimeError):
    """``references.yaml`` exists but is unreadable or structurally invalid (#2530).

    Raised by :func:`_load_reference_ids_by_kind` when the compiled reference
    set is present on disk but cannot be trusted -- unparseable YAML, a
    non-mapping document root, or a missing/malformed ``references`` list.
    Deliberately distinct from the ``None`` return of that same function,
    which signals the legitimate "no charter synthesis has run yet" no-op
    skip. Callers must fail closed on this exception (surface a
    ``ConsistencyReport.verification_errors`` entry and treat the report as
    NOT coherent), never treat it the same as the ``None``/skip case --
    an empty finding list must mean "verified coherent", never "could not
    verify".
    """

# ---------------------------------------------------------------------------
# DRG source kinds: these carry edges to other kinds in the DRG (Pattern A).
# ---------------------------------------------------------------------------
_DRG_SOURCE_KINDS: frozenset[str] = frozenset(
    {"directive", "tactic", "styleguide", "toolguide"}
)

# ---------------------------------------------------------------------------
# Map from CLI kind names (in YAML_KEY_MAP) to DRG URN singular kind prefixes.
# Not all CLI kinds have a DRG representation; absent entries are skipped in
# DRG traversal.
# ---------------------------------------------------------------------------
_CLI_KIND_TO_DRG_SINGULAR: dict[str, str] = {
    "directive": "directive",
    "tactic": "tactic",
    "styleguide": "styleguide",
    "toolguide": "toolguide",
    "paradigm": "paradigm",
    "procedure": "procedure",
    "agent-profile": "agent_profile",
    "mission-step-contract": "mission_step_contract",
    # "mission-type" has no DRG singular; omitted intentionally.
}

# Inverse: DRG singular → CLI kind (for DRG edge traversal lookups).
_DRG_SINGULAR_TO_CLI_KIND: dict[str, str] = {
    v: k for k, v in _CLI_KIND_TO_DRG_SINGULAR.items()
}

# ---------------------------------------------------------------------------
# DRG singular kind -> ``PackContext.activated_kinds`` plural member (T018).
#
# Derived from YAML_KEY_MAP (``activated_<plural>`` minus the ``activated_``
# prefix) rather than importing ``charter.drg``'s private
# ``_SINGULAR_TO_PLURAL``. Deliberately used INSTEAD of
# ``charter.drg.filter_graph_by_activation`` for the KIND-level check: that
# helper's per-artifact-ID gate (``_node_is_activated`` Step 3) compares a
# DRG node's canonical id (e.g. ``DIRECTIVE_001``) against
# ``PackContext.activated_directives``, which holds config *stems* (e.g.
# ``001-architectural-integrity-standard``) -- the exact stem<->canonical-id
# mismatch this mission's ID-reconciliation is scoped to leave punted. Using
# it here would make the KIND-level check spuriously fail for every kind
# whose stem differs from its canonical id (directives), which is a
# pre-existing defect in a file this WP does not own, not a real config<->
# graph divergence. This module therefore reproduces only the KIND-level
# gate (``activated_kinds`` membership), never the per-ID gate.
# ---------------------------------------------------------------------------
_DRG_SINGULAR_TO_ACTIVATED_KINDS_MEMBER: dict[str, str] = {
    drg_singular: YAML_KEY_MAP[cli_kind].removeprefix("activated_")
    for cli_kind, drg_singular in _CLI_KIND_TO_DRG_SINGULAR.items()
}


# ---------------------------------------------------------------------------
# ConsistencyReport
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConsistencyReport:
    """Result of a consistency check against activated doctrine artifacts.

    Attributes:
        coherent: True when no unknown references, missing cross-references,
            kind violations, duplicates, config<->derived parity
            divergences, or verification failures were found.
        unknown_references: IDs activated for a kind that do not exist in doctrine.
        missing_from_doctrine: IDs referenced by DRG edges but absent from the
            target kind's activation set.
        kind_violations: IDs that appear in the wrong kind's activation set, or
            duplicate IDs within a single activation set.
        reference_id_divergences: FR-005/T017 -- ID-level parity findings
            between ``config.activated_*`` and the compiled reference set
            (``.kittify/charter/references.yaml``). Forward direction (every
            kind): a config-activated ID that does not resolve in the
            compiled reference set is the #2524 dangler class. Reverse
            direction (paradigms only -- the one kind rendered 1:1 with no
            DRG-transitive expansion): a compiled paradigm reference with no
            matching config activation.
        graph_kind_gaps: FR-005/T018 -- KIND-level parity findings between
            ``config.activated_*`` and the activation-filtered DRG graph. A
            kind with config-activated IDs but zero surviving graph nodes of
            that kind is a whole-kind dangler. Deliberately KIND-granular,
            not ID-granular (the config<->graph ID map is punted, see
            ``_check_drg_cross_kind_refs``).
        verification_errors: #2530 -- fail-closed signal distinct from every
            other (empty) finding list above. Populated when a parity check
            could not run at all because its input was unreadable or
            structurally invalid (a corrupt/truncated
            ``references.yaml``, or a DRG load/validation failure) -- as
            opposed to the legitimate "not yet synthesized" no-op skip (no
            ``references.yaml`` on disk yet). An empty finding list must
            mean "verified coherent", never "could not verify"; this field
            is how the guard reports the latter instead of silently
            reporting the former.
        suggestions: Human-readable resolution instructions for each finding.
    """

    coherent: bool
    unknown_references: list[str] = field(default_factory=list)
    missing_from_doctrine: list[str] = field(default_factory=list)
    kind_violations: list[str] = field(default_factory=list)
    reference_id_divergences: list[str] = field(default_factory=list)
    graph_kind_gaps: list[str] = field(default_factory=list)
    verification_errors: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        """Serialise to a JSON string (FR-011 JSON output surface)."""
        return json.dumps(
            {
                "coherent": self.coherent,
                "unknown_references": self.unknown_references,
                "missing_from_doctrine": self.missing_from_doctrine,
                "kind_violations": self.kind_violations,
                "reference_id_divergences": self.reference_id_divergences,
                "graph_kind_gaps": self.graph_kind_gaps,
                "verification_errors": self.verification_errors,
                "suggestions": self.suggestions,
            },
            indent=2,
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _get_activation_set(
    activated_by_kind: dict[str, frozenset[str] | None],
    kind: str,
) -> frozenset[str] | None:
    """Return the activated ID set for *kind*, or None when absent.

    ``None`` means no explicit activation in config.yaml — backward-compat.
    """
    return activated_by_kind.get(kind)


def _get_raw_activation_list(
    raw_activated_by_kind: dict[str, list[str] | None],
    kind: str,
) -> list[str] | None:
    """Return the raw list of IDs for *kind*, or None when absent.

    The consistency check needs the un-deduplicated YAML list so duplicate
    activation entries remain observable.
    """
    return raw_activated_by_kind.get(kind)


def _load_raw_activation_lists(ctx: ProjectContext) -> dict[str, list[str] | None]:
    """Read activation lists from config.yaml without deduplicating entries."""
    config_path = ctx.require_repo_root() / ".kittify" / "config.yaml"
    if not config_path.exists():
        return dict.fromkeys(YAML_KEY_MAP, None)

    yaml = YAML(typ="safe")
    data = yaml.load(config_path) or {}
    if not isinstance(data, dict):
        return dict.fromkeys(YAML_KEY_MAP, None)

    result: dict[str, list[str] | None] = {}
    for kind, yaml_key in YAML_KEY_MAP.items():
        raw = data.get(yaml_key)
        if raw is None:
            result[kind] = None
        elif isinstance(raw, list):
            result[kind] = [str(item) for item in raw]
        else:
            result[kind] = []
    return result


def _collect_all_doctrine_ids(
    ctx: ProjectContext,
    manager: CharterPackManager,
) -> dict[str, frozenset[str]]:
    """Return a mapping of CLI kind → frozenset of doctrine IDs (loaded once).

    Invalid/missing doctrine dirs return an empty frozenset per kind.
    """
    all_ids: dict[str, frozenset[str]] = {}
    for kind in YAML_KEY_MAP:
        try:
            all_ids[kind] = manager.list_available(ctx, kind)
        except ValueError:
            all_ids[kind] = frozenset()
    return all_ids


def _has_explicit_activation(raw_activated_by_kind: dict[str, list[str] | None]) -> bool:
    """Return True when config.yaml contains at least one activation key."""
    return any(raw is not None for raw in raw_activated_by_kind.values())


def _split_urn(urn: str) -> tuple[str, str]:
    """Split ``"<kind>:<id>"`` into ``(kind, id)``.

    Returns ``(urn, "")`` when the URN has no colon.
    """
    head, _sep, tail = urn.partition(":")
    return (head, tail)


def _check_unknown_references(
    activated_by_kind: dict[str, frozenset[str] | None],
    all_doctrine_ids: dict[str, frozenset[str]],
    unknown_references: list[str],
    suggestions: list[str],
) -> None:
    """Populate *unknown_references* and *suggestions* for unknown IDs (FR-011)."""
    for kind in YAML_KEY_MAP:
        activated = _get_activation_set(activated_by_kind, kind)
        if activated is None:
            continue
        known_ids = all_doctrine_ids.get(kind, frozenset())
        for activated_id in sorted(activated):
            if activated_id not in known_ids:
                unknown_references.append(f"{kind}/{activated_id}")
                suggestions.append(
                    f"{kind}/{activated_id}: Not found in doctrine. "
                    f"Run 'charter deactivate {kind} {activated_id}' to remove."
                )


def _check_drg_cross_kind_refs(
    ctx: ProjectContext,
    activated_by_kind: dict[str, frozenset[str] | None],
    missing_from_doctrine: list[str],
    suggestions: list[str],
) -> None:
    """Populate *missing_from_doctrine* for cross-kind DRG edge gaps (FR-012).

    Background: The DRG uses numeric URN IDs (e.g. ``directive:DIRECTIVE_001``)
    while config.yaml uses human-readable IDs (e.g.
    ``001-architectural-integrity-standard``). There is currently no
    canonical mapping between the two ID systems. The cross-kind check
    therefore operates at the KIND level: if a source artifact of an
    activated kind has a DRG edge to a target kind, and that target kind's
    activation set is explicitly set to empty (``[]``), the reference is
    unresolvable and the target kind is flagged as missing.

    ``None`` activation means backward-compat (all active) — no finding.
    A non-empty activation set satisfies the check regardless of specific IDs.
    """
    try:
        from charter._drg_helpers import load_validated_graph  # noqa: PLC0415
        from charter.drg import filter_graph_by_activation  # noqa: PLC0415

        repo_root = ctx.require_repo_root()
        pack_context = ctx.require_pack_context()
        full_drg = load_validated_graph(repo_root)
        activated_drg = filter_graph_by_activation(full_drg, pack_context)

        reported_kind_pairs: set[tuple[str, str]] = set()
        for edge in activated_drg.edges:
            _inspect_drg_edge(
                edge,
                activated_by_kind,
                missing_from_doctrine,
                suggestions,
                reported_kind_pairs,
            )
    except Exception:  # noqa: BLE001
        # DRG load is best-effort; failures are surfaced by other tooling.
        pass


def _inspect_drg_edge(
    edge: object,
    activated_by_kind: dict[str, frozenset[str] | None],
    missing_from_doctrine: list[str],
    suggestions: list[str],
    reported_kind_pairs: set[tuple[str, str]],
) -> None:
    """Check one DRG edge for cross-kind activation gaps."""
    src_singular, _src_id = _split_urn(getattr(edge, "source", ""))
    tgt_singular, _tgt_id = _split_urn(getattr(edge, "target", ""))

    if src_singular not in _DRG_SOURCE_KINDS:
        return
    if src_singular == tgt_singular:
        # Same-kind edge: ID systems don't align; skip.
        return

    tgt_cli_kind = _DRG_SINGULAR_TO_CLI_KIND.get(tgt_singular)
    if tgt_cli_kind is None:
        return

    target_activated = _get_activation_set(activated_by_kind, tgt_cli_kind)
    if target_activated is None or len(target_activated) > 0:
        # None = backward-compat (all active); non-empty = satisfied.
        return

    src_cli_kind = _DRG_SINGULAR_TO_CLI_KIND.get(src_singular, src_singular)
    pair_key = (src_cli_kind, tgt_cli_kind)
    if pair_key in reported_kind_pairs:
        return
    reported_kind_pairs.add(pair_key)

    entry = f"{tgt_cli_kind}/<all>"
    if entry not in missing_from_doctrine:
        missing_from_doctrine.append(entry)
        suggestions.append(
            f"{tgt_cli_kind}/<all>: Kind '{tgt_cli_kind}' is referenced by "
            f"activated '{src_cli_kind}' artifacts via DRG edges but its "
            f"activation set is empty. "
            f"Run 'charter activate {tgt_cli_kind} <id>' "
            f"or add --cascade when activating the source."
        )


def _check_duplicates(
    raw_activated_by_kind: dict[str, list[str] | None],
    kind_violations: list[str],
) -> None:
    """Detect duplicate IDs within a single activation set."""
    for kind in YAML_KEY_MAP:
        raw_list = _get_raw_activation_list(raw_activated_by_kind, kind)
        if raw_list is None:
            continue
        seen: set[str] = set()
        for item in raw_list:
            if item in seen:
                kind_violations.append(
                    f"{kind}/{item}: Duplicate entry in activation set."
                )
            seen.add(item)


def _check_kind_violations(
    activated_by_kind: dict[str, frozenset[str] | None],
    all_doctrine_ids: dict[str, frozenset[str]],
    unknown_references: list[str],
    kind_violations: list[str],
) -> None:
    """Detect IDs that belong to the wrong kind's activation set."""
    for kind in YAML_KEY_MAP:
        activated = _get_activation_set(activated_by_kind, kind)
        if activated is None:
            continue
        own_ids = all_doctrine_ids.get(kind, frozenset())
        for artifact_id in sorted(activated):
            if f"{kind}/{artifact_id}" in unknown_references:
                continue  # Already flagged; avoid double-reporting.
            if artifact_id in own_ids:
                continue  # Correct kind.
            for other_kind, other_ids in all_doctrine_ids.items():
                if other_kind == kind:
                    continue
                if artifact_id in other_ids:
                    kind_violations.append(
                        f"{kind}/{artifact_id}: ID belongs to kind "
                        f"'{other_kind}', not '{kind}'."
                    )
                    break  # Report once per misplaced ID.


def _load_reference_ids_by_kind(ctx: ProjectContext) -> dict[str, frozenset[str]] | None:
    """Parse ``.kittify/charter/references.yaml``, grouped by kind.

    Returns ``None`` only when the compiled reference set has not been
    materialised yet (no ``references.yaml`` on disk) -- a legitimate no-op
    skip (T017 has nothing to check against), NOT a corruption signal.

    Raises:
        ReferencesCorruptError: ``references.yaml`` exists but cannot be
            trusted -- unparseable YAML, a non-mapping document root, or a
            missing/malformed ``references`` list (#2530). Fail-closed: a
            guard that cannot read its own input must never report a silent
            pass by treating "corrupt" the same as "not yet synthesized".
    """
    references_path = ctx.require_repo_root() / ".kittify" / "charter" / "references.yaml"
    if not references_path.exists():
        return None

    yaml = YAML(typ="safe")
    try:
        data = yaml.load(references_path)
    except Exception as exc:  # noqa: BLE001 -- re-raised as a typed, fail-closed signal below.
        raise ReferencesCorruptError(
            f"{references_path} could not be parsed: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ReferencesCorruptError(
            f"{references_path} does not contain a YAML mapping at its document root."
        )

    entries = data.get("references")
    if not isinstance(entries, list):
        raise ReferencesCorruptError(
            f"{references_path} is missing a valid 'references' list."
        )

    by_kind: dict[str, set[str]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        kind = entry.get("kind")
        ref_id = entry.get("id")
        if not isinstance(kind, str) or not isinstance(ref_id, str):
            continue
        _, _, bare_id = ref_id.partition(":")
        by_kind.setdefault(kind, set()).add(bare_id)
    return {kind: frozenset(ids) for kind, ids in by_kind.items()}


def _check_reference_id_parity(
    ctx: ProjectContext,
    raw_activated_by_kind: dict[str, list[str] | None],
    reference_id_divergences: list[str],
    verification_errors: list[str],
    suggestions: list[str],
) -> None:
    """FR-005/T017: config.activated_* <-> references.yaml, at ID level.

    Forward direction (every kind): every explicitly-activated config stem
    MUST resolve to a canonical id in the compiled reference set, using the
    same ``resolve_artifact_urn`` canonicalization ``compiler.py`` itself
    uses to build ``references.yaml``. A config-activated stem that does not
    resolve is the exact #2524 dangler class (an artefact live in config but
    missing from the derived output).

    Reverse direction (paradigms only): paradigms are rendered 1:1 from
    ``config.activated_paradigms`` with no DRG-transitive expansion
    (``compiler._build_references_from_service`` -- "Selection-only ...
    never DRG-reachable"), so a paradigm resolving in references.yaml with
    no matching config activation is unambiguously stale. The reverse check
    is deliberately NOT extended to directive/tactic/styleguide/toolguide/
    procedure/agent-profile: those kinds are DRG-transitively expanded (a
    directive can pull in a tactic via a ``requires`` edge with no direct
    ``config.activated_tactics`` entry), so "extra" entries there are
    expected, not a divergence -- flagging them would be a false-positive
    machine, not a regression guard.

    Org/project overlay resolution (#2529): ``resolve_artifact_urn`` must be
    given the SAME ``org_roots`` that ``compiler.py``'s equivalent resolver
    call threads through (``list(pack_context.pack_roots[1:])`` --
    ``pack_roots`` is ``(builtin_root, *org_pack_roots)``, so slicing off
    index 0 leaves only the configured org/project overlay roots; empty for
    a project with no org packs, so behaviour is unchanged there). Without
    this, a config-activated ORG-only artefact raises
    ``UnknownArtifactIdError`` here, is swallowed by the ``except`` below,
    and the guard silently skips it -- while the compiler's un-caught
    resolver call crashes on the exact same stem. That is a false negative,
    not a best-effort skip.

    Fail-closed on corrupt input (#2530): a ``references.yaml`` that exists
    but cannot be parsed/trusted raises :class:`ReferencesCorruptError` from
    :func:`_load_reference_ids_by_kind`; that is caught here and surfaced as
    a *verification_errors* entry (not silently treated as "nothing to
    check against", which is reserved for the file genuinely not existing
    yet).

    Campsite note (#2759/T010): the forward and reverse directions are
    pre-extracted into :func:`_check_reference_id_forward_parity` and
    :func:`_check_reference_id_reverse_parity` so this orchestrator stays
    well under the complexity ceiling once
    ``specify_cli.charter_runtime.freshness.computer`` gains a read-path
    consumer of this whole check (WP03) -- pure refactor, no behavior change.
    """
    try:
        references_by_kind = _load_reference_ids_by_kind(ctx)
    except ReferencesCorruptError as exc:
        verification_errors.append(f"references.yaml: {exc}")
        suggestions.append(
            f"references.yaml: Could not verify config<->references parity "
            f"({exc}). Run 'spec-kitty charter synthesize' (or "
            f"resynthesize) to regenerate .kittify/charter/references.yaml, "
            f"or restore it from version control."
        )
        return
    if references_by_kind is None:
        return  # No compiled reference set yet -- nothing to check against.

    doctrine_root = resolve_doctrine_root()
    pack_context = ctx.require_pack_context()
    org_roots = list(pack_context.pack_roots[1:])

    _check_reference_id_forward_parity(
        raw_activated_by_kind,
        references_by_kind,
        doctrine_root=doctrine_root,
        org_roots=org_roots,
        reference_id_divergences=reference_id_divergences,
        suggestions=suggestions,
    )
    _check_reference_id_reverse_parity(
        raw_activated_by_kind,
        references_by_kind,
        reference_id_divergences=reference_id_divergences,
        suggestions=suggestions,
    )


def _check_reference_id_forward_parity(
    raw_activated_by_kind: dict[str, list[str] | None],
    references_by_kind: dict[str, frozenset[str]],
    *,
    doctrine_root: Path,
    org_roots: list[Path],
    reference_id_divergences: list[str],
    suggestions: list[str],
) -> None:
    """Forward direction (every kind): config.activated_* -> references.yaml.

    Every explicitly-activated config stem MUST resolve to a canonical id in
    the compiled reference set (the #2524 dangler class). See
    :func:`_check_reference_id_parity` for the full contract.
    """
    for cli_kind in YAML_KEY_MAP:
        try:
            kind_enum = ArtifactKind.from_operator_token(cli_kind)
        except MissionTypeNotAnArtifactKind:
            continue  # "mission-type" has no ArtifactKind / DRG representation.

        raw_list = raw_activated_by_kind.get(cli_kind)
        if not raw_list:
            continue  # None (backward-compat all-active) or [] (nothing activated).

        known_ref_ids = references_by_kind.get(kind_enum.value, frozenset())
        for stem in sorted(set(raw_list)):
            try:
                urn = resolve_artifact_urn(
                    kind_enum, stem, doctrine_root=doctrine_root, org_roots=org_roots
                )
            except UnknownArtifactIdError:
                continue  # Already reported by _check_unknown_references.
            _, _, canonical_id = urn.partition(":")
            if canonical_id not in known_ref_ids:
                reference_id_divergences.append(f"{cli_kind}/{stem}")
                suggestions.append(
                    f"{cli_kind}/{stem}: Activated in config.yaml but does not "
                    f"resolve in .kittify/charter/references.yaml. Run "
                    f"'spec-kitty charter synthesize' (or resynthesize) to "
                    f"regenerate the compiled reference set."
                )


def _check_reference_id_reverse_parity(
    raw_activated_by_kind: dict[str, list[str] | None],
    references_by_kind: dict[str, frozenset[str]],
    *,
    reference_id_divergences: list[str],
    suggestions: list[str],
) -> None:
    """Reverse direction (paradigms only): references.yaml -> config.activated_paradigms.

    Paradigms are rendered 1:1 with no DRG-transitive expansion, so a
    compiled paradigm reference with no matching config activation is
    unambiguously stale. See :func:`_check_reference_id_parity` for why this
    is scoped to paradigms only.
    """
    paradigm_list = raw_activated_by_kind.get("paradigm")
    if paradigm_list is None:
        return
    known_paradigm_stems = frozenset(paradigm_list)
    for ref_id in references_by_kind.get("paradigm", frozenset()):
        if ref_id not in known_paradigm_stems:
            reference_id_divergences.append(f"paradigm/{ref_id}")
            suggestions.append(
                f"paradigm/{ref_id}: Resolves in "
                f".kittify/charter/references.yaml but is not in "
                f"config.activated_paradigms. Run 'charter deactivate "
                f"paradigm {ref_id}' or reconcile config.yaml."
            )


def _check_graph_kind_parity(
    ctx: ProjectContext,
    raw_activated_by_kind: dict[str, list[str] | None],
    graph_kind_gaps: list[str],
    verification_errors: list[str],
    suggestions: list[str],
) -> None:
    """FR-005/T018: config.activated_* <-> DRG graph, at KIND level only.

    Deliberately KIND-granular, not ID-granular: ``_check_drg_cross_kind_refs``
    already documents that there is no canonical config-stem <-> DRG-URN-id
    mapping (the "punted" map at :func:`_check_drg_cross_kind_refs`) --
    building it here would grow an ID-reconciliation sub-project FR-005 does
    not ask for. Instead this checks a coarser, still non-vacuous property:
    when config explicitly activates one or more IDs for a DRG-representable
    kind, the activation-filtered DRG graph must contain at least one
    surviving node of that kind. A kind with config-activated IDs but zero
    surviving graph nodes is a whole-kind dangler -- the KIND-level shadow of
    the #2524 class.

    NOTE: this function deliberately does NOT import
    ``specify_cli.*freshness*`` (layer rule -- ``freshness/computer.py`` is a
    ``specify_cli`` module that imports ``charter``, so ``charter`` cannot
    import it back) and asserts a disjoint property from freshness (temporal
    staleness vs config<->derived set parity). It also deliberately does NOT
    use ``charter.drg.filter_graph_by_activation`` -- see the module-level
    ``_DRG_SINGULAR_TO_ACTIVATED_KINDS_MEMBER`` docstring for why that
    helper's per-ID gate is unsuitable for a KIND-level check.

    Fail-closed on DRG-load failure (#2530): the built-in DRG graph is
    always bundled with the package, so a failure loading/validating it
    (``load_validated_graph`` raises on ``assert_valid`` rejection) or
    resolving ``ctx``'s required fields is a genuine "could not verify"
    condition, never a legitimate "not yet synthesized" skip -- unlike
    ``references.yaml``, there is no not-yet-materialised state for the DRG.
    A failure here is therefore surfaced as a *verification_errors* entry
    instead of a silent early return.
    """
    try:
        from charter._drg_helpers import load_validated_graph  # noqa: PLC0415

        repo_root = ctx.require_repo_root()
        pack_context = ctx.require_pack_context()
        full_drg = load_validated_graph(repo_root)
    except Exception as exc:  # noqa: BLE001 -- fail-closed signal below, not a silent pass.
        verification_errors.append(
            f"drg: Could not verify config<->graph kind parity "
            f"({type(exc).__name__}: {exc})."
        )
        suggestions.append(
            f"drg: Could not verify config<->graph kind parity "
            f"({type(exc).__name__}: {exc}). Regenerate graph.yaml / run "
            f"'spec-kitty charter resynthesize' and retry."
        )
        return

    graph_kinds_present: set[str] = set()
    for node in full_drg.nodes:
        node_kind, _ = _split_urn(node.urn)
        activated_kinds_member = _DRG_SINGULAR_TO_ACTIVATED_KINDS_MEMBER.get(node_kind)
        if activated_kinds_member is not None and activated_kinds_member in pack_context.activated_kinds:
            graph_kinds_present.add(node_kind)

    for cli_kind, drg_singular in _CLI_KIND_TO_DRG_SINGULAR.items():
        raw_list = raw_activated_by_kind.get(cli_kind)
        if not raw_list:
            continue  # None (backward-compat all-active) or [] (nothing activated).
        if drg_singular in graph_kinds_present:
            continue
        graph_kind_gaps.append(cli_kind)
        suggestions.append(
            f"{cli_kind}: config.yaml activates {len(set(raw_list))} "
            f"{cli_kind} id(s) but none survive in the activation-filtered "
            f"DRG graph. Regenerate graph.yaml / run 'spec-kitty charter "
            f"resynthesize' and check 'activated_kinds' in config.yaml."
        )


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------


def run_consistency_check(ctx: ProjectContext) -> ConsistencyReport:
    """Run a full consistency check for the project's activated charter pack.

    Checks:
      - Unknown references (activated IDs absent from doctrine).
      - Cross-kind DRG edge references where the target kind is empty (FR-012).
      - Kind violations and duplicate IDs within activation sets.
      - Config<->references.yaml ID parity and config<->DRG kind parity
        (FR-005), fail-closed on unreadable/corrupt input (#2530) rather
        than silently reporting an empty, passing result.

    WP template scanning is explicitly out of scope.

    Args:
        ctx: The project context, used to resolve activation state and doctrine.

    Returns:
        A frozen ConsistencyReport with coherence flag and categorised findings.
    """
    unknown_references: list[str] = []
    missing_from_doctrine: list[str] = []
    kind_violations: list[str] = []
    reference_id_divergences: list[str] = []
    graph_kind_gaps: list[str] = []
    verification_errors: list[str] = []
    suggestions: list[str] = []

    manager = CharterPackManager()
    raw_activated_by_kind = _load_raw_activation_lists(ctx)
    activated_by_kind = {
        kind: None if raw is None else frozenset(raw)
        for kind, raw in raw_activated_by_kind.items()
    }

    if not _has_explicit_activation(raw_activated_by_kind):
        return ConsistencyReport(coherent=True)

    all_doctrine_ids = _collect_all_doctrine_ids(ctx, manager)

    _check_unknown_references(
        activated_by_kind, all_doctrine_ids, unknown_references, suggestions
    )
    _check_drg_cross_kind_refs(
        ctx, activated_by_kind, missing_from_doctrine, suggestions
    )
    _check_duplicates(raw_activated_by_kind, kind_violations)
    _check_kind_violations(
        activated_by_kind, all_doctrine_ids, unknown_references, kind_violations
    )
    _check_reference_id_parity(
        ctx,
        raw_activated_by_kind,
        reference_id_divergences,
        verification_errors,
        suggestions,
    )
    _check_graph_kind_parity(
        ctx, raw_activated_by_kind, graph_kind_gaps, verification_errors, suggestions
    )

    coherent = not (
        unknown_references
        or missing_from_doctrine
        or kind_violations
        or reference_id_divergences
        or graph_kind_gaps
        or verification_errors
    )
    return ConsistencyReport(
        coherent=coherent,
        unknown_references=unknown_references,
        missing_from_doctrine=missing_from_doctrine,
        kind_violations=kind_violations,
        reference_id_divergences=reference_id_divergences,
        graph_kind_gaps=graph_kind_gaps,
        verification_errors=verification_errors,
        suggestions=suggestions,
    )
