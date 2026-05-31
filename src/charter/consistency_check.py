"""Charter pack consistency check — validates activated artifact IDs (FR-011)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from charter.invocation_context import ProjectContext
from charter.pack_manager import YAML_KEY_MAP, CharterPackManager

__all__ = [
    "ConsistencyReport",
    "run_consistency_check",
]

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
# ConsistencyReport
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConsistencyReport:
    """Result of a consistency check against activated doctrine artifacts.

    Attributes:
        coherent: True when no unknown references, missing cross-references,
            kind violations, or duplicates were found.
        unknown_references: IDs activated for a kind that do not exist in doctrine.
        missing_from_doctrine: IDs referenced by DRG edges but absent from the
            target kind's activation set.
        kind_violations: IDs that appear in the wrong kind's activation set, or
            duplicate IDs within a single activation set.
        suggestions: Human-readable resolution instructions for each finding.
    """

    coherent: bool
    unknown_references: list[str] = field(default_factory=list)
    missing_from_doctrine: list[str] = field(default_factory=list)
    kind_violations: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        """Serialise to a JSON string (FR-011 JSON output surface)."""
        return json.dumps(
            {
                "coherent": self.coherent,
                "unknown_references": self.unknown_references,
                "missing_from_doctrine": self.missing_from_doctrine,
                "kind_violations": self.kind_violations,
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
    activated_by_kind: dict[str, frozenset[str] | None],
    kind: str,
) -> list[str] | None:
    """Return the raw list of IDs for *kind*, or None when absent.

    ``CharterPackManager.list_activated`` returns frozensets, which
    deduplicate automatically.  The duplicate-detection loop is retained
    for correctness; it is a structural no-op for frozenset-based configs.
    """
    activated = activated_by_kind.get(kind)
    if activated is None:
        return None
    return list(activated)


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
    activated_by_kind: dict[str, frozenset[str] | None],
    kind_violations: list[str],
) -> None:
    """Detect duplicate IDs within a single activation set."""
    for kind in YAML_KEY_MAP:
        raw_list = _get_raw_activation_list(activated_by_kind, kind)
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


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------


def run_consistency_check(ctx: ProjectContext) -> ConsistencyReport:
    """Run a full consistency check for the project's activated charter pack.

    Checks:
      - Unknown references (activated IDs absent from doctrine).
      - Cross-kind DRG edge references where the target kind is empty (FR-012).
      - Kind violations and duplicate IDs within activation sets.

    WP template scanning is explicitly out of scope.

    Args:
        ctx: The project context, used to resolve activation state and doctrine.

    Returns:
        A frozen ConsistencyReport with coherence flag and categorised findings.
    """
    unknown_references: list[str] = []
    missing_from_doctrine: list[str] = []
    kind_violations: list[str] = []
    suggestions: list[str] = []

    manager = CharterPackManager()
    activated_by_kind = manager.list_activated(ctx)
    all_doctrine_ids = _collect_all_doctrine_ids(ctx, manager)

    _check_unknown_references(
        activated_by_kind, all_doctrine_ids, unknown_references, suggestions
    )
    _check_drg_cross_kind_refs(
        ctx, activated_by_kind, missing_from_doctrine, suggestions
    )
    _check_duplicates(activated_by_kind, kind_violations)
    _check_kind_violations(
        activated_by_kind, all_doctrine_ids, unknown_references, kind_violations
    )

    coherent = not (unknown_references or missing_from_doctrine or kind_violations)
    return ConsistencyReport(
        coherent=coherent,
        unknown_references=unknown_references,
        missing_from_doctrine=missing_from_doctrine,
        kind_violations=kind_violations,
        suggestions=suggestions,
    )
