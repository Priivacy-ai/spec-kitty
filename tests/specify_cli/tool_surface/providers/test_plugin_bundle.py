"""Live-path safety contract for plugin-bundle staging."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.tool_surface.providers.plugin_bundle import (
    PLUGIN_BUNDLE_TOOL_KEY,
    PluginBundleProvider,
    plugin_manifest_definition,
)
from specify_cli.tool_surface.status import STATE_MISSING, STATE_PRESENT

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_probe_detects_one_missing_member_among_surviving_kinds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.specify_cli.tool_surface.bundles._support import full_plans

    plans = full_plans(tmp_path)
    provider = PluginBundleProvider()
    monkeypatch.setattr(provider, "_plans_for_projection", lambda root: plans)
    instances = provider.expand(plugin_manifest_definition(), PLUGIN_BUNDLE_TOOL_KEY, tmp_path)
    result = provider.repair(tmp_path, [provider.probe(i) for i in instances])
    assert not result.failed
    victim = instances[0].path.parent.parent / "skills/spec-kitty.plan/SKILL.md"
    assert victim.is_file()
    victim.unlink()
    assert (victim.parent.parent / "spec-kitty.charter/SKILL.md").is_file()
    status = provider.probe(instances[0])
    assert status.state == STATE_MISSING, "Surviving kinds concealed an omitted member"
    assert not provider.repair(tmp_path, [status]).failed
    assert victim.read_bytes() == plans[0].instances[0].path.read_bytes()


def test_plugin_bundle_repair_is_staging_only_and_dry_run_is_inert(
    tmp_path: Path,
) -> None:
    """The provider's consumed repair path may write only under ``dist/``."""
    provider = PluginBundleProvider()
    definition = plugin_manifest_definition()
    instances = provider.expand(definition, PLUGIN_BUNDLE_TOOL_KEY, tmp_path)
    assert instances

    statuses = [provider.probe(instance) for instance in instances]
    assert {status.state for status in statuses} == {STATE_MISSING}

    dry_run = provider.repair(tmp_path, statuses, dry_run=True)
    assert dry_run.repaired
    assert not (tmp_path / "dist").exists()

    result = provider.repair(tmp_path, statuses, dry_run=False)
    assert result.failed == ()
    written = [path for path in tmp_path.rglob("*") if path.is_file()]
    assert written
    assert all(path.is_relative_to(tmp_path / "dist") for path in written)

    repaired = provider.expand(definition, PLUGIN_BUNDLE_TOOL_KEY, tmp_path)
    assert {provider.probe(instance).state for instance in repaired} == {STATE_PRESENT}
