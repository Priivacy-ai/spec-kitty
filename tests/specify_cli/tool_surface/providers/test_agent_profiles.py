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
    assert len(instances) > 1
    assert all(i.owner == "claude" for i in instances)
    assert all(i.path.suffix == ".md" for i in instances)


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
