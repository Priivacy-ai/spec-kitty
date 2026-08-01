"""T022 — Full doctor-health gate + charter catalog + clean-install load.

Three non-fakeable acceptance surfaces for the relocation (NFR-006 / NFR-002):

* **Full doctor health** — ``spec-kitty doctor doctrine --json`` reports FULL
  health: no skipped/invalid profiles (18/18 valid), no ``org_drg`` errors, no
  skipped glossary packs, and the shipped glossary term count is unchanged
  (108). A profiles-only gate would miss ``glossary_packs`` / ``assets``
  degradation, so the whole report is asserted.
* **Charter catalog non-empty** — ``charter.catalog.load_doctrine_catalog()``
  returns non-empty built-in sets for the 7 catalog kinds. ``doctor`` does NOT
  exercise the catalog, so a missed ``catalog.py`` repoint slips through every
  other gate; this is the dedicated guard.
* **Clean-install full-graph proof** — a wheel installed into a fresh venv
  resolves ``load_built_in_graph()`` to the full 324/892 identity: the packaged
  end-to-end proof that the relocated content ships and resolves off
  ``packs/built-in`` in an installed distribution (US3).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from charter.catalog import load_doctrine_catalog
from doctrine.glossary_packs import GlossaryPackRepository
from specify_cli.cli.commands.doctor import app as doctor_app

pytestmark = [pytest.mark.doctrine]

runner = CliRunner()

EXPECTED_PROFILE_COUNT = 18
EXPECTED_GLOSSARY_TERM_COUNT = 108
# The 7 charter-catalog built-in kinds (``template_sets`` / ``domains_present``
# are derived surfaces, not the per-kind artifact catalogs guarded here).
CATALOG_KINDS = (
    "paradigms",
    "directives",
    "tactics",
    "styleguides",
    "toolguides",
    "procedures",
    "agent_profiles",
)


@pytest.fixture
def bare_project_root(tmp_path: Path) -> Path:
    """A minimal spec-kitty project root — no org packs, no project doctrine."""
    project_root = tmp_path / "project"
    kittify = project_root / ".kittify"
    kittify.mkdir(parents=True)
    (kittify / "config.yaml").write_text(
        "agents:\n  available:\n    - claude\n", encoding="utf-8"
    )
    return project_root


def _invoke_doctrine_json(project_root: Path) -> tuple[int, dict]:
    with patch(
        "specify_cli.cli.commands.doctor.locate_project_root",
        return_value=project_root,
    ):
        result = runner.invoke(doctor_app, ["doctrine", "--json"])
    return result.exit_code, json.loads(result.output)


# ---------------------------------------------------------------------------
# Full doctor-health gate (NFR-006)
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_doctor_doctrine_reports_full_health(bare_project_root: Path) -> None:
    exit_code, payload = _invoke_doctrine_json(bare_project_root)

    assert exit_code == 0, f"doctor doctrine flipped unhealthy: {payload}"

    profile_health = payload["profile_health"]
    assert profile_health["healthy"] is True

    builtin_pack = next(
        p for p in profile_health["packs"] if p["layer"] == "builtin"
    )
    # 18/18 profiles valid, skipped/invalid profiles empty.
    assert builtin_pack["discovered_count"] == EXPECTED_PROFILE_COUNT
    assert builtin_pack["valid_count"] == EXPECTED_PROFILE_COUNT
    assert builtin_pack["invalid_profiles"] == []

    # No org_drg errors (top-level and nested views agree).
    assert payload["org_drg"]["errors"] == []
    assert profile_health["org_drg"]["errors"] == []


@pytest.mark.fast
def test_doctor_doctrine_glossary_packs_are_healthy(bare_project_root: Path) -> None:
    _, payload = _invoke_doctrine_json(bare_project_root)

    glossary = payload["profile_health"]["glossary_packs"]
    assert glossary["healthy"] is True
    assert glossary["invalid_packs"] == []
    assert glossary["term_count"] == EXPECTED_GLOSSARY_TERM_COUNT

    # Cross-check against the live shipped pack so the golden 108 cannot silently
    # drift from what actually loads off packs/built-in.
    live_pack = GlossaryPackRepository().get("spec-kitty-core")
    assert live_pack is not None
    assert len(live_pack.terms) == EXPECTED_GLOSSARY_TERM_COUNT


# ---------------------------------------------------------------------------
# Charter catalog non-empty (NFR-002) — the post-tasks BLOCKER guard
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_charter_catalog_built_in_sets_are_non_empty() -> None:
    catalog = load_doctrine_catalog()
    for kind in CATALOG_KINDS:
        artifacts = getattr(catalog, kind)
        assert artifacts, f"charter catalog kind {kind!r} resolved to an EMPTY set"


# ---------------------------------------------------------------------------
# Clean-install full-graph proof (NFR-002 / US3) — the packaged end-to-end gate
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.non_sandbox  # builds + installs a wheel into a fresh venv (>30s)
def test_clean_install_resolves_full_built_in_graph(
    installed_wheel_venv: dict[str, Path],
) -> None:
    """A wheel installed into a fresh venv resolves the full 324/892 identity."""
    python = installed_wheel_venv["python"]
    result = subprocess.run(
        [
            str(python),
            "-c",
            (
                "from doctrine.drg.loader import load_built_in_graph; "
                "g = load_built_in_graph(); "
                "print(len(g.nodes), len(g.edges))"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"clean-install load_built_in_graph() failed:\n{result.stderr}"
    )
    node_count, edge_count = result.stdout.split()
    assert (int(node_count), int(edge_count)) == (324, 892), (
        f"clean-install graph cardinality drifted: {result.stdout!r}"
    )
