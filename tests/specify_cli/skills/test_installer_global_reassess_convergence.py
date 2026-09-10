"""#4174 landing-pass Concern 3 (external-caller extension): apply_skill_installation
must converge on a concurrent-peer race, exactly like the three ``ensure_*``
global owners it dispatches through.

``bootstrap.ensure_runtime()`` (and its ``agent_commands.py`` /
``agent_skills.py`` mirrors) re-assess under the held lock before applying,
so a concurrent peer that already materialized the plan converges to a
no-op instead of replaying a stale, non-idempotent create-plan.
``skills/installer.py::apply_skill_installation`` is a DIRECT-CALL boundary
outside that ``ensure_*`` graph: it builds its own ``global_assets``
assessment, calls ``recheck_assets`` + ``apply_assets`` directly, and never
re-assesses. Two independent, concurrent installer invocations racing the
SAME cold home reproduce exactly the residual symptom the #4017 mission
notes recorded: the winner applies first and materializes the global
command bundle for real; the loser's OWN (now-stale) assessment still
carries "create" actions for paths the winner already created, and
``apply_assets`` replays them non-idempotently -- ``mkdir()`` raises
``FileExistsError`` ("File exists"), surfaced as a
``global_asset_write_failed`` diagnostic.

This module isolates the race to the GLOBAL side only (project skill
selection is empty, producing zero project effects, so
``recheck_project_skills`` never has state of its own to race on) and drives
the fix: ``apply_skill_installation`` gains an optional
``rebuild_global_assets`` callable that, mirroring
``asset_preparation.apply_with_reassess``, re-assesses the GLOBAL half
under the held lock and converges to a no-op when the peer already did the
work -- without touching the project half's own, unrelated
``recheck_project_skills`` boundary or its strict object-identity contract
with ``apply_project_skills``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.skills.installer import apply_skill_installation, assess_skill_installation
from specify_cli.skills.registry import SkillRegistry
from specify_cli.tool_surface.operations import ApplyConsent, AssessmentInputs, OperationRoot

pytestmark = [pytest.mark.unit, pytest.mark.fast]

GLOBAL_ASSET_WRITE_FAILED_SIGNAL = "global_asset_write_failed"


@pytest.fixture
def owner_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    for key in ("HOME", "USERPROFILE"):
        monkeypatch.setenv(key, str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))
    return home


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    return root


def _build(inputs: AssessmentInputs, registry: SkillRegistry):
    """Isolate the race to the GLOBAL commands family: an empty skill
    selection produces zero project effects, so the project half never has
    state of its own to race on.
    """
    return assess_skill_installation(
        inputs,
        registry,
        (),
        commands=True,
        command_agent_keys=["claude"],
        persist_manifest=False,
    )


class TestApplySkillInstallationConcurrentPeerConvergence:
    def test_without_rebuild_a_concurrent_peer_still_crashes_the_loser(
        self,
        owner_home: Path,
        project: Path,
    ) -> None:
        """RED (pins the pre-fix symptom): the loser's stale plan replays a
        non-idempotent mkdir against the winner's already-materialized tree.
        """
        consent = ApplyConsent(automatic=True)
        inputs = AssessmentInputs(OperationRoot("project", "project", project), consent=consent)
        registry = SkillRegistry.from_package()

        winner = _build(inputs, registry)
        loser = _build(inputs, registry)
        assert winner.global_assets.complete and winner.global_assets.effects
        assert loser.project_skills.complete and not loser.project_skills.effects, (
            "fixture must isolate the race to the global side -- project effects must be empty"
        )

        winner_results = apply_skill_installation(winner, consent)
        assert all(r.outcome in {"applied", "skipped"} for r in winner_results), winner_results

        loser_results = apply_skill_installation(loser, consent)

        assert any(r.outcome not in {"applied", "skipped"} for r in loser_results), f"expected the pre-fix crash on a concurrent peer, got: {loser_results!r}"
        messages = " ".join(d.message for r in loser_results for d in r.diagnostics)
        assert GLOBAL_ASSET_WRITE_FAILED_SIGNAL in messages or "File exists" in messages, messages

    def test_with_rebuild_a_concurrent_peer_converges_to_a_no_op(
        self,
        owner_home: Path,
        project: Path,
    ) -> None:
        """GREEN: passing rebuild_global_assets converges the loser instead
        of replaying its stale plan.
        """
        consent = ApplyConsent(automatic=True)
        inputs = AssessmentInputs(OperationRoot("project", "project", project), consent=consent)
        registry = SkillRegistry.from_package()

        winner = _build(inputs, registry)
        loser = _build(inputs, registry)

        winner_results = apply_skill_installation(winner, consent)
        assert all(r.outcome in {"applied", "skipped"} for r in winner_results), winner_results

        loser_results = apply_skill_installation(
            loser,
            consent,
            rebuild_global_assets=lambda: _build(inputs, registry).global_assets,
        )

        assert all(r.outcome in {"applied", "skipped"} for r in loser_results), loser_results

    def test_rebuild_is_never_invoked_on_a_genuinely_cold_install(
        self,
        owner_home: Path,
        project: Path,
    ) -> None:
        """The warm/no-race fast path must not be perturbed: on a genuinely
        cold, uncontested install, ``rebuild_global_assets`` still converges
        (there is no peer, so the SECOND assess -- taken under the lock --
        will just be another equally-cold plan, applied normally).
        """
        consent = ApplyConsent(automatic=True)
        inputs = AssessmentInputs(OperationRoot("project", "project", project), consent=consent)
        registry = SkillRegistry.from_package()

        calls = {"n": 0}

        def _counting_rebuild():
            calls["n"] += 1
            return _build(inputs, registry).global_assets

        installation = _build(inputs, registry)
        results = apply_skill_installation(installation, consent, rebuild_global_assets=_counting_rebuild)

        assert all(r.outcome in {"applied", "skipped"} for r in results), results
        assert calls["n"] == 1, "rebuild must run exactly once under the held lock on a genuinely cold install"
