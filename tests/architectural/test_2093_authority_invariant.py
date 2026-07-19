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

3. **The phase-1 flag is the SOLE sanctioned reader-authority gate** — hardened
   two ways (#2816):
   (a) the reader-module list is **DERIVED** by AST-walking
   ``src/specify_cli/{status,cli,core,task_utils}`` for ``extract_scalar(...,
   "<dynamic field>")`` reads (never a hardcoded list), so a NEW ungated bypass
   reader auto-joins the derived set and trips the allow-list tripwire; and
   (b) the tolerated gate is asserted by **imported-symbol IDENTITY** — every
   name that resolves to the one canonical ``phase1_snapshot_authority_active``
   object (its ``__name__`` plus every facade alias pointing at the same object)
   — never a name-substring heuristic. A differently-named second authority gate
   (``*_authority_active``) anywhere on the reader path, or a new bypass reader,
   turns this red. The writer-side ``*_dual_write_*`` helpers and the lane-mirror
   gate are deliberately NOT reader-authority gates and are excluded.

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
# Arm 3 — the phase-1 flag is the SOLE sanctioned reader-authority gate
# ===========================================================================
#
# Hardened (#2816): the reader-module list is DERIVED (AST-walk for dynamic-field
# extract_scalar reads), and the tolerated gate is asserted by imported-symbol
# IDENTITY, not a name substring.

import specify_cli.status as _status_facade  # noqa: E402
from specify_cli.status.emit import _phase1_snapshot_authority_active as _CANONICAL_GATE  # noqa: E402

#: The dynamic runtime-state fields whose authority is the event log
#: (data-model.md). A frontmatter read of any of these via ``extract_scalar`` is
#: a reader-authority site the invariant tracks.
_DYNAMIC_RUNTIME_FIELDS: frozenset[str] = frozenset(
    {
        "agent",
        "assignee",
        "shell_pid",
        "shell_pid_created_at",
        "tracker_refs",
        "reviewer",
        "reviewer_agent",
        "reviewer_shell_pid",
        "review_status",
        "reviewed_by",
        "approved_by",
        "review_feedback",
    }
)

_READER_AUTHORITY_ROOTS = ("status", "cli", "core", "task_utils")

#: The curated baseline of modules that legitimately read a dynamic runtime field
#: via ``extract_scalar``. A module APPEARING in the AST-derived set but NOT here
#: is a NEW ungated bypass reader (the tripwire). Sanctioned-gated seams
#: (``support.py`` WorkPackage fallbacks; ``tasks_status_cmd.py`` gated status
#: board) sit alongside PRE-EXISTING ungated readers deliberately left OUT of the
#: #2816 scope (``tasks_move_task.py`` current_agent/shell_pid ownership read;
#: ``workflow_cores.py`` review_status/review_feedback read) — those are tracked
#: as remaining #2093 debt, not fixed here; the tripwire only forbids NEW ones.
#: ``tasks.py`` add-history is intentionally ABSENT: it now routes through
#: ``WorkPackage.agent``/``.shell_pid`` (the ``support.py`` seam already listed),
#: so it holds no independent frontmatter-authority path.
_SANCTIONED_READER_MODULES: frozenset[str] = frozenset(
    {
        "src/specify_cli/task_utils/support.py",
        "src/specify_cli/cli/commands/agent/tasks_status_cmd.py",
        "src/specify_cli/cli/commands/agent/tasks_move_task.py",
        "src/specify_cli/cli/commands/agent/workflow_cores.py",
    }
)


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "src" / "specify_cli").is_dir():
            return parent
    raise AssertionError("could not locate repo root from test file")


def _iter_root_modules(root: Path) -> list[Path]:
    modules: list[Path] = []
    for pkg in _READER_AUTHORITY_ROOTS:
        modules.extend(sorted((root / "src" / "specify_cli" / pkg).rglob("*.py")))
    return modules


def _sanctioned_gate_names() -> frozenset[str]:
    """Every identifier that resolves, BY IDENTITY, to the one canonical gate.

    The private ``__name__`` plus every ``specify_cli.status`` facade attribute
    whose value ``is`` the canonical object. Derived from the live object's
    identity — not a hardcoded string — so the arm tracks any future rename of
    the gate or its facade alias automatically (2b).
    """
    aliases = {name for name, value in vars(_status_facade).items() if value is _CANONICAL_GATE}
    return frozenset(aliases | {_CANONICAL_GATE.__name__})


def _reads_dynamic_field_via_extract_scalar(tree: ast.AST) -> bool:
    """True if the module calls ``extract_scalar(<any>, "<dynamic field>")``."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else None
        if name != "extract_scalar" or len(node.args) < 2:
            continue
        field_arg = node.args[1]
        if isinstance(field_arg, ast.Constant) and field_arg.value in _DYNAMIC_RUNTIME_FIELDS:
            return True
    return False


def _derive_reader_authority_modules(root: Path) -> set[str]:
    """AST-derived reader modules — the hardened replacement for the old hardcoded
    tuple. Any module under the four roots that reads a dynamic runtime field via
    ``extract_scalar`` is a reader-authority site; a NEW one auto-joins."""
    derived: set[str] = set()
    for path in _iter_root_modules(root):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        if _reads_dynamic_field_via_extract_scalar(tree):
            derived.add(path.relative_to(root).as_posix())
    return derived


def _referenced_authority_gates(tree: ast.AST) -> set[str]:
    """Referenced identifiers that play a snapshot-vs-frontmatter READER-AUTHORITY
    gate role — name ends with ``_authority_active`` (the sanctioned
    ``_phase1_snapshot_authority_active`` / its facade alias, and any competing
    sibling). Writer-side ``*_dual_write_*`` helpers and the lane-mirror
    (``_legacy_lane_mirror_enabled``) gate are NOT reader-authority gates and are
    deliberately excluded so this arm tracks the ONE reader concern."""
    gates: set[str] = set()
    for node in ast.walk(tree):
        name: str | None = None
        if isinstance(node, ast.Name):
            name = node.id
        elif isinstance(node, ast.Attribute):
            name = node.attr
        elif isinstance(node, ast.FunctionDef):
            name = node.name
        if name and name.endswith("_authority_active"):
            gates.add(name)
    return gates


def test_facade_reexports_the_exact_gate_object() -> None:
    """2b precondition: the public facade export IS the private emit gate object
    (identity), so identity-based tolerance below cannot be spoofed by a
    same-named but distinct symbol."""
    assert _status_facade.phase1_snapshot_authority_active is _CANONICAL_GATE


def test_reader_authority_gate_is_solely_the_canonical_phase1_gate() -> None:
    """Across every module under the reader-authority roots, the only
    ``*_authority_active`` reader gate is the canonical
    ``phase1_snapshot_authority_active`` object (by identity). A differently-named
    second authority gate turns this red; writer-side dual-write / lane-mirror
    gates are excluded by construction."""
    root = _repo_root()
    sanctioned = _sanctioned_gate_names()
    discovered: set[str] = set()
    for path in _iter_root_modules(root):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        discovered |= _referenced_authority_gates(tree)

    assert discovered, "expected the phase-1 authority gate to appear on the reader path"
    unexpected = discovered - sanctioned
    assert not unexpected, (
        "a reader-authority gate OTHER than the canonical "
        f"phase1_snapshot_authority_active was found: {sorted(unexpected)} "
        "(a second authority path is the #2093 split-brain this mission closes)"
    )
    # Non-vacuous: the sanctioned identity really is present (deferred cutover
    # keeps exactly one sanctioned gate — NOT the post-cutover empty set).
    assert discovered >= sanctioned


def test_no_new_ungated_bypass_reader_of_dynamic_fields() -> None:
    """The AST-DERIVED set of dynamic-field ``extract_scalar`` readers must not
    exceed the curated sanctioned baseline. A NEW module reading a runtime field
    from frontmatter outside the sanctioned seam trips this — the hardened
    replacement for the old hardcoded module tuple."""
    root = _repo_root()
    derived = _derive_reader_authority_modules(root)

    # Non-vacuous: the derivation really finds the known readers (a broken AST
    # walk that discovered nothing would otherwise pass silently).
    assert derived, "expected the AST derivation to discover the known reader modules"

    new_bypass = derived - _SANCTIONED_READER_MODULES
    assert not new_bypass, (
        "a NEW module reads a dynamic runtime field via extract_scalar outside the "
        f"sanctioned gated seam (#2093 bypass): {sorted(new_bypass)}. Route the read "
        "through the phase-1 gated seam (WorkPackage / wp_snapshot_state + the flag) "
        "and, only if it is a genuinely sanctioned reader, add it to "
        "_SANCTIONED_READER_MODULES."
    )
