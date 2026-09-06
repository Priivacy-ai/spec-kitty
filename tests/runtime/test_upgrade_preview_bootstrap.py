"""Global owner regressions; public startup wiring is separately owned by WP10."""

from pathlib import Path
from collections.abc import Callable
from dataclasses import replace
import shutil
import ast
from contextlib import contextmanager
from collections.abc import Iterator
import inspect
import json
import os
import sys
from typing import Any, cast

import click
from typer.main import get_command

import pytest

from specify_cli.runtime import agent_commands, agent_skills, bootstrap
from specify_cli.skills.registry import SkillRegistry
from tests.upgrade.preview_support.snapshot import assert_unchanged, snapshot
from tests.upgrade.preview_support.snapshot import net_delta
from specify_cli.runtime.asset_preparation import apply_assets, recheck_assets
from specify_cli.tool_surface.operations import ApplyConsent, OwnerAssessment
from specify_cli.upgrade.intent import parse_upgrade_intent

pytestmark = [pytest.mark.unit, pytest.mark.fast]


@pytest.fixture
def owner_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("OPENCODE_CONFIG_DIR", str(home / ".config/opencode"))
    return home


@pytest.fixture
def skill_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    source = tmp_path / "skills"
    skill = source / "spec-kitty"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: spec-kitty\ndescription: Govern work\n---\n# Work\n")
    monkeypatch.setattr(agent_skills, "_discover_registry", lambda: SkillRegistry(source))
    return source


def test_existing_runtime_repairs_current_marker_missing_content(
    owner_home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "package/missions"
    (source / "software-dev").mkdir(parents=True)
    (source / "software-dev/templates").mkdir()
    (source / "software-dev/templates/spec.md").write_text("# Specification\n")
    (source / "software-dev/mission.yaml").write_text("mission: software-dev\n")
    monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(source))
    cache = owner_home / ".kittify/cache"
    cache.mkdir(parents=True)
    (cache / "version.lock").write_text(bootstrap._get_cli_version())
    bootstrap.ensure_runtime()
    assert (owner_home / ".kittify/missions/software-dev/mission.yaml").is_file()


def test_existing_skills_repair_current_marker_missing_content(
    owner_home: Path,
    skill_source: Path,
) -> None:
    agent_skills.ensure_global_agent_skills()
    missing = owner_home / ".agents/skills/spec-kitty/SKILL.md"
    missing.unlink()
    agent_skills.ensure_global_agent_skills()
    assert missing.is_file(), "Current stamp must not conceal missing required content"


def test_existing_commands_preserve_unknown_prefixed_link(owner_home: Path) -> None:
    output = agent_commands.get_global_command_dir("claude")
    output.mkdir(parents=True)
    target = owner_home / "custom.md"
    target.write_text("custom command\n")
    target.chmod(0o444)
    link = output / "spec-kitty.custom.md"
    link.symlink_to(target)
    before = snapshot({"target": target, "link": link})
    agent_commands.ensure_global_agent_commands(agent_keys=["claude"])
    assert_unchanged(before, snapshot({"target": target, "link": link}))


def test_existing_skills_preserve_unknown_prefixed_tree(
    owner_home: Path,
    skill_source: Path,
) -> None:
    custom = owner_home / ".agents/skills/spec-kitty-custom"
    custom.mkdir(parents=True)
    (custom / "SKILL.md").write_text("# User skill\n")
    (custom / ".ignored").write_bytes(b"sentinel")
    before = snapshot({"custom": custom})
    agent_skills.ensure_global_agent_skills()
    assert_unchanged(before, snapshot({"custom": custom}))


def test_existing_scoped_command_repair_has_no_churn(owner_home: Path) -> None:
    agent_commands.ensure_global_agent_commands(agent_keys=["claude"])
    before = snapshot({"home": owner_home})
    agent_commands.ensure_global_agent_commands(agent_keys=["claude"])
    assert_unchanged(before, snapshot({"home": owner_home}))


def _actual_upgrade_command() -> click.Command:
    from specify_cli import _get_app

    root = get_command(_get_app())
    assert isinstance(root, click.Group)
    command = root.get_command(click.Context(root), "upgrade")
    assert command is not None
    return command


@pytest.mark.parametrize(
    ("argv", "available", "mode", "representation"),
    [
        ([], True, "apply", "human"),
        (["--json"], True, "apply", "outcome"),
        (["--project", "--json"], True, "preview", "legacy"),
        (["--dry-run", "--json"], True, "preview", "legacy"),
        (["--cli", "--dry-run", "--json"], True, "guidance", "legacy"),
        ([], False, "guidance", "human"),
        (["--json"], False, "guidance", "legacy"),
        (["--agent-check", "--json"], False, "hidden", "hidden"),
        (["--agent-choice", "later", "--agent-latest", "4.0", "--json"], False, "hidden", "hidden"),
    ],
)
def test_intent_uses_actual_definitions(argv: list[str], available: bool, mode: str, representation: str) -> None:
    intent = parse_upgrade_intent(_actual_upgrade_command(), argv, project_available=available)
    assert (intent.mode, intent.representation, intent.conflicts) == (mode, representation, ())


@pytest.mark.parametrize("argv", [["--target"], ["--unknown"], ["extra"]])
def test_intent_retains_click_usage_errors(argv: list[str]) -> None:
    with pytest.raises(click.UsageError):
        parse_upgrade_intent(_actual_upgrade_command(), argv, project_available=True)


def test_intent_alias_equals_order_and_callback_denial(monkeypatch: pytest.MonkeyPatch) -> None:
    command = _actual_upgrade_command()

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Parse-only intent invoked a callback")

    monkeypatch.setattr(command, "callback", forbidden)
    for param in command.params:
        monkeypatch.setattr(param, "callback", forbidden)
    intent = parse_upgrade_intent(command, ["-v", "--target=not-a-version", "-y", "--dry-run", "--no-worktrees"], project_available=True)
    assert intent.target == "not-a-version"
    assert intent.mode == "preview"
    assert not intent.include_worktrees
    target = next(p for p in command.params if p.name == "target")
    monkeypatch.setattr(target, "default", forbidden)
    with pytest.raises(click.UsageError, match="callable default"):
        parse_upgrade_intent(command, [], project_available=True)


@pytest.mark.parametrize("hidden", [["--agent-check"], ["--agent-latest", "4.0"], ["--agent-choice", "later", "--agent-latest", "4.0"]])
def test_intent_hidden_conflicts_cover_implicit_preview(hidden: list[str]) -> None:
    command = _actual_upgrade_command()
    for ordinary in (["--project", "--json"], ["--cli", "--json"], ["--dry-run"], ["--target", "4.0"]):
        result = parse_upgrade_intent(command, [*ordinary, *hidden], project_available=False)
        assert result.conflicts


def test_intent_full_plan_precedence_is_semantic_not_public_registration(monkeypatch: pytest.MonkeyPatch) -> None:
    command = _actual_upgrade_command()
    # WP10 owns registration. Extend the actual definition locally to exercise
    # only the future semantic value; this is deliberately not CLI acceptance.
    monkeypatch.setattr(command, "params", [*command.params, click.Option(["--plan-json"], is_flag=True)])
    result = parse_upgrade_intent(command, ["--plan-json", "--json", "--dry-run", "--cli"], project_available=True)
    assert result.representation == "full"
    assert result.conflicts == ("--plan-json and --cli are mutually exclusive",)


def _apply_exact(assessment: OwnerAssessment) -> None:
    assert assessment.complete, assessment.diagnostics
    assert assessment.effects, "A known broken fixture must promise real physical work"
    roots = {assessment.root.root_id: assessment.root.path}
    before = snapshot(roots)
    with recheck_assets(assessment) as diagnostics:
        assert not diagnostics
        result = apply_assets(assessment, replace(assessment.consent, automatic=True))
    assert result.outcome == "applied", result
    actual = net_delta(before, snapshot(roots))
    expected = {(e.path, e.action, e.after.kind, e.after.sha256, e.after.target, e.after.mode) for e in assessment.effects}
    observed = {(e.path, e.action, e.after.kind, e.after.sha256, e.after.target, e.after.mode) for e in actual}
    assert expected == observed
    omitted = next(iter(expected))
    assert expected - {omitted} != observed, "The oracle must reject an omitted physical effect"


@pytest.mark.parametrize("owner", ["runtime", "commands", "skills"])
def test_owner_assessment_is_pure_exact_and_repeat_no_churn(
    owner: str,
    owner_home: Path,
    skill_source: Path,
) -> None:
    assessors: dict[str, Callable[[], OwnerAssessment]] = {
        "runtime": bootstrap.assess_runtime,
        "commands": lambda: agent_commands.assess_global_agent_commands(agent_keys=["claude"]),
        "skills": agent_skills.assess_global_agent_skills,
    }
    before = snapshot({"home": owner_home})
    assessment = assessors[owner]()
    assert_unchanged(before, snapshot({"home": owner_home}))
    _apply_exact(assessment)
    before = snapshot({"home": owner_home})
    second = assessors[owner]()
    assert second.complete and not second.effects
    with recheck_assets(second) as diagnostics:
        assert not diagnostics
        result = apply_assets(second, ApplyConsent(automatic=True))
    assert result.outcome == "skipped"
    assert_unchanged(before, snapshot({"home": owner_home}))


@pytest.mark.parametrize("change", ["source", "destination", "parent", "environment"])
def test_whole_batch_precondition_refusal_before_writes(
    change: str,
    owner_home: Path,
    skill_source: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent_skills.ensure_global_agent_skills()
    destination = owner_home / ".agents/skills/spec-kitty/SKILL.md"
    destination.unlink()
    assessment = agent_skills.assess_global_agent_skills()
    assert assessment.effects and assessment.complete
    if change == "source":
        (skill_source / "spec-kitty/SKILL.md").write_text("changed source")
    elif change == "destination":
        destination.write_text("racing user")
    elif change == "parent":
        moved = destination.parent.with_name("saved")
        destination.parent.rename(moved)
        destination.parent.symlink_to(moved, target_is_directory=True)
    else:
        monkeypatch.setenv("SPEC_KITTY_HOME", str(owner_home / "different"))
    before = snapshot({"home": owner_home, "source": skill_source})
    with recheck_assets(assessment) as diagnostics:
        assert diagnostics and diagnostics[0].code == "precondition_changed"
    result = apply_assets(assessment, ApplyConsent(automatic=True))
    assert result.outcome == "precondition_changed" and not result.succeeded
    assert_unchanged(before, snapshot({"home": owner_home, "source": skill_source}))


def test_exact_retired_skill_cleanup_and_edited_sibling_preservation(
    owner_home: Path,
    skill_source: Path,
) -> None:
    for name in ("paula-patterns", "debugger-debbie"):
        source = skill_source / name
        source.mkdir()
        (source / "SKILL.md").write_text(f"---\nname: {name}\ndescription: owned\n---\n# Body\n")
    agent_skills.ensure_global_agent_skills()
    edited = owner_home / ".agents/skills/debugger-debbie/SKILL.md"
    edited.chmod(0o644)
    edited.write_text("user edit")
    for name in ("paula-patterns", "debugger-debbie"):
        shutil.rmtree(skill_source / name)
    assessment = agent_skills.assess_global_agent_skills()
    assert any(e.action == "delete" and "paula-patterns" in e.path for e in assessment.effects)
    before = snapshot({"edited": edited})
    _apply_exact(assessment)
    assert_unchanged(before, snapshot({"edited": edited}))
    assert not (owner_home / ".agents/skills/paula-patterns").exists()
    assert not agent_skills.assess_global_agent_skills().effects


def test_prepared_bytes_and_state_backup_survive_later_clock(
    owner_home: Path,
    skill_source: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent_skills.ensure_global_agent_skills()
    path = owner_home / ".agents/skills/spec-kitty/SKILL.md"
    path.chmod(0o644)
    path.write_text("user drift at T1")
    monkeypatch.setattr("time.time", lambda: 1_000_000_000.0)
    monkeypatch.setattr("time.time_ns", lambda: 1_000_000_000_000_000_000)
    baseline = agent_skills.assess_global_agent_skills()
    relative = path.relative_to(baseline.root.path).as_posix()
    assessment = agent_skills.assess_global_agent_skills(consent=ApplyConsent(overwrite_paths=(relative,)))
    backups = [e for e in assessment.effects if "/backups/state-" in e.path]
    assert backups

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Apply recollected or rerendered at T2")

    monkeypatch.setattr(agent_skills, "_discover_registry", forbidden)
    monkeypatch.setattr(agent_skills, "_get_cli_version", forbidden)
    monkeypatch.setattr("time.time", lambda: 2_000_000_000.0)
    monkeypatch.setattr("time.time_ns", lambda: 2_000_000_000_000_000_000)
    _apply_exact(assessment)
    backup_files = [e.destination for e in backups if e.after.kind == "file"]
    assert [p.read_bytes() for p in backup_files] == [b"user drift at T1"]


def test_missing_required_registry_is_incomplete_and_pure(owner_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_skills, "_discover_registry", lambda: None)
    before = snapshot({"home": owner_home})
    result = agent_skills.assess_global_agent_skills()
    assert not result.complete and result.diagnostics and not result.effects
    assert_unchanged(before, snapshot({"home": owner_home}))


def test_independent_equivalent_cold_homes_retain_same_asset_bytes(
    tmp_path: Path,
    skill_source: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from specify_cli.runtime.asset_preparation import PreparedAssets

    batches = []
    for label in ("first", "second"):
        home = tmp_path / label / "home"
        home.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))
        before = snapshot({"home": home})
        assessment = agent_skills.assess_global_agent_skills()
        assert isinstance(assessment.prepared, PreparedAssets)
        batches.append(tuple((w.effect.path, w.effect.after, w.content) for w in assessment.prepared.writes))
        assert_unchanged(before, snapshot({"home": home}))
        _apply_exact(assessment)
        assert not agent_skills.assess_global_agent_skills().effects
    assert batches[0] == batches[1]


@contextmanager
def _wp01_owner_observer(log: Path) -> Iterator[None]:
    """Bind WP01's exact audit callback at an owner API seam, without copying it.

    WP01 main wraps CLI execution only. Its unmodified nested callback supplies
    this supplemental owner-level observer; this is not public startup evidence.
    """
    from tests.upgrade.preview_support import write_observer

    source = ast.parse(inspect.getsource(write_observer.main))
    record = next(node for node in ast.walk(source) if isinstance(node, ast.FunctionDef) and node.name == "record")
    module = ast.fix_missing_locations(ast.Module(body=[record], type_ignores=[]))
    active = True
    with log.open("w") as stream:
        scope: dict[str, Any] = {"os": os, "json": json, "Any": Any, "EVENTS": write_observer.EVENTS, "policy": "deny", "descriptor": stream.fileno()}
        exec(compile(module, inspect.getfile(write_observer), "exec"), scope)
        callback = cast(Callable[[str, tuple[Any, ...]], None], scope["record"])

        def bounded(event: str, values: tuple[Any, ...]) -> None:
            if active:
                callback(event, values)

        sys.addaudithook(bounded)
        try:
            yield
        finally:
            active = False


def test_wp01_write_observer_denies_controls_and_all_owner_preparations(
    owner_home: Path,
    skill_source: Path,
    tmp_path: Path,
) -> None:
    control = tmp_path / "denied-control.log"
    with _wp01_owner_observer(control), pytest.raises(PermissionError, match="Observed write attempt"):
        (owner_home / "forbidden").write_text("write-delete must be observed")
    assert json.loads(control.read_text())["event"] == "open"
    assert not (owner_home / "forbidden").exists()
    log = tmp_path / "assessment-observer.log"
    before = snapshot({"home": owner_home})
    with _wp01_owner_observer(log):
        assessments = (
            bootstrap.assess_runtime(),
            agent_commands.assess_global_agent_commands(agent_keys=["claude"]),
            agent_skills.assess_global_agent_skills(),
        )
    assert all(a.complete and a.effects for a in assessments)
    assert log.read_bytes() == b""
    assert_unchanged(before, snapshot({"home": owner_home}))


def test_actual_slash_dispatch_retains_empty_selection_and_caller_root(owner_home: Path, tmp_path: Path) -> None:
    from specify_cli.tool_surface.model import SurfacePlan
    from specify_cli.tool_surface.operations import AssessmentInputs, OperationRoot
    from specify_cli.tool_surface.providers.slash_commands import SlashCommandsProvider, slash_command_definition
    from specify_cli.tool_surface.repair import SurfaceRepairService

    project = tmp_path / "project"
    project.mkdir()
    inputs = AssessmentInputs(OperationRoot("project", "project", project))
    definition = slash_command_definition()
    service = SurfaceRepairService((SlashCommandsProvider(),))
    plans = (SurfacePlan("claude", (), "T1", (definition,)),)
    assessments = service.assess(inputs, (), plans=plans)
    assert len(assessments) == 1 and assessments[0].root == inputs.root
    assert assessments[0].complete and assessments[0].effects
    assert all("claude" in effect.logical_owners for effect in assessments[0].effects)
    results = service.apply_assessments(assessments * 2, ApplyConsent(automatic=True))
    assert len(results) == 1 and results[0].outcome == "applied"
    assert not service.assess(inputs, (), plans=plans)[0].effects


def test_late_io_failure_keeps_actual_ids_and_never_stamps(
    owner_home: Path,
    skill_source: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from specify_cli.runtime import asset_preparation

    assessment = agent_skills.assess_global_agent_skills()
    original = asset_preparation._write_asset
    written: list[str] = []

    def fail_after_some_content(write: asset_preparation.AssetWrite) -> None:
        if write.effect.after.kind == "file" and written:
            raise OSError("injected disk failure")
        original(write)
        if write.effect.after.kind == "file":
            written.append(write.effect.id)

    monkeypatch.setattr(asset_preparation, "_write_asset", fail_after_some_content)
    result = apply_assets(assessment, ApplyConsent(automatic=True))
    assert result.outcome == "partial" and set(written) <= set(result.succeeded)
    assert result.failed and result.skipped and result.diagnostics[0].message == "injected disk failure"
    assert not (owner_home / ".kittify/cache/agent-skills.lock").exists()
    assert not (owner_home / ".kittify/cache/global_skills-assets.json").exists()


def test_backup_collision_and_owned_link_conversion_preserve_target(
    owner_home: Path,
    skill_source: Path,
) -> None:
    agent_skills.ensure_global_agent_skills()
    path = owner_home / ".agents/skills/spec-kitty/SKILL.md"
    external = owner_home / "external"
    external.write_text("external bytes")
    path.unlink()
    path.symlink_to(external)
    initial = agent_skills.assess_global_agent_skills()
    relative = path.relative_to(initial.root.path).as_posix()
    consent = ApplyConsent(overwrite_paths=(relative,))
    first = agent_skills.assess_global_agent_skills(consent=consent)
    backup = next(e.destination for e in first.effects if "/backups/state-" in e.path and e.after.kind == "symlink")
    state_root = next(p for p in backup.parents if p.name.startswith("state-"))
    state_root.mkdir(parents=True)
    (state_root / "sentinel").write_text("older backup")
    second = agent_skills.assess_global_agent_skills(consent=consent)
    assert any(state_root.name + "-1" in e.path for e in second.effects)
    before = snapshot({"external": external, "old-backup": state_root})
    _apply_exact(second)
    assert path.is_file() and not path.is_symlink()
    assert_unchanged(before, snapshot({"external": external, "old-backup": state_root}))


def test_stale_marker_with_exact_canonical_body_is_repaired(owner_home: Path) -> None:
    import re

    agent_commands.ensure_global_agent_commands(agent_keys=["claude"])
    target = owner_home / ".claude/commands/spec-kitty.plan.md"
    target.chmod(0o644)
    target.write_bytes(re.sub(rb"spec-kitty-command-version: [^\r\n]+ -->", b"spec-kitty-command-version: 0.0.1 -->", target.read_bytes()))
    inventory = owner_home / ".kittify/cache/slash_commands-assets.json"
    inventory.unlink()
    assessment = agent_commands.assess_global_agent_commands(agent_keys=["claude"])
    assert any(e.destination == target and e.action == "update" for e in assessment.effects)
    _apply_exact(assessment)


def test_orphan_atomic_artifact_is_incomplete_and_never_changed(owner_home: Path, skill_source: Path) -> None:
    from specify_cli.runtime.generated_writer import generated_temporary_path

    target = owner_home / ".agents/skills/spec-kitty/SKILL.md"
    target.parent.mkdir(parents=True)
    artifact = generated_temporary_path(target)
    artifact.write_bytes(b"unproven ignored content")
    before = snapshot({"home": owner_home})
    assessment = agent_skills.assess_global_agent_skills()
    assert not assessment.complete and "artifact" in assessment.diagnostics[0].message
    result = apply_assets(assessment, ApplyConsent(automatic=True))
    assert result.outcome == "failed"
    assert_unchanged(before, snapshot({"home": owner_home}))


def test_inventory_change_refuses_whole_batch(owner_home: Path, skill_source: Path) -> None:
    agent_skills.ensure_global_agent_skills()
    (owner_home / ".agents/skills/spec-kitty/SKILL.md").unlink()
    assessment = agent_skills.assess_global_agent_skills()
    inventory = owner_home / ".kittify/cache/global_skills-assets.json"
    inventory.write_bytes(inventory.read_bytes() + b"\n")
    before = snapshot({"home": owner_home})
    result = apply_assets(assessment, ApplyConsent(automatic=True))
    assert result.outcome == "precondition_changed" and not result.succeeded
    assert_unchanged(before, snapshot({"home": owner_home}))


def test_source_catalog_addition_refuses_whole_batch(owner_home: Path, skill_source: Path) -> None:
    assessment = agent_skills.assess_global_agent_skills()
    new_skill = skill_source / "new-canonical-skill"
    new_skill.mkdir()
    (new_skill / "SKILL.md").write_text("# Added after assessment\n")
    before = snapshot({"home": owner_home})
    result = apply_assets(assessment, ApplyConsent(automatic=True))
    assert result.outcome == "precondition_changed" and not result.succeeded
    assert_unchanged(before, snapshot({"home": owner_home}))


@pytest.mark.parametrize("through_provider", [False, True])
def test_command_effects_retain_their_physical_agent_owners(owner_home: Path, tmp_path: Path, through_provider: bool) -> None:
    from specify_cli.tool_surface.model import SurfacePlan
    from specify_cli.tool_surface.operations import AssessmentInputs, OperationRoot
    from specify_cli.tool_surface.providers.slash_commands import SlashCommandsProvider, slash_command_definition
    from specify_cli.tool_surface.repair import SurfaceRepairService

    keys = ("claude", "gemini")
    if through_provider:
        project = tmp_path / "project"
        project.mkdir()
        inputs = AssessmentInputs(OperationRoot("project", "project", project))
        definition = slash_command_definition()
        provider = SlashCommandsProvider()
        service = SurfaceRepairService((provider,))
        plans = tuple(SurfacePlan(key, (), "T1", (definition,)) for key in keys)
        statuses = tuple(provider.probe(provider.expand(definition, key, project)[0]) for key in keys)
        assessment = service.assess(inputs, statuses, plans=plans)[0]
        frames = next(observation.value for observation in assessment.inputs_fingerprint if observation.name == "provider_instances")
        assert isinstance(frames, tuple) and frames == tuple((s.instance, s.state) for s in statuses)
        assert frames[0][0] is statuses[0].instance
    else:
        assessment = agent_commands.assess_global_agent_commands(agent_keys=list(keys))
    assert assessment.complete
    for key in keys:
        directory = agent_commands.get_global_command_dir(key)
        files = [effect for effect in assessment.effects if effect.destination.parent == directory and effect.after.kind == "file"]
        assert files
        assert all(effect.logical_owners == (key,) for effect in files)
        if through_provider:
            from specify_cli.tool_surface.status import _surface_id

            expected_ids = tuple(_surface_id(status.instance) for status in statuses if status.instance.owner == key)
            assert all(effect.surface_ids == expected_ids for effect in files)
    if through_provider:
        result = service.apply_assessments((assessment,), ApplyConsent(automatic=True))
        assert result[0].outcome == "applied"
    else:
        _apply_exact(assessment)


def test_installed_skill_catalog_prepares_under_write_denial(owner_home: Path, tmp_path: Path) -> None:
    """Real package/local resolver, not the fixture-selected registry seam."""
    log = tmp_path / "installed-catalog-observer.log"
    before = snapshot({"home": owner_home})
    with _wp01_owner_observer(log):
        assessment = agent_skills.assess_global_agent_skills()
    assert assessment.complete and assessment.effects
    assert log.read_bytes() == b""
    assert_unchanged(before, snapshot({"home": owner_home}))
