"""Routing regression for the shipped writing-comms agent profiles (FR-005, NFR-002, SC-004).

Non-fakeable form (contracts/routing-behavior.md): the registry is populated from the
**real shipped** ``packs/built-in/agent_profiles/`` YAML — not a ``MagicMock`` and not the
router-test ``FIXTURES_DIR`` stubs. A mock hand-feeds ``role``/``priority`` and would pass
regardless of the shipped YAML; copying the shipped files into the project layer of a real
``ProfileRegistry`` pins the narrowed YAML, so each scenario also asserts the shipped
``profile.role`` (e.g. ``diagram-daisy.role == "diagram-author"``).

The two negative regressions (R-1 DESIGNER, R-2 CURATOR) are RED on the relocated-but-not-
narrowed tree (``roles[0]`` still ``designer``/``curator``) and GREEN after the T004 role
narrowing removes the writing-comms profiles from those canonical-verb buckets.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from specify_cli.invocation.registry import ProfileRegistry
from specify_cli.invocation.router import ActionRouter

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# Worktree root: tests/specify_cli/invocation/<this file> → parents[3].
REPO_ROOT = Path(__file__).resolve().parents[3]
SHIPPED_PROFILES_DIR = REPO_ROOT / "packs" / "built-in" / "agent_profiles"


@pytest.fixture()
def shipped_registry(tmp_path: Path) -> ProfileRegistry:
    """A real ``ProfileRegistry`` populated from the shipped ``packs/built-in`` YAML.

    The shipped ``*.agent.yaml`` files are copied into the ungated ``.kittify/profiles``
    project layer so the registry reflects exactly the YAML this WP authored in the
    worktree (not an installed-package copy, and not a fixture stub).
    """
    project_profiles_dir = tmp_path / ".kittify" / "profiles"
    project_profiles_dir.mkdir(parents=True)
    shipped = sorted(SHIPPED_PROFILES_DIR.glob("*.agent.yaml"))
    assert shipped, f"No shipped profiles found under {SHIPPED_PROFILES_DIR}"
    for src in shipped:
        shutil.copy(src, project_profiles_dir / src.name)
    return ProfileRegistry(tmp_path)


# ---------------------------------------------------------------------------
# Shipped-registry loading (required by contracts/routing-behavior.md)
# ---------------------------------------------------------------------------


def test_registry_loaded_shipped_writing_comms_profiles(shipped_registry: ProfileRegistry) -> None:
    """The registry actually loaded the three colliding profiles from packs/built-in."""
    for profile_id in ("diagram-daisy", "comms-cleo", "synthesizer-sam"):
        assert shipped_registry.get(profile_id) is not None, (
            f"Profile '{profile_id}' was not loaded from {SHIPPED_PROFILES_DIR}"
        )


@pytest.mark.parametrize(
    "profile_id,expected_role",
    [
        ("diagram-daisy", "diagram-author"),
        ("comms-cleo", "communicator"),
        ("synthesizer-sam", "synthesizer"),
    ],
)
def test_shipped_primary_roles_are_narrowed(
    shipped_registry: ProfileRegistry, profile_id: str, expected_role: str
) -> None:
    """Each colliding profile's shipped ``roles[0]`` was narrowed off the generic bucket.

    RED-first: on the relocated-but-not-narrowed tree these are still ``designer``/``curator``.
    """
    profile = shipped_registry.get(profile_id)
    assert profile is not None
    assert profile.role == expected_role, (
        f"{profile_id}.role is {profile.role!r}, expected {expected_role!r}"
    )


# ---------------------------------------------------------------------------
# R-1 — incumbent DESIGNER preserved (negative regression; RED-first)
# ---------------------------------------------------------------------------


def test_bare_design_verb_routes_to_incumbent_designer(shipped_registry: ProfileRegistry) -> None:
    """A bare DESIGNER verb with no context selects designer-dagmar, not diagram-daisy.

    ``wireframe`` is a DESIGNER canonical verb (CANONICAL_VERB_MAP) and — unlike the
    generic ``design`` token, which architect-alphonso also carries as a canonical verb
    at equal priority — it is unique to designer-dagmar across the shipped set, so the
    incumbent wins cleanly once diagram-daisy leaves the DESIGNER bucket.
    RED before narrowing (diagram-daisy@60 still role ``designer`` beats dagmar@50).
    """
    decision = ActionRouter(shipped_registry).route("wireframe the login screen")
    assert decision.profile_id == "designer-dagmar"
    assert decision.profile_id != "diagram-daisy"


# ---------------------------------------------------------------------------
# R-2 — incumbent CURATOR preserved (negative regression; RED-first)
# ---------------------------------------------------------------------------


def test_bare_classify_verb_routes_to_incumbent_curator(shipped_registry: ProfileRegistry) -> None:
    """A bare CURATOR verb with no context selects an incumbent curator, not cleo/sam.

    ``organize`` is a CURATOR canonical verb (CANONICAL_VERB_MAP) unique to curator-carla
    across the shipped set — unlike ``classify``, which paula-patterns (architecture-scout,
    priority 65) also carries as a canonical verb and would win via the L3 keyword signal.
    RED before narrowing (comms-cleo@55 role ``curator`` beats doctrine-daphne@48/carla@40).
    """
    decision = ActionRouter(shipped_registry).route("organize these documents")
    assert decision.profile_id in {"curator-carla", "doctrine-daphne"}
    assert decision.profile_id not in {"comms-cleo", "synthesizer-sam"}


# ---------------------------------------------------------------------------
# R-3 — narrowed profile still routes for its own scope (positive guard)
# ---------------------------------------------------------------------------


def test_diagram_as_code_still_routes_to_diagram_daisy(shipped_registry: ProfileRegistry) -> None:
    """A diagram-as-code request still selects diagram-daisy (narrowing did not strand it).

    ``chart`` is a diagram-daisy domain-specific canonical verb (folded into the L3
    keyword signal); it is unique to diagram-daisy across the shipped set.
    """
    decision = ActionRouter(shipped_registry).route("chart the deployment topology")
    assert decision.profile_id == "diagram-daisy"


def test_diagram_daisy_selectable_by_profile_hint(shipped_registry: ProfileRegistry) -> None:
    """The explicit profile hint still resolves diagram-daisy after narrowing."""
    decision = ActionRouter(shipped_registry).route(
        "produce a C4 container diagram", profile_hint="diagram-daisy"
    )
    assert decision.profile_id == "diagram-daisy"


# ---------------------------------------------------------------------------
# R-5 — researcher non-collision (positive documentation; SC-004)
# ---------------------------------------------------------------------------


def test_bare_researcher_verb_routes_to_incumbent_researcher(
    shipped_registry: ProfileRegistry,
) -> None:
    """A bare researcher verb selects researcher-robbie.

    comms-cleo/synthesizer-sam carry ``researcher`` only as a *secondary* role, so
    ``profile.role`` (``roles[0]``) never enters the RESEARCHER bucket — the D-03 sharpening.
    """
    decision = ActionRouter(shipped_registry).route("research the market landscape")
    assert decision.profile_id == "researcher-robbie"
    assert decision.profile_id not in {"comms-cleo", "synthesizer-sam"}
