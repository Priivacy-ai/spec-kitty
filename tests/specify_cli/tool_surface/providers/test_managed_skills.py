"""Unit tests for ``tool_surface.providers.managed_skills``.

These tests verify that the managed doctrine-skill provider conforms to the
reporting provider protocol, expands per-tool instances from the
``.kittify/skills-manifest.json`` manifest, probes on-disk state, and delegates
repair to the underlying ``skills.verifier`` (which owns both
``verify_installed_skills`` and ``repair_skills``) without reimplementing its
logic. Doctrine skills must surface as
``surface_kind: "doctrine_skill"`` -- distinct from command skills.
"""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.skills import installer as skill_installer
from specify_cli.skills.manifest import (
    ManagedFileEntry,
    ManagedSkillManifest,
    compute_content_hash,
    load_manifest,
)
from specify_cli.skills.registry import CanonicalSkill
from specify_cli.tool_surface.enums import ToolSurfaceKind
from specify_cli.tool_surface.providers.command_skills import (
    CommandSkillsProvider,
    command_skill_definition,
)
from specify_cli.tool_surface.providers.managed_skills import (
    ManagedSkillsProvider,
    doctrine_skill_entries,
    managed_skill_definition,
)
from specify_cli.tool_surface.providers.protocol import ReportingSurfaceProvider
from specify_cli.tool_surface.status import (
    STATE_DRIFTED,
    STATE_MISSING,
    STATE_PRESENT,
)

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _write_skill_file(project: Path, rel: str, body: str = "doctrine body") -> str:
    """Materialize a managed skill file and return its content hash."""
    target = project / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return compute_content_hash(target)


def _write_manifest(project: Path, entries: list[dict[str, str]]) -> None:
    kittify = project / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "created_at": "2026-06-14T00:00:00+00:00",
        "updated_at": "2026-06-14T00:00:00+00:00",
        "spec_kitty_version": "",
        "entries": entries,
    }
    (kittify / "skills-manifest.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def _entry(
    agent_key: str,
    installed_path: str,
    content_hash: str,
    *,
    skill_name: str = "spec-kitty-setup-doctor",
) -> dict[str, str]:
    return {
        "skill_name": skill_name,
        "source_file": "SKILL.md",
        "installed_path": installed_path,
        "installation_class": "shared-root-capable",
        "agent_key": agent_key,
        "content_hash": content_hash,
        "installed_at": "2026-06-14T00:00:00+00:00",
        "delivery_mode": "copy",
    }


def test_provider_satisfies_reporting_protocol() -> None:
    provider = ManagedSkillsProvider()
    assert isinstance(provider, ReportingSurfaceProvider)
    assert provider.provider_key == "managed_skills"


def test_managed_skills_provider_can_handle_doctrine_skill() -> None:
    provider = ManagedSkillsProvider()
    definition = managed_skill_definition()
    assert definition.kind == ToolSurfaceKind.DOCTRINE_SKILL
    assert provider.can_handle(definition) is True


def test_managed_skills_provider_cannot_handle_command_skill() -> None:
    provider = ManagedSkillsProvider()
    other = command_skill_definition()
    assert other.kind == ToolSurfaceKind.COMMAND_SKILL
    assert provider.can_handle(other) is False


def _canonical_skill(root: Path, name: str = "a") -> CanonicalSkill:
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("canonical", encoding="utf-8")
    return CanonicalSkill(name=name, skill_dir=skill_dir, skill_md=skill_md)


def _manifest_only_provider() -> ManagedSkillsProvider:
    return ManagedSkillsProvider(registry_factory=lambda: _StubRegistry([]))


def test_managed_skills_expand_no_manifest_uses_registry_policy(
    tmp_path: Path,
) -> None:
    skill = _canonical_skill(tmp_path / "canonical")
    provider = ManagedSkillsProvider(
        registry_factory=lambda: _StubRegistry([skill]),
    )

    instances = provider.expand(managed_skill_definition(), "codex", tmp_path)

    assert len(instances) == 1
    assert instances[0].path == tmp_path / ".agents/skills/a/SKILL.md"
    assert provider.probe(instances[0]).state == STATE_MISSING


def test_managed_skills_expand_returns_per_tool_skills(tmp_path: Path) -> None:
    """Skills count must match what the manifest expects for the tool."""
    h1 = _write_skill_file(tmp_path, ".agents/skills/a/SKILL.md")
    h2 = _write_skill_file(tmp_path, ".agents/skills/b/SKILL.md")
    other = _write_skill_file(tmp_path, ".claude/skills/c/SKILL.md")
    _write_manifest(
        tmp_path,
        [
            _entry("codex", ".agents/skills/a/SKILL.md", h1, skill_name="a"),
            _entry("codex", ".agents/skills/b/SKILL.md", h2, skill_name="b"),
            _entry("claude", ".claude/skills/c/SKILL.md", other, skill_name="c"),
        ],
    )
    provider = _manifest_only_provider()
    instances = provider.expand(managed_skill_definition(), "codex", tmp_path)
    assert len(instances) == 2
    assert all(i.owner == "codex" for i in instances)
    assert all(i.definition.kind == ToolSurfaceKind.DOCTRINE_SKILL for i in instances)


def test_doctrine_skill_entries_helper(tmp_path: Path) -> None:
    h1 = _write_skill_file(tmp_path, ".agents/skills/a/SKILL.md")
    _write_manifest(
        tmp_path,
        [_entry("codex", ".agents/skills/a/SKILL.md", h1, skill_name="a")],
    )
    entries = doctrine_skill_entries(tmp_path, "codex")
    assert [e.agent_key for e in entries] == ["codex"]
    assert doctrine_skill_entries(tmp_path, "claude") == []
    assert doctrine_skill_entries(tmp_path / "missing", "codex") == []


def test_managed_skills_probe_present(tmp_path: Path) -> None:
    h1 = _write_skill_file(tmp_path, ".agents/skills/a/SKILL.md")
    _write_manifest(
        tmp_path,
        [_entry("codex", ".agents/skills/a/SKILL.md", h1, skill_name="a")],
    )
    provider = _manifest_only_provider()
    instance = provider.expand(managed_skill_definition(), "codex", tmp_path)[0]
    status = provider.probe(instance)
    assert status.state == STATE_PRESENT
    assert status.findings == ()


def test_managed_skills_probe_detects_missing(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        [_entry("codex", ".agents/skills/a/SKILL.md", "sha256:deadbeef", skill_name="a")],
    )
    provider = _manifest_only_provider()
    instance = provider.expand(managed_skill_definition(), "codex", tmp_path)[0]
    status = provider.probe(instance)
    assert status.state == STATE_MISSING
    assert status.findings[0].code == "generated-surface-missing"
    assert status.findings[0].repair_command is not None


def test_managed_skills_probe_detects_drift(tmp_path: Path) -> None:
    from dataclasses import replace

    h1 = _write_skill_file(tmp_path, ".agents/skills/a/SKILL.md")
    _write_manifest(
        tmp_path,
        [_entry("codex", ".agents/skills/a/SKILL.md", h1, skill_name="a")],
    )
    provider = _manifest_only_provider()
    instance = provider.expand(managed_skill_definition(), "codex", tmp_path)[0]
    drifted = replace(instance, file_hash="sha256:" + "00" * 32)
    status = provider.probe(drifted)
    assert status.state == STATE_DRIFTED
    assert status.findings[0].code == "managed-file-drift"


def test_managed_skills_repair_no_actionable_returns_clean(tmp_path: Path) -> None:
    h1 = _write_skill_file(tmp_path, ".agents/skills/a/SKILL.md")
    _write_manifest(
        tmp_path,
        [_entry("codex", ".agents/skills/a/SKILL.md", h1, skill_name="a")],
    )
    provider = _manifest_only_provider()
    instance = provider.expand(managed_skill_definition(), "codex", tmp_path)[0]
    present = provider.probe(instance)
    assert present.state == STATE_PRESENT
    result = provider.repair(tmp_path, [present])
    assert result.repaired == ()
    assert result.failed == ()


def test_managed_skills_repair_dry_run_does_not_install(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        [_entry("codex", ".agents/skills/a/SKILL.md", "sha256:deadbeef", skill_name="a")],
    )
    provider = _manifest_only_provider()
    instance = provider.expand(managed_skill_definition(), "codex", tmp_path)[0]
    missing = provider.probe(instance)
    assert missing.state == STATE_MISSING
    result = provider.repair(tmp_path, [missing], dry_run=True)
    assert result.dry_run is True
    assert result.repaired  # reported, but nothing installed
    assert not instance.path.exists()


def test_managed_skills_repair_without_manifest_installs_expected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skill = _canonical_skill(tmp_path / "canonical")
    provider = ManagedSkillsProvider(
        registry_factory=lambda: _StubRegistry([skill]),
    )
    instance = provider.expand(managed_skill_definition(), "codex", tmp_path)[0]
    missing = provider.probe(instance)
    calls: list[tuple[Path, list[str]]] = []

    def fake_install_all_skills(
        project_path: Path, agent_keys: list[str], registry: object
    ) -> ManagedSkillManifest:
        calls.append((project_path, agent_keys))
        assert registry.discover_skills() == [skill]  # type: ignore[attr-defined]
        return ManagedSkillManifest(
            entries=[
                ManagedFileEntry(
                    skill_name="a",
                    source_file="SKILL.md",
                    installed_path=".agents/skills/a/SKILL.md",
                    installation_class="shared-root-capable",
                    agent_key="codex",
                    content_hash="sha256:" + "1" * 64,
                    installed_at="2026-06-14T00:00:00+00:00",
                    delivery_mode="copy",
                )
            ]
        )

    monkeypatch.setattr(
        skill_installer, "install_all_skills", fake_install_all_skills
    )

    result = provider.repair(tmp_path, [missing])

    assert calls == [(tmp_path, ["codex"])]
    assert result.failed == ()
    assert result.repaired
    manifest = load_manifest(tmp_path)
    assert manifest is not None
    assert [entry.installed_path for entry in manifest.entries] == [
        ".agents/skills/a/SKILL.md"
    ]


class _StubVerifyResult:
    def __init__(self, ok: bool) -> None:
        self.ok = ok


class _StubVerifier:
    def __init__(self, ok: bool) -> None:
        self._ok = ok
        self.calls: list[Path] = []

    def verify_installed_skills(self, project_path: Path) -> _StubVerifyResult:
        self.calls.append(project_path)
        return _StubVerifyResult(self._ok)


class _StubInstaller:
    def __init__(self, repaired: int, failed: int) -> None:
        self._repaired = repaired
        self._failed = failed
        self.calls: list[Path] = []

    def repair_skills(
        self, project_path: Path, verify_result: object, registry: object
    ) -> tuple[int, int]:
        self.calls.append(project_path)
        return self._repaired, self._failed


class _StubRegistry:
    def __init__(self, skills: list[object]) -> None:
        self._skills = skills

    def discover_skills(self) -> list[object]:
        return self._skills


def test_managed_skills_repair_calls_installer(tmp_path: Path) -> None:
    """Repair must delegate to verifier+installer, not reimplement them."""
    _write_manifest(
        tmp_path,
        [_entry("codex", ".agents/skills/a/SKILL.md", "sha256:deadbeef", skill_name="a")],
    )
    verifier = _StubVerifier(ok=False)
    installer = _StubInstaller(repaired=1, failed=0)
    skill = _canonical_skill(tmp_path / "canonical")
    provider = ManagedSkillsProvider(
        verifier=verifier,
        installer=installer,
        registry_factory=lambda: _StubRegistry([skill]),
    )
    instance = provider.expand(managed_skill_definition(), "codex", tmp_path)[0]
    missing = provider.probe(instance)
    result = provider.repair(tmp_path, [missing])
    assert verifier.calls == [tmp_path]
    assert installer.calls == [tmp_path]
    assert result.repaired
    assert result.failed == ()


def test_managed_skills_repair_reports_installer_failures(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        [_entry("codex", ".agents/skills/a/SKILL.md", "sha256:deadbeef", skill_name="a")],
    )
    skill = _canonical_skill(tmp_path / "canonical")
    provider = ManagedSkillsProvider(
        verifier=_StubVerifier(ok=False),
        installer=_StubInstaller(repaired=0, failed=1),
        registry_factory=lambda: _StubRegistry([skill]),
    )
    instance = provider.expand(managed_skill_definition(), "codex", tmp_path)[0]
    missing = provider.probe(instance)
    result = provider.repair(tmp_path, [missing])
    assert result.failed
    assert "failed to repair" in result.failed[0]


def test_managed_skills_repair_skips_when_verifier_clean(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        [_entry("codex", ".agents/skills/a/SKILL.md", "sha256:deadbeef", skill_name="a")],
    )
    installer = _StubInstaller(repaired=0, failed=0)
    skill = _canonical_skill(tmp_path / "canonical")
    provider = ManagedSkillsProvider(
        verifier=_StubVerifier(ok=True),
        installer=installer,
        registry_factory=lambda: _StubRegistry([skill]),
    )
    instance = provider.expand(managed_skill_definition(), "codex", tmp_path)[0]
    missing = provider.probe(instance)
    result = provider.repair(tmp_path, [missing])
    # Verifier reports clean -> installer is never invoked.
    assert installer.calls == []
    assert result.repaired == ()
    assert result.failed == ()


def test_managed_skills_repair_fails_without_registry(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        [_entry("codex", ".agents/skills/a/SKILL.md", "sha256:deadbeef", skill_name="a")],
    )
    provider = ManagedSkillsProvider(
        verifier=_StubVerifier(ok=False),
        installer=_StubInstaller(repaired=0, failed=0),
        registry_factory=lambda: _StubRegistry([]),
    )
    instance = provider.expand(managed_skill_definition(), "codex", tmp_path)[0]
    missing = provider.probe(instance)
    result = provider.repair(tmp_path, [missing])
    assert result.failed
    assert "no canonical skill registry" in result.failed[0]


def test_repair_default_collaborator_binds_repair_skills() -> None:
    """Regression: the default (no-DI) repair collaborator must own repair_skills.

    Cycle-1 reject: the default ``self._installer`` was bound to
    ``skills.installer``, which has no ``repair_skills`` -- so the live ``--fix``
    path raised ``AttributeError`` while every DI test masked it with a stub. This
    guard fails fast if the wrong module is ever rebound.
    """
    provider = ManagedSkillsProvider()
    assert callable(getattr(provider._installer, "repair_skills", None))


def test_repair_default_path_repairs_without_injection(tmp_path: Path) -> None:
    """Regression: run ``repair`` with NO injected collaborators (real default).

    Exercises the production wiring the CLI ``--fix`` uses: the default
    ``skills.verifier`` collaborator and the real canonical ``SkillRegistry``.
    A real canonical skill is recorded in the manifest, deleted on disk so it is
    "missing", then repaired -- proving the default path does not raise and
    actually restores the file. Cycle-1 reject was masked because every repair
    test injected a ``_StubInstaller``; this one injects nothing.
    """
    skill_name = "ad-hoc-profile-load"
    installed_rel = ".agents/skills/ad-hoc-profile-load/SKILL.md"
    project = tmp_path.resolve()  # dodge macOS /var -> /private/var symlink mismatch
    placeholder_hash = _write_skill_file(project, installed_rel, body="placeholder")
    _write_manifest(
        project,
        [
            _entry(
                "codex",
                installed_rel,
                placeholder_hash,
                skill_name=skill_name,
            )
        ],
    )
    # Make the managed skill "missing" so repair must restore it.
    (project / installed_rel).unlink()

    provider = ManagedSkillsProvider()  # no verifier/installer/registry injected
    instance = provider.expand(managed_skill_definition(), "codex", project)[0]
    missing = provider.probe(instance)
    assert missing.state == STATE_MISSING

    result = provider.repair(project, [missing])  # real default --fix path

    assert result.failed == ()
    assert result.repaired  # at least the actionable id reported repaired
    restored = project / installed_rel
    assert restored.exists()
    assert restored.read_text(encoding="utf-8").strip()  # canonical content


def _make_real_providers() -> list[ReportingSurfaceProvider]:
    """Build the real provider list used by the two integration tests below.

    WP03: SurfaceProviderRegistry._registrations is empty until WP04 wires
    providers.  These tests pre-populate via monkeypatch on build_providers /
    build_registry so they exercise real provider logic without relying on the
    registry being populated.  WP04 will delete this helper and let the registry
    supply providers automatically.
    """
    return [CommandSkillsProvider(), ManagedSkillsProvider()]


def _make_real_registry(tool_keys: list[str]) -> object:
    """Build a real ToolSurfaceRegistry with command and doctrine definitions.

    Used by the two integration tests below to bypass the empty registry at
    WP03 stage.  WP04 will remove this helper.
    """
    from specify_cli.tool_surface.registry import ToolSurfaceRegistry

    registry = ToolSurfaceRegistry()
    definitions = (command_skill_definition(), managed_skill_definition())
    for tool_key in tool_keys:
        for defn in definitions:
            registry.register_definition(tool_key, defn)
    return registry


def test_doctrine_vs_command_skill_in_doctor_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """doctor tool-surfaces output separates doctrine and command kinds."""
    import specify_cli.tool_surface.service as svc

    # WP03: pre-populate build_providers and build_registry with real impls
    # because SurfaceProviderRegistry._registrations is empty until WP04.
    monkeypatch.setattr(svc, "build_providers", _make_real_providers)
    monkeypatch.setattr(svc, "build_registry", _make_real_registry)

    from specify_cli.tool_surface.service import run_tool_surfaces

    # One doctrine skill registered in the managed manifest.
    h1 = _write_skill_file(tmp_path, ".agents/skills/a/SKILL.md")
    _write_manifest(
        tmp_path,
        [_entry("codex", ".agents/skills/a/SKILL.md", h1, skill_name="a")],
    )
    # An empty command-skills manifest so the command-skill provider runs too.
    (tmp_path / ".kittify" / "command-skills-manifest.json").write_text(
        json.dumps({"schema_version": 1, "entries": []}), encoding="utf-8"
    )
    outcome = run_tool_surfaces(tmp_path, ["codex"])
    kinds = {s.instance.definition.kind for s in outcome.report.surfaces}
    assert ToolSurfaceKind.DOCTRINE_SKILL in kinds
    assert ToolSurfaceKind.COMMAND_SKILL in kinds
    payload = outcome.to_json()
    surface_kinds = {entry["kind"] for entry in payload["surfaces"]}  # type: ignore[index]
    assert "doctrine_skill" in surface_kinds
    assert "command_skill" in surface_kinds
    assert "doctrine_skill" != "command_skill"


def test_run_tool_surfaces_kind_filter_doctrine_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import specify_cli.tool_surface.service as svc
    from specify_cli.tool_surface.service import run_tool_surfaces

    # WP03: pre-populate build_providers and build_registry with real impls
    # because SurfaceProviderRegistry._registrations is empty until WP04.
    monkeypatch.setattr(svc, "build_providers", _make_real_providers)
    monkeypatch.setattr(svc, "build_registry", _make_real_registry)
    # _KIND_TOKENS is a module-level constant built at import time from the
    # (currently empty) registry.  Patch it so surface_kind_from_token works.
    monkeypatch.setattr(
        svc,
        "_KIND_TOKENS",
        {"doctrine-skill": ToolSurfaceKind.DOCTRINE_SKILL},
    )

    h1 = _write_skill_file(tmp_path, ".agents/skills/a/SKILL.md")
    _write_manifest(
        tmp_path,
        [_entry("codex", ".agents/skills/a/SKILL.md", h1, skill_name="a")],
    )
    (tmp_path / ".kittify" / "command-skills-manifest.json").write_text(
        json.dumps({"schema_version": 1, "entries": []}), encoding="utf-8"
    )
    kind = svc.surface_kind_from_token("doctrine-skill")
    assert kind == ToolSurfaceKind.DOCTRINE_SKILL
    outcome = run_tool_surfaces(tmp_path, ["codex"], kinds=[kind])
    kinds = {s.instance.definition.kind for s in outcome.report.surfaces}
    assert kinds == {ToolSurfaceKind.DOCTRINE_SKILL}
