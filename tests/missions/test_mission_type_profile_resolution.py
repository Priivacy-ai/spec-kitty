"""ATDD acceptance spec — mission-type governance profiles.

These tests are the executable specification for Mission B WP06 (the
original Mission B WP01–WP02 folded into the proposed scope):

    Ship one ``governance-profile.yaml`` per mission type
    (``software-dev``, ``documentation``, ``research``, ``plan``) under
    ``src/doctrine/missions/<type>/governance-profile.yaml``. Each
    profile declares default selections and default activations for that
    mission type. The charter resolver reads ``meta.json mission_type``,
    picks the matching profile, and unions its declarations into the
    project + org selections. No ``software-dev-default`` fallback for
    non-software missions — the resolver hard-fails when a mission's
    ``mission_type`` has no matching profile and the project has not
    declared its own.

See ``docs/development/mission-b-proposed-scope.md`` → WP06 and the
pre-flight's "Mission-type mismatch" edge case.

Expected status TODAY: every test FAILS — no ``governance-profile.yaml``
ships, the resolver has no loader, and the documentation mission
inherits ``software-dev-default`` content silently. Mission B WP06
ships all of these.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


_REPO_ROOT = Path(__file__).resolve().parents[2]
_MISSION_ROOT = _REPO_ROOT / "src" / "doctrine" / "missions"
_REQUIRED_MISSION_TYPES = ("software-dev", "documentation", "research", "plan")


# ---------------------------------------------------------------------------
# Test 1 — every required mission type ships a governance-profile.yaml
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mission_type", _REQUIRED_MISSION_TYPES)
def test_mission_type_ships_governance_profile_yaml(mission_type: str) -> None:
    """Each canonical mission type MUST ship a
    ``src/doctrine/missions/<type>/governance-profile.yaml`` file.

    Fails today because none of the four files exist. Mission B WP06
    creates them with mission-type-appropriate default selections.
    """
    expected = _MISSION_ROOT / mission_type / "governance-profile.yaml"
    assert expected.exists(), (
        f"Missing governance profile for mission_type `{mission_type}`. "
        f"Expected: {expected}\n"
        "Mission B WP06 must ship one profile per mission type. The profile "
        "declares default selections and activations for that mission type, "
        "and the charter context resolver unions them into project + org "
        "selections when a mission of that type runs. See "
        "docs/development/mission-b-proposed-scope.md → WP06."
    )


# ---------------------------------------------------------------------------
# Test 2 — the profile loader picks them up by mission_type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mission_type", _REQUIRED_MISSION_TYPES)
def test_load_profile_returns_mission_type_profile(mission_type: str) -> None:
    """``charter.mission_type_profiles.load_profile(mission_type)`` MUST
    return the profile for that mission type — not None, not a fallback.

    Fails today on ImportError. Mission B WP06 introduces the loader at
    this canonical import path. If WP06 chooses a different location,
    update this test (and the WP06 spec) to match.
    """
    try:
        from charter.mission_type_profiles import load_profile  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            "Could not import `charter.mission_type_profiles.load_profile`. "
            "Mission B WP06 must introduce the profile loader at this "
            "canonical import path. See mission-b-proposed-scope.md → WP06.\n"
            f"Underlying ImportError: {exc!r}"
        )

    profile = load_profile(mission_type)
    assert profile is not None, (
        f"load_profile({mission_type!r}) returned None. The loader MUST "
        f"return the shipped profile for `{mission_type}`. A None return "
        "would silently fall back to software-dev-default content, which "
        "is the documentation-vs-software-dev leak the spec forbids."
    )
    # Profile MUST expose its mission type so the resolver can sanity-check
    # the lookup.
    declared_type = getattr(profile, "mission_type", None)
    assert declared_type == mission_type, (
        f"Profile for `{mission_type}` declares mission_type=`{declared_type}`. "
        "The two must agree — otherwise the loader returned the wrong file."
    )


# ---------------------------------------------------------------------------
# Test 3 — resolve_mission_type_governance honours meta.json mission_type
# ---------------------------------------------------------------------------


def _git_init_minimal(repo_root: Path) -> None:
    subprocess.run(
        ["git", "init", "--initial-branch=main"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "atdd@example.com"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "ATDD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )


def _write_minimal_charter(repo_root: Path) -> None:
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    (charter_dir / "charter.md").write_text(
        "# Charter\n\n## Purpose\nTest charter.\n",
        encoding="utf-8",
    )


def test_resolve_governance_picks_documentation_profile_for_documentation_mission(
    tmp_path: Path,
) -> None:
    """A mission whose ``meta.json`` declares ``mission_type: documentation``
    MUST resolve a governance payload from the documentation profile —
    NOT the software-dev-default content. This is the precise leak the
    pre-flight's "Mission-type mismatch" edge case warns about.

    Fails today on ImportError or because no documentation profile exists.
    """
    try:
        from charter.mission_type_profiles import (  # type: ignore[import-not-found]
            resolve_mission_type_governance,
        )
    except ImportError as exc:
        pytest.fail(
            "Could not import `charter.mission_type_profiles.resolve_mission_type_governance`. "
            "Mission B WP06 must introduce the resolver that reads meta.json's "
            "mission_type and dispatches to the matching profile.\n"
            f"Underlying ImportError: {exc!r}"
        )

    repo_root = tmp_path
    _git_init_minimal(repo_root)
    _write_minimal_charter(repo_root)

    feature_dir = repo_root / "kitty-specs" / "documentation-mission-001"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_type": "documentation", "mission_slug": "documentation-mission-001"}),
        encoding="utf-8",
    )

    payload = resolve_mission_type_governance(repo_root, feature_dir)
    payload_text = getattr(payload, "text", str(payload))

    assert "software-dev-default" not in payload_text.lower(), (
        "Governance payload for a documentation mission MUST NOT include "
        "`software-dev-default` content. The mission_type leak is the exact "
        "failure mode Mission B WP06 prevents."
    )

    declared_mission_type = getattr(payload, "mission_type", None)
    assert declared_mission_type == "documentation", (
        f"resolve_mission_type_governance returned payload with mission_type="
        f"{declared_mission_type!r}; expected `documentation` (read from "
        "meta.json). If this fails the resolver is not honouring meta.json's "
        "mission_type at all — see WP06 spec."
    )


# ---------------------------------------------------------------------------
# Test 4 — unknown mission_type without project override hard-fails
# ---------------------------------------------------------------------------


def test_resolve_governance_hard_fails_for_unknown_mission_type(tmp_path: Path) -> None:
    """A mission whose ``mission_type`` matches no shipped profile and
    whose project has not declared an override MUST raise a clear error.
    Silent fallback to ``software-dev-default`` is the forbidden behaviour.

    Fails today on ImportError. After Mission B WP06: raises with a
    message naming the unknown mission_type.
    """
    try:
        from charter.mission_type_profiles import (  # type: ignore[import-not-found]
            resolve_mission_type_governance,
        )
    except ImportError as exc:
        pytest.fail(
            "Could not import `charter.mission_type_profiles.resolve_mission_type_governance`. "
            "Mission B WP06 must introduce the resolver.\n"
            f"Underlying ImportError: {exc!r}"
        )

    repo_root = tmp_path
    _git_init_minimal(repo_root)
    _write_minimal_charter(repo_root)

    feature_dir = repo_root / "kitty-specs" / "unknown-mission-001"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {"mission_type": "totally-made-up-mission-type", "mission_slug": "unknown-mission-001"}
        ),
        encoding="utf-8",
    )

    with pytest.raises(Exception) as excinfo:  # noqa: PT011 — accept any clear error class
        resolve_mission_type_governance(repo_root, feature_dir)

    assert "totally-made-up-mission-type" in str(excinfo.value), (
        "Hard-fail message MUST name the unknown mission_type so operators "
        "can diagnose the typo / missing profile. Observed exception text:\n"
        f"  {excinfo.value!r}"
    )


# ---------------------------------------------------------------------------
# Test 5 — profile shape: each shipped profile declares its mission_type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mission_type", _REQUIRED_MISSION_TYPES)
def test_profile_yaml_declares_its_mission_type(mission_type: str) -> None:
    """Each shipped ``governance-profile.yaml`` MUST declare a top-level
    ``mission_type:`` field whose value matches the directory it lives in.

    Pinning this prevents accidental directory / declaration mismatches
    (file lives under ``documentation/`` but declares ``mission_type:
    software-dev``), which would silently route documentation missions
    to software-dev governance.

    Fails today because the files do not exist.
    """
    from ruamel.yaml import YAML

    profile_path = _MISSION_ROOT / mission_type / "governance-profile.yaml"
    if not profile_path.exists():
        pytest.fail(
            f"Missing {profile_path} — see "
            "test_mission_type_ships_governance_profile_yaml for the gating "
            "test that pins the file existence."
        )
    data = YAML(typ="safe").load(profile_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), (
        f"{profile_path}: top level MUST be a YAML mapping."
    )
    declared = data.get("mission_type")
    assert declared == mission_type, (
        f"{profile_path}: top-level `mission_type` is `{declared!r}`; "
        f"expected `{mission_type}` to match the directory name. The two "
        "MUST agree or the resolver will route missions to the wrong profile."
    )
