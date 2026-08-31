"""Red-first regression test for #3810 — activate doctrine-daphne + randy-reducer.

The shipped charter pack (``src/charter/activation/packs/default.yaml``)
``activated_agent_profiles`` allowlist omitted ``doctrine-daphne`` and
``randy-reducer`` — the exact two lenses the ``adversarial-squad`` skill
hardcodes in its "Select 3-4 distinct profiles by lens" list
(``src/charter/offering/skills/adversarial-squad/SKILL.md``). A project that
adopts the shipped default pack verbatim therefore hits the FR-014 activation
gate (``spec-kitty profiles show <id>`` -> ``EXIT 1 "is not activated"``) for
both lenses, so a squad delegate profile-loading either one silently falls
back to unprofiled dispatch instead of failing loudly.

Covers:
- the shipped pack's ``activated_agent_profiles`` list includes both ids
  (direct read of ``default.yaml`` — no project-local override involved).
- every lens the adversarial-squad skill names is a subset of that list (the
  general contract, not just the two ids #3810 names).
- the FR-014 activation gate (``profiles show``) resolves both ids with
  ``exit_code == 0`` for a project that adopted the shipped defaults verbatim
  (no ``profile_not_activated``, no ``EXIT 1``).
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

import pytest
from ruamel.yaml import YAML
from typer.testing import CliRunner

from charter.activation.default_pack import load_default_pack_activation_ids
from specify_cli import app as cli_app

pytestmark = [pytest.mark.unit, pytest.mark.fast, pytest.mark.doctrine]

runner = CliRunner()

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SKILL_PATH = (
    _REPO_ROOT
    / "src"
    / "charter"
    / "offering"
    / "skills"
    / "adversarial-squad"
    / "SKILL.md"
)
# Matches lines like "  - `doctrine-daphne` — doctrine integrity / DRG wiring"
# in the skill's "Select 3-4 distinct profiles by lens" bullet list.
_LENS_LINE_RE = re.compile(r"^\s*-\s*`([a-z][a-z0-9-]*)`\s*—", re.MULTILINE)

# The two profiles #3810 reports as omitted from the shipped allowlist despite
# being squad lenses the adversarial-squad skill hardcodes.
_MISSING_LENSES = frozenset({"doctrine-daphne", "randy-reducer"})


def _squad_lens_ids() -> frozenset[str]:
    """Extract the lens profile ids from the skill's own "Select ... by lens" list.

    Reads the canonical skill body rather than re-hardcoding the id list here,
    so this test tracks the skill's real hardcoded lenses instead of drifting
    from them independently.
    """
    text = _SKILL_PATH.read_text(encoding="utf-8")
    ids = frozenset(_LENS_LINE_RE.findall(text))
    assert ids, f"expected to find lens ids in {_SKILL_PATH}"
    return ids


def _shipped_activated_agent_profiles() -> frozenset[str]:
    """Load ``activated_agent_profiles`` straight from the shipped default pack."""
    ids = load_default_pack_activation_ids().get("activated_agent_profiles", [])
    return frozenset(ids)


def test_squad_lens_ids_present_in_skill() -> None:
    """Sanity check: the extraction regex actually finds the two #3810 lenses."""
    assert _squad_lens_ids() >= _MISSING_LENSES


def test_missing_lenses_are_activated_in_shipped_default_pack() -> None:
    """#3810: doctrine-daphne + randy-reducer must be in the shipped allowlist."""
    activated = _shipped_activated_agent_profiles()
    missing = _MISSING_LENSES - activated
    assert not missing, (
        "src/charter/activation/packs/default.yaml activated_agent_profiles "
        f"is missing squad lens(es): {sorted(missing)}"
    )


def test_adversarial_squad_lenses_are_subset_of_activated_default_profiles() -> None:
    """Every lens the adversarial-squad skill names must resolve as activated."""
    activated = _shipped_activated_agent_profiles()
    lenses = _squad_lens_ids()
    missing = lenses - activated
    assert not missing, (
        "adversarial-squad skill names lens(es) absent from the shipped "
        f"activated_agent_profiles allowlist: {sorted(missing)}"
    )


def _write_shipped_default_config(repo_root: Path) -> None:
    """Write a ``.kittify/config.yaml`` whose activation state is the shipped pack.

    Simulates a project that adopted ``default.yaml``'s
    ``activated_agent_profiles`` verbatim (the common case: ``spec-kitty init``
    seeds config from this pack).
    """
    kittify = repo_root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    yaml = YAML()
    data = {"activated_agent_profiles": sorted(_shipped_activated_agent_profiles())}
    with (kittify / "config.yaml").open("w", encoding="utf-8") as fh:
        yaml.dump(data, fh)


@pytest.mark.parametrize("profile_id", sorted(_MISSING_LENSES))
def test_profiles_show_resolves_without_exit_1(profile_id: str, tmp_path: Path) -> None:
    """FR-014 activation gate: ``profiles show <id>`` must not exit 1 "not activated"."""
    _write_shipped_default_config(tmp_path)
    with patch(
        "specify_cli.cli.commands.profiles_cmd.find_repo_root", return_value=tmp_path
    ):
        result = runner.invoke(cli_app, ["profiles", "show", profile_id, "--json"])

    assert result.exit_code == 0, (
        f"expected profile '{profile_id}' to resolve as activated; got exit "
        f"{result.exit_code}: {result.output}"
    )
