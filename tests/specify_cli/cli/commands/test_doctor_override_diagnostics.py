"""WP08 (#2082): ``doctor doctrine`` flags unsanctioned built-in DRG overrides.

C-005 red-first through the **public** ``doctor doctrine --json`` surface (NOT
the promoted predicate API — that is WP07's surface). C-007 realistic org-pack
fixtures: a real on-disk ``drg/fragment.yaml`` pack layout (read by
``load_org_drg``) overriding a real shipped built-in URN. NFR-001 no-org-packs
regression (the finding path stays unreachable without org packs).

The governance boundary under test (FR-010 / FR-012):

* an ``org:``-provenance override of a built-in DRG node that is NOT sanctioned
  by ``.kittify/doctrine/replaceable-builtins.yaml`` is flagged and flips the
  report unhealthy (RC=1);
* a sanctioning allowlist entry (with a reason, since the target is a built-in
  *directive*) clears the finding;
* a repo with no org packs is byte-identical to today (no ``unsanctioned_overrides``
  key emitted).
"""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

pytestmark = pytest.mark.fast

runner = CliRunner()

# A real shipped built-in directive URN (src/doctrine/graph.yaml). Using a real
# built-in URN (not a handcrafted placeholder) is what makes the merge record a
# same-kind ``org_override`` the gate can adjudicate (C-007).
_BUILT_IN_DIRECTIVE_URN = "directive:DIRECTIVE_001"


# ---------------------------------------------------------------------------
# Realistic on-disk org-pack fixtures (read by ``load_org_drg``).
# ---------------------------------------------------------------------------


def _write_org_override_pack(repo_root: Path) -> Path:
    """Create a realistic org pack overriding a real built-in directive node.

    Mirrors the on-disk org-pack layout (``drg/fragment.yaml`` + body file)
    that ``load_org_drg`` reads — distinct from a hand-built ``OrgDRGFragment``.
    The override targets a real shipped built-in URN so ``merge_three_layers``
    records a same-kind ``org_override`` (C-007).
    """
    pack_root = repo_root / "org-pack"
    drg_dir = pack_root / "drg"
    directives_dir = pack_root / "directives"
    drg_dir.mkdir(parents=True)
    directives_dir.mkdir(parents=True)
    (drg_dir / "fragment.yaml").write_text(
        dedent(
            """\
            pack_name: acme-org
            source_kind: local_path
            source_ref: org-pack
            layer_index: 1
            provenance_marker: org
            nodes:
              - id: DIRECTIVE_001
                kind: directives
                title: "ACME-tightened first directive"
                body_path: directives/DIRECTIVE_001.directive.yaml
            edges: []
            """
        )
    )
    (directives_dir / "DIRECTIVE_001.directive.yaml").write_text(
        dedent(
            """\
            id: DIRECTIVE_001
            type: directive
            title: "ACME-tightened first directive"
            body: |
              Org-tier replacement for the built-in DIRECTIVE_001 (fixture).
            severity: binding
            status: active
            """
        )
    )
    return pack_root


def _write_config(repo_root: Path, pack_root: Path) -> None:
    """Write the canonical ``doctrine.org.packs`` config that ``load_org_drg`` reads."""
    kittify = repo_root / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text(
        dedent(
            f"""\
            doctrine:
              org:
                packs:
                  - name: acme-org
                    local_path: {pack_root}
            """
        )
    )


def _write_allowlist(repo_root: Path, *, reason: str) -> None:
    """Write a ``replaceable-builtins.yaml`` sanctioning the override URN."""
    doctrine_dir = repo_root / ".kittify" / "doctrine"
    doctrine_dir.mkdir(parents=True, exist_ok=True)
    (doctrine_dir / "replaceable-builtins.yaml").write_text(
        dedent(
            f"""\
            replaceable_builtins:
              - urn: {_BUILT_IN_DIRECTIVE_URN}
                reason: {reason}
            """
        )
    )


def _run_doctrine_json(repo_root: Path) -> tuple[int, dict[str, object]]:
    """Drive ``doctor doctrine --json`` and return ``(exit_code, payload)``."""
    from specify_cli.cli.commands.doctor import app as doctor_app

    with patch(
        "specify_cli.cli.commands.doctor.locate_project_root",
        return_value=repo_root,
    ):
        result = runner.invoke(doctor_app, ["doctrine", "--json"])
    try:
        payload = json.loads(result.output)
    except json.JSONDecodeError as exc:  # pragma: no cover - failure diagnostic
        pytest.fail(
            f"doctor doctrine --json did not produce valid JSON: {exc}\n"
            f"output: {result.output!r}"
        )
    return result.exit_code, payload


def _org_drg(payload: dict[str, object]) -> dict[str, object]:
    org_drg = payload.get("org_drg")
    assert isinstance(org_drg, dict), f"expected org_drg dict, got: {payload!r}"
    return org_drg


# ---------------------------------------------------------------------------
# Public-surface cases (C-005).
# ---------------------------------------------------------------------------


def test_unsanctioned_org_override_is_flagged(tmp_path: Path) -> None:
    """An unlisted org override of a built-in directive flips the report unhealthy.

    RED today: the override is invisible to the operator (no diagnostic emitted,
    RC=0). GREEN once WP08 wires the promoted predicates into the org-packs-present
    branch.
    """
    pack = _write_org_override_pack(tmp_path)
    _write_config(tmp_path, pack)

    exit_code, payload = _run_doctrine_json(tmp_path)

    org_drg = _org_drg(payload)
    overrides = org_drg.get("unsanctioned_overrides", [])
    assert isinstance(overrides, list) and overrides, (
        "expected a non-empty unsanctioned_overrides finding for the unlisted "
        f"built-in override, got org_drg={org_drg!r}"
    )
    assert any(
        isinstance(o, dict) and o.get("urn") == _BUILT_IN_DIRECTIVE_URN
        for o in overrides
    ), f"expected {_BUILT_IN_DIRECTIVE_URN} in findings: {overrides!r}"

    profile_health = payload.get("profile_health")
    assert isinstance(profile_health, dict)
    assert profile_health.get("healthy") is False, (
        "an unsanctioned built-in override must flip healthy=false"
    )
    assert exit_code == 1, f"expected RC=1, got {exit_code}: {payload!r}"


def test_sanctioned_org_override_is_cleared(tmp_path: Path) -> None:
    """A sanctioning allowlist entry (with a reason) clears the finding (RC=0)."""
    pack = _write_org_override_pack(tmp_path)
    _write_config(tmp_path, pack)
    _write_allowlist(tmp_path, reason="ACME tightened the binding posture")

    exit_code, payload = _run_doctrine_json(tmp_path)

    org_drg = _org_drg(payload)
    assert org_drg.get("unsanctioned_overrides", []) == [], (
        "a sanctioned override must NOT be flagged"
    )
    profile_health = payload.get("profile_health")
    assert isinstance(profile_health, dict)
    assert profile_health.get("healthy") is True, (
        "with the override sanctioned (and no other defects) the report is healthy"
    )
    assert exit_code == 0, f"expected RC=0, got {exit_code}: {payload!r}"


def test_no_org_packs_output_unchanged(tmp_path: Path) -> None:
    """No org packs → the finding path is unreachable; no key emitted (NFR-001)."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text(
        dedent(
            """\
            agents:
              available:
                - claude
            """
        )
    )

    exit_code, payload = _run_doctrine_json(tmp_path)

    org_drg = _org_drg(payload)
    assert "unsanctioned_overrides" not in org_drg, (
        "the unsanctioned-override key must not appear without org packs (NFR-001)"
    )
    assert org_drg.get("configured_packs", []) == []
    assert exit_code == 0, f"expected RC=0 for a built-in-only repo, got {exit_code}"


# ---------------------------------------------------------------------------
# Pure helper coverage: ``_adjudicate_org_overrides`` (extracted in T023).
# ---------------------------------------------------------------------------


def _override_fragment(urn_kind: str) -> object:
    from doctrine.drg.org_pack_loader import OrgDRGFragment

    item_id = "DIRECTIVE_001"
    return OrgDRGFragment.model_validate(
        {
            "pack_name": "acme-org",
            "source_kind": "local_path",
            "source_ref": "org-packs/acme-org",
            "layer_index": 1,
            "provenance_marker": "org",
            "nodes": [{"id": item_id, "kind": urn_kind, "title": "Override"}],
            "edges": [],
        }
    )


def test_adjudicate_org_overrides_flags_unlisted_directive(tmp_path: Path) -> None:
    """The extracted helper flags an unlisted built-in directive override."""
    from specify_cli.cli.commands._doctrine_collect import _adjudicate_org_overrides
    from doctrine.drg.merge import merge_three_layers
    from doctrine.drg.models import DRGGraph, DRGNode, NodeKind

    built_in = DRGGraph(
        schema_version="1.0",
        generated_at="2026-06-01T00:00:00Z",
        generated_by="unit-test",
        nodes=[
            DRGNode(urn="directive:DIRECTIVE_001", kind=NodeKind.DIRECTIVE, label="Built-in")
        ],
        edges=[],
    )
    merged = merge_three_layers(
        built_in=built_in, org_fragments=[_override_fragment("directives")], project=None
    )
    built_in_urns = frozenset(n.urn for n in built_in.nodes)

    findings = _adjudicate_org_overrides(merged, built_in_urns, tmp_path)
    assert [f["urn"] for f in findings] == ["directive:DIRECTIVE_001"]
    assert findings[0]["kind"] == "directive"
    assert "replaceable-builtins" in findings[0]["why"]


def test_adjudicate_org_overrides_clears_sanctioned_directive(tmp_path: Path) -> None:
    """A directive override with a non-empty reason clears via the helper."""
    from specify_cli.cli.commands._doctrine_collect import _adjudicate_org_overrides
    from doctrine.drg.merge import merge_three_layers
    from doctrine.drg.models import DRGGraph, DRGNode, NodeKind

    built_in = DRGGraph(
        schema_version="1.0",
        generated_at="2026-06-01T00:00:00Z",
        generated_by="unit-test",
        nodes=[
            DRGNode(urn="directive:DIRECTIVE_001", kind=NodeKind.DIRECTIVE, label="Built-in")
        ],
        edges=[],
    )
    merged = merge_three_layers(
        built_in=built_in, org_fragments=[_override_fragment("directives")], project=None
    )
    built_in_urns = frozenset(n.urn for n in built_in.nodes)
    _write_allowlist(tmp_path, reason="org tightened this directive")

    findings = _adjudicate_org_overrides(merged, built_in_urns, tmp_path)
    assert findings == []
