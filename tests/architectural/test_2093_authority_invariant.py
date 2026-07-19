"""FR-013 / #2093 — single-authority-per-field architectural invariant.

The WP-runtime-state eviction folds runtime-mutable WP state (``shell_pid``,
subtask completion, ``## Activity Log`` notes, ``tracker_refs``,
``agent``/``assignee``, review-cycle fields) out of ``tasks/WP##.md`` into the
append-only event log. #2093 is the split-brain this closes: a field must have
exactly ONE authority. This test is the enforcing net so the guarantee cannot
silently rot under a future refactor.

It asserts, in the **shipped dual-write end-state** (``status_phase: 1`` = flag
ON, the event-sourced read path):

1. **No dynamic field is read from frontmatter as authority** — behavioral
   proof on the canonical ``WorkPackage`` reader: at flag ON the reduced
   snapshot WINS over a divergent frontmatter value for every dynamic scalar
   slot; at flag OFF the frontmatter is the tolerated migration-window
   fallback. Inverting the read (frontmatter as authority) turns this red.

2. **No field is dual-homed** — the static authored schema
   (``FrontmatterManager.WP_FIELD_ORDER``) and the event-sourced slot set
   (``status.reducer._RUNTIME_SLOTS``) share only the explicitly TOLERATED
   migration-window cosmetic slots (deferred to IC-08). ``tracker_refs``
   (FR-006, struck from ``WP_FIELD_ORDER`` by WP07), ``notes`` and ``review``
   are purely event-sourced and MUST NOT appear in the static schema —
   re-homing any of them turns this red.

3. **The phase-1 flag is the SOLE sanctioned migration-window fallback** — the
   tolerated-gate set is exactly ``{_phase1_dual_write_enabled}`` (NOT empty, as
   a post-cutover world would assume — the corpus cutover is deferred). A
   SECOND, competing authority gate introduced into the reader path turns this
   red.

Refactor-stable: every arm keys on imported symbol / slot-name identity and
runtime behavior, never on line numbers or source text of a specific call.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from specify_cli.frontmatter import FrontmatterManager
from specify_cli.status.models import Lane, StatusEvent, WPInnerStateDelta
from specify_cli.status.reducer import _RUNTIME_SLOTS
from specify_cli.status.store import append_event
from specify_cli.task_utils import WorkPackage

pytestmark = pytest.mark.architectural

# ---------------------------------------------------------------------------
# The field-authority table (data-model.md), encoded as symbol identity.
# ---------------------------------------------------------------------------

#: The dynamic runtime-state slot set — the event log is the sole authority for
#: these. Imported straight from the reducer (single source of truth).
_EVENT_SLOTS: frozenset[str] = frozenset(_RUNTIME_SLOTS)

#: The migration-window cosmetic slots still emitted into the authored schema
#: under dual-write. Their removal from ``WP_FIELD_ORDER`` is the DEFERRED IC-08
#: post-cutover reduction — tolerated here, NOT a dual-home authority (the
#: frontmatter copy is a mirror, the snapshot is the authority; arm 1 proves it).
_TOLERATED_MIGRATION_WINDOW_SLOTS: frozenset[str] = frozenset(
    {"subtasks", "assignee", "agent", "shell_pid", "shell_pid_created_at"}
)

#: The single sanctioned migration-window authority gate. NOT empty: the corpus
#: ``backfill -> verify -> cutover`` is deferred, so the flag-gated frontmatter
#: fallback is retained. A second gate here is a #2093 regression.
_TOLERATED_MIGRATION_GATES: frozenset[str] = frozenset({"_phase1_dual_write_enabled"})


def _feature_with_flag(tmp_path: Path, *, flag_on: bool) -> tuple[Path, Path]:
    """Build a minimal ``kitty-specs/<slug>`` feature dir + WP file.

    Frontmatter deliberately carries DIVERGENT dynamic values so arm 1 can tell
    which home won. Returns ``(feature_dir, wp_file)``.
    """
    slug = "001-authority-invariant"
    feature_dir = tmp_path / "kitty-specs" / slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": "01AUTHORITYINVARIANT00000",
                "mid8": "01AUTHOR",
                "mission_slug": slug,
                "mission_type": "software-dev",
                "status_phase": "1" if flag_on else "0",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    wp_file = tasks_dir / "WP01-core.md"
    wp_file.write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Core\n"
        "agent: frontmatter-agent\n"
        "assignee: frontmatter-assignee\n"
        "shell_pid: '11111'\n"
        "---\n\n# WP01\n",
        encoding="utf-8",
    )
    return feature_dir, wp_file


def _make_work_package(wp_file: Path) -> WorkPackage:
    content = wp_file.read_text(encoding="utf-8")
    _, _, body = content.partition("---\n")
    front, _, body_text = body.partition("\n---\n")
    return WorkPackage(
        feature="001-authority-invariant",
        path=wp_file,
        current_lane="claimed",
        relative_subpath=Path("tasks/WP01-core.md"),
        frontmatter=front,
        body=body_text,
        padding="",
    )


# ===========================================================================
# Arm 1 — no dynamic field is read from frontmatter as AUTHORITY (flag ON)
# ===========================================================================


def test_snapshot_is_authority_over_frontmatter_at_flag_on(tmp_path: Path) -> None:
    """At ``status_phase: 1`` the reduced snapshot WINS over a divergent
    frontmatter value for every dynamic scalar slot — the event log is the
    authority, frontmatter is not read as authority."""
    feature_dir, wp_file = _feature_with_flag(tmp_path, flag_on=True)

    # Claim rides the transition policy_metadata (agent/shell_pid); assignee is
    # an off-axis annotation. All DIVERGE from the frontmatter values above.
    append_event(
        feature_dir,
        StatusEvent(
            event_id="seed-claim",
            mission_slug="001-authority-invariant",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-01-01T00:00:01+00:00",
            actor="fixture",
            force=True,
            execution_mode="worktree",
            policy_metadata={"shell_pid": 99999, "agent": "snapshot-agent"},
        ),
    )
    from specify_cli.status.emit import emit_inner_state_changed

    emit_inner_state_changed(
        feature_dir,
        "WP01",
        WPInnerStateDelta(assignee="snapshot-assignee"),
        actor="fixture",
        mission_slug="001-authority-invariant",
        at="2026-01-01T00:00:02+00:00",
    )

    wp = _make_work_package(wp_file)
    assert wp.agent == "snapshot-agent", "agent authority is frontmatter, not the event log (#2093)"
    assert wp.shell_pid == "99999", "shell_pid authority is frontmatter, not the event log (#2093)"
    assert wp.assignee == "snapshot-assignee", "assignee authority is frontmatter, not the event log (#2093)"


def test_frontmatter_is_tolerated_fallback_only_at_flag_off(tmp_path: Path) -> None:
    """Positive control for the tolerated migration-window fallback: at flag OFF
    (no cutover) the same reader falls back to frontmatter — proving arm 1's
    flag-ON result is the snapshot winning, not a coincidence."""
    feature_dir, wp_file = _feature_with_flag(tmp_path, flag_on=False)
    append_event(
        feature_dir,
        StatusEvent(
            event_id="seed-claim",
            mission_slug="001-authority-invariant",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-01-01T00:00:01+00:00",
            actor="fixture",
            force=True,
            execution_mode="worktree",
            policy_metadata={"shell_pid": 99999, "agent": "snapshot-agent"},
        ),
    )
    wp = _make_work_package(wp_file)
    assert wp.agent == "frontmatter-agent"
    assert wp.shell_pid == "11111"


# ===========================================================================
# Arm 2 — no field is dual-homed (static schema ∩ event-slot set)
# ===========================================================================


def test_no_field_is_dual_homed_static_and_event() -> None:
    """``WP_FIELD_ORDER`` ∩ ``_RUNTIME_SLOTS`` == exactly the tolerated
    migration-window cosmetic slots. ``tracker_refs``/``notes``/``review`` are
    purely event-sourced and MUST NOT appear in the static authored schema."""
    static_schema = set(FrontmatterManager.WP_FIELD_ORDER)
    dual_homed = static_schema & set(_EVENT_SLOTS)

    unexpected = dual_homed - _TOLERATED_MIGRATION_WINDOW_SLOTS
    assert not unexpected, (
        "field(s) dual-homed in BOTH the static authored schema (WP_FIELD_ORDER) "
        f"and the event-sourced slot set — a #2093 split-brain: {sorted(unexpected)}"
    )

    # The eviction targets must be gone from the static schema (bites on a
    # regression that re-authors them).
    for evicted in ("tracker_refs", "notes", "review"):
        assert evicted not in static_schema, (
            f"{evicted!r} is event-sourced (FR-006/SC-004/FR-009) and must NOT be "
            "re-listed in WP_FIELD_ORDER (dual-home regression)"
        )

    # The tolerated set is a genuine subset of the event slots (guards a typo
    # that would make the arm vacuous).
    assert set(_EVENT_SLOTS) >= _TOLERATED_MIGRATION_WINDOW_SLOTS


# ===========================================================================
# Arm 3 — the phase-1 flag is the SOLE sanctioned migration-window fallback
# ===========================================================================

_READER_AUTHORITY_MODULES = (
    "src/specify_cli/task_utils/support.py",
    "src/specify_cli/status/wp_metadata.py",
    "src/specify_cli/core/stale_detection.py",
    "src/specify_cli/status/emit.py",
)


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "src" / "specify_cli").is_dir():
            return parent
    raise AssertionError("could not locate repo root from test file")


def _referenced_gate_symbols(module_path: Path) -> set[str]:
    """Every referenced identifier on the reader-authority path that plays a
    migration-flag role (name contains ``dual_write`` or ``phase`` + a gate
    suffix). AST-based so it survives relocation/renaming of surrounding code.
    """
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    gates: set[str] = set()
    for node in ast.walk(tree):
        name: str | None = None
        if isinstance(node, ast.Name):
            name = node.id
        elif isinstance(node, ast.Attribute):
            name = node.attr
        elif isinstance(node, ast.FunctionDef):
            name = node.name
        if name and ("dual_write" in name or ("phase" in name and name.endswith("enabled"))):
            gates.add(name)
    return gates


def test_phase1_flag_is_the_sole_tolerated_migration_gate() -> None:
    """Across the reader-authority modules, the ONLY migration-window authority
    gate is ``_phase1_dual_write_enabled``. A second dual-write / phase flag
    (competing authority) fails here."""
    root = _repo_root()
    discovered: set[str] = set()
    for rel in _READER_AUTHORITY_MODULES:
        discovered |= _referenced_gate_symbols(root / rel)

    assert discovered, "expected the phase-1 gate to appear on the reader path"
    unexpected = discovered - _TOLERATED_MIGRATION_GATES
    assert not unexpected, (
        "a migration-window authority gate OTHER than the sanctioned "
        f"_phase1_dual_write_enabled was found on the reader path: {sorted(unexpected)} "
        "(a second authority path is the #2093 split-brain this mission closes)"
    )
    # The tolerated set is non-empty and really present (the deferred cutover
    # keeps exactly one sanctioned fallback — NOT the post-cutover empty set).
    assert discovered >= _TOLERATED_MIGRATION_GATES
