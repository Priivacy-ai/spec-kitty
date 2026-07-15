"""WP03 T009/T010 — org-pack governance context on the dispatch ``--profile`` path.

These tests drive the *dispatch* governance-context surface
(``build_charter_context(repo, profile=<id>, action=...)`` → ``_load_agent_profile``
→ the activation-aware profile map), NOT the already-gated
``charter context --include agent-profile:<id>`` path.

The assertion is **sentinel-based** (BINDING post-tasks remediation): the org
profile's own doctrine carries a distinctive string that exists ONLY in its
pack. A built-in/generic fallback context would pass a mere ``context != ""``
check, so non-emptiness is forbidden — we assert the sentinel itself.

Two-regime live proof (NFR-002):

* admitted (activation absent) → the dispatched org agent's governance context
  CONTAINS the sentinel;
* de-activated (explicit list excluding it) → the sentinel is ABSENT (the org
  profile resolves to nothing, so its profile-cited sections never render).

No-org-packs regression (NFR-001): with no pack declared the built-in profile
path is unchanged and deterministic, and no org sentinel can appear.

WP01 (#2365) extends this module with the ``activations:`` resolve-time
union's own NFR coverage:

* NFR-002 (no new shadow path) — an org-only activation reaches the
  rendered text stanza WITHOUT ever being written into the project's
  ``governance.yaml`` on disk.
* NFR-003 (zero regression for non-org repos) — a repo with no org pack
  configured resolves activations byte-identically across repeated
  bootstrap resolutions and renders no activation stanza when neither
  source declares one.
"""

from __future__ import annotations

import textwrap
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from ruamel.yaml import YAML

from charter.context import CharterContextResult, _reset_agent_profile_cache, build_charter_context
from doctrine.drg.models import DRGGraph

pytestmark = pytest.mark.fast

# A distinctive string present ONLY in the org pack's analyst doctrine.
_ORG_SENTINEL = "ORGZILLA-SENTINEL evidence-provenance governance rule"
_PACK_NAME = "orgzilla-governance-pack"
_ORG_ANALYST_ID = "orgzilla-org-analyst"
_BUILTIN_ID = "python-pedro"
_DISPATCH_ACTION = "advise"  # non-bootstrap → compact governance render path


def _org_profile_yaml() -> str:
    """Render an org analyst profile whose directive rationale is the sentinel."""
    return (
        f"profile-id: {_ORG_ANALYST_ID}\n"
        "name: Orgzilla Org Analyst\n"
        "description: Org-pack analyst profile for governance-context fixtures\n"
        'schema-version: "1.0"\n'
        "roles:\n"
        "  - researcher\n"
        "purpose: >\n"
        "  Organisation-provided analyst contributed through an org doctrine pack.\n"
        "specialization:\n"
        "  primary-focus: >\n"
        "    Organisation-specific evidence-provenance analysis.\n"
        "directive-references:\n"
        '  - code: "010"\n'
        "    name: Specification Fidelity Requirement\n"
        f"    rationale: {_ORG_SENTINEL}\n"
    )


def _write_org_pack(repo_root: Path) -> Path:
    pack_root = repo_root / "org-packs" / _PACK_NAME
    profiles_dir = pack_root / "agent_profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    (profiles_dir / f"{_ORG_ANALYST_ID}.agent.yaml").write_text(
        _org_profile_yaml(), encoding="utf-8"
    )
    return pack_root


def _write_config(repo_root: Path, pack_root: Path, *, activated: list[str] | None) -> None:
    data: dict[str, object] = {
        "doctrine": {"org": {"packs": [{"name": _PACK_NAME, "local_path": str(pack_root)}]}},
    }
    if activated is not None:
        data["activated_agent_profiles"] = activated
    kittify = repo_root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    with (kittify / "config.yaml").open("w", encoding="utf-8") as fh:
        YAML().dump(data, fh)


def _governance_text(repo_root: Path, profile_id: str) -> str:
    result = build_charter_context(
        repo_root,
        profile=profile_id,
        action=_DISPATCH_ACTION,
        mark_loaded=False,
    )
    return str(result.text)


@pytest.fixture(autouse=True)
def _clean_profile_cache() -> None:
    _reset_agent_profile_cache()


class TestTwoRegimeOrgGovernanceContext:
    def test_admitted_org_profile_context_carries_sentinel(self, tmp_path: Path) -> None:
        """Activation absent → dispatched org agent's context contains the sentinel."""
        repo = tmp_path / "admitted"
        repo.mkdir()
        pack_root = _write_org_pack(repo)
        _write_config(repo, pack_root, activated=None)

        text = _governance_text(repo, _ORG_ANALYST_ID)

        assert _ORG_SENTINEL in text

    def test_deactivated_org_profile_context_omits_sentinel(self, tmp_path: Path) -> None:
        """Explicit list excluding the org id → the sentinel is ABSENT (gate bites)."""
        repo = tmp_path / "deactivated"
        repo.mkdir()
        pack_root = _write_org_pack(repo)
        # Activate only a built-in id — the org analyst is de-activated.
        _write_config(repo, pack_root, activated=[_BUILTIN_ID])

        text = _governance_text(repo, _ORG_ANALYST_ID)

        assert _ORG_SENTINEL not in text


class TestNoOrgPacksGovernanceRegression:
    """T010 — no org packs declared → unchanged, deterministic, no org sentinel."""

    def test_builtin_profile_path_unchanged_and_deterministic(self, tmp_path: Path) -> None:
        repo = tmp_path / "no_packs"
        repo.mkdir()
        # No .kittify/config.yaml org packs at all.

        first = _governance_text(repo, _BUILTIN_ID)
        _reset_agent_profile_cache()
        second = _governance_text(repo, _BUILTIN_ID)

        # Byte-identical across calls — the no-org-packs path is unchanged.
        assert first == second
        # The org sentinel can never appear without a declared pack.
        assert _ORG_SENTINEL not in first
        # A built-in profile still resolves through the unchanged fast path.
        assert _BUILTIN_ID in first


# ---------------------------------------------------------------------------
# WP01 (#2365) — activation-stanza NFR-002/NFR-003 coverage.
# ---------------------------------------------------------------------------

_ACTIVATION_ORG_PACK_NAME = "orgzilla-activation-pack"
_ORG_ONLY_ACTIVATION_ARTIFACT_ID = "org-purity-check-artifact-2365"

_ACTIVATION_CHARTER_MD = textwrap.dedent(
    """\
    # Test Charter

    ## Policy Summary

    - Intent: deterministic delivery
    """
)

_ACTIVATION_GOVERNANCE_YAML = textwrap.dedent(
    """\
    doctrine:
      template_set: software-dev-default
      selected_paradigms: []
      selected_directives: []
      available_tools: []
    """
)

_ACTIVATION_MINIMAL_GRAPH_YAML = textwrap.dedent(
    """\
    schema_version: "1.0"
    generated_at: "2026-04-13T10:00:00+00:00"
    generated_by: "test"
    nodes:
      - urn: "action:software-dev/implement"
        kind: action
        label: implement
    edges: []
    """
)


def _write_activation_project_fixture(repo_root: Path) -> None:
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    (charter_dir / "charter.md").write_text(_ACTIVATION_CHARTER_MD, encoding="utf-8")
    (charter_dir / "governance.yaml").write_text(_ACTIVATION_GOVERNANCE_YAML, encoding="utf-8")


def _write_activation_org_pack(repo_root: Path) -> Path:
    pack_root = repo_root / "org-packs" / _ACTIVATION_ORG_PACK_NAME
    pack_root.mkdir(parents=True, exist_ok=True)
    (pack_root / "org-charter.yaml").write_text(
        textwrap.dedent(
            f"""\
            activations:
              - activation_context:
                  mission_type: software-dev
                  action: implement
                doctrine_pack_id: {_ACTIVATION_ORG_PACK_NAME}
                artifact_id: {_ORG_ONLY_ACTIVATION_ARTIFACT_ID}
                artifact_kind: styleguides
            """
        ),
        encoding="utf-8",
    )
    return pack_root


def _register_activation_org_pack(repo_root: Path, pack_root: Path) -> None:
    kittify = repo_root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    with (kittify / "config.yaml").open("w", encoding="utf-8") as fh:
        YAML().dump(
            {
                "doctrine": {
                    "org": {"packs": [{"name": _ACTIVATION_ORG_PACK_NAME, "local_path": str(pack_root)}]}
                }
            },
            fh,
        )


def _resolve_bootstrap(repo_root: Path) -> CharterContextResult:
    yaml = YAML(typ="safe")
    mock_graph = DRGGraph.model_validate(yaml.load(StringIO(_ACTIVATION_MINIMAL_GRAPH_YAML)))

    with (
        patch("charter._drg_helpers.load_validated_graph", return_value=mock_graph),
        patch("charter.catalog.resolve_doctrine_root", return_value=repo_root),
        patch("doctrine.drg.validator.assert_valid"),
        patch("charter.sync.ensure_charter_bundle_fresh", return_value=None),
    ):
        return build_charter_context(
            repo_root, action="implement", depth=2, mark_loaded=False,
            mission_type="software-dev",
        )


class TestActivationUnionShadowPathAndByteIdentity:
    """WP01 NFR-002/NFR-003 — no shadow write; non-org repos unchanged."""

    def test_org_only_activation_absent_from_governance_yaml_present_in_stanza(
        self, tmp_path: Path
    ) -> None:
        """NFR-002: the org-only activation reaches the rendered stanza
        without ever being written into the project's governance.yaml —
        the resolve-time union is read-only, never a generate-time fold."""
        repo = tmp_path / "consumer"
        repo.mkdir()
        _write_activation_project_fixture(repo)
        pack_root = _write_activation_org_pack(repo)
        _register_activation_org_pack(repo, pack_root)

        result = _resolve_bootstrap(repo)

        assert _ORG_ONLY_ACTIVATION_ARTIFACT_ID in result.text

        governance_on_disk = (repo / ".kittify" / "charter" / "governance.yaml").read_text(
            encoding="utf-8"
        )
        assert _ORG_ONLY_ACTIVATION_ARTIFACT_ID not in governance_on_disk, (
            "the org-only activation leaked into governance.yaml — the union "
            "must stay resolve-time only (NFR-002 no new shadow path)"
        )

    def test_non_org_repo_activation_resolution_is_byte_identical(self, tmp_path: Path) -> None:
        """NFR-003: with no org pack configured, repeated bootstrap
        resolution is byte-identical and renders no activation stanza —
        the org-union addition does not perturb the non-org path."""
        repo = tmp_path / "no_org_pack"
        repo.mkdir()
        _write_activation_project_fixture(repo)
        # Deliberately no .kittify/config.yaml org packs at all.

        first = _resolve_bootstrap(repo)
        second = _resolve_bootstrap(repo)

        assert first.text == second.text
        assert "Selected activations:" not in first.text
