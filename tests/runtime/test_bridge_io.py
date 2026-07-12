"""I/O-port seam tests for ``runtime_bridge_io`` (#2531 WP05, FR-006).

Four independent concerns:

1. **Non-vacuousness / compat-guard checks** — the seam actually defines every
   symbol T017-T019 relocated, and every one of those the WP02 compat guard
   binds stays a NATIVE ``def``/``class`` statement on ``runtime_bridge``
   (never a plain ``import`` alias) — the exact discipline WP03's
   ``runtime_bridge_engine`` and WP04's ``runtime_bridge_retrospective``
   already apply, required because ``test_bridge_compat_surface.py``'s
   ``test_guard_b_identity_reexport_for_relocated_symbols`` (frozen) hardcodes
   the tolerated cross-module baseline to the 3 pre-existing
   ``runtime.next.decision``-origin names.

2. **Focused unit tests (FR-006)** against the moved ports in isolation —
   stubbing the underlying I/O (tmp_path fixtures, monkeypatched
   ``runtime_bridge`` guard-helpers) rather than driving the real runtime.
   These pin the behavior-preserving move (C-001) for: the feature-runs
   index, template/pack discovery, run lifecycle, the OC builder,
   ``gather_artifact_presence`` (T018), and ``resolve_commit_target`` (T019,
   tested as a pure no-I/O function per NFR-003).

3. **Intra-seam / cross-seam live-lookup regression** (the WP05-specific risk
   flagged in ``research.md`` §Compat and ``contracts/compat-surface.md``):
   now that the moved cluster lives together in one seam module (plus calls
   back into compat-tracked names that stay in the residual), a bare
   intra-module/direct call would resolve via the seam's own globals (or fail
   to resolve at all) — bypassing a ``monkeypatch.setattr(runtime_bridge,
   "<name>", …)``. ``test_*_uses_live_lookup_for_*`` pin this by patching the
   callee on ``runtime_bridge`` and asserting the (unpatched) caller in the
   seam still observes it. ``_build_discovery_context`` is the grounded 🔴
   high-risk case research.md names explicitly.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from runtime.next._internal_runtime import MissionRunRef
from runtime.next import runtime_bridge_io as io_seam

# ---------------------------------------------------------------------------
# 1. Non-vacuousness / compat-guard checks
# ---------------------------------------------------------------------------

# Every symbol T017-T019 relocated to runtime_bridge_io.py that the WP02
# compat guard binds (ALL_COMPAT_SYMBOLS / REACH in
# test_bridge_compat_surface.py) -- MUST stay a native def/class on
# runtime_bridge, never a plain re-export (see module docstring above).
_COMPAT_GUARDED_NAMES = frozenset(
    {
        "_load_feature_runs",
        "_build_run_ref",
        "_mission_key_for_run_ref",
        "_build_discovery_context",
        "_resolve_runtime_template_in_root",
        "_runtime_template_key",
        "_existing_run_ref",
        "_start_ephemeral_query_run",
        "_resolve_run_dir_for_mission",
        "_resolve_tech_stack_for_profile",
        "_build_operational_context_for_decision",
    }
)

# Public (non-underscore) names moved by this WP. Not part of the WP02 guard's
# tracked `_`-prefixed inventory (that guard's grep only matches leading-
# underscore names), but heavily monkeypatched directly on `runtime_bridge` by
# OTHER (non-frozen) test files -- e.g. tests/unit/mission_loader/test_command.py,
# tests/integration/test_mission_run_command.py. Kept as native thin delegates
# for the same safety, even though not strictly required by guard B.
_PUBLIC_RELOCATED_NAMES = frozenset({"get_or_start_run", "build_operational_context_for_claim"})


def test_seam_defines_every_relocated_symbol() -> None:
    """Non-vacuousness check: the seam must actually define every relocated
    name, or the native-thin-delegate assertion below would pass for the
    wrong reason (nobody needing the port at all).

    ``_load_feature_runs`` is deliberately excluded here: its "body" on the
    seam is the composition ``load_feature_runs(_feature_runs_path(repo_root))``
    (the textbook path-based port + the repo_root -> path resolver), not a
    literal ``_load_feature_runs`` name on ``runtime_bridge_io`` -- only the
    residual keeps that exact repo_root-keyed compat name.
    """
    seam_names = (_COMPAT_GUARDED_NAMES - {"_load_feature_runs"}) | _PUBLIC_RELOCATED_NAMES | {
        "resolve_commit_target",
        "gather_artifact_presence",
        "load_feature_runs",
        "save_feature_runs",
        "_feature_runs_path",
    }
    for name in sorted(seam_names):
        assert hasattr(io_seam, name), f"seam is missing relocated symbol {name!r}"


def test_runtime_bridge_keeps_native_thin_delegates_for_compat_guarded_names() -> None:
    """Every compat-guarded symbol must stay a NATIVE ``def``/``class``
    statement in runtime_bridge.py (a thin delegate), never a plain
    ``import`` alias -- otherwise the WP02 compat guard's hardcoded
    identity/relocated-symbol baseline
    (``test_guard_b_identity_reexport_for_relocated_symbols``) trips."""
    from runtime.next import runtime_bridge as rb

    for name in sorted(_COMPAT_GUARDED_NAMES | _PUBLIC_RELOCATED_NAMES):
        obj = getattr(rb, name)
        assert obj.__module__ == rb.__name__, (
            f"{name!r} on runtime_bridge is NOT natively defined there "
            f"(__module__={obj.__module__!r}) -- it must be a native thin "
            "delegate, not a plain re-export, or guard B's hardcoded "
            "relocated-symbol baseline will fail."
        )


def test_runtime_bridge_no_longer_owns_feature_runs_file_constants() -> None:
    """The move actually happened: the residual no longer defines the
    feature-runs-index leaf constants (``_feature_runs_path``,
    ``MISSION_RUNTIME_YAML``, ``MISSION_YAML``) -- they live solely on the
    seam now (mirrors the WP04 "only seam owns this import surface" check,
    scoped to this WP's leaf constants instead of a third-party package)."""
    from runtime.next import runtime_bridge as rb

    assert not hasattr(rb, "_feature_runs_path")
    assert not hasattr(rb, "MISSION_RUNTIME_YAML")
    assert not hasattr(rb, "MISSION_YAML")
    assert not hasattr(rb, "_FEATURE_RUNS_FILE")
    # KITTIFY_DIR is still used by unmoved residual code (e.g. bulk_edit gate
    # path composition), so it legitimately stays defined on both modules.
    assert hasattr(rb, "KITTIFY_DIR")
    assert hasattr(io_seam, "KITTIFY_DIR")


# ---------------------------------------------------------------------------
# 2a. Feature-runs index port
# ---------------------------------------------------------------------------


def test_load_feature_runs_missing_file_returns_empty_dict(tmp_path: Path) -> None:
    assert io_seam.load_feature_runs(tmp_path / "does-not-exist.json") == {}


def test_load_feature_runs_malformed_json_returns_empty_dict(tmp_path: Path) -> None:
    path = tmp_path / "feature-runs.json"
    path.write_text("{not-json", encoding="utf-8")
    assert io_seam.load_feature_runs(path) == {}


def test_save_then_load_feature_runs_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "runtime" / "feature-runs.json"
    index: dict[str, io_seam._FeatureRunEntry] = {
        "042-test-feature": {
            "run_id": "01HRUNID000000000000000000",
            "run_dir": str(tmp_path / "runs" / "01HRUNID000000000000000000"),
            "mission_type": "software-dev",
            "mission_key": "software-dev",
            "mission_id": None,
            "mission_slug": "042-test-feature",
        }
    }
    io_seam.save_feature_runs(path, index)
    assert path.exists()
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == index
    assert io_seam.load_feature_runs(path) == index


def test_feature_runs_path_composes_kittify_runtime_location(tmp_path: Path) -> None:
    assert io_seam._feature_runs_path(tmp_path) == tmp_path / ".kittify" / "runtime" / "feature-runs.json"


def test_build_run_ref_uses_mission_key() -> None:
    ref = io_seam._build_run_ref(run_id="r1", run_dir="/tmp/r1", mission_type="software-dev")
    assert ref.run_id == "r1"
    assert ref.run_dir == "/tmp/r1"
    assert ref.mission_key == "software-dev"


def test_mission_key_for_run_ref_prefers_mission_key_then_mission_type_then_default() -> None:
    # _mission_key_for_run_ref reads both fields via getattr(...) duck-typing
    # (it tolerates cross-runtime-version MissionRunRef shapes -- see its
    # docstring), so a plain object stand-in is cast to the real type here
    # rather than constructing a full MissionRunRef for a field-presence test.
    ref_partial = cast(MissionRunRef, SimpleNamespace(mission_key="  ", mission_type="software-dev"))
    assert io_seam._mission_key_for_run_ref(ref_partial, default="fallback") == "software-dev"

    ref_neither = cast(MissionRunRef, SimpleNamespace(mission_key="", mission_type=None))
    assert io_seam._mission_key_for_run_ref(ref_neither, default="fallback") == "fallback"


# ---------------------------------------------------------------------------
# 2b. Discovery cluster
# ---------------------------------------------------------------------------


def test_candidate_templates_for_root_dedupes_and_orders(tmp_path: Path) -> None:
    root = tmp_path / "missions"
    root.mkdir()
    candidates = io_seam._candidate_templates_for_root(root, "software-dev")
    # De-duplicated (no repeats) and non-empty for a directory root.
    assert len(candidates) == len({str(c) for c in candidates})
    assert candidates  # at least one candidate composed for a dir root


def test_candidate_templates_for_root_single_file(tmp_path: Path) -> None:
    mission_yaml = tmp_path / "mission.yaml"
    mission_yaml.write_text("mission:\n  key: software-dev\n", encoding="utf-8")
    assert io_seam._candidate_templates_for_root(mission_yaml, "software-dev") == [mission_yaml]


def test_candidate_templates_for_root_rejects_unrelated_file(tmp_path: Path) -> None:
    other = tmp_path / "notes.txt"
    other.write_text("hello", encoding="utf-8")
    assert io_seam._candidate_templates_for_root(other, "software-dev") == []


def test_template_key_for_file_returns_none_on_load_failure(tmp_path: Path) -> None:
    bogus = tmp_path / "mission.yaml"
    bogus.write_text("not: valid: yaml: at: all:", encoding="utf-8")
    assert io_seam._template_key_for_file(bogus) is None


def test_split_env_paths_blank_is_empty() -> None:
    assert io_seam._split_env_paths("   ") == []


def test_split_env_paths_splits_on_os_pathsep(tmp_path: Path) -> None:
    import os

    joined = os.pathsep.join([str(tmp_path / "a"), str(tmp_path / "b")])
    assert io_seam._split_env_paths(joined) == [tmp_path / "a", tmp_path / "b"]


def test_project_config_pack_paths_missing_config_is_empty(tmp_path: Path) -> None:
    assert io_seam._project_config_pack_paths(tmp_path) == []


def test_project_config_pack_paths_reads_mission_packs(tmp_path: Path) -> None:
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text(
        "mission_packs:\n  - packs/one\n  - packs/two\n", encoding="utf-8"
    )
    assert io_seam._project_config_pack_paths(tmp_path) == [
        tmp_path / "packs/one",
        tmp_path / "packs/two",
    ]


def test_build_discovery_context_anchors_on_repo_root(tmp_path: Path) -> None:
    context = io_seam._build_discovery_context(tmp_path)
    assert context.project_dir == tmp_path
    assert len(context.builtin_roots) == 1
    assert context.builtin_roots[0].name == "missions"


# ---------------------------------------------------------------------------
# 2c. Run lifecycle
# ---------------------------------------------------------------------------


def test_existing_run_ref_returns_none_when_slug_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from runtime.next import runtime_bridge as rb

    monkeypatch.setattr(rb, "_load_feature_runs", lambda repo_root: {})
    assert io_seam._existing_run_ref("missing-mission", tmp_path, "software-dev") is None


def test_existing_run_ref_returns_none_when_state_file_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from runtime.next import runtime_bridge as rb

    run_dir = tmp_path / "runs" / "r1"
    run_dir.mkdir(parents=True)
    monkeypatch.setattr(
        rb,
        "_load_feature_runs",
        lambda repo_root: {"042-mission": {"run_id": "r1", "run_dir": str(run_dir)}},
    )
    assert io_seam._existing_run_ref("042-mission", tmp_path, "software-dev") is None


def test_existing_run_ref_builds_ref_when_state_file_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from runtime.next import runtime_bridge as rb

    run_dir = tmp_path / "runs" / "r1"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        rb,
        "_load_feature_runs",
        lambda repo_root: {
            "042-mission": {"run_id": "r1", "run_dir": str(run_dir), "mission_key": "software-dev"}
        },
    )
    ref = io_seam._existing_run_ref("042-mission", tmp_path, "software-dev")
    assert ref is not None
    assert ref.run_id == "r1"
    assert ref.mission_key == "software-dev"


def test_get_or_start_run_returns_existing_ref_without_starting_new_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """get_or_start_run must not call start_mission_run when a valid existing
    run is on record (mirrors the pre-extraction inline behavior)."""
    from runtime.next import runtime_bridge as rb

    run_dir = tmp_path / "runs" / "r1"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        rb,
        "_load_feature_runs",
        lambda repo_root: {
            "042-mission": {"run_id": "r1", "run_dir": str(run_dir), "mission_key": "software-dev"}
        },
    )

    def _should_not_start(**_kwargs: Any) -> Any:
        raise AssertionError("start_mission_run must not be called for an existing run")

    monkeypatch.setattr(io_seam, "start_mission_run", _should_not_start)

    ref = io_seam.get_or_start_run("042-mission", tmp_path, "software-dev")
    assert ref.run_id == "r1"


# ---------------------------------------------------------------------------
# 2d. OperationalContext (OC) builder
# ---------------------------------------------------------------------------


def test_resolve_run_dir_for_mission_none_when_no_run_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from runtime.next import runtime_bridge as rb

    monkeypatch.setattr(rb, "_load_feature_runs", lambda repo_root: {})
    assert io_seam._resolve_run_dir_for_mission(tmp_path, "042-mission") is None


def test_resolve_run_dir_for_mission_returns_recorded_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from runtime.next import runtime_bridge as rb

    monkeypatch.setattr(
        rb,
        "_load_feature_runs",
        lambda repo_root: {"042-mission": {"run_dir": str(tmp_path / "runs" / "r1")}},
    )
    assert io_seam._resolve_run_dir_for_mission(tmp_path, "042-mission") == tmp_path / "runs" / "r1"


def test_resolve_tech_stack_for_profile_empty_when_no_profile_id(tmp_path: Path) -> None:
    assert io_seam._resolve_tech_stack_for_profile(tmp_path, None) == frozenset()


def test_resolve_tech_stack_for_profile_empty_on_resolution_failure(tmp_path: Path) -> None:
    # No doctrine directory at all -> AgentProfileRepository resolution fails
    # -> best-effort empty frozenset (never raises), matching NFR-004.
    assert io_seam._resolve_tech_stack_for_profile(tmp_path, "nonexistent-profile") == frozenset()


def test_build_operational_context_for_claim_resolves_profile_from_run_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from runtime.next import runtime_bridge as rb

    monkeypatch.setattr(rb, "_resolve_run_dir_for_mission", lambda repo_root, mission_slug: tmp_path)
    monkeypatch.setattr(rb, "_resolve_step_agent_profile", lambda run_dir, activity: "python-pedro")
    monkeypatch.setattr(rb, "_resolve_tech_stack_for_profile", lambda repo_root, profile_id: frozenset({"python"}))

    oc = io_seam.build_operational_context_for_claim(
        repo_root=tmp_path,
        feature_dir=tmp_path,
        mission_slug="042-mission",
        wp_id="WP01",
        actor="claude",
        active_model="sonnet",
        active_role=None,
        current_activity="implement",
    )
    assert oc.active_profile == "python-pedro"
    assert oc.tech_stack == frozenset({"python"})
    assert oc.active_role == "claude"


def test_build_operational_context_for_claim_explicit_profile_skips_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from runtime.next import runtime_bridge as rb

    def _should_not_resolve(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("must not resolve run_dir when active_profile is explicit")

    monkeypatch.setattr(rb, "_resolve_run_dir_for_mission", _should_not_resolve)
    monkeypatch.setattr(rb, "_resolve_tech_stack_for_profile", lambda repo_root, profile_id: frozenset())

    oc = io_seam.build_operational_context_for_claim(
        repo_root=tmp_path,
        feature_dir=tmp_path,
        mission_slug="042-mission",
        wp_id="WP01",
        actor="claude",
        active_model="sonnet",
        active_role=None,
        active_profile="explicit-profile",
    )
    assert oc.active_profile == "explicit-profile"


# ---------------------------------------------------------------------------
# 3. T018 — gather_artifact_presence
# ---------------------------------------------------------------------------


def _stub_guard_helpers(
    monkeypatch: pytest.MonkeyPatch,
    *,
    requirement_mapping_failures: list[str] | None = None,
    occurrence_gate_failures: list[str] | None = None,
    source_documented_count: int = 0,
    publication_approved: bool = False,
    has_raw_dependencies_field: bool = True,
) -> None:
    """Stub the compat-tracked guard helpers ``gather_artifact_presence``
    reaches via live lookup.

    ``_has_generated_docs`` is deliberately NOT stubbed here: it is not part
    of the WP02 compat guard's tracked inventory (nothing patches it in
    production code), and ``tests/runtime/test_bridge_compat_surface.py``'s
    frozen ``test_reach_map_covers_the_full_grep_derived_inventory`` grep-scans
    the whole tests tree for any ``monkeypatch.setattr`` binding on
    ``runtime_bridge`` and fails if the bound name is not already a tracked
    symbol — introducing a new one here would trip that frozen gate. Tests
    that need ``has_generated_docs=True`` drive it with a real ``docs/*.md``
    file instead (see ``test_gather_artifact_presence_carries_generated_docs_flag``).
    """
    from runtime.next import runtime_bridge as rb

    monkeypatch.setattr(rb, "_check_requirement_mapping_ready", lambda feature_dir: requirement_mapping_failures or [])
    monkeypatch.setattr(rb, "_occurrence_gate_failures", lambda feature_dir: occurrence_gate_failures or [])
    monkeypatch.setattr(rb, "_count_source_documented_events", lambda feature_dir: source_documented_count)
    monkeypatch.setattr(rb, "_publication_approved", lambda feature_dir: publication_approved)
    monkeypatch.setattr(rb, "_has_raw_dependencies_field", lambda wp_file: has_raw_dependencies_field)


def test_gather_artifact_presence_reads_file_presence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_guard_helpers(monkeypatch)
    (tmp_path / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (tmp_path / "plan.md").write_text("# Plan\n", encoding="utf-8")

    snapshot = io_seam.gather_artifact_presence(
        tmp_path, mission_family="software-dev", step_id="tasks_outline"
    )
    assert snapshot.present_artifacts == {"spec.md", "plan.md"}
    assert snapshot.mission_family == "software-dev"
    assert snapshot.step_id == "tasks_outline"
    assert snapshot.legacy_step_id is None
    assert snapshot.status_facts["tasks_dir_is_dir"] is False
    assert snapshot.status_facts["wp_ids"] == ()


def test_gather_artifact_presence_reads_wp_lane_and_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_guard_helpers(monkeypatch, has_raw_dependencies_field=False)
    monkeypatch.setattr(io_seam, "get_wp_lane", lambda feature_dir, wp_id: "for_review")

    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "WP01-writeside.md").write_text("# WP01\n", encoding="utf-8")

    snapshot = io_seam.gather_artifact_presence(
        tmp_path, mission_family="software-dev", step_id="implement", legacy_step_id="tasks_finalize"
    )
    assert "tasks_wp_files" in snapshot.present_artifacts
    assert snapshot.status_facts["tasks_dir_is_dir"] is True
    assert snapshot.status_facts["wp_ids"] == ("WP01",)
    assert snapshot.status_facts["wp_lane_raw"] == {"WP01": "for_review"}
    assert snapshot.status_facts["wp_dependencies_present"] == {"WP01": False}
    assert snapshot.legacy_step_id == "tasks_finalize"


def test_gather_artifact_presence_carries_research_facts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_guard_helpers(
        monkeypatch,
        source_documented_count=3,
        publication_approved=True,
    )
    snapshot = io_seam.gather_artifact_presence(tmp_path, mission_family="research", step_id="output")
    assert snapshot.status_facts["source_documented_count"] == 3
    assert snapshot.status_facts["publication_approved"] is True


def test_gather_artifact_presence_carries_generated_docs_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_guard_helpers(monkeypatch)
    docs_dir = tmp_path / "docs" / "guides"
    docs_dir.mkdir(parents=True)
    (docs_dir / "getting-started.md").write_text("# Getting started\n", encoding="utf-8")

    snapshot = io_seam.gather_artifact_presence(tmp_path, mission_family="documentation", step_id="generate")
    assert "generated_docs" in snapshot.present_artifacts
    assert snapshot.status_facts["has_generated_docs"] is True


def test_gather_artifact_presence_never_decides_only_gathers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sanity check on the FR-009 contract: the returned snapshot carries raw
    facts, not a pass/fail verdict -- there is no boolean "guards_passed" or
    similar decision field on the value object."""
    _stub_guard_helpers(monkeypatch, requirement_mapping_failures=["missing refs for WPs: WP01"])
    snapshot = io_seam.gather_artifact_presence(tmp_path, mission_family="software-dev", step_id="tasks_packages")
    assert snapshot.status_facts["requirement_mapping_failures"] == ("missing refs for WPs: WP01",)
    assert not hasattr(snapshot, "guards_passed")
    assert not hasattr(snapshot, "guard_failures")


# ---------------------------------------------------------------------------
# 4. T019 — resolve_commit_target (pure, no I/O -- NFR-003)
# ---------------------------------------------------------------------------


def test_resolve_commit_target_non_coord_topology_lands_on_repo_root(tmp_path: Path) -> None:
    mid8, worktree_root, target = io_seam.resolve_commit_target(
        coord_routing_topology=False,
        mission_slug="042-mission",
        mission_id="01HULIDXXXXXXXXXXXXXXXXXXX",
        coordination_branch="kitty/mission-042-mission",
        repo_root=tmp_path,
    )
    assert worktree_root == tmp_path
    assert target.ref == "kitty/mission-042-mission"
    assert mid8 == "01HULIDX"


def test_resolve_commit_target_coord_topology_computes_candidate_worktree_path(tmp_path: Path) -> None:
    mission_id = "01HULIDXXXXXXXXXXXXXXXXXXX"
    mid8, worktree_root_candidate, target = io_seam.resolve_commit_target(
        coord_routing_topology=True,
        mission_slug="042-mission",
        mission_id=mission_id,
        coordination_branch="kitty/mission-042-mission-01hulidx-coord",
        repo_root=tmp_path,
    )
    assert mid8 == "01hulidx".upper()[:8].lower() or mid8 == mission_id[:8]
    assert worktree_root_candidate == tmp_path / ".worktrees" / f"042-mission-{mid8}-coord"
    assert target.ref == "kitty/mission-042-mission-01hulidx-coord"
    # No disk I/O performed: the candidate path need not exist on disk.
    assert not worktree_root_candidate.exists()


def test_resolve_commit_target_raises_when_coord_topology_has_no_resolvable_mid8(tmp_path: Path) -> None:
    from runtime.next.runtime_bridge import DecisionGitLogUnavailable

    with pytest.raises(DecisionGitLogUnavailable):
        io_seam.resolve_commit_target(
            coord_routing_topology=True,
            mission_slug="bare-slug-no-tail",
            mission_id=None,
            coordination_branch="kitty/mission-bare-slug-no-tail",
            repo_root=tmp_path,
        )


# ---------------------------------------------------------------------------
# Live-lookup regressions (the WP05-specific false-green risk)
# ---------------------------------------------------------------------------


def test_runtime_template_key_uses_live_lookup_for_build_discovery_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The grounded 🔴 high-risk case research.md §Compat names explicitly:
    ``_build_discovery_context`` is patched in production tests
    (``test_query_mode_unit.py:751``) and reached only via intra-seam movers
    -- ``_runtime_template_key`` must resolve it via a live lookup through
    ``runtime_bridge``, never a bare intra-module call."""
    from runtime.next import runtime_bridge as rb

    calls: list[Path] = []
    sentinel_context = rb._build_discovery_context(tmp_path)

    def _spy(repo_root: Path) -> Any:
        calls.append(repo_root)
        return sentinel_context

    monkeypatch.setattr(rb, "_build_discovery_context", _spy)
    monkeypatch.setattr(rb, "_resolve_runtime_template_in_root", lambda root, mission_type: None)

    io_seam._runtime_template_key("software-dev", tmp_path)

    assert calls == [tmp_path]


def test_runtime_template_key_uses_live_lookup_for_resolve_runtime_template_in_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same false-green risk for ``_resolve_runtime_template_in_root`` --
    both it and its caller ``_runtime_template_key`` moved into this same
    seam module."""
    from runtime.next import runtime_bridge as rb

    resolved = tmp_path / "mission.yaml"
    calls: list[str] = []

    def _spy(root: Path, mission_type: str) -> Path | None:
        calls.append(mission_type)
        return resolved

    monkeypatch.setattr(rb, "_resolve_runtime_template_in_root", _spy)

    result = io_seam._runtime_template_key("software-dev", tmp_path)

    assert calls, "the patched runtime_bridge._resolve_runtime_template_in_root was never invoked"
    assert result == str(resolved)


def test_existing_run_ref_uses_live_lookup_for_load_feature_runs_and_build_run_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from runtime.next import runtime_bridge as rb

    run_dir = tmp_path / "runs" / "r1"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text("{}", encoding="utf-8")

    load_calls: list[Path] = []
    build_calls: list[dict[str, Any]] = []

    def _spy_load(repo_root: Path) -> dict[str, Any]:
        load_calls.append(repo_root)
        return {"042-mission": {"run_id": "r1", "run_dir": str(run_dir)}}

    def _spy_build(*, run_id: str, run_dir: str, mission_type: str) -> Any:
        build_calls.append({"run_id": run_id, "run_dir": run_dir, "mission_type": mission_type})
        # Call the seam's real implementation directly -- NOT rb._build_run_ref,
        # which this very monkeypatch has replaced (calling it here would spy
        # on itself and recurse forever).
        return io_seam._build_run_ref(run_id=run_id, run_dir=run_dir, mission_type=mission_type)

    monkeypatch.setattr(rb, "_load_feature_runs", _spy_load)
    monkeypatch.setattr(rb, "_build_run_ref", _spy_build)

    ref = io_seam._existing_run_ref("042-mission", tmp_path, "software-dev")

    assert load_calls == [tmp_path]
    assert build_calls == [{"run_id": "r1", "run_dir": str(run_dir), "mission_type": "software-dev"}]
    assert ref is not None


def test_get_or_start_run_uses_live_lookup_for_resolve_mission_ulid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cross-seam-to-residual risk: ``_resolve_mission_ulid`` stays on the
    identity cluster in the residual (not moved by this WP); ``get_or_start_run``
    (moved) must still reach it via a live lookup, not a stale cached import."""
    from runtime.next import runtime_bridge as rb

    monkeypatch.setattr(rb, "_load_feature_runs", lambda repo_root: {})
    monkeypatch.setattr(rb, "_runtime_template_key", lambda mission_type, repo_root: "software-dev")
    monkeypatch.setattr(io_seam, "_workflow_runtime_template", lambda *a, **k: (None, None))

    class _FakeRunRef:
        run_id = "new-run"
        run_dir = str(tmp_path / "runs" / "new-run")
        mission_key = "software-dev"
        mission_type = "software-dev"

    monkeypatch.setattr(io_seam, "start_mission_run", lambda **_kw: _FakeRunRef())

    calls: list[str] = []

    def _spy_resolve_mission_ulid(mission_slug: str, repo_root: Path) -> str | None:
        calls.append(mission_slug)
        return "01HULIDXXXXXXXXXXXXXXXXXXX"

    monkeypatch.setattr(rb, "_resolve_mission_ulid", _spy_resolve_mission_ulid)

    io_seam.get_or_start_run("042-mission", tmp_path, "software-dev")

    assert calls == ["042-mission"]


def test_build_operational_context_for_claim_uses_live_lookup_for_resolve_tech_stack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Intra-seam risk: ``build_operational_context_for_claim`` and
    ``_resolve_tech_stack_for_profile`` both moved into this seam module."""
    from runtime.next import runtime_bridge as rb

    monkeypatch.setattr(rb, "_resolve_run_dir_for_mission", lambda repo_root, mission_slug: None)

    calls: list[str | None] = []

    def _spy(repo_root: Path, profile_id: str | None) -> frozenset[str]:
        calls.append(profile_id)
        return frozenset({"python"})

    monkeypatch.setattr(rb, "_resolve_tech_stack_for_profile", _spy)

    oc = io_seam.build_operational_context_for_claim(
        repo_root=tmp_path,
        feature_dir=tmp_path,
        mission_slug="042-mission",
        wp_id="WP01",
        actor="claude",
        active_model="sonnet",
        active_role=None,
        active_profile="explicit-profile",
    )

    assert calls == ["explicit-profile"]
    assert oc.tech_stack == frozenset({"python"})
