"""IC-04 / WP05 / D-09 — dashboard scanner routes RUNTIME reads onto the snapshot.

``dashboard/scanner._process_wp_file`` is a bypass reader the #2093
frontmatter-authority invariant was blind to (it read typed ``WPMetadata``
attributes, not ``extract_scalar``). Its RUNTIME fields (agent/assignee +
subtask completion) now resolve the reduced snapshot. Resolved
``role``/``agent_profile``/``model`` also come from runtime annotations, while
their distinctly labelled authored recommendations stay frontmatter-sourced.

No test mocks ``wp_snapshot_state`` / the reducer — every runtime slot is
seeded as a real event over a real event log.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.dashboard.scanner import _process_wp_file
from specify_cli.status import (
    Lane,
    WPInnerStateDelta,
    emit_inner_state_changed,
)
from specify_cli.status.models import StatusEvent
from specify_cli.status.store import append_event

pytestmark = pytest.mark.fast

_MISSION_SLUG = "021-test"
_CLAIM_EVID = "01J8Z9ABCDEFGHJKMNPQRSTVWX"


def _seed_scanner_wp(
    tmp_path: Path,
    *,
    fm_agent: str,
    fm_assignee: str,
    model: str,
    agent_profile: str,
    role: str,
    subtasks: tuple[str, ...] = (),
) -> Path:
    """Create ``kitty-specs/<slug>/tasks/WP01-x.md`` + a bootstrapped event log,
    returning the WP prompt file. Frontmatter runtime fields are seeded to
    DIVERGE from the snapshot slots seeded by the caller."""
    feature_dir = tmp_path / "kitty-specs" / _MISSION_SLUG
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    prompt_file = tasks_dir / "WP01-x.md"
    subtask_lines = (
        ["subtasks:", *(f'  - "{task_id}"' for task_id in subtasks)]
        if subtasks
        else ["subtasks: []"]
    )
    frontmatter = [
        "---",
        'work_package_id: "WP01"',
        'title: "Scanner Test WP"',
        f'agent: "{fm_agent}"',
        f'assignee: "{fm_assignee}"',
        f'model: "{model}"',
        f'agent_profile: "{agent_profile}"',
        f'role: "{role}"',
        *subtask_lines,
        "---",
        "# Work Package Prompt: Scanner Test WP",
        "",
    ]
    prompt_file.write_text("\n".join(frontmatter), encoding="utf-8")
    # A real transition so the event log exists and get_wp_lane returns a lane.
    append_event(
        feature_dir,
        StatusEvent(
            event_id=_CLAIM_EVID,
            mission_slug=_MISSION_SLUG,
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-07-20T12:00:00+00:00",
            actor="snap-agent",
            force=False,
            execution_mode="worktree",
        ),
    )
    return prompt_file


def test_scanner_runtime_fields_resolve_snapshot_over_frontmatter(tmp_path: Path) -> None:
    """A WP whose frontmatter agent/assignee DIVERGE from the snapshot slots
    renders the SNAPSHOT values (proves snapshot authority, not the WPMetadata
    attribute)."""
    prompt_file = _seed_scanner_wp(
        tmp_path,
        fm_agent="fm-agent",
        fm_assignee="fm-assignee",
        model="fm-model",
        agent_profile="fm-profile",
        role="fm-role",
    )
    feature_dir = prompt_file.parent.parent
    emit_inner_state_changed(
        feature_dir,
        "WP01",
        WPInnerStateDelta(agent="snap-agent", assignee="snap-assignee"),
        actor="snap-agent",
        mission_slug=_MISSION_SLUG,
    )

    result = _process_wp_file(prompt_file, tmp_path, "planned")

    assert result is not None
    assert result["agent"] == "snap-agent"
    assert result["assignee"] == "snap-assignee"


def test_scanner_subtask_completion_from_snapshot_slot(tmp_path: Path) -> None:
    """Subtask completion is counted from the snapshot ``subtasks`` slot
    (id -> lane status), not tasks.md/prompt checkbox counting."""
    prompt_file = _seed_scanner_wp(
        tmp_path,
        fm_agent="fm-agent",
        fm_assignee="fm-assignee",
        model="fm-model",
        agent_profile="fm-profile",
        role="fm-role",
        subtasks=("T01", "T02", "T03"),
    )
    feature_dir = prompt_file.parent.parent
    emit_inner_state_changed(
        feature_dir,
        "WP01",
        WPInnerStateDelta(
            subtasks={"T01": Lane.DONE, "T02": Lane.DONE, "T03": Lane.IN_PROGRESS}
        ),
        actor="snap-agent",
        mission_slug=_MISSION_SLUG,
    )

    result = _process_wp_file(prompt_file, tmp_path, "planned")

    assert result is not None
    assert result["subtasks_done"] == 2
    assert result["subtasks_total"] == 3


def test_scanner_partial_snapshot_uses_authored_roster_as_total(tmp_path: Path) -> None:
    """A single completed delta cannot make a two-item authored roster look 1/1."""
    from specify_cli.status import reconstruct_wp_view

    prompt_file = _seed_scanner_wp(
        tmp_path,
        fm_agent="fm-agent",
        fm_assignee="fm-assignee",
        model="fm-model",
        agent_profile="fm-profile",
        role="fm-role",
        subtasks=("T01", "T02"),
    )
    feature_dir = prompt_file.parent.parent
    emit_inner_state_changed(
        feature_dir,
        "WP01",
        WPInnerStateDelta(subtasks={"T01": Lane.DONE}),
        actor="snap-agent",
        mission_slug=_MISSION_SLUG,
    )

    view = reconstruct_wp_view(feature_dir, "WP01")
    result = _process_wp_file(prompt_file, tmp_path, "planned")

    assert result is not None
    assert view.authored.subtasks == ("T01", "T02")
    assert result["subtasks"] == list(view.authored.subtasks)
    assert result["subtasks_done"] == 1
    assert result["subtasks_total"] == 2


def test_scanner_no_snapshot_runtime_state_renders_empty(tmp_path: Path) -> None:
    """A WP with only a transition (no runtime slots) renders empty runtime
    fields and (0, 0) subtasks — the "no runtime state yet" result."""
    prompt_file = _seed_scanner_wp(
        tmp_path,
        fm_agent="fm-agent",
        fm_assignee="fm-assignee",
        model="fm-model",
        agent_profile="fm-profile",
        role="fm-role",
    )

    result = _process_wp_file(prompt_file, tmp_path, "planned")

    assert result is not None
    assert result["agent"] == ""
    assert result["assignee"] == ""
    assert result["model"] == ""
    assert result["agent_profile"] == ""
    assert result["role"] == ""
    assert result["authored_model"] == "fm-model"
    assert result["authored_agent_profile"] == "fm-profile"
    assert result["authored_role"] == "fm-role"
    assert result["subtasks_done"] == 0
    assert result["subtasks_total"] == 0


def test_scanner_labels_authored_identity_separately(tmp_path: Path) -> None:
    """Authored intent stays labelled and never replaces absent actual slots."""
    prompt_file = _seed_scanner_wp(
        tmp_path,
        fm_agent="fm-agent",
        fm_assignee="fm-assignee",
        model="fm-model",
        agent_profile="fm-profile",
        role="fm-role",
    )
    feature_dir = prompt_file.parent.parent
    # Even with a diverging runtime agent in the snapshot, authored intent holds.
    emit_inner_state_changed(
        feature_dir,
        "WP01",
        WPInnerStateDelta(agent="snap-agent"),
        actor="snap-agent",
        mission_slug=_MISSION_SLUG,
    )

    result = _process_wp_file(prompt_file, tmp_path, "planned")

    assert result is not None
    assert result["agent"] == "snap-agent"
    assert result["model"] == ""
    assert result["agent_profile"] == ""
    assert result["role"] == ""
    assert result["authored_model"] == "fm-model"
    assert result["authored_agent_profile"] == "fm-profile"
    assert result["authored_role"] == "fm-role"
