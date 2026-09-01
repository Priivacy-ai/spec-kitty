"""Integration tests for the public ``spec-kitty dispatch`` surface."""

from __future__ import annotations

import json
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from click.testing import Result
from ruamel.yaml import YAML
from typer import Typer
from typer.testing import CliRunner

from charter.activation.pack_context import PackContext
from glossary.chokepoint import GlossaryObservationBundle
from glossary.models import ConflictType, SemanticConflict, SenseRef, Severity, TermSurface
from specify_cli import app as cli_app
from specify_cli.invocation.modes import ModeOfWork, derive_mode
from specify_cli.invocation.writer import EVENTS_DIR, InvocationWriter

pytestmark = [pytest.mark.non_sandbox, pytest.mark.fast]

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "profiles"


class ArgvCliRunner(CliRunner):
    def invoke(  # type: ignore[override]
        self,
        app: Typer,
        args: str | Sequence[str] | None = None,
        **kwargs: Any,
    ) -> Result:
        argv = ["spec-kitty", *(list(args) if args is not None and not isinstance(args, str) else [])]
        with patch.object(sys, "argv", argv):
            return super().invoke(app, args, **kwargs)


runner = ArgvCliRunner()

_COMPACT_CTX = MagicMock()
_COMPACT_CTX.mode = "compact"
_COMPACT_CTX.text = "compact governance context"

_MISSING_CTX = MagicMock()
_MISSING_CTX.mode = "missing"
_MISSING_CTX.text = ""


def _setup_project(tmp_path: Path) -> Path:
    profiles_dir = tmp_path / ".kittify" / "profiles"
    profiles_dir.mkdir(parents=True)
    for yaml_file in FIXTURES_DIR.glob("*.agent.yaml"):
        shutil.copy(yaml_file, profiles_dir / yaml_file.name)
    return tmp_path


def _write_configured_charter(project: Path) -> None:
    """Write a project charter that is genuinely routable (not empty-for-dispatch).

    WP02/#3064, updated for NFR-004/#3104: ``resolve_generic_fallback`` reads
    the REAL project charter on disk (not any mocked ``ProfileRegistry``). A
    project fixture with no charter configured at all is genuinely
    "empty charter" and would now auto-route to ``generic-agent`` -- tests
    exercising the mocked-router auto-route path need a charter the NEW
    bundle-presence + org-pack-safe predicate (``specify_cli.invocation.
    empty_charter.is_charter_empty``) treats as routable, so they keep
    proving router behaviour, not the empty-charter fallback (which has its
    own dedicated tests below).

    The predicate drops non-routing dimensions (``activated_directives``
    included) -- a directive-only config.yaml no longer suffices. This writes
    both an ``activated_directives`` key (kept for fixture-history parity;
    exercises no bearing on the predicate) AND a compiled-bundle presence
    stub at ``.kittify/charter/charter.yaml`` (presence-only per the
    predicate contract -- content is a near-empty placeholder, never
    inspected), which is what actually makes ``is_charter_empty`` return
    ``False`` here.
    """
    kittify = project / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    with (kittify / "config.yaml").open("w", encoding="utf-8") as fh:
        YAML().dump({"activated_directives": ["028-efficient-local-tooling"]}, fh)
    charter_dir = kittify / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    (charter_dir / "charter.yaml").write_text("{}\n", encoding="utf-8")


def _make_mock_registry(profile_specs: list[dict[str, object]]) -> MagicMock:
    from charter.offering.agent_profiles.profile import Role

    mock_profiles = []
    for spec in profile_specs:
        profile = MagicMock()
        profile.profile_id = spec["profile_id"]
        profile.role = Role(str(spec["role_value"]))
        profile.routing_priority = spec.get("routing_priority", 50)
        profile.name = spec.get("name", spec["profile_id"])

        specialization = MagicMock()
        specialization.domain_keywords = spec.get("domain_keywords", [])
        profile.specialization_context = specialization

        collaboration = MagicMock()
        collaboration.canonical_verbs = spec.get("collab_verbs", [])
        profile.collaboration = collaboration

        mock_profiles.append(profile)

    registry = MagicMock()
    registry.list_all.return_value = mock_profiles

    def _get(profile_id: str) -> object | None:
        return next((profile for profile in mock_profiles if profile.profile_id == profile_id), None)

    def _resolve(profile_id: str) -> object:
        from specify_cli.invocation.errors import ProfileNotFoundError

        profile = _get(profile_id)
        if profile is None:
            raise ProfileNotFoundError(profile_id, [p.profile_id for p in mock_profiles])
        return profile

    registry.get.side_effect = _get
    registry.resolve.side_effect = _resolve
    return registry


def _implementer_registry() -> MagicMock:
    return _make_mock_registry(
        [
            {
                "profile_id": "implementer-fixture",
                "role_value": "implementer",
                "routing_priority": 50,
                "name": "Implementer (fixture)",
                "domain_keywords": ["implement", "build", "code"],
            }
        ]
    )


def _high_severity_bundle() -> GlossaryObservationBundle:
    conflict = SemanticConflict(
        term=TermSurface("lane"),
        conflict_type=ConflictType.AMBIGUOUS,
        severity=Severity.HIGH,
        confidence=1.0,
        candidate_senses=[
            SenseRef(surface="lane", scope="spec_kitty_core", definition="Execution lane", confidence=1.0),
            SenseRef(surface="lane", scope="team_domain", definition="Worktree lane", confidence=1.0),
        ],
        context="request_text",
    )
    return GlossaryObservationBundle(
        matched_urns=("glossary:d93244e7",),
        high_severity=(conflict,),
        all_conflicts=(conflict,),
        tokens_checked=3,
        duration_ms=1.5,
        error_msg=None,
    )


def _run(project: Path, args: list[str], *, ctx: MagicMock = _COMPACT_CTX) -> Result:
    with (
        patch("specify_cli.cli.commands.dispatch.find_repo_root", return_value=project),
        patch("specify_cli.invocation.executor.build_charter_context", return_value=ctx),
    ):
        return runner.invoke(cli_app, args)


def _run_with_registry(project: Path, args: list[str], registry: MagicMock) -> Result:
    with (
        patch("specify_cli.cli.commands.dispatch.find_repo_root", return_value=project),
        patch("specify_cli.cli.commands.dispatch.ProfileRegistry", return_value=registry),
        patch("specify_cli.invocation.executor.build_charter_context", return_value=_COMPACT_CTX),
    ):
        return runner.invoke(cli_app, args)


def _invoke_json(project: Path, args: list[str], *, ctx: MagicMock = _COMPACT_CTX) -> dict[str, Any]:
    result = _run(project, args, ctx=ctx)
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def _read_op_record(project: Path, invocation_id: str) -> list[dict[str, Any]]:
    path = InvocationWriter(project).invocation_path(invocation_id)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_dispatch_with_profile_opens_task_execution_op(tmp_path: Path) -> None:
    project = _setup_project(tmp_path)

    envelope = _invoke_json(
        project,
        ["dispatch", "implement the feature", "--profile", "implementer-fixture", "--json"],
    )

    record = _read_op_record(project, str(envelope["invocation_id"]))[0]
    assert envelope["status"] == "open"
    assert envelope["governance_context_text"] == "compact governance context"
    assert envelope["close_contract"]["evidence_flag"] == "--evidence"
    assert record["mode_of_work"] == "task_execution"
    assert record["profile_id"] == "implementer-fixture"
    assert record["request_text"] == "implement the feature"


def test_dispatch_auto_routes_and_writes_single_started_record(tmp_path: Path) -> None:
    project = _setup_project(tmp_path)
    _write_configured_charter(project)
    result = _run_with_registry(
        project,
        ["dispatch", "implement the payment module", "--json"],
        _implementer_registry(),
    )

    assert result.exit_code == 0, result.output
    envelope = json.loads(result.output)
    events = _read_op_record(project, str(envelope["invocation_id"]))
    assert envelope["profile_id"] == "implementer-fixture"
    assert envelope["router_confidence"] == "canonical_verb"
    assert [event["event"] for event in events] == ["started"]


def test_dispatch_no_charter_still_opens_record(tmp_path: Path) -> None:
    project = _setup_project(tmp_path)

    envelope = _invoke_json(
        project,
        ["dispatch", "implement the feature", "--profile", "implementer-fixture", "--json"],
        ctx=_MISSING_CTX,
    )

    record = _read_op_record(project, str(envelope["invocation_id"]))[0]
    assert envelope["governance_context_available"] is False
    assert record["governance_context_available"] is False


def test_dispatch_rich_output_includes_governance_and_close_contract(tmp_path: Path) -> None:
    project = _setup_project(tmp_path)
    with (
        patch("specify_cli.cli.commands.dispatch.find_repo_root", return_value=project),
        patch("specify_cli.invocation.executor.build_charter_context", return_value=_COMPACT_CTX),
        patch("glossary.chokepoint.GlossaryChokepoint.run", return_value=_high_severity_bundle()),
    ):
        result = runner.invoke(
            cli_app,
            ["dispatch", "implement the feature", "--profile", "implementer-fixture"],
        )

    assert result.exit_code == 0, result.output
    flat = result.output.replace("\n", " ")
    assert "High-severity terminology conflicts detected before this invocation." in result.output
    assert result.output.index("lane (ambiguous)") < result.output.index("compact governance context")
    assert "This Op is OPEN" in flat
    assert "profile-invocation complete" in flat
    assert "git add" not in flat


def test_dispatch_missing_profile_exits_1_with_routing_error(tmp_path: Path) -> None:
    project = _setup_project(tmp_path)

    result = _run(
        project,
        ["dispatch", "implement", "--profile", "nonexistent-profile", "--json"],
    )

    assert result.exit_code == 1
    error_obj = json.loads(result.output)
    assert error_obj["error"] == "routing_failed"
    assert error_obj["error_code"] == "PROFILE_NOT_FOUND"
    assert "spec-kitty profiles list" in error_obj["suggestion"]


def test_only_dispatch_is_registered_as_standalone_opener() -> None:
    assert runner.invoke(cli_app, ["dispatch", "--help"]).exit_code == 0
    for removed_command in ("do", "ask", "advise"):
        assert runner.invoke(cli_app, [removed_command, "--help"]).exit_code != 0


def test_entry_command_mode_mapping_only_has_dispatch_for_standalone_openers() -> None:
    assert derive_mode("dispatch") is ModeOfWork.TASK_EXECUTION
    for removed_command in ("do", "ask", "advise"):
        with pytest.raises(KeyError):
            derive_mode(removed_command)


def test_dispatch_writes_single_jsonl_file(tmp_path: Path) -> None:
    project = _setup_project(tmp_path)
    envelope = _invoke_json(
        project,
        ["dispatch", "implement the feature", "--profile", "implementer-fixture", "--json"],
    )
    jsonl = [p for p in (project / EVENTS_DIR).glob("*.jsonl") if p.name != "ops-index.jsonl"]
    assert len(jsonl) == 1
    assert jsonl[0].stem == str(envelope["invocation_id"])


# ---------------------------------------------------------------------------
# WP02/#3064 — empty-charter generic-agent routing fallback + warning
# ---------------------------------------------------------------------------
#
# These use the REAL ProfileRegistry/ActionRouter (no mocked registry): the
# fixture project from `_setup_project` carries no `.kittify/config.yaml`,
# which is a genuinely empty charter under the composite predicate
# (research.md Decision 3), and `generic-agent`/`architect-alphonso` are real
# shipped built-in profiles so resolution needs no mock.


def test_dispatch_empty_charter_auto_routes_to_generic_agent(tmp_path: Path) -> None:
    """No --profile hint, wholly-empty charter -> pins generic-agent (Decision 2/3)."""
    project = _setup_project(tmp_path)

    envelope = _invoke_json(project, ["dispatch", "implement the payment module", "--json"])

    assert envelope["profile_id"] == "generic-agent"
    assert envelope["router_confidence"] == "generic_fallback"
    assert envelope["action"] == "implement"
    assert envelope["empty_charter_fallback"] is True


def test_dispatch_empty_charter_rich_output_shows_warning_panel(tmp_path: Path) -> None:
    """The one-shot warning (Decision 5) renders in the rich (non-JSON) path.

    The wording is honest about what applying a pack does and does not do
    (#3064 follow-up): it must not promise a working dispatch route --
    applying a pack only records activations in config.yaml, and an
    unmatched request may still need an explicit --profile.
    """
    project = _setup_project(tmp_path)

    result = _run(project, ["dispatch", "implement the payment module"])

    assert result.exit_code == 0, result.output
    assert "Empty Charter" in result.output
    assert "generic-agent" in result.output
    assert "charter pack apply minimal" in result.output
    # Honest caveat: applying a pack is not a promise of a working dispatch.
    assert "--profile" in result.output


def test_dispatch_explicit_profile_bypasses_empty_charter_fallback(tmp_path: Path) -> None:
    """An explicit --profile hint resolves the specialist normally under an empty
    charter -- the fallback pre-check only engages on the no-hint auto-route
    branch (research.md Decision 2); it must never override an explicit hint.
    """
    project = _setup_project(tmp_path)

    envelope = _invoke_json(
        project,
        ["dispatch", "design the system architecture", "--profile", "architect-alphonso", "--json"],
    )

    assert envelope["profile_id"] == "architect-alphonso"
    assert envelope["empty_charter_fallback"] is False

    result = _run(project, ["dispatch", "design the system architecture", "--profile", "architect-alphonso"])
    assert result.exit_code == 0, result.output
    assert "Empty Charter" not in result.output


def test_dispatch_empty_charter_still_routes_despite_empty_mission_type_activation(
    tmp_path: Path,
) -> None:
    """Dispatch routing is independent of mission-type activation.

    WP04 (C-A1) retired the "absence admits all built-ins" convenience
    default for ``mission_type_activations`` specifically (#2657): an absent
    or empty key now reads as ``frozenset()``, not "all built-in mission
    types." The actionable fail-closed for that empty set lives at the
    mission-create / mission-type-use boundary
    (``specify_cli.core.mission_creation.create_mission_core``) -- a
    dimension ``spec-kitty dispatch`` never touches. Dispatch routes purely
    through the ``ProfileRegistry`` / ``ActionRouter`` (proven by the
    empty-charter generic-agent fallback tests above); it has no dependency
    on mission-type activation at all. So under the very same empty-charter
    repo those tests exercise: mission-type activation is genuinely empty
    (not "all built-ins"), AND dispatch still functions end-to-end via its
    profile-routing fallback.
    """
    project = _setup_project(tmp_path)

    pack_context = PackContext.from_config(project)
    assert pack_context.activated_mission_types == frozenset()
    assert "software-dev" not in pack_context.activated_mission_types

    envelope = _invoke_json(project, ["dispatch", "implement the payment module", "--json"])

    assert envelope["profile_id"] == "generic-agent"
    assert envelope["router_confidence"] == "generic_fallback"
    assert envelope["empty_charter_fallback"] is True
