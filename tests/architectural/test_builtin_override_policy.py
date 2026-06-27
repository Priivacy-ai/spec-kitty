"""Governance-as-test: built-in DRG overrides must be sanctioned by the repo.

The three-layer merge (:mod:`doctrine.drg.merge`) PERMITS a same-kind org node
to override a built-in node in place (recorded as a ``node_override`` conflict
with ``resolution_applied == "org_override"`` and a warning). The merge does
NOT decide whether *this* repo sanctions a given override — that is a per-repo
governance decision expressed in ``.kittify/doctrine/replaceable-builtins.yaml``.

This architectural test loads the repo's built-in graph plus any configured
org/project fragments, runs the live merge, and asserts that every built-in
URN that ends up overridden by an org node is on the repo's allowlist. A
built-in **directive** override additionally requires a non-empty reason.

With no overrides authored in this repo, the test passes vacuously (this repo
authors none — its built-in graph is unchanged and no org pack overrides it).
The adjudication logic (:func:`find_unsanctioned_overrides`) is pure and
reusable so a consumer repo can re-run the same governance gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from doctrine.drg.loader import load_graph_or_dir
from doctrine.drg.merge import merge_three_layers
from doctrine.drg.models import DRGGraph, DRGNode, NodeKind
from doctrine.drg.org_pack_loader import OrgDRGFragment
from doctrine.drg.override_policy import (
    ReplaceableBuiltinsPolicy,
    find_overridden_builtin_urns,
    find_unsanctioned_overrides,
    load_replaceable_builtins,
)

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BUILT_IN_GRAPH = _REPO_ROOT / "src" / "doctrine" / "graph.yaml"


def _load_org_fragments(repo_root: Path) -> list[OrgDRGFragment]:
    """Load configured org fragments, tolerating a repo with none.

    The org-pack registry loader lives in the charter layer; the architectural
    suite is allowed to reach across layers. A repo with no ``organisation_packs``
    yields an empty list (the common case, including this repo).
    """
    from charter.drg import load_org_drg  # noqa: PLC0415 — cross-layer test reach

    fragments: list[OrgDRGFragment] = load_org_drg(repo_root)
    return fragments


def _load_project_graph(repo_root: Path) -> DRGGraph | None:
    project_graph = repo_root / ".kittify" / "doctrine" / "graph.yaml"
    if not project_graph.is_file():
        return None
    return load_graph_or_dir(project_graph)


def test_builtin_overrides_are_sanctioned() -> None:
    """Every built-in override in the live merged graph is on the allowlist.

    Vacuously green for this repo (no overrides authored). The assertion logic
    is the governance gate a consumer repo inherits.
    """
    built_in = load_graph_or_dir(_BUILT_IN_GRAPH)
    org_fragments = _load_org_fragments(_REPO_ROOT)
    project = _load_project_graph(_REPO_ROOT)
    policy = load_replaceable_builtins(_REPO_ROOT)

    try:
        # ``merge_three_layers`` raises only on hard-fail (kind-drift /
        # layer-rule); same-kind overrides are non-fatal and surfaced via the
        # merged graph's org-provenance nodes at built-in URNs.
        merged = merge_three_layers(
            built_in=built_in, org_fragments=org_fragments, project=project
        )
    except Exception as exc:  # pragma: no cover - this repo never hard-fails
        pytest.fail(
            f"Built-in DRG merge hard-failed for this repo (no override "
            f"expected): {exc}"
        )

    built_in_urns = frozenset(n.urn for n in built_in.nodes)
    targets = find_overridden_builtin_urns(merged, built_in_urns)
    findings = find_unsanctioned_overrides(targets, policy)
    assert findings == [], (
        "Unsanctioned built-in override(s) detected. Either add the target URN "
        "to .kittify/doctrine/replaceable-builtins.yaml (with a reason for "
        "directives) or remove the override from the org pack:\n"
        + "\n".join(f"  - {f.urn} ({f.kind}): {f.why}" for f in findings)
    )


def _org_fragment(pack_name: str, nodes: list[dict[str, object]]) -> OrgDRGFragment:
    return OrgDRGFragment.model_validate(
        {
            "pack_name": pack_name,
            "source_kind": "local_path",
            "source_ref": f"/tmp/{pack_name}",
            "layer_index": 1,
            "provenance_marker": "org",
            "nodes": nodes,
            "edges": [],
        }
    )


def test_real_merge_override_is_detected_and_governed() -> None:
    """Close the seam between the merge RECORDING an override and the gate
    DETECTING it.

    The live repo test (:func:`test_builtin_overrides_are_sanctioned`) is
    vacuous — this repo authors no overrides, so it would stay green even if
    :func:`find_overridden_builtin_urns` returned ``{}``. This test plants a
    real same-kind org override, runs the *live* ``merge_three_layers``, and
    asserts the detector recovers it AND the governance predicate flags it
    when unlisted / clears it when allowlisted. A regression in the
    provenance-prefix detection (``org:`` / ``in built_in_urns``) fails here.
    """
    built_in = DRGGraph(
        schema_version="1.0",
        generated_at="2026-06-01T00:00:00Z",
        generated_by="unit-test",
        nodes=[DRGNode(urn="tactic:shared", kind=NodeKind.TACTIC, label="Built-in")],
        edges=[],
    )
    org = _org_fragment(
        "rogue",
        nodes=[{"id": "shared", "kind": "tactics", "title": "Override"}],
    )

    merged = merge_three_layers(built_in=built_in, org_fragments=[org], project=None)
    built_in_urns = frozenset(n.urn for n in built_in.nodes)

    # The detector recovers the planted override (not vacuous).
    targets = find_overridden_builtin_urns(merged, built_in_urns)
    assert targets == {"tactic:shared": "tactic"}

    # Unlisted → flagged; allowlisted → cleared. Both directions load-bearing.
    assert [f.urn for f in find_unsanctioned_overrides(targets, _policy())] == [
        "tactic:shared"
    ]
    sanctioned = _policy(("tactic:shared", "org tightened this tactic"))
    assert find_unsanctioned_overrides(targets, sanctioned) == []


# ---------------------------------------------------------------------------
# Pure adjudication-logic coverage (the reusable governance predicate)
# ---------------------------------------------------------------------------


def _policy(*entries: tuple[str, str]) -> ReplaceableBuiltinsPolicy:
    from doctrine.drg.override_policy import ReplaceableBuiltin

    return ReplaceableBuiltinsPolicy(
        entries=tuple(ReplaceableBuiltin(urn=u, reason=r) for u, r in entries)
    )


def test_unlisted_override_is_unsanctioned() -> None:
    targets = {"tactic:foo": "tactic"}
    findings = find_unsanctioned_overrides(targets, _policy())
    assert [f.urn for f in findings] == ["tactic:foo"]
    assert "replaceable-builtins" in findings[0].why


def test_allowlisted_non_directive_override_passes() -> None:
    targets = {"tactic:foo": "tactic"}
    findings = find_unsanctioned_overrides(targets, _policy(("tactic:foo", "")))
    assert findings == []


def test_directive_override_without_reason_is_unsanctioned() -> None:
    targets = {"directive:foo": "directive"}
    findings = find_unsanctioned_overrides(
        targets, _policy(("directive:foo", "   "))
    )
    assert [f.urn for f in findings] == ["directive:foo"]
    assert "reason" in findings[0].why


def test_directive_override_with_reason_passes() -> None:
    targets = {"directive:foo": "directive"}
    findings = find_unsanctioned_overrides(
        targets, _policy(("directive:foo", "we set a stricter posture"))
    )
    assert findings == []
