"""Red-first: layered per-type governance-profile probe (#3598, WP03).

FR-005/FR-006, NFR-002, AC-4/5/6 —
``docs/adr/3.x/2026-08-21-1-charter-gate-predicate-inversion.md``.

``_resolve_governance_slot`` (``src/charter/mission_type_profiles.py``)
used to tolerate ANY unregistered mission type whenever the **project-wide**
``_project_has_doctrine_overrides(repo_root)`` probe was ``True`` — a
project with *any* ``selected_*`` doctrine (directives, tactics, ...)
authored the tolerance for *every* unregistered type, including a typo. A
typo'd type (``softwaer-dev``) then resolved silently with fabricated
provenance.

This suite pins the LAYERED PER-TYPE replacement: an unregistered mission
type is tolerated **iff** a per-type ``governance-profile.yaml`` whose ``id``
matches the type resolves at the **project or org** layer (via
``MissionTypeProfileRepository`` / ``_GOVERNANCE_PROFILE_GLOB``); otherwise
``UnknownMissionTypeError`` is raised.

**Operator ruling (rework, docs/adr/3.x/2026-08-21-1-charter-gate-predicate-inversion.md
— "layered tolerance (AC-5) does NOT override mission-type activation
gating"):** the built-in layer is deliberately EXCLUDED from the tolerance
witness. Every canonical built-in type ships its own built-in
``governance-profile.yaml``, so tolerating on built-in-profile-existence
alone would let ANY non-activated canonical type silently resolve, defeating
the pre-existing FR-006 activation-subset gate pinned by
``tests/charter/test_mission_type_activation_gating.py`` (not owned by this
WP — that suite MUST stay green, unchanged). The original AC-5 draft
included a built-in-layer tolerance sub-test using a non-activated canonical
type (``research``); it collided with that gate and was replaced below by
the negative pin proving the opposite.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from charter.activation.mission_type_profiles import (
    UnknownMissionTypeError,
    resolve_mission_type_context,
)

pytestmark = [pytest.mark.fast, pytest.mark.unit]


def _write_activation_config(repo_root: Path, activations: list[str]) -> None:
    """Write a minimal ``.kittify/config.yaml`` with an explicit activation list."""
    kittify = repo_root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    lines = "\n".join(f"  - {mt}" for mt in activations)
    (kittify / "config.yaml").write_text(f"mission_type_activations:\n{lines}\n", encoding="utf-8")


def _write_charter_with_other_doctrine(repo_root: Path) -> None:
    """Seed ``charter.yaml`` with unrelated ``selected_*`` doctrine.

    This is the OLD project-wide tolerance witness
    (``_project_has_doctrine_overrides``) — present here so AC-4 proves the
    typo hard-fails even though the project-wide signal that used to
    silently tolerate it is still true.
    """
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    (charter_dir / "charter.yaml").write_text(
        "governance:\n  doctrine:\n    selected_directives:\n      - DIRECTIVE_001\n",
        encoding="utf-8",
    )


def _write_governance_profile(target_dir: Path, mission_type: str) -> None:
    """Write ``<target_dir>/governance-profile.yaml`` with a matching ``id``."""
    target_dir.mkdir(parents=True, exist_ok=True)
    yaml = YAML()
    yaml.default_flow_style = False
    with (target_dir / "governance-profile.yaml").open("w") as fh:
        yaml.dump({"id": mission_type, "mission_type": mission_type}, fh)


def _write_org_pack_config(
    repo_root: Path,
    *,
    packs: list[tuple[str, Path]],
    activated_mission_types: list[str],
) -> None:
    """Write a real ``.kittify/config.yaml`` carrying both the mission-type
    activation set and the ``doctrine.org.packs`` registry."""
    config_dir = repo_root / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    lines = ["mission_type_activations:"]
    for mission_type in activated_mission_types:
        lines.append(f"  - {mission_type}")
    if packs:
        lines += ["doctrine:", "  org:", "    packs:"]
        for name, local_path in packs:
            lines.append(f"      - name: {name}")
            lines.append(f"        local_path: {local_path}")
    (config_dir / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestAC4TypoNoLongerResolvesSilently:
    """AC-4 — an unregistered type with no matching per-type profile at any
    layer raises ``UnknownMissionTypeError``, even when the project carries
    other ``selected_*`` doctrine (the old project-wide tolerance signal)."""

    def test_typo_with_other_doctrine_present_raises(self, tmp_path: Path) -> None:
        _write_activation_config(tmp_path, ["software-dev"])
        _write_charter_with_other_doctrine(tmp_path)

        with pytest.raises(UnknownMissionTypeError) as exc_info:
            resolve_mission_type_context(tmp_path, mission_type="softwaer-dev")

        assert "softwaer-dev" in str(exc_info.value)


class TestAC5LayeredToleranceAtProjectOrOrgLayer:
    """AC-5 — an unregistered type whose per-type ``governance-profile.yaml``
    (matching ``id``) exists at project OR org resolves without error — one
    fixture per layer.

    (Rework, per operator ruling.) A third, built-in-layer sub-test was
    dropped: the only built-in profiles are the four activation-governed
    canonical types, so "tolerate via built-in profile alone" is not a valid
    tolerance case under this ruling — see
    ``TestBuiltInLayerAloneDoesNotOverrideActivationGate`` below for the
    negative pin that replaces it.
    """

    def test_tolerated_via_project_layer_profile(self, tmp_path: Path) -> None:
        _write_activation_config(tmp_path, ["software-dev"])
        _write_governance_profile(
            tmp_path / ".kittify" / "doctrine" / "mission_types" / "project-only-type",
            "project-only-type",
        )

        bundle = resolve_mission_type_context(tmp_path, mission_type="project-only-type")

        assert bundle.mission_type == "project-only-type"
        assert bundle.action_sequence == []

    def test_tolerated_via_org_layer_profile(self, tmp_path: Path) -> None:
        org_root = tmp_path / "org-pack"
        _write_governance_profile(org_root / "mission_types" / "org-only-type", "org-only-type")
        _write_org_pack_config(
            tmp_path,
            packs=[("acme", org_root)],
            activated_mission_types=["software-dev"],
        )

        bundle = resolve_mission_type_context(tmp_path, mission_type="org-only-type")

        assert bundle.mission_type == "org-only-type"
        assert bundle.action_sequence == []


class TestBuiltInLayerAloneDoesNotOverrideActivationGate:
    """Operator ruling (rework): the built-in layer is EXCLUDED from the
    AC-5 tolerance witness, so it cannot override the pre-existing FR-006
    mission-type activation-subset gate
    (``tests/charter/test_mission_type_activation_gating.py``, not owned by
    this WP — kept green, unchanged).

    ``research`` ships a built-in ``governance-profile.yaml`` but is NOT
    activated in this project's ``config.yaml`` and has no project/org
    override — ``is_registered=False`` AND no project/org tolerance witness,
    so it still hard-fails, exactly like a typo.
    """

    def test_non_activated_canonical_type_still_hard_fails(self, tmp_path: Path) -> None:
        _write_activation_config(tmp_path, ["software-dev"])

        with pytest.raises(UnknownMissionTypeError) as exc_info:
            resolve_mission_type_context(tmp_path, mission_type="research")

        assert "research" in str(exc_info.value)
        assert exc_info.value.registered_ids == ["software-dev"]
