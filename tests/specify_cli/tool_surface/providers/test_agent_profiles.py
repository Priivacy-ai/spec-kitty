"""Unit tests for ``tool_surface.providers.agent_profiles``."""

from __future__ import annotations

from pathlib import Path

import pytest

from doctrine.agent_profiles.repository import AgentProfileRepository
from specify_cli.tool_surface.profiles.manifest import (
    PROJECTION_VERSION,
    ProfileManifest,
    manifest_path_for,
)
from specify_cli.tool_surface.profiles.projection import ProfileProjector
from specify_cli.tool_surface.model import SurfaceInstance
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

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _provider(tmp_path: Path) -> AgentProfilesProvider:
    repo = AgentProfileRepository()
    return AgentProfilesProvider(
        projector=ProfileProjector(repo),
        manifest=ProfileManifest.load(tmp_path),
    )


_DIAGNOSTICS_SENTINEL_SUFFIX = "<profile-diagnostics>"


def _real_profiles(instances: list[SurfaceInstance]) -> list[SurfaceInstance]:
    """Keep only real projected-profile instances.

    Drops the #1940 ``<profile-diagnostics>`` sentinel that ``expand`` appends to
    carry ``ProfileProjector.diagnose`` findings — it is not a projected profile
    file, so per-renderer path/suffix invariants must not assert over it.
    """
    return [
        i
        for i in instances
        if not (i.surface_id and i.surface_id.endswith(_DIAGNOSTICS_SENTINEL_SUFFIX))
    ]


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
        if not (i.surface_id and i.surface_id.endswith(_DIAGNOSTICS_SENTINEL_SUFFIX))
    ]
    assert len(profile_instances) > 1
    assert all(i.owner == "claude" for i in instances)
    assert all(i.path.suffix == ".md" for i in profile_instances)


# ---------------------------------------------------------------------------
# Capability matrix integration: codex now has a renderer (WP02)
# ---------------------------------------------------------------------------


def test_codex_expands_to_real_profiles(tmp_path: Path) -> None:
    """After WP02, codex has a real renderer and projects actual profiles."""
    provider = _provider(tmp_path)
    instances = _real_profiles(provider.expand(agent_profile_definition(), "codex", tmp_path))
    # Must yield at least one real profile instance (not a sentinel).
    assert len(instances) >= 1
    assert all(i.owner == "codex" for i in instances)
    # All paths should be inside .codex/agents/ with .toml suffix.
    assert all(i.path.suffix == ".toml" for i in instances)


# ---------------------------------------------------------------------------
# Capability matrix integration: not-applicable harnesses (WP03)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "harness_key",
    ["windsurf", "cursor", "gemini", "qwen", "opencode", "kilocode", "vibe", "pi", "letta"],
)
def test_not_applicable_harnesses_yield_not_applicable_status(
    harness_key: str, tmp_path: Path
) -> None:
    provider = _provider(tmp_path)
    instances = provider.expand(agent_profile_definition(), harness_key, tmp_path)
    assert len(instances) == 1
    status = provider.probe(instances[0])
    assert status.state == STATE_NOT_APPLICABLE
    assert status.findings[0].code == "profile-projection-unsupported"
    assert status.findings[0].severity == "info"
    assert status.findings[0].details.get("status") == "not_applicable"


def test_not_applicable_finding_includes_reason(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    instances = provider.expand(agent_profile_definition(), "windsurf", tmp_path)
    status = provider.probe(instances[0])
    reason = status.findings[0].details.get("reason", "")
    assert reason, "not_applicable finding must include a non-empty reason"


def test_not_applicable_harness_is_skipped_by_repair(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    na_instance = provider.expand(agent_profile_definition(), "windsurf", tmp_path)[0]
    na_status = provider.probe(na_instance)
    assert na_status.state == STATE_NOT_APPLICABLE
    result = provider.repair(tmp_path, [na_status])
    assert result.repaired == ()
    assert len(result.skipped) == 1


# ---------------------------------------------------------------------------
# Research-gap harness (unknown / unassessed)
# ---------------------------------------------------------------------------


def test_research_gap_for_unknown_tool(tmp_path: Path) -> None:
    """A tool not in AI_CHOICES or the capability matrix yields research_gap."""
    provider = _provider(tmp_path)
    instances = provider.expand(
        agent_profile_definition(), "unknown_tool_xyz", tmp_path
    )
    assert len(instances) == 1
    status = provider.probe(instances[0])
    assert status.state == STATE_NOT_APPLICABLE
    assert status.findings[0].code == "research-gap-surface"
    assert status.findings[0].severity == "info"


def test_agent_profiles_provider_codex_no_longer_research_gap(
    tmp_path: Path,
) -> None:
    """Codex now has a renderer and expands to real profile instances, not a research gap."""
    provider = _provider(tmp_path)
    instances = _real_profiles(provider.expand(agent_profile_definition(), "codex", tmp_path))
    # At least one profile projected (built-in profiles are always loaded).
    assert len(instances) > 0
    # All instances are owned by codex and point to .toml files.
    assert all(i.owner == "codex" for i in instances)
    assert all(i.path.suffix == ".toml" for i in instances)
    # None of the instances is the research-gap sentinel.
    assert all(str(i.path) != "<unsupported>" for i in instances)


# ---------------------------------------------------------------------------
# Augment renderer (WP03) — project-local, manifest-tracked
# ---------------------------------------------------------------------------


def test_augment_expands_to_real_profiles(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    instances = _real_profiles(provider.expand(agent_profile_definition(), "auggie", tmp_path))
    assert len(instances) >= 1
    assert all(i.owner == "auggie" for i in instances)
    assert all(i.path.suffix == ".md" for i in instances)
    assert all(".augment/agents" in str(i.path) for i in instances)


def test_augment_repair_writes_file_and_records_manifest(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    instance = provider.expand(agent_profile_definition(), "auggie", tmp_path)[0]
    missing = provider.probe(instance)
    assert missing.state == STATE_MISSING

    result = provider.repair(tmp_path, [missing])
    assert result.failed == ()
    assert len(result.repaired) == 1
    assert instance.path.exists()
    reloaded = ProfileManifest.load(tmp_path)
    assert reloaded.get_hash(instance.path) is not None, (
        "Augment profiles must be recorded in the project manifest"
    )


# ---------------------------------------------------------------------------
# Amazon Q renderer (WP03) — user-global, NOT manifest-tracked
# ---------------------------------------------------------------------------


def test_amazon_q_expands_to_real_profiles(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    instances = _real_profiles(provider.expand(agent_profile_definition(), "q", tmp_path))
    assert len(instances) >= 1
    assert all(i.owner == "q" for i in instances)
    assert all(i.path.suffix == ".json" for i in instances)


def test_amazon_q_output_path_is_user_global(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    instances = _real_profiles(provider.expand(agent_profile_definition(), "q", tmp_path))
    home = Path.home()
    for instance in instances:
        assert str(instance.path).startswith(str(home)), (
            f"Amazon Q path {instance.path} must be under home directory"
        )


def test_amazon_q_repair_writes_file_but_not_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Amazon Q profiles are user-global and must NOT appear in the project manifest."""
    fake_home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    provider = _provider(tmp_path)
    instance = provider.expand(agent_profile_definition(), "q", tmp_path)[0]
    missing = provider.probe(instance)
    assert missing.state == STATE_MISSING

    result = provider.repair(tmp_path, [missing])
    assert result.failed == ()
    assert len(result.repaired) == 1
    assert instance.path.exists()
    # Check the user-global file was written.
    content = instance.path.read_text(encoding="utf-8")
    assert "name" in content  # JSON payload
    # Verify the project manifest does NOT record an Amazon Q entry.
    reloaded = ProfileManifest.load(tmp_path)
    assert reloaded.get_hash(instance.path) is None, (
        "Amazon Q (user-global) profiles must NOT be recorded in the project manifest"
    )


# ---------------------------------------------------------------------------
# Core existing probe tests
# ---------------------------------------------------------------------------


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


def test_agent_profiles_provider_repair_records_source_provenance(
    tmp_path: Path,
) -> None:
    provider = _provider(tmp_path)
    instance = _real_profiles(
        provider.expand(agent_profile_definition(), "claude", tmp_path)
    )[0]
    missing = provider.probe(instance)

    result = provider.repair(tmp_path, [missing])

    assert result.failed == ()
    reloaded = ProfileManifest.load(tmp_path)
    entry = next(e for e in reloaded.all_entries() if e.output_path == instance.path)
    assert entry.source_path
    assert entry.source_hash
    assert entry.projection_version == PROJECTION_VERSION


def test_repair_dry_run_writes_nothing(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    instance = provider.expand(agent_profile_definition(), "claude", tmp_path)[0]
    missing = provider.probe(instance)
    result = provider.repair(tmp_path, [missing], dry_run=True)
    assert result.dry_run is True
    assert result.repaired == (_surface_id(missing.instance),)
    assert not instance.path.exists()


def test_repair_not_applicable_is_skipped(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    na_instance = provider.expand(agent_profile_definition(), "windsurf", tmp_path)[0]
    na_status = provider.probe(na_instance)
    result = provider.repair(tmp_path, [na_status])
    assert result.repaired == ()
    assert len(result.skipped) == 1


def test_repair_unsupported_status_provider_marks_skip(tmp_path: Path) -> None:
    """A status whose instance has no projection is skipped, not repaired."""
    provider = _provider(tmp_path)
    na_instance = provider.expand(agent_profile_definition(), "windsurf", tmp_path)[0]
    # Force a non-applicable status object through repair to exercise the skip
    # branch deterministically.
    status = SurfaceStatus(instance=na_instance, state=STATE_NOT_APPLICABLE)
    result = provider.repair(tmp_path, [status])
    assert result.repaired == ()
    assert _surface_id(na_instance) in result.skipped


def test_expand_appends_diagnostics_instance_for_supported_tool(
    tmp_path: Path,
) -> None:
    """A supported tool's expansion includes the diagnostics sentinel."""
    provider = _provider(tmp_path)
    instances = provider.expand(agent_profile_definition(), "claude", tmp_path)
    diagnostics = [
        i
        for i in instances
        if i.surface_id and i.surface_id.endswith(_DIAGNOSTICS_SENTINEL_SUFFIX)
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
        if i.surface_id and i.surface_id.endswith(_DIAGNOSTICS_SENTINEL_SUFFIX)
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
