"""Doctrine-tier entry point for the FR-005/NFR-002 config<->derived parity guard.

WP05 (mission ``unify-charter-activation-surfaces-01KX5SJ9``). Before this WP,
``charter.consistency_check.run_consistency_check`` was reachable only from
the CLI (``spec-kitty charter pack consistency-check``, wired at
``src/specify_cli/cli/commands/charter/pack.py:31-47``). NFR-002 requires the
fail-closed config<->derived parity guard to bite in the test suite too, not
only when an operator remembers to run the CLI by hand -- this module is that
entry point (T019), plus the non-vacuity self-tests (T020) that prove each
new assertion actually fires on a planted divergence rather than being green
for the wrong reason.

Covers:
- ``test_this_project_charter_pack_is_coherent``: T019 suite-tier entry point.
- ``test_config_directive_absent_from_references_bites`` /
  ``test_config_directive_present_in_references_is_coherent``: T017 forward
  ID-level parity (the #2524 dangler class), RED/GREEN pair.
- ``test_orphan_paradigm_reference_bites``: T017 reverse ID-level parity
  (paradigms only -- see ``consistency_check._check_reference_id_parity``
  docstring for why the reverse check is scoped to paradigms).
- ``test_config_kind_absent_from_graph_bites``: T018 KIND-level config<->DRG
  parity.
- ``test_consistency_check_does_not_import_freshness_or_specify_cli``: layer
  discipline pinned per the WP -- ``consistency_check`` must stay disjoint
  from ``freshness/computer.py`` (a ``specify_cli`` module that imports
  ``charter`` back) and must never import ``specify_cli`` at all.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from charter.consistency_check import run_consistency_check
from charter.invocation_context import ProjectContext

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONSISTENCY_CHECK_SOURCE = _REPO_ROOT / "src" / "charter" / "consistency_check.py"

# A real, stable built-in directive whose canonical id (``DIRECTIVE_001``)
# DIFFERS from its config stem (``001-architectural-integrity-standard``) --
# exercises the exact stem<->canonical-id normalization the guard depends on
# (C-006: "a stem that fails to normalize must be rejected, never silently
# dropped").
_REAL_DIRECTIVE_STEM = "001-architectural-integrity-standard"
_REAL_DIRECTIVE_CANONICAL = "DIRECTIVE_001"
# A real, stable built-in paradigm whose id == its config stem (paradigms are
# rendered 1:1, never DRG-transitively expanded).
_REAL_PARADIGM_STEM = "atomic-design"


def _write_config(tmp_path: Path, content: str) -> Path:
    """Write a .kittify/config.yaml with the given content; return .kittify/."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text(content, encoding="utf-8")
    return kittify


def _write_references(kittify: Path, ref_entries: list[dict[str, str]]) -> None:
    """Write a minimal .kittify/charter/references.yaml with the given entries."""
    charter_dir = kittify / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0.0",
        "generated_at": "2026-07-10T00:00:00Z",
        "mission": "software-dev",
        "template_set": "software-dev-default",
        "languages": ["python"],
        "references": ref_entries,
    }
    yaml = YAML()
    yaml.default_flow_style = False
    with (charter_dir / "references.yaml").open("w", encoding="utf-8") as handle:
        yaml.dump(payload, handle)


def _reference_entry(ref_id: str, kind: str) -> dict[str, str]:
    return {
        "id": ref_id,
        "kind": kind,
        "title": "x",
        "summary": "x",
        "source_path": "",
        "local_path": "x",
    }


# ---------------------------------------------------------------------------
# T019: doctrine-test-tier entry point -- the guard now bites in the suite.
# ---------------------------------------------------------------------------


def test_this_project_charter_pack_is_coherent() -> None:
    """The guard runs against this project's own config/doctrine/DRG.

    Previously this only happened when an operator ran
    ``spec-kitty charter pack consistency-check`` by hand; this test makes
    it a suite-tier gate (NFR-002) so a #2524-style divergence fails
    locally, not only at CI or on manual invocation.
    """
    ctx = ProjectContext.from_repo(_REPO_ROOT)
    report = run_consistency_check(ctx)

    assert report.coherent, (
        "Charter pack consistency check failed for this project:\n"
        f"unknown_references={report.unknown_references}\n"
        f"missing_from_doctrine={report.missing_from_doctrine}\n"
        f"kind_violations={report.kind_violations}\n"
        f"reference_id_divergences={report.reference_id_divergences}\n"
        f"graph_kind_gaps={report.graph_kind_gaps}\n"
        f"suggestions={report.suggestions}"
    )


# ---------------------------------------------------------------------------
# T020: non-vacuity self-tests -- a planted divergence MUST make the guard bite.
# ---------------------------------------------------------------------------


def test_config_directive_absent_from_references_bites(tmp_path: Path) -> None:
    """#2524 dangler class: config activates a directive, references.yaml lacks it."""
    kittify = _write_config(
        tmp_path,
        f"activated_directives:\n  - {_REAL_DIRECTIVE_STEM}\n",
    )
    # Compiled WITHOUT the activated directive -- the exact #2524 shape (live
    # in config, dangling in the compiled reference set).
    _write_references(kittify, [])

    ctx = ProjectContext.from_repo(tmp_path)
    report = run_consistency_check(ctx)

    assert report.coherent is False
    assert f"directive/{_REAL_DIRECTIVE_STEM}" in report.reference_id_divergences
    assert any(
        "does not resolve in .kittify/charter/references.yaml" in s
        for s in report.suggestions
    )


def test_config_directive_present_in_references_is_coherent(tmp_path: Path) -> None:
    """Sibling GREEN case: proves the RED above is a real assertion, not env noise."""
    kittify = _write_config(
        tmp_path,
        f"activated_directives:\n  - {_REAL_DIRECTIVE_STEM}\n",
    )
    _write_references(
        kittify,
        [_reference_entry(f"DIRECTIVE:{_REAL_DIRECTIVE_CANONICAL}", "directive")],
    )

    ctx = ProjectContext.from_repo(tmp_path)
    report = run_consistency_check(ctx)

    assert report.coherent is True
    assert report.reference_id_divergences == []


def test_orphan_paradigm_reference_bites(tmp_path: Path) -> None:
    """Reverse direction (paradigms only): a compiled paradigm with no config activation.

    Paradigms are rendered 1:1 from ``config.activated_paradigms`` with no
    DRG-transitive expansion, so this is the one kind where a reverse
    (references -> config) check is sound -- see
    ``consistency_check._check_reference_id_parity``.
    """
    kittify = _write_config(
        tmp_path,
        "activated_paradigms:\n  - domain-driven-design\n",
    )
    _write_references(
        kittify,
        [
            _reference_entry("PARADIGM:domain-driven-design", "paradigm"),
            # Orphan: resolves in references.yaml but not activated in config.
            _reference_entry(f"PARADIGM:{_REAL_PARADIGM_STEM}", "paradigm"),
        ],
    )

    ctx = ProjectContext.from_repo(tmp_path)
    report = run_consistency_check(ctx)

    assert report.coherent is False
    assert f"paradigm/{_REAL_PARADIGM_STEM}" in report.reference_id_divergences


def test_config_kind_absent_from_graph_bites(tmp_path: Path) -> None:
    """KIND-level (T018): config activates directives, but 'directives' is
    excluded from ``activated_kinds`` -- no directive kind can survive the
    KIND-level activation gate, so the graph shows zero directive nodes even
    though config carries directive IDs.
    """
    _write_config(
        tmp_path,
        (
            f"activated_directives:\n  - {_REAL_DIRECTIVE_STEM}\n"
            "activated_kinds:\n"
            "  - tactics\n"
            "  - paradigms\n"
            "  - styleguides\n"
            "  - toolguides\n"
            "  - procedures\n"
            "  - agent_profiles\n"
            "  - mission_step_contracts\n"
            "  - templates\n"
            "  - assets\n"
        ),
    )
    ctx = ProjectContext.from_repo(tmp_path)
    report = run_consistency_check(ctx)

    assert report.coherent is False
    assert "directive" in report.graph_kind_gaps
    assert any(
        "none survive in the activation-filtered DRG graph" in s
        for s in report.suggestions
    )


def test_config_kind_present_in_activated_kinds_is_coherent(tmp_path: Path) -> None:
    """Sibling GREEN case for T018: proves the RED above is a real assertion."""
    _write_config(
        tmp_path,
        f"activated_directives:\n  - {_REAL_DIRECTIVE_STEM}\n",
    )
    ctx = ProjectContext.from_repo(tmp_path)
    report = run_consistency_check(ctx)

    assert report.graph_kind_gaps == []


# ---------------------------------------------------------------------------
# T020: layer discipline -- the guard must stay disjoint from freshness /
# specify_cli. ``freshness/computer.py`` is a ``specify_cli`` module that
# imports ``charter``; ``charter.consistency_check`` importing it back would
# be a cycle (and a layer-rule violation independent of the cycle -- see
# ``tests/architectural/test_layer_rules.py`` for the general charter
# !import specify_cli rule this test pins the specific case of).
# ---------------------------------------------------------------------------


def test_consistency_check_does_not_import_freshness_or_specify_cli() -> None:
    tree = ast.parse(_CONSISTENCY_CHECK_SOURCE.read_text(encoding="utf-8"))
    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)

    assert not any(
        module == "specify_cli" or module.startswith("specify_cli.")
        for module in imported_modules
    ), f"consistency_check.py must not import specify_cli (layer rule); found: {imported_modules}"
    assert not any("freshness" in module for module in imported_modules), (
        f"consistency_check.py must stay disjoint from freshness/computer.py; "
        f"found: {imported_modules}"
    )
