"""FR-012 / SC-006 compat-surface guard for ``runtime.next.runtime_bridge``.

**Mission runtime-bridge-degod-01KX8M1C (#2531), WP02 — the biggest land-ability
risk.** Tests bind to ~50 distinct private symbols on ``runtime_bridge`` across
four idioms (``from …runtime_bridge import _x``, ``monkeypatch.setattr(...,
"_x", ...)``, ``mocker.patch("...runtime_bridge._x")``, bare
``runtime_bridge._x``). When a later extraction WP relocates a symbol to a seam
module, a **plain re-export can silently break patching**:
``monkeypatch.setattr(runtime_bridge, "_x", …)`` becomes a no-op if ``_x``'s
leaf is called by another function that moved into the *same* seam — the
intra-seam call resolves via the seam module's own global, not the shim, and
the test passes by coincidence (false-green). This module is the guard that
makes that regression impossible to land silently.

Built now, against **unmodified source** (nothing has moved yet), so its
current state is GREEN — see ``contracts/compat-surface.md``.

Guard (A) — per-entry behavioral sentinel
==========================================
For each symbol, patch ``runtime_bridge.<name>`` with a **call-through spy**
(records the call, then delegates to the real, captured-before-patching
implementation) and drive the *public entry that reaches it* — one of
``decide_next_via_runtime``, ``query_current_state``, or
``answer_decision_via_runtime`` (T007's binding per-entry reach map, below).
Assert the spy recorded at least one call.

**Why a call-through spy instead of a raising marker.** The WP-02 prompt's
illustrative sketch (research.md §Compat) raises a unique exception and
asserts ``pytest.raises``. That mechanism is unsound for several symbols in
*this* module: their only call sites sit behind a legitimate
``except Exception`` swallow the production code relies on for graceful
degradation (e.g. ``_wrap_with_decision_git_log``'s non-coordination fallback
at :272-285 catches ANY construction failure and falls back to the plain
emitter; ``_run_retrospective_learning_capture``'s outer try at :814-823
swallows non-blocking retrospective failures by design). A raising sentinel
there would be silently absorbed by *correct* production code and produce a
false RED on unmodified source — failing the "green on unmodified source"
acceptance bar while proving nothing about reachability. A call-through spy
sidesteps this entirely: it still "changes behavior at the call site" (the
literal SC-006 assertion — the spy list is now non-empty, an externally
observable change), it lets the surrounding control flow run exactly as
production intends (no swallowed-exception ambiguity), and it is symmetric
under the false-green failure mode this guard exists to catch: if a future
extraction makes the patch a no-op (an intra-seam call bypasses the shim),
the spy never fires, the recorder stays empty, and the assertion fails loud —
identically to what a raising sentinel would have caught, just without the
swallow false-negative.

Per-symbol -> reaching-entry map (T007/T010, BINDING — re-run this guard as
the acceptance gate for every extraction WP that touches a listed symbol)
--------------------------------------------------------------------------
Grep-derived inventory (``tests/**/*.py`` idiom scan; 50 symbols, matches the
WP's "~50" count exactly after excluding cross-module regex noise — see
``_INVENTORY_NOTE`` below for the excluded matches and the two symbols that
are demonstrably NOT reachable from any of the three canonical public entries
today (flagged, not faked)).

    decide_next_via_runtime only:
        _compute_wp_progress, _build_operational_context_for_decision,
        _is_wp_iteration_step, _should_advance_wp_step,
        _build_wp_iteration_decision, _check_cli_guards,
        _check_composed_action_guard, _check_requirement_mapping_ready,
        _has_raw_dependencies_field, _occurrence_gate_failures,
        _parse_requirement_refs_from_tasks_md, _should_dispatch_via_composition,
        _normalize_action_for_composition, _dispatch_via_composition,
        _advance_run_state_after_composition, _resolve_retrospective_policy_for_runtime,
        _resolve_mission_id_for_terminus, _run_retrospective_learning_capture,
        _build_retrospective_facilitator_callback, _classify_and_emit_failure,
        _classify_exc, _remediation_hint, _BufferingRuntimeEmitter,
        _map_runtime_decision, _state_to_action (decision.py; exercised via
        the bridge's call sites), _build_prompt_or_error (ditto),
        _resolve_step_agent_profile, _resolve_tech_stack_for_profile

    decide_next_via_runtime AND answer_decision_via_runtime (identity /
    run-bootstrap cluster — driven through BOTH per T008's multi-entry rule):
        _wrap_with_decision_git_log, _mission_routes_through_coordination,
        _resolve_coordination_branch, _resolve_mission_ulid,
        _primary_runtime_feature_dir

    decide_next_via_runtime / query_current_state / answer_decision_via_runtime
    (run/template bootstrap shared by all three; driven via decide_next):
        _load_feature_runs, _build_run_ref, _mission_key_for_run_ref
        (decide_next + answer only — query uses ``_existing_run_ref``, not
        ``get_or_start_run``), _runtime_template_key,
        _resolve_runtime_template_in_root, _build_discovery_context

    query_current_state only:
        _existing_run_ref, _start_ephemeral_query_run,
        _finalized_task_board_override_step,
        _build_finalized_override_query_decision, _build_initial_query_decision,
        _build_decision_required_query, _build_runtime_query_decision

    NOT reachable from any of the 3 canonical public entries (flagged, not
    faked — see ``test_flagged_symbols_are_genuinely_unreachable`` below):
        _resolve_run_dir_for_mission (sole call site is
            ``build_operational_context_for_claim``, a 4th public function
            used by the WP-claim CLI path, never by decide_next/query/answer)
        _rich_hic_prompt (defined but never called anywhere in
            runtime_bridge.py today — its only production wiring point,
            an interactive HiC facilitator prompt callback, is not reached
            by any currently-implemented code path in this module)

Guard (B) — static AST guard
=============================
1. **Identity re-export.** For every compat symbol that is *not* natively
   defined in ``runtime_bridge.py`` (i.e. imported from elsewhere — this is
   currently a no-op set since nothing has been relocated yet, but the
   machinery below is what WP03+ extraction gates run against), assert
   ``getattr(runtime_bridge, name) is getattr(<origin module>, name)``.
2. **Forbid function-scope re-imports of compat names.** AST-walk
   ``runtime_bridge.py`` for any ``Import``/``ImportFrom`` binding a compat
   name below module scope (inside a function/method body) — the exact
   structural signature of false-green shadowing (a local re-import shadows
   the patched module global).
"""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from runtime.next import runtime_bridge as rb
from runtime.next.decision import DecisionKind

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

# ---------------------------------------------------------------------------
# Scaffold helpers — self-contained (T007/T008/T009/T010 own this file only;
# no cross-file test-helper dependency). Pattern mirrors the established
# runtime-bridge fixture shape used by tests/next/test_runtime_bridge_unit.py
# (git repo + kitty-specs/<slug>/meta.json + tasks/WP*.md + event-log seed is
# sufficient for get_or_start_run to resolve the REAL built-in software-dev
# template and drive the REAL engine end to end — no engine stubbing needed).
# ---------------------------------------------------------------------------


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init", "--initial-branch=main"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True, check=True)
    (path / "README.md").write_text("# test", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True, check=True)


def _scaffold_project(
    tmp_path: Path,
    mission_slug: str,
    mission_type: str = "software-dev",
) -> Path:
    from tests.lane_test_utils import write_mission_meta

    repo_root = tmp_path / "project"
    repo_root.mkdir()
    _init_git_repo(repo_root)
    (repo_root / ".kittify").mkdir()
    feature_dir = repo_root / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    # Modern ULID mission_id + mid8 meta (canonical shared test utility, see
    # tests/lane_test_utils.py) so the M-1 empty-mid8 guard and lanes.json
    # resolution both work when a scenario advances into WP workspace
    # resolution (e.g. the "tasks"/"implement" composed actions).
    write_mission_meta(feature_dir, mission_type=mission_type)
    return repo_root


def _seed_wp_lane(feature_dir: Path, wp_id: str, lane: str) -> None:
    from specify_cli.status.models import Lane, StatusEvent
    from specify_cli.status.store import append_event

    canonical_lane = {"doing": "in_progress"}.get(lane, lane)
    event = StatusEvent(
        event_id=f"test-{wp_id}-{canonical_lane}",
        mission_slug=feature_dir.name,
        wp_id=wp_id,
        from_lane=Lane.PLANNED,
        to_lane=Lane(canonical_lane),
        at="2026-01-01T00:00:00+00:00",
        actor="test",
        force=True,
        execution_mode="worktree",
    )
    append_event(feature_dir, event)


def _write_complete_artifacts(feature_dir: Path, *, wp_lane: str = "done") -> None:
    """Seed spec/plan/tasks + one WP so every CLI/composed guard passes.

    ``wp_lane`` controls whether the single WP is already handed off (the
    "happy loop drives cleanly to terminal" scaffold) or left in-flight
    (the WP-iteration "stay" scaffold).
    """
    (feature_dir / "spec.md").write_text(
        "# Spec\n\n## Functional Requirements\n\n"
        "| ID | Requirement | Acceptance Criteria | Status |\n"
        "| --- | --- | --- | --- |\n"
        "| FR-001 | First | Covered by WP01. | proposed |\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    (tasks_dir / "WP01.md").write_text(
        f"---\nwork_package_id: WP01\nlane: {wp_lane}\ndependencies: []\n"
        "requirement_refs: [FR-001]\ntitle: WP01\n---\n# WP01\n",
        encoding="utf-8",
    )
    _seed_wp_lane(feature_dir, "WP01", wp_lane)
    # lanes.json is required once a scenario advances far enough to resolve a
    # WP workspace path (_state_to_action -> resolve_workspace_for_wp).
    from tests.lane_test_utils import write_single_lane_manifest

    write_single_lane_manifest(feature_dir, wp_ids=("WP01",))


def _drive_to_terminal(repo_root: Path, mission_slug: str, *, agent: str = "test", max_iters: int = 60) -> Any:
    decision = None
    for _ in range(max_iters):
        decision = rb.decide_next_via_runtime(agent, mission_slug, "success", repo_root)
        if decision.kind == DecisionKind.terminal:
            break
    return decision


def _drive_until_step(repo_root: Path, mission_slug: str, target_step_id: str, *, agent: str = "test", max_iters: int = 60) -> Any:
    """Drive decide_next repeatedly until ``target_step_id`` is issued (or terminal)."""
    decision = None
    for _ in range(max_iters):
        decision = rb.decide_next_via_runtime(agent, mission_slug, "success", repo_root)
        if decision.kind == DecisionKind.terminal:
            return decision
        if decision.step_id == target_step_id:
            return decision
    return decision


# ---------------------------------------------------------------------------
# Call-through spy (Guard A mechanism — see module docstring rationale)
# ---------------------------------------------------------------------------


class _Recorder:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def fired(self, name: str) -> bool:
        return name in self.calls


def _spy(monkeypatch: pytest.MonkeyPatch, name: str, recorder: _Recorder) -> None:
    """Patch ``rb.<name>`` with a call-through spy: records + delegates to the
    REAL implementation captured before patching. See module docstring for
    why this is the guard's sentinel mechanism instead of a raising marker.
    """
    original = getattr(rb, name)

    def _wrapper(*args: Any, **kwargs: Any) -> Any:
        recorder.calls.append(name)
        return original(*args, **kwargs)

    monkeypatch.setattr(rb, name, _wrapper)


# ---------------------------------------------------------------------------
# Scenario builders — each returns nothing; they drive a public entry with
# whichever compat symbols are ALREADY spied via monkeypatch, then the test
# asserts the recorder fired for the target symbol.
# ---------------------------------------------------------------------------


def _scenario_happy_loop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = _scaffold_project(tmp_path, "042-compat-guard")
    feature_dir = repo_root / "kitty-specs" / "042-compat-guard"
    _write_complete_artifacts(feature_dir, wp_lane="done")
    _drive_to_terminal(repo_root, "042-compat-guard")


def _scenario_wp_iteration_stay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = _scaffold_project(tmp_path, "042-compat-guard")
    feature_dir = repo_root / "kitty-specs" / "042-compat-guard"
    _write_complete_artifacts(feature_dir, wp_lane="planned")
    # Drive until the "implement" step is issued; WP01 stays "planned" so
    # _should_advance_wp_step returns False and _build_wp_iteration_decision
    # is invoked (the "stay in step" branch, decide_next_via_runtime:2655).
    _drive_until_step(repo_root, "042-compat-guard", "implement")
    rb.decide_next_via_runtime("test", "042-compat-guard", "success", repo_root)


def _scenario_answer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = _scaffold_project(tmp_path, "042-compat-guard")
    feature_dir = repo_root / "kitty-specs" / "042-compat-guard"
    _write_complete_artifacts(feature_dir, wp_lane="done")
    # Bootstrap a real run first so get_or_start_run resolves an existing one.
    rb.decide_next_via_runtime("test", "042-compat-guard", "success", repo_root)
    with pytest.raises(Exception):  # noqa: B017 — any failure past our spies is fine
        rb.answer_decision_via_runtime(
            "042-compat-guard", "nonexistent-decision", "yes", "test", repo_root
        )


def _scenario_query_existing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = _scaffold_project(tmp_path, "042-compat-guard")
    feature_dir = repo_root / "kitty-specs" / "042-compat-guard"
    _write_complete_artifacts(feature_dir, wp_lane="done")
    # A real run must exist first: _existing_run_ref only calls _build_run_ref
    # when feature-runs.json already has an entry for this mission -- an
    # empty index falls through to the ephemeral-run path instead.
    rb.decide_next_via_runtime("test", "042-compat-guard", "success", repo_root)
    # WP already done + total_wps>0 -> _finalized_task_board_override_step
    # returns "done" -> _build_finalized_override_query_decision.
    rb.query_current_state("test", "042-compat-guard", repo_root)


def _scenario_query_fresh_ephemeral(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = _scaffold_project(tmp_path, "042-compat-guard")
    feature_dir = repo_root / "kitty-specs" / "042-compat-guard"
    # No tasks/ dir at all yet -> no existing run -> _start_ephemeral_query_run
    # bootstraps a fresh throwaway run; empty progress -> _build_initial_query_decision.
    feature_dir.mkdir(parents=True, exist_ok=True)
    rb.query_current_state("test", "042-compat-guard", repo_root)


def _seed_research_artifacts(feature_dir: Path) -> None:
    """Seed every artifact the research composed-guard chain demands so the
    mission advances cleanly through gathering (source-count) and output
    (publication) to terminal — the real guards read these from disk."""
    (feature_dir / "spec.md").write_text("# spec\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
    (feature_dir / "source-register.csv").write_text(
        "id,citation\n1,Source 1\n2,Source 2\n3,Source 3\n", encoding="utf-8"
    )
    (feature_dir / "findings.md").write_text("# findings\n", encoding="utf-8")
    (feature_dir / "report.md").write_text("# report\n", encoding="utf-8")
    events = [{"name": f"src-{i}", "type": "source_documented"} for i in (1, 2, 3)]
    events.append({"name": "publication_approved", "type": "gate_passed"})
    (feature_dir / "mission-events.jsonl").write_text(
        "\n".join(json.dumps(e, sort_keys=True) for e in events) + "\n", encoding="utf-8"
    )


def _scenario_research_loop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive a fully-seeded research mission to terminal. Research actions route
    through composition (charter action_sequence), so the gathering guard fires
    ``_count_source_documented_events`` and the output guard fires
    ``_publication_approved`` — neither is reachable from software-dev's guard
    family, hence a dedicated research scenario."""
    slug = "050-research-compat"
    repo_root = _scaffold_project(tmp_path, slug, mission_type="research")
    feature_dir = repo_root / "kitty-specs" / slug
    _seed_research_artifacts(feature_dir)
    for _ in range(40):
        decision = rb.decide_next_via_runtime("test", slug, "success", repo_root)
        if decision.kind in (DecisionKind.terminal, DecisionKind.blocked):
            break


def _scenario_retrospective_forced_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.retrospective.policy import RetrospectivePolicy

    repo_root = _scaffold_project(tmp_path, "042-compat-guard")
    feature_dir = repo_root / "kitty-specs" / "042-compat-guard"
    _write_complete_artifacts(feature_dir, wp_lane="done")

    forced_policy = RetrospectivePolicy(enabled=True, timing="post_completion", failure_policy="warn")
    monkeypatch.setattr(
        "specify_cli.retrospective.policy.resolve_policy",
        lambda repo_root: (forced_policy, {"enabled": "test-forced"}),
    )
    monkeypatch.setattr(
        "specify_cli.retrospective.generator.generate_retrospective",
        lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("forced for compat guard")),
    )
    _drive_to_terminal(repo_root, "042-compat-guard")


def _scenario_retrospective_blocking_single_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.retrospective.policy import RetrospectivePolicy

    repo_root = _scaffold_project(tmp_path, "042-compat-guard")
    feature_dir = repo_root / "kitty-specs" / "042-compat-guard"
    _write_complete_artifacts(feature_dir, wp_lane="done")

    forced_policy = RetrospectivePolicy(enabled=True, timing="before_completion", failure_policy="block")
    monkeypatch.setattr(
        "specify_cli.retrospective.policy.resolve_policy",
        lambda repo_root: (forced_policy, {"enabled": "test-forced"}),
    )
    # A single call is enough: the _BufferingRuntimeEmitter wrapping happens
    # unconditionally whenever block_on_retrospective is True, BEFORE
    # runtime_next_step is even invoked (decide_next_via_runtime:2925-2951).
    rb.decide_next_via_runtime("test", "042-compat-guard", "success", repo_root)


_SCENARIOS = {
    "happy_loop": _scenario_happy_loop,
    "wp_iteration_stay": _scenario_wp_iteration_stay,
    "answer": _scenario_answer,
    "query_existing": _scenario_query_existing,
    "query_fresh_ephemeral": _scenario_query_fresh_ephemeral,
    "research_loop": _scenario_research_loop,
    "retrospective_forced_failure": _scenario_retrospective_forced_failure,
    "retrospective_blocking_single_call": _scenario_retrospective_blocking_single_call,
}

# ---------------------------------------------------------------------------
# T007/T010 — the binding per-symbol -> (scenario, ...) reach map. Each entry
# lists every scenario T008 requires the symbol be driven through (multi-entry
# symbols get more than one row-scenario per the "drive each reaching entry"
# rule; single-entry symbols get exactly the one scenario that exercises
# their unique reaching public entry).
# ---------------------------------------------------------------------------

REACH: dict[str, tuple[str, ...]] = {
    # decide_next_via_runtime only — reached on (almost) every happy-loop call
    "_compute_wp_progress": ("happy_loop",),
    "_build_operational_context_for_decision": ("happy_loop",),
    "_resolve_step_agent_profile": ("happy_loop",),
    "_resolve_tech_stack_for_profile": ("happy_loop",),
    "_resolve_runtime_feature_dir": ("happy_loop",),
    "_parse_wp_sections_from_tasks_md": ("happy_loop",),
    # Research-mission composed guard branches only (software-dev's guard
    # family never calls these two) — driven to research terminal so both the
    # gathering (source-count) and output (publication) guards fire.
    "_count_source_documented_events": ("research_loop",),
    "_publication_approved": ("research_loop",),
    "_is_wp_iteration_step": ("happy_loop",),
    "_should_advance_wp_step": ("happy_loop",),
    "_check_cli_guards": ("happy_loop",),
    "_check_composed_action_guard": ("happy_loop",),
    "_check_requirement_mapping_ready": ("happy_loop",),
    "_has_raw_dependencies_field": ("happy_loop",),
    "_occurrence_gate_failures": ("happy_loop",),
    "_parse_requirement_refs_from_tasks_md": ("happy_loop",),
    "_should_dispatch_via_composition": ("happy_loop",),
    "_normalize_action_for_composition": ("happy_loop",),
    "_dispatch_via_composition": ("happy_loop",),
    "_advance_run_state_after_composition": ("happy_loop",),
    "_map_runtime_decision": ("happy_loop",),
    "_state_to_action": ("happy_loop",),
    "_build_prompt_or_error": ("happy_loop",),
    "_resolve_retrospective_policy_for_runtime": ("happy_loop",),
    "_BufferingRuntimeEmitter": ("retrospective_blocking_single_call",),
    # WP-iteration "stay" branch — needs an in-flight (not-yet-advanced) WP.
    "_build_wp_iteration_decision": ("wp_iteration_stay",),
    # Retrospective terminus family — forced-failure scenario guarantees the
    # classify/remediation branches actually fire (rather than depending on
    # whatever the default policy happens to resolve to).
    "_resolve_mission_id_for_terminus": ("retrospective_forced_failure",),
    "_run_retrospective_learning_capture": ("retrospective_forced_failure",),
    "_build_retrospective_facilitator_callback": ("retrospective_forced_failure",),
    "_classify_and_emit_failure": ("retrospective_forced_failure",),
    "_classify_exc": ("retrospective_forced_failure",),
    "_remediation_hint": ("retrospective_forced_failure",),
    # Identity / decision-git-log cluster — reached from BOTH decide_next and
    # answer (T008 multi-entry rule; this is the 🔴 grounded false-green
    # minefield cluster from research.md §Compat).
    "_wrap_with_decision_git_log": ("happy_loop", "answer"),
    "_mission_routes_through_coordination": ("happy_loop", "answer"),
    "_resolve_coordination_branch": ("happy_loop", "answer"),
    "_resolve_mission_ulid": ("happy_loop", "answer"),
    "_primary_runtime_feature_dir": ("happy_loop", "answer"),
    # Run/template bootstrap shared by decide_next + query + answer; proven
    # via decide_next (the identical shared function is exercised regardless
    # of which of the three entries called get_or_start_run/_existing_run_ref).
    "_load_feature_runs": ("happy_loop", "query_existing"),
    "_build_run_ref": ("happy_loop", "query_existing"),
    "_mission_key_for_run_ref": ("happy_loop",),
    "_runtime_template_key": ("happy_loop", "query_fresh_ephemeral"),
    "_resolve_runtime_template_in_root": ("happy_loop", "query_fresh_ephemeral"),
    "_build_discovery_context": ("happy_loop", "query_fresh_ephemeral"),
    # query_current_state only
    "_existing_run_ref": ("query_existing",),
    "_start_ephemeral_query_run": ("query_fresh_ephemeral",),
    "_finalized_task_board_override_step": ("query_existing",),
    "_build_finalized_override_query_decision": ("query_existing",),
    # NB: the three per-branch query builders (_build_initial_query_decision,
    # _build_decision_required_query, _build_runtime_query_decision) are NOT
    # bound by any test (grep-derived inventory finds zero import/patch/attr
    # sites) — they are NOT compat surface, so they carry no guard-A sentinel.
    # If a future test binds one, the inventory-reconciliation test below fails
    # loudly until it is added back with its reaching scenario.
}

# Symbols confirmed (by direct call-graph enumeration of runtime_bridge.py,
# not vibes) to have NO call site reachable from decide_next_via_runtime,
# query_current_state, or answer_decision_via_runtime today. Flagged per the
# WP02 instruction ("flag, don't fake") rather than forced through a
# fabricated reach.
UNREACHABLE_FROM_CANONICAL_ENTRIES: dict[str, str] = {
    "_resolve_run_dir_for_mission": (
        "sole call site is build_operational_context_for_claim (a 4th public "
        "function used by the WP-claim CLI path); never called from "
        "decide_next_via_runtime, query_current_state, or "
        "answer_decision_via_runtime"
    ),
    "_rich_hic_prompt": (
        "defined but never called anywhere in runtime_bridge.py; its "
        "interactive HiC facilitator-prompt wiring point is not exercised by "
        "any currently-implemented code path in this module"
    ),
}

# Symbols bound by tests ONLY via ``from …runtime_bridge import _x`` + a direct
# call (never ``monkeypatch.setattr(runtime_bridge, "_x", …)`` /
# ``mocker.patch`` / bare-attribute assignment), whose sole decide_next call
# site sits behind a runtime guard that no canonical public-entry fixture
# drives. For an import-only binding the CORRECT and sufficient guard is (B)
# identity re-export: ``from runtime_bridge import _x`` keeps resolving to the
# real object iff runtime_bridge re-exports it. A guard-(A) behavioral sentinel
# does not apply — no test patches the module attribute, and driving the leaf
# would require a contrived custom mission no real caller exercises. These are
# still covered by guard (B) via ``ALL_COMPAT_SYMBOLS`` and by the inventory
# reconciliation; they simply carry no guard-(A) sentinel. Distinct from
# ``UNREACHABLE_FROM_CANONICAL_ENTRIES`` (which is verified NOT statically
# reachable): these ARE statically reachable, just never on a driven path.
GUARD_B_ONLY_IMPORT_SURFACE: dict[str, str] = {
    "_resolve_runtime_contract_for_step": (
        "import-only (tests/next/test_composition_gate_widening.py imports and "
        "calls it directly; no test patches runtime_bridge."
        "_resolve_runtime_contract_for_step). Its only decide_next call site is "
        "_composition_dispatch_inputs, which short-circuits (returns before this "
        "call) for every built-in mission because the action is already in the "
        "charter action_sequence; only a custom mission with a charter-miss "
        "action + agent_profile reaches it. Guard (B) identity re-export is the "
        "correct guard for its import-only binding."
    ),
}

# Regex-scan noise excluded from the grep-derived inventory: these matched a
# "monkeypatch.setattr(..., \"_x\", ...)" pattern in a file that also happens
# to mention runtime_bridge elsewhere, but the patch TARGET is a different
# module entirely (verified by inspecting each site). Recorded here so a
# future re-run of the inventory grep doesn't have to re-derive this.
_INVENTORY_NOISE_EXCLUDED = frozenset(
    {
        "_doc_path_for",  # selector_resolution module
        "_enforce_git_preflight",  # cli.commands.merge module
        "_err_console",  # selector_resolution module
        "_read_snapshot",  # _internal_runtime.engine module (not runtime_bridge)
        "_resolve_target_branch",  # cli.commands.merge module
        "_runtime_bridge_module",  # next_cmd module (a different symbol name
        # entirely, not runtime_bridge's own _x)
        "_validate_target_branch",  # cli.commands.merge module
    }
)

# _build_prompt_safe / _find_first_wp_by_lane are compat surface of
# runtime.next.decision (tests import them `from runtime.next.decision import
# _x`, never through runtime_bridge), so they are out of scope for THIS guard
# even though runtime_bridge.py itself imports and calls them internally.
_DECISION_MODULE_SYMBOLS_OUT_OF_SCOPE = frozenset({"_build_prompt_safe", "_find_first_wp_by_lane"})

# INTERNAL decomposition symbols introduced by the #2531 strangler itself and
# patched ONLY by the mission's OWN seam tests (tests/runtime/test_bridge_*.py)
# to drive their own logic. They are NOT external compat surface: no test
# outside the mission's own decomposition suite binds them, so relocating them
# breaks no external patcher — a guard-(A) sentinel and guard-(B) identity
# re-export are both inapplicable. They are the mission's private phase/dispatch
# implementation, deliberately excluded from the compat-surface inventory the
# same way the cross-module and decision-origin false positives above are. This
# is a registry entry (classifying new internal symbols), NOT a relaxation of
# any protective assertion — the ~50 real compat symbols keep every sentinel.
_INTERNAL_DECOMPOSITION_SYMBOLS = frozenset(
    {
        # WP09 (FR-010) decide_next phase functions — patched only by
        # test_bridge_decide_next.py's orchestration tests (and AST-scanned by
        # test_operational_context_wiring.py's moved wiring anchor).
        "_dn_bootstrap",
        "_dn_dependency_gate",
        "_dn_composition_dispatch",
        "_dn_decision_materialize",
        # WP08 composition-dispatch input helper — patched only by the mission's
        # own seam tests (test_bridge_composition.py via the composition-seam
        # alias; test_bridge_decide_next.py via rb to stub the dispatch phase).
        # The external test_runtime_bridge_composition.py only names it in prose.
        "_composition_dispatch_inputs",
    }
)


def _all_sentinel_cases() -> list[tuple[str, str]]:
    cases: list[tuple[str, str]] = []
    for name, scenarios in REACH.items():
        for scenario in scenarios:
            cases.append((name, scenario))
    return cases


# ===========================================================================
# Guard (A) — per-entry behavioral sentinel
# ===========================================================================


@pytest.mark.parametrize("name,scenario", _all_sentinel_cases(), ids=lambda v: v if isinstance(v, str) else None)
def test_patch_on_runtime_bridge_reaches_seam(
    name: str, scenario: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``monkeypatch.setattr(runtime_bridge, name, ...)`` must still change
    behavior when driving ``name``'s mapped reaching entry (see REACH / the
    module docstring's per-symbol table). A no-op patch (the false-green this
    guard exists to catch) leaves the recorder empty and this assertion red.
    """
    recorder = _Recorder()
    _spy(monkeypatch, name, recorder)
    _SCENARIOS[scenario](tmp_path, monkeypatch)
    assert recorder.fired(name), (
        f"{name!r} was patched on runtime_bridge but never observed via the "
        f"{scenario!r} scenario -- the patch is a no-op at this call site "
        "(false-green regression)."
    )


def test_reach_map_covers_the_full_grep_derived_inventory() -> None:
    """T007: the REACH map + the flagged-unreachable set together account for
    every symbol the grep-derived inventory found bound to runtime_bridge via
    the four compat idioms (import / monkeypatch.setattr / mocker.patch /
    bare attribute access).
    """
    covered = set(REACH) | set(UNREACHABLE_FROM_CANONICAL_ENTRIES) | set(GUARD_B_ONLY_IMPORT_SURFACE)
    # The inventory is re-derived here (not hardcoded) so this test breaks
    # loudly if a future test file starts binding a 51st symbol without the
    # guard being updated.
    inventory = _grep_derived_inventory()
    missing = inventory - covered
    assert not missing, f"Symbols bound by tests but missing from the compat guard: {sorted(missing)}"
    extra = covered - inventory
    assert not extra, f"Compat guard covers symbols no longer bound by any test: {sorted(extra)}"


def test_flagged_symbols_are_genuinely_unreachable() -> None:
    """The two symbols excluded from Guard (A) really have no call site
    reachable from any of the three canonical public entries -- verified by
    a direct AST scan of runtime_bridge.py's call graph, not by assertion.
    """
    tree = ast.parse(Path(rb.__file__).read_text(encoding="utf-8"))
    entry_names = {"decide_next_via_runtime", "query_current_state", "answer_decision_via_runtime"}

    # Build name -> set of names it calls (direct calls only; sufficient to
    # prove reachability transitively via a fixed-point closure below).
    calls: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            called = {
                n.func.id
                for n in ast.walk(node)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            }
            calls[node.name] = called

    # Fixed-point closure of everything reachable from the 3 entries.
    reachable: set[str] = set(entry_names)
    frontier = set(entry_names)
    while frontier:
        nxt: set[str] = set()
        for fn in frontier:
            for callee in calls.get(fn, ()):
                if callee not in reachable:
                    reachable.add(callee)
                    nxt.add(callee)
        frontier = nxt

    for name in UNREACHABLE_FROM_CANONICAL_ENTRIES:
        assert name not in reachable, (
            f"{name!r} IS reachable from a canonical entry per the AST call "
            "graph -- the UNREACHABLE_FROM_CANONICAL_ENTRIES flag is stale; "
            "move it into REACH with the entry that now reaches it."
        )


def _grep_derived_inventory() -> set[str]:
    """Re-derive the compat-symbol inventory straight from the test tree.

    Mirrors T007's instruction to enumerate the four idioms directly rather
    than trust a static list. Scoped to genuine ``runtime_bridge`` targets
    (see ``_INVENTORY_NOISE_EXCLUDED`` for the cross-module false positives a
    naive regex would otherwise pick up) and excludes the two symbols that
    are compat surface of ``runtime.next.decision``, not ``runtime_bridge``.
    """
    import re

    root = Path(__file__).resolve().parents[1]  # tests/
    self_path = Path(__file__).resolve()
    names: set[str] = set()
    for path in root.rglob("*.py"):
        if path == self_path:
            # This guard's own docstring illustrates the four idioms with a
            # literal placeholder (e.g. "runtime_bridge._x") -- scanning it
            # would inject a spurious "_x" symbol into the inventory.
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "runtime_bridge" not in text:
            continue
        for m in re.finditer(r"from\s+[\w.]*runtime_bridge\s+import\s+(\((?:[^)]*)\)|[^\n]+)", text):
            names.update(re.findall(r"\b(_[A-Za-z_][A-Za-z0-9_]*)\b", m.group(1)))
        for m in re.finditer(r'monkeypatch\.setattr\(\s*([^,]+),\s*["\'](_[A-Za-z_][A-Za-z0-9_]*)["\']', text):
            target = m.group(1)
            if "runtime_bridge" in target or target.strip() in {"rb"}:
                names.add(m.group(2))
        for m in re.finditer(r'(?:mocker\.patch|patch)\(\s*["\']([\w.]*runtime_bridge\.(_[A-Za-z_][A-Za-z0-9_]*))["\']', text):
            names.add(m.group(2))
        for m in re.finditer(r"\bruntime_bridge\.(_[A-Za-z_][A-Za-z0-9_]*)", text):
            names.add(m.group(1))
    names -= _INVENTORY_NOISE_EXCLUDED
    names -= _DECISION_MODULE_SYMBOLS_OUT_OF_SCOPE
    names -= _INTERNAL_DECOMPOSITION_SYMBOLS
    return names


# ===========================================================================
# Guard (B) — static AST guard
# ===========================================================================


ALL_COMPAT_SYMBOLS: tuple[str, ...] = tuple(
    sorted(set(REACH) | set(UNREACHABLE_FROM_CANONICAL_ENTRIES) | set(GUARD_B_ONLY_IMPORT_SURFACE))
)


# Compat symbols that are DEFINED in runtime.next.decision and imported into
# runtime_bridge as compat surface — they are legitimately cross-module on
# UNMODIFIED source (not relocated by this mission). ``_build_prompt_safe`` /
# ``_find_first_wp_by_lane`` are also decision-origin but are out of scope for
# this guard (bound only through ``runtime.next.decision``, see
# ``_DECISION_MODULE_SYMBOLS_OUT_OF_SCOPE``), so they are not in ALL_COMPAT_
# SYMBOLS and not listed here.
_DECISION_ORIGIN_BASELINE: frozenset[str] = frozenset(
    {"_state_to_action", "_compute_wp_progress", "_build_prompt_or_error"}
)


def test_guard_b_identity_reexport_for_relocated_symbols() -> None:
    """Every compat symbol not natively defined in runtime_bridge.py must be
    the IDENTICAL object as its origin module's — never a copy.

    On unmodified source the only cross-module compat symbols are the three
    ``runtime.next.decision``-origin names (``_DECISION_ORIGIN_BASELINE``) that
    runtime_bridge already imports and re-exports. The per-symbol identity
    assertion below verifies ``rb.x is decision.x`` for them today and becomes
    load-bearing for every symbol WP03+ relocates into a seam; the final
    baseline-set assertion trips if a relocation quietly changes the
    cross-module surface without this guard being updated.
    """
    import sys

    relocated_names: set[str] = set()
    for name in ALL_COMPAT_SYMBOLS:
        obj = getattr(rb, name, None)
        if obj is None:
            continue
        origin_module_name: str | None = getattr(obj, "__module__", None)
        if origin_module_name is None or origin_module_name == rb.__name__:
            continue  # natively defined in runtime_bridge.py
        relocated_names.add(name)
        origin_module = sys.modules.get(origin_module_name)
        assert origin_module is not None, f"origin module {origin_module_name!r} for {name!r} not imported"
        assert getattr(origin_module, name, None) is obj, (
            f"{name!r} on runtime_bridge is NOT the same object as "
            f"{origin_module_name}.{name} -- the compat re-export is a copy, "
            "not an identity re-export (false-green under patching)."
        )
    assert relocated_names == set(_DECISION_ORIGIN_BASELINE), (
        "cross-module compat surface changed. On unmodified source only "
        f"{sorted(_DECISION_ORIGIN_BASELINE)} are decision-origin; observed "
        f"{sorted(relocated_names)}. If WP03+ relocated a symbol into a seam, "
        "add it to _DECISION_ORIGIN_BASELINE (the per-symbol identity check "
        "above already guards its re-export correctness)."
    )


def test_guard_b_no_function_scope_reimport_of_compat_names() -> None:
    """AST-walk runtime_bridge.py and forbid any Import/ImportFrom binding a
    compat name below module scope. A function-local re-import of a compat
    name shadows the patchable module global -- the exact structural
    signature of false-green shadowing this guard exists to forbid.
    """
    compat_names = set(ALL_COMPAT_SYMBOLS)
    source = Path(rb.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    violations: list[str] = []

    class _NestedImportVisitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.depth = 0

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
            self.depth += 1
            self.generic_visit(node)
            self.depth -= 1

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
            self.depth += 1
            self.generic_visit(node)
            self.depth -= 1

        def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
            if self.depth > 0:
                for alias in node.names:
                    bound = (alias.asname or alias.name).rsplit(".", 1)[-1]
                    if bound in compat_names:
                        violations.append(f"line {node.lineno}: import {alias.name}")
            self.generic_visit(node)

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
            if self.depth > 0:
                for alias in node.names:
                    bound = alias.asname or alias.name
                    if bound in compat_names:
                        violations.append(
                            f"line {node.lineno}: from {node.module} import {alias.name}"
                        )
            self.generic_visit(node)

    _NestedImportVisitor().visit(tree)
    assert not violations, "Function-scope re-imports of compat names found (false-green shadowing):\n" + "\n".join(
        violations
    )


def test_guard_b_all_compat_symbols_present_on_module() -> None:
    """Import-surface snapshot: every symbol in the frozen compat set must
    currently be an attribute of runtime_bridge, so a future refactor that
    quietly drops a re-export trips this test with the exact missing name.
    """
    missing = [name for name in ALL_COMPAT_SYMBOLS if not hasattr(rb, name)]
    assert not missing, f"Compat symbols missing from runtime_bridge: {missing}"
