"""Direct unit tests for the setup-plan phase helpers (#2056 WP06, T022/T025).

The pre-decomposition ``setup_plan`` was a 507-LOC monolith; WP06 split it into
≤15-CC phase helpers. These tests exercise each helper's branches in isolation:
the SaaS auth refusal + boundary preflight gates, feature-dir resolution, the
spec gate, the plan-template scaffold, the plan-commit branch, the documentation
wiring no-op, and the result emitter. The relocated planning-commit helpers
(``_kind_for_artifact``, ``_artifact_absent_at_placement``, etc.) keep their
existing coverage via ``test_kind_for_artifact.py`` and
``test_agent_mission_commit_to_branch.py``; the end-to-end command stays pinned
by ``test_agent_feature.py``, ``test_mission_planning_entry.py`` and the WP01
golden harness.
"""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import Any, cast

import pytest
import typer

from charter.mission_type_profiles import ResolvedMissionType
from charter.resolution import ResolutionResult, ResolutionTier
from specify_cli.cli.commands.agent import mission_setup_plan as seam
from specify_cli.mission_metadata import OnMalformed, load_meta as canonical_load_meta
from specify_cli.runtime.resolver import TemplateConfigurationError

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_DEFAULT_TEMPLATE_SET = object()


def _resolved_mission_type(
    *,
    mission_type: str | None = "software-dev",
    template_set: dict[str, str] | None | object = _DEFAULT_TEMPLATE_SET,
) -> ResolvedMissionType:
    mapping = cast(
        dict[str, str] | None,
        {"spec": "spec-template.md", "plan": "mapped-plan.md"} if template_set is _DEFAULT_TEMPLATE_SET else template_set,
    )

    def _template_set() -> MappingProxyType[str, str] | None:
        return None if mapping is None else MappingProxyType(mapping)

    return ResolvedMissionType(
        mission_type=mission_type,
        governance_text="",
        action_sequence=["specify", "plan"],
        provenance="test",
        _template_set_thunk=(None if mission_type is None else _template_set),
    )


def _resolution(path: Path) -> ResolutionResult:
    return ResolutionResult(
        path=path,
        tier=ResolutionTier.OVERRIDE,
        mission="software-dev",
    )


# ---------------------------------------------------------------------------
# _enforce_saas_sync_auth_refusal
# ---------------------------------------------------------------------------


def test_auth_refusal_noop_when_sync_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    # No exception even with no auth scope available.
    seam._enforce_saas_sync_auth_refusal(json_output=True)


def test_auth_refusal_exits_when_unauthenticated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setattr("specify_cli.sync.queue.read_queue_scope_from_session", lambda: None)
    monkeypatch.setattr("specify_cli.sync.queue.read_queue_scope_from_credentials", lambda: None)
    with pytest.raises(typer.Exit) as exc:
        seam._enforce_saas_sync_auth_refusal(json_output=True)
    assert exc.value.exit_code == 2


def test_auth_refusal_passes_with_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setattr("specify_cli.sync.queue.read_queue_scope_from_session", lambda: "scope-x")
    # Returns without raising (scope resolved).
    seam._enforce_saas_sync_auth_refusal(json_output=True)


# ---------------------------------------------------------------------------
# _enforce_saas_sync_boundary_preflight
# ---------------------------------------------------------------------------


def test_boundary_preflight_noop_when_sync_disabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    seam._enforce_saas_sync_boundary_preflight(tmp_path)


def test_boundary_preflight_exits_on_incoherence(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")

    class _Result:
        ok = False

        def render(self, _console: object) -> None:
            return None

    monkeypatch.setattr("specify_cli.sync.preflight.run_preflight", lambda **_k: _Result())
    with pytest.raises(typer.Exit) as exc:
        seam._enforce_saas_sync_boundary_preflight(tmp_path)
    assert exc.value.exit_code == 2


# ---------------------------------------------------------------------------
# _resolve_setup_plan_feature_dir
# ---------------------------------------------------------------------------


def test_resolve_feature_dir_auto_selects_sole(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent import mission as mission_mod

    monkeypatch.setattr(seam, "_sole_mission_slug_or_none", lambda _r: "001-demo")
    monkeypatch.setattr(mission_mod, "_find_feature_directory", lambda _r, _c, explicit_feature=None: tmp_path / explicit_feature)
    out = seam._resolve_setup_plan_feature_dir(tmp_path, None, json_output=True)
    assert out == tmp_path / "001-demo"


def test_resolve_feature_dir_emits_detection_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent import mission as mission_mod

    def _boom(*_a: object, **_k: object) -> Path:
        raise ValueError("ambiguous")

    monkeypatch.setattr(seam, "_sole_mission_slug_or_none", lambda _r: None)
    monkeypatch.setattr(mission_mod, "_find_feature_directory", _boom)
    monkeypatch.setattr(seam, "_build_setup_plan_detection_error", lambda *a, **k: {"error": "ambiguous"})
    with pytest.raises(typer.Exit):
        seam._resolve_setup_plan_feature_dir(tmp_path, None, json_output=True)


# ---------------------------------------------------------------------------
# _enforce_spec_gate
# ---------------------------------------------------------------------------


def test_spec_gate_exits_when_spec_missing(tmp_path: Path) -> None:
    feature_dir = tmp_path / "001-demo"
    feature_dir.mkdir()
    spec_file = feature_dir / "spec.md"  # not created
    with pytest.raises(typer.Exit):
        seam._enforce_spec_gate(
            spec_file,
            feature_dir,
            "001-demo",
            tmp_path,
            target_branch="main",
            current_branch="main",
            json_output=True,
        )


def test_spec_gate_blocks_when_not_substantive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    feature_dir = tmp_path / "001-demo"
    feature_dir.mkdir()
    spec_file = feature_dir / "spec.md"
    spec_file.write_text("# stub")
    monkeypatch.setattr("specify_cli.missions._substantive.is_committed", lambda *a, **k: True)
    monkeypatch.setattr("specify_cli.missions._substantive.is_substantive", lambda *a, **k: False)
    blocked = seam._enforce_spec_gate(
        spec_file,
        feature_dir,
        "001-demo",
        tmp_path,
        target_branch="main",
        current_branch="main",
        json_output=True,
    )
    assert blocked is True


def test_spec_gate_passes_when_committed_and_substantive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    feature_dir = tmp_path / "001-demo"
    feature_dir.mkdir()
    spec_file = feature_dir / "spec.md"
    spec_file.write_text("# real")
    monkeypatch.setattr("specify_cli.missions._substantive.is_committed", lambda *a, **k: True)
    monkeypatch.setattr("specify_cli.missions._substantive.is_substantive", lambda *a, **k: True)
    blocked = seam._enforce_spec_gate(
        spec_file,
        feature_dir,
        "001-demo",
        tmp_path,
        target_branch="main",
        current_branch="main",
        json_output=True,
    )
    assert blocked is False


# ---------------------------------------------------------------------------
# _scaffold_plan_template
# ---------------------------------------------------------------------------


def test_scaffold_plan_template_noop_when_exists(tmp_path: Path) -> None:
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("populated")
    template_src = tmp_path / "mapped-plan.md"
    template_src.write_text("TEMPLATE")
    seam._scaffold_plan_template(plan_file, _resolution(template_src))
    assert plan_file.read_text() == "populated"


def test_scaffold_plan_template_copies_mapped_filename(tmp_path: Path) -> None:
    template_src = tmp_path / "non-conventional-plan-source.md"
    template_src.write_text("TEMPLATE")
    plan_file = tmp_path / "plan.md"
    seam._scaffold_plan_template(plan_file, _resolution(template_src))
    assert plan_file.read_text() == "TEMPLATE"


def test_resolve_plan_template_uses_context_and_configured_seam(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent import mission as mission_mod

    feature_dir = tmp_path / "kitty-specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text('{"mission_type":"software-dev"}', encoding="utf-8")
    context = _resolved_mission_type()
    template_src = tmp_path / "non-conventional-plan-source.md"
    template_src.write_text("MAPPED")
    calls: list[tuple[str, Path, ResolvedMissionType]] = []

    monkeypatch.setattr(
        seam,
        "resolve_mission_type_context",
        lambda repo_root, *, mission_type: context,
    )

    def _resolve(artifact_kind: str, project_dir: Path, resolved: ResolvedMissionType) -> ResolutionResult:
        calls.append((artifact_kind, project_dir, resolved))
        return _resolution(template_src)

    monkeypatch.setattr(mission_mod, "resolve_configured_template", _resolve)

    result = seam._resolve_plan_template(tmp_path, feature_dir)

    assert result.path == template_src
    assert calls == [("plan", tmp_path, context)]


def test_resolve_plan_template_accepts_supported_legacy_mission_field(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Legacy metadata is typed configuration, not the meta-less fallback."""
    from specify_cli.cli.commands.agent import mission as mission_mod

    feature_dir = tmp_path / "kitty-specs" / "001-legacy-meta"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text('{"mission":"software-dev"}', encoding="utf-8")
    context = _resolved_mission_type()
    template_src = tmp_path / "configured-plan-source.md"
    template_src.write_text("CONFIGURED", encoding="utf-8")
    context_calls: list[str] = []

    def _context(_repo_root: Path, *, mission_type: str) -> ResolvedMissionType:
        context_calls.append(mission_type)
        return context

    monkeypatch.setattr(seam, "resolve_mission_type_context", _context)
    monkeypatch.setattr(
        mission_mod,
        "resolve_template",
        lambda *_a, **_k: pytest.fail("legacy metadata reached the meta-less fallback"),
    )
    monkeypatch.setattr(
        mission_mod,
        "resolve_configured_template",
        lambda artifact_kind, project_dir, resolved: (
            _resolution(template_src)
            if (artifact_kind, project_dir, resolved) == ("plan", tmp_path, context)
            else pytest.fail("configured resolver received the wrong authority")
        ),
    )

    result = seam._resolve_plan_template(tmp_path, feature_dir)

    assert result.path == template_src
    assert context_calls == ["software-dev"]


def test_resolve_plan_template_preserves_missing_meta_legacy_boundary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent import mission as mission_mod

    feature_dir = tmp_path / "kitty-specs" / "legacy-mission"
    feature_dir.mkdir(parents=True)
    template_src = tmp_path / "legacy-plan-template.md"
    template_src.write_text("LEGACY")
    legacy_calls: list[tuple[str, Path, str]] = []

    def _legacy_resolve(name: str, project_dir: Path, *, mission: str) -> ResolutionResult:
        legacy_calls.append((name, project_dir, mission))
        return _resolution(template_src)

    monkeypatch.setattr(mission_mod, "resolve_template", _legacy_resolve)
    monkeypatch.setattr(
        mission_mod,
        "resolve_configured_template",
        lambda *_a, **_k: pytest.fail("typeless context reached configured seam"),
    )

    result = seam._resolve_plan_template(tmp_path, feature_dir)

    assert result.path == template_src
    assert not (feature_dir / "meta.json").exists()
    assert not (feature_dir / "meta.json").is_symlink()
    assert legacy_calls == [("plan-template.md", tmp_path, "software-dev")]


@pytest.mark.parametrize(
    ("meta_case", "expected_error"),
    [
        ("malformed", "Malformed JSON"),
        ("unreadable", "Malformed JSON"),
        ("non_object", "Expected JSON object"),
        ("empty_object", "non-blank string field 'mission_type'"),
        ("missing_type", "non-blank string field 'mission_type'"),
        ("null_type", "non-blank string field 'mission_type'"),
        ("numeric_type", "non-blank string field 'mission_type'"),
        ("blank_type", "non-blank string field 'mission_type'"),
        ("whitespace_type", "non-blank string field 'mission_type'"),
        ("broken_symlink", "symlink without readable mission metadata"),
        ("self_loop_symlink", "symlink without readable mission metadata"),
    ],
)
def test_setup_plan_refuses_present_invalid_primary_meta_before_template_or_state_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    meta_case: str,
    expected_error: str,
) -> None:
    """Only absent metadata may enter the temporary #2660 compatibility arm."""
    from specify_cli.cli.commands.agent import mission as mission_mod

    mission_slug = "001-invalid-primary-meta"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("substantive spec", encoding="utf-8")
    meta_path = feature_dir / "meta.json"
    if meta_case == "malformed":
        meta_path.write_text("{", encoding="utf-8")
    elif meta_case == "unreadable":
        meta_path.mkdir()
    elif meta_case == "non_object":
        meta_path.write_text("[]", encoding="utf-8")
    elif meta_case == "broken_symlink":
        meta_path.symlink_to("missing-meta-target.json")
    elif meta_case == "self_loop_symlink":
        meta_path.symlink_to("meta.json")
    else:
        payloads = {
            "empty_object": "{}",
            "missing_type": '{"mission_slug":"001-invalid-primary-meta"}',
            "null_type": '{"mission_type":null}',
            "numeric_type": '{"mission_type":7}',
            "blank_type": '{"mission_type":""}',
            "whitespace_type": '{"mission_type":"  \\t  "}',
        }
        meta_path.write_text(payloads[meta_case], encoding="utf-8")

    template_src = tmp_path / "must-not-be-used.md"
    template_src.write_text("MUST NOT BE USED", encoding="utf-8")
    resolver_calls: list[str] = []
    state_changes: list[str] = []
    emitted: dict[str, object] = {}

    def _unexpected_resolver(name: str, *_args: object, **_kwargs: object) -> ResolutionResult:
        resolver_calls.append(name)
        return _resolution(template_src)

    def _unexpected_plan_commit(*_args: object, **_kwargs: object) -> tuple[None, None, bool]:
        state_changes.append("plan-commit")
        return None, None, True

    monkeypatch.setattr(seam, "_enforce_saas_sync_auth_refusal", lambda **_k: None)
    monkeypatch.setattr(seam, "_enforce_saas_sync_boundary_preflight", lambda _root: None)
    monkeypatch.setattr(seam, "_resolve_setup_plan_feature_dir", lambda *a, **k: feature_dir)
    monkeypatch.setattr(seam, "_enforce_spec_gate", lambda *a, **k: False)
    monkeypatch.setattr(
        seam,
        "_emit_spec_plan_phase_events",
        lambda *a, **k: state_changes.append("phase-events"),
    )
    monkeypatch.setattr(
        seam,
        "_commit_plan_if_substantive",
        _unexpected_plan_commit,
    )
    monkeypatch.setattr(seam, "_run_documentation_wiring", lambda *a, **k: (None, []))
    monkeypatch.setattr(seam, "_trigger_dossier_sync", lambda *a, **k: None)
    monkeypatch.setattr(seam, "_emit_setup_plan_result", lambda **_k: None)
    monkeypatch.setattr(seam, "_emit_json", lambda payload: emitted.update(payload))
    monkeypatch.setattr(mission_mod, "locate_project_root", lambda: tmp_path)
    monkeypatch.setattr(mission_mod, "_enforce_git_preflight", lambda *a, **k: None)
    monkeypatch.setattr(mission_mod, "_show_branch_context", lambda *a, **k: ("main", "main"))
    monkeypatch.setattr(mission_mod, "get_current_branch", lambda _root: "main")
    monkeypatch.setattr(mission_mod, "_planning_read_dir", lambda *a, **k: feature_dir)
    monkeypatch.setattr(mission_mod, "resolve_template", _unexpected_resolver)
    monkeypatch.setattr(mission_mod, "resolve_configured_template", _unexpected_resolver)

    with pytest.raises(typer.Exit) as exc_info:
        seam.setup_plan(feature=mission_slug, json_output=True)

    assert exc_info.value.exit_code == 1
    assert expected_error in str(emitted["error"])
    assert str(meta_path) in str(emitted["error"])
    assert resolver_calls == []
    assert state_changes == []
    assert not (feature_dir / "plan.md").exists()


@pytest.mark.parametrize("mutation", ["unlink", "replace"])
def test_setup_plan_uses_single_loaded_meta_snapshot_when_file_changes_after_read(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutation: str,
) -> None:
    """A post-load filesystem race cannot switch a typed mission to legacy."""
    from specify_cli.cli.commands.agent import mission as mission_mod

    mission_slug = "001-meta-snapshot"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("substantive spec", encoding="utf-8")
    meta_path = feature_dir / "meta.json"
    meta_path.write_text('{"mission_type":"software-dev"}', encoding="utf-8")
    template_src = tmp_path / "configured-plan.md"
    template_src.write_text("CONFIGURED PLAN", encoding="utf-8")
    load_calls = 0
    configured_calls: list[str | None] = []
    legacy_calls: list[str] = []

    def _load_then_mutate(
        feature_dir_arg: Path,
        *,
        allow_missing: bool = True,
        on_malformed: OnMalformed = "raise",
        encoding: str = "utf-8",
    ) -> dict[str, Any] | None:
        nonlocal load_calls
        load_calls += 1
        loaded = canonical_load_meta(
            feature_dir_arg,
            allow_missing=allow_missing,
            on_malformed=on_malformed,
            encoding=encoding,
        )
        if mutation == "unlink":
            meta_path.unlink()
        else:
            meta_path.write_text('{"mission_type":null}', encoding="utf-8")
        return cast(dict[str, Any] | None, loaded)

    def _configured_resolver(
        _artifact_kind: str,
        _project_dir: Path,
        resolved: ResolvedMissionType,
    ) -> ResolutionResult:
        configured_calls.append(resolved.mission_type)
        return _resolution(template_src)

    def _legacy_resolver(name: str, *_args: object, **_kwargs: object) -> ResolutionResult:
        legacy_calls.append(name)
        return _resolution(template_src)

    monkeypatch.setattr(seam, "load_meta", _load_then_mutate)
    monkeypatch.setattr(seam, "_enforce_saas_sync_auth_refusal", lambda **_k: None)
    monkeypatch.setattr(seam, "_enforce_saas_sync_boundary_preflight", lambda _root: None)
    monkeypatch.setattr(seam, "_resolve_setup_plan_feature_dir", lambda *a, **k: feature_dir)
    monkeypatch.setattr(seam, "_enforce_spec_gate", lambda *a, **k: False)
    monkeypatch.setattr(seam, "_emit_spec_plan_phase_events", lambda *a, **k: None)
    monkeypatch.setattr(seam, "_commit_plan_if_substantive", lambda *a, **k: (None, None, True))
    monkeypatch.setattr(seam, "_run_documentation_wiring", lambda *a, **k: (None, []))
    monkeypatch.setattr(seam, "_trigger_dossier_sync", lambda *a, **k: None)
    monkeypatch.setattr(seam, "_emit_setup_plan_result", lambda **_k: None)
    monkeypatch.setattr(mission_mod, "locate_project_root", lambda: tmp_path)
    monkeypatch.setattr(mission_mod, "_enforce_git_preflight", lambda *a, **k: None)
    monkeypatch.setattr(mission_mod, "_show_branch_context", lambda *a, **k: ("main", "main"))
    monkeypatch.setattr(mission_mod, "get_current_branch", lambda _root: "main")
    monkeypatch.setattr(mission_mod, "_planning_read_dir", lambda *a, **k: feature_dir)
    monkeypatch.setattr(mission_mod, "resolve_configured_template", _configured_resolver)
    monkeypatch.setattr(mission_mod, "resolve_template", _legacy_resolver)

    seam.setup_plan(feature=mission_slug, json_output=True)

    assert load_calls == 1
    assert configured_calls == ["software-dev"]
    assert legacy_calls == []
    assert (feature_dir / "plan.md").read_text(encoding="utf-8") == "CONFIGURED PLAN"


def test_setup_plan_resolves_template_context_from_primary_planning_surface(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Coord lifecycle state must not make a typed mission look typeless.

    The coordination directory intentionally has no ``meta.json``.  The primary
    planning directory carries the canonical typed metadata.  Running the real
    ``setup_plan`` body must therefore route through the configured resolver;
    passing the coord directory to ``_resolve_plan_template`` instead makes this
    test enter the guarded legacy resolver and fail.
    """
    from specify_cli.cli.commands.agent import mission as mission_mod

    mission_slug = "001-typed-mission"
    primary_dir = tmp_path / "kitty-specs" / mission_slug
    coord_dir = tmp_path / ".worktrees" / f"{mission_slug}-coord" / "kitty-specs" / mission_slug
    primary_dir.mkdir(parents=True)
    coord_dir.mkdir(parents=True)
    (primary_dir / "meta.json").write_text('{"mission_type":"software-dev"}', encoding="utf-8")
    (primary_dir / "spec.md").write_text("substantive spec", encoding="utf-8")
    template_src = tmp_path / "configured-plan.md"
    template_src.write_text("CONFIGURED PLAN", encoding="utf-8")
    configured_calls: list[tuple[str, Path, ResolvedMissionType]] = []

    def _resolve_configured(
        artifact_kind: str,
        project_dir: Path,
        resolved: ResolvedMissionType,
    ) -> ResolutionResult:
        configured_calls.append((artifact_kind, project_dir, resolved))
        return _resolution(template_src)

    monkeypatch.setattr(seam, "_enforce_saas_sync_auth_refusal", lambda **_k: None)
    monkeypatch.setattr(seam, "_enforce_saas_sync_boundary_preflight", lambda _root: None)
    monkeypatch.setattr(seam, "_resolve_setup_plan_feature_dir", lambda *a, **k: coord_dir)
    monkeypatch.setattr(seam, "_enforce_spec_gate", lambda *a, **k: False)
    monkeypatch.setattr(seam, "_emit_spec_plan_phase_events", lambda *a, **k: None)
    monkeypatch.setattr(seam, "_commit_plan_if_substantive", lambda *a, **k: (None, None, True))
    monkeypatch.setattr(seam, "_run_documentation_wiring", lambda *a, **k: (None, []))
    monkeypatch.setattr(seam, "_trigger_dossier_sync", lambda *a, **k: None)
    monkeypatch.setattr(seam, "_emit_setup_plan_result", lambda **_k: None)
    monkeypatch.setattr(mission_mod, "locate_project_root", lambda: tmp_path)
    monkeypatch.setattr(mission_mod, "_enforce_git_preflight", lambda *a, **k: None)
    monkeypatch.setattr(mission_mod, "_show_branch_context", lambda *a, **k: ("main", "main"))
    monkeypatch.setattr(mission_mod, "get_current_branch", lambda _root: "main")
    monkeypatch.setattr(mission_mod, "_planning_read_dir", lambda *a, **k: primary_dir)
    monkeypatch.setattr(mission_mod, "resolve_configured_template", _resolve_configured)
    monkeypatch.setattr(
        mission_mod,
        "resolve_template",
        lambda *a, **k: pytest.fail("typed primary context reached the typeless compatibility resolver"),
    )

    seam.setup_plan(feature=mission_slug, json_output=True)

    assert (primary_dir / "plan.md").read_text(encoding="utf-8") == "CONFIGURED PLAN"
    assert len(configured_calls) == 1
    artifact_kind, project_dir, resolved = configured_calls[0]
    assert artifact_kind == "plan"
    assert project_dir == tmp_path
    assert resolved.mission_type == "software-dev"
    assert coord_dir != primary_dir
    assert not (coord_dir / "meta.json").exists()


@pytest.mark.parametrize(
    ("context", "expected_fragment"),
    [
        (_resolved_mission_type(template_set={}), "missing the requested mapping key"),
        (
            _resolved_mission_type(mission_type="research", template_set=None),
            "has no configured template mapping",
        ),
        (_resolved_mission_type(template_set={"plan": "absent-plan.md"}), "absent-plan.md"),
    ],
)
def test_resolve_plan_template_fails_closed_for_bad_configuration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    context: ResolvedMissionType,
    expected_fragment: str,
) -> None:
    feature_dir = tmp_path / "kitty-specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(f'{{"mission_type":"{context.mission_type}"}}', encoding="utf-8")
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "empty-home"))
    monkeypatch.setattr(
        seam,
        "resolve_mission_type_context",
        lambda repo_root, *, mission_type: context,
    )

    with pytest.raises(TemplateConfigurationError) as exc_info:
        seam._resolve_plan_template(tmp_path, feature_dir)

    message = str(exc_info.value)
    assert context.mission_type in message
    assert "artifact kind 'plan'" in message
    assert expected_fragment in message


def test_scaffold_and_pristine_compare_share_one_resolution_result(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent import mission as mission_mod

    feature_dir = tmp_path / "kitty-specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text('{"mission_type":"software-dev"}', encoding="utf-8")
    template_src = tmp_path / "override-winner.md"
    template_src.write_text("OVERRIDE WINNER")
    context = _resolved_mission_type()
    call_count = 0

    monkeypatch.setattr(
        seam,
        "resolve_mission_type_context",
        lambda repo_root, *, mission_type: context,
    )

    def _resolve(*_args: object, **_kwargs: object) -> ResolutionResult:
        nonlocal call_count
        call_count += 1
        return _resolution(template_src)

    monkeypatch.setattr(mission_mod, "resolve_configured_template", _resolve)

    resolution = seam._resolve_plan_template(tmp_path, feature_dir)
    plan_file = feature_dir / "plan.md"
    seam._scaffold_plan_template(plan_file, resolution)

    assert seam._is_plan_pristine(plan_file, resolution) is True
    assert call_count == 1


# ---------------------------------------------------------------------------
# is_pristine_scaffold / _resolve_plan_result_state (T021/T022 direct units,
# #2566 / FR-009)
# ---------------------------------------------------------------------------


def test_is_pristine_scaffold_true_when_byte_equal() -> None:
    from specify_cli.missions._substantive import is_pristine_scaffold

    template = "## Technical Context\n**Language/Version**: [NEEDS CLARIFICATION]\n"
    assert is_pristine_scaffold(template, template) is True


def test_is_pristine_scaffold_false_when_populated_but_insufficient() -> None:
    from specify_cli.missions._substantive import is_pristine_scaffold

    template = "## Technical Context\n**Language/Version**: [NEEDS CLARIFICATION]\n"
    edited = template + "\nAgent started filling this in but not the required fields yet.\n"
    assert is_pristine_scaffold(edited, template) is False


@pytest.mark.parametrize(
    ("is_substantive_flag", "is_pristine", "committed", "expected"),
    [
        # substantive always wins -> success, no flag (regardless of pristine/committed)
        (True, False, False, ("success", False)),
        (True, True, True, ("success", False)),
        # pristine, never committed -> the first happy-path scaffold write
        (False, True, False, ("success", True)),
        # pristine but already committed (edge case) -> falls back to blocked,
        # not a repeated scaffold_only claim
        (False, True, True, ("blocked", False)),
        # populated-but-insufficient (K-1 / NFR-005): edited but not substantive
        (False, False, False, ("blocked", False)),
        (False, False, True, ("blocked", False)),
    ],
)
def test_resolve_plan_result_state(is_substantive_flag: bool, is_pristine: bool, committed: bool, expected: tuple[str, bool]) -> None:
    assert seam._resolve_plan_result_state(is_substantive=is_substantive_flag, is_pristine=is_pristine, committed=committed) == expected


# ---------------------------------------------------------------------------
# _commit_plan_if_substantive (T022: pristine -> scaffold_only, populated
# -but-insufficient -> blocked, substantive -> committed with no flag)
# ---------------------------------------------------------------------------


def test_commit_plan_scaffold_only_when_pristine(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    template_src = tmp_path / "tmpl.md"
    template_src.write_text("## Technical Context\n**Language/Version**: [NEEDS CLARIFICATION]\n")
    resolution = _resolution(template_src)

    plan_file = tmp_path / "plan.md"
    plan_file.write_text(template_src.read_text())  # byte-identical, never touched

    monkeypatch.setattr("specify_cli.missions._substantive.is_substantive", lambda *a, **k: False)
    monkeypatch.setattr("specify_cli.missions._substantive.is_committed", lambda *a, **k: False)

    commit_result, blocked_reason, scaffold_only = seam._commit_plan_if_substantive(
        plan_file,
        tmp_path,
        "001-demo",
        tmp_path,
        target_branch="main",
        json_output=True,
        plan_template=resolution,
    )
    assert commit_result is None
    assert blocked_reason is None
    assert scaffold_only is True


def test_commit_plan_blocked_when_populated_but_insufficient(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    template_src = tmp_path / "tmpl.md"
    template_src.write_text("## Technical Context\n**Language/Version**: [NEEDS CLARIFICATION]\n")
    resolution = _resolution(template_src)

    plan_file = tmp_path / "plan.md"
    plan_file.write_text(template_src.read_text() + "\nStarted editing but Technical Context still isn't real.\n")

    monkeypatch.setattr("specify_cli.missions._substantive.is_substantive", lambda *a, **k: False)
    monkeypatch.setattr("specify_cli.missions._substantive.is_committed", lambda *a, **k: False)

    commit_result, blocked_reason, scaffold_only = seam._commit_plan_if_substantive(
        plan_file,
        tmp_path,
        "001-demo",
        tmp_path,
        target_branch="main",
        json_output=True,
        plan_template=resolution,
    )
    assert commit_result is None
    assert blocked_reason is not None
    assert scaffold_only is False


def test_commit_plan_substantive_commits_with_no_scaffold_flag(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent import mission as mission_mod

    plan_file = tmp_path / "plan.md"
    plan_file.write_text("## Technical Context\n**Language/Version**: Python 3.12\n**Primary Dependencies**: typer\n")

    monkeypatch.setattr("specify_cli.missions._substantive.is_substantive", lambda *a, **k: True)
    monkeypatch.setattr(
        mission_mod,
        "_commit_to_branch",
        lambda *a, **k: seam.CommitToBranchResult(status="committed", placement_ref="main", commit_hash="abc1234"),
    )

    commit_result, blocked_reason, scaffold_only = seam._commit_plan_if_substantive(
        plan_file,
        tmp_path,
        "001-demo",
        tmp_path,
        target_branch="main",
        json_output=True,
        plan_template=_resolution(tmp_path / "unused.md"),
    )
    assert commit_result is not None
    assert commit_result.status == "committed"
    assert blocked_reason is None
    assert scaffold_only is False


# ---------------------------------------------------------------------------
# _run_documentation_wiring (non-doc mission no-op)
# ---------------------------------------------------------------------------


def test_documentation_wiring_noop_for_non_doc_mission(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(seam, "get_mission_type", lambda _fd: "software-dev")
    gap, gens = seam._run_documentation_wiring(tmp_path, "001-demo", tmp_path, target_branch="main", json_output=True)
    assert gap is None
    assert gens == []


def test_documentation_wiring_runs_both_documentation_phases(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(seam, "get_mission_type", lambda _fd: "documentation")
    monkeypatch.setattr(
        seam,
        "_run_documentation_gap_analysis",
        lambda *a, **k: "gap-analysis.md",
    )
    generator = object()
    monkeypatch.setattr(
        seam,
        "_detect_and_configure_generators",
        lambda *a, **k: [generator],
    )

    gap, generators = seam._run_documentation_wiring(
        tmp_path,
        "001-docs",
        tmp_path,
        target_branch="main",
        json_output=True,
    )

    assert gap == "gap-analysis.md"
    assert generators == [generator]


@pytest.mark.parametrize("json_output", [True, False])
def test_setup_plan_renders_configured_template_failure_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    json_output: bool,
) -> None:
    from specify_cli.cli.commands.agent import mission as mission_mod

    feature_dir = tmp_path / "kitty-specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("spec")
    emitted: dict[str, object] = {}
    error = TemplateConfigurationError(
        mission_type="software-dev",
        artifact_kind="plan",
        mapped_filename="missing-plan.md",
        reason="maps to unresolved filename 'missing-plan.md'",
    )

    monkeypatch.setattr(seam, "_enforce_saas_sync_auth_refusal", lambda **_k: None)
    monkeypatch.setattr(seam, "_enforce_saas_sync_boundary_preflight", lambda _root: None)
    monkeypatch.setattr(seam, "_resolve_setup_plan_feature_dir", lambda *a, **k: feature_dir)
    monkeypatch.setattr(seam, "_enforce_spec_gate", lambda *a, **k: False)
    monkeypatch.setattr(seam, "_resolve_plan_template", lambda *_a: (_ for _ in ()).throw(error))
    monkeypatch.setattr(seam, "_emit_json", lambda payload: emitted.update(payload))
    monkeypatch.setattr(mission_mod, "locate_project_root", lambda: tmp_path)
    monkeypatch.setattr(mission_mod, "_enforce_git_preflight", lambda *a, **k: None)
    monkeypatch.setattr(mission_mod, "_show_branch_context", lambda *a, **k: ("main", "main"))
    monkeypatch.setattr(mission_mod, "get_current_branch", lambda _root: "main")
    monkeypatch.setattr(mission_mod, "_planning_read_dir", lambda *a, **k: feature_dir)

    with pytest.raises(typer.Exit) as exc_info:
        seam.setup_plan(feature="001-demo", json_output=json_output)

    assert exc_info.value.exit_code == 1
    if json_output:
        assert emitted["error_code"] == "TEMPLATE_CONFIGURATION_ERROR"
        assert emitted["mapped_filename"] == "missing-plan.md"
    else:
        output = capsys.readouterr().out
        assert "missing-plan.md" in output
        assert "Traceback" not in output


# ---------------------------------------------------------------------------
# _emit_setup_plan_result
# ---------------------------------------------------------------------------


def test_emit_result_human(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    seam._emit_setup_plan_result(
        plan_file=tmp_path / "plan.md",
        spec_file=tmp_path / "spec.md",
        feature_dir=tmp_path,
        mission_slug="001-demo",
        plan_is_substantive=True,
        plan_blocked_reason=None,
        plan_commit_result=None,
        gap_analysis_path=None,
        generators_detected=[],
        target_branch="main",
        current_branch="main",
        json_output=False,
    )
    assert "Plan scaffolded" in capsys.readouterr().out


def test_emit_result_json_blocked(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    emitted: dict[str, object] = {}
    monkeypatch.setattr(seam, "_emit_json", lambda p: emitted.update(p))
    seam._emit_setup_plan_result(
        plan_file=tmp_path / "plan.md",
        spec_file=tmp_path / "spec.md",
        feature_dir=tmp_path,
        mission_slug="001-demo",
        plan_is_substantive=False,
        plan_blocked_reason="not substantive",
        plan_commit_result=None,
        gap_analysis_path=None,
        generators_detected=[],
        target_branch="main",
        current_branch="main",
        json_output=True,
    )
    assert emitted["result"] == "blocked"
    assert emitted["blocked_reason"] == "not substantive"
    assert "branch_context" in emitted


def test_emit_result_json_committed_surfaces_hash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    emitted: dict[str, object] = {}
    monkeypatch.setattr(seam, "_emit_json", lambda p: emitted.update(p))
    commit = seam.CommitToBranchResult(status="committed", placement_ref="main", commit_hash="abc1234")
    seam._emit_setup_plan_result(
        plan_file=tmp_path / "plan.md",
        spec_file=tmp_path / "spec.md",
        feature_dir=tmp_path,
        mission_slug="001-demo",
        plan_is_substantive=True,
        plan_blocked_reason=None,
        plan_commit_result=commit,
        gap_analysis_path=None,
        generators_detected=[],
        target_branch="main",
        current_branch="main",
        json_output=True,
    )
    assert emitted["commit_created"] is True
    assert emitted["commit_hash"] == "abc1234"
    assert emitted["commit_status"] == "committed"


def test_emit_result_json_scaffold_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """FR-009 / #2566: the first happy-path scaffold write is success, not blocked."""
    emitted: dict[str, object] = {}
    monkeypatch.setattr(seam, "_emit_json", lambda p: emitted.update(p))
    seam._emit_setup_plan_result(
        plan_file=tmp_path / "plan.md",
        spec_file=tmp_path / "spec.md",
        feature_dir=tmp_path,
        mission_slug="001-demo",
        plan_is_substantive=False,
        plan_blocked_reason=None,
        plan_commit_result=None,
        gap_analysis_path=None,
        generators_detected=[],
        target_branch="main",
        current_branch="main",
        json_output=True,
        plan_scaffold_only=True,
    )
    assert emitted["result"] == "success"
    assert emitted["scaffold_only"] is True
    assert emitted["phase_complete"] is False
    assert "blocked_reason" not in emitted
