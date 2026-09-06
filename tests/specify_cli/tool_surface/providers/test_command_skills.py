"""Unit tests for ``tool_surface.providers.command_skills``."""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.skills import command_installer
from specify_cli.skills import manifest_store
from specify_cli.tool_surface.providers.command_skills import (
    CommandSkillsProvider,
    command_skill_definition,
)
from specify_cli.tool_surface.providers.protocol import ReportingSurfaceProvider
from specify_cli.tool_surface.status import (
    STATE_DRIFTED,
    STATE_MISSING,
    STATE_PRESENT,
)

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_wp04_provider_retains_empty_expansion_selection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.tool_surface.model import SurfaceSelection
    from specify_cli.tool_surface.operations import ApplyConsent, AssessmentInputs, OperationRoot
    from tests.upgrade.preview_support.snapshot import snapshot, assert_unchanged

    codex = ".agents/skills/spec-kitty.old-codex/SKILL.md"
    vibe = ".agents/skills/spec-kitty.old-vibe/SKILL.md"
    _write_manifest_entry(tmp_path, codex, "owned codex")
    manifest = manifest_store.load(tmp_path)
    path = tmp_path / vibe
    path.parent.mkdir()
    path.write_bytes(b"owned vibe")
    manifest.upsert(manifest_store.ManifestEntry(vibe, manifest_store.fingerprint_file(path), ("vibe",), "2026-09-06T00:00:00+00:00", "test"))
    manifest_store.save(tmp_path, manifest)
    monkeypatch.setattr(command_installer, "CANONICAL_COMMANDS", ())
    provider = CommandSkillsProvider()
    definition = command_skill_definition()
    selection = SurfaceSelection("codex", definition)
    inputs = AssessmentInputs(OperationRoot("project", "project", tmp_path), consent=ApplyConsent(automatic=True))
    before = snapshot({"project": tmp_path})
    assessment = provider.assess(inputs, (), selections=(selection,))
    assert assessment.complete, assessment.diagnostics
    assert any(e.path == codex and e.action == "delete" for e in assessment.effects)
    assert not any(e.path == vibe for e in assessment.effects)
    retained = next(o.value for o in assessment.inputs_fingerprint if o.name == "selections")
    assert retained == (selection,)
    assert_unchanged(before, snapshot({"project": tmp_path}))
    with provider.recheck(assessment) as diagnostics:
        assert not diagnostics
        assert provider.apply(assessment, inputs.consent).outcome == "applied"
    assert not (tmp_path / codex).exists()
    assert path.read_bytes() == b"owned vibe"


def test_wp04_provider_preserves_status_identity_and_shared_batch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.tool_surface.model import SurfaceInstance
    from specify_cli.tool_surface.operations import ApplyConsent, AssessmentInputs, OperationRoot
    from specify_cli.tool_surface.providers.protocol import AssessingSurfaceProvider
    from specify_cli.tool_surface.plan import SurfacePlanBuilder
    from specify_cli.tool_surface.registry import ToolSurfaceRegistry
    from specify_cli.tool_surface.status import SurfaceStatus
    from tests.upgrade.preview_support.snapshot import snapshot
    from tests.specify_cli.skills.test_command_installer import _wp04_equal_effects

    provider = CommandSkillsProvider()
    assert isinstance(provider, AssessingSurfaceProvider)
    definition = command_skill_definition()
    registry = ToolSurfaceRegistry()
    for agent in ("codex", "vibe"):
        registry.register_definition(agent, definition)
    statuses: list[SurfaceStatus] = []
    original_probe = provider.probe

    def record_probe(instance: SurfaceInstance) -> SurfaceStatus:
        status = original_probe(instance)
        statuses.append(status)
        return status

    monkeypatch.setattr(provider, "probe", record_probe)
    inputs = AssessmentInputs(OperationRoot("project", "project", tmp_path), consent=ApplyConsent(automatic=True))
    before = snapshot({"project": tmp_path})
    assessed = SurfacePlanBuilder(registry, [provider]).assess(("codex", "vibe"), inputs)
    assessment = assessed.assessments[0]
    assert assessment.complete, assessment.diagnostics
    assert all(actual is original for actual, original in zip(assessed.report.surfaces, statuses, strict=True))
    retained = next(o.value for o in assessment.inputs_fingerprint if o.name == "instances")
    assert isinstance(retained, tuple)
    assert all(instance is status.instance for instance, status in zip(retained, statuses, strict=True))
    command_effects = [e for e in assessment.effects if e.after.kind == "file" and e.path.endswith("SKILL.md")]
    assert len(command_effects) == len(command_installer.CANONICAL_COMMANDS)
    assert all(e.logical_owners == ("codex", "vibe") and len(e.surface_ids) == 2 for e in command_effects)
    assert provider.apply(assessment, inputs.consent).outcome == "applied"
    _wp04_equal_effects(assessment, before, snapshot({"project": tmp_path}))


def test_wp04_ordinary_repair_keeps_drift_and_repairs_missing(tmp_path: Path) -> None:
    command_installer.install(tmp_path, "codex")
    missing = tmp_path / ".agents/skills/spec-kitty.plan/SKILL.md"
    drift = tmp_path / ".agents/skills/spec-kitty.status/SKILL.md"
    missing.unlink()
    drift.write_bytes(b"custom edited command")
    provider = CommandSkillsProvider()
    statuses = tuple(provider.probe(i) for i in provider.expand(command_skill_definition(), "codex", tmp_path))
    result = provider.repair(tmp_path, statuses)
    assert result.repaired and result.failed
    assert missing.is_file()
    assert drift.read_bytes() == b"custom edited command"


def _empty_manifest(project: Path) -> None:
    kittify = project / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "command-skills-manifest.json").write_text(json.dumps({"schema_version": 1, "entries": []}), encoding="utf-8")


def _write_manifest_entry(project: Path, rel: str, body: str) -> None:
    target = project / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    manifest_store.save(
        project,
        manifest_store.SkillsManifest(
            entries=[
                manifest_store.ManifestEntry(
                    path=rel,
                    content_hash=manifest_store.fingerprint_file(target),
                    agents=("codex",),
                    installed_at="2026-06-14T00:00:00+00:00",
                    spec_kitty_version="test",
                )
            ]
        ),
    )


def test_provider_satisfies_reporting_protocol() -> None:
    provider = CommandSkillsProvider()
    assert isinstance(provider, ReportingSurfaceProvider)
    assert provider.provider_key == "command_skills"


def test_can_handle_only_command_skill() -> None:
    from specify_cli.tool_surface.enums import ToolSurfaceKind
    from specify_cli.tool_surface.providers.slash_commands import (
        slash_command_definition,
    )

    provider = CommandSkillsProvider()
    assert provider.can_handle(command_skill_definition()) is True
    other = slash_command_definition()
    assert other.kind == ToolSurfaceKind.COMMAND_FILE
    assert provider.can_handle(other) is False


def test_expand_unsupported_agent_returns_empty(tmp_path: Path) -> None:
    _empty_manifest(tmp_path)
    provider = CommandSkillsProvider()
    instances = provider.expand(command_skill_definition(), "claude", tmp_path)
    assert instances == []


def test_expand_supported_agent_one_per_command(tmp_path: Path) -> None:
    _empty_manifest(tmp_path)
    provider = CommandSkillsProvider()
    instances = provider.expand(command_skill_definition(), "codex", tmp_path)
    assert len(instances) == len(command_installer.CANONICAL_COMMANDS)
    assert all(i.owner == "codex" for i in instances)
    assert all(i.path.name == "SKILL.md" for i in instances)


def test_probe_missing(tmp_path: Path) -> None:
    _empty_manifest(tmp_path)
    provider = CommandSkillsProvider()
    instance = provider.expand(command_skill_definition(), "codex", tmp_path)[0]
    status = provider.probe(instance)
    assert status.state == STATE_MISSING
    assert status.findings[0].code == "generated-surface-missing"
    assert status.findings[0].repair_command is not None


def test_probe_present(tmp_path: Path) -> None:
    _empty_manifest(tmp_path)
    provider = CommandSkillsProvider()
    instance = provider.expand(command_skill_definition(), "codex", tmp_path)[0]
    _write_manifest_entry(tmp_path, instance.path.relative_to(tmp_path).as_posix(), "content")
    instance = provider.expand(command_skill_definition(), "codex", tmp_path)[0]
    status = provider.probe(instance)
    assert status.state == STATE_PRESENT
    assert status.findings == ()


def test_probe_drift(tmp_path: Path) -> None:
    from dataclasses import replace

    _empty_manifest(tmp_path)
    provider = CommandSkillsProvider()
    instance = provider.expand(command_skill_definition(), "codex", tmp_path)[0]
    _write_manifest_entry(tmp_path, instance.path.relative_to(tmp_path).as_posix(), "real content")
    instance = provider.expand(command_skill_definition(), "codex", tmp_path)[0]
    # Force a mismatched expected hash to simulate manifest drift.
    drifted = replace(instance, exists=True, file_hash="deadbeef" * 8)
    status = provider.probe(drifted)
    assert status.state == STATE_DRIFTED
    assert status.findings[0].code == "managed-file-drift"


def test_repair_no_actionable_returns_clean(tmp_path: Path) -> None:
    _empty_manifest(tmp_path)
    provider = CommandSkillsProvider()
    instance = provider.expand(command_skill_definition(), "codex", tmp_path)[0]
    # Materialize the file so probe reports PRESENT (nothing to repair).
    _write_manifest_entry(tmp_path, instance.path.relative_to(tmp_path).as_posix(), "content")
    instance = provider.expand(command_skill_definition(), "codex", tmp_path)[0]
    present = provider.probe(instance)
    assert present.state == STATE_PRESENT
    result = provider.repair(tmp_path, [present])
    assert result.repaired == ()
    assert result.failed == ()


def test_repair_dry_run_reports_without_install(tmp_path: Path) -> None:
    _empty_manifest(tmp_path)
    provider = CommandSkillsProvider()
    instance = provider.expand(command_skill_definition(), "codex", tmp_path)[0]
    status = provider.probe(instance)  # missing
    result = provider.repair(tmp_path, [status], dry_run=True)
    assert result.dry_run is True
    # No file was created during a dry run.
    assert not instance.path.exists()


def test_expand_reports_unmanaged_spec_kitty_orphan(tmp_path: Path) -> None:
    _empty_manifest(tmp_path)
    orphan = tmp_path / ".agents" / "skills" / "spec-kitty.fake" / "SKILL.md"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text("orphan", encoding="utf-8")
    provider = CommandSkillsProvider()

    statuses = [provider.probe(i) for i in provider.expand(command_skill_definition(), "codex", tmp_path)]

    assert any(f.code == "unmanaged-spec-kitty-surface" for status in statuses for f in status.findings)


def test_expand_reports_stale_manifest_command(tmp_path: Path) -> None:
    stale_rel = ".agents/skills/spec-kitty.checklist/SKILL.md"
    stale = tmp_path / stale_rel
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text("stale", encoding="utf-8")
    manifest = manifest_store.SkillsManifest(
        entries=[
            manifest_store.ManifestEntry(
                path=stale_rel,
                content_hash=manifest_store.fingerprint_file(stale),
                agents=("codex",),
                installed_at="2026-06-14T00:00:00+00:00",
                spec_kitty_version="test",
            ),
        ]
    )
    manifest_store.save(tmp_path, manifest)
    provider = CommandSkillsProvider()

    statuses = [provider.probe(i) for i in provider.expand(command_skill_definition(), "codex", tmp_path)]

    assert any(f.code == "stale-generated-surface" for status in statuses for f in status.findings)
