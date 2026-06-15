"""Unit tests for ``tool_surface.providers.agent_profiles``."""

from __future__ import annotations

from pathlib import Path

from doctrine.agent_profiles.repository import AgentProfileRepository
from specify_cli.tool_surface.profiles.manifest import (
    ProfileManifest,
    manifest_path_for,
)
from specify_cli.tool_surface.profiles.projection import ProfileProjector
from specify_cli.tool_surface.providers.agent_profiles import (
    AgentProfilesProvider,
    agent_profile_definition,
)
from specify_cli.tool_surface.providers.command_skills import (
    command_skill_definition,
)
from specify_cli.tool_surface.providers.protocol import ReportingSurfaceProvider
from specify_cli.tool_surface.status import (
    STATE_DRIFTED,
    STATE_MISSING,
    STATE_NOT_APPLICABLE,
    STATE_PRESENT,
    SurfaceStatus,
    _surface_id,
)

import pytest

pytestmark = [pytest.mark.unit]


def _provider(tmp_path: Path) -> AgentProfilesProvider:
    repo = AgentProfileRepository()
    return AgentProfilesProvider(
        projector=ProfileProjector(repo),
        manifest=ProfileManifest.load(tmp_path),
    )


def test_provider_satisfies_reporting_protocol() -> None:
    assert isinstance(AgentProfilesProvider(), ReportingSurfaceProvider)
    assert AgentProfilesProvider().provider_key == "agent_profiles"


def test_can_handle_only_agent_profile() -> None:
    provider = AgentProfilesProvider()
    assert provider.can_handle(agent_profile_definition()) is True
    assert provider.can_handle(command_skill_definition()) is False


def test_expand_supported_tool_yields_profiles(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    instances = provider.expand(agent_profile_definition(), "claude", tmp_path)
    # The trailing diagnostics sentinel is not a projected profile file; scope the
    # markdown-suffix invariant to the projected-profile instances.
    profile_instances = [
        i
        for i in instances
        if not (i.surface_id and i.surface_id.endswith("<profile-diagnostics>"))
    ]
    assert len(profile_instances) > 1
    assert all(i.owner == "claude" for i in instances)
    assert all(i.path.suffix == ".md" for i in profile_instances)


def test_agent_profiles_provider_research_gap_for_unsupported_tool(
    tmp_path: Path,
) -> None:
    provider = _provider(tmp_path)
    instances = provider.expand(agent_profile_definition(), "codex", tmp_path)
    assert len(instances) == 1
    status = provider.probe(instances[0])
    assert status.state == STATE_NOT_APPLICABLE
    assert status.findings[0].code == "research-gap-surface"
    assert status.findings[0].severity == "info"


def test_probe_missing_is_error(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    instance = provider.expand(agent_profile_definition(), "claude", tmp_path)[0]
    status = provider.probe(instance)
    assert status.state == STATE_MISSING
    assert status.findings[0].code == "native-agent-profile-missing"
    assert status.findings[0].severity == "error"
    assert status.findings[0].repair_command is not None


def test_probe_present(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    instance = provider.expand(agent_profile_definition(), "claude", tmp_path)[0]
    instance.path.parent.mkdir(parents=True, exist_ok=True)
    instance.path.write_text("content", encoding="utf-8")
    # No manifest hash recorded -> present once the file exists.
    status = provider.probe(instance)
    assert status.state == STATE_PRESENT
    assert status.findings == ()


def test_probe_drift_is_warning(tmp_path: Path) -> None:
    from dataclasses import replace

    provider = _provider(tmp_path)
    instance = provider.expand(agent_profile_definition(), "claude", tmp_path)[0]
    instance.path.parent.mkdir(parents=True, exist_ok=True)
    instance.path.write_text("real content", encoding="utf-8")
    drifted = replace(instance, exists=True, file_hash="deadbeef" * 8)
    status = provider.probe(drifted)
    assert status.state == STATE_DRIFTED
    assert status.findings[0].code == "native-agent-profile-drift"
    assert status.findings[0].severity == "warning"


def test_agent_profiles_provider_repair_writes_file(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    instance = provider.expand(agent_profile_definition(), "claude", tmp_path)[0]
    missing = provider.probe(instance)
    assert missing.state == STATE_MISSING

    result = provider.repair(tmp_path, [missing])
    assert result.failed == ()
    assert len(result.repaired) == 1
    assert instance.path.exists()
    assert "name:" in instance.path.read_text(encoding="utf-8")
    # Manifest now records a hash for the written file.
    assert manifest_path_for(tmp_path).exists()
    reloaded = ProfileManifest.load(tmp_path)
    assert reloaded.get_hash(instance.path) is not None


def test_repair_dry_run_writes_nothing(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    instance = provider.expand(agent_profile_definition(), "claude", tmp_path)[0]
    missing = provider.probe(instance)
    result = provider.repair(tmp_path, [missing], dry_run=True)
    assert result.dry_run is True
    assert result.repaired == (_surface_id(missing.instance),)
    assert not instance.path.exists()


def test_repair_research_gap_is_skipped(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    gap_instance = provider.expand(agent_profile_definition(), "codex", tmp_path)[0]
    gap_status = provider.probe(gap_instance)
    result = provider.repair(tmp_path, [gap_status])
    assert result.repaired == ()
    assert len(result.skipped) == 1


def test_repair_unsupported_status_provider_marks_skip(tmp_path: Path) -> None:
    """A status whose instance has no projection is skipped, not repaired."""
    provider = _provider(tmp_path)
    gap_instance = provider.expand(agent_profile_definition(), "codex", tmp_path)[0]
    # Force a non-applicable status object through repair to exercise the skip
    # branch deterministically.
    status = SurfaceStatus(instance=gap_instance, state=STATE_NOT_APPLICABLE)
    result = provider.repair(tmp_path, [status])
    assert result.repaired == ()
    assert _surface_id(gap_instance) in result.skipped


def test_expand_appends_diagnostics_instance_for_supported_tool(
    tmp_path: Path,
) -> None:
    """A supported tool's expansion includes the diagnostics sentinel."""
    provider = _provider(tmp_path)
    instances = provider.expand(agent_profile_definition(), "claude", tmp_path)
    diagnostics = [
        i
        for i in instances
        if i.surface_id and i.surface_id.endswith("<profile-diagnostics>")
    ]
    assert len(diagnostics) == 1
    assert diagnostics[0].owner == "claude"


def test_probe_diagnostics_instance_emits_profile_finding_codes(
    tmp_path: Path,
) -> None:
    """Probing the diagnostics sentinel surfaces ProfileProjector.diagnose codes.

    The built-in profile repository ships at least one sentinel profile, so
    ``profile-sentinel-skipped`` (info) is emitted unconditionally for a
    supported tool -- proving the provider invokes ``diagnose`` rather than
    leaving it dead code.
    """
    provider = _provider(tmp_path)
    instances = provider.expand(agent_profile_definition(), "claude", tmp_path)
    diagnostics = next(
        i
        for i in instances
        if i.surface_id and i.surface_id.endswith("<profile-diagnostics>")
    )
    status = provider.probe(diagnostics)
    assert status.state == STATE_NOT_APPLICABLE
    codes = {f.code for f in status.findings}
    assert "profile-sentinel-skipped" in codes
    sentinel_findings = [
        f for f in status.findings if f.code == "profile-sentinel-skipped"
    ]
    assert sentinel_findings
    assert all(f.severity == "info" for f in sentinel_findings)


def test_provider_invokes_projector_diagnose() -> None:
    """Guard: the provider source actually calls ``projector.diagnose``.

    A grep-level assertion that catches a regression where the wiring is removed
    and ``diagnose`` reverts to dead code (the cycle-1 rejection condition).
    """
    import specify_cli.tool_surface.providers.agent_profiles as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "projector.diagnose(" in source


def test_diagnose_code_reaches_doctor_tool_surfaces_json(tmp_path: Path) -> None:
    """End-to-end: ``run_tool_surfaces`` (the doctor CLI delegate) surfaces a
    profile diagnostic code in its JSON ``findings`` for ``--kind agent-profile``.

    This exercises the full live service assembly the ``doctor tool-surfaces``
    command uses (build_providers -> build_registry -> SurfacePlanBuilder ->
    SurfaceStatusService.collect), not ``diagnose`` in isolation, satisfying the
    WP02 DoD that the new codes reach ``doctor tool-surfaces --json`` output.
    """
    from specify_cli.tool_surface.service import (
        run_tool_surfaces,
        surface_kind_from_token,
    )

    outcome = run_tool_surfaces(
        tmp_path,
        ["claude"],
        kinds=[surface_kind_from_token("agent-profile")],
    )
    # The assembled report is the object the CLI serializes to ``--json``.
    report_codes = {finding.code for finding in outcome.report.findings}
    assert "profile-sentinel-skipped" in report_codes
    # And it survives JSON serialization into the ``findings`` payload the
    # operator sees from ``doctor tool-surfaces --kind agent-profile --json``.
    payload = outcome.to_json()
    findings = payload["findings"]
    assert isinstance(findings, list)
    json_codes = {finding["code"] for finding in findings}
    assert "profile-sentinel-skipped" in json_codes
