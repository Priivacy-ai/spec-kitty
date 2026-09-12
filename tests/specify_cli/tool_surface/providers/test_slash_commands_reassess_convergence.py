"""#4174 landing-pass Concern 3 (external-caller extension): SlashCommandsProvider
must converge on a concurrent-peer race, exactly like the three ``ensure_*``
global owners it wraps.

``SlashCommandsProvider.recheck``/``apply`` are dispatched through
``tool_surface/repair.py``'s generic ``_apply_assessment`` (via
``SurfaceRepairService.apply_assessments``), which calls ``recheck()`` then
``apply()`` on the SAME stale assessment object -- there was no re-assess
seam here either, so two independent, concurrent repair-service invocations
racing the same cold home reproduce the identical residual symptom
Concern 3's other two external callers had: the winner applies first and
materializes the global command bundle for real; the loser's own (now-stale)
assessment still carries "create" actions for paths the winner already
created, replayed non-idempotently by ``apply_assets`` as a
``global_asset_write_failed: File exists``.

The fix threads an internal rebuild callable derived purely from the STALE
assessment's own effects (``logical_owners``, set by ``assess()`` from the
selected agent keys) -- never the original ``inputs``/``selections``, which
``apply()`` never receives -- through
``asset_preparation.apply_with_reassess``. Because ``repair.py``'s
``_apply_assessment`` enforces a stricter contract than the ``ensure_*``
owners (every id in the ORIGINAL assessment's effects must be reported in
the ``OwnerApplyResult``, or it downgrades to a ``failed``
``unreported_effects`` diagnostic), the converged-no-op result is remapped
to report those original ids as ``skipped`` before returning.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.tool_surface.model import SurfacePlan
from specify_cli.tool_surface.operations import ApplyConsent, AssessmentInputs, OperationRoot
from specify_cli.tool_surface.providers.slash_commands import SlashCommandsProvider, slash_command_definition
from specify_cli.tool_surface.repair import SurfaceRepairService

pytestmark = [pytest.mark.unit, pytest.mark.fast]

GLOBAL_ASSET_WRITE_FAILED_SIGNAL = "global_asset_write_failed"
UNREPORTED_EFFECTS_SIGNAL = "unreported_effects"


@pytest.fixture
def owner_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    for key in ("HOME", "USERPROFILE"):
        monkeypatch.setenv(key, str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))
    return home


def _assess(project: Path):
    inputs = AssessmentInputs(OperationRoot("project", "project", project))
    definition = slash_command_definition()
    service = SurfaceRepairService((SlashCommandsProvider(),))
    plans = (SurfacePlan("claude", (), "T1", (definition,)),)
    assessments = service.assess(inputs, (), plans=plans)
    assert len(assessments) == 1
    return service, assessments[0]


class TestSlashCommandsProviderConcurrentPeerConvergence:
    def test_loser_converges_instead_of_crashing_on_a_concurrent_peer(
        self,
        owner_home: Path,
        tmp_path: Path,
    ) -> None:
        project = tmp_path / "project"
        project.mkdir()
        winner_service, winner_assessment = _assess(project)
        loser_service, loser_assessment = _assess(project)
        assert winner_assessment.complete and winner_assessment.effects
        assert loser_assessment.complete and loser_assessment.effects

        consent = ApplyConsent(automatic=True)
        winner_results = winner_service.apply_assessments((winner_assessment,), consent)
        assert len(winner_results) == 1 and winner_results[0].outcome == "applied", winner_results

        loser_results = loser_service.apply_assessments((loser_assessment,), consent)

        assert len(loser_results) == 1
        result = loser_results[0]
        assert result.outcome in {"applied", "skipped"}, (
            f"expected the loser to converge instead of crashing on the winner's already-materialized tree, got: {result!r}"
        )
        messages = " ".join(d.message for d in result.diagnostics)
        assert GLOBAL_ASSET_WRITE_FAILED_SIGNAL not in messages
        assert UNREPORTED_EFFECTS_SIGNAL not in messages, (
            "the converged result must report every ORIGINAL id (as skipped), satisfying repair.py's stricter id-accounting contract"
        )
        original_ids = {effect.id for effect in loser_assessment.effects}
        reported = set(result.succeeded + result.failed + result.skipped)
        assert original_ids <= reported, "every id from the original stale assessment must be accounted for"
