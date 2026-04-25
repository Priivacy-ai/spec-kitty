"""Unit tests for :mod:`specify_cli.mission_loader.command` (T028).

Locks the exit-code matrix and the wire shape of the JSON envelope per
``contracts/mission-run-cli.md``. The functional core is exercised
directly without the Typer wrapper; the Typer rendering is covered by
the JSON-format test (which calls ``_render_envelope`` directly) and
by the integration tests in WP06.
"""

from __future__ import annotations

import io
import json
import textwrap
from collections.abc import Iterator
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from specify_cli.mission_loader.command import (
    RunCustomMissionResult,
    run_custom_mission,
)
from specify_cli.mission_loader.registry import get_runtime_contract_registry
from specify_cli.next._internal_runtime.discovery import DiscoveryContext

# Minimal valid custom mission body. Last step is the retrospective marker
# so structural checks pass; the planning step has an agent_profile binding.
_VALID_BODY = """
mission:
  key: {key}
  name: {name}
  version: "1.0.0"
steps:
  - id: plan
    title: Plan
    agent_profile: planner
  - id: retrospective
    title: Retrospective
    agent_profile: retro
"""

# Body with the retrospective marker missing.
_NO_RETRO_BODY = """
mission:
  key: {key}
  name: {name}
  version: "1.0.0"
steps:
  - id: plan
    title: Plan
    agent_profile: planner
  - id: write-report
    title: Write Report
    agent_profile: scribe
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_registry() -> Iterator[None]:
    """Clear the singleton registry before and after each test."""
    get_runtime_contract_registry().clear()
    yield
    get_runtime_contract_registry().clear()


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip discovery env vars so tests cannot pull in side-channel paths."""
    monkeypatch.delenv("SPEC_KITTY_MISSION_PATHS", raising=False)


def _write_mission(repo_root: Path, layer: str, key: str, body: str) -> Path:
    mission_dir = repo_root / layer / key
    mission_dir.mkdir(parents=True, exist_ok=True)
    file = mission_dir / "mission.yaml"
    file.write_text(
        textwrap.dedent(body.format(key=key, name=key.replace("-", " ").title())).lstrip(),
        encoding="utf-8",
    )
    return file


def _isolated_context(
    repo_root: Path, *, builtin_roots: list[Path] | None = None
) -> DiscoveryContext:
    """Build a DiscoveryContext that ignores the user's real ~/.kittify."""
    fake_home = repo_root / ".fake-home"
    fake_home.mkdir(exist_ok=True)
    return DiscoveryContext(
        project_dir=repo_root,
        user_home=fake_home,
        builtin_roots=list(builtin_roots or []),
    )


class _FakeRunRef:
    """Minimal stand-in for ``MissionRunRef`` used in monkeypatch paths."""

    def __init__(self, run_id: str, run_dir: str) -> None:
        self.run_id = run_id
        self.run_dir = run_dir


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_happy_path_returns_zero_and_success_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_mission(repo_root, ".kittify/missions", "erp-integration", _VALID_BODY)

    # meta.json with a mission_id so the envelope reflects the real value.
    feature_dir = repo_root / "kitty-specs" / "erp-q3-rollout-01KQABC"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_id": "01KQABCDEFGHJKMNPQRSTVWXYZ"}),
        encoding="utf-8",
    )

    fake_run_dir = tmp_path / "runs" / "abc"
    fake_run_dir.mkdir(parents=True)
    captured: dict[str, object] = {}

    def fake_get_or_start_run(*, mission_slug: str, repo_root: Path, mission_type: str) -> _FakeRunRef:
        captured["mission_slug"] = mission_slug
        captured["repo_root"] = repo_root
        captured["mission_type"] = mission_type
        return _FakeRunRef(run_id="abc", run_dir=str(fake_run_dir))

    from specify_cli.next import runtime_bridge

    monkeypatch.setattr(runtime_bridge, "get_or_start_run", fake_get_or_start_run)

    ctx = _isolated_context(repo_root)
    result = run_custom_mission(
        "erp-integration",
        "erp-q3-rollout-01KQABC",
        repo_root,
        discovery_context=ctx,
    )

    assert isinstance(result, RunCustomMissionResult)
    assert result.exit_code == 0
    env = result.envelope
    assert env["result"] == "success"
    assert env["mission_key"] == "erp-integration"
    assert env["mission_slug"] == "erp-q3-rollout-01KQABC"
    assert env["mission_id"] == "01KQABCDEFGHJKMNPQRSTVWXYZ"
    assert env["feature_dir"] == str(feature_dir)
    assert env["run_dir"] == str(fake_run_dir)
    assert env["warnings"] == []

    # Bridge invoked with the right wiring.
    assert captured["mission_slug"] == "erp-q3-rollout-01KQABC"
    assert captured["mission_type"] == "erp-integration"
    assert captured["repo_root"] == repo_root

    # Synthesized contracts registered in the shadow.
    registry = get_runtime_contract_registry()
    assert registry.lookup("custom:erp-integration:plan") is not None


def test_happy_path_with_no_meta_json_returns_null_mission_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_mission(repo_root, ".kittify/missions", "erp-integration", _VALID_BODY)

    fake_run_dir = tmp_path / "runs" / "x"
    fake_run_dir.mkdir(parents=True)

    from specify_cli.next import runtime_bridge

    monkeypatch.setattr(
        runtime_bridge,
        "get_or_start_run",
        lambda **_: _FakeRunRef(run_id="x", run_dir=str(fake_run_dir)),
    )

    ctx = _isolated_context(repo_root)
    result = run_custom_mission(
        "erp-integration", "tracked-mission-slug", repo_root, discovery_context=ctx
    )
    assert result.exit_code == 0
    assert result.envelope["mission_id"] is None


# ---------------------------------------------------------------------------
# Validation errors (exit code 2)
# ---------------------------------------------------------------------------


def test_validation_error_returns_two_with_error_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_mission(repo_root, ".kittify/missions", "no-retro", _NO_RETRO_BODY)

    # If runtime_bridge is invoked we want the test to fail fast.
    from specify_cli.next import runtime_bridge

    def _should_not_run(**_: object) -> _FakeRunRef:  # pragma: no cover - guard
        raise AssertionError("get_or_start_run must not be called on validation error")

    monkeypatch.setattr(runtime_bridge, "get_or_start_run", _should_not_run)

    ctx = _isolated_context(repo_root)
    result = run_custom_mission("no-retro", "any-slug", repo_root, discovery_context=ctx)

    assert result.exit_code == 2
    env = result.envelope
    assert env["result"] == "error"
    assert env["error_code"] == "MISSION_RETROSPECTIVE_MISSING"
    assert env["details"]["mission_key"] == "no-retro"
    assert env["details"]["expected"] == "retrospective"
    assert env["details"]["actual_last_step_id"] == "write-report"
    assert env["warnings"] == []

    # Registry stays untouched on validation error.
    assert not get_runtime_contract_registry()._contracts  # type: ignore[attr-defined]


def test_unknown_key_returns_two_with_MISSION_KEY_UNKNOWN(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    # No mission YAMLs at all.
    ctx = _isolated_context(repo_root)
    result = run_custom_mission("nope", "any-slug", repo_root, discovery_context=ctx)
    assert result.exit_code == 2
    assert result.envelope["error_code"] == "MISSION_KEY_UNKNOWN"
    assert result.envelope["details"]["mission_key"] == "nope"
    assert "tiers_searched" in result.envelope["details"]


# ---------------------------------------------------------------------------
# Run-start exception (exit code 1)
# ---------------------------------------------------------------------------


def test_run_start_failure_returns_one_with_RUN_START_FAILED(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_mission(repo_root, ".kittify/missions", "ok-mission", _VALID_BODY)

    from specify_cli.next import runtime_bridge

    def _boom(**_: object) -> _FakeRunRef:
        raise RuntimeError("disk full")

    monkeypatch.setattr(runtime_bridge, "get_or_start_run", _boom)

    ctx = _isolated_context(repo_root)
    result = run_custom_mission(
        "ok-mission", "tracked-slug", repo_root, discovery_context=ctx
    )
    assert result.exit_code == 1
    env = result.envelope
    assert env["result"] == "error"
    assert env["error_code"] == "RUN_START_FAILED"
    assert "disk full" in env["message"]
    assert env["details"] == {
        "mission_key": "ok-mission",
        "mission_slug": "tracked-slug",
    }
    assert env["warnings"] == []

    # Registry was cleared after the failure to avoid stale shadow state.
    assert not get_runtime_contract_registry()._contracts  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Warnings pass through
# ---------------------------------------------------------------------------


def test_warnings_pass_through_on_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two tiers define the same key; the higher tier wins and a shadow
    warning surfaces in the success envelope."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    # Both tiers carry the same key so we trigger MISSION_KEY_SHADOWED.
    _write_mission(repo_root, ".kittify/missions", "shadowy", _VALID_BODY)
    _write_mission(repo_root, ".kittify/overrides/missions", "shadowy", _VALID_BODY)

    fake_run_dir = tmp_path / "runs" / "y"
    fake_run_dir.mkdir(parents=True)

    from specify_cli.next import runtime_bridge

    monkeypatch.setattr(
        runtime_bridge,
        "get_or_start_run",
        lambda **_: _FakeRunRef(run_id="y", run_dir=str(fake_run_dir)),
    )

    ctx = _isolated_context(repo_root)
    result = run_custom_mission(
        "shadowy", "tracked-slug", repo_root, discovery_context=ctx
    )
    assert result.exit_code == 0
    warnings = result.envelope["warnings"]
    assert len(warnings) == 1
    assert warnings[0]["code"] == "MISSION_KEY_SHADOWED"
    assert warnings[0]["details"]["mission_key"] == "shadowy"
    assert warnings[0]["details"]["selected_tier"] == "project_override"


# ---------------------------------------------------------------------------
# JSON rendering
# ---------------------------------------------------------------------------


def test_render_envelope_json_format() -> None:
    """``_render_envelope`` with ``json_output=True`` writes parseable JSON."""
    from specify_cli.cli.commands.mission_type import _render_envelope

    envelope = {
        "result": "success",
        "mission_key": "erp",
        "mission_slug": "slug",
        "mission_id": None,
        "feature_dir": "/tmp/feature",
        "run_dir": "/tmp/run",
        "warnings": [],
    }
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        _render_envelope(envelope, json_output=True)
    output = buffer.getvalue()
    parsed = json.loads(output)
    assert parsed == envelope


def test_render_envelope_human_format_success() -> None:
    """``_render_envelope`` with ``json_output=False`` does not raise and
    renders something to the rich console."""
    from specify_cli.cli.commands.mission_type import _render_envelope

    envelope = {
        "result": "success",
        "mission_key": "erp",
        "mission_slug": "slug",
        "mission_id": "01KMID",
        "feature_dir": "/tmp/feature",
        "run_dir": "/tmp/run",
        "warnings": [{"code": "MISSION_KEY_SHADOWED", "message": "hi", "details": {}}],
    }
    # No stdout assertion -- just that the call completes without error.
    _render_envelope(envelope, json_output=False)


def test_render_envelope_human_format_error() -> None:
    from specify_cli.cli.commands.mission_type import _render_envelope

    envelope = {
        "result": "error",
        "error_code": "MISSION_RETROSPECTIVE_MISSING",
        "message": "boom",
        "details": {"mission_key": "x", "expected": "retrospective"},
        "warnings": [],
    }
    _render_envelope(envelope, json_output=False)


# ---------------------------------------------------------------------------
# Default discovery context construction
# ---------------------------------------------------------------------------


def test_default_discovery_context_is_built_when_none_supplied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When ``discovery_context`` is not provided we fall back to the
    repo-root-derived context. Exercises the `_build_discovery_context`
    helper without requiring a real built-in tree."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    # Place a custom mission in the project tier so the builtin tree is
    # irrelevant for resolution.
    _write_mission(repo_root, ".kittify/missions", "ok-mission", _VALID_BODY)

    fake_run_dir = tmp_path / "runs" / "z"
    fake_run_dir.mkdir(parents=True)

    from specify_cli.next import runtime_bridge

    monkeypatch.setattr(
        runtime_bridge,
        "get_or_start_run",
        lambda **_: _FakeRunRef(run_id="z", run_dir=str(fake_run_dir)),
    )
    # Make sure the user-home tier cannot leak in real missions.
    monkeypatch.setenv("HOME", str(tmp_path / "fake-home"))
    (tmp_path / "fake-home").mkdir(exist_ok=True)

    result = run_custom_mission("ok-mission", "tracked-slug", repo_root)
    assert result.exit_code == 0
    assert result.envelope["mission_key"] == "ok-mission"
