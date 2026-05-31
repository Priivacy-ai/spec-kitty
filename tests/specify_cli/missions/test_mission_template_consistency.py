"""Global consistency guard for packaged mission prompt templates.

Every step in a packaged ``mission-runtime.yaml`` declares a ``prompt_template``
(or ``None``). At runtime, ``spec-kitty next`` resolves that template one of two
ways:

1. **Composition-driven** -- the step's action is dispatched through
   ``StepContractExecutor`` composition (see
   ``runtime_bridge._COMPOSED_ACTIONS_BY_MISSION``). These steps never read a
   file from ``command-templates/``; the built-in step contracts under
   ``src/doctrine/missions/built_in_step_contracts/`` are authoritative.
2. **Command-template-driven** -- the step's action falls through to
   ``prompt_builder._build_template_prompt`` which calls
   ``resolve_command(f"{action}.md", ..., mission=<mission>)``. The packaged
   tier (Tier 5) of that resolver is
   ``specify_cli/missions/<mission>/command-templates/<name>``, so the file MUST
   exist in the mission's packaged ``command-templates/`` directory or a fresh
   install raises ``FileNotFoundError`` and ``spec-kitty next`` blocks.

This test asserts that every command-template-driven step has its
``prompt_template`` materialized in the packaged ``command-templates/`` for its
mission. It is the regression guard for the missing ``software-dev/accept.md``
bug: before that file existed, the ``accept`` step (which is NOT a composed
action) had no packaged template and ``spec-kitty next`` failed resolving the
accept prompt.

Genuinely CLI-driven steps that intentionally do not ship a packaged template
must be added to ``KNOWN_CLI_DRIVEN`` with a documented reason so the gap is
explicit rather than silent.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.next._internal_runtime.schema import load_mission_template_file
from specify_cli.next.runtime_bridge import _COMPOSED_ACTIONS_BY_MISSION

pytestmark = pytest.mark.fast


_REPO_ROOT = Path(__file__).resolve().parents[3]
_MISSIONS_ROOT = _REPO_ROOT / "src" / "specify_cli" / "missions"


# (mission_key, prompt_template) pairs that are intentionally CLI-driven and do
# NOT ship a packaged command-template. Each entry must carry a reason. Entries
# here are KNOWN GAPS: the runtime currently has no packaged template for them,
# so adding one (or routing them through composition) is tracked separately.
#
# NOTE: ``software-dev`` -> ``accept.md`` is deliberately NOT listed here. The
# software-dev accept step resolves a packaged command-template and must ship
# ``command-templates/accept.md``; allow-listing it would mask the very
# regression this test exists to catch.
KNOWN_CLI_DRIVEN: dict[tuple[str, str], str] = {
    # research/documentation declare an ``accept`` step but ship no
    # ``command-templates/`` directory. The runtime currently raises
    # FileNotFoundError when resolving these accept prompts (latent bug tracked
    # separately; see risks). They are allow-listed here ONLY so this guard can
    # still assert the software-dev contract without conflating the two gaps.
    ("research", "accept.md"): (
        "research mission ships no packaged command-templates/; accept prompt "
        "resolution is a known latent gap tracked separately"
    ),
    ("documentation", "accept.md"): (
        "documentation mission ships no packaged command-templates/; accept "
        "prompt resolution is a known latent gap tracked separately"
    ),
}


def _packaged_missions() -> list[Path]:
    """Return every packaged mission directory that ships a runtime YAML."""
    missions: list[Path] = []
    for child in sorted(_MISSIONS_ROOT.iterdir()):
        if not child.is_dir():
            continue
        if (child / "mission-runtime.yaml").is_file():
            missions.append(child)
    return missions


def _mission_keys() -> list[str]:
    return [m.name for m in _packaged_missions()]


def test_packaged_missions_discovered() -> None:
    """Sanity: the loader sees the shipped missions, including software-dev."""
    keys = _mission_keys()
    assert keys, "no packaged missions with mission-runtime.yaml were discovered"
    assert "software-dev" in keys


@pytest.mark.parametrize("mission_dir", _packaged_missions(), ids=_mission_keys())
def test_every_prompt_template_is_resolvable(mission_dir: Path) -> None:
    """Each step's ``prompt_template`` is composed, packaged, or allow-listed.

    A non-composed step whose ``prompt_template`` is neither present in the
    mission's packaged ``command-templates/`` nor explicitly allow-listed as
    CLI-driven would cause ``spec-kitty next`` to fail resolving that prompt on
    a fresh install. That is exactly the ``software-dev/accept.md`` regression.
    """
    runtime_path = mission_dir / "mission-runtime.yaml"
    template = load_mission_template_file(runtime_path)
    mission_key = template.mission.key

    command_templates_dir = mission_dir / "command-templates"
    composed_actions = _COMPOSED_ACTIONS_BY_MISSION.get(mission_key, frozenset())

    problems: list[str] = []
    for step in template.steps:
        prompt_template = step.prompt_template
        if not prompt_template:
            # Steps without a prompt_template carry no template contract.
            continue

        # Composition-driven steps never read command-templates/.
        if step.id in composed_actions:
            continue

        # Explicitly allow-listed CLI-driven steps.
        if (mission_key, prompt_template) in KNOWN_CLI_DRIVEN:
            continue

        # Otherwise the template MUST exist in the packaged command-templates/.
        candidate = command_templates_dir / prompt_template
        if not candidate.is_file():
            problems.append(
                f"mission '{mission_key}' step '{step.id}' references "
                f"prompt_template '{prompt_template}' but no packaged template "
                f"exists at {candidate} (and the step is neither a composed "
                f"action nor allow-listed in KNOWN_CLI_DRIVEN). "
                f"spec-kitty next will fail resolving this prompt."
            )

    assert not problems, "\n".join(problems)


def test_software_dev_accept_template_exists() -> None:
    """Regression: the software-dev accept step ships a packaged template.

    The ``accept`` step is not a composed action, so the runtime resolves it via
    ``resolve_command('accept.md', ..., mission='software-dev')`` whose packaged
    tier is ``missions/software-dev/command-templates/accept.md``. This file was
    missing, so a fresh install blocked at the accept step.
    """
    accept_template = (
        _MISSIONS_ROOT / "software-dev" / "command-templates" / "accept.md"
    )
    assert accept_template.is_file(), (
        f"software-dev accept template missing at {accept_template}; "
        "spec-kitty next cannot resolve the accept prompt without it."
    )
    # Must not be empty and should target the acceptance command.
    body = accept_template.read_text(encoding="utf-8")
    assert body.strip(), "accept.md is empty"
    assert "spec-kitty accept" in body, (
        "accept.md should instruct the operator to run 'spec-kitty accept'"
    )


def test_software_dev_accept_resolves_from_clean_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``resolve_command`` finds software-dev/accept.md at the packaged tier.

    With no project-local overrides, resolution must fall through to the
    packaged ``command-templates/accept.md``. Before the fix this raised
    ``FileNotFoundError``.

    The global runtime tier (``GLOBAL_MISSION`` --
    ``<kittify-home>/missions/software-dev/command-templates/accept.md``) is
    consulted *before* ``PACKAGE_DEFAULT``. ``get_kittify_home()`` lets
    ``SPEC_KITTY_HOME`` win unconditionally, so we pin it at an empty temp dir;
    otherwise a developer/CI machine with a populated ``~/.kittify`` would
    resolve at ``GLOBAL_MISSION`` and this assertion would be environment-coupled.
    """
    from specify_cli.runtime.resolver import ResolutionTier, resolve_command

    empty_home = tmp_path / "kittify-home"
    empty_home.mkdir()
    monkeypatch.setenv("SPEC_KITTY_HOME", str(empty_home))

    project_dir = tmp_path / "clean-project"
    project_dir.mkdir()

    result = resolve_command("accept.md", project_dir, mission="software-dev")
    assert result.tier == ResolutionTier.PACKAGE_DEFAULT
    assert result.path.name == "accept.md"
    assert result.path.is_file()
