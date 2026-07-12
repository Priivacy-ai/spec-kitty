"""Composition-dispatch seam tests for ``runtime_bridge_composition`` (#2531 WP08, FR-008).

Four concerns, mirroring the WP03/WP04/WP05 test-file pattern:

1. **Compat surface** (``test_seam_defines_every_relocated_symbol``,
   ``test_runtime_bridge_keeps_native_thin_delegates_for_compat_guarded_names``,
   ``test_runtime_bridge_keeps_plain_reexports_for_untracked_helpers``) — the
   non-vacuousness + native-thin-delegate / plain-reexport split contract from
   contracts/compat-surface.md.

2. **FR-008 both-branch fixture** (``test_should_dispatch_via_composition_*``)
   — the selection seam exercised for BOTH outcomes (dispatch / no-dispatch),
   plus the C-005 audit that it imports no gates (#2535) code.

3. **Focused unit tests (FR-006)** against the moved cluster in isolation,
   stubbing collaborators at their source (charter / doctrine / mission_step_
   contracts / executor), mirroring the pattern
   ``tests/runtime/test_bridge_retrospective.py`` already uses.

4. **Intra-seam live-lookup regression** (the WP03-WP07 risk flagged in
   ``research.md`` §Compat and ``contracts/compat-surface.md``): now that the
   whole cluster lives together in one seam module, an intra-cluster call
   between two compat-guarded symbols (or a call back into a symbol that
   stays in the residual, e.g. ``_should_advance_wp_step``) MUST resolve via
   a live lookup back through ``runtime_bridge`` (never a bare intra-module
   call), or a ``monkeypatch.setattr(runtime_bridge, "<name>", …)`` becomes a
   no-op (false-green). ``test_*_uses_live_lookup_for_*`` pin this by
   patching the callee on ``runtime_bridge`` and asserting the (unpatched)
   caller in the seam still observes it.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from runtime.next import runtime_bridge_composition as composition
from runtime.next import runtime_bridge_cores as cores_seam
from runtime.next import runtime_bridge_engine as engine_seam
from runtime.next import runtime_bridge_io as io_seam

# ---------------------------------------------------------------------------
# 1. Compat surface (non-vacuousness-checked)
# ---------------------------------------------------------------------------

_RUNTIME_BRIDGE_PATH = Path(__file__).resolve().parents[2] / "src" / "runtime" / "next" / "runtime_bridge.py"

# The 8 compat-guarded symbols (contracts/compat-surface.md) that MUST stay
# natively defined in runtime_bridge.py as thin delegates (never a plain
# re-export) -- see runtime_bridge_composition's module docstring for why.
_COMPAT_GUARDED_NAMES = frozenset(
    {
        "_should_dispatch_via_composition",
        "_normalize_action_for_composition",
        "_dispatch_via_composition",
        "_check_composed_action_guard",
        "_resolve_step_agent_profile",
        "_resolve_runtime_contract_for_step",
        "_count_source_documented_events",
        "_publication_approved",
    }
)

# The two symbols in the cluster that are NOT part of the WP02 compat guard's
# tracked inventory (nothing patches them) -- re-exported as plain
# module-level imports instead of thin delegates.
_PLAIN_REEXPORT_NAMES = frozenset({"_composition_dispatch_inputs", "_has_generated_docs"})

# Symbols that moved into this seam but have NO external caller left at all
# (purely internal helpers) -- no residual re-export of any kind.
_INTERNAL_ONLY_NAMES = frozenset({"_resolve_step_binding", "_LEGACY_TASKS_STEP_IDS"})


def test_seam_defines_every_relocated_symbol() -> None:
    """Non-vacuousness check: the seam must actually define all relocated
    names, or the delegate/re-export assertions below would pass for the
    wrong reason (nobody needing the cluster at all)."""
    for name in sorted(_COMPAT_GUARDED_NAMES | _PLAIN_REEXPORT_NAMES | _INTERNAL_ONLY_NAMES):
        assert hasattr(composition, name), f"seam is missing relocated symbol {name!r}"


def test_runtime_bridge_keeps_native_thin_delegates_for_compat_guarded_names() -> None:
    """Every compat-guarded symbol must stay a NATIVE ``def`` statement in
    runtime_bridge.py (a thin delegate), never a plain ``import`` alias --
    otherwise the WP02 compat guard's hardcoded identity/relocated-symbol
    baseline (``test_guard_b_identity_reexport_for_relocated_symbols``) trips."""
    from runtime.next import runtime_bridge as rb

    for name in sorted(_COMPAT_GUARDED_NAMES):
        obj = getattr(rb, name)
        assert obj.__module__ == rb.__name__, (
            f"{name!r} on runtime_bridge is NOT natively defined there "
            f"(__module__={obj.__module__!r}) -- it must be a native thin "
            "delegate, not a plain re-export, or guard B's hardcoded "
            "relocated-symbol baseline will fail."
        )


def test_runtime_bridge_keeps_plain_reexports_for_untracked_helpers() -> None:
    """The two untracked helpers are plain re-exports (identical object,
    origin module is the seam) -- a native delegate would be unnecessary
    ceremony since nothing patches them."""
    from runtime.next import runtime_bridge as rb

    for name in sorted(_PLAIN_REEXPORT_NAMES):
        rb_obj = getattr(rb, name)
        seam_obj = getattr(composition, name)
        assert rb_obj is seam_obj, f"{name!r} re-export is a copy, not an identity re-export"
        assert rb_obj.__module__ == composition.__name__, (
            f"{name!r} unexpectedly natively defined on runtime_bridge -- "
            "expected a plain re-export from the seam"
        )


@pytest.mark.architectural
def test_should_dispatch_via_composition_imports_no_gates_code() -> None:
    """FR-008 / C-005 (load-bearing): the selection seam must import NO gates
    (#2535) code and pull in no ``resolve_gates`` dependency -- the inversion
    that consumes this seam is gates mission WP14, landing after this
    mission. AST-scan the whole seam module (not just the one function) so a
    future edit anywhere in the file cannot quietly introduce the coupling."""
    source = _module_source()
    tree = ast.parse(source, filename=str(_composition_path()))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and "gates" in node.module.lower():
            offenders.append(f"line {node.lineno}: from {node.module} import ...")
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "gates" in alias.name.lower():
                    offenders.append(f"line {node.lineno}: import {alias.name}")
        # AST nodes only (never docstrings/comments, which are plain string
        # Constants, not Name/Attribute references) -- catches an aliased
        # `resolve_gates` call slipping in without a module name containing
        # "gates".
        if isinstance(node, ast.Name) and node.id == "resolve_gates":
            offenders.append(f"line {node.lineno}: reference to name resolve_gates")
        if isinstance(node, ast.Attribute) and node.attr == "resolve_gates":
            offenders.append(f"line {node.lineno}: reference to attribute resolve_gates")
    assert not offenders, (
        "runtime_bridge_composition.py imports gates (#2535) code -- FR-008/C-005 "
        "requires this seam stay clean for gates WP14 to route through later:\n"
        + "\n".join(offenders)
    )


def _composition_path() -> Path:
    return Path(composition.__file__)


def _module_source() -> str:
    return _composition_path().read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Frozen-template helper (self-contained -- this file owns it, mirrors
# tests/next/test_composition_gate_widening.py's established convention).
# ---------------------------------------------------------------------------


def _write_frozen_template(
    run_dir: Path,
    *,
    mission_key: str,
    steps: list[dict[str, object]],
) -> Path:
    """Write a minimal frozen template at the layout ``_load_frozen_template`` expects."""
    run_dir.mkdir(parents=True, exist_ok=True)
    template = {
        "mission": {
            "key": mission_key,
            "name": mission_key,
            "version": "1.0.0",
            "description": f"Test mission for {mission_key}",
        },
        "steps": steps,
    }
    frozen_path = run_dir / "mission_template_frozen.yaml"
    frozen_path.write_text(yaml.safe_dump(template), encoding="utf-8")
    return frozen_path


_REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# 2. FR-008 both-branch fixture for _should_dispatch_via_composition
# ---------------------------------------------------------------------------


def test_should_dispatch_via_composition_both_branches(tmp_path: Path) -> None:
    """The FR-008 selection seam's BOTH outcomes, driven without ``repo_root``
    (skips the charter lookup entirely, mirrors
    tests/next/test_composition_gate_widening.py) so only the custom-widening
    branch is exercised here."""
    dispatch_run_dir = tmp_path / "dispatch-run"
    _write_frozen_template(
        dispatch_run_dir,
        mission_key="custom-mission",
        steps=[{"id": "step1", "title": "Step One", "agent_profile": "implementer-ivan"}],
    )
    assert (
        composition._should_dispatch_via_composition("custom-mission", "step1", run_dir=dispatch_run_dir)
        is True
    )

    no_dispatch_run_dir = tmp_path / "no-dispatch-run"
    _write_frozen_template(
        no_dispatch_run_dir,
        mission_key="custom-mission",
        steps=[{"id": "step1", "title": "Step One"}],  # no agent_profile / contract_ref
    )
    assert (
        composition._should_dispatch_via_composition("custom-mission", "step1", run_dir=no_dispatch_run_dir)
        is False
    )


def test_should_dispatch_via_composition_both_branches_via_charter_lookup(tmp_path: Path) -> None:
    """Same both-branch requirement, but driven through the REAL charter
    lookup path (repo_root supplied) against this repo's actual doctrine
    data -- the built-in software-dev action sequence always dispatches;
    an unrelated custom mission with no run_dir cannot widen."""
    assert (
        composition._should_dispatch_via_composition("software-dev", "specify", repo_root=_REPO_ROOT)
        is True
    )
    assert (
        composition._should_dispatch_via_composition("totally-unknown-mission", "step1", repo_root=_REPO_ROOT)
        is False
    )


def test_should_dispatch_via_composition_uses_live_lookup_for_normalize(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Live-lookup regression: the charter branch must resolve
    ``_normalize_action_for_composition`` via ``runtime_bridge`` -- a bare
    intra-module call would silently bypass a patch on
    ``runtime_bridge._normalize_action_for_composition``."""
    from runtime.next import runtime_bridge as rb

    monkeypatch.setattr(
        "charter.mission_type_profiles.resolve_action_sequence",
        lambda mission, repo_root: ["patched-action"],
    )
    calls: list[str] = []

    def _fake_normalize(step_id: str) -> str:
        calls.append(step_id)
        return "patched-action"

    monkeypatch.setattr(rb, "_normalize_action_for_composition", _fake_normalize)

    result = composition._should_dispatch_via_composition(
        "software-dev", "unrelated-step", repo_root=tmp_path
    )

    assert calls == ["unrelated-step"]
    assert result is True  # only true because the patched normalize fired


# ---------------------------------------------------------------------------
# 3a. _normalize_action_for_composition
# ---------------------------------------------------------------------------


def test_normalize_action_for_composition_collapses_legacy_tasks_substeps() -> None:
    for legacy in ("tasks_outline", "tasks_packages", "tasks_finalize"):
        assert composition._normalize_action_for_composition(legacy) == "tasks"


def test_normalize_action_for_composition_passes_through_other_ids() -> None:
    for step_id in ("specify", "plan", "tasks", "implement", "review", "accept"):
        assert composition._normalize_action_for_composition(step_id) == step_id


# ---------------------------------------------------------------------------
# 3b. _resolve_step_binding / _resolve_step_agent_profile
# ---------------------------------------------------------------------------


def test_resolve_step_binding_missing_template_returns_none_pair(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"  # never created -- no frozen template
    assert composition._resolve_step_binding(run_dir, "step1") == (None, None)


def test_resolve_step_binding_missing_step_returns_none_pair(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_frozen_template(run_dir, mission_key="custom-mission", steps=[{"id": "other", "title": "Other"}])
    assert composition._resolve_step_binding(run_dir, "step1") == (None, None)


def test_resolve_step_binding_treats_blank_strings_as_none(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_frozen_template(
        run_dir,
        mission_key="custom-mission",
        steps=[{"id": "step1", "title": "Step One", "agent_profile": "  ", "contract_ref": "  "}],
    )
    assert composition._resolve_step_binding(run_dir, "step1") == (None, None)


def test_resolve_step_binding_returns_profile_and_contract_ref(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_frozen_template(
        run_dir,
        mission_key="custom-mission",
        steps=[{"id": "step1", "title": "Step One", "agent_profile": "implementer-ivan", "contract_ref": "ref-1"}],
    )
    assert composition._resolve_step_binding(run_dir, "step1") == ("implementer-ivan", "ref-1")


def test_resolve_step_agent_profile_returns_only_the_profile(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_frozen_template(
        run_dir,
        mission_key="custom-mission",
        steps=[{"id": "step1", "title": "Step One", "agent_profile": "implementer-ivan", "contract_ref": "ref-1"}],
    )
    assert composition._resolve_step_agent_profile(run_dir, "step1") == "implementer-ivan"


def test_resolve_step_binding_uses_live_lookup_for_normalize(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Live-lookup regression: patching ``runtime_bridge._normalize_action_for_composition``
    must still be observed from inside ``_resolve_step_binding`` even though
    both symbols now live in the same seam module."""
    from runtime.next import runtime_bridge as rb

    run_dir = tmp_path / "run"
    _write_frozen_template(
        run_dir,
        mission_key="custom-mission",
        steps=[{"id": "step1", "title": "Step One", "agent_profile": "implementer-ivan"}],
    )
    calls: list[str] = []

    def _fake_normalize(step_id: str) -> str:
        calls.append(step_id)
        return "step1"  # pretend "weird-id" normalizes to "step1"

    monkeypatch.setattr(rb, "_normalize_action_for_composition", _fake_normalize)

    profile, _contract_ref = composition._resolve_step_binding(run_dir, "weird-id")

    assert calls == ["weird-id"]
    # Only non-None because the patched normalize mapped "weird-id" -> "step1".
    assert profile == "implementer-ivan"


# ---------------------------------------------------------------------------
# 3c. _resolve_runtime_contract_for_step
# ---------------------------------------------------------------------------


def test_resolve_runtime_contract_for_step_returns_none_when_no_frozen_template(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"  # never created
    assert (
        composition._resolve_runtime_contract_for_step(
            repo_root=tmp_path, run_dir=run_dir, mission="custom-mission", step_id="step1"
        )
        is None
    )


def test_resolve_runtime_contract_for_step_returns_none_when_step_has_no_binding(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_frozen_template(run_dir, mission_key="custom-mission", steps=[{"id": "step1", "title": "Step One"}])
    assert (
        composition._resolve_runtime_contract_for_step(
            repo_root=tmp_path, run_dir=run_dir, mission="custom-mission", step_id="step1"
        )
        is None
    )


def test_resolve_runtime_contract_for_step_looks_up_by_contract_ref(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run_dir = tmp_path / "run"
    _write_frozen_template(
        run_dir,
        mission_key="custom-mission",
        steps=[{"id": "step1", "title": "Step One", "contract_ref": "ref-123"}],
    )
    sentinel_contract = object()
    seen_refs: list[str] = []

    monkeypatch.setattr(
        "doctrine.missions.step_contracts.MissionStepContractRepository",
        lambda *, project_dir: object(),
    )

    def _fake_lookup(contract_ref: str, repository: Any) -> Any:
        seen_refs.append(contract_ref)
        return sentinel_contract

    monkeypatch.setattr("specify_cli.mission_loader.registry.lookup_contract", _fake_lookup)

    result = composition._resolve_runtime_contract_for_step(
        repo_root=tmp_path, run_dir=run_dir, mission="custom-mission", step_id="step1"
    )
    assert result is sentinel_contract
    assert seen_refs == ["ref-123"]


def test_resolve_runtime_contract_for_step_synthesizes_for_agent_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run_dir = tmp_path / "run"
    _write_frozen_template(
        run_dir,
        mission_key="custom-mission",
        steps=[{"id": "step1", "title": "Step One", "agent_profile": "implementer-ivan"}],
    )

    class _FakeContract:
        def __init__(self, contract_id: str) -> None:
            self.id = contract_id

    matching = _FakeContract("custom:custom-mission:step1")
    other = _FakeContract("custom:custom-mission:other-step")

    monkeypatch.setattr(
        "specify_cli.mission_loader.contract_synthesis.synthesize_contracts",
        lambda template: [other, matching],
    )

    result = composition._resolve_runtime_contract_for_step(
        repo_root=tmp_path, run_dir=run_dir, mission="custom-mission", step_id="step1"
    )
    assert result is matching


def test_resolve_runtime_contract_for_step_uses_live_lookup_for_normalize(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Live-lookup regression: patching
    ``runtime_bridge._normalize_action_for_composition`` must still be
    observed from inside ``_resolve_runtime_contract_for_step``."""
    from runtime.next import runtime_bridge as rb

    run_dir = tmp_path / "run"
    _write_frozen_template(
        run_dir,
        mission_key="custom-mission",
        steps=[{"id": "step1", "title": "Step One", "contract_ref": "ref-xyz"}],
    )
    calls: list[str] = []

    def _fake_normalize(step_id: str) -> str:
        calls.append(step_id)
        return "step1"

    monkeypatch.setattr(rb, "_normalize_action_for_composition", _fake_normalize)
    monkeypatch.setattr(
        "doctrine.missions.step_contracts.MissionStepContractRepository",
        lambda *, project_dir: object(),
    )
    sentinel = object()
    monkeypatch.setattr(
        "specify_cli.mission_loader.registry.lookup_contract",
        lambda ref, repo: sentinel,
    )

    result = composition._resolve_runtime_contract_for_step(
        repo_root=tmp_path, run_dir=run_dir, mission="custom-mission", step_id="weird-id"
    )

    assert calls == ["weird-id"]
    assert result is sentinel


# ---------------------------------------------------------------------------
# 3d. _composition_dispatch_inputs
# ---------------------------------------------------------------------------


def test_composition_dispatch_inputs_short_circuits_when_action_in_charter_sequence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "charter.mission_type_profiles.resolve_action_sequence",
        lambda mission, repo_root: ["specify", "plan", "tasks", "implement", "review"],
    )
    profile, contract = composition._composition_dispatch_inputs(
        repo_root=tmp_path, run_dir=tmp_path, mission="software-dev", step_id="specify", action="specify"
    )
    assert (profile, contract) == (None, None)


def test_composition_dispatch_inputs_uses_live_lookup_for_resolution_helpers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Live-lookup regression: when the action is NOT in the charter sequence,
    ``_composition_dispatch_inputs`` must resolve ``_resolve_step_agent_profile``
    / ``_resolve_runtime_contract_for_step`` via a live lookup through
    ``runtime_bridge`` -- a bare intra-module call would silently bypass a
    monkeypatch on ``runtime_bridge.<name>``."""
    from runtime.next import runtime_bridge as rb

    def _raise_unknown(mission: str, repo_root: Path) -> list[str]:
        from charter.mission_type_profiles import UnknownMissionTypeError

        raise UnknownMissionTypeError(mission)

    monkeypatch.setattr("charter.mission_type_profiles.resolve_action_sequence", _raise_unknown)

    calls: list[str] = []

    def _fake_resolve_profile(run_dir: Path, step_id: str) -> str:
        calls.append("profile")
        return "patched-profile"

    def _fake_resolve_contract(**kwargs: Any) -> str:
        calls.append("contract")
        return "patched-contract"

    monkeypatch.setattr(rb, "_resolve_step_agent_profile", _fake_resolve_profile)
    monkeypatch.setattr(rb, "_resolve_runtime_contract_for_step", _fake_resolve_contract)

    profile, contract = composition._composition_dispatch_inputs(
        repo_root=tmp_path, run_dir=tmp_path, mission="custom-mission", step_id="step1", action="step1"
    )
    assert profile == "patched-profile"
    assert contract == "patched-contract"
    assert calls == ["profile", "contract"]


# ---------------------------------------------------------------------------
# 3e. _count_source_documented_events / _publication_approved / _has_generated_docs
# ---------------------------------------------------------------------------


def test_count_source_documented_events_counts_matching_entries(tmp_path: Path) -> None:
    events = [{"type": "source_documented", "name": f"src-{i}"} for i in range(3)]
    events.append({"type": "other_event"})
    (tmp_path / "mission-events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8"
    )
    assert composition._count_source_documented_events(tmp_path) == 3


def test_count_source_documented_events_missing_log_returns_zero(tmp_path: Path) -> None:
    assert composition._count_source_documented_events(tmp_path) == 0


def test_publication_approved_true_when_gate_event_present(tmp_path: Path) -> None:
    events = [{"type": "gate_passed", "name": "publication_approved"}]
    (tmp_path / "mission-events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8"
    )
    assert composition._publication_approved(tmp_path) is True


def test_publication_approved_false_when_missing(tmp_path: Path) -> None:
    assert composition._publication_approved(tmp_path) is False


def test_has_generated_docs_true_when_markdown_present(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "index.md").write_text("# Docs\n", encoding="utf-8")
    assert composition._has_generated_docs(tmp_path) is True


def test_has_generated_docs_false_when_docs_dir_absent(tmp_path: Path) -> None:
    assert composition._has_generated_docs(tmp_path) is False


# ---------------------------------------------------------------------------
# 3f. _check_composed_action_guard
# ---------------------------------------------------------------------------


def test_check_composed_action_guard_delegates_to_cores_and_io(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from runtime.next.runtime_bridge_io import ArtifactPresenceSnapshot

    def _fake_gather(feature_dir: Path, *, mission_family: str, step_id: str, legacy_step_id: str | None = None) -> Any:
        return ArtifactPresenceSnapshot(
            present_artifacts=frozenset(),
            status_facts={},
            mission_family=mission_family,
            step_id=step_id,
            legacy_step_id=legacy_step_id,
        )

    monkeypatch.setattr(io_seam, "gather_artifact_presence", _fake_gather)
    monkeypatch.setattr(cores_seam, "evaluate_guards", lambda snapshot: ["boom"])

    failures = composition._check_composed_action_guard("specify", tmp_path, mission="software-dev")
    assert failures == ["boom"]


def test_check_composed_action_guard_uses_live_lookup_for_should_advance_wp_step(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Live-lookup regression: ``_should_advance_wp_step`` stays defined in
    the residual (untouched by this WP) -- ``_check_composed_action_guard``
    must reach it via a live lookup through ``runtime_bridge``."""
    from runtime.next import runtime_bridge as rb
    from runtime.next.runtime_bridge_io import ArtifactPresenceSnapshot

    captured: dict[str, Any] = {}

    def _fake_gather(feature_dir: Path, *, mission_family: str, step_id: str, legacy_step_id: str | None = None) -> Any:
        return ArtifactPresenceSnapshot(
            present_artifacts=frozenset(),
            status_facts={},
            mission_family=mission_family,
            step_id=step_id,
            legacy_step_id=legacy_step_id,
        )

    def _fake_evaluate(snapshot: Any) -> list[str]:
        captured["wp_advance_ready"] = snapshot.wp_advance_ready
        return []

    monkeypatch.setattr(io_seam, "gather_artifact_presence", _fake_gather)
    monkeypatch.setattr(cores_seam, "evaluate_guards", _fake_evaluate)
    monkeypatch.setattr(rb, "_should_advance_wp_step", lambda step_id, feature_dir: True)

    failures = composition._check_composed_action_guard("implement", tmp_path, mission="software-dev")

    assert failures == []
    assert captured["wp_advance_ready"] is True


def test_check_composed_action_guard_does_not_thread_wp_advance_ready_for_non_wp_actions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from runtime.next.runtime_bridge_io import ArtifactPresenceSnapshot

    captured: dict[str, Any] = {}

    def _fake_gather(feature_dir: Path, *, mission_family: str, step_id: str, legacy_step_id: str | None = None) -> Any:
        return ArtifactPresenceSnapshot(
            present_artifacts=frozenset(),
            status_facts={},
            mission_family=mission_family,
            step_id=step_id,
            legacy_step_id=legacy_step_id,
        )

    def _fake_evaluate(snapshot: Any) -> list[str]:
        captured["wp_advance_ready"] = snapshot.wp_advance_ready
        return []

    monkeypatch.setattr(io_seam, "gather_artifact_presence", _fake_gather)
    monkeypatch.setattr(cores_seam, "evaluate_guards", _fake_evaluate)

    composition._check_composed_action_guard("specify", tmp_path, mission="software-dev")

    assert captured["wp_advance_ready"] is None


# ---------------------------------------------------------------------------
# 3g/4. _dispatch_via_composition -- behavior + live lookup
# ---------------------------------------------------------------------------


def test_dispatch_via_composition_success_returns_none_when_guard_passes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from unittest.mock import MagicMock

    from runtime.next import runtime_bridge as rb

    monkeypatch.setattr(rb, "_check_composed_action_guard", lambda *a, **k: [])
    monkeypatch.setattr(
        "specify_cli.mission_step_contracts.executor.StepContractExecutor.execute",
        lambda self, context, contract=None: MagicMock(invocation_ids=("inv-1",)),
    )

    failures = composition._dispatch_via_composition(
        repo_root=tmp_path,
        mission="software-dev",
        action="specify",
        actor="implementer-pedro",
        profile_hint=None,
        request_text=None,
        mode_of_work=None,
        feature_dir=tmp_path,
    )
    assert failures is None


def test_dispatch_via_composition_returns_guard_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from unittest.mock import MagicMock

    from runtime.next import runtime_bridge as rb

    monkeypatch.setattr(rb, "_check_composed_action_guard", lambda *a, **k: ["missing artifact"])
    monkeypatch.setattr(
        "specify_cli.mission_step_contracts.executor.StepContractExecutor.execute",
        lambda self, context, contract=None: MagicMock(invocation_ids=()),
    )

    failures = composition._dispatch_via_composition(
        repo_root=tmp_path,
        mission="software-dev",
        action="specify",
        actor="implementer-pedro",
        profile_hint=None,
        request_text=None,
        mode_of_work=None,
        feature_dir=tmp_path,
    )
    assert failures == ["missing artifact"]


def test_dispatch_via_composition_surfaces_structured_executor_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from specify_cli.mission_step_contracts.executor import StepContractExecutionError

    def _raise(self: Any, context: Any, contract: Any = None) -> Any:
        raise StepContractExecutionError("synthesized contract missing")

    monkeypatch.setattr(
        "specify_cli.mission_step_contracts.executor.StepContractExecutor.execute", _raise
    )

    failures = composition._dispatch_via_composition(
        repo_root=tmp_path,
        mission="software-dev",
        action="specify",
        actor="implementer-pedro",
        profile_hint=None,
        request_text=None,
        mode_of_work=None,
        feature_dir=tmp_path,
    )
    assert failures is not None
    assert "composition failed for software-dev/specify" in failures[0]


def test_dispatch_via_composition_surfaces_unexpected_exception_as_structured_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def _raise(self: Any, context: Any, contract: Any = None) -> Any:
        raise ValueError("malformed contract yaml")

    monkeypatch.setattr(
        "specify_cli.mission_step_contracts.executor.StepContractExecutor.execute", _raise
    )

    failures = composition._dispatch_via_composition(
        repo_root=tmp_path,
        mission="software-dev",
        action="specify",
        actor="implementer-pedro",
        profile_hint=None,
        request_text=None,
        mode_of_work=None,
        feature_dir=tmp_path,
    )
    assert failures is not None
    assert "composition crashed for software-dev/specify" in failures[0]
    assert "ValueError" in failures[0]


def test_dispatch_via_composition_uses_live_lookup_for_check_composed_action_guard(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Live-lookup regression: ``_dispatch_via_composition`` must resolve
    ``_check_composed_action_guard`` via a live lookup through
    ``runtime_bridge`` -- both symbols now live in this same seam module, the
    exact intra-seam false-green trap contracts/compat-surface.md warns
    about."""
    from unittest.mock import MagicMock

    from runtime.next import runtime_bridge as rb

    calls: list[str] = []

    def _spy_guard(action: str, feature_dir: Path, *, mission: str = "software-dev", legacy_step_id: str | None = None) -> list[str]:
        calls.append(action)
        return ["patched-failure"]

    monkeypatch.setattr(rb, "_check_composed_action_guard", _spy_guard)
    monkeypatch.setattr(
        "specify_cli.mission_step_contracts.executor.StepContractExecutor.execute",
        lambda self, context, contract=None: MagicMock(invocation_ids=()),
    )

    failures = composition._dispatch_via_composition(
        repo_root=tmp_path,
        mission="software-dev",
        action="specify",
        actor="implementer-pedro",
        profile_hint=None,
        request_text=None,
        mode_of_work=None,
        feature_dir=tmp_path,
    )

    assert calls == ["specify"]
    assert failures == ["patched-failure"]


# ---------------------------------------------------------------------------
# 5. _advance_run_state_after_composition residual delegate -- untouched by
#    this WP, but pinned here so a future edit to the surrounding module
#    cannot silently break the compat surface WP03 established.
# ---------------------------------------------------------------------------


def test_advance_run_state_after_composition_delegate_still_forwards_to_engine_adapter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from runtime.next import runtime_bridge as rb

    captured: dict[str, Any] = {}
    sentinel_decision = object()

    def _fake_advance(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return sentinel_decision

    monkeypatch.setattr(engine_seam, "advance_run_state_after_composition", _fake_advance)

    from runtime.next._internal_runtime import MissionRunRef

    run_ref = MissionRunRef(run_id="run-1", run_dir=str(tmp_path), mission_key="software-dev")
    result = rb._advance_run_state_after_composition(
        run_ref=run_ref,
        agent="agent-1",
        mission_slug="mission-1",
        mission_type="software-dev",
        repo_root=tmp_path,
        feature_dir=tmp_path,
        timestamp="2026-01-01T00:00:00Z",
        progress=None,
        origin={},
        sync_emitter=object(),
    )

    assert result is sentinel_decision
    assert captured["run_ref"] is run_ref
    assert captured["mission_slug"] == "mission-1"
