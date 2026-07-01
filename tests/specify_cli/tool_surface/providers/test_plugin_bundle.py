"""Unit tests for ``tool_surface.providers.plugin_bundle``.

Includes the FR-016 / C-006 PROHIBITION regression: the plugin-bundle projection
and validation path must NEVER auto-install a bundle or publish it to a
marketplace. The negative-assertion tests below fail if such logic is ever
introduced.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from specify_cli.tool_surface.bundles.model import PluginBundle
from specify_cli.tool_surface.providers.command_skills import (
    command_skill_definition,
)
from specify_cli.tool_surface.providers.plugin_bundle import (
    PLUGIN_BUNDLE_TOOL_KEY,
    PluginBundleProvider,
    plugin_manifest_definition,
)
from specify_cli.tool_surface.providers.protocol import ReportingSurfaceProvider
from specify_cli.tool_surface.repair import RepairResult
from specify_cli.tool_surface.status import (
    STATE_MISSING,
    STATE_PRESENT,
    STATE_STALE,
)

import specify_cli.tool_surface.bundles.claude as claude_mod
import specify_cli.tool_surface.bundles.copilot as copilot_mod
import specify_cli.tool_surface.bundles.projection as projection_mod
import specify_cli.tool_surface.bundles.vscode as vscode_mod
import specify_cli.tool_surface.providers.plugin_bundle as provider_mod

from ..bundles._support import full_plans, skills_only_plans

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_provider_satisfies_reporting_protocol() -> None:
    assert isinstance(PluginBundleProvider(), ReportingSurfaceProvider)
    assert PluginBundleProvider().provider_key == "plugin_bundle"


def test_can_handle_only_plugin_manifest() -> None:
    provider = PluginBundleProvider()
    assert provider.can_handle(plugin_manifest_definition()) is True
    assert provider.can_handle(command_skill_definition()) is False


def test_expand_only_fires_for_synthetic_bundle_key(tmp_path: Path) -> None:
    provider = PluginBundleProvider()
    definition = plugin_manifest_definition()
    # Non-bundle tool keys yield nothing (no duplicate-per-tool manifests).
    assert provider.expand(definition, "claude", tmp_path) == []
    instances = provider.expand(definition, PLUGIN_BUNDLE_TOOL_KEY, tmp_path)
    # One manifest instance per distribution target.
    owners = {i.owner for i in instances}
    assert owners == {
        "claude_code_plugin",
        "copilot_skill_package",
        "vscode_extension",
    }


def test_probe_detects_missing_bundle(tmp_path: Path) -> None:
    provider = PluginBundleProvider()
    definition = plugin_manifest_definition()
    instances = provider.expand(definition, PLUGIN_BUNDLE_TOOL_KEY, tmp_path)
    status = provider.probe(instances[0])
    assert status.state == STATE_MISSING


def test_probe_present_when_bundle_complete(tmp_path: Path) -> None:
    project = tmp_path
    # Project a complete Claude Code bundle into the staged output dir.
    provider = PluginBundleProvider()
    out = provider._output_dir(project, "claude_code_plugin")
    claude_mod.ClaudeCodeBundleProjector().project(
        full_plans(project), project, out
    )
    definition = plugin_manifest_definition()
    instances = provider.expand(definition, PLUGIN_BUNDLE_TOOL_KEY, project)
    claude_inst = next(i for i in instances if i.owner == "claude_code_plugin")
    status = provider.probe(claude_inst)
    assert status.state == STATE_PRESENT


def test_probe_incomplete_bundle_is_error(tmp_path: Path) -> None:
    project = tmp_path
    provider = PluginBundleProvider()
    out = provider._output_dir(project, "claude_code_plugin")
    claude_mod.ClaudeCodeBundleProjector().project(
        skills_only_plans(project), project, out
    )
    definition = plugin_manifest_definition()
    instances = provider.expand(definition, PLUGIN_BUNDLE_TOOL_KEY, project)
    claude_inst = next(i for i in instances if i.owner == "claude_code_plugin")
    status = provider.probe(claude_inst)
    assert status.state == STATE_MISSING
    assert status.findings, "incomplete bundle must produce findings"
    finding = status.findings[0]
    assert finding.code == "bundle-component-missing"
    assert finding.severity == "error"


def test_probe_unknown_target_is_stale_warning(tmp_path: Path) -> None:
    """An instance for an unregistered target yields a stale-path warning."""
    provider = PluginBundleProvider(projectors=[])
    definition = plugin_manifest_definition()
    # With no projectors, expand yields nothing; build an instance manually.
    from specify_cli.tool_surface.model import SurfaceInstance

    inst = SurfaceInstance(
        definition=definition,
        path=tmp_path / "dist" / "ghost" / "plugin.json",
        exists=False,
        file_hash=None,
        owner="ghost_target",
    )
    status = provider.probe(inst)
    assert status.state == STATE_STALE
    assert status.findings[0].code == "plugin-manifest-stale-path"
    assert status.findings[0].severity == "warning"


def test_repair_dry_run_reports_without_writing(tmp_path: Path) -> None:
    provider = PluginBundleProvider()
    definition = plugin_manifest_definition()
    instances = provider.expand(definition, PLUGIN_BUNDLE_TOOL_KEY, tmp_path)
    statuses = [provider.probe(i) for i in instances]
    result = provider.repair(tmp_path, statuses, dry_run=True)
    assert result.dry_run is True
    assert result.repaired
    # No staging files written on a dry run.
    assert not (tmp_path / "dist").exists()


def test_repair_noop_when_nothing_actionable(tmp_path: Path) -> None:
    provider = PluginBundleProvider()
    result = provider.repair(tmp_path, [], dry_run=False)
    assert isinstance(result, RepairResult)
    assert result.repaired == ()


# --- FR-016 / C-006 PROHIBITION regression -------------------------------- #
#
# C-006 amendment (mission agent-profile-projection-plugin-production-01KV3NGS,
# 2026-06-15): the prohibition targets install/publish *actions* — the bundle
# code must never auto-install a bundle or *publish* it to a marketplace
# (the original regression injected ``marketplace_publish``, still caught by the
# ``publish`` token below). Writing a *declarative* ``marketplace.json`` catalog
# descriptor alongside the bundle (FR-023 / FR-029) is inert output, not an
# action, and is therefore permitted: the bare ``marketplace`` token was removed
# so a descriptor write (``_write_marketplace_json``, ``"marketplace.json"``) no
# longer trips the guard, while ``marketplace_publish``/``*_publish`` still do.
# See docs/adr/3.x/2026-06-15-1-marketplace-descriptor-vs-publish.md.

_FORBIDDEN_TOKENS = (
    "publish",
    "auto_install",
    "auto-install",
    "autoinstall",
    "register_plugin",
    "enable_plugin",
    "upload",
)

_BUNDLE_MODULES = (
    claude_mod,
    copilot_mod,
    vscode_mod,
    projection_mod,
    provider_mod,
)


@pytest.mark.parametrize("module", _BUNDLE_MODULES)
def test_no_install_or_publish_tokens_in_source(module: object) -> None:
    """The bundle code must not name any install/publish/marketplace surface.

    Comments and docstrings legitimately mention the prohibition (e.g. "never
    publish"); this check scans only executable code -- call targets, attribute
    accesses, and string literals that are not docstrings -- so the guard fails
    only if such behaviour is actually wired in.
    """
    source = Path(module.__file__).read_text(encoding="utf-8")  # type: ignore[attr-defined]
    tree = ast.parse(source)
    offending: list[str] = []
    docstrings = _docstring_nodes(tree)
    for node in ast.walk(tree):
        if node in docstrings:
            continue
        name = _executable_name(node)
        if name is None:
            continue
        lowered = name.lower()
        for token in _FORBIDDEN_TOKENS:
            if token in lowered:
                offending.append(name)
    assert not offending, (
        f"{module.__name__} references prohibited install/publish surface: "
        f"{offending} (FR-016 / C-006)"
    )


def test_repair_projects_inert_staging_only_no_side_channels(
    tmp_path: Path,
) -> None:
    """A real repair writes ONLY staging files; no projector grows an install
    or publish method, and the projected bundle is a declarative descriptor."""
    provider = PluginBundleProvider()
    definition = plugin_manifest_definition()
    instances = provider.expand(definition, PLUGIN_BUNDLE_TOOL_KEY, tmp_path)
    # Force every status into a missing state so repair re-projects all targets.
    statuses = [provider.probe(i) for i in instances]
    assert all(s.state == STATE_MISSING for s in statuses)

    # Guard: no projector may expose an install/publish/marketplace method.
    for projector in provider._projectors:
        attrs = {a.lower() for a in dir(projector)}
        assert not any(
            tok.replace("-", "_") in a
            for a in attrs
            for tok in _FORBIDDEN_TOKENS
        ), f"{type(projector).__name__} exposes a prohibited method"

    result = provider.repair(tmp_path, statuses, dry_run=False)
    assert result.failed == ()
    # The ONLY side effect is staging files under the dist/ output tree.
    written = sorted(p for p in tmp_path.rglob("*") if p.is_file())
    assert written, "repair must produce staging files"
    for path in written:
        assert "dist" in path.parts, (
            f"repair wrote outside the staging tree: {path}"
        )

    # The descriptor returned by projection is inert (a dataclass), with no
    # install/publish behaviour attached.
    out = provider._output_dir(tmp_path, "claude_code_plugin")
    bundle = claude_mod.ClaudeCodeBundleProjector().project(
        full_plans(tmp_path), tmp_path, out
    )
    assert isinstance(bundle, PluginBundle)
    assert not any(
        tok.replace("-", "_") in m.lower()
        for m in dir(bundle)
        for tok in _FORBIDDEN_TOKENS
    )


def _docstring_nodes(tree: ast.AST) -> set[ast.AST]:
    """Collect the docstring Constant nodes of every module/class/function."""
    nodes: set[ast.AST] = set()
    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                nodes.add(body[0].value)
    return nodes


def _executable_name(node: ast.AST) -> str | None:
    """Return a code identifier/string-literal worth scanning, else ``None``."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None
